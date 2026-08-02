---
name: review-news-taxonomy
description: Audit source-code/content/news for news_tags and category-folder consistency, then identify root-level tags that may deserve a folder. Use for taxonomy reviews and organization reports; remain strictly read-only.
---

# Review news taxonomy

Produce a read-only report. Do not move, rename, create, or edit content files even when the findings look unambiguous.

Work from the repository root. Resolve it with `git rev-parse --show-toplevel` when necessary, then run:

```bash
scripts/audit-news-taxonomy.py
```

The script deterministically parses TOML frontmatter, skips `_index.md` as articles, and applies these repository rules:

- Treat folders whose `_index.md` has `transparent = true` as tag-backed categories, including nested categories.
- Require an article directly inside a tag-backed category to include that category name in `news_tags`.
- Flag a root-level article when one of its `news_tags` values already maps to a tag-backed category.
- Treat non-transparent nested sections as editorial groupings rather than category tags, avoiding false positives from their ancestor names.
- Flag a root-level tag as a folder-promotion candidate when it appears on at least three articles and has no existing tag-backed category.

Present the script's two result sections clearly:

1. Inconsistencies: file path and issue.
2. Folder-promotion candidates: tag, count, and article filenames.

If a section says `None.`, state that plainly. Stop after the report and wait for explicit authorization before changing any taxonomy or content.
