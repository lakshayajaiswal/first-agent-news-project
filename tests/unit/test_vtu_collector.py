"""
Unit tests for VTU source adapters and HTML table extraction.
"""

import unittest
from src.collectors.vtu import VTUCircularsAdapter, VTUExamsAdapter, VTUAcademicAdapter
from src.extraction.html import parse_vtu_circulars_html


SAMPLE_HTML_TABLE = """
<!DOCTYPE html>
<html>
<body>
  <h2>Official Circulars</h2>
  <table class="table-striped">
    <thead>
      <tr><th>Sl.No</th><th>Date</th><th>Circular Details</th><th>Download</th></tr>
    </thead>
    <tbody>
      <tr>
        <td>1</td>
        <td>25.08.2025</td>
        <td>Circular regarding 2025 Scheme First Semester Examination Fee & Schedule. Ref: VTU/BGM/EXAM/2025-26/109</td>
        <td><a href="/pdf/circular-2025-scheme.pdf">Download</a></td>
      </tr>
      <tr>
        <td>2</td>
        <td>22.08.2025</td>
        <td>Postponement of Practical Examination for 2022 Scheme</td>
        <td><a href="https://vtu.ac.in/circulars/2022-exam-postponed.pdf">Click here</a></td>
      </tr>
      <tr>
        <td>3</td>
        <td>18.08.2025</td>
        <td>Inter-Collegiate Football Tournament at Belagavi</td>
        <td><a href="/sports/football-2025.html">Details</a></td>
      </tr>
    </tbody>
  </table>
</body>
</html>
"""


class TestVTUCollector(unittest.TestCase):

    def test_parse_vtu_circulars_html_table(self):
        items = parse_vtu_circulars_html(SAMPLE_HTML_TABLE, base_url="https://vtu.ac.in/circulars/")
        self.assertEqual(len(items), 3)

        # First item check
        item1 = items[0]
        self.assertIn("2025 Scheme First Semester", item1["title"])
        self.assertEqual(item1["url"], "https://vtu.ac.in/pdf/circular-2025-scheme.pdf")
        self.assertTrue(item1["is_pdf"])
        self.assertIsNotNone(item1["reference_number"])
        self.assertIn("25.08.2025", item1["published_date_str"])

    def test_vtu_circulars_adapter_lifecycle(self):
        adapter = VTUCircularsAdapter(
            source_id="src-vtu-test",
            name="VTU Circulars",
            url="https://vtu.ac.in/circulars"
        )
        items = adapter.extract(SAMPLE_HTML_TABLE)
        self.assertEqual(len(items), 3)

        candidates = adapter.normalize(items)
        self.assertEqual(len(candidates), 3)
        self.assertEqual(candidates[0].category.value if hasattr(candidates[0].category, "value") else candidates[0].category, "vtu")
        self.assertTrue(candidates[0].content_hash)
        self.assertEqual(candidates[0].canonical_url, "https://vtu.ac.in/pdf/circular-2025-scheme.pdf")

    def test_vtu_adapter_fallback_mock_data(self):
        adapter = VTUExamsAdapter(
            source_id="src-vtu-exams",
            name="VTU Exams",
            url="https://vtu.ac.in/exams"
        )
        # Empty payload triggers sample circulars in offline/mock mode
        items = adapter.extract("")
        self.assertGreater(len(items), 0)
        self.assertTrue(any("exam" in i.title.lower() or "timetable" in i.title.lower() for i in items))


if __name__ == "__main__":
    unittest.main()
