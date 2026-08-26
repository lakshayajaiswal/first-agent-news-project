"""
Unit tests for Hacker News Top Stories Adapter and HTML Changelog Scraper.
Tests score thresholding, topic metadata, and HTML article block extraction.
"""

import unittest
from src.collectors.dev_ai import HackerNewsTopAdapter, HTMLChangelogAdapter
from src.storage.models import Category


class TestDevAIAdapters(unittest.TestCase):

    def test_hacker_news_top_adapter(self):
        adapter = HackerNewsTopAdapter(
            source_id="src-hn-top",
            name="Hacker News Top",
            url="mock://hn-top",
            min_score=100
        )
        candidates = adapter.collect()
        self.assertEqual(len(candidates), 2)
        
        first = candidates[0]
        self.assertEqual(first.category, Category.DEVELOPMENT)
        self.assertIn("SQLite 3.47", first.title)
        self.assertIn("sqlite.org", first.canonical_url)
        self.assertIn("Points: 380", first.content)

    def test_html_changelog_adapter(self):
        adapter = HTMLChangelogAdapter(
            source_id="src-anthropic-news",
            name="Anthropic Research & News",
            url="mock://anthropic-news",
            category=Category.AI
        )
        candidates = adapter.collect()
        self.assertEqual(len(candidates), 2)
        
        first = candidates[0]
        self.assertEqual(first.category, Category.AI)
        self.assertIn("Claude 3.7 Sonnet", first.title)
        self.assertIn("anthropic.com", first.canonical_url)
        self.assertIn("reasoning", first.content.lower())


if __name__ == "__main__":
    unittest.main()
