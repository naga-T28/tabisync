import json

from django.http import JsonResponse
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import ensure_csrf_cookie
from django_ratelimit.decorators import ratelimit

from ..models import ChecklistV2
from .access_control import EditPasswordRequiredMixin, ViewPasswordRequiredMixin, has_edit_access, require_edit_access_json
from .itinerary_helpers import build_default_checklist_v2_lists, normalize_checklist_v2_content
from .utils import parse_json_object_body, ratelimit_client_ip, validate_checklist_limits


# v2リスト表示ページ
@method_decorator(ratelimit(key=ratelimit_client_ip, rate='20/m', block=True), name='dispatch')
class ChecklistV2View(ViewPasswordRequiredMixin, View):
    template_name = "tabisync/content/list_v2.html"

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
            "can_edit_checklist": has_edit_access(request, self.itinerary),
        })

    def post(self, request, pk, token):
        gate_response = require_edit_access_json(request, self.itinerary)
        if gate_response is not None:
            return gate_response

        checklist, _ = ChecklistV2.objects.get_or_create(itinerary=self.itinerary)

        data, error_response = parse_json_object_body(request)
        if error_response is not None:
            return error_response

        lists = normalize_checklist_v2_content(json.dumps(data.get("lists", []), ensure_ascii=False))
        limit_error = validate_checklist_limits(lists)
        if limit_error:
            return JsonResponse({"status": "error", "message": limit_error}, status=400)

        checklist.content = json.dumps(lists, ensure_ascii=False)
        checklist.save()
        return JsonResponse({"status": "ok", "lists_count": len(lists), "lists": lists})



# v2リスト編集ページ
@method_decorator(ratelimit(key=ratelimit_client_ip, rate='20/m', block=True), name='dispatch')
class ChecklistV2EditView(EditPasswordRequiredMixin, View):
    template_name = "tabisync/content/list_v2.html"
    edit_redirect_url_name = "V2_list_edit"

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

        data, error_response = parse_json_object_body(request)
        if error_response is not None:
            return error_response

        lists = normalize_checklist_v2_content(json.dumps(data.get("lists", []), ensure_ascii=False))
        limit_error = validate_checklist_limits(lists)
        if limit_error:
            return JsonResponse({"status": "error", "message": limit_error}, status=400)

        checklist.content = json.dumps(lists, ensure_ascii=False)
        checklist.save()
        return JsonResponse({"status": "ok", "lists_count": len(lists), "lists": lists})
