import json
from datetime import datetime, timedelta
from uuid import uuid4

from ..models import ChecklistV2, MemoV2, ScheduleV2, WantToGo
from ..views.itinerary_helpers import (
    apply_want_to_go_payload,
    build_default_checklist_v2_lists,
    build_want_to_go_limit_message,
    can_add_want_to_go,
    count_schedules_for_day,
    get_schedule_day_index,
    get_schedule_display_date,
    normalize_checklist_v2_content,
    normalize_memo_v2_notes,
)
from ..views.utils import (
    MAX_CHECKLIST_ITEMS_PER_LIST,
    MAX_CHECKLISTS_PER_ITINERARY,
    MAX_MEMO_WORDS,
    MAX_MEMOS_PER_ITINERARY,
    MAX_SCHEDULES_PER_DAY,
    count_memo_words,
)

ALLOWED_EDIT_ACTIONS = {
    "schedule_create",
    "schedule_update",
    "schedule_delete",
    "want_create",
    "want_update",
    "want_delete",
    "memo_append",
    "checklist_add_item",
}


def _normalize_optional_float(value):
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def normalize_edit_actions(raw_actions, max_items=12):
    """モデル/クライアント由来のedit_actions配列を、既知のaction・上限件数・
    文字列化済みフィールドへ正規化する(views.concierge._normalize_edit_actions_for_responseと同一ロジック)。
    """
    if not isinstance(raw_actions, list):
        return []

    normalized = []
    for raw_action in raw_actions[:max_items]:
        if not isinstance(raw_action, dict):
            continue
        action = str(raw_action.get("action") or "").strip()
        if action not in ALLOWED_EDIT_ACTIONS:
            continue

        normalized.append({
            "action": action,
            "id": raw_action.get("id"),
            "day": raw_action.get("day"),
            "title": str(raw_action.get("title") or "").strip(),
            "description": str(raw_action.get("description") or "").strip(),
            "start_time": str(raw_action.get("start_time") or "").strip(),
            "end_time": str(raw_action.get("end_time") or "").strip(),
            "icon": str(raw_action.get("icon") or "").strip(),
            "place_name": str(raw_action.get("place_name") or "").strip(),
            "address": str(raw_action.get("address") or "").strip(),
            "place_id": str(raw_action.get("place_id") or "").strip(),
            "lat": _normalize_optional_float(raw_action.get("lat")),
            "lng": _normalize_optional_float(raw_action.get("lng")),
            "rating": _normalize_optional_float(raw_action.get("rating")),
            "memo": str(raw_action.get("memo") or "").strip(),
            "priority": raw_action.get("priority"),
            "content": str(raw_action.get("content") or "").strip(),
            "items": [
                str(item).strip()
                for item in raw_action.get("items", [])
                if str(item).strip()
            ][:20] if isinstance(raw_action.get("items"), list) else [],
        })
    return normalized


def apply_edit_action(itinerary, raw_action, touched_schedule_days):
    if not isinstance(raw_action, dict):
        raise ValueError("変更データの形式が不正です。")

    action = str(raw_action.get("action") or "").strip()
    if action in {"schedule_create", "schedule_update", "schedule_delete"}:
        return _apply_schedule_action(itinerary, action, raw_action, touched_schedule_days)
    if action in {"want_create", "want_update", "want_delete"}:
        return _apply_want_action(itinerary, action, raw_action)
    if action == "memo_append":
        return _apply_memo_action(itinerary, raw_action)
    if action == "checklist_add_item":
        return _apply_checklist_action(itinerary, raw_action)

    raise ValueError("対応していない変更です。")


def _parse_positive_int(value, field_name):
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        raise ValueError(f"{field_name}が不正です。")
    if parsed < 1:
        raise ValueError(f"{field_name}が不正です。")
    return parsed


def _parse_day(itinerary, value):
    day_index = _parse_positive_int(value, "Day")
    if not itinerary.total_days or day_index > itinerary.total_days:
        raise ValueError("存在しないDayです。")
    return day_index


def _parse_time(value, field_name, required=False):
    text = str(value or "").strip()
    if not text:
        if required:
            raise ValueError(f"{field_name}が不足しています。")
        return None
    try:
        return datetime.strptime(text, "%H:%M").time()
    except ValueError:
        raise ValueError(f"{field_name}はHH:MM形式で指定してください。")


def _clean_text(value, max_length, field_name="", required=False):
    text = str(value or "").strip()
    if required and not text:
        raise ValueError(f"{field_name or '必須項目'}が不足しています。")
    return text[:max_length]


def _apply_schedule_action(itinerary, action, raw_action, touched_schedule_days):
    if action == "schedule_delete":
        schedule_id = _parse_positive_int(raw_action.get("id"), "予定ID")
        schedule = ScheduleV2.objects.filter(pk=schedule_id, itinerary=itinerary).first()
        if not schedule:
            raise ValueError("対象の予定が見つかりません。")
        day_index = get_schedule_day_index(itinerary, schedule)
        schedule.delete()
        if day_index:
            touched_schedule_days.add(day_index)
        return {"action": action, "id": schedule_id, "label": "予定を削除しました"}

    allowed_icons = {choice[0] for choice in ScheduleV2.ICON_CHOICES}
    icon = str(raw_action.get("icon") or ScheduleV2.ICON_DEFAULT).strip()
    if icon not in allowed_icons:
        icon = ScheduleV2.ICON_DEFAULT

    if action == "schedule_create":
        day_index = _parse_day(itinerary, raw_action.get("day"))
        if count_schedules_for_day(itinerary, day_index) >= MAX_SCHEDULES_PER_DAY:
            raise ValueError(f"予定は1日につき{MAX_SCHEDULES_PER_DAY}件まで保存できます。")
        title = _clean_text(raw_action.get("title"), 30, "予定名", required=True)
        start_time = _parse_time(raw_action.get("start_time"), "開始時刻", required=True)
        end_time = _parse_time(raw_action.get("end_time"), "終了時刻")
        description = _clean_text(raw_action.get("description"), 100)
        place = _find_or_create_place(itinerary, raw_action)
        date_obj = get_schedule_display_date(itinerary, day_index) or itinerary.created_at.date() + timedelta(days=day_index - 1)
        schedule = ScheduleV2.objects.create(
            itinerary=itinerary,
            date=date_obj,
            day_index=day_index,
            title=title,
            icon=icon,
            description=description,
            start_time=start_time,
            end_time=end_time,
            place=place,
            order=0,
        )
        touched_schedule_days.add(day_index)
        return {"action": action, "id": schedule.id, "label": f"Day{day_index}に予定を追加しました"}

    if action == "schedule_update":
        schedule_id = _parse_positive_int(raw_action.get("id"), "予定ID")
        schedule = ScheduleV2.objects.filter(pk=schedule_id, itinerary=itinerary).first()
        if not schedule:
            raise ValueError("対象の予定が見つかりません。")
        old_day_index = get_schedule_day_index(itinerary, schedule)
        new_day_index = old_day_index

        if raw_action.get("day"):
            new_day_index = _parse_day(itinerary, raw_action.get("day"))
            if count_schedules_for_day(itinerary, new_day_index, schedule.id) >= MAX_SCHEDULES_PER_DAY:
                raise ValueError(f"予定は1日につき{MAX_SCHEDULES_PER_DAY}件まで保存できます。")
            schedule.day_index = new_day_index
            schedule.date = get_schedule_display_date(itinerary, new_day_index) or itinerary.created_at.date() + timedelta(days=new_day_index - 1)

        title = str(raw_action.get("title") or "").strip()
        if title:
            schedule.title = title[:30]

        description = str(raw_action.get("description") or "").strip()
        if description:
            schedule.description = description[:100]

        if raw_action.get("start_time"):
            schedule.start_time = _parse_time(raw_action.get("start_time"), "開始時刻", required=True)
        if raw_action.get("end_time") is not None:
            schedule.end_time = _parse_time(raw_action.get("end_time"), "終了時刻")

        schedule.icon = icon
        place = _find_or_create_place(itinerary, raw_action)
        if place:
            schedule.place = place
        schedule.save()

        if old_day_index:
            touched_schedule_days.add(old_day_index)
        if new_day_index:
            touched_schedule_days.add(new_day_index)
        return {"action": action, "id": schedule.id, "label": "予定を更新しました"}

    raise ValueError("対応していない予定変更です。")


def _build_want_to_go_data_from_action(raw_action):
    data = {}
    name = raw_action.get("place_name") or raw_action.get("title")
    if name is not None:
        data["name"] = name
    if raw_action.get("address") is not None:
        data["address"] = raw_action.get("address")
    if raw_action.get("place_id") is not None:
        data["place_id"] = raw_action.get("place_id")
    if raw_action.get("lat") is not None:
        data["lat"] = raw_action.get("lat")
    if raw_action.get("lng") is not None:
        data["lng"] = raw_action.get("lng")
    if raw_action.get("rating") is not None:
        data["rating"] = raw_action.get("rating")
    memo = raw_action.get("memo") or raw_action.get("description")
    if memo is not None:
        data["memo"] = memo
    if raw_action.get("day") is not None:
        data["day"] = raw_action.get("day")
    if raw_action.get("priority") is not None:
        data["priority"] = raw_action.get("priority")
    return data


def _find_or_create_place(itinerary, raw_action):
    place_name = str(raw_action.get("place_name") or "").strip()
    if not place_name:
        return None

    existing = WantToGo.objects.filter(itinerary=itinerary, name=place_name).order_by("id").first()
    if existing:
        return existing

    if not can_add_want_to_go(itinerary):
        raise ValueError(build_want_to_go_limit_message(itinerary))

    place = WantToGo(itinerary=itinerary)
    apply_want_to_go_payload(place, _build_want_to_go_data_from_action(raw_action), itinerary, require_name=True)
    place.save()
    return place


def _apply_want_action(itinerary, action, raw_action):
    if action == "want_delete":
        place_id = _parse_positive_int(raw_action.get("id"), "場所ID")
        place = WantToGo.objects.filter(pk=place_id, itinerary=itinerary).first()
        if not place:
            raise ValueError("対象の場所が見つかりません。")
        place.delete()
        return {"action": action, "id": place_id, "label": "行きたい場所を削除しました"}

    if action == "want_create":
        if not can_add_want_to_go(itinerary):
            raise ValueError(build_want_to_go_limit_message(itinerary))

        place = WantToGo(itinerary=itinerary)
        apply_want_to_go_payload(place, _build_want_to_go_data_from_action(raw_action), itinerary, require_name=True)
        place.save()
        return {"action": action, "id": place.id, "label": "行きたい場所を追加しました"}

    if action == "want_update":
        place_id = _parse_positive_int(raw_action.get("id"), "場所ID")
        place = WantToGo.objects.filter(pk=place_id, itinerary=itinerary).first()
        if not place:
            raise ValueError("対象の場所が見つかりません。")
        apply_want_to_go_payload(place, _build_want_to_go_data_from_action(raw_action), itinerary)
        place.save()
        return {"action": action, "id": place.id, "label": "行きたい場所を更新しました"}

    raise ValueError("対応していない場所変更です。")


def _apply_memo_action(itinerary, raw_action):
    content = _clean_text(raw_action.get("content") or raw_action.get("memo"), 4000, "メモ内容", required=True)
    memo, _ = MemoV2.objects.get_or_create(itinerary=itinerary)
    notes = normalize_memo_v2_notes(memo.content)
    if len(notes) >= MAX_MEMOS_PER_ITINERARY:
        raise ValueError(f"メモは最大{MAX_MEMOS_PER_ITINERARY}件まで保存できます。")
    if count_memo_words(content) > MAX_MEMO_WORDS:
        raise ValueError(f"メモは1件につき{MAX_MEMO_WORDS}語まで保存できます。")

    notes.append({"content": content})
    memo.content = json.dumps(notes, ensure_ascii=False)
    memo.save()
    return {"action": "memo_append", "label": "メモを追加しました"}


def _apply_checklist_action(itinerary, raw_action):
    items = [
        str(item).strip()[:100]
        for item in raw_action.get("items", [])
        if str(item).strip()
    ] if isinstance(raw_action.get("items"), list) else []
    content = str(raw_action.get("content") or "").strip()
    if content:
        items.append(content[:100])
    if not items:
        raise ValueError("追加するリスト項目がありません。")

    checklist, _ = ChecklistV2.objects.get_or_create(itinerary=itinerary)
    lists = normalize_checklist_v2_content(checklist.content)
    if not lists:
        lists = build_default_checklist_v2_lists()

    list_title = str(raw_action.get("title") or "持ち物リスト").strip()
    target_list = next((item_list for item_list in lists if item_list.get("title") == list_title), None)
    if not target_list:
        if len(lists) >= MAX_CHECKLISTS_PER_ITINERARY:
            raise ValueError(f"リストは最大{MAX_CHECKLISTS_PER_ITINERARY}リストまで保存できます。")

        target_list = {
            "id": f"list-{uuid4().hex[:10]}",
            "title": list_title,
            "items": [],
        }
        lists.append(target_list)

    available_slots = MAX_CHECKLIST_ITEMS_PER_LIST - len(target_list.get("items", []))
    if available_slots <= 0:
        raise ValueError(f"{target_list.get('title') or 'リスト'}は{MAX_CHECKLIST_ITEMS_PER_LIST}個まで保存できます。")
    if len(items) > available_slots:
        raise ValueError(f"{target_list.get('title') or 'リスト'}に追加できる項目はあと{available_slots}個です。")

    for item_text in items:
        target_list["items"].append({
            "id": f"item-{uuid4().hex[:10]}",
            "text": item_text,
            "checked": False,
        })

    checklist.content = json.dumps(lists, ensure_ascii=False)
    checklist.save()
    return {"action": "checklist_add_item", "label": "リスト項目を追加しました"}
