"""
Integration test for Phase 5: Scheduling, Circuit Breaker, CLI Automation & Telemetry.
"""

import unittest
from src.pipeline.scheduler import AgentScheduler
from src.pipeline.backoff import SourceCircuitBreaker
from src.pipeline.ingest import IngestionPipeline
from src.storage.supabase_client import get_storage_client


class TestEndToEndPhase5(unittest.TestCase):

    def setUp(self):
        self.cb = SourceCircuitBreaker(alert_threshold=2)
        self.storage = get_storage_client()
        self.pipeline = IngestionPipeline(storage_client=self.storage)
        self.scheduler = AgentScheduler(pipeline=self.pipeline, circuit_breaker=self.cb)

    def test_scheduled_ingestion_with_circuit_breaker(self):
        # 1. First execution should succeed and record clean circuit breaker state
        result = self.scheduler.run_scheduled_ingestion()
        self.assertIn("status", result)

        # 2. Check health audit
        health = self.scheduler.run_health_audit()
        self.assertEqual(health["backoff_sources"], 0)
        self.assertGreater(health["healthy_sources"], 0)

        # 3. Simulate failure on a source
        self.cb.record_failure("src-vtu-circ", "503 Service Unavailable", "VTU Circulars")
        health_after_fail = self.scheduler.run_health_audit()
        self.assertEqual(health_after_fail["backoff_sources"], 1)

        # 4. Check eligibility when in backoff
        self.assertFalse(self.cb.is_source_eligible("src-vtu-circ", check_interval_minutes=60))

    def test_daily_digest_scheduling(self):
        digest_res = self.scheduler.run_daily_digest(target_date="2026-08-25", deliver=False)
        self.assertEqual(digest_res["date"], "2026-08-25")


if __name__ == "__main__":
    unittest.main()
