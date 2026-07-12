---
description: Archive one or more news article URLs and create the corresponding source-code/content/news markdown files following this repo's conventions.
argument-hint: [url...]
---

Add one or more news articles to `source-code/content/news/` from source URLs.

URLs to process: $ARGUMENTS (space- or newline-separated; one URL works the same way as many)

If no URL was given, ask the user for at least one and stop.

Process every URL through steps 1-6 independently. **One URL's failure must never stop the batch** — when a URL can't proceed past a given step, drop it into the matching bucket described in "Failure handling" below and move on to the next URL. Only ask the user something mid-run if it's a genuine batch-wide blocker (e.g. no URLs given at all); everything else waits for the "Final report" at the end.

**Parallelize where possible:** step 1 (archive, batched), the initial WebFetch in step 2 for each URL, and the repo lookups in steps 3-4 (`scripts/news-context.sh`, run once for the whole batch) don't depend on each other — fire them off together instead of one at a time. The only thing that must wait on step 1 is step 2's *fallback* path (`scripts/fetch-archived.sh`) for a given URL, which needs that URL's archived link.

## 1. Archive everything

Archive every URL in one call:

```bash
scripts/archive-urls.sh $ARGUMENTS
```

This retries each URL once on failure and prints one line per URL:

- `OK <url> <archived-url>` — use `<archived-url>` verbatim as that article's `extra.link_to`, and keep it around, it's also the primary source for step 2.
- `FAIL <url>` — Save Page Now failed twice for this URL. Drop it into the **archive-failed** bucket immediately and skip steps 2-6 for it entirely — there's no `link_to` to give it, so no file can be created.

## 2. Read the source article

Try WebFetch on the *original* URL (the one being processed, not the archived one) first, to extract:

- Headline (`title`)
- Publish date in `YYYY-MM-DD` (`date`) — use the article's stated publish date, not today's date
- Skim the body for anything genuinely noteworthy that a reader wouldn't get from the title alone (a specific statistic, an official's exact quote, a surprising cause). Only if such a detail exists, draft one sentence for `description`. Most articles in this repo have no `description` — don't force one.

Many outlets (this repo has already hit `ftvnews.com.tw`) sit behind a Cloudflare bot-challenge and WebFetch will come back with a 403 or a "Just a moment..." shell instead of the article. When that happens, **don't reach for FlareSolverr yet** — read the archive.org snapshot from step 1 instead, which is a plain static page and almost always bypasses the challenge that blocked the live site:

```bash
scripts/fetch-archived.sh "<the link_to URL from step 1>"
```

Note: WebFetch itself refuses `web.archive.org` URLs outright, so this has to be a plain `curl` under the hood, not WebFetch. Parse the result yourself (there's no AI-summarization step doing it for you here):

- Title: the `<title>`/`<h1>` text, or `og:title` meta (strip any trailing `- 站名` suffix)
- Date: `article:published_time` meta, or visible text like `發佈時間：YYYY/MM/DD`
- A noteworthy detail for `description`, same bar as above

Only if the archived snapshot *also* has no real content (rare — e.g. archive.org itself failed to capture a working page) fall back to FlareSolverr, a local headless-browser proxy, against the **original** URL:

```bash
scripts/flaresolverr.sh fetch "<the original URL being processed>"
```

This starts the FlareSolverr container on demand (first call may take ~10-30s to boot) and prints the rendered HTML to stdout. Once you're done fetching (whether or not FlareSolverr was needed), run:

```bash
scripts/flaresolverr.sh stop
```

to remove the container again — it's meant to be ephemeral, not left running between commands.

If FlareSolverr *also* fails to get real content, this URL goes into the **content-unreadable** bucket: it already has a `link_to` from step 1, but nothing could be read to fill in `title`/`date`. Don't guess — don't ask the user right now either, since that would block the rest of the batch. Note the URL and its `link_to`, skip steps 3-6 for it, and move on; these get asked about together in the "Final report" at the end.

## 3. Derive the slug

Check existing slugs for the same domain first, to reuse the established shorthand for that outlet — `scripts/news-context.sh` prints these along with the existing tags and category folders (see step 4) in one call. Run it **once for the whole batch**, not per URL — but keep a running mental list of slugs/filenames you've already assigned earlier in *this* run (including for other URLs in the same batch) and treat those as taken too, since the script only sees what's already on disk:

```bash
scripts/news-context.sh
```

Known shorthands already in use: `udn`, `tvbs`, `setn`, `ettoday`, `chinatimes`, `ltn`, `ftvnews`, `pts`, `mydrivers`, `ctee`. If the outlet hasn't appeared before, derive a short lowercase code from the domain (strip `www.`/`news.`/`m.` and the TLD, e.g. `apnews.com` → `apnews`).

Build the rest of the slug as `<shortcode>-<ids>`, where `<ids>` are the numeric/alphanumeric identifier segments from the URL's path or query string, joined by `-`, in order:

- Drop plain-word path segments that just describe a site section (`news`, `story`, `article`, `local`, `detail`, `life`, `society`, `realtimenews`, `breakingnews`, `amp`, file extensions like `.htm`).
- Keep every segment that carries part of the article's actual ID, even if there are several (e.g. `udn.com/news/story/7320/9587400` → `udn-7320-9587400`, both `7320` and `9587400` are kept).
- If the ID lives in a query parameter (`?news_id=3190751`), use its value, not the param name.
- Drop tracking/non-identifying query strings (`?chdtv`).

Examples already in the repo: `ftvnews-2026502S07M1`, `tvbs-3230434`, `udn-7317-9567625`, `pts-814538`, `ltn-5482073`, `mydrivers-1-1135-1135015`, `ettoday-3190751`, `chinatimes-20260708003489-260402`.

## 4. Pick tags and a home folder

Current category folders are the third section printed by `scripts/news-context.sh` (see step 3) — this always reflects the live set, so don't rely on any list written down here or elsewhere; re-run it fresh each time.

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

Use `scripts/write-news.sh` — it produces the exact TOML shape used throughout the repo (field order, quoting/escaping) so you don't have to hand-format it:

```bash
scripts/write-news.sh \
    --title "..." \
    --description "..." \
    --slug "..." \
    --date "YYYY-MM-DD" \
    --link-to "https://web.archive.org/web/..." \
    --tags "tag1,tag2" \
    "source-code/content/news/<folder-or-nothing>/<filename>.md"
```

Omit `--description` if you decided not to add one in step 2. The script leaves the body empty — this repo doesn't reproduce article text, the frontmatter is the whole file.

The script also refuses to overwrite an existing file — if that happens here, it means the slug/filename you derived in steps 3/5 collides with something already on disk (possibly another URL from *this same batch*, see step 3's note). Don't force an overwrite: pick a distinguishing tweak (an extra ID segment for the slug, a more specific filename phrase) and retry the write. If it's not obviously resolvable, drop this URL into the **write-failed** bucket instead of guessing further.

## Failure handling

Every URL ends up in exactly one bucket:

- **created** — file written successfully.
- **archive-failed** (step 1) — Save Page Now failed twice; no `link_to` exists, so nothing else was attempted.
- **content-unreadable** (step 2) — archived fine, but no source (original, archive.org snapshot, FlareSolverr) yielded readable content for `title`/`date`.
- **write-failed** (step 6) — a slug/filename collision that couldn't be resolved automatically.

None of these should ever raise an error that stops the batch — they're just categories for the final report.

## Final report

After every URL has been processed, report a summary back to the user, grouped by bucket:

- **Created** — list each file's path, so the user can review before committing (don't commit it yourself).
- **Archive failed** — list the URLs; suggest retrying later or supplying a manual snapshot.
- **Content unreadable** — list the URLs *with* their captured `link_to` (it's already archived, so it isn't wasted work). Ask the user, in one batched question, to supply title/date (and description/tags if they want) for these; once given, write them with `scripts/write-news.sh` same as any other article.
- **Write failed** — list the URLs and what collided, so the user can decide how to disambiguate.

Omit any bucket that's empty rather than listing it as "none".
