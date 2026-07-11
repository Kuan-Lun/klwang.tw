---
description: Archive a news article URL and create the corresponding source-code/content/news markdown file following this repo's conventions.
argument-hint: [url]
---

Add one news article to `source-code/content/news/` from a source URL.

URL to process: $1

If no URL was given, ask the user for one and stop.

## 1. Archive it

Run:

```bash
scripts/archive-url.sh "$1"
```

If it fails, run it again once more (transient Save Page Now failures are common). If it **still** fails after that retry, stop here — do not create any file. Report back to the user that archiving failed, so they can retry later or supply a snapshot manually.

On success, the script prints a `web.archive.org/web/...` URL — use it verbatim as `extra.link_to`, and keep it around, it's also your primary source for step 2.

## 2. Read the source article

Try WebFetch on the *original* URL ($1) first, to extract:

- Headline (`title`)
- Publish date in `YYYY-MM-DD` (`date`) — use the article's stated publish date, not today's date
- Skim the body for anything genuinely noteworthy that a reader wouldn't get from the title alone (a specific statistic, an official's exact quote, a surprising cause). Only if such a detail exists, draft one sentence for `description`. Most articles in this repo have no `description` — don't force one.

Many outlets (this repo has already hit `ftvnews.com.tw`) sit behind a Cloudflare bot-challenge and WebFetch will come back with a 403 or a "Just a moment..." shell instead of the article. When that happens, **don't reach for FlareSolverr yet** — read the archive.org snapshot from step 1 instead, which is a plain static page and almost always bypasses the challenge that blocked the live site:

```bash
curl -sS -m 30 -A "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36" "<the link_to URL from step 1>"
```

Note: WebFetch itself refuses `web.archive.org` URLs outright, so this has to be a plain `curl`, not WebFetch. Parse the result yourself (there's no AI-summarization step doing it for you here):

- Title: the `<title>`/`<h1>` text, or `og:title` meta (strip any trailing `- 站名` suffix)
- Date: `article:published_time` meta, or visible text like `發佈時間：YYYY/MM/DD`
- A noteworthy detail for `description`, same bar as above

Only if the archived snapshot *also* has no real content (rare — e.g. archive.org itself failed to capture a working page) fall back to FlareSolverr, a local headless-browser proxy, against the **original** URL:

```bash
scripts/flaresolverr.sh fetch "$1"
```

This starts the FlareSolverr container on demand (first call may take ~10-30s to boot) and prints the rendered HTML to stdout. Once you're done fetching (whether or not FlareSolverr was needed), run:

```bash
scripts/flaresolverr.sh stop
```

to remove the container again — it's meant to be ephemeral, not left running between commands.

If FlareSolverr *also* fails to get real content, say so and ask the user to paste the title/date instead of guessing.

## 3. Derive the slug

Check existing slugs for the same domain first, to reuse the established shorthand for that outlet:

```bash
grep -rh '^slug' source-code/content/news --include="*.md"
```

(Existing tags can be surveyed the same way with `grep -rh '^news_tags' source-code/content/news --include="*.md"`.)

Known shorthands already in use: `udn`, `tvbs`, `setn`, `ettoday`, `chinatimes`, `ltn`, `ftvnews`, `pts`, `mydrivers`, `ctee`. If the outlet hasn't appeared before, derive a short lowercase code from the domain (strip `www.`/`news.`/`m.` and the TLD, e.g. `apnews.com` → `apnews`).

Build the rest of the slug as `<shortcode>-<ids>`, where `<ids>` are the numeric/alphanumeric identifier segments from the URL's path or query string, joined by `-`, in order:

- Drop plain-word path segments that just describe a site section (`news`, `story`, `article`, `local`, `detail`, `life`, `society`, `realtimenews`, `breakingnews`, `amp`, file extensions like `.htm`).
- Keep every segment that carries part of the article's actual ID, even if there are several (e.g. `udn.com/news/story/7320/9587400` → `udn-7320-9587400`, both `7320` and `9587400` are kept).
- If the ID lives in a query parameter (`?news_id=3190751`), use its value, not the param name.
- Drop tracking/non-identifying query strings (`?chdtv`).

Examples already in the repo: `ftvnews-2026502S07M1`, `tvbs-3230434`, `udn-7317-9567625`, `pts-814538`, `ltn-5482073`, `mydrivers-1-1135-1135015`, `ettoday-3190751`, `chinatimes-20260708003489-260402`.

## 4. Pick tags and a home folder

Current category folders:

```bash
ls source-code/content/news
```

This always reflects the live set — folders get added over time, so don't rely on any list written down here or elsewhere; re-run it fresh each time.

Judge the single most fitting topical tag primarily from the **title** (skim the body only to double-check, per this repo's convention). If that tag matches one of the existing folder names exactly, put it first in `news_tags` and place the file inside `source-code/content/news/<folder>/`. If it doesn't match any folder, put the file directly in `source-code/content/news/` and pick whatever tag(s) best describe it — look at tags already used at the top level for style (e.g. `["抽獎"]`, `["廣告"]`, `["韓國", "國際"]`). Don't invent a new folder yourself; that's a judgment call for `/review-news-taxonomy`.

A second tag is fine when the article clearly has more than one angle (e.g. `["移工", "失聯移工"]`), but keep it to 1-2 tags total, matching existing style.

Note: news articles use their own `news_tags` taxonomy, kept separate from the site-wide `tags` taxonomy used by `posts`/`adapted` content — don't use the `tags` field here.

## 5. Filename

Format: `YYYY-MM-DD_<short phrase>.md`, date matching the `date` field.

The short phrase is **not** the full title — it's the single clause that most concretely names what happened (who did what), dropping:

- Pure hook/label prefixes: `獨／`, `快訊／`, `影／`, exclamation lead-ins that don't name the subject (`砰一聲巨響炸出火光！`, `成功嶺又出事！`)
- Trailing reaction/quote/follow-up clauses (a bystander's quote, a "later" consequence) — *unless* that clause is actually the more newsworthy part

Calibration examples from this repo (title → filename phrase):

- "獨／誇張！不肖廠商鑽漏洞　庫錢包裝拆開竟是「牛皮紙」" → `庫錢包裝拆開竟是「牛皮紙」`
- "砰一聲巨響炸出火光！高雄鋼鐵廠爆炸　松鼠誤觸6萬9千伏電壓" → `松鼠誤觸6萬9千伏電壓`
- "快訊／「十大槍擊要犯」判無期獲假釋！他又拿長、短槍犯案…再度遭收押" → `他又拿長、短槍犯案…再度遭收押`
- "南韓反跟蹤App今起上線 受害人可即時查看跟蹤者位置" → `南韓反跟蹤App今起上線`
- "單筆3萬5千！幫地下錢莊偷查民眾個資　北市派出所警員被起訴" → `幫地下錢莊偷查民眾個資`

Use full-width punctuation only (`／`, `「」`, `？`, `！`); never put an ASCII `/` or a trailing space in the filename.

## 6. Write the file

Match the exact TOML shape used throughout the repo — check 1-2 existing files in the destination folder to mirror field order exactly:

```toml
+++
title = "..."
description = "..."   # only if you decided to add one in step 2
slug = "..."
date = "YYYY-MM-DD"

[extra]
link_to = "https://web.archive.org/web/..."

[taxonomies]
news_tags = ["..."]
+++
```

Leave the body empty — this repo doesn't reproduce article text, the frontmatter is the whole file.

Finally, show the user the file you created and its path so they can review before committing. Don't commit it yourself.
