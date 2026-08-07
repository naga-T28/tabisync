import time
from datetime import date
from uuid import uuid4

from django.test import TestCase

from ..concierge_agent.errors import UsageLimitExceeded
from ..concierge_agent.usage import DailyRunUsageService, RunUsageCounters
from ..models import ConciergeChatLog, Itinerary


class RunUsageCountersTests(TestCase):
    def test_openai_call_limit_enforced(self):
        counters = RunUsageCounters(max_openai_calls=2, max_tool_calls=5, max_run_seconds=10)
        counters.check_openai_call()
        counters.check_openai_call()
        with self.assertRaises(UsageLimitExceeded) as ctx:
            counters.check_openai_call()
        self.assertEqual(ctx.exception.limit_type, "openai_calls_per_run")

    def test_tool_call_limit_enforced(self):
        counters = RunUsageCounters(max_openai_calls=5, max_tool_calls=1, max_run_seconds=10)
        counters.check_tool_call("get_itinerary")
        with self.assertRaises(UsageLimitExceeded) as ctx:
            counters.check_tool_call("get_itinerary")
        self.assertEqual(ctx.exception.limit_type, "tool_calls_per_run")

    def test_deadline_enforced(self):
        counters = RunUsageCounters(max_openai_calls=5, max_tool_calls=5, max_run_seconds=0.01)
        time.sleep(0.05)
        with self.assertRaises(UsageLimitExceeded) as ctx:
            counters.check_deadline()
        self.assertEqual(ctx.exception.limit_type, "run_time")

    def test_counters_independent_per_instance(self):
        counters_a = RunUsageCounters(max_openai_calls=1, max_tool_calls=1, max_run_seconds=10)
        counters_b = RunUsageCounters(max_openai_calls=1, max_tool_calls=1, max_run_seconds=10)
        counters_a.check_openai_call()
        # 別インスタンスのcounterには影響しない(runをまたいだ状態共有がないことの確認)。
        counters_b.check_openai_call()


class DailyRunUsageServiceTests(TestCase):
    """既存ConciergeV2View.post()の予約ロジックをDailyRunUsageServiceへ抽出したもの。
    legacy/agent両経路がこれを共有するため、ここでの検証は両経路の日次上限判定を保証する。
    """

    def setUp(self):
        self.itinerary = Itinerary.objects.create(
            title="Trip", concierge_daily_limit=2, start_date=date(2026, 1, 1), end_date=date(2026, 1, 3),
        )

    def test_reserve_succeeds_within_limit(self):
        reservation, today_count, daily_limit = DailyRunUsageService.reserve(self.itinerary, uuid4(), 1, "hi")
        self.assertIsNotNone(reservation)
        self.assertEqual(today_count, 0)
        self.assertEqual(daily_limit, 2)

    def test_reserve_returns_none_when_limit_reached(self):
        for _ in range(2):
            reservation, _, _ = DailyRunUsageService.reserve(self.itinerary, uuid4(), 1, "hi")
            self.assertIsNotNone(reservation)

        reservation, today_count, daily_limit = DailyRunUsageService.reserve(self.itinerary, uuid4(), 1, "hi")
        self.assertIsNone(reservation)
        self.assertEqual(today_count, 2)
        self.assertEqual(daily_limit, 2)
        # 上限到達時は新しい行が作られない。
        self.assertEqual(ConciergeChatLog.objects.filter(itinerary=self.itinerary).count(), 2)

    def test_release_deletes_reservation(self):
        reservation, _, _ = DailyRunUsageService.reserve(self.itinerary, uuid4(), 1, "hi")
        DailyRunUsageService.release(reservation)
        self.assertFalse(ConciergeChatLog.objects.filter(pk=reservation.pk).exists())

    def test_finalize_updates_agent_fields(self):
        reservation, _, _ = DailyRunUsageService.reserve(self.itinerary, uuid4(), 1, "hi")
        DailyRunUsageService.finalize(
            reservation,
            engine="agent",
            run_status="ok",
            assistant_message="done",
            selected_skill_ids=["itinerary_guide"],
            openai_call_count=2,
            tool_call_count=3,
        )
        reservation.refresh_from_db()
        self.assertEqual(reservation.engine, "agent")
        self.assertEqual(reservation.run_status, "ok")
        self.assertEqual(reservation.assistant_message, "done")
        self.assertEqual(reservation.selected_skill_ids, ["itinerary_guide"])
        self.assertEqual(reservation.openai_call_count, 2)
        self.assertEqual(reservation.tool_call_count, 3)
