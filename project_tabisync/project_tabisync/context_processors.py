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
