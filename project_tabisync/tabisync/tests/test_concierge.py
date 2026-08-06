import json
import threading
from datetime import date
from unittest.mock import patch

from django.test import Client, RequestFactory, TestCase, TransactionTestCase
from django.urls import reverse

from ..models import ConciergeChatLog, Itinerary, WantToGo
from ..openai_concierge import OpenAIConciergeError
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


class ConciergeQuotaReservationTests(TestCase):
    """AI利用枠は外部API呼び出し前に予約し、失敗時は解放（消費しない）される。"""

    def setUp(self):
        self.itinerary = Itinerary.objects.create(
            title="Test Trip",
            concierge_daily_limit=3,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 3),
        )
        self.url = reverse(
            "tabisync:V2_concierge",
            kwargs={"pk": self.itinerary.pk, "token": self.itinerary.token},
        )

    def _post(self, message="旅程を教えて"):
        return self.client.post(
            self.url,
            data=json.dumps({"message": message}),
            content_type="application/json",
        )

    @patch("tabisync.views.concierge.run_answer")
    @patch("tabisync.views.concierge.run_data_selection")
    @patch("tabisync.views.concierge.run_moderation")
    def test_successful_call_consumes_exactly_one_reservation(self, mock_mod, mock_sel, mock_ans):
        mock_mod.return_value = ("p", {}, {"allowed": True, "reason": ""})
        mock_sel.return_value = ("p", {}, {"required_data": [], "reason": ""})
        mock_ans.return_value = ("p", {}, "こんにちは", [])

        response = self._post()
        data = json.loads(response.content.decode("utf-8"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(data["status"], "ok")
        self.assertEqual(ConciergeChatLog.objects.filter(itinerary=self.itinerary).count(), 1)
        log = ConciergeChatLog.objects.get(itinerary=self.itinerary)
        self.assertEqual(log.assistant_message, "こんにちは")

    @patch("tabisync.views.concierge.run_moderation")
    def test_moderation_failure_refunds_reservation(self, mock_mod):
        mock_mod.side_effect = OpenAIConciergeError("timeout")

        response = self._post()

        self.assertEqual(response.status_code, 502)
        self.assertEqual(ConciergeChatLog.objects.filter(itinerary=self.itinerary).count(), 0)

    @patch("tabisync.views.concierge.run_data_selection")
    @patch("tabisync.views.concierge.run_moderation")
    def test_data_selection_failure_refunds_reservation(self, mock_mod, mock_sel):
        mock_mod.return_value = ("p", {}, {"allowed": True, "reason": ""})
        mock_sel.side_effect = OpenAIConciergeError("boom")

        response = self._post()

        self.assertEqual(response.status_code, 502)
        self.assertEqual(ConciergeChatLog.objects.filter(itinerary=self.itinerary).count(), 0)

    @patch("tabisync.views.concierge.run_answer")
    @patch("tabisync.views.concierge.run_data_selection")
    @patch("tabisync.views.concierge.run_moderation")
    def test_answer_generation_failure_refunds_reservation(self, mock_mod, mock_sel, mock_ans):
        mock_mod.return_value = ("p", {}, {"allowed": True, "reason": ""})
        mock_sel.return_value = ("p", {}, {"required_data": [], "reason": ""})
        mock_ans.side_effect = OpenAIConciergeError("boom")

        response = self._post()

        self.assertEqual(response.status_code, 502)
        self.assertEqual(ConciergeChatLog.objects.filter(itinerary=self.itinerary).count(), 0)

    @patch("tabisync.views.concierge.run_moderation")
    def test_blocked_moderation_consumes_reservation(self, mock_mod):
        mock_mod.return_value = ("p", {}, {"allowed": False, "reason": "対応できません"})

        response = self._post()
        data = json.loads(response.content.decode("utf-8"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(data["status"], "blocked")
        self.assertEqual(ConciergeChatLog.objects.filter(itinerary=self.itinerary).count(), 1)

    @patch("tabisync.views.concierge.run_answer")
    @patch("tabisync.views.concierge.run_data_selection")
    @patch("tabisync.views.concierge.run_moderation")
    def test_daily_limit_enforced_and_stops_before_calling_openai(self, mock_mod, mock_sel, mock_ans):
        mock_mod.return_value = ("p", {}, {"allowed": True, "reason": ""})
        mock_sel.return_value = ("p", {}, {"required_data": [], "reason": ""})
        mock_ans.return_value = ("p", {}, "OK", [])

        for _ in range(self.itinerary.concierge_daily_limit):
            response = self._post()
            self.assertEqual(response.status_code, 200)

        mock_mod.reset_mock()
        response = self._post()
        data = json.loads(response.content.decode("utf-8"))

        self.assertEqual(response.status_code, 429)
        self.assertEqual(data["status"], "limit_exceeded")
        mock_mod.assert_not_called()
        self.assertEqual(
            ConciergeChatLog.objects.filter(itinerary=self.itinerary).count(),
            self.itinerary.concierge_daily_limit,
        )


class ConciergeDailyLimitConcurrencyTests(TransactionTestCase):
    """複数リクエストが同時にAI利用枠を消費しようとしても、日次上限を超えないことを検証する。

    テストDB(SQLite)は行ロック(select_for_update)を実質サポートしないため、
    このテストが保証するのは「最終的なChatLog件数が日次上限を超えない」という
    不変条件のみであり、本番のPostgreSQLで行われる真の直列化そのものを
    再現するものではない。
    """

    def test_concurrent_requests_do_not_exceed_daily_limit(self):
        itinerary = Itinerary.objects.create(
            title="Race Trip",
            concierge_daily_limit=2,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 3),
        )
        url = reverse("tabisync:V2_concierge", kwargs={"pk": itinerary.pk, "token": itinerary.token})

        moderation_patcher = patch(
            "tabisync.views.concierge.run_moderation",
            return_value=("p", {}, {"allowed": True, "reason": ""}),
        )
        selection_patcher = patch(
            "tabisync.views.concierge.run_data_selection",
            return_value=("p", {}, {"required_data": [], "reason": ""}),
        )
        answer_patcher = patch(
            "tabisync.views.concierge.run_answer",
            return_value=("p", {}, "OK", []),
        )
        moderation_patcher.start()
        selection_patcher.start()
        answer_patcher.start()
        self.addCleanup(moderation_patcher.stop)
        self.addCleanup(selection_patcher.stop)
        self.addCleanup(answer_patcher.stop)

        thread_count = 6
        barrier = threading.Barrier(thread_count)
        outcomes = []
        lock = threading.Lock()

        def worker(index):
            barrier.wait()
            client = Client()
            payload = {"message": f"問い合わせ{index}"}
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

        final_count = ConciergeChatLog.objects.filter(itinerary=itinerary).count()
        self.assertLessEqual(final_count, itinerary.concierge_daily_limit, f"outcomes={outcomes}")


class ConciergeApplyChangesWantToGoValidationTests(TestCase):
    """Task 007: AI(コンシェルジュ)経由の行きたい場所作成/更新も、
    JS経由と同じ検証(緯度経度・day・priority)を通ることを確認する。"""

    def setUp(self):
        self.itinerary = Itinerary.objects.create(
            title="Test Trip",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 3),
        )
        self.url = reverse(
            "tabisync:V2_concierge_apply",
            kwargs={"pk": self.itinerary.pk, "token": self.itinerary.token},
        )

    def _apply(self, action):
        return self.client.post(
            self.url,
            data=json.dumps({"edit_actions": [action]}),
            content_type="application/json",
        )

    def test_want_create_with_valid_fields_succeeds(self):
        response = self._apply({
            "action": "want_create",
            "place_name": "首里城",
            "day": 1,
            "priority": 4,
        })
        data = json.loads(response.content.decode("utf-8"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(data["status"], "ok")
        place = WantToGo.objects.get(itinerary=self.itinerary)
        self.assertEqual(place.planned_day, 1)
        self.assertEqual(place.priority, 4)

    def test_want_create_with_out_of_range_day_is_rejected(self):
        response = self._apply({
            "action": "want_create",
            "place_name": "範囲外スポット",
            "day": 99,
        })
        data = json.loads(response.content.decode("utf-8"))

        self.assertEqual(response.status_code, 400)
        self.assertEqual(data["status"], "error")
        self.assertFalse(WantToGo.objects.filter(itinerary=self.itinerary).exists())

    def test_want_create_with_invalid_priority_is_rejected(self):
        response = self._apply({
            "action": "want_create",
            "place_name": "優先度異常",
            "priority": 99,
        })
        self.assertEqual(response.status_code, 400)
        self.assertFalse(WantToGo.objects.filter(itinerary=self.itinerary).exists())

    def test_want_update_with_invalid_day_is_rejected_without_partial_apply(self):
        place = self.itinerary.want_to_go_list.create(name="既存スポット", planned_day=1, priority=3)
        response = self._apply({
            "action": "want_update",
            "id": place.id,
            "day": 99,
            "priority": 5,
        })
        data = json.loads(response.content.decode("utf-8"))

        self.assertEqual(response.status_code, 400)
        self.assertEqual(data["status"], "error")
        place.refresh_from_db()
        self.assertEqual(place.planned_day, 1)
        self.assertEqual(place.priority, 3)
