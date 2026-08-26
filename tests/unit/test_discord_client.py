"""
Unit tests for Discord Webhook Client.
Tests urgent alert delivery, daily digest aggregation, message chunking, and idempotency tracking.
"""

import unittest
from unittest.mock import patch, MagicMock
from src.discord.discord_client import DiscordClient
from src.storage.supabase_client import SupabaseStorageClient


class TestDiscordClient(unittest.TestCase):

    def setUp(self):
        self.storage = SupabaseStorageClient()
        self.client = DiscordClient(
            webhook_url="https://discord.com/api/webhooks/mock/123/abc",
            urgent_webhook_url="https://discord.com/api/webhooks/mock/123/urgent",
            storage_client=self.storage,
            dry_run=True
        )

    def test_send_urgent_alert_dry_run(self):
        article = {
            "id": "art-001",
            "category": "cybersecurity",
            "title": "Critical RCE in OpenSSH",
            "canonical_url": "https://nvd.nist.gov/vuln/detail/CVE-2026-3392",
            "source_url": "https://nvd.nist.gov/vuln/detail/CVE-2026-3392"
        }
        summary = {
            "headline": "Critical RCE in OpenSSH Server (CVE-2026-3392)",
            "what_happened": "Unauthenticated attackers can execute code prior to login.",
            "why_it_matters": "Actively exploited in the wild.",
            "action_required": "Patch immediately to version 9.8p1.",
        }

        result = self.client.send_urgent_alert(article=article, summary=summary)
        self.assertEqual(result["status"], "sent")
        self.assertTrue(result["delivered"])
        self.assertEqual(result["article_id"], "art-001")

        # Verify idempotency - second call should return already_sent
        duplicate_res = self.client.send_urgent_alert(article=article, summary=summary)
        self.assertEqual(duplicate_res["status"], "already_sent")
        self.assertFalse(duplicate_res["delivered"])

    def test_send_daily_digest_dry_run(self):
        items = {
            "vtu": [
                {
                    "headline": "2025 Scheme 1st Sem Syllabus Notified",
                    "what_happened": "Detailed syllabus released for CSE.",
                    "why_it_matters": "Affects 1st semester coursework.",
                    "action_required": "Review guidelines.",
                    "source_url": "https://vtu.ac.in/circulars/1042"
                }
            ],
            "ai": [
                {
                    "headline": "Gemini 2.5 Flash Released",
                    "what_happened": "Sub-second inference model available.",
                    "why_it_matters": "Real-time AI workflows.",
                    "source_url": "https://blog.google/gemini"
                }
            ]
        }

        result = self.client.send_daily_digest(
            items_by_category=items,
            accepted_count=2,
            rejected_count=10,
            duplicate_count=1,
            digest_date="25 AUG 2026"
        )
        self.assertEqual(result["status"], "sent")
        self.assertTrue(result["delivered"])
        self.assertGreaterEqual(result["chunks_sent"], 1)

    def test_message_chunking_exceeding_limit(self):
        long_paragraph = "This is a long sentence explaining an event in detail.\n" * 50
        chunks = self.client._chunk_message(long_paragraph, max_length=500)
        self.assertGreater(len(chunks), 1)
        for chunk in chunks:
            self.assertLessEqual(len(chunk), 500)


if __name__ == "__main__":
    unittest.main()
