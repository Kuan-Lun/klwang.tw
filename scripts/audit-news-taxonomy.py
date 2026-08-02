#!/usr/bin/env python3
"""Audit news placement and tags against the explicit taxonomy policy."""

from __future__ import annotations

import argparse
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path, PurePosixPath


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
DEFAULT_POLICY_PATH = REPO_ROOT / "skills/add-news/references/news-taxonomy.toml"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from news_taxonomy import (  # noqa: E402
    SectionPolicy,
    TaxonomyPolicy,
    load_policy,
    read_articles,
    read_frontmatter,
    relative_path,
)


@dataclass(frozen=True)
class Finding:
    code: str
    path: str
    message: str


@dataclass(frozen=True)
class PromotionCandidate:
    tag: str
    count: int
    filenames: tuple[str, ...]


@dataclass(frozen=True)
class AuditReport:
    article_count: int
    destination_count: int
    errors: tuple[Finding, ...]
    reviews: tuple[Finding, ...]
    candidates: tuple[PromotionCandidate, ...]


def _finding(code: str, path: str, message: str) -> Finding:
    return Finding(code=code, path=path, message=message)


def _tags_label(tags: tuple[str, ...]) -> str:
    return ", ".join(f"`{tag}`" for tag in tags)


def _destination_label(section: SectionPolicy) -> str:
    return f"`{section.path.as_posix()}/` ({section.kind})"


def _check_section_structure(news_dir: Path, policy: TaxonomyPolicy) -> list[Finding]:
    errors: list[Finding] = []
    sections_by_path = policy.sections_by_path

    for section in policy.sections:
        folder = news_dir.joinpath(*section.path.parts)
        index_file = folder / "_index.md"
        section_path = section.path.as_posix()

        if not folder.is_dir():
            errors.append(
                _finding(
                    "destination-missing",
                    section_path,
                    f"configured destination `{section_path}/` does not exist",
                )
            )
            continue

        if section.index == "required" and not index_file.is_file():
            errors.append(
                _finding(
                    "index-missing",
                    section_path,
                    f"{_destination_label(section)} requires `_index.md`",
                )
            )
            continue
        if section.index == "none" and index_file.exists():
            errors.append(
                _finding(
                    "unexpected-index",
                    relative_path(index_file, news_dir),
                    f"{_destination_label(section)} must not have `_index.md`",
                )
            )
            continue
        if not index_file.is_file():
            continue

        try:
            frontmatter = read_frontmatter(index_file)
        except (OSError, ValueError) as error:
            errors.append(
                _finding(
                    "invalid-index",
                    relative_path(index_file, news_dir),
                    str(error),
                )
            )
            continue

        if section.expected_transparent is None:
            continue
        actual_transparent = frontmatter.get("transparent", False)
        if actual_transparent is not section.expected_transparent:
            expected = str(section.expected_transparent).lower()
            actual = str(actual_transparent).lower()
            errors.append(
                _finding(
                    "transparent-drift",
                    relative_path(index_file, news_dir),
                    f"expected `transparent = {expected}`, found `{actual}`",
                )
            )

    for index_file in sorted(news_dir.rglob("_index.md")):
        if index_file.parent == news_dir:
            continue
        relative_folder = PurePosixPath(relative_path(index_file.parent, news_dir))
        if relative_folder not in sections_by_path:
            errors.append(
                _finding(
                    "unconfigured-section",
                    relative_path(index_file, news_dir),
                    "section is not declared in the taxonomy policy",
                )
            )

    return errors


def run_audit(
    news_dir: Path, policy: TaxonomyPolicy, threshold: int | None = None
) -> AuditReport:
    effective_threshold = policy.promotion_threshold if threshold is None else threshold
    if effective_threshold < 1:
        raise ValueError("threshold must be at least 1")

    errors = _check_section_structure(news_dir, policy)
    reviews: list[Finding] = []
    articles, content_errors = read_articles(news_dir)
    sections_by_path = policy.sections_by_path
    routes_by_tag = policy.routes_by_tag
    root_tags: Counter[str] = Counter()
    root_articles: dict[str, list[str]] = defaultdict(list)

    for content_error in content_errors:
        errors.append(
            _finding(
                "invalid-article",
                relative_path(content_error.path, news_dir),
                content_error.message,
            )
        )

    for article in articles:
        article_path = relative_path(article.path, news_dir)
        if article.path.parent == news_dir:
            for tag in article.tags:
                root_tags[tag] += 1
                root_articles[tag].append(article.path.name)
                route = routes_by_tag.get(tag)
                if route is None or route.root_action != "review":
                    continue
                destinations = ", ".join(
                    f"`{destination.as_posix()}/`" for destination in route.destinations
                )
                reviews.append(
                    _finding(
                        "root-route-review",
                        article_path,
                        f"root article has routed tag `{tag}`; review {destinations} "
                        "or keep the root fallback intentionally",
                    )
                )
            continue

        parent_path = PurePosixPath(relative_path(article.path.parent, news_dir))
        section = sections_by_path.get(parent_path)
        if section is None:
            errors.append(
                _finding(
                    "unknown-destination",
                    article_path,
                    f"article folder `{parent_path.as_posix()}/` is not in the policy",
                )
            )
            continue
        if not section.allow_articles:
            errors.append(
                _finding(
                    "container-has-article",
                    article_path,
                    f"{_destination_label(section)} does not allow direct articles",
                )
            )
            continue

        article_tags = set(article.tags)
        if section.require_any_tags and article_tags.isdisjoint(
            section.require_any_tags
        ):
            errors.append(
                _finding(
                    "required-tag-missing",
                    article_path,
                    f"{_destination_label(section)} requires at least one of "
                    f"{_tags_label(section.require_any_tags)}; found "
                    f"{_tags_label(article.tags)}",
                )
            )
        if section.prefer_any_tags and article_tags.isdisjoint(section.prefer_any_tags):
            reviews.append(
                _finding(
                    "preferred-tag-missing",
                    article_path,
                    f"{_destination_label(section)} normally uses one of "
                    f"{_tags_label(section.prefer_any_tags)}; review the placement or tags "
                    f"({_tags_label(article.tags)})",
                )
            )

    candidates: list[PromotionCandidate] = []
    for tag, count in root_tags.items():
        route = routes_by_tag.get(tag)
        if count < effective_threshold or (
            route is not None and route.promotion_covered
        ):
            continue
        candidates.append(
            PromotionCandidate(
                tag=tag,
                count=count,
                filenames=tuple(sorted(root_articles[tag])),
            )
        )

    errors.sort(key=lambda finding: (finding.path, finding.code, finding.message))
    reviews.sort(key=lambda finding: (finding.path, finding.code, finding.message))
    candidates.sort(key=lambda candidate: (-candidate.count, candidate.tag))
    destination_count = sum(section.allow_articles for section in policy.sections)
    return AuditReport(
        article_count=len(articles),
        destination_count=destination_count,
        errors=tuple(errors),
        reviews=tuple(reviews),
        candidates=tuple(candidates),
    )


def render_markdown(report: AuditReport, threshold: int) -> str:
    lines = [
        "# News taxonomy audit",
        "",
        f"Scanned {report.article_count} article(s) against "
        f"{report.destination_count} configured destination(s).",
        "",
        "## Errors",
        "",
    ]
    if report.errors:
        lines.extend(
            f"- `{finding.path}` [{finding.code}]: {finding.message}"
            for finding in report.errors
        )
    else:
        lines.append("None.")

    lines.extend(["", "## Classification reviews", ""])
    if report.reviews:
        lines.extend(
            f"- `{finding.path}` [{finding.code}]: {finding.message}"
            for finding in report.reviews
        )
    else:
        lines.append("None.")

    lines.extend(
        ["", f"## Folder-promotion candidates (at least {threshold} root articles)", ""]
    )
    if report.candidates:
        for candidate in report.candidates:
            lines.append(f"- `{candidate.tag}` — {candidate.count} article(s)")
            lines.extend(f"  - `{filename}`" for filename in candidate.filenames)
    else:
        lines.append("None.")

    return "\n".join(lines)


def audit(
    news_dir: Path,
    threshold: int | None = None,
    policy_path: Path = DEFAULT_POLICY_PATH,
) -> str:
    policy = load_policy(policy_path)
    report = run_audit(news_dir, policy, threshold)
    effective_threshold = policy.promotion_threshold if threshold is None else threshold
    return render_markdown(report, effective_threshold)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--news-dir",
        type=Path,
        default=REPO_ROOT / "source-code/content/news",
        help="news content directory (defaults to this repository's news directory)",
    )
    parser.add_argument(
        "--policy",
        type=Path,
        default=DEFAULT_POLICY_PATH,
        help="taxonomy policy TOML",
    )
    parser.add_argument(
        "--threshold",
        type=int,
        help="override the policy's root-tag promotion threshold",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="exit 1 when hard errors are found; reviews do not fail the check",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    news_dir = args.news_dir.resolve()
    policy_path = args.policy.resolve()
    if not news_dir.is_dir():
        print(f"News directory does not exist: {news_dir}", file=sys.stderr)
        return 2
    if args.threshold is not None and args.threshold < 1:
        print("--threshold must be at least 1", file=sys.stderr)
        return 2

    try:
        policy = load_policy(policy_path)
        report = run_audit(news_dir, policy, args.threshold)
    except ValueError as error:
        print(f"Invalid taxonomy policy: {error}", file=sys.stderr)
        return 2

    threshold = policy.promotion_threshold if args.threshold is None else args.threshold
    print(render_markdown(report, threshold))
    return 1 if args.check and report.errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
