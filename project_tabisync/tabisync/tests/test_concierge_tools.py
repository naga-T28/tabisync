import json
from datetime import date
from uuid import uuid4

from django.test import TestCase

from ..concierge_agent.context import RunContext
from ..concierge_agent.errors import ToolExecutionError
from ..concierge_tools import proposal_tools, read_tools, ui_tools
from ..models import Itinerary, ScheduleV2, WantToGo


def build_run_context(itinerary, can_edit=True):
    return RunContext(itinerary=itinerary, can_edit=can_edit, conversation_id=uuid4())


class ReadToolsScopeTests(TestCase):
    def setUp(self):
        self.itinerary = Itinerary.objects.create(
            title="Trip A", start_date=date(2026, 1, 1), end_date=date(2026, 1, 3),
        )
        self.other_itinerary = Itinerary.objects.create(
            title="Trip B", start_date=date(2026, 2, 1), end_date=date(2026, 2, 3),
        )
        self.run_context = build_run_context(self.itinerary)

    def test_get_itinerary_returns_basic_fields(self):
        result = read_tools.get_itinerary(self.run_context)
        self.assertEqual(result["title"], "Trip A")
        self.assertEqual(result["total_days"], 3)
        self.assertEqual(result["start_date"], "2026-01-01")

    def test_get_schedules_only_returns_target_itinerary_schedules(self):
        ScheduleV2.objects.create(
            itinerary=self.itinerary, date=date(2026, 1, 1), day_index=1,
            title="A", start_time="09:00",
        )
        ScheduleV2.objects.create(
            itinerary=self.other_itinerary, date=date(2026, 2, 1), day_index=1,
            title="B", start_time="09:00",
        )
        result = read_tools.get_schedules(self.run_context)
        titles = [schedule["title"] for schedule in result["schedules"]]
        self.assertEqual(titles, ["A"])

    def test_get_schedules_filters_by_day(self):
        ScheduleV2.objects.create(
            itinerary=self.itinerary, date=date(2026, 1, 1), day_index=1,
            title="Day1", start_time="09:00",
        )
        ScheduleV2.objects.create(
            itinerary=self.itinerary, date=date(2026, 1, 2), day_index=2,
            title="Day2", start_time="09:00",
        )
        result = read_tools.get_schedules(self.run_context, days=[2])
        titles = [schedule["title"] for schedule in result["schedules"]]
        self.assertEqual(titles, ["Day2"])

    def test_get_schedules_invalid_day_raises(self):
        with self.assertRaises(ToolExecutionError) as ctx:
            read_tools.get_schedules(self.run_context, days=[99])
        self.assertEqual(ctx.exception.tool_id, "get_schedules")
        self.assertEqual(ctx.exception.error_code, "invalid_day")

    def test_get_want_to_go_excludes_other_itinerary(self):
        WantToGo.objects.create(itinerary=self.itinerary, name="Place A")
        WantToGo.objects.create(itinerary=self.other_itinerary, name="Place B")
        result = read_tools.get_want_to_go(self.run_context)
        names = [place["name"] for place in result["places"]]
        self.assertEqual(names, ["Place A"])

    def test_get_want_to_go_does_not_expose_coordinates_or_place_id(self):
        WantToGo.objects.create(
            itinerary=self.itinerary, name="Place A",
            latitude=35.0, longitude=139.0, place_id="abc123",
        )
        result = read_tools.get_want_to_go(self.run_context)
        place = result["places"][0]
        self.assertNotIn("lat", place)
        self.assertNotIn("lng", place)
        self.assertNotIn("place_id", place)

    def test_get_memo_returns_empty_when_no_memo(self):
        result = read_tools.get_memo(self.run_context)
        self.assertEqual(result["notes"], [])

    def test_get_checklist_returns_empty_when_no_checklist(self):
        result = read_tools.get_checklist(self.run_context)
        self.assertEqual(result["lists"], [])

    def test_tool_outputs_do_not_leak_secrets(self):
        results = [
            read_tools.get_itinerary(self.run_context),
            read_tools.get_schedules(self.run_context),
            read_tools.get_want_to_go(self.run_context),
            read_tools.get_memo(self.run_context),
            read_tools.get_checklist(self.run_context),
        ]
        serialized = json.dumps(results, default=str).lower()
        for forbidden in ("password", "token", "session", "api_key", "secret"):
            self.assertNotIn(forbidden, serialized)


class ShowMapToolTests(TestCase):
    def setUp(self):
        self.itinerary = Itinerary.objects.create(
            title="Trip A", start_date=date(2026, 1, 1), end_date=date(2026, 1, 3),
        )
        self.other_itinerary = Itinerary.objects.create(
            title="Trip B", start_date=date(2026, 2, 1), end_date=date(2026, 2, 3),
        )
        self.run_context = build_run_context(self.itinerary)

    def test_show_map_excludes_other_itinerary_places(self):
        place_a = WantToGo.objects.create(itinerary=self.itinerary, name="A", latitude=35.0, longitude=139.0)
        place_b = WantToGo.objects.create(itinerary=self.other_itinerary, name="B", latitude=36.0, longitude=140.0)

        tool_result, ui_component = ui_tools.show_map(self.run_context, [place_a.id, place_b.id], "Test map")

        returned_ids = [place["id"] for place in tool_result["places"]]
        self.assertEqual(returned_ids, [place_a.id])
        self.assertEqual(ui_component["want_to_go_ids"], [place_a.id])
        self.assertEqual(ui_component["type"], "map")
        self.assertEqual([place["id"] for place in ui_component["places"]], [place_a.id])

    def test_show_map_ui_component_places_match_serialized_tool_result(self):
        place = WantToGo.objects.create(
            itinerary=self.itinerary, name="首里城", address="那覇市", latitude=26.2, longitude=127.7,
        )

        tool_result, ui_component = ui_tools.show_map(self.run_context, [place.id], "候補地")

        self.assertEqual(ui_component["places"], tool_result["places"])
        self.assertEqual(
            set(ui_component["places"][0].keys()),
            {"id", "name", "address", "lat", "lng", "place_id", "maps_url"},
        )

    def test_show_map_no_places_found_raises(self):
        with self.assertRaises(ToolExecutionError) as ctx:
            ui_tools.show_map(self.run_context, [999999], "Test map")
        self.assertEqual(ctx.exception.error_code, "no_places_found")

    def test_show_map_builds_server_side_maps_url(self):
        place = WantToGo.objects.create(itinerary=self.itinerary, name="A", place_id="abc123")
        tool_result, _ = ui_tools.show_map(self.run_context, [place.id], "Test")
        maps_url = tool_result["places"][0]["maps_url"]
        self.assertTrue(maps_url.startswith("https://www.google.com/maps/"))
        self.assertIn("abc123", maps_url)


class ProposeChangesToolTests(TestCase):
    """Task 001: propose_changesはDBを一切変更せず、既存apply経路と同じ検証結果を返す。"""

    def setUp(self):
        self.itinerary = Itinerary.objects.create(
            title="Trip A", start_date=date(2026, 1, 1), end_date=date(2026, 1, 3),
        )
        self.run_context = build_run_context(self.itinerary)

    def test_propose_changes_does_not_modify_db(self):
        before_count = WantToGo.objects.count()
        result = proposal_tools.propose_changes(self.run_context, [
            {"action": "want_create", "place_name": "首里城", "day": 1, "priority": 4},
        ])
        self.assertEqual(len(result["accepted"]), 1)
        self.assertEqual(WantToGo.objects.count(), before_count)

    def test_propose_changes_rejects_invalid_day_without_side_effect(self):
        before_count = WantToGo.objects.count()
        result = proposal_tools.propose_changes(self.run_context, [
            {"action": "want_create", "place_name": "範囲外スポット", "day": 99},
        ])
        self.assertEqual(len(result["accepted"]), 0)
        self.assertEqual(len(result["rejected"]), 1)
        self.assertEqual(WantToGo.objects.count(), before_count)

    def test_propose_changes_partial_acceptance_still_leaves_db_untouched(self):
        before_schedule_count = ScheduleV2.objects.count()
        before_want_count = WantToGo.objects.count()
        result = proposal_tools.propose_changes(self.run_context, [
            {"action": "want_create", "place_name": "有効なスポット", "day": 1},
            {"action": "schedule_create", "day": 99, "title": "無効な予定", "start_time": "09:00"},
        ])
        self.assertEqual(len(result["accepted"]), 1)
        self.assertEqual(len(result["rejected"]), 1)
        self.assertEqual(ScheduleV2.objects.count(), before_schedule_count)
        self.assertEqual(WantToGo.objects.count(), before_want_count)

    def test_propose_changes_empty_actions_returns_empty_result(self):
        result = proposal_tools.propose_changes(self.run_context, [])
        self.assertEqual(result, {"accepted": [], "rejected": []})
