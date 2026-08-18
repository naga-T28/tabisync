import logging

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.hashers import make_password
from django.core import signing
from django.core.mail import send_mail
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.generic import TemplateView
from django_ratelimit.decorators import ratelimit

from ..models import Itinerary
from .access_control import add_noindex_header, grant_view_access
from .itinerary_helpers import build_public_absolute_uri
from .utils import ratelimit_client_ip, verify_turnstile


logger = logging.getLogger(__name__)


# =========================
# 認証・問い合わせ
# =========================
# パスワード入力画面
@method_decorator(ratelimit(key=ratelimit_client_ip, rate='20/m', block=True), name='dispatch')
class ItineraryPasswordView(View):
    template_name = 'tabisync/password.html'

    def get(self, request, pk, token):
        itinerary = get_object_or_404(Itinerary, pk=pk, token=token)
        context = {'pk': pk, 'token': token, 'itinerary': itinerary}
        return add_noindex_header(render(request, self.template_name, context))

    def post(self, request, pk, token):
        if not verify_turnstile(request):
            return add_noindex_header(render(request, self.template_name, {'error': 'セキュリティチェックに失敗しました。もう一度お試しください。'}))

        itinerary = get_object_or_404(Itinerary, pk=pk, token=token)
        input_password = request.POST.get('view_password', '')

        if itinerary.check_view_password(input_password):
            grant_view_access(request, itinerary)
            return add_noindex_header(redirect(reverse('tabisync:content_v2', kwargs={'pk': pk, 'token': token})))
        else:
            context = {
                'error': 'パスワードが違います',
                'pk': pk,
                'token': token,
                'itinerary': itinerary  # ← ここが抜けていた
            }
            return add_noindex_header(render(request, self.template_name, context))



# 問い合わせフォーム（Googleフォームを埋め込んで表示するだけの静的ページ）
class ContactFormView(TemplateView):
    template_name = "contact/contact_form.html"



# パスワード再設定リンク送信
@method_decorator(ratelimit(key=ratelimit_client_ip, rate='20/m', block=True), name='dispatch')
class SendResetLinkView(View):
    def post(self, request, pk, token, type):
        itinerary = get_object_or_404(Itinerary, pk=pk, token=token)

        if itinerary.reset_email:
            data = {"pk": pk, "token": str(token), "type": type}
            signed_token = signing.dumps(data, salt="tabisync-password-reset")

            reset_url = build_public_absolute_uri(
                request,
                reverse("tabisync:reset_password", kwargs={"signed_token": signed_token})
            )

            subject = "【TabiSync】パスワード再設定リンク"
            message = (
                f"{'編集' if type == 'edit' else '閲覧'}パスワードの再設定リンクはこちらです。\n"
                f"1時間以内に以下のURLにアクセスしてください。\n\n{reset_url}"
            )

            try:
                sent_count = send_mail(
                    subject,
                    message,
                    settings.DEFAULT_FROM_EMAIL,
                    [itinerary.reset_email],
                    fail_silently=False,
                )
            except Exception:
                logger.exception("Failed to send password reset email for itinerary %s.", itinerary.pk)
                messages.error(request, "メールの送信に失敗しました。時間をおいて再度お試しください。")
            else:
                if sent_count:
                    messages.success(request, "再設定用リンクをメールで送信しました。")
                else:
                    logger.warning("Password reset email was not sent for itinerary %s.", itinerary.pk)
                    messages.error(request, "メールの送信に失敗しました。時間をおいて再度お試しください。")
        else:
            messages.error(request, "送信できませんでした。")

        return add_noindex_header(redirect(request.META.get("HTTP_REFERER", "/")))

    def get(self, request, *args, **kwargs):
        # POST専用にしたい場合は405返すのがベター
        from django.http import HttpResponseNotAllowed
        return HttpResponseNotAllowed(['POST'])



# 再設定リンクから新しいパスワードを保存
@method_decorator(ratelimit(key=ratelimit_client_ip, rate='20/m', block=True), name='dispatch')
class ResetPasswordView(View):
    def get(self, request, signed_token):
        try:
            data = signing.loads(signed_token, salt="tabisync-password-reset", max_age=3600)  # 1時間有効
        except signing.BadSignature:
            raise Http404("無効または期限切れのリンクです。")

        return add_noindex_header(render(request, "tabisync/reset_password.html", {
            "signed_token": signed_token,
            "type": data["type"],
        }))

    def post(self, request, signed_token):
        try:
            data = signing.loads(signed_token, salt="tabisync-password-reset", max_age=3600)
        except signing.BadSignature:
            raise Http404("無効または期限切れのリンクです。")

        itinerary = get_object_or_404(Itinerary, pk=data["pk"], token=data["token"])
        new_pw = request.POST.get("password", "").strip()

        if not new_pw:
            messages.error(request, "新しいパスワードを入力してください。")
            return add_noindex_header(redirect(request.path))

        if data["type"] == "edit":
            itinerary.edit_password = make_password(new_pw)
        else:
            itinerary.view_password = make_password(new_pw)

        itinerary.save()
        messages.success(request, "パスワードを再設定しました。")

        if data["type"] == "edit":
            return add_noindex_header(redirect("tabisync:edit", pk=data["pk"], token=data["token"]))
        else:
            return add_noindex_header(redirect("tabisync:content", pk=data["pk"], token=data["token"]))

