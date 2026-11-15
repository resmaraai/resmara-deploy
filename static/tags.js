/* Tracking tags, loaded from the server so the id lives in exactly one place.
 *
 * Why this file exists: the homepage had no Google tag and no Clarity, so nothing could ever
 * measure a visitor - the Website and Marketing pages would have stayed empty even with every
 * key in the world. Pasting a snippet into index.html would work until somebody edits it and the
 * id goes stale in two places, so the ids come from /api/public/tags (neither is a secret) and the
 * System page reads the same endpoint to tell you whether tracking is on.
 *
 * Unset = no tag injected, and nothing else changes. Failures are silent by design: a tracking
 * script must never break the page it is measuring.
 */
(function () {
  'use strict';

  function ga4(id) {
    if (!/^G-[A-Z0-9]+$/i.test(id)) return;            // a wrong id would 404 on every page view
    var s = document.createElement('script');
    s.async = true;
    s.src = 'https://www.googletagmanager.com/gtag/js?id=' + encodeURIComponent(id);
    document.head.appendChild(s);
    window.dataLayer = window.dataLayer || [];
    window.gtag = window.gtag || function () { window.dataLayer.push(arguments); };
    window.gtag('js', new Date());
    window.gtag('config', id, { anonymize_ip: true });
  }

  function clarity(id) {
    if (!/^[a-z0-9]{6,}$/i.test(id)) return;
    (function (c, l, a, r, i, t, y) {
      c[a] = c[a] || function () { (c[a].q = c[a].q || []).push(arguments); };
      t = l.createElement(r); t.async = 1; t.src = 'https://www.clarity.ms/tag/' + i;
      y = l.getElementsByTagName(r)[0]; y.parentNode.insertBefore(t, y);
    })(window, document, 'clarity', 'script', id);
  }

  try {
    fetch('/api/public/tags', { headers: { Accept: 'application/json' } })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (t) {
        if (!t) return;
        if (t.ga4) ga4(t.ga4);
        if (t.clarity) clarity(t.clarity);
      })
      .catch(function () { /* measuring is never worth breaking the page for */ });
  } catch (e) { /* no fetch, no tracking, still a working site */ }
})();
