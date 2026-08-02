from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parents[1]
SCRIPT_PATH = SCRIPT_DIR / "news-context.py"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
SPEC = importlib.util.spec_from_file_location("news_context", SCRIPT_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"Unable to load {SCRIPT_PATH}")
CONTEXT_MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = CONTEXT_MODULE
SPEC.loader.exec_module(CONTEXT_MODULE)


class NewsContextTest(unittest.TestCase):
    def test_default_context_is_compact_deterministic_and_policy_driven(self) -> None:
        repo_root = SCRIPT_DIR.parent
        news_dir = repo_root / "source-code/content/news"
        policy = CONTEXT_MODULE.load_policy(CONTEXT_MODULE.DEFAULT_POLICY_PATH)

        first = CONTEXT_MODULE.render_context(news_dir, policy)
        second = CONTEXT_MODULE.render_context(news_dir, policy)

        self.assertEqual(first, second)
        self.assertTrue(first.startswith("NEWS_CONTEXT\t2\n"))
        self.assertIn("editorial\t獨立分類/警界醜聞/檢察官\t1\trequired", first)
        self.assertIn("警察\t檢警法,獨立分類/警界醜聞/警察\treview", first)
        self.assertNotIn("[all_slugs]", first)
        self.assertLess(len(first.splitlines()), 400)

    def test_exact_slug_check_and_optional_full_listing(self) -> None:
        repo_root = SCRIPT_DIR.parent
        news_dir = repo_root / "source-code/content/news"
        policy = CONTEXT_MODULE.load_policy(CONTEXT_MODULE.DEFAULT_POLICY_PATH)
        articles, errors = CONTEXT_MODULE.read_articles(news_dir)
        self.assertEqual(errors, [])
        existing = next(article for article in articles if article.slug)

        self.assertTrue(
            CONTEXT_MODULE.check_slug(news_dir, existing.slug).startswith("EXISTS\t")
        )
        self.assertEqual(
            CONTEXT_MODULE.check_slug(news_dir, "definitely-not-a-real-news-slug"),
            "AVAILABLE\tdefinitely-not-a-real-news-slug",
        )
        self.assertIn(
            "[all_slugs]",
            CONTEXT_MODULE.render_context(news_dir, policy, include_all_slugs=True),
        )


if __name__ == "__main__":
    unittest.main()
