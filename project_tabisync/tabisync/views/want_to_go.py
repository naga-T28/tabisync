import json

from django.db.models import Case, IntegerField, Value, When
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView
from django_ratelimit.decorators import ratelimit

from ..models import Itinerary, WantToGo
from .itinerary_helpers import apply_want_to_go_payload, build_want_to_go_limit_message, can_add_want_to_go, get_want_to_go_limit
from .utils import ratelimit_client_ip


def _build_want_to_go_context(itinerary):
    return {
        "itinerary": itinerary,
        "places": WantToGo.objects.filter(
            itinerary=itinerary
        ).annotate(day_order=Case(
            When(planned_day=0, then=Value(999)),
            default="planned_day",
            output_field=IntegerField(),
        )).order_by("day_order", "id"),
        "itinerary_days": list(range(1, itinerary.total_days + 1)),
        "want_to_go_limit": get_want_to_go_limit(itinerary),
    }


def _apply_want_to_go_action(itinerary, data):
    # 行きたい場所の追加・更新・削除を一箇所で処理する（Itinerary配下に限定）
    action = data.get("action")

    if action == "save_want_to_go":
        if not can_add_want_to_go(itinerary):
            return JsonResponse({
                "status": "error",
                "message": build_want_to_go_limit_message(itinerary),
            }, status=400)

        place = WantToGo(itinerary=itinerary)
        apply_want_to_go_payload(place, data)
        place.save()
        return JsonResponse({
            "status": "saved",
            "id": place.id,
            "name": place.name,
            "address": place.address,
        })

    if action in ("update_want_to_go", "delete_want_to_go"):
        place_id = data.get("id")
        if not place_id:
            return JsonResponse({"status": "error", "message": "idが必要です。"}, status=400)

        place = get_object_or_404(WantToGo, pk=place_id, itinerary=itinerary)

        if action == "update_want_to_go":
            apply_want_to_go_payload(place, data)
            place.save()
            return JsonResponse({
                "status": "updated",
                "id": place.id,
                "name": place.name,
                "address": place.address,
            })

        place.delete()
        return JsonResponse({"status": "deleted"})

    return JsonResponse({"status": "error", "message": "不明な操作です。"}, status=400)


# 行きたい場所リスト表示（閲覧専用。変更操作は Wantedit のみで受け付ける）
@method_decorator(ratelimit(key=ratelimit_client_ip, rate='20/m', block=True), name='dispatch')
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
        context.update(_build_want_to_go_context(self.itinerary))
        return context


# 行きたい場所リスト編集
@method_decorator(ratelimit(key=ratelimit_client_ip, rate='20/m', block=True), name='dispatch')
class WantToGoV2View(TemplateView):

    template_name = "tabisync/content/want_list.html"
    password_template = "tabisync/edit_password.html"

    def dispatch(self, request, *args, **kwargs):
        pk = self.kwargs.get("pk")
        token = self.kwargs.get("token")
        self.itinerary = get_object_or_404(Itinerary, pk=pk, token=token)

        session_key = f"edit_auth_{self.itinerary.pk}"
        if self.itinerary.edit_password and not request.session.get(session_key):
            if request.method == "POST":
                content_type = request.headers.get("Content-Type", "")
                if "application/json" in content_type:
                    return JsonResponse({"status": "error", "message": "編集権限が必要です。"}, status=403)

                password = request.POST.get("password", "")
                if self.itinerary.check_edit_password(password):
                    request.session[session_key] = True
                    return redirect(reverse("tabisync:Wantedit", kwargs={"pk": pk, "token": token}))

                response = render(request, self.password_template, {
                    "error": "パスワードが間違っています。",
                    "itinerary": self.itinerary,
                    "pk": pk,
                    "token": token,
                })
                response["X-Robots-Tag"] = "noindex, nofollow"
                return response

            response = render(request, self.password_template, {
                "itinerary": self.itinerary,
                "pk": pk,
                "token": token,
            })
            response["X-Robots-Tag"] = "noindex, nofollow"
            return response

        response = super().dispatch(request, *args, **kwargs)
        response["X-Robots-Tag"] = "noindex, nofollow"
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(_build_want_to_go_context(self.itinerary))
        return context

    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body)
        except (TypeError, ValueError):
            return JsonResponse({"status": "error", "message": "不正なJSONです"}, status=400)

        return _apply_want_to_go_action(self.itinerary, data)
