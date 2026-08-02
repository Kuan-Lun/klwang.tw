#!/usr/bin/env python3
"""Audit news folder placement and news_tags without modifying content."""

from __future__ import annotations

import argparse
import sys
import tomllib
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Article:
    path: Path
    tags: tuple[str, ...]


def read_frontmatter(path: Path) -> dict[str, object]:
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0].strip() != "+++":
        raise ValueError("missing opening TOML frontmatter delimiter")

    try:
        closing = next(
            i for i, line in enumerate(lines[1:], start=1) if line.strip() == "+++"
        )
    except StopIteration as error:
        raise ValueError("missing closing TOML frontmatter delimiter") from error

    try:
        return tomllib.loads("\n".join(lines[1:closing]))
    except tomllib.TOMLDecodeError as error:
        raise ValueError(f"invalid TOML frontmatter: {error}") from error


def read_tags(frontmatter: dict[str, object]) -> tuple[str, ...]:
    taxonomies = frontmatter.get("taxonomies")
    if not isinstance(taxonomies, dict):
        raise ValueError("missing [taxonomies] table")

    tags = taxonomies.get("news_tags")
    if (
        not isinstance(tags, list)
        or not tags
        or not all(isinstance(tag, str) for tag in tags)
    ):
        raise ValueError("news_tags must be a non-empty string array")

    return tuple(tags)


def relative(path: Path, news_dir: Path) -> str:
    return path.relative_to(news_dir).as_posix()


def find_categories(
    news_dir: Path,
) -> tuple[dict[Path, str], dict[str, list[Path]], list[str]]:
    by_path: dict[Path, str] = {}
    by_name: dict[str, list[Path]] = defaultdict(list)
    errors: list[str] = []

    for index_file in sorted(news_dir.rglob("_index.md")):
        if index_file.parent == news_dir:
            continue
        try:
            frontmatter = read_frontmatter(index_file)
        except (OSError, ValueError) as error:
            errors.append(f"`{relative(index_file, news_dir)}`: {error}")
            continue

        # A transparent Zola section is the repo's tag-backed category shape.
        # Non-transparent nested sections are editorial groupings, so their
        # names are not required to appear in every descendant article's tags.
        if frontmatter.get("transparent") is not True:
            continue

        folder = index_file.parent
        name = folder.name
        by_path[folder] = name
        by_name[name].append(folder)

    return by_path, dict(by_name), errors


def find_articles(news_dir: Path) -> tuple[list[Article], list[str]]:
    articles: list[Article] = []
    errors: list[str] = []

    for article_file in sorted(news_dir.rglob("*.md")):
        if article_file.name == "_index.md":
            continue
        try:
            tags = read_tags(read_frontmatter(article_file))
        except (OSError, ValueError) as error:
            errors.append(f"`{relative(article_file, news_dir)}`: {error}")
            continue
        articles.append(Article(article_file, tags))

    return articles, errors


def audit(news_dir: Path, threshold: int) -> str:
    categories_by_path, categories_by_name, index_errors = find_categories(news_dir)
    articles, article_errors = find_articles(news_dir)
    inconsistencies = [*index_errors, *article_errors]
    root_tags: Counter[str] = Counter()
    root_articles: dict[str, list[str]] = defaultdict(list)

    for article in articles:
        article_path = relative(article.path, news_dir)
        category_name = categories_by_path.get(article.path.parent)
        if category_name is not None and category_name not in article.tags:
            inconsistencies.append(
                f"`{article_path}`: category folder `{category_name}` is missing from news_tags "
                f"({', '.join(f'`{tag}`' for tag in article.tags)})"
            )

        if article.path.parent != news_dir:
            continue

        for tag in article.tags:
            root_tags[tag] += 1
            root_articles[tag].append(article.path.name)
            matching_folders = categories_by_name.get(tag, [])
            if matching_folders:
                destinations = ", ".join(
                    f"`{relative(folder, news_dir)}/`" for folder in matching_folders
                )
                inconsistencies.append(
                    f"`{article_path}`: root article has category tag `{tag}`; expected under {destinations}"
                )

    candidates = [
        (tag, count, sorted(root_articles[tag]))
        for tag, count in root_tags.items()
        if count >= threshold and tag not in categories_by_name
    ]
    candidates.sort(key=lambda item: (-item[1], item[0]))

    lines = [
        "# News taxonomy audit",
        "",
        f"Scanned {len(articles)} article(s) and found {len(categories_by_path)} tag-backed category folder(s).",
        "",
        "## Inconsistencies",
        "",
    ]
    if inconsistencies:
        lines.extend(f"- {issue}" for issue in sorted(inconsistencies))
    else:
        lines.append("None.")

    lines.extend(
        ["", f"## Folder-promotion candidates (at least {threshold} root articles)", ""]
    )
    if candidates:
        for tag, count, filenames in candidates:
            lines.append(f"- `{tag}` — {count} article(s)")
            lines.extend(f"  - `{filename}`" for filename in filenames)
    else:
        lines.append("None.")

    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    repo_root = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--news-dir",
        type=Path,
        default=repo_root / "source-code/content/news",
        help="news content directory (defaults to this repository's news directory)",
    )
    parser.add_argument(
        "--threshold",
        type=int,
        default=3,
        help="minimum root-level article count for a folder-promotion candidate",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    news_dir = args.news_dir.resolve()
    if not news_dir.is_dir():
        print(f"News directory does not exist: {news_dir}", file=sys.stderr)
        return 2
    if args.threshold < 1:
        print("--threshold must be at least 1", file=sys.stderr)
        return 2

    print(audit(news_dir, args.threshold))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
