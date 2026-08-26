"""
Integration tests verifying database entity lifecycle, relationships, and constraints.
"""

import unittest
from datetime import datetime, timezone
from src.storage.models import (
    SourceModel,
    ArticleModel,
    ClassificationModel,
    SummaryModel,
    NotificationModel,
    FetchRunModel,
    Category,
    SourceType,
    UrgencyLevel,
    Decision,
    MessageType,
)
from src.storage.supabase_client import SupabaseStorageClient


class TestDatabaseContract(unittest.TestCase):

    def setUp(self):
        self.client = SupabaseStorageClient()

    def test_full_pipeline_persistence_contract(self):
        # 1. Source creation
        src = SourceModel(
            name="VTU Examination Cell",
            category=Category.VTU,
            url="https://vtu.ac.in/exams",
            source_type=SourceType.HTML,
            adapter_key="vtu_exams_adapter",
        )
        saved_src = self.client.upsert_source(src)
        self.assertIsNotNone(saved_src["id"])

        # 2. Article creation
        art = ArticleModel(
            title="VTU 2025 Scheme Timetable Released",
            canonical_url="https://vtu.ac.in/circulars/timetable-2025.html",
            source_url="https://vtu.ac.in/circulars/timetable-2025.html",
            category=Category.VTU,
            content="Official circular regarding examination timetable for 2025 scheme students.",
            content_hash="mock_sha256_hash_12345",
            source_id=saved_src["id"],
            status="accepted"
        )
        saved_art = self.client.insert_article(art)
        self.assertIsNotNone(saved_art["id"])

        # 3. Classification persistence
        cls_model = ClassificationModel(
            article_id=saved_art["id"],
            relevance_score=0.98,
            importance_score=9,
            urgency=UrgencyLevel.HIGH,
            action_required=True,
            action_summary="Verify subject dates on student portal.",
            confidence_score=0.95,
            decision=Decision.ACCEPT,
            reason="Directly impacts 2025 scheme examination schedule.",
            model_name="gemini-2.5-flash"
        )
        saved_cls = self.client.save_classification(cls_model)
        self.assertEqual(saved_cls["article_id"], saved_art["id"])
        self.assertEqual(saved_cls["decision"], "accept")

        # 4. Summary persistence
        sum_model = SummaryModel(
            article_id=saved_art["id"],
            headline="VTU 2025 Scheme Timetable Released",
            what_happened="VTU announced the official examination schedule for 2025 engineering scheme.",
            why_it_matters="Mandatory for 1st semester examinations.",
            action_required="Download PDF and review dates.",
            key_points=["Theory starts Sept 20", "Practical starts Sept 10"],
            source_name=saved_src["name"],
            source_url=saved_art["canonical_url"],
            model_name="gemini-2.5-flash"
        )
        saved_sum = self.client.save_summary(sum_model)
        self.assertEqual(saved_sum["article_id"], saved_art["id"])
        self.assertEqual(len(saved_sum["key_points"]), 2)

        # 5. Notification tracking
        notif, created = self.client.create_or_get_notification(
            article_id=saved_art["id"],
            channel="discord",
            message_type=MessageType.DAILY_DIGEST
        )
        self.assertTrue(created)
        self.assertEqual(notif["status"], "pending")

        # Mark sent
        self.client.mark_notification_sent(notif["id"], discord_message_id="msg_998877")
        retrieved_notif = self.client._notifications[notif["id"]]
        self.assertEqual(retrieved_notif["status"], "sent")
        self.assertEqual(retrieved_notif["discord_message_id"], "msg_998877")

        # 6. Fetch run auditability
        run = self.client.start_fetch_run()
        self.client.complete_fetch_run(
            run_id=run.id,
            status="success",
            attempted=1,
            succeeded=1,
            failed=0,
            discovered=1,
            accepted=1,
            rejected=0,
            duplicates=0
        )
        completed_run = self.client._fetch_runs[run.id]
        self.assertEqual(completed_run["status"], "success")
        self.assertEqual(completed_run["articles_accepted"], 1)


if __name__ == "__main__":
    unittest.main()
