import hashlib

from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from ..models import Itinerary

DEFAULT_EDIT_PASSWORD_TEMPLATE = "tabisync/edit_password.html"


def _password_fingerprint(password_hash):
    # パスワードハッシュ(make_password出力)は再設定のたびに変わるため、
    # これをセッションキーへ含めるだけで、パスワード変更時に旧セッションを
    # 明示的な失効処理なしに自動的に無効化できる。
    if not password_hash:
        return "none"
    return hashlib.sha256(password_hash.encode("utf-8")).hexdigest()[:16]


def build_view_session_key(itinerary):
    return f"view_auth_{itinerary.pk}_{itinerary.token}_{_password_fingerprint(itinerary.view_password)}"


def build_edit_session_key(itinerary):
    return f"edit_auth_{itinerary.pk}_{_password_fingerprint(itinerary.edit_password)}"


def has_view_access(request, itinerary):
    if not itinerary.view_password:
        return True
    return bool(request.session.get(build_view_session_key(itinerary)))


def has_edit_access(request, itinerary):
    if not itinerary.edit_password:
        return True
    return bool(request.session.get(build_edit_session_key(itinerary)))


def grant_view_access(request, itinerary):
    request.session[build_view_session_key(itinerary)] = True


def grant_edit_access(request, itinerary):
    request.session[build_edit_session_key(itinerary)] = True


def is_json_request(request):
    return "application/json" in request.headers.get("Content-Type", "")


def get_itinerary_or_404(pk, token):
    return get_object_or_404(Itinerary, pk=pk, token=token)


def add_noindex_header(response):
    response["X-Robots-Tag"] = "noindex, nofollow"
    return response


def require_view_access(request, itinerary):
    """閲覧ゲート。許可されていればNone。HTMLリクエストはパスワード画面へredirect、
    JSONリクエストは403 JsonResponseを返す。"""
    if has_view_access(request, itinerary):
        return None
    if is_json_request(request):
        return JsonResponse({"status": "error", "message": "閲覧認証が必要です。"}, status=403)
    return add_noindex_header(redirect(
        reverse("tabisync:content_password", kwargs={"pk": itinerary.pk, "token": itinerary.token})
    ))


def require_view_access_json(request, itinerary):
    """JSON APIエンドポイント用の閲覧ゲート。許可されていればNone、そうでなければ403。"""
    if has_view_access(request, itinerary):
        return None
    return JsonResponse({"status": "error", "message": "閲覧認証が必要です。"}, status=403)


def require_edit_access_json(request, itinerary):
    """JSON APIエンドポイント用の編集ゲート。許可されていればNone、そうでなければ403。"""
    if has_edit_access(request, itinerary):
        return None
    return JsonResponse({"status": "error", "message": "編集権限が必要です。"}, status=403)


def render_edit_password_form(request, itinerary, error=None, template=DEFAULT_EDIT_PASSWORD_TEMPLATE):
    context = {"itinerary": itinerary, "pk": itinerary.pk, "token": itinerary.token}
    if error:
        context["error"] = error
    return add_noindex_header(render(request, template, context))


def handle_edit_password_gate(request, itinerary, redirect_url_name, template=DEFAULT_EDIT_PASSWORD_TEMPLATE):
    """編集専用ページの認可ゲート。

    - 認可済みならNoneを返す(呼び出し側は通常のGET/POST処理を続行する)。
    - 未認可でJSON POSTなら403 JsonResponseを返す。
    - 未認可でGETならパスワード入力画面を返す。
    - 未認可でform POSTならパスワードを照合し、成功すれば編集権限を付与して自ページへredirect、
      失敗すればエラー付きのパスワード入力画面を返す。
    """
    if has_edit_access(request, itinerary):
        return None

    if request.method == "POST":
        if is_json_request(request):
            return JsonResponse({"status": "error", "message": "編集権限が必要です。"}, status=403)

        password = request.POST.get("password", "")
        if itinerary.check_edit_password(password):
            grant_edit_access(request, itinerary)
            return redirect(reverse(
                f"tabisync:{redirect_url_name}",
                kwargs={"pk": itinerary.pk, "token": itinerary.token},
            ))

        return render_edit_password_form(request, itinerary, error="パスワードが間違っています。", template=template)

    return render_edit_password_form(request, itinerary, template=template)


class ViewPasswordRequiredMixin:
    """閲覧パスワードで保護されたページ用の共通dispatch。

    self.itinerary をdispatchで一度だけ取得し、view_password未認証ならHTMLは
    パスワード画面へredirect、JSONは403を返す。認可済みなら通常どおり処理を継続する。
    """

    def dispatch(self, request, *args, **kwargs):
        self.itinerary = get_itinerary_or_404(kwargs.get("pk"), kwargs.get("token"))

        gate_response = require_view_access(request, self.itinerary)
        if gate_response is not None:
            return gate_response

        response = super().dispatch(request, *args, **kwargs)
        return add_noindex_header(response)


class EditPasswordRequiredMixin:
    """編集専用ページ用の共通dispatch。

    self.itinerary をdispatchで一度だけ取得し、edit_password未認証時は
    handle_edit_password_gate に従ってパスワード画面/403/redirectを返す。
    サブクラスは edit_redirect_url_name（パスワード成功後にredirectするURL名）を指定する。
    """

    edit_password_template = DEFAULT_EDIT_PASSWORD_TEMPLATE
    edit_redirect_url_name = None

    def dispatch(self, request, *args, **kwargs):
        self.itinerary = get_itinerary_or_404(kwargs.get("pk"), kwargs.get("token"))

        gate_response = handle_edit_password_gate(
            request, self.itinerary, self.edit_redirect_url_name, self.edit_password_template
        )
        if gate_response is not None:
            return gate_response

        response = super().dispatch(request, *args, **kwargs)
        return add_noindex_header(response)
