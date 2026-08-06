import json
from datetime import date

from django.test import TestCase

from ..models import Itinerary
from ..views.itinerary_helpers import (
    build_day_choices,
    build_default_checklist_v2_lists,
    can_add_want_to_go,
    get_schedule_day_index,
    get_want_to_go_limit,
    normalize_checklist_v2_content,
    normalize_memo_v2_notes,
)


class ScheduleDayIndexTests(TestCase):
    def setUp(self):
        self.itinerary = Itinerary.objects.create(
            title="Test Trip",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 3),
        )

    def test_returns_stored_day_index(self):
        # day_indexはTask 006のmigrationでNOT NULL化されており、常に保存済みの値をそのまま返す。
        schedule = self.itinerary.schedules.create(
            date=date(2026, 1, 1),
            day_index=2,
            title="予定",
            start_time="09:00",
        )
        self.assertEqual(get_schedule_day_index(self.itinerary, schedule), 2)


class BuildDayChoicesTests(TestCase):
    def test_builds_one_choice_per_day(self):
        itinerary = Itinerary.objects.create(
            title="Test Trip",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 3),
        )
        choices = build_day_choices(itinerary)
        self.assertEqual([c["day_num"] for c in choices], [1, 2, 3])
        self.assertEqual(choices[0]["calendar_date"], "2026-01-01")

    def test_returns_empty_without_total_days(self):
        itinerary = Itinerary.objects.create(title="No dates")
        self.assertEqual(build_day_choices(itinerary), [])


class WantToGoLimitTests(TestCase):
    def test_can_add_until_limit_reached(self):
        itinerary = Itinerary.objects.create(title="Test Trip", want_to_go_limit=1)
        self.assertTrue(can_add_want_to_go(itinerary))

        itinerary.want_to_go_list.create(name="Spot 1")
        self.assertFalse(can_add_want_to_go(itinerary))
        self.assertEqual(get_want_to_go_limit(itinerary), 1)


class NormalizeMemoV2NotesTests(TestCase):
    def test_parses_notes_list_and_drops_blank_content(self):
        raw = json.dumps({"notes": [{"content": "メモ1"}, {"content": "  "}]}, ensure_ascii=False)
        self.assertEqual(normalize_memo_v2_notes(raw), [{"content": "メモ1"}])

    def test_handles_empty_input(self):
        self.assertEqual(normalize_memo_v2_notes(""), [])


class NormalizeChecklistV2ContentTests(TestCase):
    def test_parses_lists_and_items(self):
        raw = json.dumps([
            {"id": "list-1", "title": "持ち物", "items": [{"id": "item-1", "text": "充電器", "checked": True}]},
        ], ensure_ascii=False)
        lists = normalize_checklist_v2_content(raw)
        self.assertEqual(len(lists), 1)
        self.assertEqual(lists[0]["title"], "持ち物")
        self.assertTrue(lists[0]["items"][0]["checked"])

    def test_drops_empty_lists_without_title_or_items(self):
        raw = json.dumps([{"id": "list-1", "title": "", "items": []}], ensure_ascii=False)
        self.assertEqual(normalize_checklist_v2_content(raw), [])


class BuildDefaultChecklistV2ListsTests(TestCase):
    def test_returns_single_default_list(self):
        lists = build_default_checklist_v2_lists()
        self.assertEqual(len(lists), 1)
        self.assertEqual(lists[0]["title"], "持ち物リスト")
        self.assertEqual(lists[0]["items"], [])
