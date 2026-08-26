"""
Unit tests for AgentScheduler and ScheduledJob.
Tests job registration, next run calculation, execution metrics, tick dispatching, and background daemon.
"""

import unittest
from datetime import datetime, timezone, timedelta
from src.pipeline.scheduler import AgentScheduler, ScheduledJob


class TestAgentScheduler(unittest.TestCase):

    def setUp(self):
        self.scheduler = AgentScheduler()

    def test_job_registration_and_schedule_calculation(self):
        call_count = [0]
        def dummy_handler():
            call_count[0] += 1
            return {"status": "ok"}

        job = self.scheduler.register_job(
            name="test_job",
            job_type="custom",
            interval_seconds=10,
            handler=dummy_handler
        )
        self.assertEqual(job.name, "test_job")
        self.assertIsNotNone(job.next_run_at)
        self.assertFalse(job.should_run(now=datetime.now(timezone.utc) - timedelta(seconds=100)))

        # Simulate execution when due
        job.next_run_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        self.assertTrue(job.should_run())
        res = job.execute()
        self.assertEqual(res["status"], "ok")
        self.assertEqual(job.run_count, 1)
        self.assertEqual(job.last_status, "success")

    def test_daily_timed_job_calculation(self):
        job = ScheduledJob(
            name="daily_test",
            job_type="digest",
            interval_seconds=86400,
            handler=lambda: {"digest": "done"},
            run_at_time="08:00"
        )
        now_7am = datetime(2026, 8, 25, 7, 0, 0, tzinfo=timezone.utc)
        next_run = job.calculate_next_run(now=now_7am)
        self.assertEqual(next_run.hour, 8)
        self.assertEqual(next_run.day, 25)

        now_9am = datetime(2026, 8, 25, 9, 0, 0, tzinfo=timezone.utc)
        next_run_tomorrow = job.calculate_next_run(now=now_9am)
        self.assertEqual(next_run_tomorrow.hour, 8)
        self.assertEqual(next_run_tomorrow.day, 26)

    def test_scheduler_tick_and_health_audit(self):
        health = self.scheduler.run_health_audit()
        self.assertIn("total_sources", health)
        self.assertIn("healthy_sources", health)
        self.assertGreater(health["total_sources"], 0)

        jobs = self.scheduler.get_job_status()
        self.assertGreaterEqual(len(jobs), 3)
        job_names = [j["name"] for j in jobs]
        self.assertIn("periodic_source_ingestion", job_names)
        self.assertIn("daily_intelligence_digest", job_names)

    def test_start_and_stop_daemon(self):
        self.scheduler.start_background_daemon(tick_interval_seconds=1)
        self.assertTrue(self.scheduler._is_running)
        self.scheduler.stop()
        self.assertFalse(self.scheduler._is_running)


if __name__ == "__main__":
    unittest.main()
