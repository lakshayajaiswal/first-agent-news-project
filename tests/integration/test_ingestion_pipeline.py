"""
Integration tests verifying the complete Ingestion -> Deduplication -> AI Classification pipeline.
"""

import unittest
from src.storage.supabase_client import SupabaseStorageClient
from src.ai.classifier_client import AIClassifierClient
from src.deduplication.matcher import DeduplicationService
from src.pipeline.ingest import IngestionPipeline


class TestIngestionPipeline(unittest.TestCase):

    def setUp(self):
        self.storage = SupabaseStorageClient()
        self.classifier = AIClassifierClient()
        self.dedup = DeduplicationService(title_similarity_threshold=0.70)
        self.pipeline = IngestionPipeline(
            storage_client=self.storage,
            classifier_client=self.classifier,
            dedup_service=self.dedup
        )

    def test_end_to_end_vtu_ingestion_with_classification_and_deduplication(self):
        source_record = {
            "id": "src-vtu-integration",
            "name": "VTU Official Circulars",
            "category": "vtu",
            "url": "https://vtu.ac.in/circulars",
            "source_type": "html",
            "adapter_key": "vtu_circulars_adapter",
            "enabled": True,
            "trust_level": 5
        }

        # 1. First Run: Process items
        stats1 = self.pipeline.run_source_ingestion(source_record)
        self.assertGreater(stats1["discovered"], 0)
        self.assertGreater(stats1["accepted"], 0)
        self.assertEqual(stats1["duplicates"], 0)
        self.assertEqual(stats1["errors"], 0)

        # Verify articles saved in storage
        recent_articles = self.storage.get_recent_articles(limit=50)
        self.assertGreater(len(recent_articles), 0)

        # Verify classification records exist for accepted articles
        saved_article_id = stats1["articles"][0]["article"]["id"]
        classifications = [c for c in self.storage._classifications.values() if c["article_id"] == saved_article_id]
        self.assertEqual(len(classifications), 1)
        self.assertIn(classifications[0]["decision"], ["accept", "reject"])

        # 2. Second Run: Exact same source -> All items should be caught as Level 1/2 duplicates
        stats2 = self.pipeline.run_source_ingestion(source_record)
        self.assertEqual(stats2["discovered"], stats1["discovered"])
        self.assertEqual(stats2["duplicates"], stats1["discovered"])
        self.assertEqual(stats2["accepted"], 0)
        self.assertEqual(stats2["rejected"], 0)

    def test_full_pipeline_audit_run(self):
        result = self.pipeline.run_full_pipeline()
        self.assertIsNotNone(result["run_id"])
        self.assertEqual(result["status"], "success")
        self.assertGreaterEqual(result["discovered"], 1)

        # Check fetch_runs record in storage
        completed_run = self.storage._fetch_runs[result["run_id"]]
        self.assertEqual(completed_run["status"], "success")
        self.assertIsNotNone(completed_run["finished_at"])


if __name__ == "__main__":
    unittest.main()
