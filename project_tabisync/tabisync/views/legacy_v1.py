from datetime import datetime

from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.generic import TemplateView
from django_ratelimit.decorators import ratelimit

from ..models import Item, Memo, Schedule, TravelDate
from .access_control import (
    ViewPasswordRequiredMixin,
    add_noindex_header,
    get_itinerary_or_404,
    handle_edit_password_gate,
)
from .utils import (
    MAX_CHECKLISTS_PER_ITINERARY,
    MAX_ITINERARY_DAYS,
    MAX_MEMO_WORDS,
    MAX_MEMOS_PER_ITINERARY,
    MAX_SCHEDULES_PER_DAY,
    count_memo_words,
    ratelimit_client_ip,
    verify_turnstile,
)


# =========================
# ver.1 閲覧ページ
# =========================
# memoページ
@method_decorator(ratelimit(key=ratelimit_client_ip, rate='20/m', block=True), name='dispatch')
class MemoDetailView(ViewPasswordRequiredMixin, TemplateView):
    template_name = "tabisync/memo.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        itinerary = self.itinerary

        travel_dates = itinerary.travel_dates.all().order_by('date')

        # タイトル・内容が両方空でないメモのみ表示
        memos = [
            memo for memo in itinerary.memos.all()
            if memo.title.strip() or memo.content.strip()
        ]
        context.update(get_travel_date_range_context(travel_dates))
        context.update({
            "memos": memos,
            "has_memos": len(memos) > 0,
            "itinerary": itinerary,
            "travel_dates": travel_dates,
            "items": itinerary.items.all(),
        })

        return context



# listページ
@method_decorator(ratelimit(key=ratelimit_client_ip, rate='20/m', block=True), name='dispatch')
class ListDetailView(ViewPasswordRequiredMixin, TemplateView):
    template_name = "tabisync/list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        itinerary = self.itinerary

        travel_dates = itinerary.travel_dates.all().order_by('date')

        context["itinerary"] = itinerary
        context["travel_dates"] = travel_dates
        context["memos"] = itinerary.memos.all()
        
        items = itinerary.items.all()
        context.update(get_travel_date_range_context(travel_dates))
        context["items"] = items

        # 全てのアイテムの title と detail が空かをチェック
        context["all_items_empty"] = all(
            not item.title and not item.detail for item in items
        )

        return context



# =========================
# ver.1 編集・パスワード再設定
# =========================
# 編集画面
# 注: V1のみ、認可チェックより前にverify_turnstile()を要求する既存仕様があるため、
# EditPasswordRequiredMixinは使わずhandle_edit_password_gateを直接呼び出して合成する。
@method_decorator(ratelimit(key=ratelimit_client_ip, rate='20/m', block=True), name='dispatch')
class EditView(View):
    template_name = "tabisync/edit.html"

    def dispatch(self, request, *args, **kwargs):
        self.itinerary = get_itinerary_or_404(kwargs.get("pk"), kwargs.get("token"))
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, pk, token, *args, **kwargs):
        gate_response = handle_edit_password_gate(request, self.itinerary, "content_edit_v2")
        if gate_response is not None:
            return gate_response

        return add_noindex_header(render(request, self.template_name, {"itinerary": self.itinerary}))

    def post(self, request, pk, token, *args, **kwargs):
        if not verify_turnstile(request):
            return render(request, self.template_name, {'error': 'セキュリティチェックに失敗しました。もう一度お試しください。'})

        gate_response = handle_edit_password_gate(request, self.itinerary, "content_edit_v2")
        if gate_response is not None:
            return gate_response

        itinerary = self.itinerary

        # ------------------------
        # 基本情報更新
        # ------------------------
        itinerary.title = request.POST.get("title", "")
        itinerary.subtitle = request.POST.get("subtitle", "")
        itinerary.description = request.POST.get("description", "")
        itinerary.save()

        # ------------------------
        # TravelDate & Schedule 差分更新
        # ------------------------
        existing_dates = list(itinerary.travel_dates.all())

        travel_date_indices = sorted({
            key.split("[")[1].split("]")[0]
            for key in request.POST.keys()
            if key.startswith("dates[") and "[date]" in key
        }, key=int)

        if len(travel_date_indices) > MAX_ITINERARY_DAYS:
            return render(request, self.template_name, {
                "itinerary": itinerary,
                "error": f"日程は最大{MAX_ITINERARY_DAYS}日間まで登録できます。",
            }, status=400)

        for i_str in travel_date_indices:
            i = int(i_str)
            schedule_indices = sorted({
                key.split("[")[3].split("]")[0]
                for key in request.POST.keys()
                if key.startswith(f"dates[{i}][schedules][") and "[title]" in key
            }, key=int)

            if len(schedule_indices) > MAX_SCHEDULES_PER_DAY:
                return render(request, self.template_name, {
                    "itinerary": itinerary,
                    "error": f"予定は1日につき{MAX_SCHEDULES_PER_DAY}件まで保存できます。",
                }, status=400)

        used_date_pks = []

        for idx, i_str in enumerate(travel_date_indices):
            i = int(i_str)
            date_str = request.POST.get(f"dates[{i}][date]")
            if not date_str:
                continue

            if idx < len(existing_dates):
                td = existing_dates[idx]
                td.date = date_str
                td.order = idx
                td.save()
            else:
                td = TravelDate.objects.create(
                    itinerary=itinerary,
                    date=date_str,
                    order=idx
                )
            used_date_pks.append(td.pk)

            # Schedule 差分更新
            existing_schedules = list(td.schedules.all())
            schedule_indices = sorted({
                key.split("[")[3].split("]")[0]
                for key in request.POST.keys()
                if key.startswith(f"dates[{i}][schedules][") and "[title]" in key
            }, key=int)

            used_schedule_pks = []

            for jdx, j_str in enumerate(schedule_indices):
                j = int(j_str)
                title = request.POST.get(f"dates[{i}][schedules][{j}][title]", "")
                location = request.POST.get(f"dates[{i}][schedules][{j}][location]", "")
                location_url = request.POST.get(f"dates[{i}][schedules][{j}][location_url]", "")
                description = request.POST.get(f"dates[{i}][schedules][{j}][description]", "")
                start_time = request.POST.get(f"dates[{i}][schedules][{j}][start_time]")
                end_time = request.POST.get(f"dates[{i}][schedules][{j}][end_time]") or None

                if start_time:
                    start_time = datetime.strptime(start_time, "%H:%M").time()
                if end_time:
                    end_time = datetime.strptime(end_time, "%H:%M").time()

                if jdx < len(existing_schedules):
                    sched = existing_schedules[jdx]
                    sched.title = title
                    sched.location = location
                    sched.location_url = location_url
                    sched.description = description
                    sched.start_time = start_time
                    sched.end_time = end_time
                    sched.order = jdx
                    sched.save()
                    used_schedule_pks.append(sched.pk)
                else:
                    sched = Schedule.objects.create(
                        travel_date=td,
                        title=title,
                        location=location,
                        location_url=location_url,
                        description=description,
                        start_time=start_time,
                        end_time=end_time,
                        order=jdx
                    )
                    used_schedule_pks.append(sched.pk)

            # 余ったSchedule削除
            for s in existing_schedules:
                if s.pk not in used_schedule_pks:
                    s.delete()

        # 余ったTravelDate削除
        for td in existing_dates:
            if td.pk not in used_date_pks:
                td.delete()

        # ------------------------
        # Memo 差分更新
        # ------------------------
        existing_memos = list(itinerary.memos.all())
        memo_indices = sorted({
            key.split("[")[1].split("]")[0]
            for key in request.POST.keys()
            if key.startswith("memos[") and "[title]" in key
        }, key=int)

        if len(memo_indices) > MAX_MEMOS_PER_ITINERARY:
            return render(request, self.template_name, {
                "itinerary": itinerary,
                "error": f"メモは最大{MAX_MEMOS_PER_ITINERARY}件まで保存できます。",
            }, status=400)

        for i_str in memo_indices:
            i = int(i_str)
            content = request.POST.get(f"memos[{i}][content]", "")
            if count_memo_words(content) > MAX_MEMO_WORDS:
                return render(request, self.template_name, {
                    "itinerary": itinerary,
                    "error": f"メモは1件につき{MAX_MEMO_WORDS}語まで保存できます。",
                }, status=400)

        used_memo_pks = []

        for idx, i_str in enumerate(memo_indices):
            i = int(i_str)
            title = request.POST.get(f"memos[{i}][title]", "")
            content = request.POST.get(f"memos[{i}][content]", "")

            if idx < len(existing_memos):
                memo = existing_memos[idx]
                memo.title = title
                memo.content = content
                memo.save()
                used_memo_pks.append(memo.pk)
            else:
                memo = Memo.objects.create(
                    itinerary=itinerary,
                    title=title,
                    content=content
                )
                used_memo_pks.append(memo.pk)

        for m in existing_memos:
            if m.pk not in used_memo_pks:
                m.delete()

        # ------------------------
        # Item 差分更新
        # ------------------------
        existing_items = list(itinerary.items.all())
        item_indices = sorted({
            key.split("[")[1].split("]")[0]
            for key in request.POST.keys()
            if key.startswith("items[") and "[title]" in key
        }, key=int)

        if len(item_indices) > MAX_CHECKLISTS_PER_ITINERARY:
            return render(request, self.template_name, {
                "itinerary": itinerary,
                "error": f"リストは最大{MAX_CHECKLISTS_PER_ITINERARY}リストまで保存できます。",
            }, status=400)

        used_item_pks = []

        for idx, i_str in enumerate(item_indices):
            i = int(i_str)
            title = request.POST.get(f"items[{i}][title]", "")
            detail = request.POST.get(f"items[{i}][detail]", "")
            is_checked = request.POST.get(f"items[{i}][is_checked]") == "true"

            if idx < len(existing_items):
                item = existing_items[idx]
                item.title = title
                item.detail = detail
                item.is_checked = is_checked
                item.save()
                used_item_pks.append(item.pk)
            else:
                item = Item.objects.create(
                    itinerary=itinerary,
                    title=title,
                    detail=detail,
                    is_checked=is_checked
                )
                used_item_pks.append(item.pk)

        for item in existing_items:
            if item.pk not in used_item_pks:
                item.delete()

        return redirect(reverse("tabisync:content", kwargs={"pk": itinerary.pk, "token": itinerary.token}))



# =========================
# ver.1 表示用ヘルパー
# =========================
def get_travel_date_range_context(travel_dates):
    # テンプレート表示用に、旅程の開始日・終了日を同じ形式でまとめる
    if not travel_dates.exists():
        return {
            "first_date_str": None,
            "last_date_str": None,
        }

    first_date = travel_dates.first().date
    last_date = travel_dates.last().date
    return {
        "first_date_str": first_date.strftime('%Y.%m.%d'),
        "last_date_str": last_date.strftime('%Y.%m.%d'),
    }



def prepare_travel_dates_with_schedules(itinerary):
    # TravelDate ごとに開始時刻順の予定を付与する
    travel_dates = itinerary.travel_dates.all().order_by('date')

    for travel_date in travel_dates:
        travel_date.sorted_schedules = travel_date.schedules.all().order_by('start_time')

    return travel_dates



# ver.1 の個別ページ
@method_decorator(ratelimit(key=ratelimit_client_ip, rate='20/m', block=True), name='dispatch')
class ItineraryDetailView(ViewPasswordRequiredMixin, TemplateView):
    template_name = "tabisync/content.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        itinerary = self.itinerary
        travel_dates = prepare_travel_dates_with_schedules(itinerary)

        context.update(get_travel_date_range_context(travel_dates))
        context.update({
            "itinerary": itinerary,
            "travel_dates": travel_dates,
            "memos": itinerary.memos.all(),
            "items": itinerary.items.all(),
        })

        return context

