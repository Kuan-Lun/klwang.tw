#!/usr/bin/env python3
"""Print compact slug, tag, and destination context for adding news."""

from __future__ import annotations

import argparse
import sys
from collections import Counter, defaultdict
from pathlib import Path, PurePosixPath


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
DEFAULT_POLICY_PATH = REPO_ROOT / "skills/add-news/references/news-taxonomy.toml"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from news_taxonomy import (  # noqa: E402
    Article,
    SectionPolicy,
    TaxonomyPolicy,
    load_policy,
    read_articles,
    relative_path,
)


def _cell(value: object) -> str:
    return str(value).replace("\t", " ").replace("\r", " ").replace("\n", " ")


def _top_counts(values: Counter[str], limit: int = 5) -> str:
    ordered = sorted(values.items(), key=lambda item: (-item[1], item[0]))[:limit]
    return ",".join(f"{_cell(value)}:{count}" for value, count in ordered) or "-"


def _tag_contract(section: SectionPolicy) -> tuple[str, tuple[str, ...]]:
    if section.require_any_tags:
        return "required", section.require_any_tags
    if section.prefer_any_tags:
        return "preferred", section.prefer_any_tags
    return "none", ()


def _articles_by_parent(
    articles: list[Article], news_dir: Path
) -> dict[PurePosixPath, list[Article]]:
    grouped: dict[PurePosixPath, list[Article]] = defaultdict(list)
    for article in articles:
        if article.path.parent == news_dir:
            grouped[PurePosixPath(".")].append(article)
        else:
            grouped[PurePosixPath(relative_path(article.path.parent, news_dir))].append(
                article
            )
    return grouped


def render_context(
    news_dir: Path, policy: TaxonomyPolicy, *, include_all_slugs: bool = False
) -> str:
    articles, content_errors = read_articles(news_dir)
    grouped = _articles_by_parent(articles, news_dir)
    lines = ["NEWS_CONTEXT\t2", "", "[slug_prefixes]", "prefix\tcount\texamples"]

    prefix_slugs: dict[str, list[str]] = defaultdict(list)
    for article in articles:
        if article.slug:
            prefix_slugs[article.slug.split("-", maxsplit=1)[0]].append(article.slug)
    for prefix, slugs in sorted(
        prefix_slugs.items(), key=lambda item: (-len(item[1]), item[0])
    ):
        examples = ",".join(sorted(set(slugs))[:3])
        lines.append(f"{_cell(prefix)}\t{len(slugs)}\t{_cell(examples)}")

    lines.extend(["", "[news_tags]", "tag\tarticles"])
    tag_counts = Counter(tag for article in articles for tag in set(article.tags))
    for tag, count in sorted(tag_counts.items(), key=lambda item: (-item[1], item[0])):
        lines.append(f"{_cell(tag)}\t{count}")

    lines.extend(
        [
            "",
            "[destinations]",
            "kind\tpath\tarticles\ttag_policy\ttag_hits\tfirst_tag_hits\tcommon_tags",
        ]
    )
    for section in policy.sections:
        if not section.allow_articles:
            continue
        destination_articles = grouped.get(section.path, [])
        policy_name, contract_tags = _tag_contract(section)
        contract_set = set(contract_tags)
        tag_hits = sum(
            not contract_set.isdisjoint(article.tags)
            for article in destination_articles
        )
        first_tag_hits = sum(
            bool(article.tags) and article.tags[0] in contract_set
            for article in destination_articles
        )
        common_tags = Counter(
            tag for article in destination_articles for tag in set(article.tags)
        )
        lines.append(
            "\t".join(
                (
                    _cell(section.kind),
                    _cell(section.path.as_posix()),
                    str(len(destination_articles)),
                    _cell(policy_name),
                    f"{tag_hits}/{len(destination_articles)}",
                    f"{first_tag_hits}/{len(destination_articles)}",
                    _top_counts(common_tags),
                )
            )
        )

    lines.extend(["", "[tag_routes]", "tag\tdestinations\troot_action"])
    for route in policy.tag_routes:
        destinations = ",".join(
            destination.as_posix() for destination in route.destinations
        )
        lines.append(
            f"{_cell(route.tag)}\t{_cell(destinations)}\t{_cell(route.root_action)}"
        )

    lines.extend(
        [
            "",
            "[recent_destination_examples]",
            "kind\tpath\tdate\ttags\ttitle\tfile",
        ]
    )
    for section in policy.sections:
        if not section.allow_articles:
            continue
        destination_articles = sorted(
            grouped.get(section.path, []),
            key=lambda article: (article.date, article.path.name),
            reverse=True,
        )[:2]
        for article in destination_articles:
            lines.append(
                "\t".join(
                    (
                        _cell(section.kind),
                        _cell(section.path.as_posix()),
                        _cell(article.date),
                        _cell(",".join(article.tags)),
                        _cell(article.title),
                        _cell(relative_path(article.path, news_dir)),
                    )
                )
            )

    root_articles = grouped.get(PurePosixPath("."), [])
    root_tag_counts = Counter(
        tag for article in root_articles for tag in set(article.tags)
    )
    lines.extend(
        [
            "",
            "[root_fallback]",
            "path\tarticles\tcommon_tags",
            f".\t{len(root_articles)}\t{_top_counts(root_tag_counts)}",
        ]
    )

    configured_paths = set(policy.sections_by_path)
    unconfigured_paths = sorted(
        path
        for path in grouped
        if path != PurePosixPath(".") and path not in configured_paths
    )
    if unconfigured_paths:
        lines.extend(["", "[unconfigured_destinations]", "path\tarticles"])
        for path in unconfigured_paths:
            lines.append(f"{_cell(path.as_posix())}\t{len(grouped[path])}")

    if include_all_slugs:
        lines.extend(["", "[all_slugs]", "slug\tfile"])
        for article in sorted(articles, key=lambda item: (item.slug, item.path)):
            if article.slug:
                lines.append(
                    f"{_cell(article.slug)}\t{_cell(relative_path(article.path, news_dir))}"
                )

    if content_errors:
        lines.extend(["", "[content_errors]", "file\tmessage"])
        for error in content_errors:
            lines.append(
                f"{_cell(relative_path(error.path, news_dir))}\t{_cell(error.message)}"
            )

    return "\n".join(lines)


def check_slug(news_dir: Path, slug: str) -> str:
    articles, _ = read_articles(news_dir)
    matches = [
        relative_path(article.path, news_dir)
        for article in articles
        if article.slug == slug
    ]
    if matches:
        return "\n".join(f"EXISTS\t{_cell(slug)}\t{_cell(path)}" for path in matches)
    return f"AVAILABLE\t{_cell(slug)}"


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
        "--all-slugs",
        action="store_true",
        help="append every slug and source file to the compact default report",
    )
    parser.add_argument(
        "--check-slug",
        metavar="SLUG",
        help="print AVAILABLE or matching EXISTS rows for one exact slug",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    news_dir = args.news_dir.resolve()
    if not news_dir.is_dir():
        print(f"News directory does not exist: {news_dir}", file=sys.stderr)
        return 2
    if args.check_slug is not None:
        print(check_slug(news_dir, args.check_slug))
        return 0

    try:
        policy = load_policy(args.policy.resolve())
    except ValueError as error:
        print(f"Invalid taxonomy policy: {error}", file=sys.stderr)
        return 2
    print(render_context(news_dir, policy, include_all_slugs=args.all_slugs))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
