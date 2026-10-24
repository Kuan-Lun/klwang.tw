---
name: commit-changes
description: Review current Git changes, group them by purpose, and stage and create one or more coherent local commits when the user requests automatic committing. Also supports a read-only commit plan. For exactly the existing staged snapshot, use commit-staged.
---

# Commit changes by purpose

Turn the authorized changes into a small, reviewable commit sequence. Decide the number of commits from their intent and dependencies, not their file count.

## Scope and execution

- Direct invocation authorizes inspection, grouping, staging, and local commits within the requested scope. A request for a plan, preview, or `--dry-run` authorizes inspection only: leave HEAD, the index, and working files unchanged.
- Asking about this capability or creating/editing this skill does not authorize committing the current work.
- With no narrower scope, inspect all current staged, unstaged, and untracked changes. Read untracked contents before including them. Respect explicit exclusions; do not add ignored files, generated output, or credentials merely because they exist.
- For an explicit request to commit all current changes, reviewed staged and unstaged edits in the same file can belong together. For staged-only requests, preserve the exact staged snapshot and use `commit-staged`; do not expand it to the working-tree version.
- Show the proposed sequence and its reasons before committing. When automatic grouping and committing are already authorized, proceed without a separate approval for the number of commits.
- Create new local commits only. Do not push, amend, rebase, reset history, discard working changes, or bypass hooks as part of this workflow.

## Public basis for grouping

Read [references/commit-policy.md](references/commit-policy.md) when deciding the groups. It distinguishes the adopted guidance from this repository's conventions:

- Git's contribution guidelines: separate logically independent changes.
- Google's Small CLs guidance: keep changes self-contained, reviewable, and working; include related tests.
- Conventional Commits 1.0.0: describe intent with a type, optional scope, and summary; consider splitting unrelated intents.

These sources guide decisions; they do not impose a fixed file/line limit or a universal one-file-per-commit rule.

## Inspect and plan

From the repository root, inspect the following independently where possible:

```bash
git status --short --untracked-files=all
git diff --stat
git diff --submodule=log
git diff --cached --stat
git diff --cached --submodule=log
git log -20 --format='%h %s'
```

Also read applicable repository instructions and changed/untracked files. Use NUL-delimited Git output when handling paths programmatically. If no changes are in scope, report that without creating an empty commit. If there are unresolved conflicts or an ongoing merge/rebase/cherry-pick, report the state instead of treating it as ordinary automatic committing.

Build a plan with one row per commit: order, purpose, included paths or hunks, proposed message, and why it is kept together or separated. List excluded changes and validation relevant to the groups.

Apply these decision rules:

1. Keep implementation, required configuration, relevant tests, and documentation for one behavior together when splitting would leave an incomplete or misleading intermediate state.
2. Separate independently useful fixes, features, unrelated documentation, and mechanical cleanup. Separate an enabling refactor when it is independently valid; order dependent commits after it.
3. For a file containing unrelated changes, stage selected hunks when they form valid intermediate versions. Do not split overlapping changes just to manufacture smaller commits.
4. A dependency or submodule update may include its required compatibility changes. Review the old/new revision and nested worktree status; committing a gitlink does not commit dirty files inside a submodule. Do not fetch or create nested commits just to organize the parent's existing changes.
5. In this repository, independent news entries normally follow the recent one-article-per-commit convention; a single coordinated correction across articles can remain together. Use article titles for meaningful messages.

Use recent comparable commits to choose language, type, and scope. When the repository retains its Conventional Commits style, use `type(scope): summary` with a concise imperative summary. Related tests/docs do not automatically require separate `test:`/`docs:` commits. Include a body or breaking-change notation when needed to explain the actual change; do not invent trailers or sign-offs.

## Stage and commit each group

Before changing existing staging, record the starting HEAD and preserve the original staged diff (including binary changes) and path inventory outside the repository when staging must be rearranged. Account for index-only content that differs from both HEAD and the working tree. Preserve all excluded files, hunks, and their staged/unstaged boundaries.

For each planned group:

1. Recheck the relevant diffs against the plan. If another process changed them, reassess before staging.
2. Prepare only this group's index contents using explicit paths or selected patches. Isolate unrelated existing staging and retain enough information to restore it exactly. Do not use blanket `git add .`, `git add -A`, or `git commit -a`. A plain commit includes the entire index; `git commit --only <path>` reads working-tree contents and is not a safe shortcut for partially staged files.
3. Inspect the complete candidate `git diff --cached` and run `git diff --cached --check`. Confirm its contents and message match one planned group, with no missing dependency or excluded hunk. If the scope cannot be isolated without risking content loss, leave it intact and ask about that specific conflict.
4. Run checks appropriate to the change. Where later uncommitted work could hide missing dependencies, validate the candidate tree in a disposable directory. Do not claim a test on the combined working tree proves every intermediate commit works. Report unavailable checks accurately.
5. Commit with normal hooks enabled, using a properly quoted message or a message file. After the attempt, inspect HEAD, the resulting commit, and status. If a hook changes content or fails, review the changes before a retry; re-stage only in-scope fixes. Retry only after addressing a concrete cause. On repeated unchanged failure, report it and leave the remaining work uncommitted. Do not create a duplicate commit if HEAD already advanced.
6. Restore any temporarily isolated excluded staging without altering working files, then reassess the remaining groups. Keep completed commits if a later group fails; do not automatically undo or rewrite them.

Finish by reporting each new short hash and message, the reason for the grouping, validation performed, and any remaining staged, unstaged, untracked, or submodule changes. Do not equate a successful commit with a clean repository.
