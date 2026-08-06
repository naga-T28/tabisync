import json
import logging
import urllib.parse
from io import BytesIO
from datetime import timedelta
from uuid import uuid4

from django.conf import settings
from django.core.files.base import ContentFile
from django.urls import reverse

from ..models import Itinerary, ScheduleV2


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



def _validate_optional_text(value, max_length, field_name):
    if value is None:
        return ""
    text = str(value).strip()
    if len(text) > max_length:
        raise ValueError(f"{field_name}は{max_length}文字以内で入力してください。")
    return text


def _validate_optional_float(value, field_name):
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        raise ValueError(f"{field_name}の形式が不正です。")


def _validate_optional_float_range(value, minimum, maximum, field_name):
    parsed = _validate_optional_float(value, field_name)
    if parsed is None:
        return None
    if not (minimum <= parsed <= maximum):
        raise ValueError(f"{field_name}は{minimum}〜{maximum}の範囲で指定してください。")
    return parsed


def _validate_day(value, itinerary):
    if value in (None, ""):
        return 0
    try:
        day = int(value)
    except (TypeError, ValueError):
        raise ValueError("Dayの形式が不正です。")
    max_day = itinerary.total_days or 0
    if day < 0 or day > max_day:
        raise ValueError(f"Dayは0〜{max_day}の範囲で指定してください。")
    return day


def _validate_optional_non_negative_int(value, field_name):
    if value in (None, ""):
        return None
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        raise ValueError(f"{field_name}の形式が不正です。")
    if parsed < 0:
        raise ValueError(f"{field_name}は0以上で指定してください。")
    return parsed


def _validate_priority(value):
    if value in (None, ""):
        return 3
    try:
        priority = int(value)
    except (TypeError, ValueError):
        raise ValueError("行きたい度の形式が不正です。")
    if priority not in (1, 2, 3, 4, 5):
        raise ValueError("行きたい度は1〜5で指定してください。")
    return priority


def apply_want_to_go_payload(place, data, itinerary, *, require_name=False):
    """行きたい場所の入力値を検証してplaceへ適用する。

    Google Places由来でも手入力でも、JS経由でもAI(コンシェルジュ)経由でも
    同じ検証ロジックを通す。dataにキーが存在する項目だけ検証・適用するため、
    部分更新（AIによる差分更新など）の意味論を維持しつつ、新規作成時には
    未指定項目にデフォルト値を適用する。不正な値は黙ってNone/デフォルトへ
    丸めず、ValueError(message)を送出する（呼び出し側で400へ変換すること）。
    """
    is_create = place.pk is None

    if "place_id" in data:
        place.place_id = _validate_optional_text(data.get("place_id"), 200, "place_id")

    if "name" in data:
        name = _validate_optional_text(data.get("name"), 200, "名称")
        if name:
            place.name = name
        elif require_name:
            raise ValueError("名称を入力してください。")
    elif require_name and not place.name:
        raise ValueError("名称を入力してください。")

    if "address" in data:
        place.address = _validate_optional_text(data.get("address"), 300, "住所")

    if "lat" in data:
        place.latitude = _validate_optional_float_range(data.get("lat"), -90, 90, "緯度")
    if "lng" in data:
        place.longitude = _validate_optional_float_range(data.get("lng"), -180, 180, "経度")
    if "rating" in data:
        place.rating = _validate_optional_float(data.get("rating"), "評価")

    if "memo" in data:
        place.memo = str(data.get("memo") or "")

    if "day" in data:
        place.planned_day = _validate_day(data.get("day"), itinerary)
    elif is_create:
        place.planned_day = 0

    if "stay_minutes" in data:
        place.stay_minutes = _validate_optional_non_negative_int(data.get("stay_minutes"), "滞在時間")

    if "priority" in data:
        place.priority = _validate_priority(data.get("priority"))
    elif is_create:
        place.priority = 3

    if "tag" in data:
        place.tag = _validate_optional_text(data.get("tag"), 50, "タグ")

    return place



# =========================
# v2スケジュール編集用ヘルパー
# =========================
# day_indexはTask 006のmigrationでNOT NULL化済みのため、常に保存済みの値をそのまま返す。
def get_schedule_day_index(itinerary, schedule):
    return schedule.day_index



def get_schedule_display_date(itinerary, day_index):
    # day_index から表示用の日付を逆算する
    if itinerary.start_date and day_index:
        return itinerary.start_date + timedelta(days=day_index - 1)
    return None



def reorder_schedules_for_day(itinerary, day_index):
    # 同じ Day 内の予定を開始時刻順に並び替えて order を振り直す。
    # 対象日の行だけをDB側でfilterし、変更が必要な行のみbulk_updateで一括更新する。
    if day_index is None:
        return

    day_schedules = list(itinerary.schedules.filter(day_index=day_index).order_by("start_time", "id"))

    to_update = []
    for i, schedule in enumerate(day_schedules):
        if schedule.order != i:
            schedule.order = i
            to_update.append(schedule)

    if to_update:
        ScheduleV2.objects.bulk_update(to_update, ["order"])



def count_schedules_for_day(itinerary, day_index, exclude_schedule_id=None):
    if day_index is None:
        return 0

    qs = itinerary.schedules.filter(day_index=day_index)
    if exclude_schedule_id:
        qs = qs.exclude(pk=exclude_schedule_id)
    return qs.count()



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

