from django.shortcuts import render, redirect, get_object_or_404
from django.utils.decorators import method_decorator
from django_ratelimit.decorators import ratelimit
from django.urls import reverse
from django.views.generic import TemplateView #add_2025.06.07
from django.views import View
from .models import Itinerary, TravelDate, Schedule, Memo, Item
from django.core.mail import send_mail
from .forms import ContactForm
import urllib.request
import urllib.parse
import json
import os
from django.conf import settings
from django.http import HttpResponse
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
from django.contrib.auth.hashers import make_password
from django.shortcuts import render


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



    
@method_decorator(ratelimit(key='ip', rate='20/m', block=True), name='dispatch')
class CreateView(View):
    template_name = "tabisync/create.html"

    def get(self, request, *args, **kwargs):
        return render(request, self.template_name)

    def post(self, request, *args, **kwargs):
        if not verify_turnstile(request):
            return render(request, self.template_name, {'error': 'セキュリティチェックに失敗しました。もう一度お試しください。'})
        # 1. しおり本体の作成
        itinerary = Itinerary(
            title=request.POST.get('title'),
            subtitle=request.POST.get('subtitle'),
            description=request.POST.get('description'),
            reset_email=request.POST.get('reset_email', '')
        )
        itinerary.set_passwords(
            view_pw=request.POST.get('view_password', ''),
            edit_pw=request.POST.get('edit_password', '')
        )
        itinerary.save()

        # 2. 日付とスケジュール
        for i in range(100):
            date_key = f'dates[{i}][date]'
            if date_key not in request.POST:
                break
            travel_date = TravelDate.objects.create(
                itinerary=itinerary,
                date=request.POST[date_key],
                order=i
            )
            for j in range(100):
                prefix = f'dates[{i}][schedules][{j}]'
                if f'{prefix}[start_time]' not in request.POST:
                    break

                # end_time の空文字を None に変換
                raw_end_time = request.POST.get(f'{prefix}[end_time]', '')
                end_time = raw_end_time if raw_end_time else None

                Schedule.objects.create(
                    travel_date=travel_date,
                    start_time=request.POST.get(f'{prefix}[start_time]', ''),  # ここも空の場合に注意した方がよい
                    end_time=end_time,
                    title=request.POST.get(f'{prefix}[title]', ''),
                    description=request.POST.get(f'{prefix}[description]', ''),
                    location=request.POST.get(f'{prefix}[location]', ''),
                    location_url=request.POST.get(f'{prefix}[location_url]', ''),
                    order=j
                )


        # 3. メモ
        for i in range(100):
            title_key = f'memos[{i}][title]'
            if title_key not in request.POST:
                break
            Memo.objects.create(
                itinerary=itinerary,
                title=request.POST.get(title_key, ''),
                content=request.POST.get(f'memos[{i}][content]', '')
            )

        # 4. 持ち物
        for i in range(100):
            title_key = f'items[{i}][title]'
            if title_key not in request.POST:
                break
            Item.objects.create(
                itinerary=itinerary,
                title=request.POST.get(title_key, ''),
                detail=request.POST.get(f'items[{i}][detail]', '')
            )

        return redirect(reverse('tabisync:content', kwargs={
            'pk': itinerary.pk,
            'token': itinerary.token
        }))
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