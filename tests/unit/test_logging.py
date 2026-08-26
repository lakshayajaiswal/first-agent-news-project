"""
Unit tests for structured logging and secret masking.
"""

import json
import logging
import unittest
from src.config.logging_config import mask_sensitive_data, StructuredJsonFormatter, generate_run_id


class TestLogging(unittest.TestCase):

    def test_mask_sensitive_data(self):
        payload = {
            "title": "Clean Title",
            "api_key": "AIzaSySecretToken12345",
            "discord_token": "SecretDiscordBotToken",
            "nested": {
                "service_role_key": "SecretSupabaseKey",
                "safe_field": "visible_value"
            }
        }
        masked = mask_sensitive_data(payload)
        self.assertEqual(masked["title"], "Clean Title")
        self.assertEqual(masked["api_key"], "***MASKED***")
        self.assertEqual(masked["discord_token"], "***MASKED***")
        self.assertEqual(masked["nested"]["service_role_key"], "***MASKED***")
        self.assertEqual(masked["nested"]["safe_field"], "visible_value")

    def test_structured_json_formatter(self):
        formatter = StructuredJsonFormatter(run_id="run-1234")
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Processing test item",
            args=(),
            exc_info=None
        )
        formatted = formatter.format(record)
        parsed = json.loads(formatted)
        self.assertEqual(parsed["level"], "INFO")
        self.assertEqual(parsed["run_id"], "run-1234")
        self.assertEqual(parsed["message"], "Processing test item")

    def test_generate_run_id(self):
        run_id_1 = generate_run_id()
        run_id_2 = generate_run_id()
        self.assertNotEqual(run_id_1, run_id_2)
        self.assertEqual(len(run_id_1), 36)


if __name__ == "__main__":
    unittest.main()
