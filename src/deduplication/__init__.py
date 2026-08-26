"""
Deduplication module exports.
"""

from src.deduplication.matcher import (
    DeduplicationService,
    DeduplicationResult,
    calculate_jaccard_similarity,
)

__all__ = [
    "DeduplicationService",
    "DeduplicationResult",
    "calculate_jaccard_similarity",
]
