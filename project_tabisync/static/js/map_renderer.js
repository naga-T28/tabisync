/*
 * Map Display Adapter (Task 002)
 *
 * 可視地図の描画をprovider実装から分離する。呼び出し側(want_list.html/concierge_v2.html)は
 * 保存済みの id/name/address/lat/lng/planned_day などの構造化データだけを渡し、
 * providerが返すHTMLやtile URLを直接扱わない。
 *
 * providerの切り替えは window.TABISYNC_MAP_CONFIG (サーバー設定由来、利用者入力からは
 * 変更不可)のみで行い、テンプレート側の分岐は増やさない。
 *
 * classic <script> として読み込む(既存画面がすべてグローバル関数前提のため)。
 * MapLibre GL JS本体はESM配布のみのため、内部で dynamic import() を使って読み込む。
 *
 * 将来CSPヘッダを導入する場合に必要となるorigin:
 *   script-src 'self'; style-src 'self'; worker-src 'self';
 *   connect-src 'self' https://tiles.openfreemap.org;
 *   img-src 'self' https://tiles.openfreemap.org data:;
 * (workerはmaplibregl.setWorkerUrl()で自ドメイン固定のため blob: は不要)
 */
(function () {
  "use strict";

  var MAPLIBRE_MODULE_URL = new URL("./vendor/maplibre-gl/maplibre-gl.mjs", document.currentScript.src).href;
  var DEFAULT_CENTER = { lat: 35.681236, lng: 139.767125 };
  var DEFAULT_ZOOM = 4;
  var LOAD_TIMEOUT_MS = 8000;

  var maplibreModulePromise = null;

  function loadMapLibre(workerUrl) {
    if (!maplibreModulePromise) {
      // maplibre-gl@6のESM distはdefault exportを持たず、名前付きexportのみを提供する
      // (import maplibregl from '...' は mod.default===undefined になり壊れる)。
      // dynamic import()が返すmodule namespace object自体をAPIオブジェクトとして扱う。
      maplibreModulePromise = import(MAPLIBRE_MODULE_URL).then(function (maplibregl) {
        if (workerUrl) {
          maplibregl.setWorkerUrl(workerUrl);
        }
        return maplibregl;
      });
    }
    return maplibreModulePromise;
  }

  function isValidCoordinate(lat, lng) {
    return (
      typeof lat === "number" && Number.isFinite(lat) && lat >= -90 && lat <= 90 &&
      typeof lng === "number" && Number.isFinite(lng) && lng >= -180 && lng <= 180
    );
  }

  function isTrustedHttpsUrl(value) {
    return typeof value === "string" && /^https:\/\//.test(value);
  }

  function buildMarkerElement(place, markerStyle, onMarkerClick) {
    var el = document.createElement("button");
    el.type = "button";
    el.className = "tabisync-map-marker";
    el.setAttribute("aria-label", place.name || "");
    var style = (typeof markerStyle === "function" && markerStyle(place)) || {};
    el.style.backgroundColor = style.color || "#2f3747";
    if (onMarkerClick) {
      el.addEventListener("click", function () {
        onMarkerClick(place);
      });
    }
    return el;
  }

  function createMockRenderer(container, geoPlaces) {
    container.textContent = "";
    container.dataset.mapProvider = "mock";

    function toMockMarkers(places) {
      return places.map(function (place) {
        return { place: place, setVisible: function () {} };
      });
    }

    var handle = {
      markers: toMockMarkers(geoPlaces),
      fitToMarkers: function () {},
      setPlaces: function (newPlaces) {
        var nextGeoPlaces = (Array.isArray(newPlaces) ? newPlaces : []).filter(function (place) {
          return isValidCoordinate(place.lat, place.lng);
        });
        handle.markers = toMockMarkers(nextGeoPlaces);
        return handle.markers;
      },
      destroy: function () {},
    };
    return Promise.resolve(handle);
  }

  function createMapRenderer(container, options) {
    options = options || {};
    var places = Array.isArray(options.places) ? options.places : [];
    var onMarkerClick = options.onMarkerClick;
    var markerStyle = options.markerStyle;
    var fallback = options.fallback;

    var geoPlaces = places.filter(function (place) {
      return isValidCoordinate(place.lat, place.lng);
    });

    var config = window.TABISYNC_MAP_CONFIG || {};

    if (config.provider === "mock") {
      return createMockRenderer(container, geoPlaces);
    }

    if (!isTrustedHttpsUrl(config.styleUrl)) {
      if (fallback) fallback();
      return Promise.reject(new Error("map style is not configured"));
    }

    return loadMapLibre(config.workerUrl)
      .catch(function (err) {
        if (fallback) fallback();
        throw err;
      })
      .then(function (maplibregl) {
        // geoPlaces/currentMarkersはsetPlaces()で入れ替え可能なmutable stateとして持つ
        // (Task 003: 日タブ切替のたびにMap本体・style・WebGL contextを再生成しないため)。
        var currentGeoPlaces = geoPlaces;
        var currentMarkers = [];

        var initialCenter = currentGeoPlaces.length
          ? [currentGeoPlaces[0].lng, currentGeoPlaces[0].lat]
          : [DEFAULT_CENTER.lng, DEFAULT_CENTER.lat];
        var map = new maplibregl.Map({
          container: container,
          style: config.styleUrl,
          center: initialCenter,
          zoom: currentGeoPlaces.length ? 12 : DEFAULT_ZOOM,
          attributionControl: false,
        });
        map.addControl(
          new maplibregl.AttributionControl({
            compact: false,
            customAttribution: "© OpenStreetMap contributors",
          })
        );

        function buildMarkers(places) {
          return places.map(function (place) {
            var el = buildMarkerElement(place, markerStyle, onMarkerClick);
            var marker = new maplibregl.Marker({ element: el }).setLngLat([place.lng, place.lat]).addTo(map);
            return {
              place: place,
              setVisible: function (visible) {
                el.style.display = visible ? "" : "none";
              },
              _marker: marker,
            };
          });
        }

        currentMarkers = buildMarkers(currentGeoPlaces);

        function fitToMarkers() {
          if (currentGeoPlaces.length === 0) return;
          if (currentGeoPlaces.length === 1) {
            map.setCenter([currentGeoPlaces[0].lng, currentGeoPlaces[0].lat]);
            map.setZoom(14);
            return;
          }
          var bounds = new maplibregl.LngLatBounds(
            [currentGeoPlaces[0].lng, currentGeoPlaces[0].lat],
            [currentGeoPlaces[0].lng, currentGeoPlaces[0].lat]
          );
          currentGeoPlaces.forEach(function (place) {
            bounds.extend([place.lng, place.lat]);
          });
          map.fitBounds(bounds, { padding: 48, maxZoom: 16 });
        }

        function setPlaces(newPlaces) {
          var nextGeoPlaces = (Array.isArray(newPlaces) ? newPlaces : []).filter(function (place) {
            return isValidCoordinate(place.lat, place.lng);
          });

          currentMarkers.forEach(function (marker) {
            marker._marker.remove();
          });

          currentGeoPlaces = nextGeoPlaces;
          currentMarkers = buildMarkers(currentGeoPlaces);
          rendererHandle.markers = currentMarkers;

          // 非表示状態から復帰した直後は前回のcanvasサイズを引きずるため、
          // resizeしてからfitさせて欠け・中心ずれを防ぐ。
          map.resize();
          fitToMarkers();

          return currentMarkers;
        }

        var rendererHandle = null;

        return new Promise(function (resolve, reject) {
          var settled = false;

          var timeoutId = window.setTimeout(function () {
            if (settled) return;
            settled = true;
            if (fallback) fallback();
            reject(new Error("map load timeout"));
          }, LOAD_TIMEOUT_MS);

          map.on("load", function () {
            if (settled) return;
            settled = true;
            window.clearTimeout(timeoutId);
            fitToMarkers();
            rendererHandle = {
              markers: currentMarkers,
              fitToMarkers: fitToMarkers,
              setPlaces: setPlaces,
              destroy: function () {
                currentMarkers.forEach(function (marker) {
                  marker._marker.remove();
                });
                map.remove();
              },
            };
            resolve(rendererHandle);
          });

          map.on("error", function (event) {
            if (settled) return;
            settled = true;
            window.clearTimeout(timeoutId);
            if (fallback) fallback();
            reject((event && event.error) || new Error("map error"));
          });
        });
      });
  }

  window.createMapRenderer = createMapRenderer;
})();
