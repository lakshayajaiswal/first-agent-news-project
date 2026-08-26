"""
PDF document extraction module for VTU circulars and official notifications.
Extracts text, scheme mentions, reference numbers, and dates from PDF bytes or files.
"""

from __future__ import annotations
import io
import re
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger("ai_agent.extraction.pdf")


def extract_text_from_pdf_bytes(pdf_bytes: bytes, max_pages: int = 5) -> Dict[str, Any]:
    """
    Extract text and metadata from PDF bytes using pypdf.
    Gracefully handles corrupted or non-standard PDF formats.
    """
    result: Dict[str, Any] = {
        "text": "",
        "page_count": 0,
        "scheme_mentions": [],
        "reference_number": None,
        "date_mentioned": None,
        "is_successful": False,
        "error": None
    }

    if not pdf_bytes:
        result["error"] = "Empty PDF bytes provided"
        return result

    try:
        from pypdf import PdfReader
        stream = io.BytesIO(pdf_bytes)
        reader = PdfReader(stream)
        
        result["page_count"] = len(reader.pages)
        pages_to_extract = min(len(reader.pages), max_pages)
        
        extracted_chunks = []
        for i in range(pages_to_extract):
            try:
                page_text = reader.pages[i].extract_text() or ""
                if page_text.strip():
                    extracted_chunks.append(page_text.strip())
            except Exception as e:
                logger.warning("Error extracting page %d: %s", i + 1, e)

        full_text = "\n\n".join(extracted_chunks)
        result["text"] = full_text
        result["is_successful"] = bool(full_text.strip())

        # Extract scheme indicators (e.g., 2025 scheme, 2022 scheme, 2021 scheme)
        schemes = set(re.findall(r"\b(20(?:18|21|22|24|25|26))\s*(?:Scheme|scheme)?\b", full_text, re.IGNORECASE))
        result["scheme_mentions"] = sorted(list(schemes))

        # Extract reference numbers (e.g., VTU/BGM/ACA-OS/2025-26/1024)
        ref_match = re.search(r"VTU/[A-Z0-9_\-\.\/]+(?:/\d+)?", full_text, re.IGNORECASE)
        if ref_match:
            result["reference_number"] = ref_match.group(0)

        # Extract dates
        date_match = re.search(r"(?:Dated?|Date\s*:?)\s*(\d{1,2}[-/\.]\d{1,2}[-/\.]\d{2,4}|\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4})", full_text, re.IGNORECASE)
        if date_match:
            result["date_mentioned"] = date_match.group(1)

    except ImportError:
        logger.warning("pypdf is not installed or available. Falling back to plain text handling.")
        result["error"] = "pypdf library not available"
    except Exception as e:
        logger.error("Failed to parse PDF bytes: %s", e)
        result["error"] = str(e)

    return result
