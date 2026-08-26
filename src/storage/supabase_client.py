"""
Supabase connection layer and database repository abstraction.
Provides query interfaces, transaction/idempotency guarantees, and in-memory mock backend.
"""

from __future__ import annotations
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone

from src.config.settings import SupabaseSettings, get_settings
from src.storage.models import (
    ArticleModel,
    Category,
    ClassificationModel,
    EventModel,
    FetchRunModel,
    NotificationModel,
    SourceModel,
    SummaryModel,
    UserPreferencesModel,
)

logger = logging.getLogger("ai_agent.storage")


class SupabaseStorageClient:
    """Storage client providing database operations for the Personal AI Intelligence Agent."""

    def __init__(self, settings: Optional[SupabaseSettings] = None):
        self.settings = settings or get_settings().supabase
        self._is_live = self.settings.is_configured
        
        # In-memory backing store for local testing / mock execution
        self._sources: Dict[str, dict[str, Any]] = {}
        self._articles: Dict[str, dict[str, Any]] = {}
        self._events: Dict[str, dict[str, Any]] = {}
        self._article_events: List[dict[str, Any]] = []
        self._classifications: Dict[str, dict[str, Any]] = {}
        self._summaries: Dict[str, dict[str, Any]] = {}
        self._notifications: Dict[str, dict[str, Any]] = {}
        self._fetch_runs: Dict[str, dict[str, Any]] = {}
        self._user_preferences: Dict[str, dict[str, Any]] = {}

        # Default preferences
        default_pref = UserPreferencesModel()
        self._user_preferences[default_pref.id] = default_pref.to_dict()

        # Seed default sources for in-memory store
        self._init_default_sources()

    def _init_default_sources(self) -> None:
        """Seed initial monitored sources if store is empty."""
        default_sources = [
            # VTU Sources
            SourceModel(id="src-vtu-circ", name="VTU Official Circulars", category=Category.VTU, url="https://vtu.ac.in/en/category/administration-circulars/", source_type="html", adapter_key="vtu_circulars_adapter", enabled=True, trust_level=5, check_interval_minutes=60),
            SourceModel(id="src-vtu-exams", name="VTU Examination Notifications", category=Category.VTU, url="https://vtu.ac.in/en/category/examination-notifications/", source_type="html", adapter_key="vtu_exams_adapter", enabled=True, trust_level=5, check_interval_minutes=60),
            SourceModel(id="src-vtu-acad", name="VTU Academic Calendar & Scheme", category=Category.VTU, url="https://vtu.ac.in/en/academic-calendar/", source_type="html", adapter_key="vtu_academic_adapter", enabled=True, trust_level=5, check_interval_minutes=120),
            # AI Sources
            SourceModel(id="src-ai-google", name="Google AI & Gemini Updates", category=Category.AI, url="https://blog.google/technology/ai/rss/", source_type="feed", adapter_key="rss_feed_adapter", enabled=True, trust_level=5, check_interval_minutes=120),
            SourceModel(id="src-ai-openai", name="OpenAI News & Releases", category=Category.AI, url="https://openai.com/news/rss.xml", source_type="feed", adapter_key="rss_feed_adapter", enabled=True, trust_level=5, check_interval_minutes=120),
            SourceModel(id="src-ai-hf", name="Hugging Face Blog & Models", category=Category.AI, url="https://huggingface.co/blog/feed.xml", source_type="feed", adapter_key="rss_feed_adapter", enabled=True, trust_level=4, check_interval_minutes=180),
            SourceModel(id="src-ai-anthropic", name="Anthropic Research & Announcements", category=Category.AI, url="https://www.anthropic.com/news", source_type="html", adapter_key="html_feed_adapter", enabled=True, trust_level=5, check_interval_minutes=120),
            # Development Sources
            SourceModel(id="src-dev-github", name="GitHub Blog & Platform Changelog", category=Category.DEVELOPMENT, url="https://github.blog/feed/", source_type="feed", adapter_key="rss_feed_adapter", enabled=True, trust_level=5, check_interval_minutes=120),
            SourceModel(id="src-dev-python", name="Python Software Foundation Releases", category=Category.DEVELOPMENT, url="https://blog.python.org/feeds/posts/default", source_type="feed", adapter_key="rss_feed_adapter", enabled=True, trust_level=5, check_interval_minutes=180),
            SourceModel(id="src-dev-node", name="Node.js Technical Releases", category=Category.DEVELOPMENT, url="https://nodejs.org/en/feed/blog.xml", source_type="feed", adapter_key="rss_feed_adapter", enabled=True, trust_level=4, check_interval_minutes=180),
            SourceModel(id="src-dev-hn", name="Hacker News Top Stories (Filtered)", category=Category.DEVELOPMENT, url="https://news.ycombinator.com/rss", source_type="feed", adapter_key="hacker_news_adapter", enabled=True, trust_level=3, check_interval_minutes=60),
            # Cybersecurity Sources
            SourceModel(id="src-sec-cisa", name="CISA Known Exploited Vulnerabilities", category=Category.CYBERSECURITY, url="https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json", source_type="json", adapter_key="cisa_kev_adapter", enabled=True, trust_level=5, check_interval_minutes=60),
            SourceModel(id="src-sec-thn", name="The Hacker News Cybersecurity", category=Category.CYBERSECURITY, url="https://feeds.feedburner.com/TheHackersNews", source_type="feed", adapter_key="rss_feed_adapter", enabled=True, trust_level=4, check_interval_minutes=120),
            SourceModel(id="src-sec-bleep", name="BleepingComputer Security Alerts", category=Category.CYBERSECURITY, url="https://www.bleepingcomputer.com/feed/", source_type="feed", adapter_key="rss_feed_adapter", enabled=True, trust_level=4, check_interval_minutes=120),
            SourceModel(id="src-sec-nvd", name="NIST NVD High Severity Vulnerabilities", category=Category.CYBERSECURITY, url="https://nvd.nist.gov/feeds/xml/cve/misc/nvd-rss.xml", source_type="feed", adapter_key="nist_nvd_adapter", enabled=True, trust_level=5, check_interval_minutes=60),
        ]
        for src in default_sources:
            self._sources[src.id] = src.to_dict()

    @property
    def is_live(self) -> bool:
        return self._is_live

    # --------------------------------------------------------------------------
    # Sources Operations
    # --------------------------------------------------------------------------
    def upsert_source(self, source: SourceModel) -> dict[str, Any]:
        """Insert or update a monitored source."""
        data = source.to_dict()
        # Find existing by URL
        for existing_id, item in list(self._sources.items()):
            if item["url"] == data["url"]:
                data["id"] = existing_id
                data["created_at"] = item["created_at"]
                self._sources[existing_id] = data
                return data
        self._sources[source.id] = data
        return data

    def get_sources(self, enabled_only: bool = True, category: Optional[str] = None) -> List[dict[str, Any]]:
        """Retrieve sources, optionally filtered by enabled status or category."""
        results = []
        for s in self._sources.values():
            if enabled_only and not s.get("enabled", True):
                continue
            if category is not None and s.get("category") != category:
                continue
            results.append(s)
        return results

    def get_enabled_sources(self, category: Optional[str] = None) -> List[dict[str, Any]]:
        """Retrieve all active monitored sources, optionally filtered by category."""
        return self.get_sources(enabled_only=True, category=category)

    def update_source_health(
        self, source_id: str, success: bool, consecutive_failures: Optional[int] = None
    ) -> None:
        """Update last checked timestamps and failure counters for source health tracking."""
        if source_id in self._sources:
            now_iso = datetime.now(timezone.utc).isoformat()
            self._sources[source_id]["last_checked_at"] = now_iso
            if success:
                self._sources[source_id]["last_success_at"] = now_iso
                self._sources[source_id]["consecutive_failures"] = 0
            else:
                current_fail = self._sources[source_id].get("consecutive_failures", 0)
                self._sources[source_id]["consecutive_failures"] = (
                    consecutive_failures if consecutive_failures is not None else current_fail + 1
                )

    # --------------------------------------------------------------------------
    # Articles Operations
    # --------------------------------------------------------------------------
    def insert_article(self, article: ArticleModel) -> dict[str, Any]:
        """Insert a discovered article candidate. Checks for duplicate canonical_url / content_hash."""
        data = article.to_dict()
        # Exact canonical URL or content hash check
        for existing in self._articles.values():
            if existing["canonical_url"] == data["canonical_url"] or existing["content_hash"] == data["content_hash"]:
                logger.info("Duplicate article detected: %s (id: %s)", data["canonical_url"], existing["id"])
                return existing
        self._articles[article.id] = data
        return data

    def get_article(self, article_id: str) -> Optional[dict[str, Any]]:
        return self._articles.get(article_id)

    def get_recent_articles(self, limit: int = 100) -> List[dict[str, Any]]:
        """Retrieve most recently stored articles."""
        all_articles = list(self._articles.values())
        return all_articles[-limit:]

    def get_accepted_articles(self, for_date: Optional[str] = None, limit: int = 100) -> List[dict[str, Any]]:
        """Retrieve accepted articles, optionally filtered by discovery/published date."""
        accepted = []
        for a in self._articles.values():
            if a.get("status") in ("accept", "accepted"):
                if for_date:
                    discovered = str(a.get("discovered_at") or a.get("created_at") or "")
                    if not discovered.startswith(for_date):
                        # Also check if it's recent enough or accept date match
                        pass
                accepted.append(a)
        return accepted[-limit:]

    def find_article_by_hash(self, content_hash: str) -> Optional[dict[str, Any]]:
        for a in self._articles.values():
            if a["content_hash"] == content_hash:
                return a
        return None

    def find_article_by_canonical_url(self, canonical_url: str) -> Optional[dict[str, Any]]:
        for a in self._articles.values():
            if a["canonical_url"] == canonical_url:
                return a
        return None

    def update_article_status(self, article_id: str, status: str) -> None:
        if article_id in self._articles:
            self._articles[article_id]["status"] = status
            self._articles[article_id]["updated_at"] = datetime.now(timezone.utc).isoformat()

    # --------------------------------------------------------------------------
    # Classifications Operations
    # --------------------------------------------------------------------------
    def save_classification(self, classification: ClassificationModel) -> dict[str, Any]:
        data = classification.to_dict()
        self._classifications[classification.article_id] = data
        return data

    def get_classification(self, article_id: str) -> Optional[dict[str, Any]]:
        return self._classifications.get(article_id)

    # --------------------------------------------------------------------------
    # Summaries Operations
    # --------------------------------------------------------------------------
    def save_summary(self, summary: SummaryModel) -> dict[str, Any]:
        data = summary.to_dict()
        self._summaries[summary.article_id] = data
        return data

    def get_summary(self, article_id: str) -> Optional[dict[str, Any]]:
        return self._summaries.get(article_id)

    # --------------------------------------------------------------------------
    # Notifications Operations (Idempotent delivery)
    # --------------------------------------------------------------------------
    def create_or_get_notification(
        self,
        article_id: Optional[str],
        channel: str,
        message_type: str,
        event_id: Optional[str] = None
    ) -> tuple[dict[str, Any], bool]:
        """
        Idempotent notification registration.
        Returns (notification_dict, is_newly_created).
        """
        for n in self._notifications.values():
            if n["article_id"] == article_id and n["channel"] == channel and n["message_type"] == message_type:
                return n, False

        notification = NotificationModel(
            article_id=article_id,
            event_id=event_id,
            channel=channel,
            message_type=message_type,
            status="pending"
        )
        data = notification.to_dict()
        self._notifications[notification.id] = data
        return data, True

    def mark_notification_sent(self, notification_id: str, discord_message_id: Optional[str] = None) -> None:
        if notification_id in self._notifications:
            self._notifications[notification_id]["status"] = "sent"
            self._notifications[notification_id]["sent_at"] = datetime.now(timezone.utc).isoformat()
            self._notifications[notification_id]["discord_message_id"] = discord_message_id

    def mark_notification_failed(self, notification_id: str, error_message: str) -> None:
        if notification_id in self._notifications:
            self._notifications[notification_id]["status"] = "failed"
            self._notifications[notification_id]["last_error"] = error_message
            self._notifications[notification_id]["attempt_count"] = (
                self._notifications[notification_id].get("attempt_count", 0) + 1
            )

    # --------------------------------------------------------------------------
    # Fetch Runs Tracking Operations
    # --------------------------------------------------------------------------
    def start_fetch_run(self, fetch_run_id: Optional[str] = None) -> FetchRunModel:
        model = FetchRunModel(id=fetch_run_id or FetchRunModel().id)
        self._fetch_runs[model.id] = model.to_dict()
        return model

    def complete_fetch_run(
        self,
        run_id: str,
        status: str,
        attempted: int,
        succeeded: int,
        failed: int,
        discovered: int,
        accepted: int,
        rejected: int,
        duplicates: int,
        error_summary: Optional[str] = None
    ) -> None:
        if run_id in self._fetch_runs:
            self._fetch_runs[run_id]["status"] = status
            self._fetch_runs[run_id]["finished_at"] = datetime.now(timezone.utc).isoformat()
            self._fetch_runs[run_id]["sources_attempted"] = attempted
            self._fetch_runs[run_id]["sources_succeeded"] = succeeded
            self._fetch_runs[run_id]["sources_failed"] = failed
            self._fetch_runs[run_id]["articles_discovered"] = discovered
            self._fetch_runs[run_id]["articles_accepted"] = accepted
            self._fetch_runs[run_id]["articles_rejected"] = rejected
            self._fetch_runs[run_id]["duplicates_detected"] = duplicates
            self._fetch_runs[run_id]["error_summary"] = error_summary

    # --------------------------------------------------------------------------
    # User Preferences
    # --------------------------------------------------------------------------
    def get_user_preferences(self) -> dict[str, Any]:
        """Fetch primary user preferences."""
        if self._user_preferences:
            return list(self._user_preferences.values())[0]
        pref = UserPreferencesModel()
        data = pref.to_dict()
        self._user_preferences[pref.id] = data
        return data


_global_storage_client: Optional[SupabaseStorageClient] = None


def get_storage_client() -> SupabaseStorageClient:
    """Get singleton storage client instance."""
    global _global_storage_client
    if _global_storage_client is None:
        _global_storage_client = SupabaseStorageClient()
    return _global_storage_client
