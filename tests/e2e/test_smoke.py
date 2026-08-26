"""
Smoke test verifying component wiring and end-to-end importability.
"""

import unittest
from src.config.settings import get_settings
from src.config.logging_config import setup_logger
from src.storage.supabase_client import get_storage_client
from src.storage.schema_validator import verify_schema_integrity
from src.collectors.registry import get_source_registry
from src.deduplication.matcher import DeduplicationService
from src.normalization.url import canonicalize_url
from src.normalization.content import compute_content_hash


class TestSmoke(unittest.TestCase):

    def test_system_components_wiring(self):
        settings = get_settings()
        self.assertIsNotNone(settings)

        logger = setup_logger("test_smoke")
        self.assertIsNotNone(logger)

        client = get_storage_client()
        self.assertIsNotNone(client)

        registry = get_source_registry()
        self.assertIsNotNone(registry)

        dedup = DeduplicationService()
        self.assertIsNotNone(dedup)

        schema_status = verify_schema_integrity()
        self.assertTrue(schema_status["valid"])

        test_url = canonicalize_url("https://vtu.ac.in/circulars/?utm_source=twitter")
        self.assertEqual(test_url, "https://vtu.ac.in/circulars")

        test_hash = compute_content_hash("Smoke test content")
        self.assertEqual(len(test_hash), 64)


if __name__ == "__main__":
    unittest.main()
