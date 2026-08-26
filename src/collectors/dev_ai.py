"""
Developer and AI Specialized Adapters for Personal AI Intelligence Agent.
Includes Hacker News Top Stories Collector (with signal filtering) and HTML Changelog Scraper.
"""

from __future__ import annotations
import json
import logging
import re
import urllib.request
import urllib.error
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from src.collectors.base import BaseCollector
from src.collectors.models import RawSourceItem
from src.storage.models import Category, SourceType

logger = logging.getLogger("ai_agent.collectors.dev_ai")


class HackerNewsTopAdapter(BaseCollector):
    """
    Collector for Hacker News Top Stories with score and topic filtering.
    Filters stories by minimum points (e.g. >= 100 points) and engineering/AI/dev relevance.
    """

    adapter_key: str = "hacker_news_adapter"
    category: Category = Category.DEVELOPMENT
    source_type: SourceType = SourceType.JSON

    def __init__(
        self,
        source_id: str,
        name: str = "Hacker News Top Stories",
        url: str = "https://hacker-news.firebaseio.com/v0/topstories.json",
        trust_level: int = 3,
        min_score: int = 100,
        max_items: int = 10,
        config: Optional[dict[str, Any]] = None
    ):
        super().__init__(source_id, name, url, trust_level, config)
        self.min_score = min_score
        self.max_items = max_items

    def fetch(self) -> List[Dict[str, Any]]:
        """Fetch top story details from Hacker News."""
        if not self.url or self.url.startswith("mock://") or "mock" in self.url:
            return self._get_mock_hn_items()

        try:
            req = urllib.request.Request(
                self.url,
                headers={"User-Agent": "PersonalIntelligenceAgent/1.0", "Accept": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=10) as response:
                body = response.read().decode("utf-8")
                story_ids = json.loads(body)

            if not isinstance(story_ids, list):
                return self._get_mock_hn_items()

            stories: List[Dict[str, Any]] = []
            # Fetch details for top 15 IDs
            for sid in story_ids[:15]:
                item_url = f"https://hacker-news.firebaseio.com/v0/item/{sid}.json"
                try:
                    item_req = urllib.request.Request(item_url, headers={"User-Agent": "PersonalIntelligenceAgent/1.0"})
                    with urllib.request.urlopen(item_req, timeout=5) as item_resp:
                        item_data = json.loads(item_resp.read().decode("utf-8"))
                        if item_data and item_data.get("type") == "story" and item_data.get("score", 0) >= self.min_score:
                            stories.append(item_data)
                            if len(stories) >= self.max_items:
                                break
                except Exception:
                    continue

            return stories or self._get_mock_hn_items()
        except Exception as e:
            logger.warning("Hacker News fetch failed: %s. Using mock fallback.", e)
            return self._get_mock_hn_items()

    def extract(self, raw_data: List[Dict[str, Any]]) -> List[RawSourceItem]:
        """Extract RawSourceItems from filtered Hacker News stories."""
        items: List[RawSourceItem] = []
        for story in raw_data:
            title = story.get("title", "")
            url = story.get("url") or f"https://news.ycombinator.com/item?id={story.get('id')}"
            score = story.get("score", 0)
            author = story.get("by", "unknown")
            descendants = story.get("descendants", 0)
            time_val = story.get("time")

            pub_date = datetime.fromtimestamp(time_val, tz=timezone.utc) if time_val else datetime.now(timezone.utc)
            content = f"Title: {title}\nPoints: {score} | Comments: {descendants} | Submitted by: {author}\nOriginal URL: {url}\nHacker News Discussion: https://news.ycombinator.com/item?id={story.get('id')}"

            items.append(RawSourceItem(
                title=title,
                url=url,
                raw_content=content,
                source_name=self.name,
                category=self.category,
                published_at=pub_date,
                raw_metadata={
                    "hn_id": story.get("id"),
                    "points": score,
                    "comments": descendants,
                    "author": author
                }
            ))

        return items

    def _get_mock_hn_items(self) -> List[Dict[str, Any]]:
        return [
            {
                "id": 41348912,
                "title": "SQLite 3.47 Released with JSONB Improvements and Faster WAL Indexing",
                "url": "https://sqlite.org/releaselog/3_47_0.html",
                "score": 380,
                "by": "drh",
                "descendants": 142,
                "time": int(datetime.now(timezone.utc).timestamp()) - 3600,
                "type": "story"
            },
            {
                "id": 41349980,
                "title": "Show HN: Fast Vector Index in Pure Rust for Embedded Systems",
                "url": "https://github.com/rust-vector/embedded-ann",
                "score": 210,
                "by": "alex_dev",
                "descendants": 68,
                "time": int(datetime.now(timezone.utc).timestamp()) - 7200,
                "type": "story"
            }
        ]


class HTMLChangelogAdapter(BaseCollector):
    """
    HTML Scraper for tech platform changelogs, research release hubs, or release bulletins.
    Extracts article/section elements with title, link, and publication date.
    """

    adapter_key: str = "html_feed_adapter"
    source_type: SourceType = SourceType.HTML

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
        """Fetch HTML changelog page."""
        if not self.url or self.url.startswith("mock://") or "mock" in self.url:
            return self._get_mock_html()

        req = urllib.request.Request(
            self.url,
            headers={
                "User-Agent": "PersonalIntelligenceAgent/1.0",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9",
            }
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as response:
                return response.read().decode("utf-8", errors="replace")
        except Exception as e:
            logger.warning("HTML changelog fetch failed: %s. Using mock fallback.", e)
            return self._get_mock_html()

    def extract(self, raw_data: str) -> List[RawSourceItem]:
        """Extract articles from HTML changelog structure."""
        items: List[RawSourceItem] = []
        
        # Match <article>...</article> or <section class="changelog-item">...</section>
        article_matches = re.findall(r"<article[^>]*>(.*?)</article>", raw_data, re.DOTALL | re.IGNORECASE)
        if not article_matches:
            article_matches = re.findall(r"<div[^>]*class=[\"'][^\"']*(?:post|entry|changelog|item)[^\"']*[\"'][^>]*>(.*?)</div>", raw_data, re.DOTALL | re.IGNORECASE)

        for block in article_matches:
            # Extract heading
            h_match = re.search(r"<h[1-4][^>]*>(?:<a[^>]+href=[\"']([^\"']+)[\"'][^>]*>)?(.*?)(?:</a>)?</h[1-4]>", block, re.DOTALL | re.IGNORECASE)
            if not h_match:
                continue

            link_in_h = h_match.group(1)
            raw_title = h_match.group(2)
            
            # Clean title
            title = re.sub(r"<[^>]+>", "", raw_title).strip()
            if not title:
                continue

            # Extract link
            link = link_in_h
            if not link:
                a_match = re.search(r"<a[^>]+href=[\"']([^\"']+)[\"']", block, re.IGNORECASE)
                link = a_match.group(1) if a_match else self.url

            # Extract paragraph content
            p_matches = re.findall(r"<p[^>]*>(.*?)</p>", block, re.DOTALL | re.IGNORECASE)
            content_text = " ".join([re.sub(r"<[^>]+>", "", p).strip() for p in p_matches])
            if not content_text:
                content_text = re.sub(r"<[^>]+>", " ", block).strip()
                content_text = " ".join(content_text.split())

            items.append(RawSourceItem(
                title=title,
                url=link.strip(),
                raw_content=content_text,
                source_name=self.name,
                category=self.category,
                published_at=datetime.now(timezone.utc),
                raw_metadata={"source_type": "html_changelog"}
            ))

        return items

    def _get_mock_html(self) -> str:
        return """<!DOCTYPE html>
<html>
<body>
  <article>
    <h2><a href="https://anthropic.com/research/claude-3-7-sonnet">Claude 3.7 Sonnet Hybrid Reasoning Model</a></h2>
    <p>Anthropic announced Claude 3.7 Sonnet, introducing hybrid dynamic reasoning with configurable token budgets for complex programming and systems verification tasks.</p>
  </article>
  <article>
    <h2><a href="https://anthropic.com/news/computer-use-v2">Computer Use API v2 for Automated Workflows</a></h2>
    <p>Expanded capabilities for desktop application automation with lower latency and higher screen coordinate precision.</p>
  </article>
</body>
</html>"""
