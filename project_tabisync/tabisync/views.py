from django.shortcuts import render, redirect, get_object_or_404
from django.utils.decorators import method_decorator
from django_ratelimit.decorators import ratelimit
from django.urls import reverse
from django.views.generic import TemplateView #add_2025.06.07
from django.views import View
from .models import Itinerary, TravelDate, Schedule, Memo, Item,MemoV2,ScheduleV2,WantToGo
from django.db import transaction
from collections import defaultdict
from django.core.mail import send_mail
from .forms import ContactForm
import urllib.request
import urllib.parse
import json
import os
from django.conf import settings
from django.http import HttpResponse
from django.views.decorators.http import require_POST
# views.py
from django.core import signing
from django.core.mail import send_mail
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.contrib import messages
from .models import Itinerary  # あなたのモデルに合わせてインポート
from django.views import View
from django.core import signing
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import Http404
from .models import Itinerary
from .models import WantToGo
from django.contrib.auth.hashers import make_password
from django.shortcuts import render
from django.http import JsonResponse
from django.db.models import Case, When, Value, IntegerField
from .forms import MemoV2Form
from datetime import datetime, timedelta


def offline_view(request):
    return render(request, "offline.html")

#クローラ対策
def robots_txt_view(request):
    lines = [
        "User-agent: *",
        "Disallow: /content/",
        "Disallow: /reset-link/",
        "Disallow: /reset/",
    ]
    return HttpResponse("\n".join(lines), content_type="text/plain")


def verify_turnstile(request):
    secret_key = os.environ.get('CLOUDFLARE_TURNSTILE_SECRET_KEY')
    token = request.POST.get('cf-turnstile-response')
    remoteip = request.META.get('REMOTE_ADDR')

    if not token:
        return False

    data = urllib.parse.urlencode({
        'secret': secret_key,
        'response': token,
        'remoteip': remoteip,
    }).encode()

    req = urllib.request.Request(
        url='https://challenges.cloudflare.com/turnstile/v0/siteverify',
        data=data,
        method='POST'
    )
    req.add_header("Content-type", "application/x-www-form-urlencoded")

    try:
        with urllib.request.urlopen(req) as resp:
            response_data = json.loads(resp.read().decode())
            return response_data.get('success', False)
    except Exception as e:
        print("Turnstile verify error:", e)
        return False

# utils.py（または views.py の冒頭でも可）


# ホーム画面を表示するビュー
class HomeView(TemplateView):
    template_name = "home.html"
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context  
# ホーム画面を表示するビュー
class ProfileView(TemplateView):
    template_name = "docs/profile.html"
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context  
# 利用規約
class UserAgreementView(TemplateView):
    template_name = "docs/user_agreement.html"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context
# Q and Aを表示するビュー
class QAView(TemplateView):
    template_name = "docs/qanda.html"
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context  
# プライバシーポリシー
class PrivacyPolicyView(TemplateView):
    template_name = "docs/privacy_policy.html"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context
    
class UpdatesView(TemplateView):
    template_name = "docs/update.html"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context

class DemoContentView(TemplateView):
    template_name = "demo/content_demo.html"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context
class DemoMemoView(TemplateView):
    template_name = "demo/memo_demo.html"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context
    
class DemoEditView(TemplateView):
    template_name = "demo/edit_demo.html"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context
class DemoListView(TemplateView):
    template_name = "demo/list_demo.html"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context


#しおり作成画面
@method_decorator(ratelimit(key='ip', rate='20/m', block=True), name='dispatch')
class CreateView(View):
    template_name = "tabisync/create.html"

    def get(self, request, *args, **kwargs):
        return render(request, self.template_name)

    def post(self, request, *args, **kwargs):

        #if not verify_turnstile(request):
        #    return render(request, self.template_name, {
        #        'error': 'セキュリティチェックに失敗しました。もう一度お試しください。'
        #    })

        # =====================
        # 日程関連データ取得
        # =====================
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')
        total_days = request.POST.get('total_days')
        design_number = request.POST.get('design_number', 1)

        # 文字列 → date型へ変換
        start_date_obj = None
        end_date_obj = None

        if start_date:
            start_date_obj = datetime.strptime(start_date, "%Y-%m-%d").date()

        if end_date:
            end_date_obj = datetime.strptime(end_date, "%Y-%m-%d").date()

        # =====================
        # しおり作成
        # =====================
        itinerary = Itinerary(
            title=request.POST.get('title'),
            subtitle=request.POST.get('subtitle'),
            description=request.POST.get('description'),
            reset_email=request.POST.get('reset_email', ''),
            start_date=start_date_obj,
            end_date=end_date_obj,
            design_number=int(design_number)
        )

        # 日程未定モードなら total_days をセット
        if not start_date_obj and total_days:
            itinerary.total_days = int(total_days)

        itinerary.set_passwords(
            view_pw=request.POST.get('view_password', ''),
            edit_pw=request.POST.get('edit_password', '')
        )

        itinerary.save()

        return redirect(reverse('tabisync:content_v2', kwargs={
            'pk': itinerary.pk,
            'token': itinerary.token
        }))

#個別ページ
@method_decorator(ratelimit(key='ip', rate='20/m', block=True), name='dispatch')
class ItineraryDetailV2View(TemplateView):
    template_name = "tabisync/content/content.html"

    def _get_itinerary(self, pk, token):
        return get_object_or_404(Itinerary, pk=pk, token=token)

    def get(self, request, pk, token, *args, **kwargs):
        itinerary = self._get_itinerary(pk, token)

        if itinerary.view_password and not request.session.get(f'view_auth_{pk}_{token}', False):
            response = redirect(reverse('tabisync:content_password', kwargs={'pk': pk, 'token': token}))
            response["X-Robots-Tag"] = "noindex, nofollow"
            return response

        schedules = list(itinerary.schedules.select_related("place").all().order_by(
            "day_index", "start_time", "order", "id"
        ))
        day_choices = build_day_choices(itinerary)

        grouped_days = []
        for choice in day_choices:
            day_num = choice.get("day_num")
            day_schedules = [s for s in schedules if get_schedule_day_index(itinerary, s) == day_num]

            grouped_days.append({
                "choice": choice,
                "schedules": day_schedules,
            })

        first_date_str = None
        last_date_str = None
        if itinerary.start_date and itinerary.end_date:
            first_date_str = itinerary.start_date.strftime("%Y.%m.%d")
            last_date_str = itinerary.end_date.strftime("%Y.%m.%d")

        response = render(request, self.template_name, {
            "itinerary": itinerary,
            "grouped_days": grouped_days,
            "day_choices": day_choices,
            "first_date_str": first_date_str,
            "last_date_str": last_date_str,
        })
        response["X-Robots-Tag"] = "noindex, nofollow"
        return response

#行きたい場所リスト表示
@method_decorator(ratelimit(key='ip', rate='20/m', block=True), name='dispatch')
class WantToGoMapView(TemplateView):
    template_name = "tabisync/content/want_list.html"

    def dispatch(self, request, *args, **kwargs):
        pk = self.kwargs.get("pk")
        token = self.kwargs.get("token")
        self.itinerary = get_object_or_404(Itinerary, pk=pk, token=token)

        if self.itinerary.view_password and not request.session.get(f'view_auth_{pk}_{token}', False):
            return redirect(reverse('tabisync:content_password', kwargs={'pk': pk, 'token': token}))

        response = super().dispatch(request, *args, **kwargs)
        response["X-Robots-Tag"] = "noindex, nofollow"
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        pk = self.kwargs.get("pk")
        token = self.kwargs.get("token")

        itinerary = get_object_or_404(Itinerary, pk=pk, token=token)

        context["itinerary"] = itinerary
        
        context["places"] = WantToGo.objects.filter(
            itinerary=itinerary
            ).annotate(day_order=Case(
                When(planned_day=0, then=Value(999)),
                default="planned_day",
                output_field=IntegerField(),
            )
        ).order_by("day_order", "id")

        context["itinerary_days"] = list(range(1, itinerary.total_days + 1))

        return context
    
    def post(self, request, *args, **kwargs):
        pk = self.kwargs.get("pk")
        token = self.kwargs.get("token")

        data = json.loads(request.body)
        action = data.get("action")

        itinerary = get_object_or_404(Itinerary, pk=pk, token=token)

        if action == "save_want_to_go":
            place = WantToGo.objects.create(
                itinerary=itinerary,
                place_id=data.get("place_id"),
                name=data.get("name"),
                address=data.get("address"),
                latitude=data.get("lat"),
                longitude=data.get("lng"),
                rating=data.get("rating"),
                memo=data.get("memo", ""),
                planned_day=int(data.get("day", 0)),
                stay_minutes=data.get("stay_minutes") or None,
                priority=data.get("priority", 3),
                tag=data.get("tag", ""),
            )
            return JsonResponse({
                "status": "saved",
                "id": place.id,
                "name": place.name,
                "address": place.address,
            })

        if action == "update_want_to_go":
            place = get_object_or_404(WantToGo, pk=data.get("id"), itinerary=itinerary)

            # 基本情報も更新（Google候補で選び直した場合にも対応）
            place.place_id = data.get("place_id") or place.place_id
            place.name = data.get("name", place.name)
            place.address = data.get("address", place.address)
            place.latitude = data.get("lat", place.latitude)
            place.longitude = data.get("lng", place.longitude)
            place.rating = data.get("rating", place.rating)

            # ユーザー入力
            place.memo = data.get("memo", place.memo)
            place.planned_day = int(data.get("day", place.planned_day or 0))

            place.stay_minutes = data.get("stay_minutes") or place.stay_minutes
            place.priority = data.get("priority", place.priority)
            place.tag = data.get("tag", place.tag)

            place.save()
            return JsonResponse({
                    "status": "updated",
                    "id": place.id,
                    "name": place.name,
                    "address": place.address,
                })

        if action == "delete_want_to_go":
            place = get_object_or_404(WantToGo, pk=data.get("id"), itinerary=itinerary)
            place.delete()
            return JsonResponse({"status": "deleted"})

        return JsonResponse({"status": "error"})

#行きたいとこリスト編集
@method_decorator(ratelimit(key='ip', rate='20/m', block=True), name='dispatch')
class WantToGoV2View(TemplateView):

    template_name = "tabisync/content/want_list_edit.html"

    def dispatch(self, request, *args, **kwargs):
        pk = self.kwargs.get("pk")
        token = self.kwargs.get("token")
        self.itinerary = get_object_or_404(Itinerary, pk=pk, token=token)

        if self.itinerary.view_password and not request.session.get(f'view_auth_{pk}_{token}', False):
            return redirect(reverse('tabisync:content_password', kwargs={'pk': pk, 'token': token}))

        response = super().dispatch(request, *args, **kwargs)
        response["X-Robots-Tag"] = "noindex, nofollow"
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        pk = self.kwargs.get("pk")
        token = self.kwargs.get("token")

        itinerary = get_object_or_404(
            Itinerary,
            pk=pk,
            token=token,
        )

        context["itinerary"] = itinerary
        context["places"] = WantToGo.objects.filter(itinerary=itinerary)
        context["itinerary_days"] = list(range(1, itinerary.total_days + 1))

        return context


    def post(self, request, *args, **kwargs):
        pk = self.kwargs.get("pk")
        token = self.kwargs.get("token")

        data = json.loads(request.body)
        action = data.get("action")

        itinerary = get_object_or_404(Itinerary, pk=pk, token=token)

        if action == "save_want_to_go":
            place = WantToGo.objects.create(
                itinerary=itinerary,
                place_id=data.get("place_id"),
                name=data.get("name"),
                address=data.get("address"),
                latitude=data.get("lat"),
                longitude=data.get("lng"),
                rating=data.get("rating"),
                memo=data.get("memo", ""),
                planned_day=int(data.get("day", 0)),
                stay_minutes=data.get("stay_minutes") or None,
                priority=data.get("priority", 3),
                tag=data.get("tag", ""),
            )
            return JsonResponse({
                "status": "saved",
                "id": place.id,
                "name": place.name,
                "address": place.address,
            })

        if action == "update_want_to_go":
            place = get_object_or_404(WantToGo, pk=data.get("id"), itinerary=itinerary)

            # 基本情報も更新（Google候補で選び直した場合にも対応）
            place.place_id = data.get("place_id") or place.place_id
            place.name = data.get("name", place.name)
            place.address = data.get("address", place.address)
            place.latitude = data.get("lat", place.latitude)
            place.longitude = data.get("lng", place.longitude)
            place.rating = data.get("rating", place.rating)

            # ユーザー入力
            place.memo = data.get("memo", place.memo)
            place.planned_day = int(data.get("day", place.planned_day or 0))

            place.stay_minutes = data.get("stay_minutes") or place.stay_minutes
            place.priority = data.get("priority", place.priority)
            place.tag = data.get("tag", place.tag)

            place.save()
            return JsonResponse({
                    "status": "updated",
                    "id": place.id,
                    "name": place.name,
                    "address": place.address,
                })

        if action == "delete_want_to_go":
            place = get_object_or_404(WantToGo, pk=data.get("id"), itinerary=itinerary)
            place.delete()
            return JsonResponse({"status": "deleted"})

        return JsonResponse({"status": "error"})

#version2のしおり内容編集
# version2のしおり内容編集
def get_schedule_day_index(itinerary, schedule):
    if schedule.day_index:
        return schedule.day_index

    if itinerary.start_date and schedule.date:
        return (schedule.date - itinerary.start_date).days + 1

    return None


def get_schedule_display_date(itinerary, day_index):
    if itinerary.start_date and day_index:
        return itinerary.start_date + timedelta(days=day_index - 1)
    return None


def reorder_schedules_for_day(itinerary, day_index):
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


def build_day_choices(itinerary):
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


@method_decorator(ratelimit(key='ip', rate='20/m', block=True), name='dispatch')
class EditContentV2View(View):
    template_name = "tabisync/content/edit_content.html"
    password_template = "tabisync/edit_password.html"

    def _get_itinerary(self, pk, token):
        return get_object_or_404(Itinerary, pk=pk, token=token)

    def _render_password(self, request, itinerary, pk, token):
        response = render(request, self.password_template, {
            "itinerary": itinerary,
            "pk": pk,
            "token": token,
        })
        response["X-Robots-Tag"] = "noindex, nofollow"
        return response

    def _render_form(self, request, itinerary, extra_context=None, status=200):
        context = {
            "itinerary": itinerary,
            "is_undecided": bool(itinerary.total_days and not itinerary.start_date and not itinerary.end_date),
        }
        if extra_context:
            context.update(extra_context)
        response = render(request, self.template_name, context, status=status)
        response["X-Robots-Tag"] = "noindex, nofollow"
        return response

    def get(self, request, pk, token, *args, **kwargs):
        itinerary = self._get_itinerary(pk, token)
        session_key = f"edit_auth_{itinerary.pk}"

        if itinerary.edit_password and not request.session.get(session_key):
            return self._render_password(request, itinerary, pk, token)

        return self._render_form(request, itinerary)

    def post(self, request, pk, token, *args, **kwargs):
        itinerary = self._get_itinerary(pk, token)
        session_key = f"edit_auth_{itinerary.pk}"

        if itinerary.edit_password and not request.session.get(session_key):
            password = request.POST.get("password", "")
            if itinerary.check_edit_password(password):
                request.session[session_key] = True
                return redirect(reverse("tabisync:content_edit_v2", kwargs={"pk": pk, "token": token}))
            response = render(request, self.password_template, {
                "error": "パスワードが間違っています。",
                "itinerary": itinerary,
                "pk": pk,
                "token": token,
            })
            response["X-Robots-Tag"] = "noindex, nofollow"
            return response

        title = (request.POST.get("title") or "").strip()
        subtitle = (request.POST.get("subtitle") or "").strip()
        description = (request.POST.get("description") or "").strip()
        start_date_str = (request.POST.get("start_date") or "").strip()
        end_date_str = (request.POST.get("end_date") or "").strip()
        total_days_str = (request.POST.get("total_days") or "").strip()
        is_undecided = request.POST.get("is_undecided") == "1"

        if not title:
            itinerary.title = title
            itinerary.subtitle = subtitle
            itinerary.description = description
            return self._render_form(
                request,
                itinerary,
                {"error": "タイトルを入力してください。", "is_undecided": is_undecided},
                status=400,
            )

        new_start_date = None
        new_end_date = None
        new_total_days = None
        old_start_date = itinerary.start_date

        if is_undecided:
            try:
                new_total_days = int(total_days_str)
            except (TypeError, ValueError):
                new_total_days = 0

            if new_total_days < 1:
                itinerary.title = title
                itinerary.subtitle = subtitle
                itinerary.description = description
                itinerary.total_days = new_total_days or None
                itinerary.start_date = None
                itinerary.end_date = None
                return self._render_form(
                    request,
                    itinerary,
                    {"error": "旅行日数は1日以上で入力してください。", "is_undecided": True},
                    status=400,
                )
        else:
            if not start_date_str or not end_date_str:
                itinerary.title = title
                itinerary.subtitle = subtitle
                itinerary.description = description
                itinerary.start_date = start_date_str or None
                itinerary.end_date = end_date_str or None
                itinerary.total_days = None
                return self._render_form(
                    request,
                    itinerary,
                    {"error": "開始日と終了日を入力してください。", "is_undecided": False},
                    status=400,
                )

            try:
                new_start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
                new_end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
            except ValueError:
                itinerary.title = title
                itinerary.subtitle = subtitle
                itinerary.description = description
                itinerary.start_date = start_date_str or None
                itinerary.end_date = end_date_str or None
                itinerary.total_days = None
                return self._render_form(
                    request,
                    itinerary,
                    {"error": "日付の形式が正しくありません。", "is_undecided": False},
                    status=400,
                )

            if new_end_date < new_start_date:
                itinerary.title = title
                itinerary.subtitle = subtitle
                itinerary.description = description
                itinerary.start_date = new_start_date
                itinerary.end_date = new_end_date
                itinerary.total_days = None
                return self._render_form(
                    request,
                    itinerary,
                    {"error": "終了日は開始日以降を指定してください。", "is_undecided": False},
                    status=400,
                )

        schedule_max_day = 0
        for schedule in itinerary.schedules.all():
            day_index = get_schedule_day_index(itinerary, schedule)
            if day_index:
                schedule_max_day = max(schedule_max_day, day_index)

        place_max_day = max(
            itinerary.want_to_go_list.values_list("planned_day", flat=True).filter(planned_day__gt=0),
            default=0,
        )

        existing_max_day = max(schedule_max_day, place_max_day)

        if is_undecided and new_total_days and existing_max_day > new_total_days:
            itinerary.title = title
            itinerary.subtitle = subtitle
            itinerary.description = description
            itinerary.start_date = None
            itinerary.end_date = None
            itinerary.total_days = new_total_days
            return self._render_form(
                request,
                itinerary,
                {
                    "error": f"既存の予定または行きたい場所がDay {existing_max_day}まで入っているため、{new_total_days}日にはできません。",
                    "is_undecided": True,
                },
                status=400,
            )

        if new_start_date and new_end_date:
            new_span_days = (new_end_date - new_start_date).days + 1
            if existing_max_day > new_span_days:
                itinerary.title = title
                itinerary.subtitle = subtitle
                itinerary.description = description
                itinerary.start_date = new_start_date
                itinerary.end_date = new_end_date
                itinerary.total_days = None
                return self._render_form(
                    request,
                    itinerary,
                    {
                        "error": f"既存の予定または行きたい場所がDay {existing_max_day}まで入っているため、この日程には収まりません。",
                        "is_undecided": False,
                    },
                    status=400,
                )

        itinerary.title = title
        itinerary.subtitle = subtitle
        itinerary.description = description
        itinerary.start_date = new_start_date
        itinerary.end_date = new_end_date
        itinerary.total_days = new_total_days
        itinerary.save()

        schedules = itinerary.schedules.all()
        fallback_base_date = itinerary.created_at.date()
        for schedule in schedules:
            day_index = get_schedule_day_index(itinerary, schedule)
            if not day_index:
                continue

            update_fields = []
            if schedule.day_index != day_index:
                schedule.day_index = day_index
                update_fields.append("day_index")

            target_date = get_schedule_display_date(itinerary, day_index)
            if not target_date:
                target_date = fallback_base_date + timedelta(days=day_index - 1)

            if schedule.date != target_date:
                schedule.date = target_date
                update_fields.append("date")

            if update_fields:
                schedule.save(update_fields=update_fields)

        return redirect(reverse("tabisync:content_v2", kwargs={"pk": itinerary.pk, "token": itinerary.token}))

# version2の編集選択画面
@method_decorator(ratelimit(key='ip', rate='20/m', block=True), name='dispatch')
class EditContentV2View(View):
    template_name = "tabisync/content/edit_menu.html"
    password_template = "tabisync/edit_password.html"

    def _get_itinerary(self, pk, token):
        return get_object_or_404(Itinerary, pk=pk, token=token)

    def _render_password(self, request, itinerary, pk, token):
        response = render(request, self.password_template, {
            "itinerary": itinerary,
            "pk": pk,
            "token": token,
        })
        response["X-Robots-Tag"] = "noindex, nofollow"
        return response

    def _render_form(self, request, itinerary, extra_context=None, status=200):
        context = {
            "itinerary": itinerary,
            "is_undecided": bool(itinerary.total_days and not itinerary.start_date and not itinerary.end_date),
        }
        if extra_context:
            context.update(extra_context)
        response = render(request, self.template_name, context, status=status)
        response["X-Robots-Tag"] = "noindex, nofollow"
        return response



@method_decorator(ratelimit(key='ip', rate='20/m', block=True), name='dispatch')
class ScheduleV2EditView(View):
    template_name = "tabisync/content/schedule_edit.html"
    password_template = "tabisync/edit_password.html"

    def _get_itinerary(self, pk, token):
        return get_object_or_404(Itinerary, pk=pk, token=token)

    def get(self, request, pk, token, *args, **kwargs):
        itinerary = self._get_itinerary(pk, token)
        session_key = f"edit_auth_{itinerary.pk}"

        if itinerary.edit_password and not request.session.get(session_key):
            response = render(request, self.password_template, {
                "itinerary": itinerary,
                "pk": pk,
                "token": token,
            })
            response["X-Robots-Tag"] = "noindex, nofollow"
            return response

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

        response = render(request, self.template_name, {
            "itinerary": itinerary,
            "grouped_days": grouped_days,
            "day_choices": day_choices,
            "want_to_go_places": want_to_go_places,
        })
        response["X-Robots-Tag"] = "noindex, nofollow"
        return response


@require_POST
def schedule_v2_row_save(request, pk, token):
    itinerary = get_object_or_404(Itinerary, pk=pk, token=token)

    session_key = f"edit_auth_{itinerary.pk}"
    if itinerary.edit_password and not request.session.get(session_key):
        return JsonResponse({"status": "error", "message": "認証が必要です"}, status=403)

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
        "description": schedule.description,
        "start_time": schedule.start_time.strftime("%H:%M"),
        "end_time": schedule.end_time.strftime("%H:%M") if schedule.end_time else "",
        "date": f"day-{schedule.day_index}",
        "place_id": schedule.place.id if schedule.place else "",
        "place_name": schedule.place.name if schedule.place else "",
        "day_index": schedule.day_index,
    })

@require_POST
def schedule_v2_row_delete(request, pk, token):
    itinerary = get_object_or_404(Itinerary, pk=pk, token=token)

    session_key = f"edit_auth_{itinerary.pk}"
    if itinerary.edit_password and not request.session.get(session_key):
        return JsonResponse({"status": "error", "message": "認証が必要です"}, status=403)

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


#version2のmemoページ
@method_decorator(ratelimit(key='ip', rate='20/m', block=True), name='dispatch')
class MemoV2View(View):
    template_name = "tabisync/content/memo_v2.html"

    def dispatch(self, request, *args, **kwargs):
        self.pk = kwargs.get("pk")
        self.token = kwargs.get("token")
        self.itinerary = get_object_or_404(Itinerary, pk=self.pk, token=self.token)

        if self.itinerary.view_password and not request.session.get(f'view_auth_{self.pk}_{self.token}', False):
            return redirect(reverse('tabisync:content_password', kwargs={'pk': self.pk, 'token': self.token}))

        response = super().dispatch(request, *args, **kwargs)
        response["X-Robots-Tag"] = "noindex, nofollow"
        return response

    def get(self, request, pk, token):
        memo, _ = MemoV2.objects.get_or_create(itinerary=self.itinerary)
        form = MemoV2Form(instance=memo)
        return render(request, self.template_name, {
            "memo": memo,
            "form": form,
            "itinerary": self.itinerary,
        })

    def post(self, request, pk, token):
        memo, _ = MemoV2.objects.get_or_create(itinerary=self.itinerary)
        data = json.loads(request.body)
        memo.content = data.get("content", "")
        memo.save()
        return JsonResponse({"status": "ok"})

#memoページ
@method_decorator(ratelimit(key='ip', rate='20/m', block=True), name='dispatch')
class MemoDetailView(TemplateView):
    template_name = "tabisync/memo.html"

    def dispatch(self, request, *args, **kwargs):
        pk = self.kwargs.get("pk")
        token = self.kwargs.get("token")
        itinerary = get_object_or_404(Itinerary, pk=pk, token=token)

        # 閲覧用パスワードが設定されているかチェック
        if itinerary.view_password and not request.session.get(f'view_auth_{pk}_{token}', False):
            # 認証されていなければパスワード入力画面へリダイレクト
            return redirect(reverse('tabisync:content_password', kwargs={'pk': pk, 'token': token}))

        response = super().dispatch(request, *args, **kwargs)
        response["X-Robots-Tag"] = "noindex, nofollow"
        return response


    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        pk = self.kwargs.get("pk")
        token = self.kwargs.get("token")
        itinerary = get_object_or_404(Itinerary, pk=pk, token=token)

        travel_dates = itinerary.travel_dates.all().order_by('date')

        if travel_dates.exists():
            first_date = travel_dates.first().date
            last_date = travel_dates.last().date
            context["first_date_str"] = first_date.strftime('%Y.%m.%d')
            context["last_date_str"] = last_date.strftime('%Y.%m.%d')
        else:
            context["first_date_str"] = None
            context["last_date_str"] = None

        # タイトル・内容が両方空でないメモのみ表示
        memos = [
            memo for memo in itinerary.memos.all()
            if memo.title.strip() or memo.content.strip()
        ]
        context["memos"] = memos
        context["has_memos"] = len(memos) > 0

        context["itinerary"] = itinerary
        context["travel_dates"] = itinerary.travel_dates.all()
        context["items"] = itinerary.items.all()

        return context

#listページ
@method_decorator(ratelimit(key='ip', rate='20/m', block=True), name='dispatch')
class ListDetailView(TemplateView):
    template_name = "tabisync/list.html"

    def dispatch(self, request, *args, **kwargs):
        pk = self.kwargs.get("pk")
        token = self.kwargs.get("token")
        itinerary = get_object_or_404(Itinerary, pk=pk, token=token)

        # 閲覧用パスワードが設定されているかチェック
        if itinerary.view_password and not request.session.get(f'view_auth_{pk}_{token}', False):
            # 認証されていなければパスワード入力画面へリダイレクト
            return redirect(reverse('tabisync:content_password', kwargs={'pk': pk, 'token': token}))

        response = super().dispatch(request, *args, **kwargs)
        response["X-Robots-Tag"] = "noindex, nofollow"
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        pk = self.kwargs.get("pk")
        token = self.kwargs.get("token")
        itinerary = get_object_or_404(Itinerary, pk=pk, token=token)

        travel_dates = itinerary.travel_dates.all().order_by('date')

        if travel_dates.exists():
            first_date = travel_dates.first().date
            last_date = travel_dates.last().date
            context["first_date_str"] = first_date.strftime('%Y.%m.%d')
            context["last_date_str"] = last_date.strftime('%Y.%m.%d')
        else:
            context["first_date_str"] = None
            context["last_date_str"] = None

        context["itinerary"] = itinerary
        context["travel_dates"] = travel_dates
        context["memos"] = itinerary.memos.all()
        
        items = itinerary.items.all()
        context["items"] = items

        # 全てのアイテムの title と detail が空かをチェック
        context["all_items_empty"] = all(
            not item.title and not item.detail for item in items
        )

        return context

    
#パスワード入力画面
@method_decorator(ratelimit(key='ip', rate='20/m', block=True), name='dispatch')
class ItineraryPasswordView(View):
    template_name = 'tabisync/password.html'

    def get(self, request, pk, token):
        itinerary = get_object_or_404(Itinerary, pk=pk, token=token)
        context = {'pk': pk, 'token': token, 'itinerary': itinerary}
        response = render(request, self.template_name, context)
        response["X-Robots-Tag"] = "noindex, nofollow"
        return response

    def post(self, request, pk, token):
        if not verify_turnstile(request):
            return render(request, self.template_name, {'error': 'セキュリティチェックに失敗しました。もう一度お試しください。'})
        
        itinerary = get_object_or_404(Itinerary, pk=pk, token=token)
        input_password = request.POST.get('view_password', '')

        if itinerary.check_view_password(input_password):
            request.session[f'view_auth_{pk}_{token}'] = True
            return redirect(reverse('tabisync:content', kwargs={'pk': pk, 'token': token}))
        else:
            context = {
                'error': 'パスワードが違います',
                'pk': pk,
                'token': token,
                'itinerary': itinerary  # ← ここが抜けていた
            }
            return render(request, self.template_name, context)
        

#form
@method_decorator(ratelimit(key='ip', rate='20/m', block=True), name='dispatch')
class ContactFormView(View):
    template_name = "contact/contact_form.html"
    success_template_name = "contact/thanks.html"

    def get(self, request):
        form = ContactForm()
        return render(request, self.template_name, {"form": form})

    def post(self, request):
        if not verify_turnstile(request):
            return render(request, self.template_name, {'error': 'セキュリティチェックに失敗しました。もう一度お試しください。'})
        form = ContactForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data["email"]
            name = form.cleaned_data["name"]
            subject = form.cleaned_data["subject"]
            message = form.cleaned_data["message"]

            # 管理者向けメール内容
            full_message = f"送信者: {name} <{email}>\n\n{message}"

            # 1. 管理者宛にメール送信
            send_mail(
                subject=subject,
                message=full_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[settings.CONTACT_RECEIVER_EMAIL],
            )

            # 2. 自動返信メール送信
            auto_reply_subject = "【自動返信】お問い合わせありがとうございます"
            auto_reply_message = (
                f"{name} 様\n\n"
                "この度はお問い合わせいただきありがとうございます。\n"
                "以下の内容でお問い合わせを受け付けました。\n\n"
                "------\n"
                f"件名: {subject}\n"
                f"内容:\n{message}\n"
                "------\n\n"
                "折り返しご連絡いたしますので、今しばらくお待ちください。\n\n"
                "※本メールは自動返信です。返信いただいても対応できません。\n"
                "--------------------------------------------------\n"
                f"{getattr(settings, 'TabiSync', '旅シンク')} サポート"
            )

            send_mail(
                subject=auto_reply_subject,
                message=auto_reply_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
            )

            return render(request, self.success_template_name)

        # バリデーションエラー時
        return render(request, self.template_name, {"form": form})
    
from datetime import datetime

#編集画面
@method_decorator(ratelimit(key='ip', rate='20/m', block=True), name='dispatch')
class EditView(View):
    template_name = "tabisync/edit.html"
    password_template = "tabisync/edit_password.html"

    def get(self, request, pk, token, *args, **kwargs):
        itinerary = get_object_or_404(Itinerary, pk=pk, token=token)
        session_key = f"edit_auth_{itinerary.pk}"

        if itinerary.edit_password and not request.session.get(session_key):
            response = render(request, self.password_template, {
                "itinerary": itinerary,
                "pk": pk,
                "token": token
            })
            response["X-Robots-Tag"] = "noindex, nofollow"
            return response

        response = render(request, self.template_name, {"itinerary": itinerary})
        response["X-Robots-Tag"] = "noindex, nofollow"
        return response

    def post(self, request, pk, token, *args, **kwargs):
        if not verify_turnstile(request):
            return render(request, self.template_name, {'error': 'セキュリティチェックに失敗しました。もう一度お試しください。'})
        itinerary = get_object_or_404(Itinerary, pk=pk, token=token)
        session_key = f"edit_auth_{itinerary.pk}"

        if itinerary.edit_password and not request.session.get(session_key):
            password = request.POST.get("password", "")
            if itinerary.check_edit_password(password):
                request.session[session_key] = True
                return redirect(reverse("tabisync:edit", kwargs={"pk": pk, "token": token}))
            else:
                return render(request, self.password_template, {
                    "error": "パスワードが間違っています。",
                    "itinerary": itinerary,
                    "pk": pk,
                    "token": token
                })

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


@method_decorator(ratelimit(key='ip', rate='20/m', block=True), name='dispatch')
class SendResetLinkView(View):
    def post(self, request, pk, token, type):
        itinerary = get_object_or_404(Itinerary, pk=pk, token=token)

        if itinerary.reset_email:
            data = {"pk": pk, "token": str(token), "type": type}
            signed_token = signing.dumps(data, salt="tabisync-password-reset")

            reset_url = request.build_absolute_uri(
                reverse("tabisync:reset_password", kwargs={"signed_token": signed_token})
            )

            subject = "【TabiSync】パスワード再設定リンク"
            message = (
                f"{'編集' if type == 'edit' else '閲覧'}パスワードの再設定リンクはこちらです。\n"
                f"1時間以内に以下のURLにアクセスしてください。\n\n{reset_url}"
            )

            send_mail(subject, message, None, [itinerary.reset_email])
            messages.success(request, "再設定用リンクをメールで送信しました。")
        else:
            messages.error(request, "送信できませんでした。")

        return redirect(request.META.get("HTTP_REFERER", "/"))

    def get(self, request, *args, **kwargs):
        # POST専用にしたい場合は405返すのがベター
        from django.http import HttpResponseNotAllowed
        return HttpResponseNotAllowed(['POST'])


@method_decorator(ratelimit(key='ip', rate='20/m', block=True), name='dispatch')
class ResetPasswordView(View):
    def get(self, request, signed_token):
        try:
            data = signing.loads(signed_token, salt="tabisync-password-reset", max_age=3600)  # 1時間有効
        except signing.BadSignature:
            raise Http404("無効または期限切れのリンクです。")

        response = render(request, "tabisync/reset_password.html", {
            "signed_token": signed_token,
            "type": data["type"],
        })
        response["X-Robots-Tag"] = "noindex, nofollow"
        return response
    
    def post(self, request, signed_token):
        try:
            data = signing.loads(signed_token, salt="tabisync-password-reset", max_age=3600)
        except signing.BadSignature:
            raise Http404("無効または期限切れのリンクです。")

        itinerary = get_object_or_404(Itinerary, pk=data["pk"], token=data["token"])
        new_pw = request.POST.get("password", "").strip()

        if not new_pw:
            messages.error(request, "新しいパスワードを入力してください。")
            return redirect(request.path)

        if data["type"] == "edit":
            itinerary.edit_password = make_password(new_pw)
        else:
            itinerary.view_password = make_password(new_pw)

        itinerary.save()
        messages.success(request, "パスワードを再設定しました。")

        if data["type"] == "edit":
            return redirect("tabisync:edit", pk=data["pk"], token=data["token"])
        else:
            return redirect("tabisync:content", pk=data["pk"], token=data["token"])

       
#ver.1のもの↓

#個別ページ
@method_decorator(ratelimit(key='ip', rate='20/m', block=True), name='dispatch')
class ItineraryDetailView(TemplateView):
    template_name = "tabisync/content.html"

    def dispatch(self, request, *args, **kwargs):
        pk = self.kwargs.get("pk")
        token = self.kwargs.get("token")
        self.itinerary = get_object_or_404(Itinerary, pk=pk, token=token)

        if self.itinerary.view_password and not request.session.get(f'view_auth_{pk}_{token}', False):
            return redirect(reverse('tabisync:content_password', kwargs={'pk': pk, 'token': token}))

        response = super().dispatch(request, *args, **kwargs)
        response["X-Robots-Tag"] = "noindex, nofollow"
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        itinerary = self.itinerary  # dispatch() で取得したものを使用
        travel_dates = itinerary.travel_dates.all().order_by('date')

        for travel_date in travel_dates:
            travel_date.sorted_schedules = travel_date.schedules.all().order_by('start_time')

        if travel_dates.exists():
            first_date = travel_dates.first().date
            last_date = travel_dates.last().date
            context["first_date_str"] = first_date.strftime('%Y.%m.%d')
            context["last_date_str"] = last_date.strftime('%Y.%m.%d')
        else:
            context["first_date_str"] = None
            context["last_date_str"] = None

        context["itinerary"] = itinerary
        context["travel_dates"] = travel_dates
        context["memos"] = itinerary.memos.all()
        context["items"] = itinerary.items.all()

        return context
