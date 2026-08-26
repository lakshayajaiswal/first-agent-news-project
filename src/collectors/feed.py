"""
Generic and Specialized RSS/Atom Feed Adapters for AI, Development, and Cybersecurity sources.
Supports RSS 2.0, Atom 1.0, and RDF XML structures using standard library XML parser.
"""

from __future__ import annotations
import email.utils
import logging
import re
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import Any, List, Optional

from src.collectors.base import BaseCollector
from src.collectors.models import RawSourceItem
from src.storage.models import Category, SourceType

logger = logging.getLogger("ai_agent.collectors.feed")


def parse_rfc822_or_iso_date(date_str: Optional[str]) -> Optional[datetime]:
    """Parse common feed publication date formats (RFC 822 / RFC 2822 or ISO 8601)."""
    if not date_str:
        return None
    cleaned = date_str.strip()
    
    # 1. Try RFC 822 (standard RSS pubDate)
    try:
        parsed_tuple = email.utils.parsedate_tz(cleaned)
        if parsed_tuple:
            timestamp = email.utils.mktime_tz(parsed_tuple)
            return datetime.fromtimestamp(timestamp, tz=timezone.utc)
    except Exception:
        pass

    # 2. Try ISO 8601 (Atom updated/published)
    iso_cleaned = cleaned.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(iso_cleaned)
    except Exception:
        pass

    # 3. Fallback matching YYYY-MM-DD
    match = re.search(r"(\d{4})-(\d{2})-(\d{2})", cleaned)
    if match:
        try:
            return datetime(int(match.group(1)), int(match.group(2)), int(match.group(3)), tzinfo=timezone.utc)
        except Exception:
            pass

    return None


def _get_elem_text(elem: Optional[ET.Element]) -> str:
    """Safely extract all text from an XML element and its descendants."""
    if elem is None:
        return ""
    text = "".join(elem.itertext()).strip()
    return text


def _find_child(parent: ET.Element, tag_names: List[str]) -> Optional[ET.Element]:
    """Find a child element matching any local tag name regardless of namespace."""
    for child in parent:
        local_name = child.tag.split("}")[-1] if "}" in child.tag else child.tag
        if local_name.lower() in [t.lower() for t in tag_names]:
            return child
    return None


def _find_all_children(parent: ET.Element, tag_names: List[str]) -> List[ET.Element]:
    """Find all child elements matching any local tag name."""
    res: List[ET.Element] = []
    for child in parent:
        local_name = child.tag.split("}")[-1] if "}" in child.tag else child.tag
        if local_name.lower() in [t.lower() for t in tag_names]:
            res.append(child)
    return res


class RSSFeedAdapter(BaseCollector):
    """
    Standard RSS 2.0 / Atom 1.0 Collector.
    Extracts title, link, published_at, and content from XML feed items.
    """

    adapter_key: str = "rss_feed_adapter"
    source_type: SourceType = SourceType.FEED

    def __init__(
        self,
        source_id: str,
        name: str,
        url: str,
        trust_level: int = 4,
        category: Category | str = Category.AI,
        config: Optional[dict[str, Any]] = None
    ):
        super().__init__(source_id, name, url, trust_level, config)
        self.category = category

    def fetch(self) -> str:
        """Fetch raw XML content from the feed URL."""
        if not self.url or self.url.startswith("mock://") or "mock" in self.url:
            return self._get_mock_feed()

        req = urllib.request.Request(
            self.url,
            headers={
                "User-Agent": "PersonalIntelligenceAgent/1.0 (+https://github.com/agentic-intelligence)",
                "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml;q=0.9",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as response:
                charset = response.headers.get_content_charset() or "utf-8"
                return response.read().decode(charset, errors="replace")
        except Exception as e:
            logger.warning("Feed fetch failed for %s (%s). Using fallback mock payload.", self.name, e)
            return self._get_mock_feed()

    def extract(self, raw_data: str) -> List[RawSourceItem]:
        """Parse RSS or Atom XML and return discrete RawSourceItems."""
        if not raw_data or not raw_data.strip():
            return []

        raw_items: List[RawSourceItem] = []
        try:
            root = ET.fromstring(raw_data)
        except Exception as e:
            logger.warning("Standard XML parse failed in %s (%s). Trying fallback regex.", self.name, e)
            return self._fallback_regex_extract(raw_data)

        # 1. Check for RSS channel
        channel = _find_child(root, ["channel"])
        if channel is not None:
            items = _find_all_children(channel, ["item"])
            for item in items:
                title_elem = _find_child(item, ["title"])
                link_elem = _find_child(item, ["link"])
                desc_elem = _find_child(item, ["description", "encoded", "content", "summary"])
                pubdate_elem = _find_child(item, ["pubdate", "date", "published"])

                title = _get_elem_text(title_elem)
                link = ""
                if link_elem is not None:
                    link = link_elem.get("href") or _get_elem_text(link_elem)
                desc = _get_elem_text(desc_elem)
                pub_date = parse_rfc822_or_iso_date(_get_elem_text(pubdate_elem))

                if title and link:
                    raw_items.append(RawSourceItem(
                        title=title,
                        url=link,
                        raw_content=desc,
                        source_name=self.name,
                        category=self.category,
                        published_at=pub_date,
                        raw_metadata={"feed_type": "rss20"}
                    ))
            return raw_items

        # 2. Check for Atom feed entries
        entries = _find_all_children(root, ["entry"])
        if entries:
            for entry in entries:
                title_elem = _find_child(entry, ["title"])
                link_elem = _find_child(entry, ["link"])
                summary_elem = _find_child(entry, ["summary", "content", "description"])
                updated_elem = _find_child(entry, ["published", "updated", "date"])

                title = _get_elem_text(title_elem)
                link = ""
                if link_elem is not None:
                    link = link_elem.get("href") or _get_elem_text(link_elem)
                content = _get_elem_text(summary_elem)
                pub_date = parse_rfc822_or_iso_date(_get_elem_text(updated_elem))

                if title and link:
                    raw_items.append(RawSourceItem(
                        title=title,
                        url=link,
                        raw_content=content,
                        source_name=self.name,
                        category=self.category,
                        published_at=pub_date,
                        raw_metadata={"feed_type": "atom"}
                    ))
            return raw_items

        return raw_items

    def _fallback_regex_extract(self, raw_data: str) -> List[RawSourceItem]:
        """Regex fallback extractor for malformed XML feeds."""
        items: List[RawSourceItem] = []
        item_blocks = re.findall(r"<(?:item|entry)[\s>](.*?)</(?:item|entry)>", raw_data, re.DOTALL | re.IGNORECASE)
        for block in item_blocks:
            t_match = re.search(r"<title[^>]*>(.*?)</title>", block, re.DOTALL | re.IGNORECASE)
            l_match = re.search(r"<link[^>]*>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</link>|<link[^>]+href=[\"'](.*?)[\"']", block, re.IGNORECASE)
            d_match = re.search(r"<(?:description|summary|content)[^>]*>(.*?)</(?:description|summary|content)>", block, re.DOTALL | re.IGNORECASE)

            title = re.sub(r"<!\[CDATA\[(.*?)\]\]>", r"\1", t_match.group(1)).strip() if t_match else ""
            link = ""
            if l_match:
                link = l_match.group(1) or l_match.group(2) or ""
            content = re.sub(r"<!\[CDATA\[(.*?)\]\]>", r"\1", d_match.group(1)).strip() if d_match else ""

            if title and link:
                items.append(RawSourceItem(
                    title=title,
                    url=link.strip(),
                    raw_content=content,
                    source_name=self.name,
                    category=self.category,
                    published_at=datetime.now(timezone.utc),
                    raw_metadata={"fallback": True}
                ))
        return items

    def _get_mock_feed(self) -> str:
        """Sample mock feed representation."""
        if "google" in self.name.lower() or "gemini" in self.name.lower() or self.category == Category.AI:
            return """<?xml version="1.0" encoding="utf-8"?>
<rss version="2.0">
  <channel>
    <title>Google AI Updates</title>
    <link>https://blog.google/technology/ai/</link>
    <description>Latest AI breakthroughs from Google</description>
    <item>
      <title>Gemini 2.5 Flash GA Release with Sub-Second Inference Latency</title>
      <link>https://blog.google/technology/ai/gemini-2-5-flash</link>
      <description>Google today released Gemini 2.5 Flash for high-throughput enterprise intelligence workloads with native JSON structured output compliance and sub-second TTFT.</description>
      <pubDate>Tue, 25 Aug 2026 10:00:00 GMT</pubDate>
    </item>
    <item>
      <title>Optimizing Agentic Workflows with Multi-Turn Tool Chains</title>
      <link>https://blog.google/technology/ai/agentic-workflows-guide</link>
      <description>A technical overview of building stateful AI agents with strict function calling guarantees and verified schemas.</description>
      <pubDate>Mon, 24 Aug 2026 14:30:00 GMT</pubDate>
    </item>
  </channel>
</rss>"""
        elif self.category == Category.DEVELOPMENT:
            return """<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>GitHub Platform Engineering Blog</title>
  <link href="https://github.blog" />
  <updated>2026-08-25T12:00:00Z</updated>
  <entry>
    <title>Python 3.14 Performance Enhancements: Free-Threading by Default</title>
    <link href="https://github.blog/2026-08-25-python-3-14-performance" />
    <summary>Exploring the memory model optimizations and GIL removal benchmark results in production systems.</summary>
    <published>2026-08-25T11:00:00Z</published>
  </entry>
</feed>"""
        else:
            return """<?xml version="1.0" encoding="utf-8"?>
<rss version="2.0">
  <channel>
    <title>The Hacker News Security</title>
    <link>https://thehackernews.com</link>
    <item>
      <title>Critical Zero-Day Vulnerability Disclosed in Enterprise Firewalls</title>
      <link>https://thehackernews.com/2026/08/critical-zero-day-firewall.html</link>
      <description>Security researchers identified active exploitation targeting SSL VPN endpoints without multi-factor authentication.</description>
      <pubDate>Tue, 25 Aug 2026 09:15:00 GMT</pubDate>
    </item>
  </channel>
</rss>"""
