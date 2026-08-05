import json

from django.db.models import Case, IntegerField, Value, When
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView
from django_ratelimit.decorators import ratelimit

from ..models import Itinerary, WantToGo
from .itinerary_helpers import apply_want_to_go_payload, build_want_to_go_limit_message, can_add_want_to_go, get_want_to_go_limit
from .utils import ratelimit_client_ip


# 行きたい場所リスト表示
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
        context["want_to_go_limit"] = get_want_to_go_limit(itinerary)

        return context
    
    def post(self, request, *args, **kwargs):
        pk = self.kwargs.get("pk")
        token = self.kwargs.get("token")

        data = json.loads(request.body)
        action = data.get("action")

        itinerary = get_object_or_404(Itinerary, pk=pk, token=token)

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
@method_decorator(ratelimit(key=ratelimit_client_ip, rate='20/m', block=True), name='dispatch')
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
        context["want_to_go_limit"] = get_want_to_go_limit(itinerary)

        return context


    def post(self, request, *args, **kwargs):
        pk = self.kwargs.get("pk")
        token = self.kwargs.get("token")

        data = json.loads(request.body)
        action = data.get("action")

        itinerary = get_object_or_404(Itinerary, pk=pk, token=token)

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

