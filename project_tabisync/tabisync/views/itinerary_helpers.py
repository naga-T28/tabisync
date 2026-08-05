import json
import logging
import urllib.parse
from io import BytesIO
from datetime import timedelta
from uuid import uuid4

from django.conf import settings
from django.core.files.base import ContentFile
from django.urls import reverse

from ..models import Itinerary


logger = logging.getLogger(__name__)


def lock_itinerary_for_update(itinerary):
    """しおり単位の上限付き作成処理（行きたい場所・予定・AI利用枠）を直列化するため、
    Itinerary行をロックして再取得する。PostgreSQL本番環境では行ロックとして機能し、
    同時リクエストによる上限超過を防ぐ（SQLiteはFOR UPDATEに対応していないため、
    ロックとしては機能せずno-opの通常SELECTになる）。
    呼び出しは必ず transaction.atomic() の中で行うこと。
    """
    return Itinerary.objects.select_for_update().get(pk=itinerary.pk)


def get_itinerary_cover_url(itinerary):
    if not itinerary.cover_image:
        return ""

    return reverse("tabisync:content_v2_cover_image", kwargs={"pk": itinerary.pk, "token": itinerary.token})



def build_public_absolute_uri(request, path=None):
    target_path = path or request.get_full_path()
    scheme = "https" if getattr(settings, "USE_HTTPS", False) else request.scheme
    return f"{scheme}://{request.get_host()}{target_path}"



def build_itinerary_share_url(request, itinerary):
    return build_public_absolute_uri(
        request,
        reverse("tabisync:content_v2", kwargs={"pk": itinerary.pk, "token": itinerary.token})
    )



def ensure_itinerary_qr_code(itinerary, share_url):
    if itinerary.qr_code and itinerary.qr_code.storage.exists(itinerary.qr_code.name):
        return itinerary.qr_code.url

    filename = f"itinerary-{itinerary.pk}-{itinerary.token}.png"

    try:
        import qrcode
    except ImportError:
        qr_code_url = (
            "https://api.qrserver.com/v1/create-qr-code/"
            f"?size=220x220&data={urllib.parse.quote(share_url, safe='')}"
        )
        try:
            with urllib.request.urlopen(qr_code_url, timeout=10) as response:
                itinerary.qr_code.save(filename, ContentFile(response.read()), save=False)
            itinerary.save(update_fields=["qr_code"])
            return itinerary.qr_code.url
        except Exception:
            logger.exception("Failed to fetch and save QR code image.")
            return qr_code_url

    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=4,
    )
    qr.add_data(share_url)
    qr.make(fit=True)

    image = qr.make_image(fill_color="black", back_color="white")
    buffer = BytesIO()
    image.save(buffer, format="PNG")

    itinerary.qr_code.save(filename, ContentFile(buffer.getvalue()), save=False)
    itinerary.save(update_fields=["qr_code"])
    return itinerary.qr_code.url



def build_itinerary_qr_code_url(itinerary):
    return reverse("tabisync:content_v2_qr_code", kwargs={"pk": itinerary.pk, "token": itinerary.token})



def get_want_to_go_limit(itinerary):
    return itinerary.get_want_to_go_limit()



def can_add_want_to_go(itinerary):
    return itinerary.want_to_go_list.count() < get_want_to_go_limit(itinerary)



def build_want_to_go_limit_message(itinerary):
    return f"行きたいとこリストは1つのしおりにつき{get_want_to_go_limit(itinerary)}件まで保存できます。"



# 行きたい場所の詳細入力値を空文字/数値に正規化する
def parse_optional_float(value):
    if value in (None, ""):
        return None

    try:
        return float(value)
    except (TypeError, ValueError):
        return None



def parse_optional_int(value, default=None):
    if value in (None, ""):
        return default

    try:
        return int(value)
    except (TypeError, ValueError):
        return default



def apply_want_to_go_payload(place, data):
    # Google Places 由来でも手入力でも同じ保存ロジックを使う
    place.place_id = (data.get("place_id") or "").strip()
    place.name = (data.get("name") or place.name).strip()
    place.address = (data.get("address") or "").strip()
    place.latitude = parse_optional_float(data.get("lat"))
    place.longitude = parse_optional_float(data.get("lng"))
    place.rating = parse_optional_float(data.get("rating"))
    place.memo = data.get("memo", place.memo)
    place.planned_day = parse_optional_int(data.get("day"), default=0)
    place.stay_minutes = parse_optional_int(data.get("stay_minutes"))
    place.priority = parse_optional_int(data.get("priority"), default=3)
    place.tag = (data.get("tag") or "").strip()



# =========================
# v2スケジュール編集用ヘルパー
# =========================
# ScheduleV2 が持つ day_index と旧 date ベースの値を吸収する
def get_schedule_day_index(itinerary, schedule):
    if schedule.day_index:
        return schedule.day_index

    if itinerary.start_date and schedule.date:
        return (schedule.date - itinerary.start_date).days + 1

    return None



def get_schedule_display_date(itinerary, day_index):
    # day_index から表示用の日付を逆算する
    if itinerary.start_date and day_index:
        return itinerary.start_date + timedelta(days=day_index - 1)
    return None



def reorder_schedules_for_day(itinerary, day_index):
    # 同じ Day 内の予定を開始時刻順に並び替えて order を振り直す
    if day_index is None:
        return

    day_schedules = [
        schedule for schedule in itinerary.schedules.all().order_by("start_time", "id")
        if get_schedule_day_index(itinerary, schedule) == day_index
    ]

    for i, schedule in enumerate(day_schedules):
        if schedule.order != i:
            schedule.order = i
            schedule.save(update_fields=["order"])



def count_schedules_for_day(itinerary, day_index, exclude_schedule_id=None):
    if day_index is None:
        return 0

    count = 0
    for schedule in itinerary.schedules.all():
        if exclude_schedule_id and schedule.id == exclude_schedule_id:
            continue
        if get_schedule_day_index(itinerary, schedule) == day_index:
            count += 1
    return count



def build_day_choices(itinerary):
    # テンプレートで使う Day 選択肢を組み立てる
    choices = []

    if itinerary.total_days:
        for day_num in range(1, itinerary.total_days + 1):
            display_date = get_schedule_display_date(itinerary, day_num)
            choices.append({
                "value": f"day-{day_num}",
                "label": f"Day {day_num}",
                "day_num": day_num,
                "date_obj": display_date,
                "calendar_date": display_date.strftime("%Y-%m-%d") if display_date else "",
                "is_date_mode": bool(display_date),
            })
        return choices

    return []



def build_google_maps_search_url(place):
    if not place:
        return ""

    params = {"api": "1", "query": place.name or "Google"}
    if place.place_id:
        params["query_place_id"] = place.place_id
    return f"https://www.google.com/maps/search/?{urllib.parse.urlencode(params)}"



def normalize_memo_v2_notes(raw_content):
    if not raw_content:
        return []

    try:
        parsed = json.loads(raw_content)
    except (TypeError, ValueError):
        stripped = str(raw_content).strip()
        return [{"content": stripped}] if stripped else []

    if isinstance(parsed, dict):
        parsed = parsed.get("notes", [])

    if not isinstance(parsed, list):
        return []

    normalized_notes = []
    for note in parsed:
        if not isinstance(note, dict):
            continue

        content = str(note.get("content", "")).strip()
        if not content:
            continue

        normalized_notes.append({"content": content})

    return normalized_notes



def normalize_checklist_v2_content(raw_content):
    if not raw_content:
        return []

    try:
        parsed = json.loads(raw_content)
    except (TypeError, ValueError):
        return []

    if isinstance(parsed, dict):
        parsed = parsed.get("lists", [])

    if not isinstance(parsed, list):
        return []

    normalized_lists = []
    for checklist in parsed:
        if not isinstance(checklist, dict):
            continue

        title = str(checklist.get("title", "")).strip()
        items = checklist.get("items", [])
        if not isinstance(items, list):
            items = []

        normalized_items = []
        for item in items:
            if not isinstance(item, dict):
                continue

            text = str(item.get("text", "")).strip()
            if not text:
                continue

            normalized_items.append({
                "id": str(item.get("id") or f"item-{uuid4().hex[:10]}"),
                "text": text,
                "checked": bool(item.get("checked", False)),
            })

        if not title and not normalized_items:
            continue

        normalized_lists.append({
            "id": str(checklist.get("id") or f"list-{uuid4().hex[:10]}"),
            "title": title,
            "items": normalized_items,
        })

    return normalized_lists



def build_default_checklist_v2_lists():
    return [{
        "id": f"list-{uuid4().hex[:10]}",
        "title": "持ち物リスト",
        "items": [],
    }]

