import json

from django.http import JsonResponse
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import ensure_csrf_cookie
from django_ratelimit.decorators import ratelimit

from ..models import MemoV2
from .access_control import EditPasswordRequiredMixin, ViewPasswordRequiredMixin, has_edit_access, require_edit_access_json
from .itinerary_helpers import normalize_memo_v2_notes
from .utils import ratelimit_client_ip, validate_memo_notes_limits


# v2メモページ
@method_decorator(ratelimit(key=ratelimit_client_ip, rate='20/m', block=True), name='dispatch')
class MemoV2View(ViewPasswordRequiredMixin, View):
    template_name = "tabisync/content/memo_v2.html"

    @method_decorator(ensure_csrf_cookie)
    def get(self, request, pk, token):
        memo, _ = MemoV2.objects.get_or_create(itinerary=self.itinerary)
        notes = normalize_memo_v2_notes(memo.content)
        return render(request, self.template_name, {
            "memo": memo,
            "memo_notes": notes,
            "itinerary": self.itinerary,
            "can_edit_memo": has_edit_access(request, self.itinerary),
        })

    def post(self, request, pk, token):
        gate_response = require_edit_access_json(request, self.itinerary)
        if gate_response is not None:
            return gate_response

        memo, _ = MemoV2.objects.get_or_create(itinerary=self.itinerary)
        try:
            data = json.loads(request.body.decode("utf-8"))
        except (TypeError, ValueError, json.JSONDecodeError):
            return JsonResponse({"status": "error", "message": "不正なJSONです"}, status=400)

        if isinstance(data.get("notes"), list):
            notes = normalize_memo_v2_notes(json.dumps(data.get("notes", []), ensure_ascii=False))
        else:
            notes = normalize_memo_v2_notes(data.get("content", ""))

        limit_error = validate_memo_notes_limits(notes)
        if limit_error:
            return JsonResponse({"status": "error", "message": limit_error}, status=400)

        memo.content = json.dumps(notes, ensure_ascii=False)
        memo.save()
        return JsonResponse({"status": "ok", "notes_count": len(notes), "notes": notes})



@method_decorator(ratelimit(key=ratelimit_client_ip, rate='20/m', block=True), name='dispatch')
class MemoV2EditView(EditPasswordRequiredMixin, View):
    template_name = "tabisync/content/memo_v2.html"
    edit_redirect_url_name = "V2_memo_edit"

    @method_decorator(ensure_csrf_cookie)
    def get(self, request, pk, token):
        memo, _ = MemoV2.objects.get_or_create(itinerary=self.itinerary)
        notes = normalize_memo_v2_notes(memo.content)
        return render(request, self.template_name, {
            "memo": memo,
            "memo_notes": notes,
            "itinerary": self.itinerary,
            "can_edit_memo": True,
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

        limit_error = validate_memo_notes_limits(notes)
        if limit_error:
            return JsonResponse({"status": "error", "message": limit_error}, status=400)

        memo.content = json.dumps(notes, ensure_ascii=False)
        memo.save()
        return JsonResponse({"status": "ok", "notes_count": len(notes), "notes": notes})
