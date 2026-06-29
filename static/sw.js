const CACHE_NAME = 'inktracker-v2';
const STATIC_ASSETS = [
  '/static/app.css',
  '/static/vendor/alpine.min.js',
  '/static/vendor/chart.umd.min.js',
  '/static/vendor/jsqr.js',
];

// Offline fallback page
const OFFLINE_HTML = `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>InkTrack — Offline</title>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
           background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
           min-height: 100vh; display: flex; align-items: center; justify-content: center; padding: 20px; }
    .container { background: white; border-radius: 12px; padding: 40px; 
                 text-align: center; box-shadow: 0 20px 60px rgba(0,0,0,0.2); max-width: 400px; }
    h1 { color: #1e293b; font-size: 28px; margin-bottom: 16px; }
    p { color: #64748b; font-size: 16px; margin-bottom: 24px; line-height: 1.5; }
    .icon { font-size: 64px; margin-bottom: 16px; }
    .button { display: inline-block; background: #4f46e5; color: white; 
              padding: 12px 24px; border-radius: 6px; text-decoration: none; 
              font-weight: 600; margin-top: 16px; border: none; cursor: pointer; }
    .button:hover { background: #4338ca; }
  </style>
</head>
<body>
  <div class="container">
    <div class="icon">📶</div>
    <h1>You're Offline</h1>
    <p>InkTrack is not available while offline. Please check your connection and try again.</p>
    <button class="button" onclick="location.reload()">Retry</button>
  </div>
</body>
</html>`;

// Install: cache static assets
self.addEventListener('install', (event) => {
  console.log('[SW] Installing service worker v1...');
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      console.log('[SW] Caching static assets');
      return cache.addAll(STATIC_ASSETS).catch((err) => {
        console.warn('[SW] Warning: Some static assets failed to cache (this is OK if CSS is not yet built by CI):', err.message);
      });
    })
  );
  self.skipWaiting();
});

// Activate: clean up old caches and claim clients
self.addEventListener('activate', (event) => {
  console.log('[SW] Activating...');
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames
          .filter((name) => name !== CACHE_NAME)
          .map((name) => {
            console.log('[SW] Deleting old cache:', name);
            return caches.delete(name);
          })
      );
    })
  );
  self.clients.claim();
});

// Fetch: network-first for HTML, cache-first for static assets
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Skip non-GET or cross-origin requests
  if (request.method !== 'GET' || url.origin !== self.location.origin) {
    return;
  }

  // Strategy 1: For HTML pages (navigation), use network-first with offline fallback
  if (request.mode === 'navigate' || url.pathname === '/') {
    event.respondWith(
      fetch(request)
        .then((response) => {
          if (response && response.status === 200) {
            // Cache successful HTML responses
            const responseClone = response.clone();
            caches.open(CACHE_NAME).then((cache) => {
              cache.put(request, responseClone);
            });
            return response;
          }
          return response;
        })
        .catch(() => {
          console.log('[SW] Network failed for', url.pathname, '— showing offline page');
          return new Response(OFFLINE_HTML, {
            headers: { 'Content-Type': 'text/html' },
          });
        })
    );
    return;
  }

  // Strategy 2: For static assets, use cache-first with network fallback
  if (url.pathname.startsWith('/static/')) {
    event.respondWith(
      caches.match(request).then((response) => {
        if (response) {
          return response;
        }
        return fetch(request).then((response) => {
          if (!response || response.status !== 200) {
            return response;
          }
          const responseClone = response.clone();
          caches.open(CACHE_NAME).then((cache) => {
            cache.put(request, responseClone);
          });
          return response;
        }).catch(() => {
          console.log('[SW] Static asset failed:', url.pathname);
          // Return a minimal response rather than failing completely
          return new Response('', { status: 503 });
        });
      })
    );
    return;
  }

  // Strategy 3: For API calls and other routes, use network-first
  event.respondWith(
    fetch(request)
      .then((response) => {
        if (response && response.status === 200) {
          const responseClone = response.clone();
          caches.open(CACHE_NAME).then((cache) => {
            cache.put(request, responseClone);
          });
        }
        return response;
      })
      .catch(() => {
        console.log('[SW] Network request failed:', url.pathname);
        return caches.match(request).then((response) => {
          if (response) {
            return response;
          }
          // If nothing is cached, show offline page
          return new Response(OFFLINE_HTML, {
            headers: { 'Content-Type': 'text/html' },
          });
        });
      })
  );
});
