const CACHE_PREFIX = 'gas-quotecard-';
const CACHE = 'gas-quotecard-wrapper-v2';
const ASSETS = [
  './manifest.webmanifest',
  './apple-touch-icon.png',
  './icon-192.png',
  './icon-512.png'
];

function isWrapperShellRequest(request, url) {
  return request.mode === 'navigate' || url.pathname === '/' || url.pathname.endsWith('/index.html');
}

function fetchAndCache(request) {
  return fetch(request).then(response => {
    if (response && response.ok) {
      const clone = response.clone();
      caches.open(CACHE).then(cache => cache.put(request, clone)).catch(() => undefined);
    }
    return response;
  });
}

self.addEventListener('install', event => {
  event.waitUntil(caches.open(CACHE).then(cache => cache.addAll(ASSETS)).catch(() => undefined));
  self.skipWaiting();
});

self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys()
      .then(keys => Promise.all(
        keys
          .filter(key => key.startsWith(CACHE_PREFIX) && key !== CACHE)
          .map(key => caches.delete(key))
      ))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', event => {
  const url = new URL(event.request.url);
  if (url.hostname === 'script.google.com' || url.hostname.endsWith('.googleusercontent.com')) return;
  if (url.pathname.endsWith('/config.js') || url.pathname.endsWith('/sw.js') || isWrapperShellRequest(event.request, url)) {
    event.respondWith(fetchAndCache(event.request).catch(() => caches.match(event.request)));
    return;
  }
  event.respondWith(caches.match(event.request).then(cached => cached || fetchAndCache(event.request)));
});
