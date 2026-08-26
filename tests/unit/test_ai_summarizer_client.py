"""
Unit tests for AI Summarizer Client.
Tests Gemini output parsing, JSON code-fence cleaning, schema validation, and extractive fallback.
"""

import unittest
from unittest.mock import MagicMock
from src.ai.schemas import SummarizerInput, SummarizerOutput
from src.ai.summarizer_client import AISummarizerClient


class TestAISummarizerClient(unittest.TestCase):

    def setUp(self):
        self.client = AISummarizerClient(api_key=None)

    def test_extractive_fallback_vtu_circular(self):
        inp = SummarizerInput(
            source_title="CIRCULAR: 2025 Scheme 1st Semester Syllabus & Internal Assessment Norms",
            source_url="https://vtu.ac.in/pdf/circular_1042.pdf",
            extracted_source_content="""Ref: VTU/BGM/ACA/2025-26/1042.
The syllabus and continuous internal evaluation (CIE) guidelines for 1st semester B.E. Computer Science under 2025 Scheme are hereby notified.
Theory courses will have 3 CIE tests of 50 marks each.
Practical courses require minimum 8 laboratory experiments.
College coordinators must enter CIE marks on the university portal before 15th December.""",
            category="vtu",
            importance=9,
            action_required=True,
            publication_date="2026-08-25T00:00:00Z"
        )
        summary = self.client.summarize(inp)
        
        self.assertIsInstance(summary, SummarizerOutput)
        self.assertIn("2025 Scheme", summary.headline)
        self.assertTrue(len(summary.what_happened) > 0)
        self.assertIn("2025 engineering scheme", summary.why_it_matters.lower())
        self.assertIsNotNone(summary.action_required)
        self.assertTrue(len(summary.key_points) >= 1)

    def test_extractive_fallback_cybersecurity_cve(self):
        inp = SummarizerInput(
            source_title="Critical RCE in OpenSSH Server (CVE-2026-3392)",
            source_url="https://nvd.nist.gov/vuln/detail/CVE-2026-3392",
            extracted_source_content="""CVSS Score: 9.8 Critical.
A remote unauthenticated code execution vulnerability was identified in OpenSSH server versions prior to 9.8p1.
Actively exploited in the wild according to CISA advisory.
Administrators should update immediately to patched versions or restrict port 22 access.""",
            category="cybersecurity",
            importance=10,
            action_required=True,
            publication_date="2026-08-25T00:00:00Z"
        )
        summary = self.client.summarize(inp)
        
        self.assertEqual(summary.headline, "Critical RCE in OpenSSH Server (CVE-2026-3392)")
        self.assertIn("CVSS Score", summary.what_happened)
        self.assertIn("security advisory", summary.why_it_matters.lower())
        self.assertIn("patches", summary.action_required.lower())

    def test_parse_and_repair_json_with_code_fences(self):
        mock_raw_json = """```json
        {
            "headline": "VTU Timetable for 1st Sem 2025 Scheme Published",
            "what_happened": "Draft timetable for 1st Semester exams published with discrepancy window.",
            "why_it_matters": "Crucial examination dates for 2025 scheme students.",
            "action_required": "Report timetable clashes before Aug 30.",
            "key_points": [
                "Exams begin Sept 20",
                "Discrepancy window closes Aug 30"
            ]
        }
        ```"""
        inp = SummarizerInput(
            source_title="Draft Timetable",
            source_url="https://vtu.ac.in/exams",
            extracted_source_content="Content",
            category="vtu",
            importance=9,
            action_required=True
        )
        parsed = self.client._parse_and_repair_json(mock_raw_json, inp)
        self.assertEqual(parsed.headline, "VTU Timetable for 1st Sem 2025 Scheme Published")
        self.assertEqual(len(parsed.key_points), 2)
        self.assertEqual(parsed.action_required, "Report timetable clashes before Aug 30.")

    def test_gemini_client_mock_invocation(self):
        mock_gemini_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = """{
            "headline": "Gemini 2.5 Flash GA Release",
            "what_happened": "Google released Gemini 2.5 Flash with sub-second latency.",
            "why_it_matters": "Enables faster real-time summarization.",
            "action_required": null,
            "key_points": ["Lower latency", "Improved reasoning"]
        }"""
        mock_gemini_client.models.generate_content.return_value = mock_response

        client = AISummarizerClient(api_key="test_key")
        client._client = mock_gemini_client

        inp = SummarizerInput(
            source_title="Gemini 2.5 Flash Released",
            source_url="https://blog.google/gemini",
            extracted_source_content="New release announcement",
            category="ai",
            importance=8,
            action_required=False
        )
        result = client.summarize(inp)
        self.assertEqual(result.headline, "Gemini 2.5 Flash GA Release")
        self.assertEqual(result.action_required, None)
        self.assertEqual(len(result.key_points), 2)


if __name__ == "__main__":
    unittest.main()
