"""
Test fixtures and configuration for pytest and unittest test suites.
"""

import json
import os
from typing import Any, Dict


def load_fixture(fixture_name: str) -> Dict[str, Any]:
    """Load JSON fixture from tests/fixtures directory."""
    current_dir = os.path.dirname(__file__)
    fixture_path = os.path.join(current_dir, "fixtures", fixture_name)
    with open(fixture_path, "r", encoding="utf-8") as f:
        return json.load(f)
