from datetime import date

from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase


class BackfillScheduleV2DayIndexMigrationTests(TransactionTestCase):
    """Task 006: 旧day_index=NULLデータがmigrationで正しく補完されることを確認する。

    day_indexは現在の最新スキーマではNOT NULLのため、通常のORM経由ではNULLデータを
    再現できない。migration 0020時点(NULL許容)のスキーマまで一時的に戻してNULL行を
    作成し、0021(データ補完)・0022(NOT NULL化)まで適用して結果を検証する。
    テスト終了後は必ず最新migrationへ戻す。
    """

    def setUp(self):
        self.executor = MigrationExecutor(connection)
        self.leaf = self.executor.loader.graph.leaf_nodes()

    def tearDown(self):
        # 後続テストへ影響しないよう、必ず最新migrationへ戻す。
        executor = MigrationExecutor(connection)
        executor.migrate(self.leaf)

    def test_backfills_null_day_index_from_itinerary_start_date(self):
        self.executor.migrate([("tabisync", "0020_itinerary_blog_embed_token")])
        old_apps = self.executor.loader.project_state(
            [("tabisync", "0020_itinerary_blog_embed_token")]
        ).apps

        OldItinerary = old_apps.get_model("tabisync", "Itinerary")
        OldScheduleV2 = old_apps.get_model("tabisync", "ScheduleV2")

        itinerary = OldItinerary.objects.create(
            title="Legacy Trip",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 3),
            total_days=3,
        )
        schedule_with_null = OldScheduleV2.objects.create(
            itinerary=itinerary,
            date=date(2026, 1, 3),
            day_index=None,
            title="旧予定",
            start_time="09:00",
        )
        schedule_already_set = OldScheduleV2.objects.create(
            itinerary=itinerary,
            date=date(2026, 1, 1),
            day_index=1,
            title="既に設定済みの予定",
            start_time="10:00",
        )

        executor = MigrationExecutor(connection)
        executor.migrate([("tabisync", "0022_alter_schedulev2_day_index_and_more")])
        new_apps = executor.loader.project_state(
            [("tabisync", "0022_alter_schedulev2_day_index_and_more")]
        ).apps
        NewScheduleV2 = new_apps.get_model("tabisync", "ScheduleV2")

        migrated_null_schedule = NewScheduleV2.objects.get(pk=schedule_with_null.pk)
        migrated_existing_schedule = NewScheduleV2.objects.get(pk=schedule_already_set.pk)

        # 2026-01-03 は開始日(2026-01-01)から2日後 -> Day 3
        self.assertEqual(migrated_null_schedule.day_index, 3)
        # 既にday_indexが設定済みだった行は変更されない
        self.assertEqual(migrated_existing_schedule.day_index, 1)
