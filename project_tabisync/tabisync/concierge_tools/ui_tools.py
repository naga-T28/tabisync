from ..concierge_agent.errors import ToolExecutionError
from ..models import WantToGo
from ..views.itinerary_helpers import build_google_maps_search_url

MAX_MAP_PLACES = 8


def serialize_place_for_map(place):
    return {
        "id": place.id,
        "name": place.name,
        "address": place.address or "",
        "lat": place.latitude,
        "lng": place.longitude,
        "place_id": place.place_id or "",
        # Google Maps URLはモデルの自由記述ではなく、常にサーバー側でこの共通ヘルパーを使い組み立てる。
        "maps_url": build_google_maps_search_url(place),
    }


def show_map(run_context, want_to_go_ids, title):
    """指定されたWantToGo idのうち、現在のItineraryに属するものだけを地図表示対象にする。

    戻り値は (tool_result, ui_component) のタプル。ui_componentのplacesはserialize_place_for_map
    が返す構造化データ(id/name/address/lat/lng/place_id/maps_url)のみを持ち、任意HTMLや
    任意tile URLは含まない。フロントはこれをそのまま場所一覧・地図マーカーの描画に使う。
    """
    itinerary = run_context.itinerary
    requested_ids = [
        value for value in (want_to_go_ids or [])
        if isinstance(value, int) and not isinstance(value, bool)
    ][:MAX_MAP_PLACES]

    places = list(WantToGo.objects.filter(itinerary=itinerary, pk__in=requested_ids))
    order_index = {place_id: index for index, place_id in enumerate(requested_ids)}
    places.sort(key=lambda place: order_index.get(place.id, len(requested_ids)))

    if not places:
        raise ToolExecutionError("show_map", "no_places_found", "対象の場所が見つかりませんでした。")

    serialized_places = [serialize_place_for_map(place) for place in places]
    tool_result = {"places": serialized_places}
    ui_component = {
        "type": "map",
        "title": (str(title or "").strip()[:60]) or "地図",
        "want_to_go_ids": [place.id for place in places],
        "places": serialized_places,
    }
    return tool_result, ui_component
