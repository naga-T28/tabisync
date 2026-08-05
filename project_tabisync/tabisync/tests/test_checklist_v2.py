import json

from django.test import RequestFactory, TestCase
from django.urls import reverse

from ..models import ChecklistV2, Itinerary
from ..views.checklist_v2 import ChecklistV2View


class ChecklistV2ViewTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.itinerary = Itinerary.objects.create(title="Test Trip")

    def test_post_saves_lists_from_view_page(self):
        payload = {
            "lists": [
                {
                    "id": "list-1",
                    "title": "持ち物",
                    "items": [
                        {"id": "item-1", "text": "充電器", "checked": True},
                    ],
                },
                {
                    "id": "list-2",
                    "title": "買い物",
                    "items": [],
                },
            ]
        }
        request = self.factory.generic(
            "POST",
            "/",
            data=json.dumps(payload),
            content_type="application/json",
        )
        view = ChecklistV2View()
        view.itinerary = self.itinerary

        response = view.post(request, pk=self.itinerary.pk, token=self.itinerary.token)
        data = json.loads(response.content.decode("utf-8"))
        checklist = ChecklistV2.objects.get(itinerary=self.itinerary)
        saved_lists = json.loads(checklist.content)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(data["status"], "ok")
        self.assertEqual(data["lists_count"], 2)
        self.assertTrue(saved_lists[0]["items"][0]["checked"])
        self.assertEqual(saved_lists[1]["title"], "買い物")

    def test_get_view_page_returns_200_and_seeds_default_list(self):
        url = reverse("tabisync:V2_list", kwargs={"pk": self.itinerary.pk, "token": self.itinerary.token})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        checklist = ChecklistV2.objects.get(itinerary=self.itinerary)
        self.assertIn("持ち物リスト", checklist.content)
