"""
AI Classifier specification and prompt contract.
"""

from __future__ import annotations
import json
from src.ai.schemas import ClassifierInput, ClassifierOutput, parse_and_validate_classifier_json

SYSTEM_INSTRUCTION_CLASSIFIER = """You are the classification layer of a personal intelligence agent.
Your task is to determine whether a retrieved source item is relevant to the user's configured interests.
Use only the supplied source content and configuration.
Do not invent facts.
Do not treat speculation as confirmed information.
Do not reward sensational wording.
Prefer primary/official sources.

For VTU, prioritize information that affects the user's 2025 engineering scheme context, examinations, timetable, results, registration, syllabus, scheme, revaluation, summer/supplementary examinations, academic calendar, attendance, or other student-impacting official changes.
For AI/development, prioritize significant technical releases, model/tool changes, developer platform changes, major open-source releases, APIs, frameworks, and engineering developments.
For cybersecurity, prioritize critical/high-impact vulnerabilities, active exploitation, major attacks, malware/ransomware, important advisories, and significant security research.

Return only the required JSON object conforming to the specification schema."""


def build_classifier_prompt(input_data: ClassifierInput) -> str:
    """Build structured prompt for AI classifier."""
    return f"""Analyze this candidate item:

Category: {input_data.category}
Source Name: {input_data.source_name}
Source Trust Level (1-5): {input_data.source_trust_level}
Publication Date: {input_data.publication_date or 'Unknown'}
Title: {input_data.title}

User Target Scheme: {input_data.user_preferences.get('scheme', '2025')}
User Branch: {input_data.user_preferences.get('branch', 'CSE')}

Content:
{input_data.extracted_content}

Output JSON schema:
{{
  "category": "{input_data.category}",
  "relevance_score": 0.95,
  "importance_score": 8,
  "urgency": "low | medium | high | critical",
  "action_required": true | false,
  "action_summary": "Action text if applicable",
  "confidence_score": 0.90,
  "decision": "accept | reject | needs_review",
  "reason": "Brief explanation of relevance/decision grounded in text"
}}
"""
