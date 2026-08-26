"""
Unit tests for the BaseCollector lifecycle, extraction, and normalization pipeline.
"""

import unittest
from datetime import datetime, timezone
from src.collectors.base import BaseCollector
from src.collectors.models import RawSourceItem
from src.storage.models import Category, SourceType


class ConcreteDummyCollector(BaseCollector):
    adapter_key = "concrete_dummy"
    category = Category.VTU
    source_type = SourceType.HTML

    def fetch(self):
        return [
            {
                "title": "  VTU Revised Scheme Notification 2025  ",
                "link": "/circulars/scheme_2025.html?utm_source=news",
                "body": "Official details on first semester syllabus for 2025 engineering scheme.",
            }
        ]

    def extract(self, raw_data):
        items = []
        for d in raw_data:
            items.append(
                RawSourceItem(
                    title=d["title"],
                    url=d["link"],
                    raw_content=d["body"],
                    source_name=self.name,
                    category=self.category,
                    published_at=datetime.now(timezone.utc)
                )
            )
        return items


class TestCollectorInterface(unittest.TestCase):

    def test_collector_lifecycle(self):
        collector = ConcreteDummyCollector(
            source_id="src-vtu-01",
            name="VTU Official Portal",
            url="https://vtu.ac.in/en/",
            trust_level=5
        )

        candidates = collector.collect()
        self.assertEqual(len(candidates), 1)

        candidate = candidates[0]
        self.assertEqual(candidate.title, "VTU Revised Scheme Notification 2025")
        self.assertEqual(candidate.canonical_url, "https://vtu.ac.in/circulars/scheme_2025.html")
        self.assertEqual(candidate.category, Category.VTU)
        self.assertEqual(len(candidate.content_hash), 64)
        self.assertIsNotNone(candidate.published_at)


if __name__ == "__main__":
    unittest.main()
