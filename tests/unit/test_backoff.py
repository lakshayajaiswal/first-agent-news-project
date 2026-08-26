"""
Unit tests for Source Circuit Breaker and Exponential Backoff.
Tests failure increments, cooldown windows, eligibility checks, and admin alert thresholds.
"""

import unittest
from datetime import datetime, timezone, timedelta
from src.pipeline.backoff import SourceCircuitBreaker


class TestSourceCircuitBreaker(unittest.TestCase):

    def setUp(self):
        self.cb = SourceCircuitBreaker(
            backoff_schedule=[5, 15, 30, 60],
            alert_threshold=3
        )

    def test_initial_source_eligibility(self):
        # A source with no prior history should be eligible immediately
        self.assertTrue(self.cb.is_source_eligible("src-new", check_interval_minutes=60))

    def test_record_success_resets_failures(self):
        self.cb.record_failure("src-1", "HTTP 500", "Source 1")
        state = self.cb.get_state("src-1")
        self.assertEqual(state["consecutive_failures"], 1)
        self.assertTrue(state["in_backoff"])

        self.cb.record_success("src-1", "Source 1")
        state_after = self.cb.get_state("src-1")
        self.assertEqual(state_after["consecutive_failures"], 0)
        self.assertFalse(state_after["in_backoff"])
        self.assertIsNone(state_after["last_error"])

    def test_exponential_backoff_cooldown(self):
        # Failure 1 -> 5 min
        s1 = self.cb.record_failure("src-2", "Timeout", "Source 2")
        self.assertEqual(s1["backoff_minutes"], 5)
        self.assertFalse(s1["should_alert_admin"])
        # Should NOT be eligible immediately
        self.assertFalse(self.cb.is_source_eligible("src-2", check_interval_minutes=60))

        # Failure 2 -> 15 min
        s2 = self.cb.record_failure("src-2", "Timeout", "Source 2")
        self.assertEqual(s2["backoff_minutes"], 15)
        self.assertFalse(s2["should_alert_admin"])

        # Failure 3 -> 30 min (crosses alert threshold of 3)
        s3 = self.cb.record_failure("src-2", "Timeout", "Source 2")
        self.assertEqual(s3["backoff_minutes"], 30)
        self.assertTrue(s3["should_alert_admin"])

    def test_eligibility_after_cooldown(self):
        s = self.cb.record_failure("src-3", "Error", "Source 3")
        # Manually alter next_retry_at to the past
        self.cb._source_states["src-3"]["next_retry_at"] = datetime.now(timezone.utc) - timedelta(minutes=1)
        self.cb._source_states["src-3"]["last_checked_at"] = datetime.now(timezone.utc) - timedelta(minutes=120)

        self.assertTrue(self.cb.is_source_eligible("src-3", check_interval_minutes=60))


if __name__ == "__main__":
    unittest.main()
