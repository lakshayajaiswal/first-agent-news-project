"""
AI Classifier Client powered by Gemini 2.5.
Evaluates candidates for relevance, importance, urgency, and actionability.
"""

from __future__ import annotations
import json
import logging
import re
from typing import Any, Dict, Optional

from src.config.settings import get_settings
from src.ai.schemas import ClassifierInput, ClassifierOutput, parse_and_validate_classifier_json
from src.ai.classifier import SYSTEM_INSTRUCTION_CLASSIFIER, build_classifier_prompt
from src.storage.models import Category, Decision, UrgencyLevel

logger = logging.getLogger("ai_agent.ai.classifier")


class AIClassifierClient:
    """Client for performing AI classification using Gemini API or rule-based fallback."""

    def __init__(self, api_key: Optional[str] = None, model_name: Optional[str] = None):
        settings = get_settings()
        self.api_key = api_key or settings.gemini.api_key
        self.model_name = model_name or settings.gemini.model_name
        self._client = None

        if self.api_key and self.api_key != "MY_GEMINI_API_KEY":
            try:
                from google import genai
                self._client = genai.Client(api_key=self.api_key)
                logger.info("Initialized Gemini AI client with model: %s", self.model_name)
            except Exception as e:
                logger.warning("Could not initialize google-genai client (%s). Using fallback engine.", e)

    def classify(self, input_data: ClassifierInput) -> ClassifierOutput:
        """
        Classify a candidate item against user preferences and domain guidelines.
        Returns validated ClassifierOutput.
        """
        prompt = build_classifier_prompt(input_data)

        # 1. If Gemini API client is available and configured, call Gemini
        if self._client and self.api_key:
            try:
                response = self._client.models.generate_content(
                    model=self.model_name,
                    contents=prompt,
                    config={
                        "system_instruction": SYSTEM_INSTRUCTION_CLASSIFIER,
                        "temperature": 0.1,
                        "response_mime_type": "application/json",
                    }
                )
                raw_text = response.text or ""
                return self._parse_and_repair_json(raw_text, input_data)
            except Exception as e:
                logger.error("Gemini API call failed during classification: %s. Falling back to heuristic classifier.", e)

        # 2. Heuristic / Rule-based classifier (offline / sandbox / fallback)
        return self._heuristic_classify(input_data)

    def _parse_and_repair_json(self, raw_text: str, input_data: ClassifierInput) -> ClassifierOutput:
        """Sanitize raw response text, strip markdown fences, and validate against schema."""
        cleaned = raw_text.strip()
        # Strip markdown ```json ... ``` if present
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
            cleaned = re.sub(r"\s*```$", "", cleaned)
            cleaned = cleaned.strip()

        try:
            return parse_and_validate_classifier_json(cleaned)
        except Exception as e:
            logger.warning("Failed to validate JSON response: %s. Attempting repair.", e)
            # Try to extract first JSON object {...}
            match = re.search(r"\{.*\}", cleaned, re.DOTALL)
            if match:
                try:
                    return parse_and_validate_classifier_json(match.group(0))
                except Exception:
                    pass

            # Fallback to safe rejection with reason
            return ClassifierOutput(
                category=input_data.category if input_data.category in [c.value for c in Category] else "development",
                relevance_score=0.3,
                importance_score=3,
                urgency="low",
                action_required=False,
                confidence_score=0.4,
                decision="needs_review",
                reason=f"Classifier response malformed: {str(e)[:100]}",
            )

    def _heuristic_classify(self, input_data: ClassifierInput) -> ClassifierOutput:
        """
        Deterministic rule-based evaluator used in local mode or when API key is not present.
        Accurately flags 2025 VTU scheme circulars, critical CVEs, and high-impact AI releases.
        """
        title_lower = input_data.title.lower()
        content_lower = input_data.extracted_content.lower()
        category_str = input_data.category.lower()

        # VTU Heuristics
        if category_str == "vtu":
            target_scheme = str(input_data.user_preferences.get("scheme", "2025")).lower()
            
            is_relevant_scheme = target_scheme in title_lower or target_scheme in content_lower or "all schemes" in content_lower or "1st sem" in title_lower or "first semester" in content_lower
            is_exam_or_syllabus = any(w in title_lower or w in content_lower for w in ["timetable", "exam", "syllabus", "scheme", "circular", "revaluation", "curriculum", "guideline"])
            is_sports_or_unrelated = any(w in title_lower for w in ["athletic", "sports", "cultural", "tender", "yoga", "hostel mess"])

            if is_sports_or_unrelated:
                return ClassifierOutput(
                    category="vtu",
                    relevance_score=0.15,
                    importance_score=2,
                    urgency="low",
                    action_required=False,
                    confidence_score=0.92,
                    decision="reject",
                    reason="Unrelated sports or non-academic campus activity.",
                )

            if is_relevant_scheme and is_exam_or_syllabus:
                is_urgent = any(w in title_lower or w in content_lower for w in ["timetable", "urgent", "postponed", "rescheduled", "immediate"])
                return ClassifierOutput(
                    category="vtu",
                    relevance_score=0.96,
                    importance_score=9 if is_urgent else 8,
                    urgency="high" if is_urgent else "medium",
                    action_required=True,
                    action_summary=f"Review official VTU notice for {target_scheme} scheme.",
                    confidence_score=0.94,
                    decision="accept",
                    reason=f"Directly addresses VTU {target_scheme} scheme academic regulations / examination schedule.",
                )

            return ClassifierOutput(
                category="vtu",
                relevance_score=0.60,
                importance_score=5,
                urgency="low",
                action_required=False,
                confidence_score=0.80,
                decision="accept" if is_exam_or_syllabus else "reject",
                reason="General VTU circular without explicit 2025 scheme exclusivity.",
            )

        # Cybersecurity Heuristics
        if category_str == "cybersecurity":
            is_critical = any(w in title_lower or w in content_lower for w in ["0-day", "zero-day", "actively exploited", "critical cve", "cvss 9", "cvss 10", "cisa kev", "ransomware"])
            return ClassifierOutput(
                category="cybersecurity",
                relevance_score=0.95 if is_critical else 0.70,
                importance_score=10 if is_critical else 6,
                urgency="critical" if is_critical else "medium",
                action_required=is_critical,
                action_summary="Review patch or mitigation guidelines immediately." if is_critical else None,
                confidence_score=0.90,
                decision="accept",
                reason="High-severity vulnerability or active threat advisory.",
            )

        # AI / Development Heuristics
        is_major = any(w in title_lower or w in content_lower for w in ["release", "model", "gemini", "gpt", "claude", "llama", "python 3", "vulnerability", "breaking change", "announced"])
        return ClassifierOutput(
            category=category_str if category_str in [c.value for c in Category] else "ai",
            relevance_score=0.85 if is_major else 0.50,
            importance_score=7 if is_major else 4,
            urgency="medium" if is_major else "low",
            action_required=False,
            confidence_score=0.85,
            decision="accept" if is_major else "reject",
            reason="Technical software release or foundation model announcement." if is_major else "Low-impact update or promotional content.",
        )
