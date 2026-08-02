"""Shared policy and content readers for the news taxonomy tools."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path, PurePosixPath


SCHEMA_VERSION = 1
SECTION_KINDS = {"topic", "umbrella", "editorial", "container"}
INDEX_POLICIES = {"required", "optional", "none"}
ROOT_ACTIONS = {"allow", "review"}


@dataclass(frozen=True)
class Article:
    path: Path
    title: str
    slug: str
    date: str
    tags: tuple[str, ...]


@dataclass(frozen=True)
class ContentError:
    path: Path
    message: str


@dataclass(frozen=True)
class SectionPolicy:
    path: PurePosixPath
    kind: str
    index: str
    expected_transparent: bool | None
    allow_articles: bool
    require_any_tags: tuple[str, ...]
    prefer_any_tags: tuple[str, ...]


@dataclass(frozen=True)
class TagRoute:
    tag: str
    destinations: tuple[PurePosixPath, ...]
    root_action: str
    promotion_covered: bool


@dataclass(frozen=True)
class TaxonomyPolicy:
    path: Path
    promotion_threshold: int
    sections: tuple[SectionPolicy, ...]
    tag_routes: tuple[TagRoute, ...]

    @property
    def sections_by_path(self) -> dict[PurePosixPath, SectionPolicy]:
        return {section.path: section for section in self.sections}

    @property
    def routes_by_tag(self) -> dict[str, TagRoute]:
        return {route.tag: route for route in self.tag_routes}


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
        or not all(isinstance(tag, str) and tag for tag in tags)
    ):
        raise ValueError("news_tags must be a non-empty string array")
    if len(tags) != len(set(tags)):
        raise ValueError("news_tags must not contain duplicates")

    return tuple(tags)


def read_articles(news_dir: Path) -> tuple[list[Article], list[ContentError]]:
    articles: list[Article] = []
    errors: list[ContentError] = []

    for article_file in sorted(news_dir.rglob("*.md")):
        if article_file.name == "_index.md":
            continue
        try:
            frontmatter = read_frontmatter(article_file)
            tags = read_tags(frontmatter)
        except (OSError, ValueError) as error:
            errors.append(ContentError(article_file, str(error)))
            continue

        title_value = frontmatter.get("title")
        slug_value = frontmatter.get("slug")
        date_value = frontmatter.get("date")
        articles.append(
            Article(
                path=article_file,
                title=title_value
                if isinstance(title_value, str)
                else article_file.stem,
                slug=slug_value if isinstance(slug_value, str) else "",
                date=str(date_value) if date_value is not None else "",
                tags=tags,
            )
        )

    return articles, errors


def relative_path(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def _required_string(value: object, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field} must be a non-empty string")
    return value


def _string_tuple(value: object, field: str) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, list) or not all(
        isinstance(item, str) and item for item in value
    ):
        raise ValueError(f"{field} must be an array of non-empty strings")
    if len(value) != len(set(value)):
        raise ValueError(f"{field} must not contain duplicates")
    return tuple(value)


def _relative_policy_path(value: object, field: str) -> PurePosixPath:
    raw_path = _required_string(value, field)
    path = PurePosixPath(raw_path)
    if (
        path.is_absolute()
        or raw_path != path.as_posix()
        or ".." in path.parts
        or "\\" in raw_path
    ):
        raise ValueError(f"{field} must be a normalized relative POSIX path")
    if path in {PurePosixPath("."), PurePosixPath("")}:
        raise ValueError(f"{field} must not be the news root")
    return path


def load_policy(path: Path) -> TaxonomyPolicy:
    try:
        document = tomllib.loads(path.read_text(encoding="utf-8"))
    except OSError as error:
        raise ValueError(f"unable to read policy: {error}") from error
    except tomllib.TOMLDecodeError as error:
        raise ValueError(f"invalid TOML policy: {error}") from error

    if document.get("schema_version") != SCHEMA_VERSION:
        raise ValueError(f"schema_version must be {SCHEMA_VERSION}")

    promotion = document.get("promotion", {})
    if not isinstance(promotion, dict):
        raise ValueError("promotion must be a table")
    promotion_threshold = promotion.get("threshold", 3)
    if not isinstance(promotion_threshold, int) or promotion_threshold < 1:
        raise ValueError("promotion.threshold must be an integer of at least 1")

    raw_sections = document.get("sections")
    if not isinstance(raw_sections, list) or not raw_sections:
        raise ValueError("sections must contain at least one table")

    sections: list[SectionPolicy] = []
    section_paths: set[PurePosixPath] = set()
    for index, raw_section in enumerate(raw_sections):
        field_prefix = f"sections[{index}]"
        if not isinstance(raw_section, dict):
            raise ValueError(f"{field_prefix} must be a table")
        section_path = _relative_policy_path(
            raw_section.get("path"), f"{field_prefix}.path"
        )
        if section_path in section_paths:
            raise ValueError(f"duplicate section path: {section_path}")
        section_paths.add(section_path)

        kind = _required_string(raw_section.get("kind"), f"{field_prefix}.kind")
        if kind not in SECTION_KINDS:
            raise ValueError(
                f"{field_prefix}.kind must be one of {', '.join(sorted(SECTION_KINDS))}"
            )
        index_policy = _required_string(
            raw_section.get("index", "required"), f"{field_prefix}.index"
        )
        if index_policy not in INDEX_POLICIES:
            raise ValueError(
                f"{field_prefix}.index must be one of "
                f"{', '.join(sorted(INDEX_POLICIES))}"
            )
        expected_transparent = raw_section.get("expected_transparent")
        if expected_transparent is not None and not isinstance(
            expected_transparent, bool
        ):
            raise ValueError(f"{field_prefix}.expected_transparent must be boolean")
        allow_articles = raw_section.get("allow_articles", True)
        if not isinstance(allow_articles, bool):
            raise ValueError(f"{field_prefix}.allow_articles must be boolean")

        require_any_tags = _string_tuple(
            raw_section.get("require_any_tags"), f"{field_prefix}.require_any_tags"
        )
        prefer_any_tags = _string_tuple(
            raw_section.get("prefer_any_tags"), f"{field_prefix}.prefer_any_tags"
        )
        if set(require_any_tags) & set(prefer_any_tags):
            raise ValueError(
                f"{field_prefix} must not repeat tags across require_any_tags and "
                "prefer_any_tags"
            )

        sections.append(
            SectionPolicy(
                path=section_path,
                kind=kind,
                index=index_policy,
                expected_transparent=expected_transparent,
                allow_articles=allow_articles,
                require_any_tags=require_any_tags,
                prefer_any_tags=prefer_any_tags,
            )
        )

    raw_routes = document.get("tag_routes", [])
    if not isinstance(raw_routes, list):
        raise ValueError("tag_routes must be an array of tables")

    sections_by_path = {section.path: section for section in sections}
    tag_routes: list[TagRoute] = []
    route_tags: set[str] = set()
    for index, raw_route in enumerate(raw_routes):
        field_prefix = f"tag_routes[{index}]"
        if not isinstance(raw_route, dict):
            raise ValueError(f"{field_prefix} must be a table")
        tag = _required_string(raw_route.get("tag"), f"{field_prefix}.tag")
        if tag in route_tags:
            raise ValueError(f"duplicate tag route: {tag}")
        route_tags.add(tag)
        raw_destinations = _string_tuple(
            raw_route.get("destinations"), f"{field_prefix}.destinations"
        )
        if not raw_destinations:
            raise ValueError(f"{field_prefix}.destinations must not be empty")
        destinations = tuple(
            _relative_policy_path(destination, f"{field_prefix}.destinations")
            for destination in raw_destinations
        )
        unknown_destinations = [
            destination
            for destination in destinations
            if destination not in section_paths
        ]
        if unknown_destinations:
            raise ValueError(
                f"{field_prefix} references unknown destinations: "
                + ", ".join(map(str, unknown_destinations))
            )
        container_destinations = [
            destination
            for destination in destinations
            if not sections_by_path[destination].allow_articles
        ]
        if container_destinations:
            raise ValueError(
                f"{field_prefix} routes to container-only destinations: "
                + ", ".join(map(str, container_destinations))
            )
        root_action = _required_string(
            raw_route.get("root_action", "review"), f"{field_prefix}.root_action"
        )
        if root_action not in ROOT_ACTIONS:
            raise ValueError(
                f"{field_prefix}.root_action must be one of "
                f"{', '.join(sorted(ROOT_ACTIONS))}"
            )
        promotion_covered = raw_route.get("promotion_covered", True)
        if not isinstance(promotion_covered, bool):
            raise ValueError(f"{field_prefix}.promotion_covered must be boolean")
        tag_routes.append(
            TagRoute(
                tag=tag,
                destinations=destinations,
                root_action=root_action,
                promotion_covered=promotion_covered,
            )
        )

    return TaxonomyPolicy(
        path=path,
        promotion_threshold=promotion_threshold,
        sections=tuple(sections),
        tag_routes=tuple(tag_routes),
    )
