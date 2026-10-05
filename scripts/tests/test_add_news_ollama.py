from __future__ import annotations

import sys
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import add_news_ollama as module  # noqa: E402


SAMPLE_HTML = """
<html><head>
<title>颱風假亂象！雇主逼上班 勞動部：可拒絕 | 示範新聞網</title>
<meta property="og:title" content="颱風假亂象！雇主逼上班 勞動部：可拒絕">
<meta property="article:published_time" content="2026-09-18T08:30:00+08:00">
<meta name="description" content="勞動部指出，颱風假期間雇主不得強迫出勤。">
<script type="application/ld+json">{"@type":"NewsArticle","headline":"颱風假亂象！雇主逼上班","datePublished":"2026-09-18"}</script>
<script>var challenge = "2020-01-01";</script>
</head><body>
<nav><li>首頁</li></nav>
<h1>颱風假亂象！雇主逼上班 勞動部：可拒絕</h1>
<article>
<p>""" + "勞動部今天表示，颱風假期間雇主若強迫勞工出勤，勞工可以拒絕，且不得因此受到不利處分。" * 6 + """</p>
<p>相關規定依《天然災害發生事業單位勞工出勤管理及工資給付要點》辦理。</p>
</article>
<footer><p>© 示範新聞網</p></footer>
</body></html>
"""


class SlugDerivationTest(unittest.TestCase):
    def test_known_outlet_conventions(self) -> None:
        cases = {
            "https://udn.com/news/story/7320/9587400": "udn-7320-9587400",
            "https://www.storm.mg/article/11158013": "storm-11158013",
            "https://news.ltn.com.tw/news/society/breakingnews/4567890": "ltn-4567890",
            "https://www.setn.com/News.aspx?NewsID=1650622&utm_source=x": "setn-1650622",
            "https://www.ettoday.net/news/20250506/2955389.htm": "ettoday-2955389",
            "https://news.cnyes.com/news/id/6063858": "cnyes-6063858",
            "https://www.chinatimes.com/realtimenews/20260708003489-260402?chdtv": (
                "chinatimes-20260708003489-260402"
            ),
            "https://news.mydrivers.com/1/1135/1135015.htm": "mydrivers-1-1135-1135015",
            "https://www.ftvnews.com.tw/news/detail/2025502S07M1": "ftvnews-2025502S07M1",
            "https://news.pts.org.tw/article/814538": "pts-814538",
            "https://www.bbc.com/zhongwen/articles/cp8yy1z6g3lo/trad": "bbc-cp8yy1z6g3lo",
        }
        for url, expected in cases.items():
            with self.subTest(url=url):
                self.assertEqual(module.derive_slug(url), expected)

    def test_keep_dates_variant_adds_distinguishing_segment(self) -> None:
        url = "https://www.ettoday.net/news/20250506/2955389.htm"
        self.assertEqual(module.derive_slug(url, keep_dates=True), "ettoday-20250506-2955389")

    def test_slug_override_must_come_from_url(self) -> None:
        url = "https://tw.nextapple.com/local/20250523/CEA519302FE817ACC1B84B3670B8CE5C"
        self.assertTrue(
            module.slug_override_is_valid(
                "nextapple-20250523-CEA519302FE817ACC1B84B3670B8CE5C", url
            )
        )
        self.assertFalse(module.slug_override_is_valid("nextapple-99999", url))
        self.assertFalse(module.slug_override_is_valid("udn-20250523", url))
        self.assertFalse(module.slug_override_is_valid("nextapple", url))


class PageEvidenceTest(unittest.TestCase):
    def test_extracts_title_date_description_and_body(self) -> None:
        evidence = module.extract_page(SAMPLE_HTML)

        self.assertTrue(evidence.readable)
        self.assertEqual(evidence.title_candidates[0], "颱風假亂象！雇主逼上班 勞動部：可拒絕")
        self.assertIn("颱風假亂象！雇主逼上班", evidence.title_candidates)
        self.assertEqual(evidence.date_candidates[0], "2026-09-18")
        self.assertNotIn("2020-01-01", evidence.date_candidates)
        self.assertEqual(evidence.description, "勞動部指出，颱風假期間雇主不得強迫出勤。")
        self.assertIn("勞動部今天表示", evidence.text)
        self.assertNotIn("challenge", evidence.text)

    def test_challenge_page_is_not_readable(self) -> None:
        html = "<html><head><title>Just a moment...</title></head><body><p>" + "x" * 500 + "</p></body></html>"
        self.assertFalse(module.extract_page(html).readable)

    def test_normalize_date_forms(self) -> None:
        self.assertEqual(module.normalize_date("2026-09-19T10:20:00+08:00"), "2026-09-19")
        self.assertEqual(module.normalize_date("2026年9月19日 10:20"), "2026-09-19")
        self.assertEqual(module.normalize_date("發布 2026/09/19"), "2026-09-19")
        self.assertEqual(module.normalize_date("20260919"), "2026-09-19")
        self.assertIsNone(module.normalize_date("2026-13-40"))
        self.assertIsNone(module.normalize_date("none"))

    def test_strip_site_suffix_only_removes_short_tail(self) -> None:
        self.assertEqual(module.strip_site_suffix("標題 | 聯合新聞網"), "標題")
        self.assertEqual(module.strip_site_suffix("A | B | 記者"), "A | B")
        long_tail = "標題 - " + "尾" * 30
        self.assertEqual(module.strip_site_suffix(long_tail), long_tail)


class AnswerValidationTest(unittest.TestCase):
    def setUp(self) -> None:
        policy = module.load_policy(module.POLICY_TOML)
        self.sections = {
            section.path.as_posix(): section
            for section in policy.sections
            if section.allow_articles
        }
        self.evidence = module.extract_page(SAMPLE_HTML)
        self.url = "https://www.example.com/news/12345"
        self.answer = {
            "title": "颱風假亂象！雇主逼上班 勞動部：可拒絕 | 示範新聞網",
            "date": "2026-09-18",
            "description": None,
            "destination": "勞權",
            "tags": ["勞權", "勞權", "政府"],
            "filename_phrase": "雇主逼上班/勞動部：可拒絕",
            "slug": "example-12345",
            "needs_review": False,
            "review_reason": "",
        }

    def validate(self, **overrides: object):
        answer = {**self.answer, **overrides}
        return module.validate_answer(
            answer,
            evidence=self.evidence,
            url=self.url,
            slug_candidate="example-12345",
            policy_sections=self.sections,
        )

    def test_accepts_and_normalizes_a_good_answer(self) -> None:
        fields, bucket, _ = self.validate()
        self.assertEqual(bucket, "")
        assert fields is not None
        self.assertEqual(fields["title"], "颱風假亂象！雇主逼上班 勞動部：可拒絕")
        self.assertEqual(fields["tags"], ["勞權", "政府"])
        self.assertEqual(fields["filename"], "2026-09-18_雇主逼上班／勞動部：可拒絕.md")
        self.assertEqual(fields["slug"], "example-12345")

    def test_rejects_todays_date_when_not_in_evidence(self) -> None:
        import datetime as dt

        _, bucket, detail = self.validate(date=dt.date.today().isoformat())
        self.assertEqual(bucket, "content-unreadable")
        self.assertIn("today", detail)

    def test_review_request_lands_in_classification_needed(self) -> None:
        _, bucket, detail = self.validate(needs_review=True, review_reason="勞權 vs 政府")
        self.assertEqual(bucket, "classification-needed")
        self.assertEqual(detail, "勞權 vs 政府")

    def test_editorial_destination_gets_required_tag(self) -> None:
        fields, bucket, _ = self.validate(
            destination="獨立分類/警界醜聞/警察", tags=["毒品"]
        )
        self.assertEqual(bucket, "")
        assert fields is not None
        self.assertEqual(fields["tags"], ["警察", "毒品"])

    def test_umbrella_without_subject_tag_needs_classification(self) -> None:
        _, bucket, _ = self.validate(destination="檢警法", tags=["社會"])
        self.assertEqual(bucket, "classification-needed")

    def test_invalid_slug_override_falls_back_to_candidate(self) -> None:
        fields, bucket, _ = self.validate(slug="example-99999")
        self.assertEqual(bucket, "")
        assert fields is not None
        self.assertEqual(fields["slug"], "example-12345")


class ArchiveOutputTest(unittest.TestCase):
    def test_parses_all_statuses(self) -> None:
        output = "OK https://a/1 https://web.archive.org/web/1/https://a/1\nDUP https://a/2 news/x.md\nFAIL https://a/3\nnoise\n"
        items = module.parse_archive_output(output)
        self.assertEqual([item.bucket for item in items], ["ok", "already-archived", "archive-failed"])
        self.assertEqual(items[0].archived_url, "https://web.archive.org/web/1/https://a/1")
        self.assertEqual(items[1].detail, "news/x.md")


if __name__ == "__main__":
    unittest.main()
