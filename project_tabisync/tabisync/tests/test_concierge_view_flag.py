import json
import os
from datetime import date
from unittest.mock import Mock, patch

from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from ..concierge_agent.agent import AgentRunResult
from ..concierge_agent.context import is_agent_mode_enabled
from ..models import ConciergeChatLog, Itinerary
from ..openai_concierge import OpenAIConciergeError


def _itinerary_stub(pk):
    # DB保存なしでpkのみ持つインスタンス(is_agent_mode_enabledはpk参照のみ行う)。
    return Itinerary(pk=pk, title="stub")


class AgentModeFlagTests(SimpleTestCase):
    def test_disabled_when_env_vars_unset(self):
        itinerary = _itinerary_stub(1)
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("CONCIERGE_AGENT_ENABLED", None)
            os.environ.pop("CONCIERGE_AGENT_ENABLED_ITINERARY_IDS", None)
            self.assertFalse(is_agent_mode_enabled(itinerary))

    def test_global_flag_enables_all_itineraries(self):
        itinerary = _itinerary_stub(1)
        with patch.dict(os.environ, {"CONCIERGE_AGENT_ENABLED": "true"}, clear=False):
            os.environ.pop("CONCIERGE_AGENT_ENABLED_ITINERARY_IDS", None)
            self.assertTrue(is_agent_mode_enabled(itinerary))

    def test_allowlist_enables_listed_itinerary_even_if_global_flag_false(self):
        itinerary = _itinerary_stub(5)
        with patch.dict(os.environ, {
            "CONCIERGE_AGENT_ENABLED": "false",
            "CONCIERGE_AGENT_ENABLED_ITINERARY_IDS": "5,9",
        }, clear=False):
            self.assertTrue(is_agent_mode_enabled(itinerary))

    def test_allowlist_excludes_unlisted_itinerary_even_if_global_flag_true(self):
        itinerary = _itinerary_stub(3)
        with patch.dict(os.environ, {
            "CONCIERGE_AGENT_ENABLED": "true",
            "CONCIERGE_AGENT_ENABLED_ITINERARY_IDS": "5,9",
        }, clear=False):
            self.assertFalse(is_agent_mode_enabled(itinerary))


def _mock_trace(selected_skill_ids=None, openai_call_count=1, tool_call_records=None, web_search_call_count=0):
    trace = Mock()
    trace.selected_skill_ids = selected_skill_ids or []
    trace.openai_call_count = openai_call_count
    trace.tool_call_records = tool_call_records or []
    trace.web_search_call_count = web_search_call_count
    trace.persist_tool_calls = Mock()
    return trace


class ConciergeAgentModeViewIntegrationTests(TestCase):
    """CONCIERGE_AGENT_ENABLED=true のとき、ConciergeV2View.postがrun_agent経由で
    正しく応答を組み立て、ConciergeChatLogをengine="agent"として記録することを確認する。
    OpenAIとは実通信せず、run_agent自体をモックする。
    """

    def setUp(self):
        self.itinerary = Itinerary.objects.create(
            title="Trip", start_date=date(2026, 1, 1), end_date=date(2026, 1, 3),
        )
        self.url = reverse(
            "tabisync:V2_concierge", kwargs={"pk": self.itinerary.pk, "token": self.itinerary.token},
        )

    def _post(self, message="旅程を教えて"):
        return self.client.post(self.url, data=json.dumps({"message": message}), content_type="application/json")

    @patch("tabisync.views.concierge.run_agent")
    @patch("tabisync.views.concierge.run_moderation")
    def test_agent_mode_returns_reply_and_persists_agent_engine_log(self, mock_moderation, mock_run_agent):
        mock_moderation.return_value = ("p", {}, {"allowed": True, "reason": ""})
        mock_run_agent.return_value = AgentRunResult(
            reply_markdown="こんにちは、旅程はDay1〜3です。",
            ui_components=[{"type": "map", "title": "候補地", "want_to_go_ids": [1]}],
            edit_actions=[],
            run_status="ok",
            trace=_mock_trace(selected_skill_ids=["itinerary_guide"], openai_call_count=2),
        )

        with patch.dict(os.environ, {"CONCIERGE_AGENT_ENABLED": "true"}, clear=False):
            response = self._post()

        data = json.loads(response.content.decode("utf-8"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data["status"], "ok")
        self.assertEqual(data["reply"], "こんにちは、旅程はDay1〜3です。")
        self.assertEqual(data["ui_components"][0]["type"], "map")

        log = ConciergeChatLog.objects.get(itinerary=self.itinerary)
        self.assertEqual(log.engine, "agent")
        self.assertEqual(log.selected_skill_ids, ["itinerary_guide"])
        self.assertEqual(log.run_status, "ok")

    @patch("tabisync.views.concierge.run_agent")
    @patch("tabisync.views.concierge.run_moderation")
    def test_agent_mode_moderation_block_does_not_call_run_agent(self, mock_moderation, mock_run_agent):
        mock_moderation.return_value = ("p", {}, {"allowed": False, "reason": "対応できません"})

        with patch.dict(os.environ, {"CONCIERGE_AGENT_ENABLED": "true"}, clear=False):
            response = self._post()

        data = json.loads(response.content.decode("utf-8"))
        self.assertEqual(data["status"], "blocked")
        mock_run_agent.assert_not_called()
        self.assertEqual(ConciergeChatLog.objects.filter(itinerary=self.itinerary).count(), 1)

    @patch("tabisync.views.concierge.run_agent")
    @patch("tabisync.views.concierge.run_moderation")
    def test_agent_mode_run_failure_releases_reservation(self, mock_moderation, mock_run_agent):
        mock_moderation.return_value = ("p", {}, {"allowed": True, "reason": ""})
        mock_run_agent.side_effect = OpenAIConciergeError("boom")

        with patch.dict(os.environ, {"CONCIERGE_AGENT_ENABLED": "true"}, clear=False):
            response = self._post()

        self.assertEqual(response.status_code, 502)
        self.assertEqual(ConciergeChatLog.objects.filter(itinerary=self.itinerary).count(), 0)

    @patch("tabisync.views.concierge.run_agent")
    @patch("tabisync.views.concierge.run_moderation")
    def test_legacy_mode_used_when_flag_disabled(self, mock_moderation, mock_run_agent):
        mock_moderation.return_value = ("p", {}, {"allowed": True, "reason": ""})

        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("CONCIERGE_AGENT_ENABLED", None)
            os.environ.pop("CONCIERGE_AGENT_ENABLED_ITINERARY_IDS", None)
            with patch("tabisync.views.concierge.run_data_selection") as mock_selection, \
                    patch("tabisync.views.concierge.run_answer") as mock_answer:
                mock_selection.return_value = ("p", {}, {"required_data": [], "reason": ""})
                mock_answer.return_value = ("p", {}, "legacyの回答", [])
                response = self._post()

        data = json.loads(response.content.decode("utf-8"))
        self.assertEqual(data["reply"], "legacyの回答")
        mock_run_agent.assert_not_called()
        log = ConciergeChatLog.objects.get(itinerary=self.itinerary)
        self.assertEqual(log.engine, "legacy")
