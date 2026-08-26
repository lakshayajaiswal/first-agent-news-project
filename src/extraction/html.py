"""
HTML content extraction and table parser for source pages.
Supports table layouts, WordPress list/accordion containers, and direct link blocks.
"""

from __future__ import annotations
import re
import logging
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

logger = logging.getLogger("ai_agent.extraction.html")


def parse_vtu_circulars_html(html_content: str, base_url: str) -> List[Dict[str, Any]]:
    """
    Parse VTU circulars and examination notifications HTML.
    Supports standard VTU table layouts, WordPress lists, and direct notification anchors.
    """
    if not html_content or not html_content.strip():
        return []

    try:
        from bs4 import BeautifulSoup
        items = _parse_with_bs4(html_content, base_url)
    except ImportError:
        items = _parse_with_regex(html_content, base_url)

    if not items:
        # Fallback to regex link scanner across all anchors
        items = _scan_all_notification_links(html_content, base_url)

    return items


def _parse_with_bs4(html_content: str, base_url: str) -> List[Dict[str, Any]]:
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html_content, "html.parser")
    items: List[Dict[str, Any]] = []

    # 1. Look for tables containing circulars
    tables = soup.find_all("table")
    for table in tables:
        rows = table.find_all("tr")
        for row in rows:
            cols = row.find_all(["td", "th"])
            if not cols or len(cols) < 2:
                continue

            links = row.find_all("a", href=True)
            if not links:
                continue

            primary_link = links[0]
            href = primary_link.get("href", "").strip()
            if not href or href.startswith("#") or href.startswith("javascript:"):
                continue

            absolute_url = urljoin(base_url, href)
            title = primary_link.get_text(strip=True)
            row_text = row.get_text(" ", strip=True)
            
            if len(title) < 5 or title.lower() in ("download", "view", "pdf", "click here", "read more", "details"):
                full_row_text = " - ".join([c.get_text(" ", strip=True) for c in cols if c.get_text(strip=True)])
                if len(full_row_text) > len(title):
                    title = full_row_text

            date_match = re.search(r"(\d{1,2}[-/\.]\d{1,2}[-/\.]\d{2,4}|\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4})", row_text, re.IGNORECASE)
            pub_date = date_match.group(0) if date_match else None

            ref_match = re.search(r"(?:VTU/[A-Za-z0-9_\-\.\/]+|Ref(?:\s*No\.?)?\s*:\s*[A-Za-z0-9_\-\.\/]+)", row_text, re.IGNORECASE)
            ref_no = ref_match.group(0) if ref_match else None

            is_pdf = absolute_url.lower().endswith(".pdf") or "application/pdf" in href.lower()

            items.append({
                "title": title,
                "url": absolute_url,
                "raw_content": f"{title}\n{row_text}",
                "published_date_str": pub_date,
                "reference_number": ref_no,
                "is_pdf": is_pdf,
            })

    # 2. Look for lists (<li>...</li>) or card blocks
    if not items:
        entries = soup.find_all(["li", "p", "div"], class_=re.compile(r"(circular|post|item|news|notice|accordion|entry)", re.IGNORECASE))
        for el in entries:
            links = el.find_all("a", href=True)
            for link in links:
                href = link.get("href", "").strip()
                if not href or href.startswith("#") or href.startswith("javascript:"):
                    continue

                title = link.get_text(strip=True)
                el_text = el.get_text(" ", strip=True)
                if len(title) < 5 and len(el_text) > len(title):
                    title = el_text

                if not title or len(title) < 5:
                    continue

                absolute_url = urljoin(base_url, href)
                date_match = re.search(r"(\d{1,2}[-/\.]\d{1,2}[-/\.]\d{2,4}|\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4})", el_text, re.IGNORECASE)
                pub_date = date_match.group(0) if date_match else None

                items.append({
                    "title": title,
                    "url": absolute_url,
                    "raw_content": el_text,
                    "published_date_str": pub_date,
                    "reference_number": None,
                    "is_pdf": absolute_url.lower().endswith(".pdf"),
                })

    return items


def _parse_with_regex(html_content: str, base_url: str) -> List[Dict[str, Any]]:
    """Regex-based parser for table rows and list items."""
    items: List[Dict[str, Any]] = []
    row_matches = re.findall(r"<tr[^>]*>(.*?)</tr>", html_content, re.DOTALL | re.IGNORECASE)
    for row_html in row_matches:
        link_match = re.search(r'<a\s+[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', row_html, re.DOTALL | re.IGNORECASE)
        if not link_match:
            continue

        href = link_match.group(1).strip()
        link_text = re.sub(r"<[^>]+>", "", link_match.group(2)).strip()
        clean_row = re.sub(r"<[^>]+>", " ", row_html).strip()
        clean_row = re.sub(r"\s+", " ", clean_row)

        if not href or href.startswith("#") or href.startswith("javascript:"):
            continue

        title = link_text
        if len(title) < 5 or title.lower() in ("download", "view", "pdf", "click here", "read more", "details"):
            title = clean_row

        absolute_url = urljoin(base_url, href)
        date_match = re.search(r"(\d{1,2}[-/\.]\d{1,2}[-/\.]\d{2,4}|\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4})", clean_row, re.IGNORECASE)
        pub_date = date_match.group(0) if date_match else None

        ref_match = re.search(r"(?:VTU/[A-Za-z0-9_\-\.\/]+|Ref(?:\s*No\.?)?\s*:\s*[A-Za-z0-9_\-\.\/]+)", clean_row, re.IGNORECASE)
        ref_no = ref_match.group(0) if ref_match else None

        items.append({
            "title": title,
            "url": absolute_url,
            "raw_content": f"{title}\n{clean_row}",
            "published_date_str": pub_date,
            "reference_number": ref_no,
            "is_pdf": absolute_url.lower().endswith(".pdf"),
        })

    return items


def _scan_all_notification_links(html_content: str, base_url: str) -> List[Dict[str, Any]]:
    """Scan all <a> tags that point to PDFs or circulars."""
    items: List[Dict[str, Any]] = []
    link_matches = re.findall(r'<a\s+[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', html_content, re.DOTALL | re.IGNORECASE)
    seen_urls = set()

    for href, raw_text in link_matches:
        href = href.strip()
        text = re.sub(r"<[^>]+>", "", raw_text).strip()
        text = re.sub(r"\s+", " ", text)

        if not href or href.startswith("#") or href.startswith("javascript:"):
            continue

        abs_url = urljoin(base_url, href)
        if abs_url in seen_urls:
            continue

        is_pdf = abs_url.lower().endswith(".pdf")
        is_circular = any(k in abs_url.lower() or k in text.lower() for k in ["circular", "notification", "exam", "timetable", "scheme", "syllabus"])

        if is_pdf or is_circular:
            if len(text) < 5:
                continue
            seen_urls.add(abs_url)
            items.append({
                "title": text,
                "url": abs_url,
                "raw_content": text,
                "published_date_str": None,
                "reference_number": None,
                "is_pdf": is_pdf,
            })

    return items
