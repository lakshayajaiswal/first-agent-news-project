"""
Unit tests for CISA KEV and NIST NVD Cybersecurity Adapters.
Tests KEV catalog parsing, mandatory remediation actions, CVE extraction, and CVSS threshold filtering.
"""

import unittest
from src.collectors.cybersecurity import CISAKEVAdapter, NISTNVDAdapter
from src.storage.models import Category


class TestCybersecurityAdapters(unittest.TestCase):

    def test_cisa_kev_adapter_extraction(self):
        adapter = CISAKEVAdapter(
            source_id="src-cisa-kev",
            name="CISA Known Exploited Vulnerabilities",
            url="mock://cisa-kev"
        )
        candidates = adapter.collect()
        self.assertGreaterEqual(len(candidates), 2)
        
        first = candidates[0]
        self.assertEqual(first.category, Category.CYBERSECURITY)
        self.assertIn("CVE-2026-3392", first.title)
        self.assertIn("OpenSSH", first.title)
        self.assertIn("Required Remediation Action", first.content)
        self.assertIn("nvd.nist.gov", first.canonical_url)

    def test_nist_nvd_adapter_filtering(self):
        adapter = NISTNVDAdapter(
            source_id="src-nist-nvd",
            name="NIST NVD High Severity",
            url="mock://nist-nvd",
            min_cvss_score=7.0
        )
        candidates = adapter.collect()
        self.assertEqual(len(candidates), 1)
        
        cve = candidates[0]
        self.assertEqual(cve.category, Category.CYBERSECURITY)
        self.assertIn("CVE-2026-4401", cve.title)
        self.assertIn("8.8", cve.title)
        self.assertIn("PostgreSQL", cve.content)

    def test_nist_nvd_filters_low_cvss(self):
        adapter = NISTNVDAdapter(
            source_id="src-nist-nvd",
            name="NIST NVD",
            url="mock://nist-nvd",
            min_cvss_score=9.5  # Higher than 8.8
        )
        candidates = adapter.collect()
        self.assertEqual(len(candidates), 0)


if __name__ == "__main__":
    unittest.main()
