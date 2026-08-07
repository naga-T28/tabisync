import os
import time

from django.db import transaction
from django.utils import timezone

from ..models import ConciergeChatLog
from ..views.itinerary_helpers import lock_itinerary_for_update
from .errors import UsageLimitExceeded

# run内(1リクエスト内)の既定上限。Skill Markdownの`max_tool_calls`と比較し、
# 小さい方が実際の上限として採用される(registry.resolve_tools_for_skillsで適用)。
CONCIERGE_AGENT_MAX_OPENAI_CALLS_PER_RUN = int(os.environ.get("CONCIERGE_AGENT_MAX_OPENAI_CALLS_PER_RUN", "6"))
CONCIERGE_AGENT_MAX_TOOL_CALLS_PER_RUN = int(os.environ.get("CONCIERGE_AGENT_MAX_TOOL_CALLS_PER_RUN", "6"))
CONCIERGE_AGENT_MAX_RUN_SECONDS = float(os.environ.get("CONCIERGE_AGENT_MAX_RUN_SECONDS", "25"))


class RunUsageCounters:
    """Agent run 1回分(=1 HTTPリクエスト内)の利用回数・経過時間を管理する。

    Gunicornワーカーは1リクエストを最初から最後まで単一スレッドで逐次処理するため、
    複数リクエストにまたがる並行アクセスはこのオブジェクト単位では発生せず、
    DBロックは不要(日次上限側の並行性はDailyRunUsageServiceが別途担保する)。
    将来async化・バックグラウンド実行化する場合は永続ストアへの置き換えが必要。
    """

    def __init__(self, max_openai_calls, max_tool_calls, max_run_seconds):
        self.max_openai_calls = max_openai_calls
        self.max_tool_calls = max_tool_calls
        self.max_run_seconds = max_run_seconds
        self.openai_call_count = 0
        self.tool_call_count = 0
        self._started_at = time.monotonic()

    @classmethod
    def from_env(cls):
        return cls(
            max_openai_calls=CONCIERGE_AGENT_MAX_OPENAI_CALLS_PER_RUN,
            max_tool_calls=CONCIERGE_AGENT_MAX_TOOL_CALLS_PER_RUN,
            max_run_seconds=CONCIERGE_AGENT_MAX_RUN_SECONDS,
        )

    def check_deadline(self):
        if time.monotonic() - self._started_at > self.max_run_seconds:
            raise UsageLimitExceeded("run_time", "AIコンシェルジュの処理時間上限に達しました。")

    def check_openai_call(self):
        if self.openai_call_count >= self.max_openai_calls:
            raise UsageLimitExceeded("openai_calls_per_run", "AIモデル呼び出し回数の上限に達しました。")
        self.openai_call_count += 1

    def check_tool_call(self, tool_id):
        if self.tool_call_count >= self.max_tool_calls:
            raise UsageLimitExceeded("tool_calls_per_run", "Tool呼び出し回数の上限に達しました。")
        self.tool_call_count += 1


class DailyRunUsageService:
    """既存ConciergeV2View.post()冒頭にあった日次利用枠の予約/確定/解放ロジックを移設したもの。

    legacy path・agent pathの両方がこれ経由で予約・確定・解放を行うことで、
    日次上限ロジックが2箇所へ分岐して片方だけ修正され不整合を起こすリスクを無くす。
    予約はDBロック内で完結させ、外部API呼び出し中はロックを保持しない(既存方針を維持)。
    """

    @staticmethod
    def reserve(itinerary, conversation_id, turn_index, user_message):
        """当日の利用回数を確認し、上限内であればConciergeChatLogを予約行として作成する。

        戻り値は (reservation_or_none, today_count, daily_limit)。
        上限到達時は reservation が None になる(呼び出し側は429を返すこと)。
        """
        daily_limit = itinerary.get_concierge_daily_limit()
        with transaction.atomic():
            locked_itinerary = lock_itinerary_for_update(itinerary)
            today_count = ConciergeChatLog.objects.filter(
                itinerary=locked_itinerary,
                created_at__date=timezone.localdate(),
            ).count()

            if today_count >= daily_limit:
                return None, today_count, daily_limit

            reservation = ConciergeChatLog.objects.create(
                itinerary=locked_itinerary,
                conversation_id=conversation_id,
                turn_index=turn_index,
                user_message=user_message,
            )
            return reservation, today_count, daily_limit

    @staticmethod
    def finalize(reservation, **fields):
        for key, value in fields.items():
            setattr(reservation, key, value)
        reservation.save()

    @staticmethod
    def release(reservation):
        reservation.delete()
