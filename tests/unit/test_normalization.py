"""
Unit tests for URL canonicalization, text cleaning, and SHA-256 hashing.
"""

import unittest
from src.normalization.url import canonicalize_url
from src.normalization.content import clean_text, normalize_title, compute_content_hash


class TestNormalization(unittest.TestCase):

    def test_canonicalize_url_strips_tracking_params(self):
        raw_url = "https://VTU.ac.in/en/circulars/exam.html?utm_source=telegram&utm_medium=broadcast&page=1&fbclid=IwAR123"
        expected = "https://vtu.ac.in/en/circulars/exam.html?page=1"
        self.assertEqual(canonicalize_url(raw_url), expected)

    def test_canonicalize_url_resolves_relative_and_fragments(self):
        relative = "/pdf/exam_timetable.pdf#page=2"
        base = "https://vtu.ac.in/en/notifications/"
        expected = "https://vtu.ac.in/pdf/exam_timetable.pdf"
        self.assertEqual(canonicalize_url(relative, base_url=base), expected)

    def test_canonicalize_url_sorts_query_params(self):
        url1 = "https://example.com/api?b=2&a=1"
        url2 = "https://example.com/api?a=1&b=2"
        self.assertEqual(canonicalize_url(url1), canonicalize_url(url2))

    def test_clean_text_normalizes_whitespace(self):
        dirty = "  VTU   Notification \n\n  2025 \t Scheme  "
        self.assertEqual(clean_text(dirty), "VTU Notification 2025 Scheme")

    def test_normalize_title(self):
        raw = "Revised VTU Examination Timetable 2025! - Official Portal"
        normalized = normalize_title(raw)
        self.assertEqual(normalized, "revised vtu examination timetable 2025")

    def test_content_hashing_is_deterministic(self):
        text_a = "Visvesvaraya Technological University Circular"
        text_b = "  Visvesvaraya   Technological University Circular  "
        hash_a = compute_content_hash(text_a)
        hash_b = compute_content_hash(text_b)
        self.assertEqual(hash_a, hash_b)
        self.assertEqual(len(hash_a), 64)


if __name__ == "__main__":
    unittest.main()
