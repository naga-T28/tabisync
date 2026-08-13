import json
from datetime import date
from unittest.mock import patch
from uuid import uuid4

from django.test import TestCase

from ..concierge_agent import agent as agent_module
from ..concierge_agent.context import RunContext
from ..concierge_agent.registry import build_registry
from ..concierge_agent.usage import RunUsageCounters
from ..models import Itinerary, WantToGo


def _message_output(text):
    return [{
        "type": "message",
        "role": "assistant",
        "content": [{"type": "output_text", "text": text}],
    }]


def _function_call_output(call_id, name, arguments):
    return [{
        "type": "function_call",
        "call_id": call_id,
        "name": name,
        "arguments": json.dumps(arguments, ensure_ascii=False),
    }]


def _skill_routing_parsed(skill_ids, reason=""):
    return {"output": _message_output(json.dumps({"skill_ids": skill_ids, "reason": reason}, ensure_ascii=False))}


def _final_text_parsed(text):
    return {"output": _message_output(text)}


def _tool_call_parsed(call_id, name, arguments):
    return {"output": _function_call_output(call_id, name, arguments)}


class AgentLoopTests(TestCase):
    """独自function-calling loop(concierge_agent.agent.run_agent)の検証。
    OpenAIとは実通信せず、post_responses_api_rawをモックする。
    """

    def setUp(self):
        self.itinerary = Itinerary.objects.create(
            title="Trip A", start_date=date(2026, 1, 1), end_date=date(2026, 1, 3),
        )
        self.run_context = RunContext(itinerary=self.itinerary, can_edit=True, conversation_id=uuid4())
        self.registry = build_registry()

    def _counters(self, max_tool_calls=6, max_openai_calls=6):
        return RunUsageCounters(max_openai_calls=max_openai_calls, max_tool_calls=max_tool_calls, max_run_seconds=30)

    @patch("tabisync.concierge_agent.agent.post_responses_api_raw")
    def test_reaches_final_answer_without_tool_calls(self, mock_post):
        mock_post.side_effect = [
            _skill_routing_parsed(["itinerary_guide"]),
            _final_text_parsed("こんにちは、旅程の確認ですね。"),
        ]
        result = agent_module.run_agent("旅程を教えて", [], self.run_context, self.registry, self._counters())

        self.assertEqual(result.reply_markdown, "こんにちは、旅程の確認ですね。")
        self.assertEqual(result.run_status, "ok")
        self.assertEqual(mock_post.call_count, 2)

    @patch("tabisync.concierge_agent.agent.post_responses_api_raw")
    def test_reaches_final_answer_after_one_tool_call(self, mock_post):
        mock_post.side_effect = [
            _skill_routing_parsed(["itinerary_guide"]),
            _tool_call_parsed("call_1", "get_itinerary", {}),
            _final_text_parsed("旅程はDay1〜3です。"),
        ]
        result = agent_module.run_agent("旅程を教えて", [], self.run_context, self.registry, self._counters())

        self.assertEqual(result.reply_markdown, "旅程はDay1〜3です。")
        self.assertEqual(mock_post.call_count, 3)
        self.assertEqual(len(result.trace.tool_call_records), 1)
        self.assertEqual(result.trace.tool_call_records[0]["tool_id"], "get_itinerary")
        self.assertEqual(result.trace.tool_call_records[0]["status"], "ok")

    @patch("tabisync.concierge_agent.agent.post_responses_api_raw")
    def test_unauthorized_tool_is_not_executed(self, mock_post):
        # itinerary_guideはpropose_changesを許可していないので、モデルが要求しても実行しない。
        mock_post.side_effect = [
            _skill_routing_parsed(["itinerary_guide"]),
            _tool_call_parsed("call_1", "propose_changes", {"actions": []}),
            _final_text_parsed("対応できません。"),
        ]
        with patch("tabisync.concierge_tools.proposal_tools.propose_changes") as mock_handler:
            result = agent_module.run_agent("何か編集して", [], self.run_context, self.registry, self._counters())

        mock_handler.assert_not_called()
        self.assertEqual(result.trace.tool_call_records[0]["status"], "not_allowed")

    @patch("tabisync.concierge_agent.agent.post_responses_api_raw")
    def test_tool_call_limit_stops_loop_safely(self, mock_post):
        # max_tool_calls=1のとき、モデルが2回目のTool呼び出しを要求しても実行されず、
        # 無限ループにならず強制的な最終回答(force_final_answer)へ切り替わる。
        mock_post.side_effect = [
            _skill_routing_parsed(["itinerary_guide"]),
            _tool_call_parsed("call_1", "get_itinerary", {}),
            _tool_call_parsed("call_2", "get_schedules", {}),
            _final_text_parsed("上限に達しました。"),
        ]
        result = agent_module.run_agent(
            "詳しく教えて", [], self.run_context, self.registry, self._counters(max_tool_calls=1),
        )

        self.assertEqual(result.run_status, "tool_calls_per_run_reached")
        self.assertEqual(result.reply_markdown, "上限に達しました。")
        executed = [record for record in result.trace.tool_call_records if record["status"] == "ok"]
        self.assertEqual(len(executed), 1)
        self.assertEqual(mock_post.call_count, 4)

    @patch("tabisync.concierge_agent.agent.post_responses_api_raw")
    def test_duplicate_tool_call_with_same_arguments_is_cached(self, mock_post):
        mock_post.side_effect = [
            _skill_routing_parsed(["itinerary_guide"]),
            {"output": _function_call_output("call_1", "get_itinerary", {}) + _function_call_output("call_2", "get_itinerary", {})},
            _final_text_parsed("完了しました。"),
        ]
        result = agent_module.run_agent("旅程を教えて", [], self.run_context, self.registry, self._counters())

        statuses = [record["status"] for record in result.trace.tool_call_records]
        self.assertEqual(statuses, ["ok", "cached"])

    @patch("tabisync.concierge_agent.agent.post_responses_api_raw")
    def test_show_map_ui_component_is_built_from_tool_result(self, mock_post):
        place = WantToGo.objects.create(itinerary=self.itinerary, name="首里城", latitude=26.2, longitude=127.7)
        mock_post.side_effect = [
            _skill_routing_parsed(["place_guide"]),
            _tool_call_parsed("call_1", "show_map", {"want_to_go_ids": [place.id], "title": "候補地"}),
            _final_text_parsed("地図を確認してください。"),
        ]
        result = agent_module.run_agent("首里城の場所を見せて", [], self.run_context, self.registry, self._counters())

        self.assertEqual(len(result.ui_components), 1)
        self.assertEqual(result.ui_components[0]["type"], "map")
        self.assertEqual(result.ui_components[0]["want_to_go_ids"], [place.id])
        self.assertEqual(result.ui_components[0]["places"][0]["id"], place.id)
        self.assertEqual(result.ui_components[0]["places"][0]["name"], "首里城")
        self.assertEqual(result.ui_components[0]["places"][0]["lat"], 26.2)
        self.assertEqual(result.ui_components[0]["places"][0]["lng"], 127.7)

    @patch("tabisync.concierge_agent.agent.post_responses_api_raw")
    def test_propose_changes_accepted_actions_become_edit_actions(self, mock_post):
        mock_post.side_effect = [
            _skill_routing_parsed(["note_assistant"]),
            _tool_call_parsed("call_1", "propose_changes", {
                "actions": [{"action": "memo_append", "content": "テストメモ"}],
            }),
            _final_text_parsed("追記候補を提案します。"),
        ]
        result = agent_module.run_agent("メモに追記して", [], self.run_context, self.registry, self._counters())

        self.assertEqual(len(result.edit_actions), 1)
        self.assertEqual(result.edit_actions[0]["action"], "memo_append")

    @patch("tabisync.concierge_agent.agent.post_responses_api_raw")
    def test_falls_back_to_itinerary_guide_when_no_skill_selected(self, mock_post):
        mock_post.side_effect = [
            _skill_routing_parsed([]),
            _final_text_parsed("旅程を確認しました。"),
        ]
        result = agent_module.run_agent("よくわからない相談", [], self.run_context, self.registry, self._counters())

        self.assertEqual(result.trace.selected_skill_ids, [])
        self.assertEqual(result.reply_markdown, "旅程を確認しました。")
