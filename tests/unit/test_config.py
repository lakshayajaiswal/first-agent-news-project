"""
Unit tests for settings and configuration management.
"""

import os
import unittest
from src.config.settings import Settings, get_settings


class TestConfig(unittest.TestCase):

    def setUp(self):
        # Backup environment
        self._env_backup = dict(os.environ)

    def tearDown(self):
        # Restore environment
        os.environ.clear()
        os.environ.update(self._env_backup)

    def test_default_settings(self):
        settings = Settings()
        self.assertEqual(settings.preferences.scheme, "2025")
        self.assertEqual(settings.preferences.branch, "CSE")
        self.assertEqual(settings.collector.max_articles_per_run, 50)
        self.assertFalse(settings.supabase.is_configured)

    def test_environment_overrides(self):
        os.environ["USER_SCHEME"] = "2025-REVISED"
        os.environ["MAX_ARTICLES_PER_RUN"] = "100"
        os.environ["SUPABASE_URL"] = "https://myproject.supabase.co"
        os.environ["SUPABASE_SERVICE_ROLE_KEY"] = "my_service_role_key"
        os.environ["APP_ENV"] = "production"

        settings = Settings()
        self.assertEqual(settings.preferences.scheme, "2025-REVISED")
        self.assertEqual(settings.collector.max_articles_per_run, 100)
        self.assertTrue(settings.supabase.is_configured)
        self.assertEqual(settings.app_env, "production")

    def test_production_validation_catches_missing_secrets(self):
        os.environ["APP_ENV"] = "production"
        os.environ.pop("GEMINI_API_KEY", None)
        os.environ.pop("DISCORD_WEBHOOK_URL", None)
        os.environ.pop("SUPABASE_URL", None)

        settings = Settings()
        errors = settings.validate_for_production()
        self.assertGreater(len(errors), 0)


if __name__ == "__main__":
    unittest.main()
