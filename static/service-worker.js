const CACHE_NAME = 'fincom-cache-v2';

const urlsToCache = [
  '/',
  '/login',
  '/verify_pin',                // root/homepage
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
// Install event
self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(urlsToCache);
    })
  );
});
// Fetch event
self.addEventListener("fetch", (event) => {
  event.respondWith(
    caches.match(event.request).then((response) => {
      return response || fetch(event.request);
    })
  );
});
