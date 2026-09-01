import json
import logging
import urllib.parse
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

from ..concierge_agent.agent import run_agent
from ..concierge_agent.context import RunContext, is_agent_mode_enabled
from ..concierge_agent.errors import ConciergeAgentError
from ..concierge_agent.link_preview import MAX_LINK_PREVIEW_URLS_PER_REQUEST, get_link_preview
from ..concierge_agent.registry import get_registry
from ..concierge_agent.usage import DailyRunUsageService, RunUsageCounters
from ..concierge_tools import edit_actions as edit_actions_service
from ..models import ConciergeChatLog
from ..openai_concierge import OpenAIConciergeError, run_answer, run_data_selection, run_moderation
from .access_control import (
    ViewPasswordRequiredMixin,
    get_itinerary_or_404,
    has_edit_access,
    require_edit_access_json,
    require_view_access_json,
)
from .itinerary_helpers import (
    get_schedule_day_index,
    lock_itinerary_for_update,
    normalize_checklist_v2_content,
    normalize_memo_v2_notes,
    reorder_schedules_for_day,
)
from .utils import (
    CONCIERGE_USER_MESSAGE_MAX_LENGTH,
    build_public_service_error_message,
    parse_json_object_body,
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
        body, error_response = parse_json_object_body(request)
        if error_response is not None:
            return error_response

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

        # 日次上限のチェックと利用枠の予約(ConciergeChatLogの仮登録)を、
        # 外部API呼び出し(長時間かかりうる)より前に同一トランザクション・行ロック内で行う。
        # legacy/agent両経路がこの予約ロジックを共有することで、上限判定が2箇所へ
        # 分岐して不整合を起こすリスクを無くす(DailyRunUsageService.reserve参照)。
        try:
            reservation, today_count, daily_limit = DailyRunUsageService.reserve(
                self.itinerary, conversation_id, turn_index, user_message,
            )
        except Exception:
            logger.exception("Failed to reserve concierge usage slot for itinerary_id=%s", self.itinerary.pk)
            return JsonResponse({
                "status": "error",
                "message": "AIコンシェルジュの利用状況を確認できませんでした。DB設定を確認してください。",
            }, status=500)

        if reservation is None:
            return JsonResponse({
                "status": "limit_exceeded",
                "message": f"本日の利用上限に達しました。日付が変わってから再度お試しください。({daily_limit}回/日)",
                "conversation_id": str(conversation_id),
                "daily_limit": daily_limit,
                "remaining_count": 0,
            }, status=429)

        if is_agent_mode_enabled(self.itinerary):
            return self._post_agent_mode(
                request, user_message, history, reservation, conversation_id, daily_limit, today_count,
            )
        return self._post_legacy_mode(
            user_message, history, reservation, conversation_id, daily_limit, today_count,
        )

    def _post_legacy_mode(self, user_message, history, reservation, conversation_id, daily_limit, today_count):
        # ここから先は外部API呼び出し。失敗時は予約を解放し、日次上限を消費しない
        # （＝失敗した呼び出しはカウントしない仕様）。
        try:
            moderation_prompt, moderation_payload, moderation_result = run_moderation(
                user_message, history, conversation_id=conversation_id,
            )
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
            selection_prompt, selection_payload, selection_result = run_data_selection(
                user_message, history, conversation_id=conversation_id,
            )
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
            answer_prompt, answer_payload, assistant_message, edit_actions = run_answer(
                history, user_message, selected_context, conversation_id=conversation_id,
            )
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

    def _post_agent_mode(self, request, user_message, history, reservation, conversation_id, daily_limit, today_count):
        try:
            moderation_prompt, moderation_payload, moderation_result = run_moderation(
                user_message, history, conversation_id=conversation_id,
            )
        except OpenAIConciergeError as exc:
            logger.warning(
                "Concierge agent moderation failed for itinerary_id=%s: %s",
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
            logger.exception("Unexpected agent moderation failure for itinerary_id=%s", self.itinerary.pk)
            self._release_reservation_safely(reservation)
            return JsonResponse({"status": "error", "message": "AIコンシェルジュの安全判定で予期しないエラーが発生しました。"}, status=500)

        if not moderation_result.get("allowed", False):
            assistant_message = moderation_result.get("reason") or "この内容には対応できません。"
            self._finalize_chat_log_safely(
                reservation,
                moderation_prompt=self._merge_prompt_and_payload(moderation_prompt, moderation_payload),
                moderation_result=moderation_result,
                assistant_message=assistant_message,
                engine="agent",
                run_status="blocked",
            )
            return JsonResponse({
                "status": "blocked",
                "conversation_id": str(conversation_id),
                "reply": assistant_message,
                "daily_limit": daily_limit,
                "remaining_count": max(daily_limit - (today_count + 1), 0),
            })

        run_context = RunContext(
            itinerary=self.itinerary,
            can_edit=has_edit_access(request, self.itinerary),
            conversation_id=conversation_id,
        )
        counters = RunUsageCounters.from_env()

        try:
            registry = get_registry()
            result = run_agent(user_message, history, run_context, registry, counters)
        except OpenAIConciergeError as exc:
            logger.warning("Concierge agent run failed for itinerary_id=%s: %s", self.itinerary.pk, exc)
            self._release_reservation_safely(reservation)
            return JsonResponse({
                "status": "error",
                "message": build_public_service_error_message(
                    exc,
                    "AIコンシェルジュの処理に失敗しました。",
                ),
            }, status=502)
        except ConciergeAgentError as exc:
            logger.warning("Concierge agent run rejected for itinerary_id=%s: %s", self.itinerary.pk, exc)
            self._release_reservation_safely(reservation)
            return JsonResponse({"status": "error", "message": "AIコンシェルジュの処理を完了できませんでした。"}, status=502)
        except Exception:
            logger.exception("Unexpected agent run failure for itinerary_id=%s", self.itinerary.pk)
            self._release_reservation_safely(reservation)
            return JsonResponse({"status": "error", "message": "AIコンシェルジュの処理で予期しないエラーが発生しました。"}, status=500)

        ui_component_types = [
            component.get("type") for component in result.ui_components if isinstance(component, dict)
        ]

        try:
            result.trace.persist_tool_calls(reservation)
        except Exception:
            logger.exception("Failed to save concierge tool call logs for itinerary_id=%s", self.itinerary.pk)

        self._finalize_chat_log_safely(
            reservation,
            moderation_prompt=self._merge_prompt_and_payload(moderation_prompt, moderation_payload),
            moderation_result=moderation_result,
            assistant_message=result.reply_markdown,
            engine="agent",
            selected_skill_ids=result.trace.selected_skill_ids,
            openai_call_count=result.trace.openai_call_count,
            tool_call_count=len(result.trace.tool_call_records),
            web_search_call_count=result.trace.web_search_call_count,
            ui_component_types=ui_component_types,
            edit_action_count=len(result.edit_actions),
            run_status=result.run_status,
        )

        return JsonResponse({
            "status": "ok",
            "conversation_id": str(conversation_id),
            "reply": result.reply_markdown,
            "edit_actions": result.edit_actions,
            "ui_components": result.ui_components,
            "citations": result.citations,
            "daily_limit": daily_limit,
            "remaining_count": max(daily_limit - (today_count + 1), 0),
        })

    def _normalize_edit_actions_for_response(self, raw_actions):
        return edit_actions_service.normalize_edit_actions(raw_actions, max_items=12)

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

    def _finalize_chat_log_safely(self, reservation, **kwargs):
        # post()の冒頭で予約済みのConciergeChatLog行へ結果を書き戻す(新規作成はしない)。
        # legacy/agent両経路が同じDailyRunUsageService.finalizeを経由することで、
        # ログ保存ロジックが分岐して不整合を起こすリスクを無くす。
        try:
            DailyRunUsageService.finalize(reservation, **kwargs)
        except Exception:
            logger.exception("Failed to save concierge chat log for itinerary_id=%s", self.itinerary.pk)

    def _release_reservation_safely(self, reservation):
        # 外部API呼び出し失敗時に予約を取り消し、日次上限を消費しない（失敗は不課金の仕様）。
        try:
            DailyRunUsageService.release(reservation)
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

    data, error_response = parse_json_object_body(request)
    if error_response is not None:
        return error_response

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
                result = edit_actions_service.apply_edit_action(itinerary, raw_action, touched_schedule_days)
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


@require_POST
@ratelimit(key=ratelimit_client_ip, rate='30/m', block=True)
def concierge_v2_link_previews(request, pk, token):
    itinerary = get_itinerary_or_404(pk, token)

    view_gate_response = require_view_access_json(request, itinerary)
    if view_gate_response is not None:
        return view_gate_response

    data, error_response = parse_json_object_body(request)
    if error_response is not None:
        return error_response

    raw_urls = data.get("urls")
    if not isinstance(raw_urls, list):
        return JsonResponse({"status": "error", "message": "urlsが不正です。"}, status=400)

    seen = set()
    urls = []
    for raw_url in raw_urls:
        url = str(raw_url or "").strip()
        if not url or url in seen:
            continue
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme not in ("http", "https") or not parsed.hostname:
            continue
        seen.add(url)
        urls.append(url)
        if len(urls) >= MAX_LINK_PREVIEW_URLS_PER_REQUEST:
            break

    previews = [get_link_preview(url) for url in urls]
    return JsonResponse({"status": "ok", "previews": previews})

