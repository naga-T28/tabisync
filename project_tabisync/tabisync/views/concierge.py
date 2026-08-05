import json
import logging
from datetime import datetime, timedelta
from uuid import UUID, uuid4

from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.utils.html import strip_tags
from django.views import View
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_POST
from django_ratelimit.decorators import ratelimit

from ..models import ChecklistV2, ConciergeChatLog, MemoV2, ScheduleV2, WantToGo
from ..openai_concierge import OpenAIConciergeError, run_answer, run_data_selection, run_moderation
from .access_control import (
    ViewPasswordRequiredMixin,
    get_itinerary_or_404,
    require_edit_access_json,
    require_view_access_json,
)
from .itinerary_helpers import (
    build_default_checklist_v2_lists,
    build_want_to_go_limit_message,
    can_add_want_to_go,
    count_schedules_for_day,
    get_schedule_day_index,
    get_schedule_display_date,
    lock_itinerary_for_update,
    normalize_checklist_v2_content,
    normalize_memo_v2_notes,
    parse_optional_int,
    reorder_schedules_for_day,
)
from .utils import (
    CONCIERGE_USER_MESSAGE_MAX_LENGTH,
    MAX_CHECKLIST_ITEMS_PER_LIST,
    MAX_CHECKLISTS_PER_ITINERARY,
    MAX_MEMO_WORDS,
    MAX_MEMOS_PER_ITINERARY,
    MAX_SCHEDULES_PER_DAY,
    build_public_service_error_message,
    count_memo_words,
    ratelimit_client_ip,
)


logger = logging.getLogger(__name__)


@method_decorator(ratelimit(key=ratelimit_client_ip, rate='20/m', block=True), name='dispatch')
class ConciergeV2View(ViewPasswordRequiredMixin, View):
    template_name = "tabisync/content/concierge_v2.html"

    @method_decorator(ensure_csrf_cookie)
    def get(self, request, pk, token):
        first_date_str = None
        last_date_str = None
        if self.itinerary.start_date and self.itinerary.end_date:
            first_date_str = self.itinerary.start_date.strftime("%Y.%m.%d")
            last_date_str = self.itinerary.end_date.strftime("%Y.%m.%d")
        concierge_daily_limit = self.itinerary.get_concierge_daily_limit()
        concierge_today_count = self._get_today_usage_count()

        return render(request, self.template_name, {
            "itinerary": self.itinerary,
            "first_date_str": first_date_str,
            "last_date_str": last_date_str,
            "concierge_daily_limit": concierge_daily_limit,
            "concierge_today_count": min(concierge_today_count, concierge_daily_limit),
        })

    def post(self, request, pk, token):
        try:
            body = json.loads(request.body.decode("utf-8"))
        except (TypeError, ValueError, json.JSONDecodeError):
            return JsonResponse({"status": "error", "message": "不正なJSONです。"}, status=400)

        user_message = str(body.get("message") or "").strip()
        if not user_message:
            return JsonResponse({"status": "error", "message": "メッセージを入力してください。"}, status=400)
        if len(user_message) > CONCIERGE_USER_MESSAGE_MAX_LENGTH:
            return JsonResponse({
                "status": "error",
                "message": f"メッセージは{CONCIERGE_USER_MESSAGE_MAX_LENGTH}字以内で入力してください。",
            }, status=400)

        if user_message == "__ping__":
            return JsonResponse({
                "status": "ok",
                "reply": "concierge ping ok",
                "debug": {
                    "view": "ConciergeV2View.post",
                    "itinerary_id": self.itinerary.pk,
                },
            })

        raw_conversation_id = str(body.get("conversation_id") or "").strip()
        conversation_id = self._parse_conversation_id(raw_conversation_id)
        history = self._normalize_history(body.get("history"))
        turn_index = len([item for item in history if item.get("role") == "user"]) + 1
        daily_limit = self.itinerary.get_concierge_daily_limit()

        # 日次上限のチェックと利用枠の予約(ConciergeChatLogの仮登録)を、
        # 外部API呼び出し(長時間かかりうる)より前に同一トランザクション・行ロック内で行う。
        # これにより「countしてからcreate」の競合で上限を超えて呼び出せてしまう問題を防ぐ。
        # DBロックは予約の間だけ保持し、外部API呼び出し中は保持しない。
        try:
            with transaction.atomic():
                locked_itinerary = lock_itinerary_for_update(self.itinerary)
                today_count = ConciergeChatLog.objects.filter(
                    itinerary=locked_itinerary,
                    created_at__date=timezone.localdate(),
                ).count()

                if today_count >= daily_limit:
                    return JsonResponse({
                        "status": "limit_exceeded",
                        "message": f"本日の利用上限に達しました。日付が変わってから再度お試しください。({daily_limit}回/日)",
                        "conversation_id": str(conversation_id),
                        "daily_limit": daily_limit,
                        "remaining_count": 0,
                    }, status=429)

                reservation = ConciergeChatLog.objects.create(
                    itinerary=locked_itinerary,
                    conversation_id=conversation_id,
                    turn_index=turn_index,
                    user_message=user_message,
                )
        except Exception:
            logger.exception("Failed to reserve concierge usage slot for itinerary_id=%s", self.itinerary.pk)
            return JsonResponse({
                "status": "error",
                "message": "AIコンシェルジュの利用状況を確認できませんでした。DB設定を確認してください。",
            }, status=500)

        # ここから先は外部API呼び出し。失敗時は予約を解放し、日次上限を消費しない
        # （＝失敗した呼び出しはカウントしない仕様）。
        try:
            moderation_prompt, moderation_payload, moderation_result = run_moderation(user_message, history)
        except OpenAIConciergeError as exc:
            logger.warning(
                "Concierge moderation failed for itinerary_id=%s: %s",
                self.itinerary.pk,
                exc,
            )
            self._release_reservation_safely(reservation)
            return JsonResponse({
                "status": "error",
                "message": build_public_service_error_message(
                    exc,
                    "AIコンシェルジュの安全判定に失敗しました。",
                ),
            }, status=502)
        except Exception:
            logger.exception("Unexpected moderation failure for itinerary_id=%s", self.itinerary.pk)
            self._release_reservation_safely(reservation)
            return JsonResponse({"status": "error", "message": "AIコンシェルジュの安全判定で予期しないエラーが発生しました。"}, status=500)

        if not moderation_result.get("allowed", False):
            assistant_message = moderation_result.get("reason") or "この内容には対応できません。"
            self._finalize_chat_log_safely(
                reservation,
                moderation_prompt=self._merge_prompt_and_payload(moderation_prompt, moderation_payload),
                moderation_result=moderation_result,
                assistant_message=assistant_message,
            )
            return JsonResponse({
                "status": "blocked",
                "conversation_id": str(conversation_id),
                "reply": assistant_message,
                "daily_limit": daily_limit,
                "remaining_count": max(daily_limit - (today_count + 1), 0),
            })

        try:
            selection_prompt, selection_payload, selection_result = run_data_selection(user_message, history)
        except OpenAIConciergeError as exc:
            logger.warning(
                "Concierge data selection failed for itinerary_id=%s: %s",
                self.itinerary.pk,
                exc,
            )
            self._release_reservation_safely(reservation)
            return JsonResponse({
                "status": "error",
                "message": build_public_service_error_message(
                    exc,
                    "AIコンシェルジュの文脈選択に失敗しました。",
                ),
            }, status=502)
        except Exception:
            logger.exception("Unexpected data-selection failure for itinerary_id=%s", self.itinerary.pk)
            self._release_reservation_safely(reservation)
            return JsonResponse({"status": "error", "message": "AIコンシェルジュの文脈選択で予期しないエラーが発生しました。"}, status=500)

        required_data = selection_result.get("required_data", [])
        try:
            selected_context = self._build_selected_context(required_data)
        except Exception:
            logger.exception("Failed to build concierge context for itinerary_id=%s", self.itinerary.pk)
            self._release_reservation_safely(reservation)
            return JsonResponse({"status": "error", "message": "AIコンシェルジュ用の旅程データを組み立てられませんでした。"}, status=500)

        try:
            answer_prompt, answer_payload, assistant_message, edit_actions = run_answer(history, user_message, selected_context)
        except OpenAIConciergeError as exc:
            logger.warning(
                "Concierge answer generation failed for itinerary_id=%s: %s",
                self.itinerary.pk,
                exc,
            )
            self._release_reservation_safely(reservation)
            return JsonResponse({
                "status": "error",
                "message": build_public_service_error_message(
                    exc,
                    "AIコンシェルジュの回答生成に失敗しました。",
                ),
            }, status=502)
        except Exception:
            logger.exception("Unexpected answer generation failure for itinerary_id=%s", self.itinerary.pk)
            self._release_reservation_safely(reservation)
            return JsonResponse({"status": "error", "message": "AIコンシェルジュの回答生成で予期しないエラーが発生しました。"}, status=500)

        self._finalize_chat_log_safely(
            reservation,
            moderation_prompt=self._merge_prompt_and_payload(moderation_prompt, moderation_payload),
            moderation_result=moderation_result,
            data_selection_prompt=self._merge_prompt_and_payload(selection_prompt, selection_payload),
            data_selection_result=selection_result,
            answer_prompt=self._merge_prompt_and_payload(answer_prompt, answer_payload),
            answer_context=selected_context,
            assistant_message=assistant_message,
        )

        return JsonResponse({
            "status": "ok",
            "conversation_id": str(conversation_id),
            "reply": assistant_message,
            "edit_actions": self._normalize_edit_actions_for_response(edit_actions),
            "required_data": required_data,
            "daily_limit": daily_limit,
            "remaining_count": max(daily_limit - (today_count + 1), 0),
        })

    def _normalize_edit_actions_for_response(self, raw_actions):
        if not isinstance(raw_actions, list):
            return []

        allowed_actions = {
            "schedule_create",
            "schedule_update",
            "schedule_delete",
            "want_create",
            "want_update",
            "want_delete",
            "memo_append",
            "checklist_add_item",
        }
        normalized = []
        for raw_action in raw_actions[:12]:
            if not isinstance(raw_action, dict):
                continue
            action = str(raw_action.get("action") or "").strip()
            if action not in allowed_actions:
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

    def _parse_conversation_id(self, raw_value):
        try:
            return UUID(raw_value)
        except (ValueError, TypeError, AttributeError):
            return uuid4()

    def _normalize_history(self, raw_history):
        if not isinstance(raw_history, list):
            return []

        normalized_history = []
        for item in raw_history[-8:]:
            if not isinstance(item, dict):
                continue
            role = str(item.get("role") or "").strip()
            content = str(item.get("content") or "").strip()
            if role not in {"user", "assistant"} or not content:
                continue
            normalized_history.append({
                "role": role,
                "content": content[:1500],
            })
        return normalized_history

    def _get_today_usage_count(self):
        return ConciergeChatLog.objects.filter(
            itinerary=self.itinerary,
            created_at__date=timezone.localdate(),
        ).count()

    def _build_selected_context(self, required_data):
        context = {
            "itinerary": {
                "title": self.itinerary.title,
                "subtitle": self.itinerary.subtitle or "",
                "description": self.itinerary.description or "",
                "start_date": self.itinerary.start_date.strftime("%Y-%m-%d") if self.itinerary.start_date else "",
                "end_date": self.itinerary.end_date.strftime("%Y-%m-%d") if self.itinerary.end_date else "",
                "total_days": self.itinerary.total_days or 0,
            }
        }

        requested = set(required_data)

        if "schedule" in requested:
            schedules = list(
                self.itinerary.schedules.select_related("place").all().order_by("day_index", "start_time", "order", "id")
            )
            context["schedule"] = [{
                "id": schedule.id,
                "day_index": get_schedule_day_index(self.itinerary, schedule) or schedule.day_index or 0,
                "date": schedule.date.strftime("%Y-%m-%d") if schedule.date else "",
                "title": schedule.title,
                "start_time": schedule.start_time.strftime("%H:%M") if schedule.start_time else "",
                "end_time": schedule.end_time.strftime("%H:%M") if schedule.end_time else "",
                "description": schedule.description or "",
                "place_name": schedule.place.name if schedule.place else "",
            } for schedule in schedules]

        if "want_to_go" in requested:
            places = list(self.itinerary.want_to_go_list.all().order_by("-priority", "planned_day", "id"))
            context["want_to_go"] = [{
                "id": place.id,
                "name": place.name,
                "planned_day": place.planned_day or 0,
                "priority": place.priority or 3,
                "memo": place.memo or "",
                "address": place.address or "",
            } for place in places]

        if "items" in requested:
            checklist = getattr(self.itinerary, "checklist_v2", None)
            checklist_lists = normalize_checklist_v2_content(getattr(checklist, "content", ""))
            if checklist_lists:
                context["items"] = checklist_lists
            else:
                items = list(self.itinerary.items.all().order_by("id"))
                context["items"] = [{
                    "title": item.title,
                    "detail": item.detail or "",
                    "is_checked": item.is_checked,
                } for item in items]

        if "memo" in requested:
            memo = getattr(self.itinerary, "memo_v2", None)
            memo_notes = normalize_memo_v2_notes(getattr(memo, "content", ""))
            context["memo"] = [{
                "content": strip_tags(note.get("content", "")).strip()
            } for note in memo_notes if strip_tags(note.get("content", "")).strip()]

        return context

    def _merge_prompt_and_payload(self, prompt_text, payload):
        return f"{prompt_text}\n\n--- REQUEST PAYLOAD ---\n{json.dumps(payload, ensure_ascii=False, indent=2)}"

    def _finalize_chat_log(
        self,
        reservation,
        moderation_prompt="",
        moderation_result=None,
        data_selection_prompt="",
        data_selection_result=None,
        answer_prompt="",
        answer_context=None,
        assistant_message="",
    ):
        # post()の冒頭で予約済みのConciergeChatLog行に結果を書き戻す（新規作成はしない）。
        reservation.moderation_prompt = moderation_prompt
        reservation.moderation_result = moderation_result or {}
        reservation.data_selection_prompt = data_selection_prompt
        reservation.data_selection_result = data_selection_result or {}
        reservation.answer_prompt = answer_prompt
        reservation.answer_context = answer_context or {}
        reservation.assistant_message = assistant_message
        reservation.save()

    def _finalize_chat_log_safely(self, reservation, **kwargs):
        try:
            self._finalize_chat_log(reservation, **kwargs)
        except Exception:
            logger.exception("Failed to save concierge chat log for itinerary_id=%s", self.itinerary.pk)

    def _release_reservation_safely(self, reservation):
        # 外部API呼び出し失敗時に予約を取り消し、日次上限を消費しない（失敗は不課金の仕様）。
        try:
            reservation.delete()
        except Exception:
            logger.exception(
                "Failed to release concierge usage reservation id=%s for itinerary_id=%s",
                reservation.pk,
                self.itinerary.pk,
            )



@require_POST
@ratelimit(key=ratelimit_client_ip, rate='20/m', block=True)
def concierge_v2_apply_changes(request, pk, token):
    itinerary = get_itinerary_or_404(pk, token)

    view_gate_response = require_view_access_json(request, itinerary)
    if view_gate_response is not None:
        return view_gate_response

    edit_gate_response = require_edit_access_json(request, itinerary)
    if edit_gate_response is not None:
        return edit_gate_response

    try:
        data = json.loads(request.body.decode("utf-8"))
    except (TypeError, ValueError, json.JSONDecodeError):
        return JsonResponse({"status": "error", "message": "不正なJSONです。"}, status=400)

    actions = data.get("edit_actions", [])
    if not isinstance(actions, list) or not actions:
        return JsonResponse({"status": "error", "message": "適用する変更がありません。"}, status=400)

    if len(actions) > 12:
        return JsonResponse({"status": "error", "message": "一度に適用できる変更は12件までです。"}, status=400)

    try:
        with transaction.atomic():
            # 行きたい場所・予定の件数上限チェックをこのバッチ全体で直列化するため、
            # 個々のアクション処理前にItinerary行をロックする。
            itinerary = lock_itinerary_for_update(itinerary)
            results = []
            touched_schedule_days = set()
            for raw_action in actions:
                result = _apply_concierge_edit_action(itinerary, raw_action, touched_schedule_days)
                if result:
                    results.append(result)

            for day_index in touched_schedule_days:
                reorder_schedules_for_day(itinerary, day_index)
    except ValueError as exc:
        return JsonResponse({"status": "error", "message": str(exc)}, status=400)

    return JsonResponse({
        "status": "ok",
        "applied_count": len(results),
        "results": results,
    })



def _apply_concierge_edit_action(itinerary, raw_action, touched_schedule_days):
    if not isinstance(raw_action, dict):
        raise ValueError("変更データの形式が不正です。")

    action = str(raw_action.get("action") or "").strip()
    if action in {"schedule_create", "schedule_update", "schedule_delete"}:
        return _apply_concierge_schedule_action(itinerary, action, raw_action, touched_schedule_days)
    if action in {"want_create", "want_update", "want_delete"}:
        return _apply_concierge_want_action(itinerary, action, raw_action)
    if action == "memo_append":
        return _apply_concierge_memo_action(itinerary, raw_action)
    if action == "checklist_add_item":
        return _apply_concierge_checklist_action(itinerary, raw_action)

    raise ValueError("対応していない変更です。")



def _parse_concierge_positive_int(value, field_name):
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        raise ValueError(f"{field_name}が不正です。")
    if parsed < 1:
        raise ValueError(f"{field_name}が不正です。")
    return parsed



def _parse_concierge_day(itinerary, value):
    day_index = _parse_concierge_positive_int(value, "Day")
    if not itinerary.total_days or day_index > itinerary.total_days:
        raise ValueError("存在しないDayです。")
    return day_index



def _parse_concierge_time(value, field_name, required=False):
    text = str(value or "").strip()
    if not text:
        if required:
            raise ValueError(f"{field_name}が不足しています。")
        return None
    try:
        return datetime.strptime(text, "%H:%M").time()
    except ValueError:
        raise ValueError(f"{field_name}はHH:MM形式で指定してください。")



def _clean_concierge_text(value, max_length, field_name="", required=False):
    text = str(value or "").strip()
    if required and not text:
        raise ValueError(f"{field_name or '必須項目'}が不足しています。")
    return text[:max_length]



def _apply_concierge_schedule_action(itinerary, action, raw_action, touched_schedule_days):
    if action == "schedule_delete":
        schedule_id = _parse_concierge_positive_int(raw_action.get("id"), "予定ID")
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
        day_index = _parse_concierge_day(itinerary, raw_action.get("day"))
        if count_schedules_for_day(itinerary, day_index) >= MAX_SCHEDULES_PER_DAY:
            raise ValueError(f"予定は1日につき{MAX_SCHEDULES_PER_DAY}件まで保存できます。")
        title = _clean_concierge_text(raw_action.get("title"), 30, "予定名", required=True)
        start_time = _parse_concierge_time(raw_action.get("start_time"), "開始時刻", required=True)
        end_time = _parse_concierge_time(raw_action.get("end_time"), "終了時刻")
        description = _clean_concierge_text(raw_action.get("description"), 100)
        place = _find_or_create_concierge_place(itinerary, raw_action)
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
        schedule_id = _parse_concierge_positive_int(raw_action.get("id"), "予定ID")
        schedule = ScheduleV2.objects.filter(pk=schedule_id, itinerary=itinerary).first()
        if not schedule:
            raise ValueError("対象の予定が見つかりません。")
        old_day_index = get_schedule_day_index(itinerary, schedule)
        new_day_index = old_day_index

        if raw_action.get("day"):
            new_day_index = _parse_concierge_day(itinerary, raw_action.get("day"))
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
            schedule.start_time = _parse_concierge_time(raw_action.get("start_time"), "開始時刻", required=True)
        if raw_action.get("end_time") is not None:
            schedule.end_time = _parse_concierge_time(raw_action.get("end_time"), "終了時刻")

        schedule.icon = icon
        place = _find_or_create_concierge_place(itinerary, raw_action)
        if place:
            schedule.place = place
        schedule.save()

        if old_day_index:
            touched_schedule_days.add(old_day_index)
        if new_day_index:
            touched_schedule_days.add(new_day_index)
        return {"action": action, "id": schedule.id, "label": "予定を更新しました"}

    raise ValueError("対応していない予定変更です。")



def _find_or_create_concierge_place(itinerary, raw_action):
    place_name = str(raw_action.get("place_name") or "").strip()
    if not place_name:
        return None

    existing = WantToGo.objects.filter(itinerary=itinerary, name=place_name).order_by("id").first()
    if existing:
        return existing

    if not can_add_want_to_go(itinerary):
        raise ValueError(build_want_to_go_limit_message(itinerary))

    return WantToGo.objects.create(
        itinerary=itinerary,
        name=place_name[:200],
        address=str(raw_action.get("address") or "").strip()[:300],
        memo=str(raw_action.get("memo") or "").strip(),
        planned_day=parse_optional_int(raw_action.get("day"), default=0) or 0,
        priority=parse_optional_int(raw_action.get("priority"), default=3) or 3,
    )



def _apply_concierge_want_action(itinerary, action, raw_action):
    if action == "want_delete":
        place_id = _parse_concierge_positive_int(raw_action.get("id"), "場所ID")
        place = WantToGo.objects.filter(pk=place_id, itinerary=itinerary).first()
        if not place:
            raise ValueError("対象の場所が見つかりません。")
        place.delete()
        return {"action": action, "id": place_id, "label": "行きたい場所を削除しました"}

    if action == "want_create":
        if not can_add_want_to_go(itinerary):
            raise ValueError(build_want_to_go_limit_message(itinerary))

        name = _clean_concierge_text(raw_action.get("place_name") or raw_action.get("title"), 200, "場所名", required=True)
        place = WantToGo.objects.create(
            itinerary=itinerary,
            name=name,
            address=str(raw_action.get("address") or "").strip()[:300],
            memo=str(raw_action.get("memo") or raw_action.get("description") or "").strip(),
            planned_day=parse_optional_int(raw_action.get("day"), default=0) or 0,
            priority=parse_optional_int(raw_action.get("priority"), default=3) or 3,
        )
        return {"action": action, "id": place.id, "label": "行きたい場所を追加しました"}

    if action == "want_update":
        place_id = _parse_concierge_positive_int(raw_action.get("id"), "場所ID")
        place = WantToGo.objects.filter(pk=place_id, itinerary=itinerary).first()
        if not place:
            raise ValueError("対象の場所が見つかりません。")
        name = str(raw_action.get("place_name") or raw_action.get("title") or "").strip()
        if name:
            place.name = name[:200]
        address = str(raw_action.get("address") or "").strip()
        if address:
            place.address = address[:300]
        memo = str(raw_action.get("memo") or raw_action.get("description") or "").strip()
        if memo:
            place.memo = memo
        if raw_action.get("day") is not None:
            place.planned_day = parse_optional_int(raw_action.get("day"), default=0) or 0
        if raw_action.get("priority") is not None:
            place.priority = parse_optional_int(raw_action.get("priority"), default=3) or 3
        place.save()
        return {"action": action, "id": place.id, "label": "行きたい場所を更新しました"}

    raise ValueError("対応していない場所変更です。")



def _apply_concierge_memo_action(itinerary, raw_action):
    content = _clean_concierge_text(raw_action.get("content") or raw_action.get("memo"), 4000, "メモ内容", required=True)
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



def _apply_concierge_checklist_action(itinerary, raw_action):
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

