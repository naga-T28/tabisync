import json
from datetime import datetime, timedelta

from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.http import require_POST
from django_ratelimit.decorators import ratelimit

from ..models import ScheduleV2, WantToGo
from .access_control import EditPasswordRequiredMixin, get_itinerary_or_404, require_edit_access_json
from .itinerary_helpers import (
    build_day_choices,
    count_schedules_for_day,
    get_schedule_day_index,
    get_schedule_display_date,
    lock_itinerary_for_update,
    reorder_schedules_for_day,
)
from .utils import MAX_SCHEDULES_PER_DAY, ratelimit_client_ip


# スケジュール本体の編集画面
@method_decorator(ratelimit(key=ratelimit_client_ip, rate='20/m', block=True), name='dispatch')
class ScheduleV2EditView(EditPasswordRequiredMixin, View):
    template_name = "tabisync/content/schedule_edit.html"
    edit_redirect_url_name = "Scheduleedit"

    def get(self, request, pk, token, *args, **kwargs):
        itinerary = self.itinerary
        schedules = list(itinerary.schedules.select_related("place").all().order_by("day_index", "start_time", "order", "id"))
        day_choices = build_day_choices(itinerary)

        grouped_days = []
        for choice in day_choices:
            day_num = choice.get("day_num")
            day_schedules = [s for s in schedules if get_schedule_day_index(itinerary, s) == day_num]

            grouped_days.append({
                "choice": choice,
                "schedules": day_schedules,
            })

        want_to_go_places = itinerary.want_to_go_list.all().order_by("planned_day", "id")
        first_date_str = None
        last_date_str = None
        if itinerary.start_date and itinerary.end_date:
            first_date_str = itinerary.start_date.strftime("%Y.%m.%d")
            last_date_str = itinerary.end_date.strftime("%Y.%m.%d")

        return render(request, self.template_name, {
            "itinerary": itinerary,
            "grouped_days": grouped_days,
            "day_choices": day_choices,
            "want_to_go_places": want_to_go_places,
            "first_date_str": first_date_str,
            "last_date_str": last_date_str,
        })



# ScheduleV2 の行を追加・更新する API
@require_POST
def schedule_v2_row_save(request, pk, token):
    itinerary = get_itinerary_or_404(pk, token)

    gate_response = require_edit_access_json(request, itinerary)
    if gate_response is not None:
        return gate_response

    try:
        data = json.loads(request.body.decode("utf-8"))
    except Exception:
        return JsonResponse({"status": "error", "message": "不正なJSONです"}, status=400)

    row_id = data.get("id")
    title = (data.get("title") or "").strip()[:30]
    description = (data.get("description") or "").strip()[:100]
    start_time_str = (data.get("start_time") or "").strip()
    end_time_str = (data.get("end_time") or "").strip()
    date_str = (data.get("date") or "").strip()
    place_id = data.get("place_id")
    icon = (data.get("icon") or ScheduleV2.ICON_DEFAULT).strip()
    allowed_icons = {choice[0] for choice in ScheduleV2.ICON_CHOICES}
    if icon not in allowed_icons:
        icon = ScheduleV2.ICON_DEFAULT

    if not title or not start_time_str or not date_str:
        return JsonResponse({"status": "error", "message": "必須項目が不足しています"}, status=400)

    try:
        start_time = datetime.strptime(start_time_str, "%H:%M").time()
        end_time = datetime.strptime(end_time_str, "%H:%M").time() if end_time_str else None
    except ValueError:
        return JsonResponse({"status": "error", "message": "時刻の形式が不正です"}, status=400)

    day_index = None
    if date_str.startswith("day-"):
        try:
            day_index = int(date_str.replace("day-", ""))
        except ValueError:
            return JsonResponse({"status": "error", "message": "Day指定が不正です"}, status=400)
    elif "-" in date_str:
        try:
            legacy_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            return JsonResponse({"status": "error", "message": "日付形式が不正です"}, status=400)

        if itinerary.start_date:
            day_index = (legacy_date - itinerary.start_date).days + 1
    else:
        return JsonResponse({"status": "error", "message": "日付の形式が不正です"}, status=400)

    if not day_index or not itinerary.total_days or day_index < 1 or day_index > itinerary.total_days:
        return JsonResponse({"status": "error", "message": "存在しないDayです"}, status=400)

    exclude_schedule_id = None
    if row_id:
        try:
            exclude_schedule_id = int(row_id)
        except (TypeError, ValueError):
            return JsonResponse({"status": "error", "message": "予定IDが不正です"}, status=400)

    # 件数チェックと作成/更新を同一トランザクション・行ロック内で行い、
    # 同時リクエストによる1日あたり上限超過（TOCTOU競合）を防ぐ。
    with transaction.atomic():
        itinerary = lock_itinerary_for_update(itinerary)

        if count_schedules_for_day(itinerary, day_index, exclude_schedule_id) >= MAX_SCHEDULES_PER_DAY:
            return JsonResponse({
                "status": "error",
                "message": f"予定は1日につき{MAX_SCHEDULES_PER_DAY}件まで保存できます。",
            }, status=400)

        date_obj = get_schedule_display_date(itinerary, day_index)
        if not date_obj:
            date_obj = itinerary.created_at.date() + timedelta(days=day_index - 1)

        place_obj = None
        if place_id:
            place_obj = WantToGo.objects.filter(pk=place_id, itinerary=itinerary).first()

        if row_id:
            schedule = get_object_or_404(ScheduleV2, pk=row_id, itinerary=itinerary)
            old_day_index = get_schedule_day_index(itinerary, schedule)

            schedule.date = date_obj
            schedule.day_index = day_index
            schedule.title = title
            schedule.icon = icon
            schedule.description = description
            schedule.start_time = start_time
            schedule.end_time = end_time
            schedule.place = place_obj
            schedule.save()
            created = False
        else:
            schedule = ScheduleV2.objects.create(
                itinerary=itinerary,
                date=date_obj,
                day_index=day_index,
                title=title,
                icon=icon,
                description=description,
                start_time=start_time,
                end_time=end_time,
                place=place_obj,
                order=0,
            )
            old_day_index = None
            created = True

        # 並び順再計算
        reorder_schedules_for_day(itinerary, schedule.day_index)

        # もとの日付グループから移動した場合は旧グループも再計算
        if old_day_index is not None and old_day_index != schedule.day_index:
            reorder_schedules_for_day(itinerary, old_day_index)

        return JsonResponse({
            "status": "saved",
            "created": created,
            "id": schedule.id,
            "title": schedule.title,
            "icon": schedule.icon,
            "icon_class": schedule.get_icon_class(),
            "title_color_class": schedule.get_title_color_class(),
            "description": schedule.description,
            "start_time": schedule.start_time.strftime("%H:%M"),
            "end_time": schedule.end_time.strftime("%H:%M") if schedule.end_time else "",
            "date": f"day-{schedule.day_index}",
            "place_id": schedule.place.id if schedule.place else "",
            "place_name": schedule.place.name if schedule.place else "",
            "day_index": schedule.day_index,
        })



# ScheduleV2 の行を削除する API
@require_POST
def schedule_v2_row_delete(request, pk, token):
    itinerary = get_itinerary_or_404(pk, token)

    gate_response = require_edit_access_json(request, itinerary)
    if gate_response is not None:
        return gate_response

    try:
        data = json.loads(request.body.decode("utf-8"))
    except Exception:
        return JsonResponse({"status": "error", "message": "不正なJSONです"}, status=400)

    row_id = data.get("id")
    if not row_id:
        return JsonResponse({"status": "error", "message": "idがありません"}, status=400)

    schedule = get_object_or_404(ScheduleV2, pk=row_id, itinerary=itinerary)
    target_day_index = get_schedule_day_index(itinerary, schedule)
    schedule.delete()

    if target_day_index is None:
        return JsonResponse({"status": "deleted"})

    reorder_schedules_for_day(itinerary, target_day_index)

    return JsonResponse({"status": "deleted"})

