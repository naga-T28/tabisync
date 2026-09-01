import json
import urllib.error
import urllib.request

from django.conf import settings

from ..concierge_agent.errors import ToolExecutionError

PLACES_SEARCH_ENDPOINT = "https://places.googleapis.com/v1/places:searchText"
PLACES_SEARCH_TIMEOUT_SECONDS = 8
MAX_PLACE_SEARCH_RESULTS = 7
PLACES_FIELD_MASK = (
    "places.id,places.displayName,places.formattedAddress,"
    "places.location,places.rating,places.userRatingCount"
)


def _serialize_place(place):
    display_name = place.get("displayName") or {}
    location = place.get("location") or {}
    return {
        "place_id": str(place.get("id") or ""),
        "name": str(display_name.get("text") or ""),
        "address": str(place.get("formattedAddress") or ""),
        "lat": location.get("latitude"),
        "lng": location.get("longitude"),
        "rating": place.get("rating"),
        "user_rating_count": place.get("userRatingCount"),
    }


def search_places(run_context, query):
    """Google Places API (Text Search)でキーワード検索し、最大MAX_PLACE_SEARCH_RESULTS件を返す。
    保存は行わない(side_effect: none) — 追加はpropose_changesのwant_create経由。"""
    api_key = (getattr(settings, "GOOGLE_MAPS_API_KEY", "") or "").strip()
    if not api_key:
        raise ToolExecutionError("search_places", "not_configured", "地点検索が利用できません。")

    query_text = str(query or "").strip()
    if not query_text:
        raise ToolExecutionError("search_places", "invalid_query", "検索キーワードが空です。")

    payload = {
        "textQuery": query_text[:200],
        "maxResultCount": MAX_PLACE_SEARCH_RESULTS,
        "languageCode": "ja",
    }
    request = urllib.request.Request(
        PLACES_SEARCH_ENDPOINT,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "X-Goog-Api-Key": api_key,
            "X-Goog-FieldMask": PLACES_FIELD_MASK,
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=PLACES_SEARCH_TIMEOUT_SECONDS) as response:
            raw = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        raise ToolExecutionError("search_places", "api_error", "地点検索でエラーが発生しました。") from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise ToolExecutionError("search_places", "timeout", "地点検索がタイムアウトしました。") from exc

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ToolExecutionError("search_places", "invalid_response", "地点検索の応答を解釈できませんでした。") from exc

    places = parsed.get("places") if isinstance(parsed, dict) else None
    if not isinstance(places, list):
        places = []

    return {"places": [_serialize_place(place) for place in places[:MAX_PLACE_SEARCH_RESULTS] if isinstance(place, dict)]}
