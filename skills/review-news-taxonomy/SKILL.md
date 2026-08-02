---
name: review-news-taxonomy
description: Audit source-code/content/news against the shared destination and news_tags policy, review semantic placement boundaries, and identify root-level tags that may deserve a folder. Use for taxonomy reviews and organization reports; remain strictly read-only.
---

# Review news taxonomy

Produce a read-only report. Do not move, rename, create, or edit content files even when the findings look unambiguous.

Work from the repository root. Resolve it with `git rev-parse --show-toplevel`
when necessary.

Read `skills/add-news/references/news-taxonomy.md` before interpreting placement.
The companion `news-taxonomy.toml` is the machine-readable source for structural
contracts and routing hints. Existing content is evidence, not a guarantee that
every historical placement is correct.

Then run:

```bash
scripts/audit-news-taxonomy.py
```

The script deterministically parses TOML frontmatter, skips `_index.md` as an
article, and applies the explicit policy rather than deriving taxonomy semantics
from Zola's `transparent` setting. It separates:

- **Errors**: malformed content, policy/index drift, unknown destinations,
  articles inside container-only sections, and missing tags required by an
  umbrella or editorial route.
- **Classification reviews**: ordinary folder tags that are preferred but not
  mandatory, plus root articles whose tags have configured destinations.
- **Folder-promotion candidates**: root tags meeting the configured threshold
  that are not already covered by a route.

After the deterministic pass, apply the semantic boundaries from the Markdown
reference to likely edge cases. At minimum, compare:

- `檢警法/` against both `獨立分類/警界醜聞/` routes;
- ordinary `移工/` against `獨立分類/移工內部社會新聞/`;
- cross-topic articles whose plausible destinations include `校園`/`偷拍`,
  `金融業`/`詐騙`, or `政府`/`醫療`/`食安`.

Do not promote a script review to an error without semantic evidence. Present
errors, classification reviews, semantic placement reviews, and promotion
candidates separately. If a section says `None.`, state that plainly. Stop after
the report and wait for explicit authorization before changing any taxonomy or
content.
