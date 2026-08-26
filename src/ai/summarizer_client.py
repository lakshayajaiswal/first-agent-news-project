"""
AI Summarizer Client powered by Gemini 2.5.
Produces factual, grounded, structured summaries for accepted intelligence items with strict source attribution.
"""

from __future__ import annotations
import json
import logging
import re
from typing import Any, Dict, List, Optional

from src.config.settings import get_settings
from src.ai.schemas import SummarizerInput, SummarizerOutput, parse_and_validate_summarizer_json
from src.ai.summarizer import SYSTEM_INSTRUCTION_SUMMARIZER, build_summarizer_prompt

logger = logging.getLogger("ai_agent.ai.summarizer")


class AISummarizerClient:
    """Client for generating grounded AI summaries using Gemini 2.5 or deterministic fallback."""

    def __init__(self, api_key: Optional[str] = None, model_name: Optional[str] = None):
        settings = get_settings()
        self.api_key = api_key or settings.gemini.api_key
        self.model_name = model_name or settings.gemini.model_name
        self._client = None

        if self.api_key and self.api_key != "MY_GEMINI_API_KEY":
            try:
                from google import genai
                self._client = genai.Client(api_key=self.api_key)
                logger.info("Initialized Gemini AI client for summarizer with model: %s", self.model_name)
            except Exception as e:
                logger.warning("Could not initialize google-genai client for summarizer (%s). Using fallback engine.", e)

    def summarize(self, input_data: SummarizerInput) -> SummarizerOutput:
        """
        Generate a factual, grounded summary for an accepted candidate.
        Returns validated SummarizerOutput.
        """
        prompt = build_summarizer_prompt(input_data)

        # 1. If Gemini API client is available and configured, call Gemini
        if self._client and self.api_key:
            try:
                response = self._client.models.generate_content(
                    model=self.model_name,
                    contents=prompt,
                    config={
                        "system_instruction": SYSTEM_INSTRUCTION_SUMMARIZER,
                        "temperature": 0.1,
                        "response_mime_type": "application/json",
                    }
                )
                raw_text = response.text or ""
                return self._parse_and_repair_json(raw_text, input_data)
            except Exception as e:
                logger.error("Gemini API call failed during summarization: %s. Falling back to extractive summarizer.", e)

        # 2. Deterministic extractive summarizer fallback (offline / tests / fallback)
        return self._extractive_fallback_summarize(input_data)

    def _parse_and_repair_json(self, raw_text: str, input_data: SummarizerInput) -> SummarizerOutput:
        """Sanitize raw response text, strip markdown code fences, and validate schema."""
        cleaned = raw_text.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
            cleaned = re.sub(r"\s*```$", "", cleaned)
            cleaned = cleaned.strip()

        try:
            return parse_and_validate_summarizer_json(cleaned)
        except Exception as e:
            logger.warning("Failed to validate Summarizer JSON response: %s. Attempting repair.", e)
            match = re.search(r"\{.*\}", cleaned, re.DOTALL)
            if match:
                try:
                    return parse_and_validate_summarizer_json(match.group(0))
                except Exception:
                    pass

            return self._extractive_fallback_summarize(input_data)

    def _extractive_fallback_summarize(self, input_data: SummarizerInput) -> SummarizerOutput:
        """
        Grounded extractive fallback summarizer.
        Derives summary strictly from source title and content without hallucinating dates or numbers.
        """
        title = input_data.source_title.strip()
        content = input_data.extracted_source_content.strip()
        
        # Clean title for headline
        headline = re.sub(r"^(?:CIRCULAR|NOTIFICATION|ALERT|ADVISORY):\s*", "", title, flags=re.IGNORECASE)
        if not headline:
            headline = title or "Important Source Update"

        # Split content into non-empty sentences/lines
        lines = [line.strip() for line in content.split("\n") if line.strip()]
        
        # Determine what happened
        what_happened = ""
        if lines:
            first_line = lines[0]
            if len(first_line) > 200:
                first_line = first_line[:197] + "..."
            what_happened = first_line
        else:
            what_happened = f"Update published regarding {headline}."

        # Determine why it matters based on category
        cat_lower = input_data.category.lower()
        if cat_lower == "vtu":
            why_it_matters = "Directly impacts 2025 engineering scheme academic schedules, syllabus, or examination guidelines."
        elif cat_lower == "cybersecurity":
            why_it_matters = "High-priority security advisory requiring awareness or mitigation."
        elif cat_lower == "ai":
            why_it_matters = "Significant artificial intelligence tooling or model architecture release."
        else:
            why_it_matters = "Important software development framework or platform update."

        # Action required
        action_required = None
        if input_data.action_required:
            if cat_lower == "vtu":
                action_required = "Review official notification details and note relevant submission/exam dates."
            elif cat_lower == "cybersecurity":
                action_required = "Check vulnerability exposure and apply recommended patches or mitigations."
            else:
                action_required = "Review release notes and assess compatibility."

        # Key points extraction
        key_points: List[str] = []
        for line in lines[1:5]:
            cleaned_line = re.sub(r"^[-*•\d.]+\s*", "", line).strip()
            if len(cleaned_line) > 10 and len(cleaned_line) < 180:
                key_points.append(cleaned_line)

        if not key_points:
            key_points = [
                f"Source: {input_data.source_url}",
                f"Priority rating: {input_data.importance}/10"
            ]

        output = SummarizerOutput(
            headline=headline,
            what_happened=what_happened,
            why_it_matters=why_it_matters,
            action_required=action_required,
            key_points=key_points[:4]
        )
        return output
