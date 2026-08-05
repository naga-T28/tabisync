import json
from datetime import date

from django.test import TestCase
from django.urls import reverse

from ..models import Itinerary, WantToGo


class WantToGoV2ViewTests(TestCase):
    def setUp(self):
        self.itinerary = Itinerary.objects.create(
            title="Test Trip",
            want_to_go_limit=2,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 3),
        )
        self.url = reverse(
            "tabisync:Wantedit",
            kwargs={"pk": self.itinerary.pk, "token": self.itinerary.token},
        )

    def test_get_returns_200(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_save_want_to_go_creates_place(self):
        payload = {"action": "save_want_to_go", "name": "首里城", "address": "那覇市"}
        response = self.client.post(self.url, data=json.dumps(payload), content_type="application/json")
        data = json.loads(response.content.decode("utf-8"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(data["status"], "saved")
        self.assertEqual(WantToGo.objects.filter(itinerary=self.itinerary).count(), 1)

    def test_save_want_to_go_rejects_over_limit(self):
        self.itinerary.want_to_go_list.create(name="スポット1")
        self.itinerary.want_to_go_list.create(name="スポット2")

        payload = {"action": "save_want_to_go", "name": "スポット3"}
        response = self.client.post(self.url, data=json.dumps(payload), content_type="application/json")
        data = json.loads(response.content.decode("utf-8"))

        self.assertEqual(response.status_code, 400)
        self.assertEqual(data["status"], "error")
        self.assertEqual(WantToGo.objects.filter(itinerary=self.itinerary).count(), 2)

    def test_delete_want_to_go_removes_place(self):
        place = self.itinerary.want_to_go_list.create(name="削除対象")
        payload = {"action": "delete_want_to_go", "id": place.id}
        response = self.client.post(self.url, data=json.dumps(payload), content_type="application/json")
        data = json.loads(response.content.decode("utf-8"))

        self.assertEqual(data["status"], "deleted")
        self.assertFalse(WantToGo.objects.filter(pk=place.pk).exists())
