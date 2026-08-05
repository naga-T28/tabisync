import json
import threading
from datetime import date

from django.test import Client, TestCase, TransactionTestCase
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
