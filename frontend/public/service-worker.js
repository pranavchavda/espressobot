
// Service Worker for PWA functionality
const CACHE_NAME = 'shopify-agent-v1';
const urlsToCache = [
  '/',
  '/index.html',
  '/static/output.css',
  '/static/shopify_assistant_logo.png',
  '/static/favicon.ico'
];

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => {
        return cache.addAll(urlsToCache);
      })
  );
});

self.addEventListener('fetch', event => {
  // Skip caching for API requests and SSE streams
  const url = new URL(event.request.url);
  
  // Skip caching for chrome-extension, moz-extension, and other unsupported schemes
  const unsupportedSchemes = ['chrome-extension', 'moz-extension', 'safari-extension', 'ms-browser-extension'];
  
  if (unsupportedSchemes.includes(url.protocol.replace(':', ''))) {
    console.log('[ServiceWorker] Skipping unsupported URL scheme:', url.protocol, url.href);
    return; // Let the browser handle it normally
  }
  
  // Don't cache API calls, especially streaming endpoints
  if (url.pathname.startsWith('/api/')) {
    return;
  }
  
  // Don't cache SSE or streaming responses
  if (event.request.headers.get('accept') === 'text/event-stream') {
    return;
  }
  
  // Also skip non-HTTP schemes and cross-origin requests
  if (!['http', 'https'].includes(url.protocol.replace(':', '')) || 
      (url.origin !== self.location.origin && !event.request.url.startsWith(self.location.origin))) {
    return; // Let the browser handle it normally
  }
  
  event.respondWith(
    caches.match(event.request)
      .then(response => {
        // Cache hit - return response
        if (response) {
          return response;
        }
        return fetch(event.request).then(
          response => {
            // Check if we received a valid response
            if(!response || response.status !== 200 || response.type !== 'basic') {
              return response;
            }

            // Additional check - don't cache if response URL has unsupported scheme
            const responseUrl = new URL(response.url);
            if (unsupportedSchemes.includes(responseUrl.protocol.replace(':', ''))) {
              return response;
            }

            // Clone the response
            const responseToCache = response.clone();

            caches.open(CACHE_NAME)
              .then(cache => {
                cache.put(event.request, responseToCache);
              })
              .catch(error => {
                console.warn('[ServiceWorker] Failed to cache response:', error, event.request.url);
              });

            return response;
          }
        ).catch(error => {
          console.warn('[ServiceWorker] Fetch failed:', error, event.request.url);
          throw error;
        });
      })
  );
});

self.addEventListener('activate', event => {
  const cacheWhitelist = [CACHE_NAME];
  event.waitUntil(
    caches.keys().then(cacheNames => {
      return Promise.all(
        cacheNames.map(cacheName => {
          if (cacheWhitelist.indexOf(cacheName) === -1) {
            return caches.delete(cacheName);
          }
        })
      );
    })
  );
});
