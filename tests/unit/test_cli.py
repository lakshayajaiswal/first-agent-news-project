"""
Unit tests for Main CLI subcommands.
Tests status, check-schema, ingest filtering, health diagnostics, digest dry-run, and sources listing.
"""

import unittest
from src.main import (
    run_schema_check,
    run_system_status,
    run_ingest,
    run_digest,
    run_health,
    run_sources_mgmt,
    run_test_vtu
)


class TestCLICommands(unittest.TestCase):

    def test_schema_check(self):
        exit_code = run_schema_check()
        self.assertEqual(exit_code, 0)

    def test_system_status(self):
        exit_code = run_system_status()
        self.assertEqual(exit_code, 0)

    def test_run_ingest_with_category(self):
        exit_code = run_ingest(category="vtu", force=True)
        self.assertEqual(exit_code, 0)

    def test_run_digest_dry_run(self):
        exit_code = run_digest(date_str="2026-08-25", deliver=False, dry_run=True)
        self.assertEqual(exit_code, 0)

    def test_run_health_telemetry(self):
        exit_code = run_health()
        self.assertEqual(exit_code, 0)

    def test_run_sources_management(self):
        exit_code = run_sources_mgmt(list_all=True)
        self.assertEqual(exit_code, 0)

    def test_test_vtu(self):
        exit_code = run_test_vtu()
        self.assertEqual(exit_code, 0)


if __name__ == "__main__":
    unittest.main()
