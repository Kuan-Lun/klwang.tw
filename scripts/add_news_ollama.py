#!/usr/bin/env python3
"""Run the add-news workflow with a local Ollama model; no coding agent needed.

The pipeline mirrors skills/add-news/SKILL.md:

1. scripts/archive-urls.sh queues and archives every URL (OK / DUP / FAIL).
2. scripts/news-context.sh supplies slug, tag, and destination context.
3. Each article is read from the original URL, then the archived snapshot,
   then FlareSolverr, and reduced to title/date/body evidence.
4. The local model returns title, date, description, destination, tags,
   a filename phrase, and an optional slug override as strict JSON.
5. The answer is validated against the taxonomy policy, the slug is checked
   for repository-wide uniqueness, and scripts/write-news.sh writes the file.
6. Created and duplicate URLs leave the queue, a bucketed report is printed,
   and the model is unloaded from memory. When this script had to start
   `ollama serve` itself, that server process is stopped as well.

Usage:
    scripts/add-news-ollama.sh [options] [url ...]
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path, PurePosixPath

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
NEWS_DIR = REPO_ROOT / "source-code/content/news"
QUEUE_FILE = NEWS_DIR / "toadd-news.txt"
SKILL_DIR = REPO_ROOT / "skills/add-news"
TAXONOMY_MD = SKILL_DIR / "references/news-taxonomy.md"
POLICY_TOML = SKILL_DIR / "references/news-taxonomy.toml"

if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from news_taxonomy import load_policy, read_articles  # noqa: E402

DEFAULT_MODEL = os.environ.get("ADD_NEWS_MODEL", "qwen3.8:27b")
DEFAULT_OLLAMA_URL = os.environ.get("ADD_NEWS_OLLAMA_URL", "http://localhost:11434")
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
ROOT_DESTINATION = "."
MAX_BODY_CHARS = 5000
MIN_READABLE_CHARS = 200

# URL path words that never identify an article.
DROP_SEGMENTS = {
    "news", "story", "stories", "article", "articles", "local", "detail",
    "details", "life", "society", "realtimenews", "breakingnews", "amp", "id",
    "post", "posts", "category", "cat", "content", "view", "index", "politics",
    "world", "entertainment", "sports", "finance", "money", "tech",
    "international", "paper", "breaking", "realtime", "zhongwen", "trad",
    "simp", "zh-tw", "zh-hant", "page", "p", "n", "a", "s", "m",
}
# Host labels that belong to the public suffix rather than the outlet name.
SUFFIX_LABELS = {
    "com", "net", "org", "gov", "edu", "co", "tw", "mg", "cn", "hk", "jp",
    "uk", "us", "io", "info", "biz", "ac", "kr", "sg", "my", "au",
}
LEADING_HOST_LABELS = {"www", "news", "m", "amp", "mobile", "tw", "en", "zh"}
ID_QUERY_KEY = re.compile(r"(id|no|sn|num|key)$", re.IGNORECASE)
FILE_EXTENSION = re.compile(
    r"\.(html?|htm|aspx?|php|jsp|shtml|cfm|xhtml)$", re.IGNORECASE
)
DATE_SEGMENT = re.compile(r"^(19|20)\d{6}$")
SLUG_SHAPE = re.compile(r"^[a-z0-9]+(?:-[A-Za-z0-9]+)+$")
CHALLENGE_TITLE = re.compile(
    r"just a moment|attention required|access denied|checking your browser|"
    r"verify you are human|captcha|\b40[34]\b|page not found|找不到網頁|"
    r"請稍候|驗證您|瀏覽器驗證|error",
    re.IGNORECASE,
)
HOOK_PREFIX = re.compile(r"^(?:[^／/]{1,4}[／/])+")
DATE_PATTERNS = (
    re.compile(r"(?<!\d)(\d{4})[-/.年](\d{1,2})[-/.月](\d{1,2})"),
    re.compile(r"(?<!\d)((?:19|20)\d{2})(\d{2})(\d{2})(?!\d)"),
)
META_TITLE_KEYS = ("og:title", "twitter:title", "headline", "title")
META_DATE_KEYS = (
    "article:published_time", "og:article:published_time", "datepublished",
    "pubdate", "publishdate", "publish_date", "publish-date", "date",
    "dc.date", "dc.date.issued", "dcterms.created", "dcterms.date",
    "sailthru.date", "parsely-pub-date", "article:modified_time",
)
META_DESCRIPTION_KEYS = ("og:description", "twitter:description", "description")


# ---------------------------------------------------------------------------
# Shell helpers


def run_script(name: str, *args: str, timeout: int | None = None) -> str:
    """Run a repository script and return stdout; stderr is passed through."""
    completed = subprocess.run(
        [str(SCRIPT_DIR / name), *args],
        capture_output=True,
        text=True,
        timeout=timeout,
        cwd=REPO_ROOT,
        check=False,
    )
    if completed.stderr:
        sys.stderr.write(completed.stderr)
    if completed.returncode != 0:
        raise RuntimeError(f"{name} exited with {completed.returncode}")
    return completed.stdout


def curl(url: str, timeout: int = 30) -> bytes:
    completed = subprocess.run(
        ["curl", "-sS", "-L", "--compressed", "-m", str(timeout), "-A", USER_AGENT, url],
        capture_output=True,
        timeout=timeout + 10,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.decode("utf-8", "replace").strip())
    return completed.stdout


def decode_html(raw: bytes) -> str:
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        pass
    head = raw[:4096].decode("ascii", "ignore")
    match = re.search(r"charset=[\"']?([A-Za-z0-9_-]+)", head, re.IGNORECASE)
    if match:
        try:
            return raw.decode(match.group(1))
        except (UnicodeDecodeError, LookupError):
            pass
    for encoding in ("big5", "gb18030"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", "replace")


# ---------------------------------------------------------------------------
# Page evidence extraction


def normalize_date(value: str | None) -> str | None:
    if not value:
        return None
    for pattern in DATE_PATTERNS:
        match = pattern.search(value)
        if not match:
            continue
        try:
            date = dt.date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
        except ValueError:
            continue
        if 1990 <= date.year <= 2100:
            return date.isoformat()
    return None


def find_dates(text: str) -> list[str]:
    found: list[str] = []
    for pattern in DATE_PATTERNS:
        for match in pattern.finditer(text):
            date = normalize_date(match.group(0))
            if date and date not in found:
                found.append(date)
    return found


class _PageParser(HTMLParser):
    SKIP_TAGS = frozenset({"script", "style", "noscript", "template", "svg", "iframe"})
    TEXT_TAGS = frozenset(
        {"p", "li", "h2", "h3", "h4", "blockquote", "td", "figcaption", "pre"}
    )
    # Block containers whose start or end also terminates an unclosed text tag.
    BLOCK_TAGS = frozenset(
        {"div", "section", "article", "header", "footer", "nav", "aside", "ul",
         "ol", "table", "tr", "main", "figure", "form"}
    )

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.metas: dict[str, str] = {}
        self.title = ""
        self.h1s: list[str] = []
        self.times: list[str] = []
        self.jsonld: list[str] = []
        self.paragraphs: list[str] = []
        self._skip_depth = 0
        self._in_title = False
        self._h1_depth = 0
        self._time_depth = 0
        self._jsonld = False
        self._collecting = False
        self._buffer: list[str] = []
        self._h1_buffer: list[str] = []
        self._time_buffer: list[str] = []
        self._jsonld_buffer: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr = {key.lower(): (value or "") for key, value in attrs}
        if tag in self.SKIP_TAGS:
            if tag == "script" and "ld+json" in attr.get("type", "").lower():
                self._jsonld = True
            else:
                self._skip_depth += 1
            return
        if self._skip_depth:
            return
        if tag == "meta":
            key = (attr.get("property") or attr.get("name") or attr.get("itemprop") or "").lower()
            content = attr.get("content", "").strip()
            if key and content and key not in self.metas:
                self.metas[key] = content
            return
        if tag == "title":
            self._in_title = True
        elif tag == "h1":
            self._h1_depth += 1
        elif tag == "time":
            self._time_depth += 1
            for key in ("datetime", "pubdate", "content"):
                if attr.get(key):
                    self.times.append(attr[key])
        elif tag in self.TEXT_TAGS:
            # Sites often omit </p> or </li>; a new text tag ends the previous one.
            self._flush_paragraph()
            self._collecting = True
        elif tag in self.BLOCK_TAGS:
            self._flush_paragraph()
        elif tag == "br" and self._collecting:
            self._buffer.append(" ")

    def handle_endtag(self, tag: str) -> None:
        if tag in self.SKIP_TAGS:
            if tag == "script" and self._jsonld:
                self.jsonld.append("".join(self._jsonld_buffer))
                self._jsonld_buffer = []
                self._jsonld = False
            elif self._skip_depth:
                self._skip_depth -= 1
            return
        if self._skip_depth:
            return
        if tag == "title":
            self._in_title = False
        elif tag == "h1" and self._h1_depth:
            self._h1_depth -= 1
            if self._h1_depth == 0:
                text = " ".join("".join(self._h1_buffer).split())
                self._h1_buffer = []
                if text:
                    self.h1s.append(text)
        elif tag == "time" and self._time_depth:
            self._time_depth -= 1
            text = "".join(self._time_buffer).strip()
            self._time_buffer = []
            if text:
                self.times.append(text)
        elif tag in self.TEXT_TAGS or tag in self.BLOCK_TAGS:
            self._flush_paragraph()

    def _flush_paragraph(self) -> None:
        text = " ".join("".join(self._buffer).split())
        self._buffer = []
        self._collecting = False
        if text:
            self.paragraphs.append(text)

    def close(self) -> None:
        super().close()
        self._flush_paragraph()

    def handle_data(self, data: str) -> None:
        if self._jsonld:
            self._jsonld_buffer.append(data)
            return
        if self._skip_depth:
            return
        if self._in_title:
            self.title += data
        if self._h1_depth:
            self._h1_buffer.append(data)
        if self._time_depth:
            self._time_buffer.append(data)
        if self._collecting:
            self._buffer.append(data)


def _walk_jsonld(node: object, headlines: list[str], dates: list[str]) -> None:
    if isinstance(node, dict):
        headline = node.get("headline")
        if isinstance(headline, str) and headline.strip():
            headlines.append(headline.strip())
        for key in ("datePublished", "dateCreated", "uploadDate"):
            value = node.get(key)
            if isinstance(value, str):
                dates.append(value)
        for value in node.values():
            _walk_jsonld(value, headlines, dates)
    elif isinstance(node, list):
        for value in node:
            _walk_jsonld(value, headlines, dates)


SITE_SUFFIX = re.compile(r"\s*(?:\|{1,2}|｜|│|::|\s[-–—]\s)\s*")


def strip_site_suffix(title: str) -> str:
    """Drop one trailing site or author suffix such as ' | 聯合新聞網'."""
    title = " ".join(title.replace("\u00a0", " ").split())
    last = None
    for match in SITE_SUFFIX.finditer(title):
        last = match
    if last is not None and last.start() > 0 and len(title[last.end():]) <= 20:
        return title[: last.start()].strip()
    return title


@dataclass
class PageEvidence:
    title_candidates: list[str] = field(default_factory=list)
    date_candidates: list[str] = field(default_factory=list)
    description: str = ""
    text: str = ""
    raw_title: str = ""

    @property
    def readable(self) -> bool:
        if not self.title_candidates:
            return False
        if CHALLENGE_TITLE.search(self.raw_title or ""):
            return False
        return len(self.text) >= MIN_READABLE_CHARS


def extract_page(html_text: str) -> PageEvidence:
    parser = _PageParser()
    parser.feed(html_text)
    parser.close()

    headlines: list[str] = []
    ld_dates: list[str] = []
    for blob in parser.jsonld:
        try:
            _walk_jsonld(json.loads(blob), headlines, ld_dates)
        except json.JSONDecodeError:
            continue

    titles: list[str] = []
    for value in (
        *(parser.metas.get(key, "") for key in META_TITLE_KEYS),
        *headlines,
        *parser.h1s,
        parser.title,
    ):
        cleaned = strip_site_suffix(value)
        if cleaned and cleaned not in titles:
            titles.append(cleaned)

    dates: list[str] = []
    raw_dates = [
        *(parser.metas.get(key, "") for key in META_DATE_KEYS),
        *ld_dates,
        *parser.times,
    ]
    for value in raw_dates:
        date = normalize_date(value)
        if date and date not in dates:
            dates.append(date)

    # Menu items and breadcrumbs are short; keep them only when nothing else exists.
    paragraphs = [item for item in parser.paragraphs if len(item) >= 12]
    text = "\n".join(paragraphs or parser.paragraphs)
    for date in find_dates(text[:1500]):
        if date not in dates:
            dates.append(date)

    description = ""
    for key in META_DESCRIPTION_KEYS:
        if parser.metas.get(key):
            description = " ".join(parser.metas[key].split())
            break

    return PageEvidence(
        title_candidates=titles,
        date_candidates=dates,
        description=description,
        text=text[:MAX_BODY_CHARS],
        raw_title=" ".join(parser.title.split()),
    )


# ---------------------------------------------------------------------------
# Slug and filename derivation


def outlet_shortcode(url: str) -> str:
    host = (urllib.parse.urlsplit(url).hostname or "").lower()
    labels = [label for label in host.split(".") if label]
    while len(labels) > 1 and labels[-1] in SUFFIX_LABELS:
        labels.pop()
    while len(labels) > 1 and labels[0] in LEADING_HOST_LABELS:
        labels.pop(0)
    code = labels[-1] if labels else "news"
    return re.sub(r"[^a-z0-9-]", "", code) or "news"


def url_id_segments(url: str) -> list[str]:
    parts = urllib.parse.urlsplit(url)
    segments: list[str] = []
    for raw in parts.path.split("/"):
        segment = urllib.parse.unquote(raw).strip()
        if not segment:
            continue
        segment = FILE_EXTENSION.sub("", segment)
        if not segment or segment.lower() in DROP_SEGMENTS:
            continue
        if not segment.isascii():
            continue
        segments.append(segment)
    for key, value in urllib.parse.parse_qsl(parts.query, keep_blank_values=False):
        if ID_QUERY_KEY.search(key) and value.isascii() and value not in segments:
            segments.append(value)
    return [re.sub(r"[^A-Za-z0-9-]", "", segment) for segment in segments if segment]


def derive_slug(url: str, *, keep_dates: bool = False) -> str:
    shortcode = outlet_shortcode(url)
    segments = [segment for segment in url_id_segments(url) if segment]
    if not keep_dates and len(segments) > 1:
        trimmed = [segment for segment in segments if not DATE_SEGMENT.match(segment)]
        if trimmed:
            segments = trimmed
    if not segments:
        segments = [dt.date.today().strftime("%Y%m%d")]
    return "-".join([shortcode, *segments])


def slug_override_is_valid(slug: str, url: str) -> bool:
    shortcode = outlet_shortcode(url)
    if not SLUG_SHAPE.match(slug) or not slug.startswith(f"{shortcode}-"):
        return False
    haystack = urllib.parse.unquote(url).lower()
    remainder = slug[len(shortcode) + 1:]
    return all(part.lower() in haystack for part in remainder.split("-") if part)


def sanitize_filename_phrase(phrase: str, fallback_title: str) -> str:
    phrase = " ".join((phrase or "").replace("/", "／").replace("\\", "").split())
    phrase = phrase.strip(" .")
    if not phrase:
        phrase = HOOK_PREFIX.sub("", fallback_title).replace("/", "／").strip()
    return phrase[:60].strip()


# ---------------------------------------------------------------------------
# Ollama client


class OllamaError(RuntimeError):
    pass


class OllamaClient:
    def __init__(
        self,
        base_url: str,
        model: str,
        *,
        think: bool | None,
        num_ctx: int,
        timeout: int,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.think = think
        self.num_ctx = num_ctx
        self.timeout = timeout

    def _request(self, path: str, payload: dict | None, timeout: int) -> dict:
        data = json.dumps(payload).encode("utf-8") if payload is not None else None
        request = urllib.request.Request(
            f"{self.base_url}{path}",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST" if data is not None else "GET",
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                body = response.read().decode("utf-8")
        except urllib.error.HTTPError as error:
            detail = error.read().decode("utf-8", "replace")[:500]
            raise OllamaError(f"{path}: HTTP {error.code}: {detail}") from error
        except (urllib.error.URLError, TimeoutError, OSError) as error:
            raise OllamaError(f"{path}: {error}") from error
        return json.loads(body) if body else {}

    def is_up(self) -> bool:
        try:
            self._request("/api/version", None, timeout=3)
            return True
        except OllamaError:
            return False

    def has_model(self) -> bool:
        tags = self._request("/api/tags", None, timeout=10)
        names = {item.get("name", "") for item in tags.get("models", [])}
        return self.model in names or f"{self.model}:latest" in names

    def chat_json(self, system: str, user: str, schema: dict) -> dict:
        payload: dict = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "stream": False,
            "format": schema,
            "keep_alive": "10m",
            "options": {
                "temperature": 0.2 if self.think is False else 0.6,
                "num_ctx": self.num_ctx,
            },
        }
        if self.think is not None:
            payload["think"] = self.think
        last_error: Exception | None = None
        for attempt in range(2):
            response = self._request("/api/chat", payload, timeout=self.timeout)
            content = response.get("message", {}).get("content", "")
            try:
                parsed = json.loads(content)
            except json.JSONDecodeError as error:
                last_error = error
                sys.stderr.write(f"model returned non-JSON output (attempt {attempt + 1})\n")
                continue
            if isinstance(parsed, dict):
                return parsed
            last_error = OllamaError("model returned a non-object JSON value")
        raise OllamaError(f"model did not return valid JSON: {last_error}")

    def unload(self) -> None:
        self._request(
            "/api/generate", {"model": self.model, "keep_alive": 0}, timeout=30
        )


def ensure_server(client: OllamaClient) -> subprocess.Popen | None:
    """Return a server process when this script had to start one."""
    if client.is_up():
        return None
    if shutil.which("ollama") is None:
        raise OllamaError("ollama is not installed and no server is reachable")
    sys.stderr.write("starting ollama serve...\n")
    process = subprocess.Popen(
        ["ollama", "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    for _ in range(30):
        time.sleep(1)
        if client.is_up():
            return process
    process.terminate()
    raise OllamaError("ollama serve did not become ready in time")


# ---------------------------------------------------------------------------
# Prompting


def response_schema(destinations: list[str]) -> dict:
    return {
        "type": "object",
        "properties": {
            "title": {"type": "string"},
            "date": {"type": "string"},
            "description": {"type": ["string", "null"]},
            "destination": {"type": "string", "enum": destinations},
            "tags": {
                "type": "array",
                "items": {"type": "string"},
                "minItems": 1,
                "maxItems": 3,
            },
            "filename_phrase": {"type": "string"},
            "slug": {"type": "string"},
            "needs_review": {"type": "boolean"},
            "review_reason": {"type": "string"},
        },
        "required": [
            "title", "date", "description", "destination", "tags",
            "filename_phrase", "slug", "needs_review", "review_reason",
        ],
    }


SYSTEM_PROMPT = """你是新聞歸檔助理，替一個 Zola 靜態網站的新聞區決定每篇文章的 metadata。只輸出符合 JSON schema 的 JSON，不要輸出其他文字。

欄位規則：
- title：文章標題，去掉尾端的網站名稱後綴，保留原文用字與標點。
- date：文章刊登日期，格式 YYYY-MM-DD。必須是頁面證據（date candidates 或內文）中出現的日期；絕對不可用今天的日期代替。無法確定時把 needs_review 設為 true 並說明。
- description：只有在內文含有標題未傳達的具體數據、確切引述、意外原因等實質細節時，才寫一句精簡描述；大多數文章應為 null。
- destination：從 schema 允許的清單中選一個。先套用編輯路由：警察或檢察官本身的不當行為（違法、貪瀆、濫權、洩密、造假、吃案）走「獨立分類/警界醜聞/警察」或「獨立分類/警界醜聞/檢察官」；主要發生在移工社群內部（行為人與受害者、客戶、交易對象多為移工）的事件走「獨立分類/移工內部社會新聞」。否則依文章的主要編輯框架選一個一般主題資料夾，不要機械地從第一個標籤推導。只有完全找不到合適資料夾時才用 "."（新聞根目錄，多為國際、科技、消費、文化類）。若兩個目的地同樣合理，把 needs_review 設為 true，並在 review_reason 列出候選與理由。
- tags：news_tags。預設 1 到 2 個，最多 3 個且每個都要獨立有檢索價值。優先使用倉庫既有詞彙。一般主題資料夾優先把資料夾同名標籤放前面，但不要為了對應路徑硬加不準確的標籤。編輯分類使用「警察」「檢察官」「移工」等主題標籤，不要發明「警界醜聞」或「移工內部社會新聞」標籤，也不要使用「檢警法」這個總稱標籤。
- filename_phrase：檔名短語。只保留最具體說明「誰做了什麼」的單一子句，不是完整標題。去掉「獨／」「快訊／」「影／」等前綴、無實質內容的感嘆詞、以及尾端的反應或後續子句（除非後續事件才是新聞主體）。使用全形標點，不可含 ASCII 斜線或多餘空白。範例：
  - 獨／誇張！不肖廠商鑽漏洞　庫錢包裝拆開竟是「牛皮紙」 → 庫錢包裝拆開竟是「牛皮紙」
  - 砰一聲巨響炸出火光！高雄鋼鐵廠爆炸　松鼠誤觸6萬9千伏電壓 → 松鼠誤觸6萬9千伏電壓
  - 南韓反跟蹤App今起上線 受害人可即時查看跟蹤者位置 → 南韓反跟蹤App今起上線
  - 單筆3萬5千！幫地下錢莊偷查民眾個資　北市派出所警員被起訴 → 幫地下錢莊偷查民眾個資
- slug：預設照抄提供的 slug candidate。只有當該媒體既有 slug 範例明顯採用不同慣例時才改寫；改寫後的每個片段都必須出自原始 URL，不可自創。
- needs_review / review_reason：只有在日期無法確定或目的地無法二選一時才設 true；其他情況設 false 並讓 review_reason 為空字串。

以下是分類規範全文：

"""


def build_system_prompt() -> str:
    return SYSTEM_PROMPT + TAXONOMY_MD.read_text(encoding="utf-8")


def build_user_prompt(
    context_report: str,
    url: str,
    archived_url: str,
    evidence: PageEvidence,
    slug_candidate: str,
    slug_examples: list[str],
) -> str:
    lines = [
        f"今天日期（僅供參考，不可當作文章日期）：{dt.date.today().isoformat()}",
        "",
        "[repository context]",
        context_report.strip(),
        "",
        "[article]",
        f"url: {url}",
        f"archived_url: {archived_url}",
        f"slug candidate: {slug_candidate}",
        f"existing slug examples for this outlet: {', '.join(slug_examples) or '(none)'}",
        f"title candidates: {json.dumps(evidence.title_candidates, ensure_ascii=False)}",
        f"date candidates: {json.dumps(evidence.date_candidates, ensure_ascii=False)}",
        f"meta description: {evidence.description or '(none)'}",
        "body (truncated):",
        evidence.text,
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Workflow


@dataclass
class Item:
    url: str
    archived_url: str = ""
    bucket: str = ""
    detail: str = ""


@dataclass
class Buckets:
    created: list[Item] = field(default_factory=list)
    already_archived: list[Item] = field(default_factory=list)
    archive_failed: list[Item] = field(default_factory=list)
    content_unreadable: list[Item] = field(default_factory=list)
    classification_needed: list[Item] = field(default_factory=list)
    write_failed: list[Item] = field(default_factory=list)

    def add(self, item: Item, bucket: str, detail: str = "") -> None:
        item.bucket = bucket
        item.detail = detail
        getattr(self, bucket.replace("-", "_")).append(item)


def parse_archive_output(output: str) -> list[Item]:
    items: list[Item] = []
    for line in output.splitlines():
        parts = line.split()
        if not parts:
            continue
        status = parts[0]
        if status == "OK" and len(parts) >= 3:
            items.append(Item(url=parts[1], archived_url=parts[2], bucket="ok"))
        elif status == "DUP" and len(parts) >= 3:
            items.append(Item(url=parts[1], bucket="already-archived", detail=" ".join(parts[2:])))
        elif status == "FAIL" and len(parts) >= 2:
            items.append(Item(url=parts[1], bucket="archive-failed"))
    return items


def slug_examples_from_report(report: str, shortcode: str) -> list[str]:
    in_section = False
    for line in report.splitlines():
        if line.startswith("["):
            in_section = line.strip() == "[slug_prefixes]"
            continue
        if in_section and line.startswith(f"{shortcode}\t"):
            return line.split("\t")[2].split(",")
    return []


class ArticleFetcher:
    def __init__(self, *, allow_flaresolverr: bool) -> None:
        self.allow_flaresolverr = allow_flaresolverr and shutil.which("docker") is not None
        self.flaresolverr_used = False

    def fetch(self, url: str, archived_url: str) -> tuple[PageEvidence | None, str]:
        attempts: list[tuple[str, callable]] = [
            ("original", lambda: decode_html(curl(url))),
            ("archived", lambda: run_script("fetch-archived.sh", archived_url, timeout=60)),
        ]
        if self.allow_flaresolverr:
            attempts.append(("flaresolverr", lambda: self._flaresolverr(url)))
        for source, loader in attempts:
            try:
                html_text = loader()
            except (RuntimeError, subprocess.TimeoutExpired) as error:
                sys.stderr.write(f"  {source}: fetch failed: {error}\n")
                continue
            evidence = extract_page(html_text)
            if evidence.readable:
                return evidence, source
            sys.stderr.write(f"  {source}: no readable article content\n")
        return None, ""

    def _flaresolverr(self, url: str) -> str:
        self.flaresolverr_used = True
        return run_script("flaresolverr.sh", "fetch", url, timeout=150)

    def cleanup(self) -> None:
        if self.flaresolverr_used:
            subprocess.run([str(SCRIPT_DIR / "flaresolverr.sh"), "stop"], check=False)


def validate_answer(
    answer: dict,
    *,
    evidence: PageEvidence,
    url: str,
    slug_candidate: str,
    policy_sections: dict,
) -> tuple[dict | None, str, str]:
    """Return (fields, bucket, detail). bucket is '' when the answer is usable."""
    title = strip_site_suffix(str(answer.get("title") or ""))
    if not title:
        return None, "content-unreadable", "model produced no title"

    date = normalize_date(str(answer.get("date") or ""))
    if not date:
        return None, "content-unreadable", f"model produced no valid date: {answer.get('date')!r}"
    evidence_dates = set(evidence.date_candidates) | set(find_dates(evidence.text))
    if date not in evidence_dates and date == dt.date.today().isoformat():
        return None, "content-unreadable", "model substituted today's date"
    if date not in evidence_dates:
        sys.stderr.write(f"  warning: date {date} not found in page evidence {sorted(evidence_dates)}\n")

    if answer.get("needs_review"):
        return None, "classification-needed", str(answer.get("review_reason") or "model asked for review")

    destination = str(answer.get("destination") or ROOT_DESTINATION)
    section = policy_sections.get(destination)
    if destination != ROOT_DESTINATION and section is None:
        return None, "classification-needed", f"unknown destination {destination!r}"

    tags: list[str] = []
    for tag in answer.get("tags") or []:
        tag = " ".join(str(tag).split())
        if tag and tag not in tags:
            tags.append(tag)
    tags = tags[:3]
    required = tuple(section.require_any_tags) if section is not None else ()
    if required and not set(tags) & set(required):
        if len(required) == 1:
            tags = [required[0], *tags][:3]
        else:
            return None, "classification-needed", (
                f"destination {destination} requires one of "
                f"{list(required)} but tags were {tags}"
            )
    if not tags:
        return None, "classification-needed", "model produced no tags"

    slug = str(answer.get("slug") or "").strip()
    if slug != slug_candidate and not slug_override_is_valid(slug, url):
        if slug:
            sys.stderr.write(f"  ignoring invalid slug override {slug!r}\n")
        slug = slug_candidate

    description = answer.get("description")
    description = " ".join(str(description).split()) if description else ""
    if description and (description == title or len(description) < 8):
        description = ""

    phrase = sanitize_filename_phrase(str(answer.get("filename_phrase") or ""), title)
    fields = {
        "title": title,
        "date": date,
        "description": description,
        "destination": destination,
        "tags": tags,
        "slug": slug,
        "filename": f"{date}_{phrase}.md",
    }
    return fields, "", ""


def write_entry(fields: dict, archived_url: str, output: Path, *, dry_run: bool) -> None:
    args = [
        "--title", fields["title"],
        "--slug", fields["slug"],
        "--date", fields["date"],
        "--link-to", archived_url,
        "--tags", ",".join(fields["tags"]),
    ]
    if fields["description"]:
        args += ["--description", fields["description"]]
    if dry_run:
        sys.stderr.write(f"  dry-run: would write {output}\n")
        return
    run_script("write-news.sh", *args, str(output))


def update_queue(remove: set[str], *, dry_run: bool) -> None:
    if not QUEUE_FILE.exists() or not remove:
        return
    lines = QUEUE_FILE.read_text(encoding="utf-8").splitlines()
    kept = [line for line in lines if line not in remove]
    if dry_run:
        sys.stderr.write(f"  dry-run: would drop {len(lines) - len(kept)} queue line(s)\n")
        return
    QUEUE_FILE.write_text("".join(f"{line}\n" for line in kept), encoding="utf-8")


def print_report(buckets: Buckets) -> None:
    def section(name: str, items: list[Item], render) -> None:
        if not items:
            return
        print(f"\n== {name} ({len(items)}) ==")
        for item in items:
            print(render(item))

    section("created", buckets.created, lambda i: f"  {i.url}\n    -> {i.detail}")
    section("already-archived", buckets.already_archived, lambda i: f"  {i.url}\n    -> {i.detail}")
    section("archive-failed", buckets.archive_failed, lambda i: f"  {i.url}")
    section(
        "content-unreadable",
        buckets.content_unreadable,
        lambda i: f"  {i.url}\n    archived: {i.archived_url}\n    reason: {i.detail}",
    )
    section(
        "classification-needed",
        buckets.classification_needed,
        lambda i: f"  {i.url}\n    archived: {i.archived_url}\n    reason: {i.detail}",
    )
    section("write-failed", buckets.write_failed, lambda i: f"  {i.url}\n    reason: {i.detail}")

    if buckets.content_unreadable:
        print(
            "\n請為 content-unreadable 的每個 URL 提供可靠的標題與刊登日期"
            "（可另附 description 或 tags），這些 URL 仍留在佇列中。"
        )
    if buckets.classification_needed:
        print(
            "\n請為 classification-needed 的每個 URL 指定目的地資料夾（或補充日期），"
            "這些 URL 仍留在佇列中。"
        )
    if buckets.created:
        print("\n已建立的檔案尚未 commit，請先檢視內容再提交。")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Add news entries with a local Ollama model.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Environment: ADD_NEWS_MODEL (default model), ADD_NEWS_OLLAMA_URL "
            "(default server URL)."
        ),
    )
    parser.add_argument("urls", nargs="*", help="news URLs to add (queue is also processed)")
    parser.add_argument("--model", default=DEFAULT_MODEL, help=f"Ollama model (default: {DEFAULT_MODEL})")
    parser.add_argument("--ollama-url", default=DEFAULT_OLLAMA_URL, help=f"Ollama server (default: {DEFAULT_OLLAMA_URL})")
    parser.add_argument("--num-ctx", type=int, default=32768, help="context window for the model (default: 32768)")
    parser.add_argument("--timeout", type=int, default=900, help="seconds to wait for one model answer (default: 900)")
    parser.add_argument("--no-think", action="store_true", help="disable the model's thinking mode for faster answers")
    parser.add_argument("--keep-model", action="store_true", help="leave the model loaded after finishing")
    parser.add_argument("--no-flaresolverr", action="store_true", help="never fall back to the FlareSolverr container")
    parser.add_argument("--dry-run", action="store_true", help="classify but do not write files or edit the queue")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    client = OllamaClient(
        args.ollama_url,
        args.model,
        think=False if args.no_think else None,
        num_ctx=args.num_ctx,
        timeout=args.timeout,
    )
    if not client.is_up() and shutil.which("ollama") is None:
        print("Ollama is not reachable and the ollama CLI is not installed.", file=sys.stderr)
        return 2

    policy = load_policy(POLICY_TOML)
    sections = {
        section.path.as_posix(): section
        for section in policy.sections
        if section.allow_articles
    }
    destinations = [*sections.keys(), ROOT_DESTINATION]
    schema = response_schema(destinations)

    print("archiving queue...", file=sys.stderr)
    items = parse_archive_output(run_script("archive-urls.sh", *args.urls, timeout=3600))
    if not items:
        print("No URLs to process. Pass at least one URL.", file=sys.stderr)
        return 1

    buckets = Buckets()
    pending = [item for item in items if item.bucket == "ok"]
    for item in items:
        if item.bucket == "already-archived":
            buckets.add(item, "already-archived", item.detail)
        elif item.bucket == "archive-failed":
            buckets.add(item, "archive-failed")

    server_process: subprocess.Popen | None = None
    fetcher = ArticleFetcher(allow_flaresolverr=not args.no_flaresolverr)
    model_used = False
    try:
        if pending:
            context_report = run_script("news-context.sh")
            existing_slugs = {article.slug for article in read_articles(NEWS_DIR)[0]}
            batch_slugs: set[str] = set()
            system_prompt = build_system_prompt()

        for item in pending:
            print(f"\n[{item.url}]", file=sys.stderr)
            evidence, source = fetcher.fetch(item.url, item.archived_url)
            if evidence is None:
                buckets.add(item, "content-unreadable", "no source yielded article content")
                continue
            print(f"  read from {source}; asking {args.model}...", file=sys.stderr)

            if server_process is None and not model_used:
                server_process = ensure_server(client)
                if not client.has_model():
                    raise OllamaError(f"model {args.model!r} is not installed; run: ollama pull {args.model}")
                model_used = True

            shortcode = outlet_shortcode(item.url)
            slug_candidate = derive_slug(item.url)
            user_prompt = build_user_prompt(
                context_report,
                item.url,
                item.archived_url,
                evidence,
                slug_candidate,
                slug_examples_from_report(context_report, shortcode),
            )
            try:
                answer = client.chat_json(system_prompt, user_prompt, schema)
            except OllamaError as error:
                buckets.add(item, "classification-needed", f"model call failed: {error}")
                continue

            fields, bucket, detail = validate_answer(
                answer,
                evidence=evidence,
                url=item.url,
                slug_candidate=slug_candidate,
                policy_sections=sections,
            )
            if fields is None:
                buckets.add(item, bucket, detail)
                continue

            taken = existing_slugs | batch_slugs
            if fields["slug"] in taken:
                alternative = derive_slug(item.url, keep_dates=True)
                if alternative not in taken and alternative != fields["slug"]:
                    fields["slug"] = alternative
                else:
                    buckets.add(item, "write-failed", f"slug {fields['slug']} already exists")
                    continue

            relative_dir = PurePosixPath(fields["destination"])
            output = NEWS_DIR / relative_dir / fields["filename"]
            if output.exists():
                buckets.add(item, "write-failed", f"file already exists: {output.relative_to(REPO_ROOT)}")
                continue

            try:
                write_entry(fields, item.archived_url, output, dry_run=args.dry_run)
            except RuntimeError as error:
                buckets.add(item, "write-failed", str(error))
                continue
            batch_slugs.add(fields["slug"])
            summary = (
                f"{output.relative_to(REPO_ROOT)}\n       slug={fields['slug']} "
                f"tags={','.join(fields['tags'])}"
            )
            if fields["description"]:
                summary += f"\n       description={fields['description']}"
            buckets.add(item, "created", summary)
    finally:
        fetcher.cleanup()
        if model_used and not args.keep_model:
            try:
                client.unload()
                print(f"\nunloaded {args.model}", file=sys.stderr)
            except OllamaError as error:
                print(f"\ncould not unload model: {error}", file=sys.stderr)
        if server_process is not None:
            server_process.terminate()
            try:
                server_process.wait(timeout=15)
            except subprocess.TimeoutExpired:
                server_process.kill()
            print("stopped ollama serve", file=sys.stderr)

    update_queue(
        {item.url for item in (*buckets.created, *buckets.already_archived)},
        dry_run=args.dry_run,
    )
    print_report(buckets)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
