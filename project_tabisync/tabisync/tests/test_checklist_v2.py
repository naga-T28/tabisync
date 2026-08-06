import json
import re

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


def _extract_json_script(html, element_id):
    match = re.search(
        rf'<script id="{element_id}"[^>]*>(.*?)</script>',
        html,
        re.DOTALL,
    )
    assert match, f"#{element_id} script block not found in response"
    return json.loads(match.group(1))


class ChecklistJsonEmbeddingTests(TestCase):
    """checklists_json|safe から json_script への置き換えがXSSを防ぐことを検証する。"""

    MALICIOUS_TITLE = "</script><script>window.__pwned = true;</script>"
    MALICIOUS_ITEM_TEXT = '<img src=x onerror="window.__pwned = true">\'"&'
    UNICODE_TITLE = "旅行の持ち物リスト 🧳✈️"
    MULTILINE_ITEM_TEXT = "1行目\n2行目\n3行目"

    def setUp(self):
        self.itinerary = Itinerary.objects.create(title="Test Trip")
        self.lists_payload = [
            {
                "id": "list-xss",
                "title": self.MALICIOUS_TITLE,
                "items": [
                    {"id": "item-xss", "text": self.MALICIOUS_ITEM_TEXT, "checked": False},
                ],
            },
            {
                "id": "list-unicode",
                "title": self.UNICODE_TITLE,
                "items": [
                    {"id": "item-multiline", "text": self.MULTILINE_ITEM_TEXT, "checked": True},
                ],
            },
        ]
        ChecklistV2.objects.create(
            itinerary=self.itinerary,
            content=json.dumps(self.lists_payload, ensure_ascii=False),
        )

    def _assert_page_embeds_lists_safely(self, url):
        response = self.client.get(url)
        html = response.content.decode("utf-8")

        self.assertEqual(response.status_code, 200)
        # 危険なペイロードがscriptタグを脱出する形でそのまま出力されていないこと
        self.assertNotIn("</script><script>window.__pwned", html)
        self.assertNotIn("<img src=x onerror=", html)
        # checklists_json（二重JSON化された旧context変数）はもう使われていないこと
        self.assertNotIn("checklists_json", html)

        embedded = _extract_json_script(html, "checklists-data")
        self.assertEqual(embedded[0]["title"], self.MALICIOUS_TITLE)
        self.assertEqual(embedded[0]["items"][0]["text"], self.MALICIOUS_ITEM_TEXT)
        self.assertEqual(embedded[1]["title"], self.UNICODE_TITLE)
        self.assertEqual(embedded[1]["items"][0]["text"], self.MULTILINE_ITEM_TEXT)

    def test_view_page_embeds_lists_safely(self):
        url = reverse("tabisync:V2_list", kwargs={"pk": self.itinerary.pk, "token": self.itinerary.token})
        self._assert_page_embeds_lists_safely(url)

    def test_edit_page_embeds_lists_safely(self):
        url = reverse("tabisync:V2_list_edit", kwargs={"pk": self.itinerary.pk, "token": self.itinerary.token})
        self._assert_page_embeds_lists_safely(url)
