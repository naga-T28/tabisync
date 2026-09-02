from django.conf import settings
from django.db.models import Q
from django.utils import timezone


def announcement(request):
    match = request.resolver_match
    url_name = getattr(match, "url_name", None) if match else None

    qs = None
    if url_name == "home":
        qs = _base_announcement_queryset().filter(show_on_home=True)
    elif url_name == "content_v2":
        pk = match.kwargs.get("pk")
        qs = _base_announcement_queryset().filter(
            Q(show_on_all_itineraries=True) | Q(itineraries__id=pk)
        )

    if qs is None:
        return {"active_announcement": None}

    active = qs.order_by("-updated_at").distinct().first()
    return {"active_announcement": active}


def _base_announcement_queryset():
    # importをここに置くのは、context_processors.pyがsettings読み込み時に
    # 評価されるモジュールであり、tabisync.modelsとの循環importを避けるため。
    from tabisync.models import SiteAnnouncement

    now = timezone.now()
    return SiteAnnouncement.objects.filter(is_active=True).filter(
        Q(starts_at__isnull=True) | Q(starts_at__lte=now)
    ).filter(
        Q(ends_at__isnull=True) | Q(ends_at__gte=now)
    )


def google_maps(request):
    return {
        "google_maps_api_key": getattr(settings, "GOOGLE_MAPS_API_KEY", "") or "",
    }


def map_display(request):
    return {
        "map_display_config": {
            "provider": getattr(settings, "MAP_DISPLAY_PROVIDER", "google") or "google",
        },
    }


def seo(request):
    # canonical・OGP・構造化データ・サイトマップが参照する単一の公開オリジン。
    # request.get_host()を使わないのは、ALLOWED_HOSTSに含まれる別Hostや
    # プロキシ設定差でcanonicalが分散するのを防ぐため。
    return {
        "public_base_url": settings.PUBLIC_BASE_URL,
    }
