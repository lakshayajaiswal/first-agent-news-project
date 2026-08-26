"""
Unit tests for AI Classifier Client (Gemini API & Heuristic evaluator).
"""

import unittest
from src.ai.classifier_client import AIClassifierClient
from src.ai.schemas import ClassifierInput


class TestAIClassifierClient(unittest.TestCase):

    def setUp(self):
        self.classifier = AIClassifierClient()

    def test_vtu_2025_scheme_circular_classified_as_accepted(self):
        input_data = ClassifierInput(
            category="vtu",
            source_name="VTU Examination Cell",
            source_trust_level=5,
            title="VTU Circular: 2025 Scheme Examination Timetable for 1st Semester B.E.",
            extracted_content="Official notification regarding timetable and eligibility for 2025 engineering scheme students.",
            user_preferences={"scheme": "2025", "branch": "CSE", "semester": "1"}
        )

        output = self.classifier.classify(input_data)
        self.assertEqual(output.category, "vtu")
        self.assertEqual(output.decision, "accept")
        self.assertGreaterEqual(output.relevance_score, 0.8)
        self.assertGreaterEqual(output.importance_score, 7)
        self.assertIn(output.urgency, ["medium", "high", "critical"])
        self.assertTrue(output.action_required)

    def test_vtu_sports_circular_classified_as_rejected(self):
        input_data = ClassifierInput(
            category="vtu",
            source_name="VTU Sports Division",
            source_trust_level=4,
            title="Inter-Collegiate Annual Athletic Meet 2025 at Belagavi Zone",
            extracted_content="Notice regarding sports events, track and field schedules, and team registration.",
            user_preferences={"scheme": "2025", "branch": "CSE", "semester": "1"}
        )

        output = self.classifier.classify(input_data)
        self.assertEqual(output.category, "vtu")
        self.assertEqual(output.decision, "reject")
        self.assertLess(output.relevance_score, 0.5)

    def test_cybersecurity_critical_cve_classified_as_urgent(self):
        input_data = ClassifierInput(
            category="cybersecurity",
            source_name="CISA KEV Catalog",
            source_trust_level=5,
            title="CISA Adds Actively Exploited Zero-Day Vulnerability in Linux Kernel to KEV",
            extracted_content="Critical remote code execution vulnerability (CVSS 9.8) actively exploited in the wild.",
            user_preferences={}
        )

        output = self.classifier.classify(input_data)
        self.assertEqual(output.category, "cybersecurity")
        self.assertEqual(output.decision, "accept")
        self.assertEqual(output.urgency, "critical")
        self.assertEqual(output.importance_score, 10)
        self.assertTrue(output.action_required)

    def test_parse_and_repair_json_with_code_fences(self):
        raw_markdown_json = """```json
        {
          "category": "vtu",
          "relevance_score": 0.95,
          "importance_score": 9,
          "urgency": "high",
          "action_required": true,
          "action_summary": "Check dates on student portal.",
          "confidence_score": 0.90,
          "decision": "accept",
          "reason": "Directly impacts 2025 scheme exams."
        }
        ```"""

        input_data = ClassifierInput(
            category="vtu",
            source_name="VTU",
            source_trust_level=5,
            title="Exam Timetable",
            extracted_content="Content",
        )

        output = self.classifier._parse_and_repair_json(raw_markdown_json, input_data)
        self.assertEqual(output.category, "vtu")
        self.assertEqual(output.decision, "accept")
        self.assertEqual(output.importance_score, 9)


if __name__ == "__main__":
    unittest.main()
