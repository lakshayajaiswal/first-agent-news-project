"""
Source Registry and Factory for the Personal AI Intelligence Agent.
Manages adapter registrations, source instantiation, and health metric tracking.
"""

from __future__ import annotations
import logging
from typing import Any, Dict, List, Optional, Type

from src.collectors.base import BaseCollector
from src.collectors.models import SourceHealthMetric
from src.storage.models import SourceModel

logger = logging.getLogger("ai_agent.registry")


class SourceRegistry:
    """Registry maintaining mapping between adapter keys and collector classes."""

    def __init__(self):
        self._adapters: Dict[str, Type[BaseCollector]] = {}
        self._health_metrics: Dict[str, SourceHealthMetric] = {}

    def register(self, adapter_key: str, collector_class: Type[BaseCollector]) -> None:
        """Register an adapter class by its unique adapter_key."""
        self._adapters[adapter_key] = collector_class
        logger.debug("Registered collector adapter: %s -> %s", adapter_key, collector_class.__name__)

    def unregister(self, adapter_key: str) -> None:
        if adapter_key in self._adapters:
            del self._adapters[adapter_key]

    def has_adapter(self, adapter_key: str) -> bool:
        return adapter_key in self._adapters

    def list_adapters(self) -> List[str]:
        return list(self._adapters.keys())

    def create_collector(self, source: SourceModel | dict[str, Any]) -> BaseCollector:
        """Instantiate an adapter for a given Source record."""
        source_dict = source.to_dict() if isinstance(source, SourceModel) else source
        adapter_key = source_dict.get("adapter_key", "")
        
        adapter_cls = self._adapters.get(adapter_key)
        if not adapter_cls:
            raise KeyError(f"No collector registered for adapter_key: '{adapter_key}'. Available: {self.list_adapters()}")

        collector = adapter_cls(
            source_id=source_dict.get("id", ""),
            name=source_dict.get("name", "Unnamed Source"),
            url=source_dict.get("url", ""),
            trust_level=source_dict.get("trust_level", 3),
        )
        return collector

    def record_health_metric(
        self,
        source_id: str,
        source_name: str,
        success: bool,
        items_discovered: int = 0,
        items_accepted: int = 0,
        error: Optional[str] = None
    ) -> SourceHealthMetric:
        """Update and return source health statistics."""
        if source_id not in self._health_metrics:
            self._health_metrics[source_id] = SourceHealthMetric(
                source_id=source_id,
                source_name=source_name
            )

        metric = self._health_metrics[source_id]
        metric.total_runs += 1
        if success:
            metric.successful_runs += 1
            metric.consecutive_failures = 0
            metric.items_discovered += items_discovered
            metric.items_accepted += items_accepted
            metric.last_error = None
        else:
            metric.failed_runs += 1
            metric.consecutive_failures += 1
            metric.last_error = error

        return metric

    def get_health_metrics(self) -> List[SourceHealthMetric]:
        return list(self._health_metrics.values())


_global_registry = SourceRegistry()


def _register_default_adapters(reg: SourceRegistry) -> None:
    """Register core domain adapters (VTU, RSS feeds, Cybersecurity, Dev, AI)."""
    try:
        from src.collectors.vtu import VTUCircularsAdapter, VTUExamsAdapter, VTUAcademicAdapter
        reg.register("vtu_circulars_adapter", VTUCircularsAdapter)
        reg.register("vtu_exams_adapter", VTUExamsAdapter)
        reg.register("vtu_academic_adapter", VTUAcademicAdapter)
    except Exception as e:
        logger.warning("Could not auto-register VTU adapters: %s", e)

    try:
        from src.collectors.feed import RSSFeedAdapter
        reg.register("rss_feed_adapter", RSSFeedAdapter)
    except Exception as e:
        logger.warning("Could not auto-register RSS feed adapter: %s", e)

    try:
        from src.collectors.cybersecurity import CISAKEVAdapter, NISTNVDAdapter
        reg.register("cisa_kev_adapter", CISAKEVAdapter)
        reg.register("nist_nvd_adapter", NISTNVDAdapter)
    except Exception as e:
        logger.warning("Could not auto-register cybersecurity adapters: %s", e)

    try:
        from src.collectors.dev_ai import HackerNewsTopAdapter, HTMLChangelogAdapter
        reg.register("hacker_news_adapter", HackerNewsTopAdapter)
        reg.register("html_feed_adapter", HTMLChangelogAdapter)
    except Exception as e:
        logger.warning("Could not auto-register Dev/AI adapters: %s", e)


_register_default_adapters(_global_registry)


def get_source_registry() -> SourceRegistry:
    """Get singleton SourceRegistry instance."""
    return _global_registry
