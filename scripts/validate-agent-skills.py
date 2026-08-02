#!/usr/bin/env python3
"""Validate canonical skills and their Claude/Codex discovery symlinks."""

from __future__ import annotations

import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = REPO_ROOT / "skills"
ADAPTER_DIRS = (REPO_ROOT / ".claude/skills", REPO_ROOT / ".agents/skills")
NAME_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
FRONTMATTER_PATTERN = re.compile(r"\A---\n(?P<body>.*?)\n---(?:\n|\Z)", re.DOTALL)


def parse_frontmatter(skill_file: Path) -> tuple[dict[str, str], list[str]]:
    errors: list[str] = []
    content = skill_file.read_text(encoding="utf-8")
    match = FRONTMATTER_PATTERN.match(content)
    if match is None:
        return {}, [f"{skill_file}: missing or malformed YAML frontmatter"]

    values: dict[str, str] = {}
    for line in match.group("body").splitlines():
        key, separator, value = line.partition(":")
        if not separator or not key.strip() or not value.strip():
            errors.append(f"{skill_file}: unsupported frontmatter line: {line!r}")
            continue
        key = key.strip()
        if key in values:
            errors.append(f"{skill_file}: duplicate frontmatter key: {key}")
            continue
        values[key] = value.strip().strip("\"'")

    unexpected = sorted(set(values) - {"name", "description"})
    if unexpected:
        errors.append(
            f"{skill_file}: agent-neutral frontmatter may only contain name and description; "
            f"found {', '.join(unexpected)}"
        )
    return values, errors


def main() -> int:
    errors: list[str] = []
    skill_dirs = sorted(path for path in SKILLS_DIR.iterdir() if path.is_dir())
    if not skill_dirs:
        errors.append(f"No skills found under {SKILLS_DIR}")

    for skill_dir in skill_dirs:
        skill_file = skill_dir / "SKILL.md"
        if not skill_file.is_file():
            errors.append(f"{skill_file}: missing")
            continue

        frontmatter, frontmatter_errors = parse_frontmatter(skill_file)
        errors.extend(frontmatter_errors)
        name = frontmatter.get("name", "")
        if name != skill_dir.name:
            errors.append(
                f"{skill_file}: frontmatter name {name!r} does not match directory {skill_dir.name!r}"
            )
        if name and NAME_PATTERN.fullmatch(name) is None:
            errors.append(f"{skill_file}: name must use lowercase hyphen-case")
        if not frontmatter.get("description"):
            errors.append(f"{skill_file}: description must not be empty")

        for adapter_dir in ADAPTER_DIRS:
            adapter = adapter_dir / skill_dir.name
            if not adapter.is_symlink():
                errors.append(f"{adapter}: expected a discovery symlink")
                continue
            try:
                target = adapter.resolve(strict=True)
            except FileNotFoundError:
                errors.append(f"{adapter}: broken symlink")
                continue
            if target != skill_dir.resolve():
                errors.append(
                    f"{adapter}: resolves to {target}, expected {skill_dir.resolve()}"
                )

    legacy_commands = sorted((REPO_ROOT / ".claude/commands").glob("*.md"))
    if legacy_commands:
        errors.append(
            "Legacy Claude commands would duplicate shared skills: "
            + ", ".join(str(path.relative_to(REPO_ROOT)) for path in legacy_commands)
        )

    if errors:
        print("Agent skill validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    print(
        f"Validated {len(skill_dirs)} shared skill(s) and "
        f"{len(skill_dirs) * len(ADAPTER_DIRS)} discovery symlink(s)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
