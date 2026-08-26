"""
Ingestion & Classification Pipeline Orchestrator.
Coordinates: Source Ingestion -> Multi-level Deduplication -> AI Classification -> Grounded Summarization -> Discord Notification -> Persistence.
"""

from __future__ import annotations
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone

from src.collectors.registry import get_source_registry
from src.collectors.models import NormalizedCandidate
from src.deduplication.matcher import DeduplicationService
from src.ai.classifier_client import AIClassifierClient
from src.ai.summarizer_client import AISummarizerClient
from src.ai.schemas import ClassifierInput, ClassifierOutput, SummarizerInput, SummarizerOutput
from src.discord.discord_client import DiscordClient
from src.storage.supabase_client import get_storage_client, SupabaseStorageClient
from src.storage.models import (
    ArticleModel,
    ClassificationModel,
    SummaryModel,
    Category,
    Decision,
    UrgencyLevel
)

logger = logging.getLogger("ai_agent.pipeline.ingest")


class IngestionPipeline:
    """Orchestrates candidate extraction, deduplication, AI classification, summarization, and notification."""

    def __init__(
        self,
        storage_client: Optional[SupabaseStorageClient] = None,
        classifier_client: Optional[AIClassifierClient] = None,
        summarizer_client: Optional[AISummarizerClient] = None,
        discord_client: Optional[DiscordClient] = None,
        dedup_service: Optional[DeduplicationService] = None,
    ):
        self.storage = storage_client or get_storage_client()
        self.classifier = classifier_client or AIClassifierClient()
        self.summarizer = summarizer_client or AISummarizerClient()
        self.discord = discord_client or DiscordClient(storage_client=self.storage)
        self.dedup = dedup_service or DeduplicationService(title_similarity_threshold=0.70)
        self.registry = get_source_registry()

    def run_source_ingestion(self, source_record: Dict[str, Any], user_preferences: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Run ingestion and classification for a single source.
        Returns execution statistics for this source.
        """
        source_id = source_record.get("id", "src-default")
        source_name = source_record.get("name", "Unknown Source")
        prefs = user_preferences or self.storage.get_user_preferences()

        stats = {
            "source_id": source_id,
            "source_name": source_name,
            "discovered": 0,
            "accepted": 0,
            "rejected": 0,
            "duplicates": 0,
            "summarized": 0,
            "urgent_alerts_sent": 0,
            "errors": 0,
            "articles": []
        }

        try:
            collector = self.registry.create_collector(source_record)
            candidates: List[NormalizedCandidate] = collector.collect()
            stats["discovered"] = len(candidates)

            # Get recent articles for near-duplicate comparison
            existing_articles = self.storage.get_recent_articles(limit=100)

            for candidate in candidates:
                # 1. Level 1 Exact Deduplication (Canonical URL / Content Hash)
                is_exact_dup, dup_reason, orig_id = self.dedup.check_exact_duplicate(
                    canonical_url=candidate.canonical_url,
                    content_hash=candidate.content_hash,
                    existing_articles=existing_articles
                )
                if is_exact_dup:
                    logger.info("Exact duplicate skipped: %s (Reason: %s)", candidate.title, dup_reason)
                    stats["duplicates"] += 1
                    continue

                # 2. Level 2 Near-Duplicate Title Match
                is_near_dup, sim_score, matched_art = self.dedup.check_near_duplicate_title(
                    title=candidate.title,
                    existing_articles=existing_articles
                )
                if is_near_dup:
                    logger.info("Near-duplicate skipped (sim=%.2f): %s", sim_score, candidate.title)
                    stats["duplicates"] += 1
                    continue

                # 3. AI Classification
                cls_input = ClassifierInput(
                    category=candidate.category.value if hasattr(candidate.category, "value") else str(candidate.category),
                    source_name=source_name,
                    source_trust_level=source_record.get("trust_level", 3),
                    title=candidate.title,
                    extracted_content=candidate.content,
                    publication_date=candidate.published_at.isoformat() if candidate.published_at else None,
                    user_preferences=prefs,
                )
                
                classification: ClassifierOutput = self.classifier.classify(cls_input)

                # 4. Save Article to Database
                art_model = ArticleModel(
                    title=candidate.title,
                    canonical_url=candidate.canonical_url,
                    source_url=candidate.source_url,
                    category=Category(classification.category) if classification.category in [c.value for c in Category] else Category.VTU,
                    content=candidate.content,
                    content_hash=candidate.content_hash,
                    source_id=source_id,
                    published_at=candidate.published_at,
                    discovered_at=candidate.discovered_at,
                    status=classification.decision
                )
                saved_article = self.storage.insert_article(art_model)

                # 5. Save Classification Output
                cls_model = ClassificationModel(
                    article_id=saved_article["id"],
                    relevance_score=classification.relevance_score,
                    importance_score=classification.importance_score,
                    urgency=UrgencyLevel(classification.urgency) if classification.urgency in [u.value for u in UrgencyLevel] else UrgencyLevel.LOW,
                    action_required=classification.action_required,
                    action_summary=classification.action_summary,
                    confidence_score=classification.confidence_score,
                    decision=Decision(classification.decision) if classification.decision in [d.value for d in Decision] else Decision.REJECT,
                    reason=classification.reason,
                    model_name=self.classifier.model_name
                )
                saved_cls = self.storage.save_classification(cls_model)

                # Append to existing articles in-memory cache for subsequent item comparisons in this run
                existing_articles.append(saved_article)

                saved_summary = None
                alert_result = None

                if classification.decision == "accept":
                    stats["accepted"] += 1

                    # 6. Grounded AI Summarization for accepted items
                    sum_input = SummarizerInput(
                        source_title=candidate.title,
                        source_url=candidate.canonical_url or candidate.source_url,
                        extracted_source_content=candidate.content,
                        category=classification.category,
                        importance=classification.importance_score,
                        action_required=classification.action_required,
                        publication_date=candidate.published_at.isoformat() if candidate.published_at else None,
                        classifier_decision=classification.decision
                    )
                    summary_output: SummarizerOutput = self.summarizer.summarize(sum_input)
                    
                    sum_model = SummaryModel(
                        article_id=saved_article["id"],
                        headline=summary_output.headline,
                        what_happened=summary_output.what_happened,
                        why_it_matters=summary_output.why_it_matters,
                        action_required=summary_output.action_required,
                        key_points=summary_output.key_points,
                        source_name=source_name,
                        source_url=candidate.canonical_url or candidate.source_url,
                        model_name=self.summarizer.model_name
                    )
                    saved_summary = self.storage.save_summary(sum_model)
                    stats["summarized"] += 1

                    # 7. Urgent Discord Alert Dispatch (Critical urgency or High urgency with action required)
                    if classification.urgency in ("critical", "high") and classification.action_required:
                        alert_result = self.discord.send_urgent_alert(
                            article=saved_article,
                            summary=saved_summary,
                            classification=saved_cls
                        )
                        if alert_result.get("delivered") or alert_result.get("status") == "sent":
                            stats["urgent_alerts_sent"] += 1
                else:
                    stats["rejected"] += 1

                stats["articles"].append({
                    "article": saved_article,
                    "classification": saved_cls,
                    "summary": saved_summary,
                    "alert_result": alert_result
                })

            # Record source health
            self.registry.record_health_metric(
                source_id=source_id,
                source_name=source_name,
                success=True,
                items_discovered=stats["discovered"],
                items_accepted=stats["accepted"]
            )

        except Exception as e:
            logger.error("Error during source ingestion for '%s': %s", source_name, e, exc_info=True)
            stats["errors"] += 1
            self.registry.record_health_metric(
                source_id=source_id,
                source_name=source_name,
                success=False,
                error=str(e)
            )

        return stats

    def generate_and_send_daily_digest(self, digest_date: Optional[str] = None) -> Dict[str, Any]:
        """
        Aggregate all accepted articles and summaries from storage and send daily digest.
        """
        articles = self.storage.get_recent_articles(limit=100)
        items_by_category: Dict[str, List[Dict[str, Any]]] = {
            "vtu": [],
            "ai": [],
            "development": [],
            "cybersecurity": []
        }

        accepted_count = 0
        rejected_count = 0

        for art in articles:
            status = art.get("status")
            cat = str(art.get("category", "vtu")).lower()
            if status == "accept" or status == "accepted":
                accepted_count += 1
                summary = self.storage.get_summary(art["id"])
                item_dict = {
                    "headline": summary.get("headline") if summary else art.get("title"),
                    "what_happened": summary.get("what_happened", "") if summary else "",
                    "why_it_matters": summary.get("why_it_matters", "") if summary else "",
                    "action_required": summary.get("action_required") if summary else None,
                    "source_url": art.get("canonical_url") or art.get("source_url", "")
                }
                if cat not in items_by_category:
                    items_by_category[cat] = []
                items_by_category[cat].append(item_dict)
            elif status == "reject" or status == "rejected":
                rejected_count += 1

        return self.discord.send_daily_digest(
            items_by_category=items_by_category,
            accepted_count=accepted_count,
            rejected_count=rejected_count,
            duplicate_count=0,
            digest_date=digest_date
        )

    # Alias for daily digest dispatching
    dispatch_daily_digest = generate_and_send_daily_digest

    def run_full_pipeline(self, sources: Optional[List[Any]] = None) -> Dict[str, Any]:
        """
        Execute full pipeline across all configured sources with audit logging.
        Accepts a list of dictionaries or SourceModel instances.
        """
        run = self.storage.start_fetch_run()
        sources_to_run = sources or self.storage.get_sources(enabled_only=True)
        
        # If no sources in DB, provide default VTU sources from registry
        if not sources_to_run:
            sources_to_run = [
                {
                    "id": "src-vtu-circ",
                    "name": "VTU Official Circulars",
                    "category": "vtu",
                    "url": "https://vtu.ac.in/circulars",
                    "source_type": "html",
                    "adapter_key": "vtu_circulars_adapter",
                    "enabled": True,
                    "trust_level": 5
                },
                {
                    "id": "src-vtu-exams",
                    "name": "VTU Examination Notifications",
                    "category": "vtu",
                    "url": "https://vtu.ac.in/examination",
                    "source_type": "html",
                    "adapter_key": "vtu_exams_adapter",
                    "enabled": True,
                    "trust_level": 5
                }
            ]

        # Normalize sources if SourceModel objects are passed
        normalized_sources: List[Dict[str, Any]] = []
        for s in sources_to_run:
            if hasattr(s, "to_dict"):
                normalized_sources.append(s.to_dict())
            elif isinstance(s, dict):
                normalized_sources.append(s)
            else:
                normalized_sources.append({
                    "id": getattr(s, "id", "src-custom"),
                    "name": getattr(s, "name", "Custom Source"),
                    "category": getattr(s, "category", "vtu"),
                    "url": getattr(s, "url", ""),
                    "source_type": getattr(s, "source_type", "feed"),
                    "adapter_key": getattr(s, "adapter_key", "rss_feed_adapter"),
                    "trust_level": getattr(s, "trust_level", 4),
                    "enabled": getattr(s, "enabled", True),
                })

        total_discovered = 0
        total_accepted = 0
        total_rejected = 0
        total_duplicates = 0
        total_summarized = 0
        succeeded = 0
        failed = 0
        all_results = []

        for src in normalized_sources:
            res = self.run_source_ingestion(src)
            all_results.append(res)
            
            total_discovered += res["discovered"]
            total_accepted += res["accepted"]
            total_rejected += res["rejected"]
            total_duplicates += res["duplicates"]
            total_summarized += res.get("summarized", 0)

            if res["errors"] == 0:
                succeeded += 1
            else:
                failed += 1

        run_status = "success" if failed == 0 else "partial" if succeeded > 0 else "failed"
        completed_run = self.storage.complete_fetch_run(
            run_id=run.id,
            status=run_status,
            attempted=len(sources_to_run),
            succeeded=succeeded,
            failed=failed,
            discovered=total_discovered,
            accepted=total_accepted,
            rejected=total_rejected,
            duplicates=total_duplicates,
        )

        return {
            "run_id": run.id,
            "status": run_status,
            "sources_attempted": len(normalized_sources),
            "sources_succeeded": succeeded,
            "sources_failed": failed,
            "discovered": total_discovered,
            "accepted": total_accepted,
            "rejected": total_rejected,
            "duplicates": total_duplicates,
            "summarized": total_summarized,
            "source_results": all_results,
        }

    # Alias for pipeline execution
    run = run_full_pipeline
