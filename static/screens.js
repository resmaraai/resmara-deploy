/* Screen tracking for Clarity heat maps and recordings.
 *
 * Why this file exists: the whole agent app is one page (index.html) and every dashboard screen
 * shares the address resmara.com/#dashboard. Clarity drops everything after the "#" when it
 * decides what page a visitor is on, so My Brand, Billing, a campaign page and the calendar were
 * all being lumped into ONE heat map. Nobody could tell which screen an agent was stuck on.
 *
 * What it does, on every screen change:
 *   1. Puts the screen in the address as ?screen=<name> (history.replaceState, so the back button
 *      and refresh behave exactly as before). Clarity watches replaceState and starts a new page
 *      when the part before the "#" changes, so each screen gets its own heat map.
 *   2. Tags the Clarity page with the screen name ("screen" custom tag) and sends a "screen: <name>"
 *      custom event, so recordings can be filtered and funnels built in Clarity.
 *   3. Tells Clarity which agent this is (clarity "identify" with their account email), so a
 *      support question can be matched to that agent's recordings.
 *
 * It only wraps the existing screen functions; it never changes what they draw. Every call is
 * guarded: tracking must never break the page it is measuring. Loaded last in index.html.
 */
(function () {
  'use strict';

  var current = '';        // the screen the agent is on now
  var underModal = '';     // the page screen behind an open pop-up (restored when it closes)

  function clarityReady() { return typeof window.clarity === 'function'; }

  function agentEmail() {
    try {
      var t = window.RM && RM.token && RM.token();
      if (!t || !(RM.isLoggedIn && RM.isLoggedIn())) return '';
      var part = String(t).split('.')[1].replace(/-/g, '+').replace(/_/g, '/');
      while (part.length % 4) part += '=';
      return String(JSON.parse(atob(part)).sub || '');
    } catch (e) { return ''; }
  }

  /* Clarity restarts ~250 ms after the address changes and forgets the page's tags, so they are
   * sent after the restart (and again a little later in case the Clarity script loads late). */
  function sendTags(name) {
    if (!clarityReady()) return;
    try {
      window.clarity('set', 'screen', name);
      var email = agentEmail();
      window.clarity('set', 'signed_in', email ? 'yes' : 'no');
      if (email) window.clarity('identify', email, null, null, email);
      window.clarity('event', 'screen: ' + name);
    } catch (e) { /* never break the page */ }
  }

  function setAddress(name) {
    try {
      var params = new URLSearchParams(location.search || '');
      if (params.get('screen') === name) return false;
      params.set('screen', name);
      history.replaceState(history.state, '', location.pathname + '?' + params.toString() + location.hash);
      return true;
    } catch (e) { return false; }
  }

  function screen(name) {
    if (!name) return;
    var moved = setAddress(name);
    var first = name !== current;
    current = name;
    if (!first && !moved) return;
    setTimeout(function () { if (current === name) sendTags(name); }, moved ? 600 : 0);
    setTimeout(function () { if (current === name) sendTags(name); }, 3000);
  }
  window.resmaraScreen = screen;

  /* A pop-up (new campaign, sign-in, reports in a modal...) gets its own screen while open, then
   * hands back to the page underneath. */
  function popup(name) {
    if (!underModal) underModal = current;
    screen(name);
  }
  function popupClosed() {
    if (underModal) { var back = underModal; underModal = ''; screen(back); }
  }

  /* Named events for the steps inside a screen (funnel steps in Clarity). */
  function step(name) { if (clarityReady()) { try { window.clarity('event', name); } catch (e) {} } }
  window.resmaraStep = step;

  function slug(s) { return String(s || '').toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, ''); }

  // The campaign page is named by where the campaign is in its life, not by address, so all
  // campaigns at the same stage share one heat map (sample campaigns are kept apart).
  function campaignScreen(index) {
    try {
      var c = [].concat(state.campaigns, examples)[index];
      if (!c) return 'campaign';
      var phase = typeof campaignPhase === 'function' ? campaignPhase(c) : 'active';
      var launched = !!(c.approved || c.launched || c.live || (phase !== 'active' && phase !== 'staged'));
      var stage = phase === 'completed' ? 'completed'
                : phase === 'republished' ? 'republished'
                : launched ? 'live' : 'review';
      if (typeof isSample === 'function' && isSample(c)) return 'sample-campaign';
      return 'campaign-' + stage;
    } catch (e) { return 'campaign'; }
  }

  var DASH = { campaigns: 'my-campaigns', brand: 'my-brand', credits: 'billing', accounts: 'accounts', support: 'support' };

  // [function name, what to call the screen (string or function of the call's arguments), kind]
  var MAP = [
    ['home', 'home', 'page'],
    ['howItWorks', 'how-it-works', 'page'],
    ['pricing', 'pricing', 'page'],
    ['setupGuides', 'setup-guides', 'page'],
    ['confirmEmailPage', 'confirm-email', 'page'],
    ['resetPasswordPage', 'reset-password', 'page'],
    ['dashboard', function () { return DASH[typeof view !== 'undefined' ? view : ''] || 'my-campaigns'; }, 'page'],
    ['details', function (a) { return campaignScreen(a[0]); }, 'page'],
    ['clientAccess', function (a) { return a[0] === 'signup' ? 'sign-up' : 'sign-in'; }, 'popup'],
    ['onboard', function (a) { return 'onboarding-connect-meta' + (a[0] ? '-' + a[0] : ''); }, 'popup'],
    ['obNeedsSetup', 'onboarding-meta-needs-setup', 'popup'],
    ['obNoFacebook', 'onboarding-no-facebook', 'popup'],
    ['obBrand', 'onboarding-brand', 'popup'],
    ['obFirstCampaign', 'onboarding-first-campaign', 'popup'],
    ['workspaceTour', function (a) { return 'tour-step-' + ((a[0] || 0) + 1); }, 'popup'],
    ['newCampaign', 'new-campaign', 'popup'],
    ['showPaywall', 'new-campaign-pay', 'popup'],
    ['openListingPage', 'listing-website-preview', 'popup']
  ];

  // Steps inside a screen, sent as Clarity events (no new heat map).
  var STEPS = [
    ['ncCheck', 'new campaign: link checked'],
    ['ncManual', 'new campaign: typed address instead'],
    ['ncNeedPhotos', 'new campaign: asked for photos'],
    ['ncBuild', 'new campaign: build started'],
    ['approveCampaignCalendar', 'campaign: calendar approved'],
    ['confirmCampaignApproval', 'campaign: approved'],
    ['editCampaignItem', 'campaign: post opened'],
    ['confirmWithdrawPost', 'campaign: post withdrawn'],
    ['openPropertyReport', 'campaign: report opened'],
    ['downloadReportPDF', 'campaign: report downloaded'],
    ['openLeads', 'campaign: leads opened'],
    ['saveBrandProfile', 'brand: saved'],
    ['brandResearchAgain', 'brand: research again'],
    ['openFontPicker', 'brand: font picker opened'],
    ['addPaymentCard', 'billing: add card'],
    ['connectMeta', 'accounts: connect meta'],
    ['submitTicket', 'support: ticket sent'],
    ['finishWorkspaceTour', 'tour: finished']
  ];

  function wrap(fn, after) {
    var orig = window[fn];
    if (typeof orig !== 'function' || orig.__tracked) return;
    var wrapped = function () {
      var out = orig.apply(this, arguments);
      try { after(arguments); } catch (e) { /* never break the page */ }
      return out;
    };
    wrapped.__tracked = true;
    window[fn] = wrapped;
  }

  MAP.forEach(function (m) {
    wrap(m[0], function (args) {
      var name = typeof m[1] === 'function' ? m[1](args) : m[1];
      if (m[2] === 'popup') popup(slug(name));
      else { underModal = ''; screen(slug(name)); }
    });
  });
  STEPS.forEach(function (s) { wrap(s[0], function () { step(s[1]); }); });

  // Pop-ups hand back to the page underneath when they close.
  try {
    var m = document.getElementById('modal');
    if (m) m.addEventListener('close', function () { setTimeout(popupClosed, 0); });
  } catch (e) {}
  wrap('closeListingPage', popupClosed);
  wrap('finishWorkspaceTour', popupClosed);

  // The screen the app opened on (it renders before this file loads).
  function initial() {
    if (current) return;
    var h = location.hash;
    var name = h === '#dashboard' ? DASH[typeof view !== 'undefined' ? view : ''] || 'my-campaigns'
             : h === '#pricing' ? 'pricing'
             : h === '#how-it-works' ? 'how-it-works'
             : h === '#setup-guides' ? 'setup-guides'
             : /\/confirm\/?$/.test(location.pathname) ? 'confirm-email'
             : /\/reset\/?$/.test(location.pathname) ? 'reset-password'
             : 'home';
    screen(name);
  }
  if (document.readyState === 'complete') initial();
  else window.addEventListener('load', function () { setTimeout(initial, 0); });
})();
