"""
Content Normalization, Text Sanitization, and Cryptographic Fingerprinting.
"""

from __future__ import annotations
import hashlib
import re
import unicodedata


def clean_text(text: str) -> str:
    """Normalize unicode, whitespace, and non-printable characters."""
    if not text:
        return ""
    # Normalize unicode to NFKC
    normalized = unicodedata.normalize("NFKC", text)
    # Collapse multiple whitespaces and newlines
    cleaned = re.sub(r"\s+", " ", normalized).strip()
    return cleaned


def normalize_title(title: str) -> str:
    """Normalize title for fuzzy comparisons (lowercased, punctuation removed, trimmed)."""
    if not title:
        return ""
    # Remove HTML tags if present
    cleaned = re.sub(r"<[^>]+>", "", title)
    cleaned = clean_text(cleaned).lower()
    # Strip common site suffixes like " | VTU", " - Hacker News", etc.
    cleaned = re.sub(r"\s+[|\-–—]\s+.*$", "", cleaned)
    # Remove non-alphanumeric except spaces
    cleaned = re.sub(r"[^\w\s]", "", cleaned)
    return re.sub(r"\s+", " ", cleaned).strip()


def compute_content_hash(text: str) -> str:
    """Generate deterministic SHA-256 hash of cleaned content."""
    normalized = clean_text(text).lower()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()
