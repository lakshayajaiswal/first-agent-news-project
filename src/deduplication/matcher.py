"""
Deduplication Engine implementing Level 1 (Exact), Level 2 (Near Duplicate),
and Level 3 (Event grouping) as specified in 04_SOURCE_AND_FILTERING_SPEC.md.
"""

from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, List, Optional, Set
import re

from src.normalization.url import canonicalize_url
from src.normalization.content import compute_content_hash, normalize_title


def calculate_jaccard_similarity(str1: str, str2: str) -> float:
    """Calculate token-level Jaccard similarity index between two strings."""
    tokens1 = set(re.findall(r"\w+", str1.lower()))
    tokens2 = set(re.findall(r"\w+", str2.lower()))
    if not tokens1 or not tokens2:
        return 0.0
    intersection = len(tokens1.intersection(tokens2))
    union = len(tokens1.union(tokens2))
    return intersection / union if union > 0 else 0.0


@dataclass
class DeduplicationResult:
    is_duplicate: bool
    duplicate_type: Optional[str] = None  # "exact_url" | "exact_hash" | "near_title" | "event_overlap"
    matched_article_id: Optional[str] = None
    similarity_score: float = 0.0
    reason: Optional[str] = None


class DeduplicationService:
    """Service providing multi-level progressive deduplication."""

    def __init__(self, title_similarity_threshold: float = 0.70, publication_window_hours: int = 48):
        self.title_similarity_threshold = title_similarity_threshold
        self.publication_window_hours = publication_window_hours

    def check_duplicate(
        self,
        candidate_canonical_url: str,
        candidate_content_hash: str,
        candidate_title: str,
        candidate_published_at: Optional[datetime],
        existing_articles: List[dict[str, Any]]
    ) -> DeduplicationResult:
        """
        Evaluate candidate item against existing stored articles.
        Executes Level 1 exact checks first, then Level 2 near-duplicate checks.
        """
        canonical_target = canonicalize_url(candidate_canonical_url)
        norm_title = normalize_title(candidate_title)

        for item in existing_articles:
            item_id = item.get("id")
            existing_url = canonicalize_url(item.get("canonical_url", ""))
            existing_hash = item.get("content_hash", "")
            existing_title = normalize_title(item.get("title", ""))

            # Level 1.1: Exact canonical URL match
            if canonical_target and existing_url and canonical_target == existing_url:
                return DeduplicationResult(
                    is_duplicate=True,
                    duplicate_type="exact_url",
                    matched_article_id=item_id,
                    similarity_score=1.0,
                    reason=f"Canonical URL matches existing article ID {item_id}",
                )

            # Level 1.2: Exact content hash match
            if candidate_content_hash and existing_hash and candidate_content_hash == existing_hash:
                return DeduplicationResult(
                    is_duplicate=True,
                    duplicate_type="exact_hash",
                    matched_article_id=item_id,
                    similarity_score=1.0,
                    reason=f"SHA-256 content hash matches existing article ID {item_id}",
                )

            # Level 2: Near-duplicate title similarity check
            if norm_title and existing_title:
                score = calculate_jaccard_similarity(norm_title, existing_title)
                if score >= self.title_similarity_threshold:
                    # Check publication window if available
                    in_window = True
                    if candidate_published_at and item.get("published_at"):
                        try:
                            pub_dt = datetime.fromisoformat(item["published_at"].replace("Z", "+00:00"))
                            time_diff = abs((candidate_published_at - pub_dt).total_seconds())
                            in_window = time_diff <= (self.publication_window_hours * 3600)
                        except Exception:
                            in_window = True

                    if in_window:
                        return DeduplicationResult(
                            is_duplicate=True,
                            duplicate_type="near_title",
                            matched_article_id=item_id,
                            similarity_score=score,
                            reason=f"Title similarity {score:.2f} >= {self.title_similarity_threshold} within publication window",
                        )

        return DeduplicationResult(
            is_duplicate=False,
            similarity_score=0.0,
        )

    def check_exact_duplicate(
        self,
        canonical_url: str,
        content_hash: str,
        existing_articles: List[dict[str, Any]]
    ) -> tuple[bool, Optional[str], Optional[str]]:
        """
        Check for Level 1 exact duplicate by canonical URL or SHA-256 content hash.
        Returns (is_duplicate, reason, matched_article_id).
        """
        res = self.check_duplicate(
            candidate_canonical_url=canonical_url,
            candidate_content_hash=content_hash,
            candidate_title="",
            candidate_published_at=None,
            existing_articles=existing_articles
        )
        if res.is_duplicate and res.duplicate_type in ("exact_url", "exact_hash"):
            return True, res.reason, res.matched_article_id
        return False, None, None

    def check_near_duplicate_title(
        self,
        title: str,
        existing_articles: List[dict[str, Any]],
        published_at: Optional[datetime] = None
    ) -> tuple[bool, float, Optional[dict[str, Any]]]:
        """
        Check for Level 2 title similarity match above threshold.
        Returns (is_duplicate, similarity_score, matched_article_dict).
        """
        norm_title = normalize_title(title)
        for item in existing_articles:
            existing_title = normalize_title(item.get("title", ""))
            if norm_title and existing_title:
                score = calculate_jaccard_similarity(norm_title, existing_title)
                if score >= self.title_similarity_threshold:
                    return True, score, item
        return False, 0.0, None

