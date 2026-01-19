const CACHE_NAME = "tabisync-cache-v1";
const OFFLINE_URL = "/offline/";

self.addEventListener("install", event => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache =>
      cache.addAll([
        OFFLINE_URL
      ])
    )
  );
  self.skipWaiting();
});

self.addEventListener("activate", event => {
  event.waitUntil(clients.claim());
});

self.addEventListener("fetch", event => {
  const url = new URL(event.request.url);
  const pathname = url.pathname;

  const itineraryPattern = /^\/content\/\d+\/[0-9a-fA-F-]+(\/(memo|list))?\/?$/;

  if (itineraryPattern.test(pathname)) {
    // キャッシュ優先
    event.respondWith(
      caches.match(event.request).then(response => {
        return response || fetch(event.request).then(networkResponse => {
          return caches.open(CACHE_NAME).then(cache => {
            cache.put(event.request, networkResponse.clone());
            return networkResponse;
          });
        }).catch(() => caches.match(OFFLINE_URL));
      })
    );
  } else {
    // オフラインページにフォールバック
    event.respondWith(
      fetch(event.request).catch(() => caches.match(OFFLINE_URL))
    );
  }
});
