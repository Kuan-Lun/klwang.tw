---
name: commit-staged
description: Draft and create a Git commit from exactly the currently staged changes using this repository's recent message convention. Use only when the user explicitly asks to commit staged work; never stage, amend, or push implicitly.
---

# Commit staged changes

Commit only after an explicit user request. Preserve the working tree and index scope: do not add unstaged or untracked files, amend an existing commit, bypass hooks, or push.

## 1. Confirm the staged scope

Work from the repository root and run `git status --short`. If nothing is staged, stop and ask the user to stage the intended files. Do not infer the intended scope or run `git add`.

## 2. Gather live conventions

Inspect these independently, in parallel when possible:

```bash
git diff --cached --stat
git diff --cached
git log --oneline -20
```

Treat the recent log as the source of truth. Do not preserve a stale hard-coded type or scope when the repository's convention has changed.

## 3. Draft one accurate message

Match the prevailing `type(scope): summary` shape when the recent log still uses it:

- Choose `type` from comparable recent commits; this repository uses `feat` frequently but also uses types such as `fix`, `refactor`, and `chore` when appropriate.
- Derive `scope` from the logical area changed, such as `news`, `skills`, `hooks`, `settings`, or another concise repository area.
- Write a lowercase, imperative, single-line summary that describes the staged diff. For a news entry, use the actual article title rather than only its filename.
- Do not add a body or trailers unless the recent history clearly establishes them for comparable changes.

If the staged diff spans unrelated logical changes, show the proposed split and ask whether to combine or split them. Do not manipulate the index until the user chooses. When splitting is requested, preserve all unstaged content and commit only the explicitly selected staged subsets.

## 4. Commit and verify

Show the proposed message, then commit it without bypassing verification:

```bash
git commit -m "type(scope): summary"
```

If a hook fails, fix only an in-scope underlying issue, re-stage the affected tracked files, and retry as a new commit attempt. Never use `--no-verify` or `--amend`.

After success, run:

```bash
git status --short
git log -1 --format='%h %s'
```

Report the short hash and final message. Also report any remaining unstaged, staged, or untracked changes accurately; do not claim the tree is clean merely because the staged commit succeeded. Do not push.
