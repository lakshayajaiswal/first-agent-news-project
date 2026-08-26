"""
Unit tests for Supabase database migrations, schema verification, and models.
"""

import unittest
from src.storage.schema_validator import verify_schema_integrity, validate_migration_sql, EXPECTED_TABLES
from src.storage.supabase_client import SupabaseStorageClient
from src.storage.models import SourceModel, ArticleModel, Category, SourceType, ArticleStatus


class TestStorageSchema(unittest.TestCase):

    def test_schema_integrity(self):
        report = verify_schema_integrity()
        self.assertTrue(report["valid"], f"Missing tables: {report.get('missing_tables')}")
        self.assertEqual(len(report["missing_tables"]), 0)
        self.assertGreaterEqual(report["total_migrations"], 2)
        self.assertGreaterEqual(report["total_indexes"], 5)
        self.assertTrue(report["has_seed_file"])
        self.assertGreater(report["seed_sources_count"], 0)

    def test_supabase_client_mock_layer(self):
        client = SupabaseStorageClient()
        
        # Test Source Upsert
        src = SourceModel(
            name="VTU Main",
            category=Category.VTU,
            url="https://vtu.ac.in/feed",
            source_type=SourceType.HTML,
            adapter_key="vtu_circulars_adapter",
        )
        saved_src = client.upsert_source(src)
        self.assertEqual(saved_src["name"], "VTU Main")
        
        # Test Article Insert & Duplicate Idempotency
        art = ArticleModel(
            title="VTU Circular 2025",
            canonical_url="https://vtu.ac.in/circulars/123",
            source_url="https://vtu.ac.in/circulars/123?utm_source=tg",
            category=Category.VTU,
            content_hash="hash12345",
            source_id=saved_src["id"],
        )
        saved_art1 = client.insert_article(art)
        saved_art2 = client.insert_article(art)
        self.assertEqual(saved_art1["id"], saved_art2["id"])

        # Test Notification Idempotency
        notif1, created1 = client.create_or_get_notification(
            article_id=saved_art1["id"],
            channel="discord",
            message_type="daily_digest"
        )
        self.assertTrue(created1)

        notif2, created2 = client.create_or_get_notification(
            article_id=saved_art1["id"],
            channel="discord",
            message_type="daily_digest"
        )
        self.assertFalse(created2)
        self.assertEqual(notif1["id"], notif2["id"])


if __name__ == "__main__":
    unittest.main()
