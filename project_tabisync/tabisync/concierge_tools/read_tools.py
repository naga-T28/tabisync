from django.utils.html import strip_tags

from ..concierge_agent.errors import ToolExecutionError
from ..views.itinerary_helpers import (
    get_schedule_day_index,
    normalize_checklist_v2_content,
    normalize_memo_v2_notes,
)

"""既存 views.concierge.ConciergeV2View._build_selected_context を、
Agent loopから個別に呼び出せる5つの読み取りToolへ分解したもの。

全関数は RunContext のみを受け取り、run_context.itinerary 経由でのみDBへアクセスする。
pk/token/passwordはToolの引数として一切受け取らない(モデルがそもそも指定できない設計)。
"""


def get_itinerary(run_context):
    itinerary = run_context.itinerary
    return {
        "title": itinerary.title,
        "subtitle": itinerary.subtitle or "",
        "description": itinerary.description or "",
        "start_date": itinerary.start_date.strftime("%Y-%m-%d") if itinerary.start_date else "",
        "end_date": itinerary.end_date.strftime("%Y-%m-%d") if itinerary.end_date else "",
        "total_days": itinerary.total_days or 0,
    }


def _validate_days(itinerary, days):
    max_day = itinerary.total_days or 0
    for day in days:
        if not isinstance(day, int) or isinstance(day, bool) or day < 1 or day > max_day:
            raise ToolExecutionError("get_schedules", "invalid_day", f"存在しないDayが指定されました: {day!r}")


def get_schedules(run_context, days=None):
    itinerary = run_context.itinerary
    queryset = itinerary.schedules.select_related("place").all().order_by("day_index", "start_time", "order", "id")

    if days:
        _validate_days(itinerary, days)
        queryset = queryset.filter(day_index__in=days)

    return {
        "schedules": [{
            "id": schedule.id,
            "day_index": get_schedule_day_index(itinerary, schedule) or schedule.day_index or 0,
            "date": schedule.date.strftime("%Y-%m-%d") if schedule.date else "",
            "title": schedule.title,
            "start_time": schedule.start_time.strftime("%H:%M") if schedule.start_time else "",
            "end_time": schedule.end_time.strftime("%H:%M") if schedule.end_time else "",
            "description": schedule.description or "",
            "place_name": schedule.place.name if schedule.place else "",
        } for schedule in queryset]
    }


def get_want_to_go(run_context):
    itinerary = run_context.itinerary
    places = list(itinerary.want_to_go_list.all().order_by("-priority", "planned_day", "id"))
    return {
        "places": [{
            "id": place.id,
            "name": place.name,
            "planned_day": place.planned_day or 0,
            "priority": place.priority or 3,
            "memo": place.memo or "",
            "address": place.address or "",
        } for place in places]
    }


def get_memo(run_context):
    itinerary = run_context.itinerary
    memo = getattr(itinerary, "memo_v2", None)
    memo_notes = normalize_memo_v2_notes(getattr(memo, "content", ""))
    return {
        "notes": [
            {"content": strip_tags(note.get("content", "")).strip()}
            for note in memo_notes
            if strip_tags(note.get("content", "")).strip()
        ]
    }


def get_checklist(run_context):
    itinerary = run_context.itinerary
    checklist = getattr(itinerary, "checklist_v2", None)
    checklist_lists = normalize_checklist_v2_content(getattr(checklist, "content", ""))
    if checklist_lists:
        return {"lists": checklist_lists}

    # V2チェックリスト未作成時は、既存_build_selected_contextと同じくレガシーItemへフォールバックする。
    legacy_items = list(itinerary.items.all().order_by("id"))
    if not legacy_items:
        return {"lists": []}

    return {
        "lists": [{
            "id": "legacy",
            "title": "持ち物リスト",
            "items": [
                {"id": str(item.id), "text": item.title, "checked": item.is_checked}
                for item in legacy_items
            ],
        }]
    }
