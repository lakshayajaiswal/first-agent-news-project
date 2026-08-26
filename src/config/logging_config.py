"""
Structured Logging System for Personal AI Intelligence Agent.
Formats logs with run IDs, timestamps, categories, and masks sensitive secrets.
"""

from __future__ import annotations
import json
import logging
import sys
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

SENSITIVE_KEYS = {"api_key", "secret", "token", "service_role_key", "password", "authorization"}


def mask_sensitive_data(data: Any) -> Any:
    """Recursively mask secrets and credentials in logs/dicts."""
    if isinstance(data, dict):
        masked = {}
        for k, v in data.items():
            if any(s in k.lower() for s in SENSITIVE_KEYS):
                masked[k] = "***MASKED***"
            else:
                masked[k] = mask_sensitive_data(v)
        return masked
    elif isinstance(data, list):
        return [mask_sensitive_data(item) for item in data]
    return data


class StructuredJsonFormatter(logging.Formatter):
    """Formats log records as structured JSON for cloud observability."""

    def __init__(self, run_id: Optional[str] = None):
        super().__init__()
        self.run_id = run_id

    def format(self, record: logging.LogRecord) -> str:
        log_entry: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        if hasattr(record, "run_id") and record.run_id:
            log_entry["run_id"] = record.run_id
        elif self.run_id:
            log_entry["run_id"] = self.run_id

        if hasattr(record, "source_id") and record.source_id:
            log_entry["source_id"] = record.source_id

        if hasattr(record, "category") and record.category:
            log_entry["category"] = record.category

        if hasattr(record, "extra_data") and record.extra_data:
            log_entry["data"] = mask_sensitive_data(record.extra_data)

        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_entry)


def setup_logger(
    name: str = "ai_agent",
    level: str = "INFO",
    run_id: Optional[str] = None,
    json_format: bool = False
) -> logging.Logger:
    """Set up and configure a structured logger."""
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    logger.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)
    if json_format:
        handler.setFormatter(StructuredJsonFormatter(run_id=run_id))
    else:
        prefix = f"[{run_id[:8]}] " if run_id else ""
        handler.setFormatter(
            logging.Formatter(
                f"%(asctime)s [%(levelname)s] {prefix}%(name)s: %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )

    logger.addHandler(handler)
    logger.propagate = False
    return logger


def generate_run_id() -> str:
    """Generate a unique run ID for tracking a full collector/digest execution."""
    return str(uuid.uuid4())
