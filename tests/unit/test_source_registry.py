"""
Unit tests for the Source Registry and dynamic adapter instantiation.
"""

import unittest
from typing import Any, List
from src.collectors.base import BaseCollector
from src.collectors.models import RawSourceItem
from src.collectors.registry import SourceRegistry
from src.storage.models import SourceModel, Category, SourceType


class MockTestAdapter(BaseCollector):
    adapter_key = "mock_test_adapter"
    category = Category.VTU
    source_type = SourceType.HTML

    def fetch(self) -> Any:
        return "<html><body>Sample</body></html>"

    def extract(self, raw_data: Any) -> List[RawSourceItem]:
        return [
            RawSourceItem(
                title="Mock VTU Circular 2025",
                url="https://vtu.ac.in/circulars/mock.html",
                raw_content="Content of mock circular",
                source_name="Mock VTU",
                category=Category.VTU
            )
        ]


class TestSourceRegistry(unittest.TestCase):

    def setUp(self):
        self.registry = SourceRegistry()

    def test_register_and_create_collector(self):
        self.registry.register("mock_test_adapter", MockTestAdapter)
        self.assertTrue(self.registry.has_adapter("mock_test_adapter"))

        source_model = SourceModel(
            name="VTU Mock Source",
            category=Category.VTU,
            url="https://vtu.ac.in/feed",
            source_type=SourceType.HTML,
            adapter_key="mock_test_adapter",
        )

        collector = self.registry.create_collector(source_model)
        self.assertIsInstance(collector, MockTestAdapter)
        self.assertEqual(collector.name, "VTU Mock Source")

    def test_create_collector_missing_adapter_raises(self):
        source_model = SourceModel(
            name="Unknown Source",
            category=Category.AI,
            url="https://ai.example.com",
            source_type=SourceType.FEED,
            adapter_key="unregistered_adapter_key",
        )
        with self.assertRaises(KeyError):
            self.registry.create_collector(source_model)

    def test_health_metric_recording(self):
        metric = self.registry.record_health_metric(
            source_id="src-101",
            source_name="VTU Feed",
            success=True,
            items_discovered=5,
            items_accepted=3
        )
        self.assertEqual(metric.total_runs, 1)
        self.assertEqual(metric.successful_runs, 1)
        self.assertEqual(metric.consecutive_failures, 0)
        self.assertEqual(metric.items_discovered, 5)

        # Record a failure
        metric_fail = self.registry.record_health_metric(
            source_id="src-101",
            source_name="VTU Feed",
            success=False,
            error="Connection timed out"
        )
        self.assertEqual(metric_fail.total_runs, 2)
        self.assertEqual(metric_fail.failed_runs, 1)
        self.assertEqual(metric_fail.consecutive_failures, 1)


if __name__ == "__main__":
    unittest.main()
