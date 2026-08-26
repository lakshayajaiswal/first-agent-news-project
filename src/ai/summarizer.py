"""
AI Summarizer specification and prompt contract.
"""

from __future__ import annotations
from src.ai.schemas import SummarizerInput, SummarizerOutput, parse_and_validate_summarizer_json

SYSTEM_INSTRUCTION_SUMMARIZER = """You are the summarization layer of a personal intelligence agent.
Your task is to produce a factual, grounded, concise summary of an accepted source update.

Rules:
- Do not invent dates.
- Do not invent deadlines.
- Do not infer a requirement unless supported by the source.
- Preserve critical numbers and version identifiers.
- Use plain language.
- Keep summaries concise and scannable.
- Always distinguish official facts from interpretation.
- Return only the required JSON object conforming to the specification schema."""


def build_summarizer_prompt(input_data: SummarizerInput) -> str:
    """Build structured prompt for AI summarizer."""
    return f"""Summarize this accepted update:

Category: {input_data.category}
Source Title: {input_data.source_title}
Source URL: {input_data.source_url}
Publication Date: {input_data.publication_date or 'Unknown'}
Importance: {input_data.importance}/10
Action Required Flag: {input_data.action_required}

Content:
{input_data.extracted_source_content}

Output JSON schema:
{{
  "headline": "Concise factual headline",
  "what_happened": "Clear 1-2 sentence description of what occurred",
  "why_it_matters": "Context on impact for 2025 scheme / developers / security",
  "action_required": "Concrete next step or null",
  "key_points": ["Point 1", "Point 2"]
}}
"""
