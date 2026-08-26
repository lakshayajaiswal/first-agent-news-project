"""
Integration test for Multi-Domain Ingestion Pipeline across VTU, AI, Development, and Cybersecurity sources.
"""

import unittest
from src.collectors.registry import get_source_registry
from src.pipeline.ingest import IngestionPipeline
from src.storage.models import SourceModel, Category, SourceType


class TestMultiDomainPipeline(unittest.TestCase):

    def setUp(self):
        self.registry = get_source_registry()
        self.pipeline = IngestionPipeline()

    def test_registry_has_all_adapters(self):
        registered = self.registry.list_adapters()
        self.assertIn("vtu_circulars_adapter", registered)
        self.assertIn("vtu_exams_adapter", registered)
        self.assertIn("vtu_academic_adapter", registered)
        self.assertIn("rss_feed_adapter", registered)
        self.assertIn("cisa_kev_adapter", registered)
        self.assertIn("nist_nvd_adapter", registered)
        self.assertIn("hacker_news_adapter", registered)
        self.assertIn("html_feed_adapter", registered)

    def test_multi_domain_sources_execution(self):
        sources = [
            SourceModel(
                name="VTU Official Circulars",
                category=Category.VTU,
                source_type=SourceType.HTML,
                url="mock://vtu/circulars",
                adapter_key="vtu_circulars_adapter",
                trust_level=5
            ),
            SourceModel(
                name="Google AI Updates",
                category=Category.AI,
                source_type=SourceType.FEED,
                url="mock://google-ai/rss",
                adapter_key="rss_feed_adapter",
                trust_level=5
            ),
            SourceModel(
                name="Hacker News Top Tech",
                category=Category.DEVELOPMENT,
                source_type=SourceType.JSON,
                url="mock://hn/top",
                adapter_key="hacker_news_adapter",
                trust_level=4
            ),
            SourceModel(
                name="CISA KEV Alerts",
                category=Category.CYBERSECURITY,
                source_type=SourceType.JSON,
                url="mock://cisa/kev",
                adapter_key="cisa_kev_adapter",
                trust_level=5
            ),
            SourceModel(
                name="NIST NVD High Severity CVEs",
                category=Category.CYBERSECURITY,
                source_type=SourceType.JSON,
                url="mock://nvd/cves",
                adapter_key="nist_nvd_adapter",
                trust_level=5
            )
        ]

        result = self.pipeline.run(sources=sources)
        self.assertGreater(result["discovered"], 0)
        self.assertGreater(result["accepted"], 0)
        self.assertGreater(result["summarized"], 0)
        self.assertEqual(result["sources_failed"], 0)


if __name__ == "__main__":
    unittest.main()
