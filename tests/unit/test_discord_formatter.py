"""
Unit tests for Discord message formatting (daily digest & urgent alerts).
"""

import unittest
from src.discord.formatter import format_daily_digest, format_urgent_alert


class TestDiscordFormatter(unittest.TestCase):

    def test_format_urgent_alert(self):
        alert_msg = format_urgent_alert(
            category="cybersecurity",
            headline="Critical RCE in OpenSSH (CVE-2026-3392)",
            what_happened="Unauthenticated remote attackers can execute code prior to auth.",
            why_it_matters="Affects Linux servers exposed to public internet.",
            action="Apply vendor patch immediately.",
            source_url="https://nvd.nist.gov/vuln/detail/CVE-2026-3392"
        )
        self.assertIn("CRITICAL ALERT", alert_msg)
        self.assertIn("CYBERSECURITY", alert_msg)
        self.assertIn("CVE-2026-3392", alert_msg)
        self.assertIn("<https://nvd.nist.gov/vuln/detail/CVE-2026-3392>", alert_msg)

    def test_format_daily_digest(self):
        items = {
            "vtu": [
                {
                    "headline": "Revised VTU Examination Dates",
                    "what_happened": "Practical exams scheduled for Sept 10.",
                    "why_it_matters": "Affects 2025 scheme students.",
                    "action_required": "Check center schedule.",
                    "source_url": "https://vtu.ac.in/exams",
                }
            ],
            "ai": [
                {
                    "headline": "Gemini 2.5 Flash Released",
                    "what_happened": "New low-latency model available.",
                    "why_it_matters": "Improves real-time processing.",
                    "source_url": "https://blog.google/gemini",
                }
            ]
        }

        digest = format_daily_digest(
            items_by_category=items,
            accepted_count=2,
            rejected_count=15,
            duplicate_count=3,
            digest_date="25 AUG 2026"
        )

        self.assertIn("PERSONAL INTELLIGENCE DIGEST", digest)
        self.assertIn("25 AUG 2026", digest)
        self.assertIn("VTU UPDATES (2025 SCHEME)", digest)
        self.assertIn("ARTIFICIAL INTELLIGENCE", digest)
        self.assertIn("2 accepted", digest)
        self.assertIn("15 rejected", digest)
        self.assertIn("3 duplicates", digest)


if __name__ == "__main__":
    unittest.main()
