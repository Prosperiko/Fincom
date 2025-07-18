const CACHE_NAME = 'fincom-cache-v2';

const urlsToCache = [
  '/',                // root/homepage
  '/home1',
  '/community',
  '/chatbox',
  '/expenses',
  '/income',
  '/analysis',
  '/budget',
  '/all_transactions',
  '/offline',         // fallback route
  '/static/css/style.css',
  '/static/js/main.js',
  // Add more assets if needed (fonts, logos, icons, etc.)
];

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => cache.addAll(urlsToCache))
  );
});

self.addEventListener('fetch', event => {
  event.respondWith(
    fetch(event.request).catch(() =>
      caches.match(event.request).then(response =>
        response || caches.match('/offline')
      )
    )
  );
});
