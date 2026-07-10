---
description: Audit source-code/content/news for tag/folder consistency and flag topics that have accumulated enough root-level articles to deserve their own folder. Read-only — reports findings, never moves files itself.
---

Audit the news archive's taxonomy. This is a **read-only report** — do not move, rename, or edit any files. Present findings and wait for the user's go-ahead.

## 1. Gather the data

Enumerate every article file (skip `_index.md`) under `source-code/content/news/`, recording for each: its folder (or `root` if directly under `news/`), its `tags` list, and its filename.

## 2. Flag inconsistencies

- A file inside a category folder (`交通安全`, `勞權`, `國軍`, `社會`, `移工`, `警察`, `電力`, `食安`, or any newer folder — re-check the actual folder list, don't assume this one is current) whose `tags` do **not** include that folder's name.
- A file at `root` whose `tags` *do* include a name that matches an existing folder — it probably should have been placed inside that folder instead.

## 3. Look for folder-promotion candidates

Tally how many `root`-level articles share the same tag. If any tag appears on **3 or more** root-level articles, flag it as a candidate for promotion to its own folder — this mirrors how `電力` was created (see commit `34d66fc`) after enough articles on the topic accumulated at the root.

## 4. Report

Present a short table or list:

- Inconsistencies found: file → issue
- Folder-promotion candidates: tag → count → article filenames
- If nothing is found in either category, say so plainly — don't manufacture findings.

Then stop. If the user asks you to act on any finding (move a file, create a new folder + `_index.md`), do that as a separate, explicit step — not automatically as part of this report.
