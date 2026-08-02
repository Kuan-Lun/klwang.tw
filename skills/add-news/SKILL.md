---
name: add-news
description: Archive one or more news URLs and create matching source-code/content/news Markdown entries. Use when the user asks to add, archive, queue, or import news articles into this repository; do not commit the created files.
---

# Add news

Process every URL independently and finish the whole batch even when individual URLs fail. Use the URLs in the user's request plus any URLs already present in `source-code/content/news/toadd-news.txt`. Treat that queue as the source of truth for the batch.

Work from the repository root. Resolve it with `git rev-parse --show-toplevel` when the current directory may be a subdirectory.

## 1. Archive the batch

Pass every newly supplied URL as its own quoted argument:

```bash
scripts/archive-urls.sh "https://example.com/article-one" "https://example.com/article-two"
```

The script adds new URLs to the queue, checks existing `link_to` fields for duplicates, and archives non-duplicates with one retry. Interpret each output line as follows:

- `OK <url> <archived-url>`: keep the archived URL verbatim for `extra.link_to` and the content fallback.
- `DUP <url> <existing-file>`: put the URL in **already-archived** and skip the remaining steps.
- `FAIL <url>`: put the URL in **archive-failed** and skip the remaining steps.

If the script prints nothing, ask the user for at least one URL and stop. A failure for one URL must not stop another URL.

Run `scripts/news-context.sh` once for the whole batch. Fetching the original articles and gathering this repository context are independent, so parallelize them when the available tools allow it.

## 2. Read each source article

Use the available web-reading or browsing capability on the original URL first. Extract:

- `title`: the article headline.
- `date`: the article's stated publication date in `YYYY-MM-DD`, never today's date as a substitute.
- `description`: one concise sentence only when the body contains a specific statistic, exact quote, surprising cause, or other material detail that the title does not convey. Omit it for most articles.

Reject challenge pages, consent shells, login pages, and other responses that do not contain the article. If the original is unreadable, fetch the archived snapshot from step 1:

```bash
scripts/fetch-archived.sh "<archived-url>"
```

Parse the returned HTML directly. Prefer `<h1>`, `<title>`, or `og:title` for the title and `article:published_time` or a visible publication date for the date. Strip a trailing site-name suffix from the title.

Only when both the original and archived snapshot lack real content, use the original URL through FlareSolverr:

```bash
scripts/flaresolverr.sh fetch "<original-url>"
```

Stop the ephemeral container after all fallback fetches, including after failures:

```bash
scripts/flaresolverr.sh stop
```

If no source yields a reliable title and date, do not guess. Put the URL and its archived URL in **content-unreadable**, skip file creation, and continue.

## 3. Derive a unique slug

Use the existing slugs printed by `scripts/news-context.sh` to preserve each outlet's established shorthand. Keep a list of slugs selected earlier in the current batch because those are not yet on disk.

Known shorthands include `udn`, `tvbs`, `setn`, `ettoday`, `chinatimes`, `ltn`, `ftvnews`, `pts`, `mydrivers`, and `ctee`. For a new outlet, strip prefixes such as `www.`, `news.`, or `m.` and the TLD, then use a short lowercase domain code.

Build `<shortcode>-<ids>` from the identifying path or query values in URL order:

- Drop section words such as `news`, `story`, `article`, `local`, `detail`, `life`, `society`, `realtimenews`, `breakingnews`, `amp`, and file extensions.
- Keep every segment that contributes to the article ID. For example, `udn.com/news/story/7320/9587400` becomes `udn-7320-9587400`.
- Use an identifying query value such as `news_id=3190751`, but ignore tracking-only queries.

Examples in this repository include `ftvnews-2026502S07M1`, `tvbs-3230434`, `pts-814538`, `mydrivers-1-1135-1135015`, and `chinatimes-20260708003489-260402`.

## 4. Choose tags and destination

Use `news_tags`, never the site-wide `tags` taxonomy. Judge the primary topic mainly from the title and use the body only to confirm it.

The category section from `scripts/news-context.sh` maps each tag-backed category name to its relative path. When the primary tag exactly matches a listed category, put that tag first and write the file under that mapped path, including nested paths. Otherwise, write it directly under `source-code/content/news/` and follow the style of existing root-level tags.

Use one or two tags. Do not create a folder during this workflow; use the `review-news-taxonomy` skill later to identify promotion candidates.

## 5. Choose the filename

Use `YYYY-MM-DD_<short phrase>.md`, with the same date as the frontmatter. Make the phrase the single clause that most concretely says who did what, not the full headline.

Drop hook prefixes such as `獨／`, `快訊／`, or `影／`, non-substantive exclamations, and trailing reaction or follow-up clauses unless the follow-up is the more newsworthy event. Calibrate against these examples:

- `獨／誇張！不肖廠商鑽漏洞　庫錢包裝拆開竟是「牛皮紙」` → `庫錢包裝拆開竟是「牛皮紙」`
- `砰一聲巨響炸出火光！高雄鋼鐵廠爆炸　松鼠誤觸6萬9千伏電壓` → `松鼠誤觸6萬9千伏電壓`
- `南韓反跟蹤App今起上線 受害人可即時查看跟蹤者位置` → `南韓反跟蹤App今起上線`
- `單筆3萬5千！幫地下錢莊偷查民眾個資　北市派出所警員被起訴` → `幫地下錢莊偷查民眾個資`

Use full-width punctuation in filenames. Never include an ASCII `/` or trailing whitespace.

## 6. Write without overwriting

Use the deterministic writer so field order and TOML escaping remain consistent:

```bash
scripts/write-news.sh \
    --title "..." \
    --description "..." \
    --slug "..." \
    --date "YYYY-MM-DD" \
    --link-to "https://web.archive.org/web/..." \
    --tags "tag1,tag2" \
    "source-code/content/news/<relative-category>/<filename>.md"
```

Omit `--description` when no description is warranted. The writer intentionally leaves the body empty and refuses to overwrite an existing file.

If a collision occurs, add a real distinguishing ID segment to the slug or make the filename phrase more specific, then retry. If no evidence-based distinction is clear, put the URL in **write-failed** instead of forcing an overwrite.

## Final report and queue update

Place every URL in exactly one bucket:

- **created**
- **already-archived**
- **archive-failed**
- **content-unreadable**
- **write-failed**

After the whole batch:

1. Remove exact queue lines only for **created** and **already-archived** URLs. Preserve order and keep **archive-failed**, **content-unreadable**, and **write-failed** URLs for retry.
2. Report only non-empty buckets. List created file paths, duplicate matches, failed URLs, archived links for unreadable content, and collision details for failed writes.
3. Ask one batched question for all **content-unreadable** items, requesting reliable title and date plus any optional description or tags.
4. Do not commit or push. Tell the user to review the created files first.
