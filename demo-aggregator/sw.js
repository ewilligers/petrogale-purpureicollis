'use strict';

self.addEventListener('fetch', function(event) {
  event.respondWith(
    caches.match(event.request)
      .then(function(response) {
        // Cache hit - return response
        if (response) {
          return response;
        }
        console.log('Fetching');
        return fetch(event.request);
      }
    )
  );
});
