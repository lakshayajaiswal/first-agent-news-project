"""
Base Collector Interface for Personal AI Intelligence Agent.
Defines the contract and execution lifecycle for all domain sources (VTU, AI, Dev, Cybersecurity).
"""

from __future__ import annotations
from abc import ABC, abstractmethod
import logging
from typing import Any, List, Optional
from datetime import datetime, timezone

from src.collectors.models import NormalizedCandidate, RawSourceItem
from src.normalization.url import canonicalize_url
from src.normalization.content import clean_text, compute_content_hash
from src.storage.models import Category, SourceType

logger = logging.getLogger("ai_agent.collectors")


class BaseCollector(ABC):
    """
    Abstract Base Class for all Source Adapters.
    Every source implements:
      1. fetch() -> raw bytes / string / response
      2. extract() -> List[RawSourceItem]
      3. normalize() -> List[NormalizedCandidate]
    """

    adapter_key: str = "base_adapter"
    category: Category | str = Category.DEVELOPMENT
    source_type: SourceType | str = SourceType.HTML

    def __init__(self, source_id: str, name: str, url: str, trust_level: int = 3, config: Optional[dict[str, Any]] = None):
        self.source_id = source_id
        self.name = name
        self.url = url
        self.trust_level = trust_level
        self.config = config or {}

    @abstractmethod
    def fetch(self) -> Any:
        """Fetch raw content from the source URL. Must raise on network/protocol failures."""
        pass

    @abstractmethod
    def extract(self, raw_data: Any) -> List[RawSourceItem]:
        """Parse raw data into discrete RawSourceItems."""
        pass

    def normalize(self, raw_items: List[RawSourceItem]) -> List[NormalizedCandidate]:
        """Transform raw items into canonical candidates with normalized URLs and SHA-256 hashes."""
        candidates: List[NormalizedCandidate] = []
        for raw in raw_items:
            canonical_link = canonicalize_url(raw.url, base_url=self.url)
            cleaned_body = clean_text(raw.raw_content)
            
            # Use title + content for hash integrity
            hash_input = f"{raw.title}\n{cleaned_body}"
            content_hash = compute_content_hash(hash_input)

            candidate = NormalizedCandidate(
                title=clean_text(raw.title),
                canonical_url=canonical_link,
                source_url=raw.url,
                category=self.category,
                content=cleaned_body,
                content_hash=content_hash,
                source_id=self.source_id,
                published_at=raw.published_at,
                discovered_at=datetime.now(timezone.utc),
            )
            candidates.append(candidate)
        return candidates

    def collect(self) -> List[NormalizedCandidate]:
        """
        Full lifecycle execution for this source adapter.
        Isolated: failure in one source does not affect other collectors.
        """
        logger.info("Executing collector [%s] for source: %s (%s)", self.adapter_key, self.name, self.url)
        raw_payload = self.fetch()
        raw_items = self.extract(raw_payload)
        candidates = self.normalize(raw_items)
        logger.info("Collector [%s] discovered %d candidates", self.adapter_key, len(candidates))
        return candidates
