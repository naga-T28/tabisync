import json

from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import ensure_csrf_cookie
from django_ratelimit.decorators import ratelimit

from ..models import ChecklistV2, Itinerary
from .itinerary_helpers import build_default_checklist_v2_lists, normalize_checklist_v2_content
from .utils import ratelimit_client_ip, validate_checklist_limits


# v2リスト表示ページ
@method_decorator(ratelimit(key=ratelimit_client_ip, rate='20/m', block=True), name='dispatch')
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

    @method_decorator(ensure_csrf_cookie)
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
            "can_edit_checklist": not self.itinerary.edit_password or request.session.get(f"edit_auth_{self.itinerary.pk}", False),
        })

    def post(self, request, pk, token):
        if self.itinerary.edit_password and not request.session.get(f"edit_auth_{self.itinerary.pk}", False):
            return JsonResponse({"status": "error", "message": "編集権限が必要です。"}, status=403)

        checklist, _ = ChecklistV2.objects.get_or_create(itinerary=self.itinerary)

        try:
            data = json.loads(request.body)
        except (TypeError, ValueError):
            return JsonResponse({"status": "error", "message": "不正なJSONです"}, status=400)

        lists = normalize_checklist_v2_content(json.dumps(data.get("lists", []), ensure_ascii=False))
        limit_error = validate_checklist_limits(lists)
        if limit_error:
            return JsonResponse({"status": "error", "message": limit_error}, status=400)

        checklist.content = json.dumps(lists, ensure_ascii=False)
        checklist.save()
        return JsonResponse({"status": "ok", "lists_count": len(lists), "lists": lists})



# v2リスト編集ページ
@method_decorator(ratelimit(key=ratelimit_client_ip, rate='20/m', block=True), name='dispatch')
class ChecklistV2EditView(View):
    template_name = "tabisync/content/list_v2.html"
    password_template = "tabisync/edit_password.html"

    def dispatch(self, request, *args, **kwargs):
        self.pk = kwargs.get("pk")
        self.token = kwargs.get("token")
        self.itinerary = get_object_or_404(Itinerary, pk=self.pk, token=self.token)

        session_key = f"edit_auth_{self.itinerary.pk}"
        if self.itinerary.edit_password and not request.session.get(session_key):
            if request.method == "POST":
                content_type = request.headers.get("Content-Type", "")
                if "application/json" in content_type:
                    return JsonResponse({"status": "error", "message": "編集権限が必要です。"}, status=403)

                password = request.POST.get("password", "")
                if self.itinerary.check_edit_password(password):
                    request.session[session_key] = True
                    return redirect(reverse("tabisync:V2_list_edit", kwargs={"pk": self.pk, "token": self.token}))

                response = render(request, self.password_template, {
                    "error": "パスワードが間違っています。",
                    "itinerary": self.itinerary,
                    "pk": self.pk,
                    "token": self.token,
                })
                response["X-Robots-Tag"] = "noindex, nofollow"
                return response

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

    @method_decorator(ensure_csrf_cookie)
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
            "can_edit_checklist": True,
        })

    def post(self, request, pk, token):
        checklist, _ = ChecklistV2.objects.get_or_create(itinerary=self.itinerary)

        try:
            data = json.loads(request.body)
        except (TypeError, ValueError):
            return JsonResponse({"status": "error", "message": "不正なJSONです"}, status=400)

        lists = normalize_checklist_v2_content(json.dumps(data.get("lists", []), ensure_ascii=False))
        limit_error = validate_checklist_limits(lists)
        if limit_error:
            return JsonResponse({"status": "error", "message": limit_error}, status=400)

        checklist.content = json.dumps(lists, ensure_ascii=False)
        checklist.save()
        return JsonResponse({"status": "ok", "lists_count": len(lists), "lists": lists})

