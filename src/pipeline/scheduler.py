"""
Production Scheduler & Background Daemon for Personal AI Intelligence Agent.
Handles periodic source ingestion loops, scheduled daily & weekly intelligence digests,
source backoff enforcement, and telemetry reporting.
"""

from __future__ import annotations
import logging
import threading
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List, Callable

from src.config.settings import get_settings
from src.pipeline.ingest import IngestionPipeline
from src.pipeline.backoff import get_circuit_breaker, SourceCircuitBreaker
from src.discord import DiscordDispatcher

logger = logging.getLogger("ai_agent.pipeline.scheduler")


class ScheduledJob:
    """Represents a registered background job with run metrics and intervals."""

    def __init__(
        self,
        name: str,
        job_type: str,
        interval_seconds: int,
        handler: Callable[..., Any],
        run_at_time: Optional[str] = None  # Format "HH:MM" in UTC
    ):
        self.name = name
        self.job_type = job_type
        self.interval_seconds = interval_seconds
        self.handler = handler
        self.run_at_time = run_at_time
        self.last_run_at: Optional[datetime] = None
        self.next_run_at: Optional[datetime] = None
        self.run_count: int = 0
        self.last_status: str = "pending"
        self.last_result: Optional[Dict[str, Any]] = None
        self.last_error: Optional[str] = None

    def calculate_next_run(self, now: Optional[datetime] = None) -> datetime:
        """Compute the next scheduled execution timestamp."""
        current_now = now or datetime.now(timezone.utc)
        if self.run_at_time:
            # Parse "HH:MM"
            parts = self.run_at_time.split(":")
            target_hour = int(parts[0])
            target_minute = int(parts[1])
            scheduled = current_now.replace(hour=target_hour, minute=target_minute, second=0, microsecond=0)
            if scheduled <= current_now:
                scheduled += timedelta(days=1)
            self.next_run_at = scheduled
        else:
            self.next_run_at = current_now + timedelta(seconds=self.interval_seconds)
        return self.next_run_at

    def should_run(self, now: Optional[datetime] = None) -> bool:
        """Determine if this job is due for execution."""
        current_now = now or datetime.now(timezone.utc)
        if self.next_run_at is None:
            self.calculate_next_run(current_now)
        return current_now >= self.next_run_at

    def execute(self) -> Any:
        """Run the job handler, record execution metrics, and recalculate next schedule."""
        self.last_run_at = datetime.now(timezone.utc)
        self.run_count += 1
        try:
            logger.info("Executing scheduled job '%s' (%s)...", self.name, self.job_type)
            result = self.handler()
            self.last_status = "success"
            self.last_result = result if isinstance(result, dict) else {"result": str(result)}
            self.last_error = None
            return result
        except Exception as e:
            self.last_status = "error"
            self.last_error = str(e)
            logger.error("Error executing scheduled job '%s': %s", self.name, e, exc_info=True)
            return {"error": str(e)}
        finally:
            self.calculate_next_run(datetime.now(timezone.utc))


class AgentScheduler:
    """
    Continuous background daemon and orchestration coordinator.
    """

    def __init__(
        self,
        pipeline: Optional[IngestionPipeline] = None,
        circuit_breaker: Optional[SourceCircuitBreaker] = None,
        dispatcher: Optional[DiscordDispatcher] = None
    ):
        self.settings = get_settings()
        self.pipeline = pipeline or IngestionPipeline()
        self.circuit_breaker = circuit_breaker or get_circuit_breaker()
        self.dispatcher = dispatcher or DiscordDispatcher()

        self._jobs: Dict[str, ScheduledJob] = {}
        self._is_running: bool = False
        self._stop_event = threading.Event()
        self._worker_thread: Optional[threading.Thread] = None

        self._register_default_jobs()

    def _register_default_jobs(self) -> None:
        """Configure standard background tasks (Ingestion, Daily Digest, Health Check)."""
        # 1. Periodic Ingestion Job (every 30 minutes)
        self.register_job(
            name="periodic_source_ingestion",
            job_type="ingestion",
            interval_seconds=1800,  # 30 mins
            handler=self.run_scheduled_ingestion
        )

        # 2. Daily Intelligence Digest Job (Runs at 08:00 UTC)
        self.register_job(
            name="daily_intelligence_digest",
            job_type="digest",
            interval_seconds=86400,
            handler=self.run_daily_digest,
            run_at_time="08:00"
        )

        # 3. Source Health Audit & Circuit Breaker Telemetry (every 1 hour)
        self.register_job(
            name="source_health_audit",
            job_type="telemetry",
            interval_seconds=3600,
            handler=self.run_health_audit
        )

    def register_job(
        self,
        name: str,
        job_type: str,
        interval_seconds: int,
        handler: Callable[..., Any],
        run_at_time: Optional[str] = None
    ) -> ScheduledJob:
        """Register a new scheduled task."""
        job = ScheduledJob(
            name=name,
            job_type=job_type,
            interval_seconds=interval_seconds,
            handler=handler,
            run_at_time=run_at_time
        )
        job.calculate_next_run()
        self._jobs[name] = job
        return job

    def run_scheduled_ingestion(self) -> Dict[str, Any]:
        """
        Execute ingestion across all enabled sources, respecting backoff cooldowns.
        """
        sources = self.pipeline.storage.get_sources(enabled_only=True)
        eligible_sources = []
        skipped_in_backoff = []

        for src in sources:
            src_id = src.get("id", "")
            interval = src.get("check_interval_minutes", 60)
            if self.circuit_breaker.is_source_eligible(src_id, check_interval_minutes=interval):
                eligible_sources.append(src)
            else:
                skipped_in_backoff.append(src.get("name", src_id))

        if skipped_in_backoff:
            logger.info("Skipping %d sources currently in cooldown/interval: %s", len(skipped_in_backoff), skipped_in_backoff)

        if not eligible_sources:
            logger.info("No sources currently due for polling.")
            return {"status": "skipped", "message": "No eligible sources due"}

        # Run pipeline
        res = self.pipeline.run_full_pipeline(sources=eligible_sources)

        # Update circuit breaker for each source
        for src_res in res.get("source_results", []):
            s_id = src_res.get("source_id", "")
            s_name = src_res.get("source_name", "")
            err_count = src_res.get("errors", 0)
            if err_count == 0:
                self.circuit_breaker.record_success(s_id, s_name)
            else:
                last_err = src_res.get("error_detail", "Collector error")
                cb_state = self.circuit_breaker.record_failure(s_id, last_err, s_name)
                # Alert Discord if threshold exceeded
                if cb_state.get("should_alert_admin") and self.dispatcher:
                    alert_content = (
                        f"⚠️ **Source Collector Failure Alert**\n"
                        f"Source **{s_name}** (`{s_id}`) has failed **{cb_state['consecutive_failures']} consecutive times**.\n"
                        f"Latest Error: `{last_err}`\n"
                        f"Cooldown Backoff: {cb_state['backoff_minutes']} minutes."
                    )
                    self.dispatcher.send_text(alert_content)

        return res

    def run_daily_digest(self, target_date: Optional[str] = None, deliver: bool = True) -> Dict[str, Any]:
        """
        Assemble and deliver the Daily Intelligence Digest.
        """
        digest_date = target_date or datetime.now(timezone.utc).strftime("%Y-%m-%d")
        logger.info("Assembling Daily Intelligence Digest for %s...", digest_date)
        
        result = self.pipeline.dispatch_daily_digest(digest_date=digest_date)
        return {
            "date": digest_date,
            "status": "delivered" if result.get("delivered") else "empty_or_failed",
            "messages_sent": result.get("message_count", 0),
            "articles_count": result.get("articles_count", 0)
        }

    def run_health_audit(self) -> Dict[str, Any]:
        """
        Audit overall system health, source circuit breaker states, and adapter connectivity.
        """
        sources = self.pipeline.storage.get_sources(enabled_only=False)
        all_states = self.circuit_breaker.get_all_states()

        healthy_count = 0
        in_backoff_count = 0
        source_summaries = []

        for s in sources:
            s_id = s.get("id", "")
            s_name = s.get("name", "")
            cb = all_states.get(s_id)
            if cb and cb.get("in_backoff"):
                in_backoff_count += 1
                source_summaries.append({
                    "id": s_id,
                    "name": s_name,
                    "status": "backoff",
                    "failures": cb.get("consecutive_failures", 0),
                    "retry_at": cb.get("next_retry_at").isoformat() if cb.get("next_retry_at") else None
                })
            else:
                healthy_count += 1
                source_summaries.append({
                    "id": s_id,
                    "name": s_name,
                    "status": "healthy",
                    "failures": 0
                })

        return {
            "total_sources": len(sources),
            "healthy_sources": healthy_count,
            "backoff_sources": in_backoff_count,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "sources": source_summaries
        }

    def tick(self, now: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """Check all registered jobs and execute due jobs."""
        current_now = now or datetime.now(timezone.utc)
        executed_jobs = []
        for job_name, job in self._jobs.items():
            if job.should_run(current_now):
                res = job.execute()
                executed_jobs.append({"job": job_name, "result": res})
        return executed_jobs

    def start_background_daemon(self, tick_interval_seconds: int = 10) -> None:
        """Start scheduler execution loop in a background thread."""
        if self._is_running:
            logger.warning("Scheduler is already running.")
            return

        self._is_running = True
        self._stop_event.clear()

        def _worker_loop():
            logger.info("Agent Scheduler Background Worker Started.")
            while not self._stop_event.is_set():
                try:
                    self.tick()
                except Exception as e:
                    logger.error("Unexpected error in scheduler tick loop: %s", e, exc_info=True)
                self._stop_event.wait(timeout=tick_interval_seconds)
            logger.info("Agent Scheduler Background Worker Terminated gracefully.")

        self._worker_thread = threading.Thread(target=_worker_loop, daemon=True, name="AgentSchedulerDaemon")
        self._worker_thread.start()

    def stop(self) -> None:
        """Stop background worker thread gracefully."""
        if not self._is_running:
            return
        logger.info("Stopping Agent Scheduler...")
        self._is_running = False
        self._stop_event.set()
        if self._worker_thread and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=5)

    def get_job_status(self) -> List[Dict[str, Any]]:
        """Get current status of all scheduled jobs."""
        statuses = []
        for name, job in self._jobs.items():
            statuses.append({
                "name": job.name,
                "job_type": job.job_type,
                "interval_seconds": job.interval_seconds,
                "run_at_time": job.run_at_time,
                "last_run_at": job.last_run_at.isoformat() if job.last_run_at else None,
                "next_run_at": job.next_run_at.isoformat() if job.next_run_at else None,
                "run_count": job.run_count,
                "last_status": job.last_status,
                "last_error": job.last_error
            })
        return statuses


# Singleton instance
_global_scheduler: Optional[AgentScheduler] = None

def get_scheduler() -> AgentScheduler:
    global _global_scheduler
    if _global_scheduler is None:
        _global_scheduler = AgentScheduler()
    return _global_scheduler
