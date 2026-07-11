---
description: Draft a commit message matching this repo's existing convention from the currently staged changes, then commit them.
---

Commit the currently staged changes. This command drafts the message itself — no need to type one.

## 1. Check there's something to commit

Run `git status`. If nothing is staged, stop and tell the user to `git add` the files first — don't guess at what they meant to include, and don't stage anything yourself.

## 2. Gather context

In parallel:

```bash
git diff --cached
git log --oneline -20
```

The log shows this repo's live convention, not a fixed rulebook — read the last 20 before assuming the pattern below still holds.

## 3. Match the convention

As of this writing, every commit in this repo follows `type(scope): summary`:

- **type** is almost always `feat`, even for small edits (typo fixes, tag updates) — this repo doesn't distinguish `fix`/`chore`/`docs` the way some do. Only deviate if the log itself shows a different type in recent history.
- **scope** is the area touched: `news` for anything under `source-code/content/news/`, `settings` for `.claude/settings*`, `commands` for `.claude/commands/`, `gitignore` for `.gitignore`. If the staged files don't match an existing scope, derive a short new one from the top-level path touched.
- **summary** is a lowercase imperative clause naming what was added/changed, e.g. `add article on <title> with details and link`, `update tags for <article> article to reflect <reason>`, `add <name> script for <purpose>`. For news articles use the article's actual title, not the filename.

Single-line message only — this repo's history has no multi-line bodies or trailers, so don't add one.

## 4. Handle mixed staged changes

If the staged diff spans multiple unrelated scopes (e.g. a news article plus an unrelated settings tweak), don't force one message. Show the user the split you see and ask whether to commit as one combined message, or split into separate `git add`/`git commit` passes — then proceed accordingly.

## 5. Commit

Show the drafted message, then commit with it via heredoc:

```bash
git commit -m "$(cat <<'EOF'
type(scope): summary
EOF
)"
```

Never use `--no-verify`. If a pre-commit hook fails, fix the underlying issue, re-stage, and commit again as a **new** attempt — don't amend.

## 6. Confirm

Run `git status` to confirm a clean tree, then report the short hash and final message back to the user. Don't push — that's a separate, explicit step.
