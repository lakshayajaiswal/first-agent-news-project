"""
Unit tests for multi-level progressive deduplication.
"""

import unittest
from datetime import datetime, timezone
from src.deduplication.matcher import DeduplicationService, calculate_jaccard_similarity
from src.normalization.content import compute_content_hash


class TestDeduplication(unittest.TestCase):

    def setUp(self):
        self.dedup = DeduplicationService(title_similarity_threshold=0.70)
        self.existing_articles = [
            {
                "id": "art-001",
                "canonical_url": "https://vtu.ac.in/circulars/exam-2025.html",
                "content_hash": compute_content_hash("VTU Exam Timetable 2025 details"),
                "title": "VTU Revised Examination Timetable 2025 Scheme",
                "published_at": "2026-08-25T10:00:00+00:00",
            },
            {
                "id": "art-002",
                "canonical_url": "https://blog.google/technology/ai/gemini-2-5-flash",
                "content_hash": compute_content_hash("Gemini 2.5 Flash release"),
                "title": "Google DeepMind Announces Gemini 2.5 Flash",
                "published_at": "2026-08-25T08:00:00+00:00",
            }
        ]

    def test_exact_canonical_url_match(self):
        result = self.dedup.check_duplicate(
            candidate_canonical_url="https://vtu.ac.in/circulars/exam-2025.html?utm_source=twitter",
            candidate_content_hash="different_content_hash",
            candidate_title="A New Title",
            candidate_published_at=datetime.now(timezone.utc),
            existing_articles=self.existing_articles
        )
        self.assertTrue(result.is_duplicate)
        self.assertEqual(result.duplicate_type, "exact_url")
        self.assertEqual(result.matched_article_id, "art-001")

    def test_exact_content_hash_match(self):
        result = self.dedup.check_duplicate(
            candidate_canonical_url="https://mirrorsite.com/vtu/mirror-exam.html",
            candidate_content_hash=compute_content_hash("VTU Exam Timetable 2025 details"),
            candidate_title="Mirror Copy of VTU Notice",
            candidate_published_at=datetime.now(timezone.utc),
            existing_articles=self.existing_articles
        )
        self.assertTrue(result.is_duplicate)
        self.assertEqual(result.duplicate_type, "exact_hash")
        self.assertEqual(result.matched_article_id, "art-001")

    def test_near_title_similarity_match(self):
        result = self.dedup.check_duplicate(
            candidate_canonical_url="https://newsportal.com/gemini-2-5-flash-deepmind",
            candidate_content_hash="unique_hash_12345",
            candidate_title="Google DeepMind Releases Gemini 2.5 Flash",
            candidate_published_at=datetime.fromisoformat("2026-08-25T09:00:00+00:00"),
            existing_articles=self.existing_articles
        )
        self.assertTrue(result.is_duplicate)
        self.assertEqual(result.duplicate_type, "near_title")
        self.assertEqual(result.matched_article_id, "art-002")

    def test_non_duplicate_item(self):
        result = self.dedup.check_duplicate(
            candidate_canonical_url="https://nvd.nist.gov/vuln/detail/CVE-2026-9999",
            candidate_content_hash="cve_unique_hash_9999",
            candidate_title="Critical Buffer Overflow Vulnerability in OpenSSL",
            candidate_published_at=datetime.now(timezone.utc),
            existing_articles=self.existing_articles
        )
        self.assertFalse(result.is_duplicate)


if __name__ == "__main__":
    unittest.main()
