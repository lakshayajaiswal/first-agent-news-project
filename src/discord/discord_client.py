"""
Discord Webhook Client for Personal AI Intelligence Agent.
Handles immediate critical/urgent alerts and consolidated daily digests with idempotent delivery tracking.
"""

from __future__ import annotations
import json
import logging
import time
import urllib.request
import urllib.error
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timezone

from src.config.settings import get_settings
from src.discord.formatter import format_daily_digest, format_urgent_alert
from src.storage.supabase_client import get_storage_client, SupabaseStorageClient

logger = logging.getLogger("ai_agent.discord.client")


class DiscordClient:
    """Dispatches formatted alerts and digests to Discord webhooks with retry and idempotency."""

    def __init__(
        self,
        webhook_url: Optional[str] = None,
        urgent_webhook_url: Optional[str] = None,
        storage_client: Optional[SupabaseStorageClient] = None,
        dry_run: bool = False,
    ):
        settings = get_settings()
        self.webhook_url = webhook_url if webhook_url is not None else settings.discord.webhook_url
        self.urgent_webhook_url = urgent_webhook_url or self.webhook_url
        self.storage = storage_client or get_storage_client()
        self.dry_run = dry_run or not bool(self.webhook_url)

    def send_urgent_alert(
        self,
        article: Dict[str, Any],
        summary: Dict[str, Any],
        classification: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Send an immediate critical/urgent alert to Discord.
        Guarantees idempotent delivery via Supabase notifications ledger.
        """
        article_id = article.get("id")
        category = article.get("category", "vtu")
        source_url = article.get("canonical_url") or article.get("source_url", "")
        headline = summary.get("headline") or article.get("title", "Urgent Alert")
        what_happened = summary.get("what_happened", "")
        why_it_matters = summary.get("why_it_matters", "")
        action = summary.get("action_required")

        # 1. Register notification record in database for idempotency
        notification, is_new = self.storage.create_or_get_notification(
            article_id=article_id,
            channel="discord",
            message_type="urgent",
        )

        notification_id = notification["id"]

        # If already sent, skip duplicate delivery
        if not is_new and notification.get("status") == "sent":
            logger.info("Notification %s for article %s already sent. Skipping duplicate dispatch.", notification_id, article_id)
            return {
                "status": "already_sent",
                "notification_id": notification_id,
                "article_id": article_id,
                "delivered": False
            }

        # 2. Format message
        formatted_message = format_urgent_alert(
            category=category,
            headline=headline,
            what_happened=what_happened,
            why_it_matters=why_it_matters,
            action=action,
            source_url=source_url,
        )

        # 3. Post to Discord webhook
        target_webhook = self.urgent_webhook_url or self.webhook_url
        success, message_id, error_msg = self._post_webhook(
            url=target_webhook,
            payload={"content": formatted_message},
        )

        # 4. Update notification ledger
        if success:
            self.storage.mark_notification_sent(notification_id, discord_message_id=message_id)
            logger.info("Successfully delivered urgent alert to Discord for article: %s", headline)
            return {
                "status": "sent",
                "notification_id": notification_id,
                "article_id": article_id,
                "discord_message_id": message_id,
                "delivered": True,
            }
        else:
            self.storage.mark_notification_failed(notification_id, error_message=error_msg or "Unknown error")
            logger.error("Failed to deliver urgent alert for article %s: %s", article_id, error_msg)
            return {
                "status": "failed",
                "notification_id": notification_id,
                "article_id": article_id,
                "error": error_msg,
                "delivered": False,
            }

    def send_daily_digest(
        self,
        items_by_category: Dict[str, List[Dict[str, Any]]],
        accepted_count: int,
        rejected_count: int,
        duplicate_count: int,
        digest_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Send formatted daily digest to Discord webhook.
        Splits message into multiple chunks if length exceeds 2000 characters.
        """
        date_str = digest_date or datetime.now(timezone.utc).strftime("%d %b %Y").upper()

        # Register digest notification record
        digest_key = f"digest-{date_str.replace(' ', '-').lower()}"
        notification, is_new = self.storage.create_or_get_notification(
            article_id=None,
            channel="discord",
            message_type=f"daily_digest_{digest_key}",
        )
        notification_id = notification["id"]

        formatted_digest = format_daily_digest(
            items_by_category=items_by_category,
            accepted_count=accepted_count,
            rejected_count=rejected_count,
            duplicate_count=duplicate_count,
            digest_date=date_str,
        )

        chunks = self._chunk_message(formatted_digest, max_length=1950)
        overall_success = True
        last_message_id = None
        last_error = None

        target_webhook = self.webhook_url

        for chunk in chunks:
            success, msg_id, err = self._post_webhook(
                url=target_webhook,
                payload={"content": chunk},
            )
            if success:
                last_message_id = msg_id
            else:
                overall_success = False
                last_error = err
                break

        if overall_success:
            self.storage.mark_notification_sent(notification_id, discord_message_id=last_message_id)
            logger.info("Successfully delivered daily digest for %s to Discord (%d chunks)", date_str, len(chunks))
            return {
                "status": "sent",
                "notification_id": notification_id,
                "chunks_sent": len(chunks),
                "delivered": True,
            }
        else:
            self.storage.mark_notification_failed(notification_id, error_message=last_error or "Chunk delivery failed")
            logger.error("Failed to send daily digest: %s", last_error)
            return {
                "status": "failed",
                "notification_id": notification_id,
                "error": last_error,
                "delivered": False,
            }

    def send_text(self, text: str, webhook_url: Optional[str] = None) -> Tuple[bool, Optional[str], Optional[str]]:
        """Send arbitrary text content to the Discord webhook."""
        target_url = webhook_url or self.webhook_url
        return self._post_webhook(url=target_url, payload={"content": text})

    def format_daily_digest(
        self,
        articles: List[Dict[str, Any]],
        digest_date: Optional[str] = None
    ) -> List[str]:
        """Group accepted articles by category and return formatted Discord message chunks."""
        items_by_category: Dict[str, List[Dict[str, Any]]] = {
            "vtu": [],
            "ai": [],
            "development": [],
            "cybersecurity": []
        }
        for art in articles:
            cat = art.get("category", "vtu")
            if cat not in items_by_category:
                items_by_category[cat] = []
            items_by_category[cat].append(art)

        formatted_raw = format_daily_digest(
            items_by_category=items_by_category,
            accepted_count=len(articles),
            rejected_count=0,
            duplicate_count=0,
            digest_date=digest_date
        )
        return self._chunk_message(formatted_raw, max_length=1950)

    def _chunk_message(self, text: str, max_length: int = 1950) -> List[str]:
        """Split a long text by lines or paragraphs to fit Discord's message size limit."""
        if len(text) <= max_length:
            return [text]

        chunks: List[str] = []
        current_chunk: List[str] = []
        current_len = 0

        for line in text.split("\n"):
            line_len = len(line) + 1
            if current_len + line_len > max_length and current_chunk:
                chunks.append("\n".join(current_chunk))
                current_chunk = [line]
                current_len = line_len
            else:
                current_chunk.append(line)
                current_len += line_len

        if current_chunk:
            chunks.append("\n".join(current_chunk))

        return chunks

    def _post_webhook(self, url: str, payload: Dict[str, Any], max_retries: int = 2) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Execute HTTP POST to Discord webhook with backoff retry on rate limit (429).
        In dry_run or when URL is missing/dummy, returns simulated success.
        """
        if self.dry_run or not url or url.startswith("https://discord.com/api/webhooks/mock"):
            simulated_id = f"msg_mock_{int(time.time())}"
            logger.info("Dry-run / Mock webhook execution: Payload length=%d chars", len(payload.get("content", "")))
            return True, simulated_id, None

        payload_bytes = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=payload_bytes,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "PersonalIntelligenceAgent/1.0",
            },
            method="POST",
        )

        for attempt in range(max_retries + 1):
            try:
                with urllib.request.urlopen(req, timeout=10) as response:
                    resp_body = response.read().decode("utf-8", errors="replace")
                    message_id = None
                    if resp_body:
                        try:
                            resp_json = json.loads(resp_body)
                            message_id = resp_json.get("id")
                        except Exception:
                            pass
                    return True, message_id or f"msg_{int(time.time())}", None
            except urllib.error.HTTPError as e:
                if e.code == 429 and attempt < max_retries:
                    # Discord rate limit
                    retry_after = 1.0
                    try:
                        err_body = json.loads(e.read().decode("utf-8"))
                        retry_after = float(err_body.get("retry_after", 1.0))
                    except Exception:
                        pass
                    logger.warning("Discord rate limited (429). Waiting %.2f seconds before retry.", retry_after)
                    time.sleep(retry_after)
                    continue
                elif e.code in (500, 502, 503, 504) and attempt < max_retries:
                    time.sleep(1.0 * (attempt + 1))
                    continue
                else:
                    err_msg = f"Discord HTTP Error {e.code}: {e.reason}"
                    return False, None, err_msg
            except Exception as e:
                if attempt < max_retries:
                    time.sleep(1.0)
                    continue
                return False, None, str(e)

        return False, None, "Max retries exceeded"
