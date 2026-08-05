import json
from unittest.mock import patch

from django.test import RequestFactory, TestCase

from ..views.concierge import ConciergeV2View


class OpenAIConciergeModerationPromptTests(TestCase):
    @patch("tabisync.openai_concierge.call_openai_responses_api")
    def test_moderation_prompt_includes_only_latest_history_for_short_confirmation(self, mock_call):
        from ..openai_concierge import run_moderation

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

    @patch("tabisync.views.concierge.run_moderation")
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


class ConciergePingTests(TestCase):
    def test_ping_message_short_circuits_without_calling_openai(self):
        from datetime import date

        from ..models import Itinerary

        itinerary = Itinerary.objects.create(
            title="Test Trip",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 3),
        )

        view = ConciergeV2View()
        view.itinerary = itinerary
        request = RequestFactory().post(
            "/",
            data=json.dumps({"message": "__ping__"}),
            content_type="application/json",
        )

        response = view.post(request, pk=itinerary.pk, token=str(itinerary.token))
        payload = json.loads(response.content.decode("utf-8"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["reply"], "concierge ping ok")
