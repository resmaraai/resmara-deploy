/* Resmara API client.
 *
 * One small, dependency-free ES2020 browser client for the Resmara backend.
 * Loaded before the UI scripts (see index.html); exposes window.RM.
 *
 * Rules this file lives by:
 *  - every path is written WITHOUT the mount prefix ("/api/boosts") and the prefix is
 *    detected at load time from where this file itself was served. Behind the Command
 *    Center router the app lives at /resmara, so a root-absolute "/api/boosts" resolves to
 *    the router's 404 long before it reaches this app: the request must go to
 *    "/resmara/api/boosts". Serving the app directly (127.0.0.1:8083) detects an empty
 *    prefix and the same call is right there too, so the deployment is never hard-coded;
 *  - the bearer token lives in localStorage and is sent only in the
 *    Authorization header - never in a URL or a query string;
 *  - a non-2xx response throws an Error carrying .status and the server's
 *    detail, so callers can tell a 401 from an offline failure;
 *  - nothing here touches the DOM or the app's state: it is transport only.
 */
(function () {
  'use strict';

  var TOKEN_KEY = 'resmara_token';

  // ---- mount prefix -------------------------------------------------------

  /* Where this app is mounted, so that "/api/..." reaches IT and not the router.
   * Read from api.js's own <script src>, falling back to the page location. Both forms
   * are handled: the browser's absolute URL and a plain path. Returns "" (served at the
   * root) or "/resmara" - no trailing slash, no guessing.
   */
  function detectBase() {
    var raw = '';
    try {
      if (typeof document !== 'undefined') {
        if (document.currentScript && document.currentScript.src) {
          raw = document.currentScript.src;
        } else if (document.scripts) {
          for (var i = document.scripts.length - 1; i >= 0; i--) {
            var src = (document.scripts[i] && document.scripts[i].src) || '';
            if (/\/api\.js(\?|$)/.test(src)) { raw = src; break; }
          }
        }
      }
    } catch (e) { raw = ''; }
    var isScript = !!raw;
    if (!raw) {
      try { raw = (typeof location !== 'undefined' && location.pathname) || ''; } catch (e) { raw = ''; }
    }
    var pathname = raw;
    try { pathname = new URL(raw, 'http://x/').pathname; } catch (e) { /* keep raw */ }
    pathname = isScript
      ? pathname.replace(/\/[^/]*$/, '')                     // .../api.js -> the directory
      : pathname.replace(/\/[^/]*\.[A-Za-z0-9]+$/, '');       // a page file -> its directory
    return pathname.replace(/\/+$/, '');
  }

  var BASE = detectBase();

  // Photos and other media the API hands us are root-absolute ("/uploads/<file>"), which is
  // right only when this app is served at the domain root. Mounted under a prefix — the
  // Command Center serves it at /resmara/ — "/uploads/x.jpg" asks the router for
  // /uploads/x.jpg, which has no route, so every real campaign photo renders as a broken
  // image while the bundled demo photos (page-relative "sample/card-1.jpg") keep working.
  // Prefix app paths with the detected mount; leave absolute URLs, data/blob URIs and
  // page-relative paths untouched, so the domain-root deploy is byte-for-byte unchanged.
  function mediaUrl(u) {
    if (!u) return u;
    var s = String(u);
    if (s.charAt(0) !== '/') return s;             // relative already, or data:/blob:/http:
    if (s.charAt(1) === '/') return s;             // protocol-relative //cdn...
    return BASE + s;
  }
  window.mediaUrl = mediaUrl;

  // ---- session / token ----------------------------------------------------

  function token() {
    try { return localStorage.getItem(TOKEN_KEY) || null; } catch (e) { return null; }
  }

  function setToken(t) {
    try {
      if (t) localStorage.setItem(TOKEN_KEY, t);
      else localStorage.removeItem(TOKEN_KEY);
    } catch (e) { /* storage unavailable: stay logged out */ }
    return t || null;
  }

  function logout() {
    setToken(null);
    return true;
  }

  /* A token that is past its own exp is not a session.
   *
   * Checking only "is there a string in localStorage?" meant a browser could sit for hours
   * holding a dead token, still call itself signed in, and hand the customer the server's
   * "Could not validate credentials" as though they had typed something wrong. Reading exp
   * here turns that into an honest sign-in prompt the caller can act on.
   */
  function payload(t) {
    try {
      var part = String(t || '').split('.')[1];
      if (!part) return null;
      var b64 = part.replace(/-/g, '+').replace(/_/g, '/');
      while (b64.length % 4) { b64 += '='; }
      return JSON.parse(atob(b64));
    } catch (e) { return null; }
  }

  function expired(t) {
    var p = payload(t || token());
    if (!p || !p.exp) return false;        // unreadable: let the server be the judge
    return p.exp * 1000 <= Date.now();
  }

  // One listener, so the UI can say "your session ended" in its own words and in its own place.
  var sessionLost = null;
  function onSessionLost(fn) { sessionLost = typeof fn === 'function' ? fn : null; }

  function endSession(notify) {
    var had = !!token();
    setToken(null);
    if (had && notify !== false) { try { if (sessionLost) sessionLost(); } catch (e) { /* a UI hook must never eat the error */ } }
    return true;
  }

  function isLoggedIn() {
    var t = token();
    if (!t) return false;
    // A token that has merely aged out is dropped quietly: the caller is about to say
    // "sign in" in its own words, and a toast on every page load is noise.
    if (expired(t)) { endSession(false); return false; }
    return true;
  }

  // The expiry this browser holds, so a screen can say when the session ends without guessing.
  function sessionExpiresAt() {
    var p = payload(token());
    return (p && p.exp) ? new Date(p.exp * 1000) : null;
  }

  // ---- low level ----------------------------------------------------------

  function authHeaders(extra) {
    var headers = Object.assign({}, extra || {});
    var t = token();
    if (t) headers['Authorization'] = 'Bearer ' + t;
    return headers;
  }

  async function parse(res) {
    var text = '';
    try { text = await res.text(); } catch (e) { text = ''; }
    var body = null;
    if (text) {
      try { body = JSON.parse(text); } catch (e) { body = text; }
    }
    if (!res.ok) {
      var detail;
      if (body && typeof body === 'object' && body.detail !== undefined) {
        detail = body.detail;                       // FastAPI's shaped error
      } else if (typeof body === 'string' && body && body.length <= 300 && body.indexOf('<') === -1) {
        detail = body;                              // a plain-text message
      } else {
        detail = 'HTTP ' + res.status;              // HTML/empty body: never dump markup at the user
      }
      var message = typeof detail === 'string' ? detail : JSON.stringify(detail);
      var err = new Error(message);
      err.status = res.status;
      err.detail = detail;
      err.body = body;
      throw err;
    }
    return body;
  }

  // opts: {method, headers, body}. Content-Type is set by the caller so that
  // multipart uploads let the browser choose the boundary.
  // The app's own page root, prefix included, so the health probe of a mounted deployment
  // asks the app for the app and not the router for '/'.
  function home() {
    return BASE + '/';
  }

  function request(path, opts) {
    opts = opts || {};
    var sentSession = !!token();
    return fetch(BASE + path, {
      method: opts.method || 'GET',
      headers: authHeaders(opts.headers),
      body: opts.body,
    }).then(parse).catch(function (err) {
      // A 401 on the login call is "wrong password", not "your session ended" - the two
      // must never be confused, because only one of them is the customer's to fix.
      if (err && err.status === 401 && sentSession && path !== '/api/auth/login') {
        // The server no longer accepts the token this browser holds. Drop it and say what
        // actually happened, instead of passing "Could not validate credentials" on as if
        // the customer had done something wrong.
        endSession();
        err.message = 'Your session ended — sign in again.';
      }
      throw err;
    });
  }

  function json(path, method, payload) {
    return request(path, {
      method: method,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
  }

  function segment(value) {
    return encodeURIComponent(value);
  }

  // ---- auth ---------------------------------------------------------------

  async function login(email, password) {
    var form = new URLSearchParams();
    form.set('username', email);
    form.set('password', password);
    var body = await request('/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: form,
    });
    if (body && body.access_token) setToken(body.access_token);
    return body;
  }

  // ---- "Log in with Facebook" (Engine 1 Part A) ---------------------------
  // The Terms box is ticked before any of this is called: the server refuses to start the
  // Facebook dialog without it, and the consent it records is what the new account is stamped
  // with. The redirect comes back as a one-time ticket, never as a token in the URL.
  function facebookStart(termsVersion) {
    return json('/api/auth/facebook/start', 'POST',
      { terms_accepted: true, terms_version: termsVersion || TERMS_VERSION });
  }

  function facebookExchange(ticket) {
    return json('/api/auth/facebook/exchange', 'POST', { ticket: ticket })
      .then(function (body) {
        if (body && body.access_token) setToken(body.access_token);
        return body;
      });
  }

  function facebookReactivate(ticket) {
    return json('/api/auth/facebook/reactivate', 'POST', { ticket: ticket })
      .then(function (body) {
        if (body && body.access_token) setToken(body.access_token);
        return body;
      });
  }

  // Facebook hid the email, so we ask once - for receipts, never to sign in.
  function setEmail(email) {
    return json('/api/auth/me/email', 'PATCH', { email: email });
  }

  // Close my account (Engine 10, section 10): everything stops, confirmed by typing the email.
  function closeAccount(email) {
    return json('/api/auth/me/close', 'POST', { email: email }).then(function (r) { logout(); return r; });
  }

  // Change together with the "Last updated" date on terms.html and privacy.html.
  var TERMS_VERSION = '2026-11-22';

  function register(email, password, name, inviteCode) {
    // invite_code is only sent when there is one: the open-signup path keeps the exact body
    // it always had, and the beta gate treats a missing code the same as an empty one.
    // terms_version: the Terms and Privacy Policy the agent ticked "I agree" to (Terms §1). The
    // server records it with the time and IP so the agreement can be proved later.
    var body = { email: email, password: password, name: name,
                 terms_accepted: true, terms_version: TERMS_VERSION };
    // Engine 9, section 1a: where this sign-up came from, captured from the link this browser
    // landed on. Stored in sessionStorage on the first page it sees, so an agent who lands on a
    // page without the query string and signs up three pages later still gets the stamp.
    var source = signupSource();
    if (source && Object.keys(source).length) body.source = source;
    if (inviteCode) body.invite_code = inviteCode;
    return json('/api/auth/register', 'POST', body);
  }

  // The attribution keys we understand. Anything else on the query string is not kept.
  var SOURCE_KEYS = ['utm_source', 'utm_medium', 'utm_campaign', 'utm_content', 'utm_term',
                     'fbclid', 'gclid', 'ad_id', 'campaign_id'];
  function signupSource() {
    var kept = {};
    try { kept = JSON.parse(sessionStorage.getItem('resmara_attribution') || '{}') || {}; } catch (e) { kept = {}; }
    try {
      var query = new URLSearchParams(location.search);
      SOURCE_KEYS.forEach(function (k) { if (query.get(k)) kept[k] = String(query.get(k)).slice(0, 200); });
      if (!kept.landing) kept.landing = location.pathname;
      if (!kept.referrer && document.referrer && document.referrer.indexOf(location.host) === -1) {
        kept.referrer = String(document.referrer).slice(0, 200);
      }
      sessionStorage.setItem('resmara_attribution', JSON.stringify(kept));
    } catch (e) { /* private mode: the query string still counts, it just is not remembered */ }
    return kept;
  }

  function me() {
    return request('/api/auth/me');
  }

  // Password recovery. The request call is deliberately unauthenticated and always answers
  // the same way; the answer's `delivery` is what the page reports ("email" / "not_configured"),
  // so a customer is never told a letter went out when no mail provider exists.
  function requestPasswordReset(email) {
    return request('/api/auth/password-reset/request?email=' + segment(String(email || '').trim()),
      { method: 'POST' });
  }

  function confirmPasswordReset(token, newPassword) {
    return request('/api/auth/password-reset/confirm?token=' + segment(token) +
      '&new_password=' + segment(newPassword), { method: 'POST' });
  }

  // Closing the account needs the password typed again; the server refuses operator accounts.
  function deleteAccount(password) {
    return request('/api/auth/me?password=' + segment(password), { method: 'DELETE' })
      .then(function (r) { logout(); return r; });
  }

  // ---- boosts (campaigns) -------------------------------------------------

  function boosts() {
    return request('/api/boosts');
  }

  function boost(id) {
    return request('/api/boosts/' + segment(id));
  }

  // Hiding and deleting are the two ways a customer clears their list. Hiding is reversible and
  // keeps the campaign and its report; deleting removes Resmara's copy of the campaign.
  function hideBoost(id, hidden) {
    return request('/api/boosts/' + segment(id) + '/hide?hidden=' + (hidden === false ? 'false' : 'true'),
      { method: 'POST' });
  }

  // "Run it until it sells" is a fact about the campaign, not a browser preference: the server
  // builds and charges the next round from this flag, so the toggle has to reach it. A campaign
  // whose listing is already pending or sold answers 409 with the sentence to show the agent.
  function setUntilSold(id, on) {
    // Turning it on carries the auto-renewal consent the agent just ticked (Terms §8), so the
    // server can keep proof of it; turning it off needs none.
    return request('/api/boosts/' + segment(id) + '/until-sold?until_sold=' + (on === false ? 'false' : 'true') +
        (on === false ? '' : '&renewal_consent=' + segment(TERMS_VERSION)),
      { method: 'POST' });
  }

  function deleteBoost(id) {
    return request('/api/boosts/' + segment(id), { method: 'DELETE' });
  }

  function createBoost(data) {
    data = data || {};
    return json('/api/boosts', 'POST', {
      address: data.address,
      go_live_date: data.go_live_date,
      campaign_days: data.campaign_days,
      ad_budget_usd: data.ad_budget_usd,
      property_facts: data.property_facts,
      ad_account_id: data.ad_account_id,
    });
  }

  // ---- content: uploads, assets, photo index ------------------------------

  function uploadPhoto(file, boostId, kind) {
    var form = new FormData();
    form.append('file', file);
    if (boostId !== undefined && boostId !== null) form.append('boost_id', String(boostId));
    form.append('kind', kind || 'photo');
    // No Content-Type: the browser adds the multipart boundary itself.
    return request('/api/content/upload/photo', { method: 'POST', body: form });
  }

  function assets(boostId) {
    return request('/api/content/assets/' + segment(boostId));
  }

  function photoIndex(boostId) {
    return request('/api/content/photo-index/' + segment(boostId));
  }

  // The gallery in the order the engine uses it (strongest-selling photo first), with the space
  // each photo shows — the photos panel reads this instead of raw upload order.
  function gallery(boostId) {
    return request('/api/content/gallery/' + segment(boostId));
  }

  // Pull a listing's gallery (or direct image URLs) into the campaign.
  function importPhotos(boostId, opts) {
    opts = opts || {};
    return json('/api/content/import/photos', 'POST', {
      boost_id: boostId,
      listing_url: opts.listingUrl || null,
      urls: opts.urls || [],
      limit: opts.limit || 60,
    });
  }

  // Open a listing link before a campaign is built: the home, its photo count and any video.
  // Take one scheduled post off a live campaign (the rest keeps running).
  function withdrawPost(postId) {
    return request('/api/posts/' + segment(postId) + '/withdraw', { method: 'PATCH' });
  }

  function checkListing(url) {
    return json('/api/content/listing/check', 'POST', { url: url });
  }

  function tagAssets(boostId) {
    return request('/api/content/assets/' + segment(boostId) + '/tag', { method: 'POST' });
  }

  // ---- content generation -------------------------------------------------

  var GENERATE_FIELDS = [
    'boost_id', 'agent_name', 'phone', 'license_no', 'brokerage', 'instagram',
    'website', 'property_website', 'beds', 'baths', 'sqft', 'city', 'feature',
    'cta', 'notes', 'force',
  ];

  function generateContent(fields) {
    fields = fields || {};
    var form = new FormData();
    GENERATE_FIELDS.forEach(function (key) {
      var value = fields[key];
      if (value === undefined || value === null || value === '') return;
      form.append(key, String(value));
    });
    return request('/api/content/generate/content', { method: 'POST', body: form });
  }

  // ---- engine: build / plan / posts / approval ----------------------------

  function buildCampaign(boostId, opts) {
    opts = opts || {};
    return json('/api/boosts/' + segment(boostId) + '/build', 'POST',
                { force: !!opts.force, photo_permission: !!opts.photo_permission });
  }

  // Records the "I have permission to use these photos" answer with its timestamp (item 9).
  function setPhotoPermission(boostId, granted) {
    return json('/api/boosts/' + segment(boostId) + '/photo-permission', 'PATCH',
                { granted: !!granted });
  }

  function buildStatus(boostId) {
    return request('/api/boosts/' + segment(boostId) + '/build-status');
  }

  function plan(boostId) {
    return request('/api/boosts/' + segment(boostId) + '/plan');
  }

  function posts(boostId) {
    return request('/api/boosts/' + segment(boostId) + '/posts');
  }

  function approvePost(postId) {
    return request('/api/posts/' + segment(postId) + '/approve', { method: 'PATCH' });
  }

  function approveAll(boostId, opts) {
    // The server refuses to approve posts the agent never opened unless this second answer
    // comes back with confirm: true (item 20 — no go-live without review).
    const body = {};
    if (opts && opts.unreviewed) body.unreviewed = opts.unreviewed;
    if (opts && opts.confirm) body.confirm = true;
    if (opts && opts.post_ids) body.post_ids = opts.post_ids;
    return request('/api/boosts/' + segment(boostId) + '/approve',
                   { method: 'POST', body: JSON.stringify(body) });
  }

  // ---- billing ------------------------------------------------------------
  // One campaign costs $49 and is bought outright: there is no credit balance to check, so
  // the old /adflow/credits/precheck/ call is gone with the credit system.

  function billingConfig() {
    return request('/api/billing/config');
  }

  function savedCards() {
    // The cards Stripe already holds for this account, masked. Read-only.
    return request('/api/billing/cards');
  }

  function checkout(boostId) {
    return json('/api/billing/checkout', 'POST', { boost_id: boostId });
  }

  function addCard(embedded) {
    // Add or change the card (nothing is charged). embedded: Stripe's form inside the pop-up,
    // returns { client_secret, session_id }; otherwise Stripe's page, returns { url }.
    return json('/api/billing/card', 'POST', { embedded: !!embedded });
  }

  function cardSaved(sessionId) {
    // The pop-up's form finished: the new card replaces the old one, and a held round is retried.
    return json('/api/billing/card/saved', 'POST', { session_id: sessionId });
  }

  function removeCard() {
    return request('/api/billing/card', { method: 'DELETE' });
  }

  function upcoming() {
    // Coming up: each listing on Run it until it sells and its next charge.
    return request('/api/billing/upcoming');
  }

  function chargeSaved(boostId) {
    // Pay for this campaign with the card on file. Clicking Build is the approval.
    return json('/api/billing/charge', 'POST', { boost_id: boostId });
  }

  function orders() {
    return request('/api/billing/orders');
  }

  function boostBilling(boostId) {
    return request('/api/billing/boost/' + segment(boostId));
  }

  function balance() {
    // Campaigns already paid for and not yet built (`campaigns_left`), plus the purchase
    // history. Packs are no longer sold, so this is above zero only for a balance bought
    // before they were withdrawn — and that balance still builds.
    return request('/api/billing/balance');
  }

  /* Take one photo out of a campaign's gallery. A repeat campaign on the same listing is
   * supposed to run different photos, so the gallery it inherits has to be editable. */
  function deletePhoto(assetId) {
    return json('/api/content/assets/' + segment(assetId), 'DELETE');
  }

  function campaignAgain(boostId) {
    // Start the next campaign on the same house: same address, facts, brand and photos.
    return json('/api/boosts/' + segment(boostId) + '/again', 'POST', {});
  }

  function launch(boostId, opts) {
    opts = opts || {};
    return json('/api/launch', 'POST', {
      platform: 'meta',
      boost_id: boostId,
      // No auto_approve: the server ignores it now and approval is always a human reading the
      // posts (item 20), so sending the flag would only pretend otherwise.
      meta_custom_configs: opts.meta_custom_configs || {},
    });
  }

  // ---- publishing ---------------------------------------------------------

  function publishStatus(boostId) {
    return request('/api/content/publish/status/' + segment(boostId));
  }

  function publishNow(boostId) {
    return request('/api/content/publish/boost/' + segment(boostId), { method: 'POST' });
  }

  // ---- Meta connection ----------------------------------------------------
  // Consent happens on Facebook, so metaConnect() only hands back the URL to visit;
  // the app never sees the token — Meta redirects to /api/oauth/meta/callback.

  function metaConnect() {
    return request('/api/oauth/meta/connect');
  }

  // The customer's brand profile, kept on the account so it is not lost with a browser.
  function brandProfile() {
    return request('/api/auth/me/brand').then(function (r) { return (r && r.brand) || {}; });
  }

  function saveBrandProfile(brand) {
    return request('/api/auth/me/brand', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ brand: brand || {} }),
    }).then(function (r) { return (r && r.brand) || {}; });
  }

  // Build the brand kit from the Facebook Page the agent connected (Brand Engine §4). The answer
  // separates facts (from Meta) from proposals (from the model) - the caller must not merge them
  // silently, so it returns the whole kit.
  function brandFromMeta() {
    return request('/api/auth/me/brand/from-meta', { method: 'POST' });
  }

  function adAccounts() {
    return request('/api/ad-accounts');
  }

  /* Re-check every connected ad account against Meta right now.
   * This is a POST with no body: it makes the app go and ask Meta, and it can refresh a
   * token that is close to expiring, so it must never be cached or done on page load. */
  // Onboarding answers come from the server (item 8), not from whatever this browser kept:
  // the Meta gate, the booked session and the tour must be the same on any device.
  function onboardingState() {
    return request('/api/onboarding/state');
  }
  function onboardingAudit() {
    return request('/api/onboarding/meta-audit');
  }
  function bookSetupSession(payload) {
    return request('/api/onboarding/setup-session',
                   { method: 'POST', body: JSON.stringify(payload || { booked: true }) });
  }
  function tourSeen() {
    return request('/api/onboarding/tour-seen', { method: 'POST' });
  }

  function checkConnections() {
    return request('/api/ad-accounts/check-all', { method: 'POST' });
  }

  // ---- reports ------------------------------------------------------------

  function report(boostId, day) {
    var d = (day === undefined || day === null) ? 7 : day;
    return request('/api/content/reports/' + segment(boostId) + '?day=' + segment(d));
  }

  // ---- support ------------------------------------------------------------

  // The client's own support desk: raising a request and reading the replies are the
  // same two calls the Support page and the "Ask Resmara" assistant both use, so a
  // question asked in the chat lands in the operator console as a real ticket.
  async function createTicket(subject, message, extra) {
    // extra: { boost_id, page } - which listing it's about and where they were.
    var body = { subject: String(subject || '').slice(0, 200), message: String(message || '') };
    if (extra && extra.boost_id) body.boost_id = extra.boost_id;
    var page = (extra && extra.page) || '';
    if (page) body.page = String(page);
    return request('/api/support', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
  }

  async function replyTicket(id, text) {
    return json('/api/support/' + segment(id) + '/reply', 'POST', { text: String(text || '') });
  }

  async function tickets() {
    return request('/api/support');
  }

  // Opening Support is reading the replies: this clears the orange number for good, on
  // every browser, instead of only in the one that happens to be open.
  async function markSupportRead() {
    return request('/api/support/read', { method: 'POST' });
  }

  // ---- health / version ---------------------------------------------------

  async function checkHealth() {
    var res = await fetch(home(), { method: 'GET', headers: authHeaders() });
    if (!res.ok) {
      var err = new Error('UI returned HTTP ' + res.status);
      err.status = res.status;
      throw err;
    }
    return { ok: true, status: res.status };
  }

  async function apiVersion() {
    // The app's own OpenAPI document carries its version and always exists; there is no
    // /api/status endpoint, so asking for one only ever produced a 404 to swallow.
    var res = await fetch(BASE + '/openapi.json', { method: 'GET', headers: authHeaders() });
    if (res.status === 404) return null; // deployment without docs - skip, not an error
    return parse(res);
  }

  // ---- social leads (Post Engine §10.4) -----------------------------------
  // The campaign page shows what the server found in Meta's comments. A lead lives on the
  // server, not in this browser, so ticking one off on a phone is the same lead everywhere.

  function leads(boostId) {
    return request('/api/boosts/' + segment(boostId) + '/leads');
  }

  function addLead(boostId, lead) {
    return json('/api/boosts/' + segment(boostId) + '/leads', 'POST', lead || {});
  }

  function setLeadStatus(leadId, status) {
    return json('/api/leads/' + segment(leadId), 'PATCH', { status: status });
  }

  function setLeadNote(leadId, note) {
    return json('/api/leads/' + segment(leadId), 'PATCH', { note: note || '' });
  }

  function removeLead(leadId) {
    return request('/api/leads/' + segment(leadId), { method: 'DELETE' });
  }

  function scanLeads(boostId) {
    return request('/api/boosts/' + segment(boostId) + '/leads/scan', { method: 'POST' });
  }

  // ---- export -------------------------------------------------------------

  window.RM = {
    base: BASE,           // the detected mount prefix ('' or '/resmara'); read-only
    media: mediaUrl,      // prefix an API media path for the current mount

    // The raw caller, for endpoints without a named helper (the Meta audit, the brand build, unlock).
    request: request,
    token: token,
    setToken: setToken,
    logout: logout,
    isLoggedIn: isLoggedIn,
    sessionExpiresAt: sessionExpiresAt,
    onSessionLost: onSessionLost,
    login: login,
    register: register,
    facebookStart: facebookStart,
    facebookExchange: facebookExchange,
    facebookReactivate: facebookReactivate,
    setEmail: setEmail,
    closeAccount: closeAccount,
    termsVersion: function () { return TERMS_VERSION; },
    me: me,
    requestPasswordReset: requestPasswordReset,
    confirmPasswordReset: confirmPasswordReset,
    deleteAccount: deleteAccount,
    boosts: boosts,
    boost: boost,
    hideBoost: hideBoost,
    setUntilSold: setUntilSold,
    deleteBoost: deleteBoost,
    createBoost: createBoost,
    uploadPhoto: uploadPhoto,
    assets: assets,
    buildCampaign: buildCampaign,
    setPhotoPermission: setPhotoPermission,
    buildStatus: buildStatus,
    plan: plan,
    posts: posts,
    approvePost: approvePost,
    approveAll: approveAll,
    generateContent: generateContent,
    billingConfig: billingConfig,
    savedCards: savedCards,
    cardSaved: cardSaved,
    removeCard: removeCard,
    upcoming: upcoming,
    checkout: checkout,
    addCard: addCard,
    chargeSaved: chargeSaved,
    orders: orders,
    boostBilling: boostBilling,
    balance: balance,
    deletePhoto: deletePhoto,
    campaignAgain: campaignAgain,
    launch: launch,
    publishStatus: publishStatus,
    publishNow: publishNow,
    report: report,
    leads: leads,
    addLead: addLead,
    setLeadStatus: setLeadStatus,
    setLeadNote: setLeadNote,
    removeLead: removeLead,
    scanLeads: scanLeads,
    photoIndex: photoIndex,
    gallery: gallery,
    importPhotos: importPhotos,
    checkListing: checkListing,
    withdrawPost: withdrawPost,
    tagAssets: tagAssets,
    createTicket: createTicket,
    replyTicket: replyTicket,
    tickets: tickets,
    markSupportRead: markSupportRead,
    metaConnect: metaConnect,
    brandProfile: brandProfile,
    saveBrandProfile: saveBrandProfile,
    brandFromMeta: brandFromMeta,
    adAccounts: adAccounts,
    checkConnections: checkConnections,
    onboardingState: onboardingState,
    onboardingAudit: onboardingAudit,
    bookSetupSession: bookSetupSession,
    tourSeen: tourSeen,
    checkHealth: checkHealth,
    apiVersion: apiVersion,
  };
})();
