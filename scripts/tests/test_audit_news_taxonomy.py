from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parents[1]
SCRIPT_PATH = SCRIPT_DIR / "audit-news-taxonomy.py"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
SPEC = importlib.util.spec_from_file_location("audit_news_taxonomy", SCRIPT_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"Unable to load {SCRIPT_PATH}")
AUDIT_MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = AUDIT_MODULE
SPEC.loader.exec_module(AUDIT_MODULE)


def write_index(folder: Path, *, transparent: bool) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    folder.joinpath("_index.md").write_text(
        f'+++\ntitle = "{folder.name}"\n'
        f"transparent = {str(transparent).lower()}\n+++\n",
        encoding="utf-8",
    )


def write_article(path: Path, tags: list[str], *, slug: str = "test-1") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rendered_tags = ", ".join(f'"{tag}"' for tag in tags)
    path.write_text(
        '+++\ntitle = "Test"\ndate = "2026-01-01"\n'
        f'slug = "{slug}"\n\n[taxonomies]\nnews_tags = [{rendered_tags}]\n+++\n',
        encoding="utf-8",
    )


def write_policy(path: Path) -> None:
    path.write_text(
        """schema_version = 1

[promotion]
threshold = 3

[[sections]]
path = "交通"
kind = "topic"
index = "required"
expected_transparent = true
allow_articles = true
prefer_any_tags = ["交通"]

[[sections]]
path = "檢警法"
kind = "umbrella"
index = "required"
expected_transparent = true
allow_articles = true
require_any_tags = ["檢警法", "警察", "檢察官"]

[[sections]]
path = "獨立分類/警界醜聞"
kind = "container"
index = "required"
expected_transparent = false
allow_articles = false

[[sections]]
path = "獨立分類/警界醜聞/警察"
kind = "editorial"
index = "required"
expected_transparent = true
allow_articles = true
require_any_tags = ["警察"]

[[sections]]
path = "獨立分類/移工內部社會新聞"
kind = "editorial"
index = "required"
expected_transparent = false
allow_articles = true
require_any_tags = ["移工"]

[[tag_routes]]
tag = "交通"
destinations = ["交通"]
root_action = "review"
promotion_covered = true

[[tag_routes]]
tag = "警察"
destinations = ["檢警法", "獨立分類/警界醜聞/警察"]
root_action = "review"
promotion_covered = true

[[tag_routes]]
tag = "移工"
destinations = ["獨立分類/移工內部社會新聞"]
root_action = "review"
promotion_covered = true
""",
        encoding="utf-8",
    )


class AuditNewsTaxonomyTest(unittest.TestCase):
    def test_explicit_policy_separates_errors_reviews_and_candidates(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            news_dir = root / "news"
            policy_path = root / "policy.toml"
            write_policy(policy_path)

            write_index(news_dir / "交通", transparent=True)
            write_index(news_dir / "檢警法", transparent=True)
            write_index(news_dir / "獨立分類/警界醜聞", transparent=False)
            write_index(news_dir / "獨立分類/警界醜聞/警察", transparent=True)
            write_index(news_dir / "獨立分類/移工內部社會新聞", transparent=False)

            write_article(news_dir / "交通/good.md", ["交通"], slug="test-good")
            write_article(news_dir / "交通/review.md", ["其他"], slug="test-review")
            write_article(
                news_dir / "檢警法/umbrella-good.md",
                ["檢察官"],
                slug="test-umbrella-good",
            )
            write_article(
                news_dir / "檢警法/umbrella-bad.md",
                ["金融業"],
                slug="test-umbrella-bad",
            )
            write_article(
                news_dir / "獨立分類/警界醜聞/警察/good.md",
                ["警察"],
                slug="test-police-good",
            )
            write_article(
                news_dir / "獨立分類/移工內部社會新聞/bad.md",
                ["其他"],
                slug="test-migrant-bad",
            )
            write_article(news_dir / "root-police.md", ["警察"], slug="root-police")
            write_article(news_dir / "root-route.md", ["交通"], slug="root-route")
            for index in range(3):
                write_article(
                    news_dir / f"candidate-{index}.md",
                    ["候選"],
                    slug=f"candidate-{index}",
                )

            policy = AUDIT_MODULE.load_policy(policy_path)
            report = AUDIT_MODULE.run_audit(news_dir, policy)
            rendered = AUDIT_MODULE.render_markdown(report, threshold=3)

        error_paths = {finding.path for finding in report.errors}
        review_paths = {finding.path for finding in report.reviews}
        self.assertEqual(
            error_paths,
            {
                "檢警法/umbrella-bad.md",
                "獨立分類/移工內部社會新聞/bad.md",
            },
        )
        self.assertIn("交通/review.md", review_paths)
        self.assertIn("root-police.md", review_paths)
        self.assertIn("root-route.md", review_paths)
        self.assertEqual(
            [(candidate.tag, candidate.count) for candidate in report.candidates],
            [("候選", 3)],
        )
        self.assertIn("## Errors", rendered)
        self.assertIn("## Classification reviews", rendered)
        self.assertIn("`候選` — 3 article(s)", rendered)

    def test_repository_policy_avoids_old_umbrella_false_positives(self) -> None:
        repo_root = SCRIPT_DIR.parent
        news_dir = repo_root / "source-code/content/news"
        policy = AUDIT_MODULE.load_policy(AUDIT_MODULE.DEFAULT_POLICY_PATH)

        report = AUDIT_MODULE.run_audit(news_dir, policy)

        error_paths = {finding.path for finding in report.errors}
        review_paths = {finding.path for finding in report.reviews}
        self.assertEqual(error_paths, set())
        self.assertNotIn(
            "檢警法/2025-05-09_女檢赴88會館受招待遭罰俸3月.md",
            review_paths,
        )
        self.assertNotIn(
            "獨立分類/警界醜聞/檢察官/2026-06-27_前檢察官涉高利貸案改裁交保科技監控.md",
            review_paths,
        )
        self.assertIn(
            "校園/2026-05-29_北教大女廁驚見「2台針孔」對準蹲式馬桶.md",
            review_paths,
        )


if __name__ == "__main__":
    unittest.main()
