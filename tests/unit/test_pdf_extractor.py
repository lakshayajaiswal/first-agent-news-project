"""
Unit tests for PDF document text and scheme extraction.
"""

import unittest
from src.extraction.pdf import extract_text_from_pdf_bytes


class TestPDFExtractor(unittest.TestCase):

    def test_extract_from_empty_bytes(self):
        res = extract_text_from_pdf_bytes(b"")
        self.assertFalse(res["is_successful"])
        self.assertIsNotNone(res["error"])

    def test_extract_invalid_pdf_bytes_fails_gracefully(self):
        res = extract_text_from_pdf_bytes(b"NOT_A_REAL_PDF_HEADER_12345")
        self.assertFalse(res["is_successful"])
        self.assertIsNotNone(res["error"])


if __name__ == "__main__":
    unittest.main()
