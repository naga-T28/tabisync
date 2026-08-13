from django.conf import settings


def google_maps(request):
    return {
        "google_maps_api_key": getattr(settings, "GOOGLE_MAPS_API_KEY", "") or "",
    }


def map_display(request):
    return {
        "map_display_config": {
            "provider": getattr(settings, "MAP_DISPLAY_PROVIDER", "openfreemap") or "openfreemap",
            "styleUrl": getattr(settings, "MAP_STYLE_URL", "") or "",
            "tileUrl": getattr(settings, "MAP_TILE_URL", "") or "",
        },
    }


def seo(request):
    # canonical・OGP・構造化データ・サイトマップが参照する単一の公開オリジン。
    # request.get_host()を使わないのは、ALLOWED_HOSTSに含まれる別Hostや
    # プロキシ設定差でcanonicalが分散するのを防ぐため。
    return {
        "public_base_url": settings.PUBLIC_BASE_URL,
    }
