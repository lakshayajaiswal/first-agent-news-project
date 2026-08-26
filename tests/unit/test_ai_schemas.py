"""
Unit tests for AI Classifier and Summarizer JSON output contracts and schemas.
"""

import unittest
from src.ai.schemas import (
    ClassifierOutput,
    SummarizerOutput,
    parse_and_validate_classifier_json,
    parse_and_validate_summarizer_json,
)


class TestAISchemas(unittest.TestCase):

    def test_valid_classifier_json_parsing(self):
        valid_json = """{
            "category": "vtu",
            "relevance_score": 0.95,
            "importance_score": 9,
            "urgency": "high",
            "action_required": true,
            "action_summary": "Check revised timetable",
            "confidence_score": 0.93,
            "decision": "accept",
            "reason": "Official VTU notification directly affects the 2025 scheme."
        }"""
        parsed = parse_and_validate_classifier_json(valid_json)
        self.assertEqual(parsed.category, "vtu")
        self.assertEqual(parsed.importance_score, 9)
        self.assertEqual(parsed.decision, "accept")
        self.assertTrue(parsed.action_required)

    def test_invalid_category_fails_validation(self):
        invalid_json = """{
            "category": "sports",
            "relevance_score": 0.5,
            "importance_score": 5,
            "urgency": "low",
            "action_required": false,
            "confidence_score": 0.5,
            "decision": "reject",
            "reason": "Irrelevant"
        }"""
        with self.assertRaises(ValueError):
            parse_and_validate_classifier_json(invalid_json)

    def test_valid_summarizer_json_parsing(self):
        valid_json = """{
            "headline": "Revised VTU examination notification released",
            "what_happened": "VTU published revised examination dates for 2025 scheme.",
            "why_it_matters": "Directly impacts CSE first semester students.",
            "action_required": "Verify exam dates with college coordinator.",
            "key_points": [
                "Theory exams start Sept 20",
                "Internal marks due Sept 5"
            ]
        }"""
        parsed = parse_and_validate_summarizer_json(valid_json)
        self.assertEqual(parsed.headline, "Revised VTU examination notification released")
        self.assertEqual(len(parsed.key_points), 2)


if __name__ == "__main__":
    unittest.main()
