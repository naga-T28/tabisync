import json

from django.test import TestCase
from django.urls import reverse

from ..models import Itinerary, MemoV2


class MemoV2ViewTests(TestCase):
    def setUp(self):
        self.itinerary = Itinerary.objects.create(title="Test Trip")
        self.view_url = reverse("tabisync:V2_memo", kwargs={"pk": self.itinerary.pk, "token": self.itinerary.token})
        self.edit_url = reverse("tabisync:V2_memo_edit", kwargs={"pk": self.itinerary.pk, "token": self.itinerary.token})

    def test_get_view_page_returns_200(self):
        response = self.client.get(self.view_url)
        self.assertEqual(response.status_code, 200)

    def test_post_edit_saves_notes(self):
        payload = {"notes": [{"content": "持ち物を確認する"}]}
        response = self.client.post(self.edit_url, data=json.dumps(payload), content_type="application/json")
        data = json.loads(response.content.decode("utf-8"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(data["status"], "ok")
        self.assertEqual(data["notes_count"], 1)

        memo = MemoV2.objects.get(itinerary=self.itinerary)
        self.assertIn("持ち物を確認する", memo.content)

    def test_post_edit_rejects_too_many_notes(self):
        payload = {"notes": [{"content": f"メモ{i}"} for i in range(16)]}
        response = self.client.post(self.edit_url, data=json.dumps(payload), content_type="application/json")
        data = json.loads(response.content.decode("utf-8"))

        self.assertEqual(response.status_code, 400)
        self.assertEqual(data["status"], "error")
