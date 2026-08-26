"""
Discord Message Formatting according to 06_DISCORD_API_SPEC.md.
"""

from __future__ import annotations
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


def format_urgent_alert(
    category: str,
    headline: str,
    what_happened: str,
    why_it_matters: str,
    action: Optional[str],
    source_url: str
) -> str:
    """Format an immediate critical/urgent alert for Discord delivery."""
    action_text = action if action else "None required."
    return f"""🚨 **CRITICAL ALERT**

**Category:** {category.upper()}
**Headline:** {headline}

**What happened:**
{what_happened}

**Why it matters:**
{why_it_matters}

**Action:**
{action_text}

**Source:**
<{source_url}>"""


def format_daily_digest(
    items_by_category: Dict[str, List[Dict[str, Any]]],
    accepted_count: int,
    rejected_count: int,
    duplicate_count: int,
    digest_date: Optional[str] = None
) -> str:
    """Format standard daily digest grouping stories by category with run statistics."""
    date_str = digest_date or datetime.now(timezone.utc).strftime("%d %b %Y").upper()
    
    sections = [f"📰 **PERSONAL INTELLIGENCE DIGEST**\n_{date_str}_\n"]

    category_titles = {
        "vtu": "🎓 VTU UPDATES (2025 SCHEME)",
        "ai": "🤖 ARTIFICIAL INTELLIGENCE",
        "development": "💻 SOFTWARE DEVELOPMENT",
        "cybersecurity": "🛡️ CYBERSECURITY",
    }

    for cat_key, title in category_titles.items():
        items = items_by_category.get(cat_key, [])
        if items:
            sections.append(f"### {title}")
            for item in items:
                headline = item.get("headline", "Update")
                what = item.get("what_happened", "")
                why = item.get("why_it_matters", "")
                action = item.get("action_required")
                url = item.get("source_url", "")

                block = [f"**{headline}**"]
                if what:
                    block.append(f"• **What happened:** {what}")
                if why:
                    block.append(f"• **Why it matters:** {why}")
                if action:
                    block.append(f"• **Action:** {action}")
                if url:
                    block.append(f"• **Source:** <{url}>")
                
                sections.append("\n".join(block) + "\n")

    # Add summary statistics footer
    sections.append(f"📊 **{accepted_count} accepted** • **{rejected_count} rejected** • **{duplicate_count} duplicates**")

    return "\n".join(sections)
