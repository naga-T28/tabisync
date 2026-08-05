import mimetypes
from datetime import datetime, timedelta

from PIL import Image, UnidentifiedImageError

from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.clickjacking import xframe_options_exempt
from django.views.generic import TemplateView
from django_ratelimit.decorators import ratelimit

from ..models import Itinerary
from .itinerary_helpers import (
    build_day_choices,
    build_google_maps_search_url,
    build_itinerary_qr_code_url,
    build_itinerary_share_url,
    ensure_itinerary_qr_code,
    get_itinerary_cover_url,
    get_schedule_day_index,
    get_schedule_display_date,
)
from .utils import (
    ALLOWED_COVER_IMAGE_CONTENT_TYPES,
    MAX_COVER_IMAGE_SIZE,
    MAX_ITINERARY_DAYS,
    get_inclusive_day_count,
    ratelimit_client_ip,
)


def itinerary_qr_code_view(request, pk, token):
    itinerary = get_object_or_404(Itinerary, pk=pk, token=token)

    if itinerary.view_password and not request.session.get(f'view_auth_{pk}_{token}', False):
        return redirect(reverse('tabisync:content_password', kwargs={'pk': pk, 'token': token}))

    share_url = build_itinerary_share_url(request, itinerary)
    ensure_itinerary_qr_code(itinerary, share_url)

    if not itinerary.qr_code or not itinerary.qr_code.storage.exists(itinerary.qr_code.name):
        raise Http404("QR code image was not found.")

    response = FileResponse(itinerary.qr_code.open("rb"), content_type="image/png")
    response["X-Robots-Tag"] = "noindex, nofollow"
    return response



def itinerary_cover_image_view(request, pk, token):
    itinerary = get_object_or_404(Itinerary, pk=pk, token=token)

    view_session_key = f"view_auth_{pk}_{token}"
    edit_session_key = f"edit_auth_{pk}"
    if (
        itinerary.view_password
        and not request.session.get(view_session_key, False)
        and not request.session.get(edit_session_key, False)
    ):
        raise Http404("Cover image was not found.")

    if not itinerary.cover_image or not itinerary.cover_image.storage.exists(itinerary.cover_image.name):
        raise Http404("Cover image was not found.")

    content_type = mimetypes.guess_type(itinerary.cover_image.name)[0] or "application/octet-stream"
    response = FileResponse(itinerary.cover_image.open("rb"), content_type=content_type)
    response["X-Robots-Tag"] = "noindex, nofollow"
    response["Cache-Control"] = "private, max-age=3600"
    return response



# =========================
# しおり作成・閲覧（v2）
# =========================
# しおり作成画面
@method_decorator(ratelimit(key=ratelimit_client_ip, rate='20/m', block=True), name='dispatch')
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

        if get_inclusive_day_count(start_date_obj, end_date_obj) > MAX_ITINERARY_DAYS:
            return render(request, self.template_name, {
                "error": f"日程は最大{MAX_ITINERARY_DAYS}日間まで登録できます。",
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
        share_url = build_itinerary_share_url(request, itinerary)
        ensure_itinerary_qr_code(itinerary, share_url)

        return redirect(reverse('tabisync:content_v2', kwargs={
            'pk': itinerary.pk,
            'token': itinerary.token
        }))



# 公開用のしおり表示画面
@method_decorator(ratelimit(key=ratelimit_client_ip, rate='20/m', block=True), name='dispatch')
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

        share_url = build_itinerary_share_url(request, itinerary)
        ensure_itinerary_qr_code(itinerary, share_url)
        qr_code_url = build_itinerary_qr_code_url(itinerary)
        cover_image_url = get_itinerary_cover_url(itinerary)

        response = render(request, self.template_name, {
            "itinerary": itinerary,
            "grouped_days": grouped_days,
            "day_choices": day_choices,
            "first_date_str": first_date_str,
            "last_date_str": last_date_str,
            "share_url": share_url,
            "qr_code_url": qr_code_url,
            "cover_image_url": cover_image_url,
        })
        response["X-Robots-Tag"] = "noindex, nofollow"
        return response



@method_decorator(ratelimit(key=ratelimit_client_ip, rate='20/m', block=True), name='dispatch')
@method_decorator(xframe_options_exempt, name='dispatch')
class BlogScheduleEmbedView(TemplateView):
    template_name = "tabisync/content/blog_schedule_embed.html"

    def get(self, request, pk, open_token, day, *args, **kwargs):
        itinerary = get_object_or_404(Itinerary, pk=pk, blog_embed_token=open_token)
        day_choices = build_day_choices(itinerary)
        choice = next((item for item in day_choices if item.get("day_num") == day), None)
        if not choice:
            raise Http404("指定された日付の旅程が見つかりません。")

        schedules = [
            schedule for schedule in itinerary.schedules.select_related("place").all().order_by("day_index", "start_time", "order", "id")
            if get_schedule_day_index(itinerary, schedule) == day
        ]
        for schedule in schedules:
            schedule.blog_maps_url = build_google_maps_search_url(schedule.place)

        response = render(request, self.template_name, {
            "itinerary": itinerary,
            "choice": choice,
            "schedules": schedules,
        })
        response["X-Robots-Tag"] = "noindex, nofollow"
        return response



# =========================
# v2編集画面
# =========================
@method_decorator(ratelimit(key=ratelimit_client_ip, rate='20/m', block=True), name='dispatch')
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
            "cover_image_url": get_itinerary_cover_url(itinerary),
            "can_update_cover_image": itinerary.cover_image_updated_on != timezone.localdate(),
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
        cover_image = request.FILES.get("cover_image")

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

        today = timezone.localdate()
        if cover_image:
            if itinerary.cover_image_updated_on == today:
                itinerary.title = title
                itinerary.subtitle = subtitle
                itinerary.description = description
                return self._render_form(
                    request,
                    itinerary,
                    {"error": "表紙画像の変更は1日1回までです。明日以降に再度お試しください。"},
                    status=400,
                )

            if cover_image.size > MAX_COVER_IMAGE_SIZE:
                itinerary.title = title
                itinerary.subtitle = subtitle
                itinerary.description = description
                return self._render_form(
                    request,
                    itinerary,
                    {"error": "表紙画像は5MB以下の画像を選択してください。"},
                    status=400,
                )

            if cover_image.content_type not in ALLOWED_COVER_IMAGE_CONTENT_TYPES:
                itinerary.title = title
                itinerary.subtitle = subtitle
                itinerary.description = description
                return self._render_form(
                    request,
                    itinerary,
                    {"error": "表紙画像はJPEG、PNG、WebP、GIFのいずれかを選択してください。"},
                    status=400,
                )

            try:
                Image.open(cover_image).verify()
                cover_image.seek(0)
            except (UnidentifiedImageError, OSError):
                itinerary.title = title
                itinerary.subtitle = subtitle
                itinerary.description = description
                return self._render_form(
                    request,
                    itinerary,
                    {"error": "表紙画像として読み込めないファイルです。別の画像を選択してください。"},
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

        new_span_days = get_inclusive_day_count(new_start_date, new_end_date)
        if new_span_days > MAX_ITINERARY_DAYS:
            itinerary.title = title
            itinerary.subtitle = subtitle
            itinerary.description = description
            itinerary.start_date = new_start_date
            itinerary.end_date = new_end_date
            return self._render_form(
                request,
                itinerary,
                {"error": f"日程は最大{MAX_ITINERARY_DAYS}日間まで登録できます。"},
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
        old_cover_image = itinerary.cover_image.name if itinerary.cover_image else ""
        if cover_image:
            itinerary.cover_image = cover_image
            itinerary.cover_image_updated_on = today
        itinerary.save()

        if cover_image and old_cover_image and old_cover_image != itinerary.cover_image.name:
            storage = itinerary.cover_image.storage
            if storage.exists(old_cover_image):
                storage.delete(old_cover_image)

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
@method_decorator(ratelimit(key=ratelimit_client_ip, rate='20/m', block=True), name='dispatch')
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

