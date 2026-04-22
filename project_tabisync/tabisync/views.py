import json
import os
import urllib.parse
import urllib.request

from datetime import datetime, timedelta
from uuid import UUID, uuid4

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.hashers import make_password
from django.core import signing
from django.core.mail import send_mail
from django.db import transaction
from django.db.models import Case, IntegerField, Value, When
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.utils.html import strip_tags
from django.utils import timezone
from django.views import View
from django.views.decorators.http import require_POST
from django.views.generic import TemplateView  # add_2025.06.07
from django_ratelimit.decorators import ratelimit

from .forms import ContactForm
from .openai_concierge import OpenAIConciergeError, run_answer, run_data_selection, run_moderation
from .models import ChecklistV2, ConciergeChatLog, Itinerary, Item, Memo, MemoV2, Schedule, ScheduleV2, TravelDate, WantToGo


# =========================
# 基本ユーティリティ
# =========================
def offline_view(request):
    return render(request, "offline.html")

# クローラ対策
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


def build_public_absolute_uri(request, path=None):
    target_path = path or request.get_full_path()
    scheme = "https" if getattr(settings, "USE_HTTPS", False) else request.scheme
    return f"{scheme}://{request.get_host()}{target_path}"

# =========================
# 静的ページ・案内ページ
# =========================
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

# =========================
# デモページ
# =========================
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


# =========================
# しおり作成・閲覧（v2）
# =========================
# しおり作成画面
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
        design_number = request.POST.get('design_number', 1)

        if not start_date or not end_date:
            return render(request, self.template_name, {
                "error": "開始日と終了日を入力してください。",
            }, status=400)

        try:
            start_date_obj = datetime.strptime(start_date, "%Y-%m-%d").date()
            end_date_obj = datetime.strptime(end_date, "%Y-%m-%d").date()
        except ValueError:
            return render(request, self.template_name, {
                "error": "日付の形式が正しくありません。",
            }, status=400)

        if end_date_obj < start_date_obj:
            return render(request, self.template_name, {
                "error": "終了日は開始日以降を指定してください。",
            }, status=400)

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

        itinerary.set_passwords(
            view_pw=request.POST.get('view_password', ''),
            edit_pw=request.POST.get('edit_password', '')
        )

        itinerary.save()

        return redirect(reverse('tabisync:content_v2', kwargs={
            'pk': itinerary.pk,
            'token': itinerary.token
        }))

# 公開用のしおり表示画面
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

        share_url = build_public_absolute_uri(
            request,
            reverse("tabisync:content_v2", kwargs={"pk": itinerary.pk, "token": itinerary.token})
        )
        qr_code_url = (
            "https://api.qrserver.com/v1/create-qr-code/"
            f"?size=220x220&data={urllib.parse.quote(share_url, safe='')}"
        )

        response = render(request, self.template_name, {
            "itinerary": itinerary,
            "grouped_days": grouped_days,
            "day_choices": day_choices,
            "first_date_str": first_date_str,
            "last_date_str": last_date_str,
            "share_url": share_url,
            "qr_code_url": qr_code_url,
        })
        response["X-Robots-Tag"] = "noindex, nofollow"
        return response

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


# 行きたい場所リスト表示
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
            place = WantToGo(itinerary=itinerary)
            apply_want_to_go_payload(place, data)
            place.save()
            return JsonResponse({
                "status": "saved",
                "id": place.id,
                "name": place.name,
                "address": place.address,
            })

        if action == "update_want_to_go":
            place = get_object_or_404(WantToGo, pk=data.get("id"), itinerary=itinerary)
            apply_want_to_go_payload(place, data)
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

# 行きたい場所リスト編集
@method_decorator(ratelimit(key='ip', rate='20/m', block=True), name='dispatch')
class WantToGoV2View(TemplateView):

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
            place = WantToGo(itinerary=itinerary)
            apply_want_to_go_payload(place, data)
            place.save()
            return JsonResponse({
                "status": "saved",
                "id": place.id,
                "name": place.name,
                "address": place.address,
            })

        if action == "update_want_to_go":
            place = get_object_or_404(WantToGo, pk=data.get("id"), itinerary=itinerary)
            apply_want_to_go_payload(place, data)
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
                "checked": False,
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

# =========================
# v2編集画面
# =========================
@method_decorator(ratelimit(key='ip', rate='20/m', block=True), name='dispatch')
class EditContentFormV2View(View):
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
                return redirect(reverse("tabisync:content_edit_form_v2", kwargs={"pk": pk, "token": token}))
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

        if not title:
            itinerary.title = title
            itinerary.subtitle = subtitle
            itinerary.description = description
            return self._render_form(
                request,
                itinerary,
                {"error": "タイトルを入力してください。"},
                status=400,
            )

        new_start_date = None
        new_end_date = None
        old_start_date = itinerary.start_date

        if not start_date_str or not end_date_str:
            itinerary.title = title
            itinerary.subtitle = subtitle
            itinerary.description = description
            itinerary.start_date = start_date_str or None
            itinerary.end_date = end_date_str or None
            return self._render_form(
                request,
                itinerary,
                {"error": "開始日と終了日を入力してください。"},
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
            return self._render_form(
                request,
                itinerary,
                {"error": "日付の形式が正しくありません。"},
                status=400,
            )

        if new_end_date < new_start_date:
            itinerary.title = title
            itinerary.subtitle = subtitle
            itinerary.description = description
            itinerary.start_date = new_start_date
            itinerary.end_date = new_end_date
            return self._render_form(
                request,
                itinerary,
                {"error": "終了日は開始日以降を指定してください。"},
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

        if new_start_date and new_end_date:
            new_span_days = (new_end_date - new_start_date).days + 1
            if existing_max_day > new_span_days:
                itinerary.title = title
                itinerary.subtitle = subtitle
                itinerary.description = description
                itinerary.start_date = new_start_date
                itinerary.end_date = new_end_date
                return self._render_form(
                    request,
                    itinerary,
                    {
                        "error": f"既存の予定または行きたい場所がDay {existing_max_day}まで入っているため、この日程には収まりません。",
                    },
                    status=400,
                )

        schedules = list(itinerary.schedules.all())
        existing_schedule_day_indexes = {
            schedule.id: get_schedule_day_index(itinerary, schedule)
            for schedule in schedules
        }

        itinerary.title = title
        itinerary.subtitle = subtitle
        itinerary.description = description
        itinerary.start_date = new_start_date
        itinerary.end_date = new_end_date
        itinerary.save()

        fallback_base_date = itinerary.created_at.date()
        for schedule in schedules:
            day_index = existing_schedule_day_indexes.get(schedule.id)
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

# version2の編集メニュー画面
@method_decorator(ratelimit(key='ip', rate='20/m', block=True), name='dispatch')
class EditMenuV2View(View):
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

        return self._render_form(request, itinerary)

# スケジュール本体の編集画面
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
# ScheduleV2 の行を追加・更新する API
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
# ScheduleV2 の行を削除する API
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
# v2メモページ
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
        notes = normalize_memo_v2_notes(memo.content)
        return render(request, self.template_name, {
            "memo": memo,
            "memo_notes": notes,
            "itinerary": self.itinerary,
        })

    def post(self, request, pk, token):
        memo, _ = MemoV2.objects.get_or_create(itinerary=self.itinerary)
        try:
            data = json.loads(request.body.decode("utf-8"))
        except (TypeError, ValueError, json.JSONDecodeError):
            return JsonResponse({"status": "error", "message": "不正なJSONです"}, status=400)

        if isinstance(data.get("notes"), list):
            notes = normalize_memo_v2_notes(json.dumps(data.get("notes", []), ensure_ascii=False))
        else:
            notes = normalize_memo_v2_notes(data.get("content", ""))

        memo.content = json.dumps(notes, ensure_ascii=False)
        memo.save()
        return JsonResponse({"status": "ok", "notes_count": len(notes)})


# v2リスト表示ページ
@method_decorator(ratelimit(key='ip', rate='20/m', block=True), name='dispatch')
class ChecklistV2View(View):
    template_name = "tabisync/content/list_v2.html"

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
        checklist, _ = ChecklistV2.objects.get_or_create(itinerary=self.itinerary)
        lists = normalize_checklist_v2_content(checklist.content)
        if not lists:
            lists = build_default_checklist_v2_lists()
            checklist.content = json.dumps(lists, ensure_ascii=False)
            checklist.save(update_fields=["content"])
        return render(request, self.template_name, {
            "itinerary": self.itinerary,
            "checklists": lists,
            "checklists_json": json.dumps(lists, ensure_ascii=False),
        })

    def post(self, request, pk, token):
        checklist, _ = ChecklistV2.objects.get_or_create(itinerary=self.itinerary)

        try:
            data = json.loads(request.body)
        except (TypeError, ValueError):
            return JsonResponse({"status": "error", "message": "不正なJSONです"}, status=400)

        lists = normalize_checklist_v2_content(json.dumps(data.get("lists", []), ensure_ascii=False))
        checklist.content = json.dumps(lists, ensure_ascii=False)
        checklist.save()
        return JsonResponse({"status": "ok", "lists_count": len(lists)})


@method_decorator(ratelimit(key='ip', rate='20/m', block=True), name='dispatch')
class ConciergeV2View(View):
    template_name = "tabisync/content/concierge_v2.html"

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
        first_date_str = None
        last_date_str = None
        if self.itinerary.start_date and self.itinerary.end_date:
            first_date_str = self.itinerary.start_date.strftime("%Y.%m.%d")
            last_date_str = self.itinerary.end_date.strftime("%Y.%m.%d")

        return render(request, self.template_name, {
            "itinerary": self.itinerary,
            "first_date_str": first_date_str,
            "last_date_str": last_date_str,
        })

    def post(self, request, pk, token):
        try:
            body = json.loads(request.body.decode("utf-8"))
        except (TypeError, ValueError, json.JSONDecodeError):
            return JsonResponse({"status": "error", "message": "不正なJSONです。"}, status=400)

        user_message = str(body.get("message") or "").strip()
        if not user_message:
            return JsonResponse({"status": "error", "message": "メッセージを入力してください。"}, status=400)

        raw_conversation_id = str(body.get("conversation_id") or "").strip()
        conversation_id = self._parse_conversation_id(raw_conversation_id)
        history = self._normalize_history(body.get("history"))
        turn_index = len([item for item in history if item.get("role") == "user"]) + 1
        daily_limit = self.itinerary.get_concierge_daily_limit()
        today_count = self._get_today_usage_count()

        if today_count >= daily_limit:
            return JsonResponse({
                "status": "limit_exceeded",
                "message": f"このしおりのAIコンシェルジュは1日{daily_limit}回までです。日付が変わってから再度お試しください。",
                "conversation_id": str(conversation_id),
                "daily_limit": daily_limit,
                "remaining_count": 0,
            }, status=429)

        try:
            moderation_prompt, moderation_payload, moderation_result = run_moderation(user_message)
        except OpenAIConciergeError as exc:
            return JsonResponse({"status": "error", "message": str(exc)}, status=502)

        if not moderation_result.get("allowed", False):
            assistant_message = moderation_result.get("reason") or "この内容には対応できません。"
            self._save_chat_log(
                conversation_id=conversation_id,
                turn_index=turn_index,
                user_message=user_message,
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
            return JsonResponse({"status": "error", "message": str(exc)}, status=502)

        required_data = selection_result.get("required_data", [])
        selected_context = self._build_selected_context(required_data)

        try:
            answer_prompt, answer_payload, assistant_message = run_answer(history, user_message, selected_context)
        except OpenAIConciergeError as exc:
            return JsonResponse({"status": "error", "message": str(exc)}, status=502)

        self._save_chat_log(
            conversation_id=conversation_id,
            turn_index=turn_index,
            user_message=user_message,
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
            "required_data": required_data,
            "daily_limit": daily_limit,
            "remaining_count": max(daily_limit - (today_count + 1), 0),
        })

    def _parse_conversation_id(self, raw_value):
        try:
            return UUID(raw_value)
        except (ValueError, TypeError, AttributeError):
            return uuid4()

    def _normalize_history(self, raw_history):
        if not isinstance(raw_history, list):
            return []

        normalized_history = []
        for item in raw_history[-12:]:
            if not isinstance(item, dict):
                continue
            role = str(item.get("role") or "").strip()
            content = str(item.get("content") or "").strip()
            if role not in {"user", "assistant"} or not content:
                continue
            normalized_history.append({
                "role": role,
                "content": content[:4000],
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

    def _save_chat_log(
        self,
        conversation_id,
        turn_index,
        user_message,
        moderation_prompt="",
        moderation_result=None,
        data_selection_prompt="",
        data_selection_result=None,
        answer_prompt="",
        answer_context=None,
        assistant_message="",
    ):
        ConciergeChatLog.objects.create(
            itinerary=self.itinerary,
            conversation_id=conversation_id,
            turn_index=turn_index,
            user_message=user_message,
            moderation_prompt=moderation_prompt,
            moderation_result=moderation_result or {},
            data_selection_prompt=data_selection_prompt,
            data_selection_result=data_selection_result or {},
            answer_prompt=answer_prompt,
            answer_context=answer_context or {},
            assistant_message=assistant_message,
        )


# v2リスト編集ページ
@method_decorator(ratelimit(key='ip', rate='20/m', block=True), name='dispatch')
class ChecklistV2EditView(View):
    template_name = "tabisync/content/list_edit_v2.html"
    password_template = "tabisync/edit_password.html"

    def dispatch(self, request, *args, **kwargs):
        self.pk = kwargs.get("pk")
        self.token = kwargs.get("token")
        self.itinerary = get_object_or_404(Itinerary, pk=self.pk, token=self.token)

        session_key = f"edit_auth_{self.itinerary.pk}"
        if self.itinerary.edit_password and not request.session.get(session_key):
            response = render(request, self.password_template, {
                "itinerary": self.itinerary,
                "pk": self.pk,
                "token": self.token,
            })
            response["X-Robots-Tag"] = "noindex, nofollow"
            return response

        response = super().dispatch(request, *args, **kwargs)
        response["X-Robots-Tag"] = "noindex, nofollow"
        return response

    def get(self, request, pk, token):
        checklist, _ = ChecklistV2.objects.get_or_create(itinerary=self.itinerary)
        lists = normalize_checklist_v2_content(checklist.content)
        if not lists:
            lists = build_default_checklist_v2_lists()
            checklist.content = json.dumps(lists, ensure_ascii=False)
            checklist.save(update_fields=["content"])
        return render(request, self.template_name, {
            "itinerary": self.itinerary,
            "checklists_json": json.dumps(lists, ensure_ascii=False),
        })

    def post(self, request, pk, token):
        checklist, _ = ChecklistV2.objects.get_or_create(itinerary=self.itinerary)

        try:
            data = json.loads(request.body)
        except (TypeError, ValueError):
            return JsonResponse({"status": "error", "message": "不正なJSONです"}, status=400)

        lists = normalize_checklist_v2_content(json.dumps(data.get("lists", []), ensure_ascii=False))
        checklist.content = json.dumps(lists, ensure_ascii=False)
        checklist.save()
        return JsonResponse({"status": "ok", "lists_count": len(lists)})

# =========================
# ver.1 閲覧ページ
# =========================
# memoページ
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
# 認証・問い合わせ
# =========================
# パスワード入力画面
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
            return redirect(reverse('tabisync:content_v2', kwargs={'pk': pk, 'token': token}))
        else:
            context = {
                'error': 'パスワードが違います',
                'pk': pk,
                'token': token,
                'itinerary': itinerary  # ← ここが抜けていた
            }
            return render(request, self.template_name, context)
        

# 問い合わせフォーム
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
# =========================
# ver.1 編集・パスワード再設定
# =========================
# 編集画面
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
                return redirect(reverse("tabisync:content_edit_v2", kwargs={"pk": pk, "token": token}))
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
# パスワード再設定リンク送信
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
# 再設定リンクから新しいパスワードを保存
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
