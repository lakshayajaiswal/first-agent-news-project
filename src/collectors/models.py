"""
Collector data models representing raw source extractions and normalized candidates.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, List, Optional
import uuid

from src.storage.models import Category, SourceType


@dataclass
class RawSourceItem:
    """Raw item extracted from a source before pipeline normalization."""
    title: str
    url: str
    raw_content: str
    source_name: str
    category: Category | str
    published_at: Optional[datetime] = None
    document_links: list[str] = field(default_factory=list)
    raw_metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class NormalizedCandidate:
    """Normalized article candidate ready for deduplication and AI classification."""
    title: str
    canonical_url: str
    source_url: str
    category: Category | str
    content: str
    content_hash: str
    source_id: Optional[str] = None
    published_at: Optional[datetime] = None
    discovered_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    document_storage_path: Optional[str] = None
    document_mime_type: Optional[str] = None
    language: str = "en"
    id: str = field(default_factory=lambda: str(uuid.uuid4()))


@dataclass
class SourceHealthMetric:
    source_id: str
    source_name: str
    total_runs: int = 0
    successful_runs: int = 0
    failed_runs: int = 0
    consecutive_failures: int = 0
    items_discovered: int = 0
    items_accepted: int = 0
    last_run_at: Optional[datetime] = None
    last_error: Optional[str] = None
