import json
from datetime import date

from django.test import TestCase
from django.urls import reverse

from ..models import Itinerary, ScheduleV2


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
