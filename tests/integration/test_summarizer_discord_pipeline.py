"""
Integration test for Grounded Summarization and Discord Notification Delivery in Ingestion Pipeline.
"""

import unittest
from src.pipeline.ingest import IngestionPipeline
from src.ai.classifier_client import AIClassifierClient
from src.ai.summarizer_client import AISummarizerClient
from src.discord.discord_client import DiscordClient
from src.storage.supabase_client import SupabaseStorageClient


class TestSummarizerDiscordPipeline(unittest.TestCase):

    def setUp(self):
        self.storage = SupabaseStorageClient()
        self.classifier = AIClassifierClient(api_key=None)
        self.summarizer = AISummarizerClient(api_key=None)
        self.discord = DiscordClient(
            webhook_url="https://discord.com/api/webhooks/mock/123/general",
            urgent_webhook_url="https://discord.com/api/webhooks/mock/123/urgent",
            storage_client=self.storage,
            dry_run=True
        )
        self.pipeline = IngestionPipeline(
            storage_client=self.storage,
            classifier_client=self.classifier,
            summarizer_client=self.summarizer,
            discord_client=self.discord
        )

    def test_end_to_end_summarization_and_urgent_alert(self):
        source = {
            "id": "src-vtu-test",
            "name": "VTU Official Circulars",
            "category": "vtu",
            "url": "https://vtu.ac.in/circulars",
            "source_type": "html",
            "adapter_key": "vtu_circulars_adapter",
            "enabled": True,
            "trust_level": 5
        }

        stats = self.pipeline.run_source_ingestion(source)

        self.assertGreater(stats["discovered"], 0)
        self.assertGreater(stats["accepted"], 0)
        self.assertGreater(stats["summarized"], 0)
        self.assertEqual(stats["accepted"], stats["summarized"])

        # Verify summary stored in Supabase mock storage
        accepted_item = [a for a in stats["articles"] if a["classification"]["decision"] == "accept"][0]
        article_id = accepted_item["article"]["id"]
        
        stored_summary = self.storage.get_summary(article_id)
        self.assertIsNotNone(stored_summary)
        self.assertTrue(len(stored_summary["headline"]) > 0)
        self.assertTrue(len(stored_summary["what_happened"]) > 0)
        self.assertTrue(len(stored_summary["why_it_matters"]) > 0)

        # Generate and test daily digest delivery
        digest_res = self.pipeline.generate_and_send_daily_digest(digest_date="25 AUG 2026")
        self.assertEqual(digest_res["status"], "sent")
        self.assertTrue(digest_res["delivered"])


if __name__ == "__main__":
    unittest.main()
