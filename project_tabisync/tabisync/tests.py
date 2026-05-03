import json

from django.test import RequestFactory, TestCase
from unittest.mock import patch

from .openai_concierge import run_moderation
from .models import ChecklistV2, Itinerary
from .views import (
    ChecklistV2View,
    ConciergeV2View,
    build_public_service_error_message,
    get_client_ip,
    ratelimit_client_ip,
)


class ClientIpTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_get_client_ip_prefers_cloudflare_header(self):
        request = self.factory.get(
            "/",
            REMOTE_ADDR="10.0.0.1",
            HTTP_X_FORWARDED_FOR="198.51.100.10, 10.0.0.1",
            HTTP_CF_CONNECTING_IP="203.0.113.10",
        )

        self.assertEqual(get_client_ip(request), "203.0.113.10")

    def test_get_client_ip_falls_back_to_first_forwarded_ip(self):
        request = self.factory.get(
            "/",
            REMOTE_ADDR="10.0.0.1",
            HTTP_X_FORWARDED_FOR="198.51.100.10, 10.0.0.1",
        )

        self.assertEqual(get_client_ip(request), "198.51.100.10")

    def test_ratelimit_client_ip_uses_same_resolution(self):
        request = self.factory.get("/", REMOTE_ADDR="198.51.100.10")

        self.assertEqual(ratelimit_client_ip(None, request), "198.51.100.10")

    def test_get_client_ip_ignores_invalid_proxy_headers(self):
        request = self.factory.get(
            "/",
            REMOTE_ADDR="198.51.100.10",
            HTTP_X_FORWARDED_FOR="unknown, 198.51.100.20",
            HTTP_CF_CONNECTING_IP="not-an-ip",
        )

        self.assertEqual(get_client_ip(request), "198.51.100.20")


class PublicErrorMessageTests(TestCase):
    def test_public_error_message_hides_detail_outside_debug(self):
        with self.settings(DEBUG=False):
            self.assertEqual(
                build_public_service_error_message(Exception("OpenAI API timeout after 8s"), "fallback"),
                "現在アクセスが集中しています。しばらくしてから再度お試しください。",
            )

    def test_public_error_message_keeps_detail_in_debug(self):
        with self.settings(DEBUG=True):
            self.assertEqual(
                build_public_service_error_message(Exception("debug detail"), "fallback"),
                "debug detail",
            )


class OpenAIConciergeModerationPromptTests(TestCase):
    @patch("tabisync.openai_concierge.call_openai_responses_api")
    def test_moderation_prompt_includes_only_latest_history_for_short_confirmation(self, mock_call):
        mock_call.return_value = ('{"allowed": true, "reason": ""}', {"mock": True})
        history = [
            {
                "role": "user",
                "content": "古い履歴です。",
            },
            {
                "role": "assistant",
                "content": "チェックのため、既存の『持ち物リスト』に追加してよければ登録しますか？その場合は「追加して」とお伝えください。",
            }
        ]

        prompt, payload, result = run_moderation("追加して", history)

        self.assertTrue(result["allowed"])
        self.assertEqual(payload, {"mock": True})
        self.assertIn("直前までの会話履歴", prompt)
        self.assertIn("持ち物リスト", prompt)
        self.assertNotIn("古い履歴です。", prompt)
        self.assertIn("追加して", prompt)
        called_prompt = mock_call.call_args.args[0]
        self.assertEqual(called_prompt, prompt)


class ConciergeMessageLengthTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    @patch("tabisync.views.run_moderation")
    def test_post_rejects_user_message_over_60_chars_before_moderation(self, mock_moderation):
        request = self.factory.post(
            "/",
            data=json.dumps({"message": "あ" * 61}),
            content_type="application/json",
        )

        response = ConciergeV2View().post(request, pk=1, token="token")
        payload = json.loads(response.content.decode("utf-8"))

        self.assertEqual(response.status_code, 400)
        self.assertEqual(payload["status"], "error")
        self.assertEqual(payload["message"], "メッセージは60字以内で入力してください。")
        mock_moderation.assert_not_called()


class ConciergeHistoryNormalizationTests(TestCase):
    def test_normalize_history_keeps_latest_8_items_and_truncates_content(self):
        raw_history = [
            {
                "role": "user" if index % 2 else "assistant",
                "content": f"message-{index}-" + ("x" * 2000),
            }
            for index in range(10)
        ]

        normalized = ConciergeV2View()._normalize_history(raw_history)

        self.assertEqual(len(normalized), 8)
        self.assertTrue(normalized[0]["content"].startswith("message-2-"))
        self.assertTrue(normalized[-1]["content"].startswith("message-9-"))
        self.assertTrue(all(len(item["content"]) == 1500 for item in normalized))


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
