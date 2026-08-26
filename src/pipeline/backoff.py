"""
Source Health & Exponential Backoff Circuit Breaker.
Tracks consecutive failures per source, applies cooldown backoff windows,
and alerts administrators when critical failure thresholds are breached.
"""

from __future__ import annotations
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List

logger = logging.getLogger("ai_agent.pipeline.backoff")

# Base backoff multipliers in minutes based on consecutive failure counts
DEFAULT_BACKOFF_SCHEDULE_MINUTES = [
    5,     # 1 failure -> 5 min delay
    15,    # 2 failures -> 15 min delay
    30,    # 3 failures -> 30 min delay
    60,    # 4 failures -> 1 hour delay
    180,   # 5 failures -> 3 hours delay
    720,   # 6 failures -> 12 hours delay
    1440   # 7+ failures -> 24 hours max delay
]

CRITICAL_ALERT_FAILURE_THRESHOLD = 5


class SourceCircuitBreaker:
    """
    Manages per-source failure counts, backoff cooldown eligibility, and alerting.
    """

    def __init__(self, backoff_schedule: Optional[List[int]] = None, alert_threshold: int = CRITICAL_ALERT_FAILURE_THRESHOLD):
        self.backoff_schedule = backoff_schedule or DEFAULT_BACKOFF_SCHEDULE_MINUTES
        self.alert_threshold = alert_threshold
        # In-memory tracking cache: source_id -> health stats
        self._source_states: Dict[str, Dict[str, Any]] = {}

    def get_backoff_minutes(self, consecutive_failures: int) -> int:
        """Calculate cooldown minutes given failure count."""
        if consecutive_failures <= 0:
            return 0
        idx = min(consecutive_failures - 1, len(self.backoff_schedule) - 1)
        return self.backoff_schedule[idx]

    def record_success(self, source_id: str, source_name: str = "") -> Dict[str, Any]:
        """Record successful collector run, resetting consecutive failures."""
        now = datetime.now(timezone.utc)
        state = {
            "source_id": source_id,
            "source_name": source_name,
            "consecutive_failures": 0,
            "last_success_at": now,
            "last_checked_at": now,
            "in_backoff": False,
            "next_retry_at": None,
            "last_error": None
        }
        self._source_states[source_id] = state
        return state

    def record_failure(self, source_id: str, error_message: str, source_name: str = "") -> Dict[str, Any]:
        """Record a collector failure, incrementing failure counter and calculating next retry time."""
        now = datetime.now(timezone.utc)
        prev = self._source_states.get(source_id, {
            "consecutive_failures": 0,
            "last_success_at": None
        })
        new_failures = prev.get("consecutive_failures", 0) + 1
        backoff_mins = self.get_backoff_minutes(new_failures)
        next_retry = now + timedelta(minutes=backoff_mins)

        state = {
            "source_id": source_id,
            "source_name": source_name or prev.get("source_name", source_id),
            "consecutive_failures": new_failures,
            "last_success_at": prev.get("last_success_at"),
            "last_checked_at": now,
            "in_backoff": True,
            "backoff_minutes": backoff_mins,
            "next_retry_at": next_retry,
            "last_error": error_message,
            "should_alert_admin": new_failures >= self.alert_threshold
        }
        self._source_states[source_id] = state
        logger.warning(
            "Source '%s' (%s) failure count=%d. Backoff cooldown: %d min (next retry: %s). Error: %s",
            source_name or source_id,
            source_id,
            new_failures,
            backoff_mins,
            next_retry.strftime("%H:%M:%S UTC"),
            error_message
        )
        return state

    def is_source_eligible(self, source_id: str, check_interval_minutes: int = 60) -> bool:
        """
        Check if a source is eligible to be fetched right now based on:
        1. Whether its regular interval has elapsed since last checked.
        2. Whether it has cleared any active backoff cooldown window.
        """
        state = self._source_states.get(source_id)
        if not state:
            return True  # Never checked before

        now = datetime.now(timezone.utc)

        # Check backoff window
        if state.get("in_backoff") and state.get("next_retry_at"):
            if now < state["next_retry_at"]:
                return False

        # Check interval window
        last_checked = state.get("last_checked_at")
        if last_checked:
            elapsed = (now - last_checked).total_seconds() / 60.0
            if elapsed < check_interval_minutes:
                return False

        return True

    def get_state(self, source_id: str) -> Optional[Dict[str, Any]]:
        """Get current health and circuit breaker state for a source."""
        return self._source_states.get(source_id)

    def get_all_states(self) -> Dict[str, Dict[str, Any]]:
        """Get all tracked source health states."""
        return dict(self._source_states)


# Global singleton instance
_circuit_breaker = SourceCircuitBreaker()

def get_circuit_breaker() -> SourceCircuitBreaker:
    return _circuit_breaker
