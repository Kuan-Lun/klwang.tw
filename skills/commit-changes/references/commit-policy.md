# Commit grouping policy and public sources

The user requested decisions grounded in public commit/PR guidance. The following are adopted principles, not a claim that every repository must follow the source projects' complete contribution processes. Explicit user scope and applicable repository instructions take precedence.

## Logical changes: Git project

[Git — SubmittingPatches, “Make separate commits for logically separate changes”](https://git-scm.com/docs/SubmittingPatches#_make_separate_commits_for_logically_separate_changes)

Use a distinct commit for each independent purpose. A message that must describe several unrelated outcomes is evidence for splitting. Preserve enough explanation for a reviewer to understand the problem and resulting behavior.

This is guidance written for contributions to Git itself. Adopt its logical separation principle here; do not import Git's mailing-list process, branch strategy, sign-off requirements, or full test-suite policy.

## Reviewable, working units: Google Engineering Practices

[Google — Small CLs](https://google.github.io/eng-practices/review/developer/small-cls.html)

A change should be self-contained, include its relevant tests, and leave the system usable. Choose boundaries that make review and rollback understandable. Dependencies may form an ordered sequence if each step is valid. File count and line count are signals to inspect, not hard thresholds.

Google describes changelists, which are review units. Here those principles inform individual commits; they do not imply that one commit must become one PR or authorize creating PRs.

## Message semantics: Conventional Commits

[Conventional Commits 1.0.0](https://www.conventionalcommits.org/en/v1.0.0/), including the FAQ on changes fitting multiple types.

Use a type and optional scope to describe the commit's main intent. `feat` introduces a feature; `fix` addresses a bug. Other types are allowed. Mark real breaking changes with `!` or a `BREAKING CHANGE` footer as specified. The FAQ recommends splitting changes with multiple intents where possible.

This primarily specifies message syntax and semantics, not a complete splitting algorithm. A feature's supporting tests or documentation do not by themselves create unrelated intents. Apply the logical-purpose and working-state rules above first.

## Repository adaptation

Inspect the current diff and recent history each time. The recent history currently favors `type(scope): summary`, often with one news article per `feat(news)` commit. That is a local convention, not a requirement of any public specification. Do not carry over stale types, scopes, or article boundaries when the actual change or current repository policy differs.

For example, a theme update, tracking-branch setting, and helper script can belong together when they implement one theme-update workflow. Adding a general-purpose commit skill is independently useful and belongs in a separate commit. These are examples of the criteria, not predetermined groups for future requests.
