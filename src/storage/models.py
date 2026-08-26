"""
Data models and typed representations of Supabase schema entities.
Mapped directly to the specification in 03_SUPABASE_DATABASE_SCHEMA.md.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional
import uuid


class Category(str, Enum):
    VTU = "vtu"
    AI = "ai"
    DEVELOPMENT = "development"
    CYBERSECURITY = "cybersecurity"


class SourceType(str, Enum):
    HTML = "html"
    PDF = "pdf"
    FEED = "feed"
    API = "api"
    JSON = "json"


class ArticleStatus(str, Enum):
    CANDIDATE = "candidate"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    ERROR = "error"


class UrgencyLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Decision(str, Enum):
    ACCEPT = "accept"
    REJECT = "reject"
    NEEDS_REVIEW = "needs_review"


class NotificationChannel(str, Enum):
    DISCORD = "discord"


class MessageType(str, Enum):
    URGENT = "urgent"
    DAILY_DIGEST = "daily_digest"
    WEEKLY_DIGEST = "weekly_digest"


class NotificationStatus(str, Enum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"


class FetchRunStatus(str, Enum):
    RUNNING = "running"
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"


def _enum_val(val: Any) -> Any:
    return val.value if hasattr(val, "value") else str(val) if val is not None else None


@dataclass
class SourceModel:
    name: str
    category: Category | str
    url: str
    source_type: SourceType | str
    adapter_key: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    enabled: bool = True
    trust_level: int = 3
    check_interval_minutes: int = 60
    last_checked_at: Optional[datetime] = None
    last_success_at: Optional[datetime] = None
    consecutive_failures: int = 0
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "category": _enum_val(self.category),
            "url": self.url,
            "source_type": _enum_val(self.source_type),
            "adapter_key": self.adapter_key,
            "enabled": self.enabled,
            "trust_level": self.trust_level,
            "check_interval_minutes": self.check_interval_minutes,
            "last_checked_at": self.last_checked_at.isoformat() if self.last_checked_at else None,
            "last_success_at": self.last_success_at.isoformat() if self.last_success_at else None,
            "consecutive_failures": self.consecutive_failures,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


@dataclass
class ArticleModel:
    title: str
    canonical_url: str
    source_url: str
    category: Category | str
    content_hash: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    source_id: Optional[str] = None
    published_at: Optional[datetime] = None
    discovered_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    content: Optional[str] = None
    document_storage_path: Optional[str] = None
    document_mime_type: Optional[str] = None
    language: str = "en"
    status: ArticleStatus | str = ArticleStatus.CANDIDATE
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "source_id": self.source_id,
            "title": self.title,
            "canonical_url": self.canonical_url,
            "source_url": self.source_url,
            "published_at": self.published_at.isoformat() if self.published_at else None,
            "discovered_at": self.discovered_at.isoformat(),
            "content": self.content,
            "content_hash": self.content_hash,
            "document_storage_path": self.document_storage_path,
            "document_mime_type": self.document_mime_type,
            "language": self.language,
            "category": _enum_val(self.category),
            "status": _enum_val(self.status),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


@dataclass
class EventModel:
    event_key: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    primary_article_id: Optional[str] = None
    event_title: Optional[str] = None
    first_seen_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_seen_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    article_count: int = 1
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "primary_article_id": self.primary_article_id,
            "event_key": self.event_key,
            "event_title": self.event_title,
            "first_seen_at": self.first_seen_at.isoformat(),
            "last_seen_at": self.last_seen_at.isoformat(),
            "article_count": self.article_count,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class ClassificationModel:
    article_id: str
    relevance_score: float
    importance_score: int
    urgency: UrgencyLevel | str
    confidence_score: float
    decision: Decision | str
    reason: str
    model_name: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    action_required: bool = False
    action_summary: Optional[str] = None
    model_version: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "article_id": self.article_id,
            "relevance_score": round(self.relevance_score, 4),
            "importance_score": self.importance_score,
            "urgency": _enum_val(self.urgency),
            "action_required": self.action_required,
            "action_summary": self.action_summary,
            "confidence_score": round(self.confidence_score, 4),
            "decision": _enum_val(self.decision),
            "reason": self.reason,
            "model_name": self.model_name,
            "model_version": self.model_version,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class SummaryModel:
    article_id: str
    headline: str
    what_happened: str
    why_it_matters: str
    source_name: str
    source_url: str
    model_name: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    action_required: Optional[str] = None
    key_points: list[str] = field(default_factory=list)
    summary_version: int = 1
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "article_id": self.article_id,
            "headline": self.headline,
            "what_happened": self.what_happened,
            "why_it_matters": self.why_it_matters,
            "action_required": self.action_required,
            "key_points": self.key_points,
            "source_name": self.source_name,
            "source_url": self.source_url,
            "summary_version": self.summary_version,
            "model_name": self.model_name,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class NotificationModel:
    article_id: Optional[str]
    channel: NotificationChannel | str = NotificationChannel.DISCORD
    message_type: MessageType | str = MessageType.DAILY_DIGEST
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    event_id: Optional[str] = None
    discord_message_id: Optional[str] = None
    status: NotificationStatus | str = NotificationStatus.PENDING
    attempt_count: int = 0
    sent_at: Optional[datetime] = None
    last_error: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "article_id": self.article_id,
            "event_id": self.event_id,
            "channel": _enum_val(self.channel),
            "message_type": _enum_val(self.message_type),
            "discord_message_id": self.discord_message_id,
            "status": _enum_val(self.status),
            "attempt_count": self.attempt_count,
            "sent_at": self.sent_at.isoformat() if self.sent_at else None,
            "last_error": self.last_error,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class FetchRunModel:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    finished_at: Optional[datetime] = None
    status: FetchRunStatus | str = FetchRunStatus.RUNNING
    sources_attempted: int = 0
    sources_succeeded: int = 0
    sources_failed: int = 0
    articles_discovered: int = 0
    articles_accepted: int = 0
    articles_rejected: int = 0
    duplicates_detected: int = 0
    error_summary: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "started_at": self.started_at.isoformat(),
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "status": str(self.status),
            "sources_attempted": self.sources_attempted,
            "sources_succeeded": self.sources_succeeded,
            "sources_failed": self.sources_failed,
            "articles_discovered": self.articles_discovered,
            "articles_accepted": self.articles_accepted,
            "articles_rejected": self.articles_rejected,
            "duplicates_detected": self.duplicates_detected,
            "error_summary": self.error_summary,
        }


@dataclass
class UserPreferencesModel:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    scheme: str = "2025"
    branch: str = "CSE"
    semester: str = "1"
    ai_interest_level: int = 4
    development_interest_level: int = 4
    cybersecurity_interest_level: int = 5
    urgent_alerts_enabled: bool = True
    daily_digest_enabled: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "scheme": self.scheme,
            "branch": self.branch,
            "semester": self.semester,
            "ai_interest_level": self.ai_interest_level,
            "development_interest_level": self.development_interest_level,
            "cybersecurity_interest_level": self.cybersecurity_interest_level,
            "urgent_alerts_enabled": self.urgent_alerts_enabled,
            "daily_digest_enabled": self.daily_digest_enabled,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
