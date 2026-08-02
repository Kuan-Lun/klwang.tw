from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "audit-news-taxonomy.py"
SPEC = importlib.util.spec_from_file_location("audit_news_taxonomy", SCRIPT_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"Unable to load {SCRIPT_PATH}")
AUDIT_MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = AUDIT_MODULE
SPEC.loader.exec_module(AUDIT_MODULE)


def write_index(folder: Path, *, transparent: bool) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    folder.joinpath("_index.md").write_text(
        f'+++\ntitle = "{folder.name}"\ntransparent = {str(transparent).lower()}\n+++\n',
        encoding="utf-8",
    )


def write_article(path: Path, tags: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rendered_tags = ", ".join(f'"{tag}"' for tag in tags)
    path.write_text(
        f'+++\ntitle = "Test"\ndate = "2026-01-01"\n\n[taxonomies]\n'
        f"news_tags = [{rendered_tags}]\n+++\n",
        encoding="utf-8",
    )


class AuditNewsTaxonomyTest(unittest.TestCase):
    def test_category_rules_and_promotion_candidates(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            news_dir = Path(temp_dir) / "news"
            write_index(news_dir / "交通", transparent=True)
            write_index(news_dir / "獨立分類", transparent=False)
            write_index(news_dir / "獨立分類/警察", transparent=True)

            write_article(news_dir / "交通/good.md", ["交通"])
            write_article(news_dir / "交通/bad.md", ["其他"])
            write_article(news_dir / "獨立分類/grouped.md", ["其他"])
            write_article(news_dir / "獨立分類/警察/officer.md", ["警察"])
            write_article(news_dir / "root-existing.md", ["警察"])
            for index in range(3):
                write_article(news_dir / f"candidate-{index}.md", ["候選"])

            report = AUDIT_MODULE.audit(news_dir, threshold=3)

        self.assertIn("交通/bad.md", report)
        self.assertIn("root-existing.md", report)
        self.assertIn("expected under `獨立分類/警察/`", report)
        self.assertIn("`候選` — 3 article(s)", report)
        self.assertNotIn("獨立分類/grouped.md", report)
        self.assertNotIn("交通/good.md", report)
        self.assertNotIn("獨立分類/警察/officer.md", report)


if __name__ == "__main__":
    unittest.main()
