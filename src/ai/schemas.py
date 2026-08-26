"""
Strict Schemas and Validation for AI Layer (Classifier & Summarizer).
Follows specifications in 05_AI_AGENT_SPEC.md.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import json

from src.storage.models import Category, Decision, UrgencyLevel


@dataclass
class ClassifierInput:
    """Structured input supplied to the AI Classifier."""
    category: str
    source_name: str
    source_trust_level: int
    title: str
    extracted_content: str
    publication_date: Optional[str] = None
    user_preferences: Dict[str, Any] = field(default_factory=dict)
    source_rules: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ClassifierOutput:
    """
    Structured output returned by the AI Classifier.
    Exact schema from 05_AI_AGENT_SPEC.md:
    {
      "category": "vtu" | "ai" | "development" | "cybersecurity",
      "relevance_score": float (0.0 to 1.0),
      "importance_score": int (1 to 10),
      "urgency": "low" | "medium" | "high" | "critical",
      "action_required": bool,
      "action_summary": Optional[str],
      "confidence_score": float (0.0 to 1.0),
      "decision": "accept" | "reject" | "needs_review",
      "reason": str
    }
    """
    category: str
    relevance_score: float
    importance_score: int
    urgency: str
    action_required: bool
    confidence_score: float
    decision: str
    reason: str
    action_summary: Optional[str] = None

    def validate(self) -> None:
        """Validate all enum fields, ranges, and types."""
        valid_cats = {c.value for c in Category}
        if self.category not in valid_cats:
            raise ValueError(f"Invalid category '{self.category}'. Expected one of {valid_cats}")

        valid_urgencies = {u.value for u in UrgencyLevel}
        if self.urgency not in valid_urgencies:
            raise ValueError(f"Invalid urgency '{self.urgency}'. Expected one of {valid_urgencies}")

        valid_decisions = {d.value for d in Decision}
        if self.decision not in valid_decisions:
            raise ValueError(f"Invalid decision '{self.decision}'. Expected one of {valid_decisions}")

        if not (0.0 <= self.relevance_score <= 1.0):
            raise ValueError(f"relevance_score {self.relevance_score} must be between 0.0 and 1.0")

        if not (1 <= self.importance_score <= 10):
            raise ValueError(f"importance_score {self.importance_score} must be integer between 1 and 10")

        if not (0.0 <= self.confidence_score <= 1.0):
            raise ValueError(f"confidence_score {self.confidence_score} must be between 0.0 and 1.0")

        if not self.reason or len(self.reason.strip()) == 0:
            raise ValueError("reason cannot be empty")


@dataclass
class SummarizerInput:
    """Input supplied to the AI Summarizer (only for accepted items)."""
    source_title: str
    source_url: str
    extracted_source_content: str
    category: str
    importance: int
    action_required: bool
    publication_date: Optional[str] = None
    classifier_decision: str = "accept"


@dataclass
class SummarizerOutput:
    """
    Structured output returned by the AI Summarizer.
    Exact schema from 05_AI_AGENT_SPEC.md:
    {
      "headline": str,
      "what_happened": str,
      "why_it_matters": str,
      "action_required": Optional[str],
      "key_points": list[str]
    }
    """
    headline: str
    what_happened: str
    why_it_matters: str
    key_points: List[str]
    action_required: Optional[str] = None

    def validate(self) -> None:
        if not self.headline or len(self.headline.strip()) == 0:
            raise ValueError("headline cannot be empty")
        if not self.what_happened or len(self.what_happened.strip()) == 0:
            raise ValueError("what_happened cannot be empty")
        if not self.why_it_matters or len(self.why_it_matters.strip()) == 0:
            raise ValueError("why_it_matters cannot be empty")
        if not isinstance(self.key_points, list):
            raise ValueError("key_points must be a list of strings")


def parse_and_validate_classifier_json(json_str: str) -> ClassifierOutput:
    """Parse JSON string and validate against ClassifierOutput schema."""
    data = json.loads(json_str)
    output = ClassifierOutput(
        category=str(data.get("category", "")).lower(),
        relevance_score=float(data.get("relevance_score", 0.0)),
        importance_score=int(data.get("importance_score", 1)),
        urgency=str(data.get("urgency", "low")).lower(),
        action_required=bool(data.get("action_required", False)),
        action_summary=data.get("action_summary"),
        confidence_score=float(data.get("confidence_score", 0.0)),
        decision=str(data.get("decision", "reject")).lower(),
        reason=str(data.get("reason", "")),
    )
    output.validate()
    return output


def parse_and_validate_summarizer_json(json_str: str) -> SummarizerOutput:
    """Parse JSON string and validate against SummarizerOutput schema."""
    data = json.loads(json_str)
    output = SummarizerOutput(
        headline=str(data.get("headline", "")).strip(),
        what_happened=str(data.get("what_happened", "")).strip(),
        why_it_matters=str(data.get("why_it_matters", "")).strip(),
        action_required=data.get("action_required"),
        key_points=[str(p) for p in data.get("key_points", []) if str(p).strip()],
    )
    output.validate()
    return output
