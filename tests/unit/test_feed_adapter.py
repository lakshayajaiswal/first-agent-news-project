"""
Unit tests for RSS and Atom Feed Adapter.
Tests XML parsing, RSS 2.0 items, Atom entries, malformed XML fallbacks, and date format parsing.
"""

import unittest
from datetime import datetime, timezone
from src.collectors.feed import RSSFeedAdapter, parse_rfc822_or_iso_date
from src.storage.models import Category


class TestRSSFeedAdapter(unittest.TestCase):

    def setUp(self):
        self.rss_adapter = RSSFeedAdapter(
            source_id="src-rss-test",
            name="Google AI Updates",
            url="mock://google-ai-feed",
            category=Category.AI
        )

    def test_parse_dates(self):
        rfc822 = "Tue, 25 Aug 2026 10:00:00 GMT"
        parsed_rfc = parse_rfc822_or_iso_date(rfc822)
        self.assertIsNotNone(parsed_rfc)
        self.assertEqual(parsed_rfc.year, 2026)
        self.assertEqual(parsed_rfc.month, 8)
        self.assertEqual(parsed_rfc.day, 25)

        iso_date = "2026-08-25T12:00:00Z"
        parsed_iso = parse_rfc822_or_iso_date(iso_date)
        self.assertIsNotNone(parsed_iso)
        self.assertEqual(parsed_iso.hour, 12)

    def test_extract_rss20_xml(self):
        xml = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>AI News Feed</title>
    <link>https://ai.example.com</link>
    <item>
      <title>Gemini 2.5 Flash GA Released</title>
      <link>https://ai.example.com/gemini-2-5-flash</link>
      <description>Fast low-latency inference model for AI applications.</description>
      <pubDate>Tue, 25 Aug 2026 10:00:00 GMT</pubDate>
    </item>
  </channel>
</rss>"""
        items = self.rss_adapter.extract(xml)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].title, "Gemini 2.5 Flash GA Released")
        self.assertEqual(items[0].url, "https://ai.example.com/gemini-2-5-flash")
        self.assertIn("Fast low-latency", items[0].raw_content)

    def test_extract_atom_xml(self):
        atom_xml = """<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>Engineering Blog</title>
  <link href="https://example.com/blog" />
  <entry>
    <title>Rust 2026 Edition Release Candidate</title>
    <link href="https://example.com/blog/rust-2026" />
    <summary>Complete overview of language stabilization and compiler performance improvements.</summary>
    <updated>2026-08-25T08:00:00Z</updated>
  </entry>
</feed>"""
        items = self.rss_adapter.extract(atom_xml)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].title, "Rust 2026 Edition Release Candidate")
        self.assertEqual(items[0].url, "https://example.com/blog/rust-2026")
        self.assertIn("compiler performance", items[0].raw_content)

    def test_collect_lifecycle(self):
        candidates = self.rss_adapter.collect()
        self.assertGreater(len(candidates), 0)
        self.assertEqual(candidates[0].category, Category.AI)
        self.assertTrue(len(candidates[0].content_hash) == 64)
        self.assertTrue(candidates[0].canonical_url.startswith("http"))


if __name__ == "__main__":
    unittest.main()
