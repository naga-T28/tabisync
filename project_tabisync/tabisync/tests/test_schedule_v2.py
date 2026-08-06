import json
import threading
from datetime import date

from django.db import connection
from django.test import Client, TestCase, TransactionTestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from ..models import Itinerary, ScheduleV2
from ..views.utils import MAX_SCHEDULES_PER_DAY


class ScheduleV2RowSaveTests(TestCase):
    def setUp(self):
        self.itinerary = Itinerary.objects.create(
            title="Test Trip",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 3),
        )
        self.url = reverse(
            "tabisync:schedule_v2_row_save",
            kwargs={"pk": self.itinerary.pk, "token": self.itinerary.token},
        )

    def test_creates_new_schedule_row(self):
        payload = {
            "title": "朝食",
            "description": "ホテルで朝食",
            "start_time": "08:00",
            "end_time": "09:00",
            "date": "day-1",
            "icon": "food",
        }
        response = self.client.post(self.url, data=json.dumps(payload), content_type="application/json")
        data = json.loads(response.content.decode("utf-8"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(data["status"], "saved")
        self.assertTrue(data["created"])
        self.assertEqual(ScheduleV2.objects.filter(itinerary=self.itinerary).count(), 1)

    def test_rejects_missing_required_fields(self):
        response = self.client.post(self.url, data=json.dumps({}), content_type="application/json")
        data = json.loads(response.content.decode("utf-8"))

        self.assertEqual(response.status_code, 400)
        self.assertEqual(data["status"], "error")

    def test_rejects_out_of_range_day(self):
        payload = {
            "title": "予定",
            "start_time": "08:00",
            "date": "day-99",
        }
        response = self.client.post(self.url, data=json.dumps(payload), content_type="application/json")
        self.assertEqual(response.status_code, 400)

    def test_rejects_when_day_already_at_max_schedules(self):
        for i in range(MAX_SCHEDULES_PER_DAY):
            self.itinerary.schedules.create(
                date=date(2026, 1, 1),
                day_index=1,
                title=f"予定{i}",
                start_time=f"{8 + i % 12:02d}:00",
            )

        payload = {"title": "溢れた予定", "start_time": "23:00", "date": "day-1"}
        response = self.client.post(self.url, data=json.dumps(payload), content_type="application/json")
        data = json.loads(response.content.decode("utf-8"))

        self.assertEqual(response.status_code, 400)
        self.assertEqual(data["status"], "error")
        self.assertEqual(
            ScheduleV2.objects.filter(itinerary=self.itinerary, day_index=1).count(),
            MAX_SCHEDULES_PER_DAY,
        )


class ScheduleV2ConcurrentCreationTests(TransactionTestCase):
    """複数リクエストが同時に1日あたり上限へ書き込もうとしても、上限を超えないことを検証する。

    テストDB(SQLite)は行ロック(select_for_update)を実質サポートしないため、
    このテストが保証するのは「最終的なDB状態が上限を超えない」という不変条件のみであり、
    本番のPostgreSQLで行われる真の直列化そのものを再現するものではない。
    """

    def test_concurrent_saves_do_not_exceed_daily_schedule_limit(self):
        itinerary = Itinerary.objects.create(
            title="Race Trip",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 3),
        )
        url = reverse(
            "tabisync:schedule_v2_row_save",
            kwargs={"pk": itinerary.pk, "token": itinerary.token},
        )

        # 既に上限-1件を埋めておき、残り1枠を複数スレッドで奪い合わせる。
        for i in range(MAX_SCHEDULES_PER_DAY - 1):
            itinerary.schedules.create(
                date=date(2026, 1, 1),
                day_index=1,
                title=f"既存予定{i}",
                start_time=f"{6 + i:02d}:00",
            )

        thread_count = 5
        barrier = threading.Barrier(thread_count)
        outcomes = []
        lock = threading.Lock()

        def worker(index):
            barrier.wait()
            client = Client()
            payload = {
                "title": f"新規予定{index}",
                "start_time": "22:00",
                "date": "day-1",
            }
            try:
                response = client.post(url, data=json.dumps(payload), content_type="application/json")
                outcome = response.status_code
            except Exception:
                outcome = "error"
            with lock:
                outcomes.append(outcome)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(thread_count)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        final_count = ScheduleV2.objects.filter(itinerary=itinerary, day_index=1).count()
        self.assertLessEqual(final_count, MAX_SCHEDULES_PER_DAY, f"outcomes={outcomes}")


class ScheduleV2RowDeleteTests(TestCase):
    def setUp(self):
        self.itinerary = Itinerary.objects.create(
            title="Test Trip",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 3),
        )
        self.schedule = self.itinerary.schedules.create(
            date=date(2026, 1, 1),
            day_index=1,
            title="予定",
            start_time="09:00",
        )
        self.url = reverse(
            "tabisync:schedule_v2_row_delete",
            kwargs={"pk": self.itinerary.pk, "token": self.itinerary.token},
        )

    def test_deletes_existing_row(self):
        response = self.client.post(
            self.url,
            data=json.dumps({"id": self.schedule.id}),
            content_type="application/json",
        )
        data = json.loads(response.content.decode("utf-8"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(data["status"], "deleted")
        self.assertFalse(ScheduleV2.objects.filter(pk=self.schedule.pk).exists())


class ScheduleV2OrderRecomputeTests(TestCase):
    """Task 006: 作成・日移動・削除のいずれの後もorderが0始まりの連番になることを確認する。"""

    def setUp(self):
        self.itinerary = Itinerary.objects.create(
            title="Test Trip",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 3),
        )
        self.save_url = reverse(
            "tabisync:schedule_v2_row_save",
            kwargs={"pk": self.itinerary.pk, "token": self.itinerary.token},
        )
        self.delete_url = reverse(
            "tabisync:schedule_v2_row_delete",
            kwargs={"pk": self.itinerary.pk, "token": self.itinerary.token},
        )

    def _orders_for_day(self, day_index):
        return list(
            ScheduleV2.objects.filter(itinerary=self.itinerary, day_index=day_index)
            .order_by("start_time", "id")
            .values_list("order", flat=True)
        )

    def test_orders_are_contiguous_after_creating_out_of_order(self):
        for start_time in ("18:00", "08:00", "12:00"):
            self.client.post(
                self.save_url,
                data=json.dumps({"title": f"予定{start_time}", "start_time": start_time, "date": "day-1"}),
                content_type="application/json",
            )
        self.assertEqual(self._orders_for_day(1), [0, 1, 2])

    def test_orders_stay_contiguous_after_moving_schedule_to_another_day(self):
        first = self.itinerary.schedules.create(date=date(2026, 1, 1), day_index=1, title="A", start_time="08:00")
        second = self.itinerary.schedules.create(date=date(2026, 1, 1), day_index=1, title="B", start_time="09:00")

        response = self.client.post(
            self.save_url,
            data=json.dumps({
                "id": first.id, "title": "A", "start_time": "08:00", "date": "day-2",
            }),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)

        self.assertEqual(self._orders_for_day(1), [0])
        self.assertEqual(self._orders_for_day(2), [0])
        second.refresh_from_db()
        self.assertEqual(second.order, 0)

    def test_orders_stay_contiguous_after_delete(self):
        first = self.itinerary.schedules.create(date=date(2026, 1, 1), day_index=1, title="A", start_time="08:00")
        self.itinerary.schedules.create(date=date(2026, 1, 1), day_index=1, title="B", start_time="09:00")
        third = self.itinerary.schedules.create(date=date(2026, 1, 1), day_index=1, title="C", start_time="10:00")

        response = self.client.post(
            self.delete_url,
            data=json.dumps({"id": first.id}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)

        self.assertEqual(self._orders_for_day(1), [0, 1])
        third.refresh_from_db()
        self.assertEqual(third.order, 1)


class ScheduleV2RowSaveQueryCountTests(TestCase):
    """Task 006: 同じ日の予定数が増えてもschedule_v2_row_saveのクエリ数が一定であることを確認する。"""

    def _build_itinerary_with_schedules(self, count):
        itinerary = Itinerary.objects.create(
            title=f"Trip-{count}", start_date=date(2026, 1, 1), end_date=date(2026, 1, 3)
        )
        for i in range(count):
            itinerary.schedules.create(
                date=date(2026, 1, 1), day_index=1, title=f"既存{i}", start_time=f"{6 + i:02d}:00"
            )
        return itinerary

    def _post_new_schedule(self, itinerary, start_time="23:30"):
        url = reverse("tabisync:schedule_v2_row_save", kwargs={"pk": itinerary.pk, "token": itinerary.token})
        return self.client.post(
            url,
            data=json.dumps({"title": "新規予定", "start_time": start_time, "date": "day-1"}),
            content_type="application/json",
        )

    def test_query_count_is_constant_regardless_of_existing_schedule_count(self):
        small_itinerary = self._build_itinerary_with_schedules(1)
        large_itinerary = self._build_itinerary_with_schedules(10)

        with CaptureQueriesContext(connection) as small_ctx:
            response = self._post_new_schedule(small_itinerary)
        self.assertEqual(response.status_code, 200)

        with CaptureQueriesContext(connection) as large_ctx:
            response = self._post_new_schedule(large_itinerary)
        self.assertEqual(response.status_code, 200)

        self.assertEqual(
            len(small_ctx.captured_queries),
            len(large_ctx.captured_queries),
            f"small={[q['sql'] for q in small_ctx.captured_queries]}\nlarge={[q['sql'] for q in large_ctx.captured_queries]}",
        )
