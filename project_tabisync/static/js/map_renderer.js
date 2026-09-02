/*
 * Map Display Adapter
 *
 * 可視地図の描画をprovider実装から分離する。呼び出し側(want_list.html/content.html/
 * concierge_v2.html)は保存済みの id/name/address/lat/lng/planned_day などの構造化データ
 * だけを渡し、providerが返すHTMLやオブジェクトを直接扱わない。
 *
 * providerは window.TABISYNC_MAP_CONFIG (サーバー設定由来、利用者入力からは変更不可)の
 * みで切り替え、テンプレート側の分岐は増やさない。実体はGoogle Maps JavaScript APIで、
 * 各ページが読み込む `<script src="https://maps.googleapis.com/maps/api/js?...">` が
 * window.google.maps を用意するまで待ってから地図を生成する。
 *
 * classic <script> として読み込む(既存画面がすべてグローバル関数前提のため)。
 */
(function () {
  "use strict";

  var DEFAULT_CENTER = { lat: 35.681236, lng: 139.767125 };
  var DEFAULT_ZOOM = 4;
  var LOAD_TIMEOUT_MS = 8000;
  var POLL_INTERVAL_MS = 100;

  var googleMapsReadyPromise = null;

  function isGoogleMapsReady() {
    return !!(window.google && window.google.maps && window.google.maps.Map);
  }

  function loadGoogleMaps() {
    if (isGoogleMapsReady()) return Promise.resolve(window.google.maps);
    if (!googleMapsReadyPromise) {
      googleMapsReadyPromise = new Promise(function (resolve, reject) {
        var elapsed = 0;
        var intervalId = window.setInterval(function () {
          if (isGoogleMapsReady()) {
            window.clearInterval(intervalId);
            resolve(window.google.maps);
            return;
          }
          elapsed += POLL_INTERVAL_MS;
          if (elapsed >= LOAD_TIMEOUT_MS) {
            window.clearInterval(intervalId);
            reject(new Error("Google Maps JavaScript API failed to load"));
          }
        }, POLL_INTERVAL_MS);
      });
    }
    return googleMapsReadyPromise;
  }

  function isValidCoordinate(lat, lng) {
    return (
      typeof lat === "number" && Number.isFinite(lat) && lat >= -90 && lat <= 90 &&
      typeof lng === "number" && Number.isFinite(lng) && lng >= -180 && lng <= 180
    );
  }

  function buildMarkerIcon(googleMaps, markerStyle, place) {
    var style = (typeof markerStyle === "function" && markerStyle(place)) || {};
    var color = style.color || "#2f3747";
    var svg = '<svg xmlns="http://www.w3.org/2000/svg" width="26" height="26">' +
      '<circle cx="13" cy="13" r="10" fill="' + color + '" stroke="#ffffff" stroke-width="2"/>' +
      "</svg>";
    return {
      url: "data:image/svg+xml;charset=UTF-8," + encodeURIComponent(svg),
      scaledSize: new googleMaps.Size(26, 26),
      anchor: new googleMaps.Point(13, 13),
    };
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

    return loadGoogleMaps()
      .catch(function (err) {
        if (fallback) fallback();
        throw err;
      })
      .then(function (googleMaps) {
        // geoPlaces/currentMarkersはsetPlaces()で入れ替え可能なmutable stateとして持つ
        // (日タブ切替のたびにMap本体を再生成しないため)。
        var currentGeoPlaces = geoPlaces;
        var currentMarkers = [];

        var initialCenter = currentGeoPlaces.length
          ? { lat: currentGeoPlaces[0].lat, lng: currentGeoPlaces[0].lng }
          : DEFAULT_CENTER;

        var map = new googleMaps.Map(container, {
          center: initialCenter,
          zoom: currentGeoPlaces.length ? 12 : DEFAULT_ZOOM,
          mapTypeControl: false,
          streetViewControl: false,
          fullscreenControl: false,
        });

        function buildMarkers(places) {
          return places.map(function (place) {
            var marker = new googleMaps.Marker({
              position: { lat: place.lat, lng: place.lng },
              map: map,
              title: place.name || "",
              icon: buildMarkerIcon(googleMaps, markerStyle, place),
            });
            if (onMarkerClick) {
              marker.addListener("click", function () {
                onMarkerClick(place);
              });
            }
            return {
              place: place,
              setVisible: function (visible) {
                marker.setVisible(visible);
              },
              _marker: marker,
            };
          });
        }

        currentMarkers = buildMarkers(currentGeoPlaces);

        function fitToMarkers() {
          if (currentGeoPlaces.length === 0) return;
          if (currentGeoPlaces.length === 1) {
            map.setCenter({ lat: currentGeoPlaces[0].lat, lng: currentGeoPlaces[0].lng });
            map.setZoom(14);
            return;
          }
          var bounds = new googleMaps.LatLngBounds();
          currentGeoPlaces.forEach(function (place) {
            bounds.extend({ lat: place.lat, lng: place.lng });
          });
          map.fitBounds(bounds, 48);
        }

        function setPlaces(newPlaces) {
          var nextGeoPlaces = (Array.isArray(newPlaces) ? newPlaces : []).filter(function (place) {
            return isValidCoordinate(place.lat, place.lng);
          });

          currentMarkers.forEach(function (marker) {
            marker._marker.setMap(null);
          });

          currentGeoPlaces = nextGeoPlaces;
          currentMarkers = buildMarkers(currentGeoPlaces);
          rendererHandle.markers = currentMarkers;

          // 非表示状態から復帰した直後は前回のcanvasサイズを引きずるため、
          // resizeイベントを発火してからfitさせて欠け・中心ずれを防ぐ。
          googleMaps.event.trigger(map, "resize");
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

          googleMaps.event.addListenerOnce(map, "idle", function () {
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
                  marker._marker.setMap(null);
                });
                googleMaps.event.clearInstanceListeners(map);
                container.textContent = "";
              },
            };
            resolve(rendererHandle);
          });
        });
      });
  }

  window.createMapRenderer = createMapRenderer;
})();
