#!/usr/bin/env node
'use strict';
/*
 * static/signup.js (slice 1): the screens read the server's Meta status and brand kit, never guesses.
 *
 *  - the finish pop-up names the brand and shows each Facebook item as Connected / Not set up yet;
 *  - the tour opens on Accounts when something needs setting up, and skips straight to the look
 *    around when nothing does;
 *  - Fix it now opens the right fix for each outcome key;
 *  - the setup plan lists the three items and ticks what Meta already confirms;
 *  - + Campaign asks only for a missing phone, license or brokerage;
 *  - the pay card is Stripe's embedded form, and one locked campaign at a time.
 *
 * Runs the real file in a vm sandbox with a small fake browser.  Run: node tests/test_signup_flow.js
 */
const fs = require('fs');
const path = require('path');
const vm = require('vm');

let checks = 0, failures = 0;
function ok(name, cond, extra) {
  checks++;
  if (cond) console.log('  PASS  ' + name);
  else { failures++; console.log('  FAIL  ' + name + (extra ? '  (' + extra + ')' : '')); }
}

function sandbox(status, brand) {
  const shown = [], calls = [], toasts = [];
  const el = () => ({ innerHTML: '', textContent: '', classList: { add() {}, remove() {}, toggle() {}, contains() { return false; } }, dataset: {}, style: {}, querySelector() { return null; }, querySelectorAll() { return []; }, insertAdjacentHTML() {}, remove() {}, getAttribute() { return ''; } });
  const modal = Object.assign(el(), { open: false, close() { this.open = false; } });
  const responses = {
    '/api/onboarding/meta-audit': status, '/api/onboarding/meta-audit?force=1': status,
    '/api/auth/me/brand/build': { build: (brand && brand.build) || { status: 'done' }, brand: brand || {}, missing: (brand && brand.missing) || [] },
  };
  const ctx = {
    console, setTimeout: (fn) => { fn(); return 0; }, Promise, JSON, String, Number, Date, URLSearchParams,
    location: { hash: '', search: '', pathname: '/' }, history: { replaceState() {} },
    document: { querySelector() { return null; }, querySelectorAll() { return []; }, getElementById() { return null; }, createElement: el, head: { appendChild() {} } },
    modal, view: 'campaigns', state: { campaigns: [], name: 'Jamie Carter', firstRun: true, tourDone: false, clientSignedIn: true },
    TOUR: [], workspaceTourCleanup: null, persist() {}, esc: s => String(s == null ? '' : s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c])),
    show(html) { shown.push(html); modal.open = true; }, toast(t) { toasts.push(t); }, dashboard(v) { calls.push('dashboard:' + v); ctx.view = v; },
    workspaceTour(i) { calls.push('tour:' + i); }, tourDone() { calls.push('tourDone'); }, hydrateOnboarding() { return Promise.resolve(); },
    applyMetaChecks() {}, obBook() { calls.push('book'); }, setupGuides() {}, loadGoogleFont() {}, campaignBoostId: c => c.boostId,
    connectMeta() { calls.push('connect'); }, newCampaign() { calls.push('newCampaign:base'); }, accounts() {},
    RM: { isLoggedIn: () => true, request: p => { calls.push('GET ' + p); return Promise.resolve(responses[p] || {}); }, saveBrandProfile: b => Promise.resolve(b) },
    window: null,
  };
  ctx.window = ctx; ctx.$ = () => null;
  vm.createContext(ctx);
  vm.runInContext(fs.readFileSync(path.join(__dirname, '..', 'static', 'signup.js'), 'utf8'), ctx);
  return { ctx, shown, calls, toasts };
}
const tick = () => new Promise(r => setImmediate(r));
const flush = async () => { for (let i = 0; i < 20; i++) await tick(); };

const PERSONAL = { facebook: true, facebook_name: 'Jamie Carter', issues: ['no_page', 'no_ad_account'], lines: [{ key: 'no_page', line: 'No Facebook business Page is connected.', means: 'x', fix: { kind: 'setup', step: 'page' } }], fix: { kind: 'setup', step: 'page' }, capabilities: { fb_post: false, ig_post: false, ad: false, download_mode: true }, pages: [], done: [], todo: [] };
const READY = { facebook: true, facebook_name: 'Jamie Carter', issues: [], lines: [], capabilities: { fb_post: true, ig_post: true, ad: true }, page: { name: 'Jamie Carter Realty' }, instagram: { username: 'jamiecarterhomes' }, ad_account: { name: 'Jamie Ads' }, pages: [{ id: 'p1', name: 'Jamie Carter Realty', has_instagram: true }], done: [], todo: [] };
const KIT = { agent: 'Jamie Carter', company: "Shasta Sotheby's International Realty", license: '', fonts: ['Playfair Display', 'Jost'], palette: [['Primary', '#2F4F3E']], voiceOfClient: 'Jamie is warm and local. Second sentence. Third sentence.', build: { status: 'done' }, missing: ['license'] };

(async () => {
  console.log('Finish pop-up');
  let t = sandbox(PERSONAL, KIT);
  await t.ctx.RMSignup.metaStatus(false);
  t.ctx.RMSignup.brand = KIT;
  t.ctx.finishPopup();
  let html = t.shown[t.shown.length - 1];
  ok('greets them by first name', /You’re all set up, Jamie\./.test(html));
  ok('shows their brand: name, fonts, swatch', html.includes('Jamie Carter') && html.includes('Playfair Display · Jost') && html.includes('#2F4F3E'));
  ok('a missing license says so, without alarm', html.includes('License number not found yet'));
  ok('the first lines of the Voice of the client', html.includes('Jamie is warm and local. Second sentence.') && !html.includes('Third sentence'));
  ok('each Facebook item is Not set up yet, never orange', (html.match(/af-st info/g) || []).length === 3 && !html.includes('af-st bad'));
  ok('one button: Show me around', html.includes('Show me around'));

  console.log('The tour');
  t.ctx.startTour();
  ok('something to set up: the tour opens on Accounts first', t.ctx.TOUR[0].page === 'accounts' && /set up for business/.test(t.ctx.TOUR[0].title), t.ctx.TOUR[0].title);
  ok('  ...with Walk me through it and Do it with our team', t.ctx.TOUR[0].extra.includes('Walk me through it') && t.ctx.TOUR[0].extra.includes('Do it with our team'));
  ok('a missing license is its own stop on My Brand', t.ctx.TOUR[1].page === 'brand' && t.ctx.TOUR[1].extra.includes('Add it now'));
  ok('Billing says no card is needed yet', t.ctx.TOUR.some(s => s.page === 'credits' && /don’t need a card yet/.test(s.text)));
  ok('the last stop starts the first campaign', /Let’s start your first campaign/.test(t.ctx.TOUR[t.ctx.TOUR.length - 1].title));
  let r = sandbox(READY, { ...KIT, license: '02123456', missing: [] });
  await r.ctx.RMSignup.metaStatus(false);
  r.ctx.RMSignup.brand = { ...KIT, license: '02123456', missing: [] };
  r.ctx.startTour();
  ok('nothing to fix: straight to the look around', r.ctx.TOUR[0].page === 'campaigns' && /Campaign button/.test(r.ctx.TOUR[0].title), r.ctx.TOUR[0].title);

  console.log('Fix it now');
  const route = (fix, issues) => { const s = sandbox({ ...PERSONAL, issues: issues || [] }, KIT); return s.ctx.RMSignup.metaStatus(false).then(() => { s.ctx.metaFixIt(fix); return s; }); };
  let s = await route({ kind: 'reconnect' });
  ok('reconnect opens the Facebook dialog', s.calls.includes('connect'));
  s = await route({ kind: 'book' });
  ok('book opens the setup booking', s.calls.includes('book'));
  s = await route({ kind: 'dialog', rerequest: true });
  await flush();
  ok('an unticked permission re-asks in the dialog', s.calls.includes('GET /api/oauth/meta/connect?rerequest=1'));
  s = await route({ kind: 'setup', step: 'page' }, ['no_page']);
  ok('setup opens the setup plan', /Let’s get you set up for business/.test(s.shown[s.shown.length - 1]));

  console.log('The setup plan');
  let p = sandbox({ ...READY, issues: ['ig_not_linked', 'ad_no_payment'], capabilities: { fb_post: true, ig_post: false, ad: false }, pages: [{ id: 'p1', name: 'Jamie Realty', has_instagram: false }] }, KIT);
  await p.ctx.RMSignup.metaStatus(false);
  p.ctx.setupPlan();
  html = p.shown[p.shown.length - 1];
  ok('two things left, the Page already ticked', html.includes('2 things left') && html.includes('Already set up'));
  ok('no Instagram at all: create, not switch', html.includes('Create your Instagram business account'));
  ok('an ad account with no card: add a payment method', html.includes('Add a card to your ad account'));
  ok('the open item has its three buttons', html.includes('Do it with our team') && html.includes('See the tutorial') && html.includes('Check again'));

  console.log('+ Campaign asks only for what’s missing');
  let n = sandbox(READY, KIT);
  await n.ctx.newCampaign();
  html = n.shown[n.shown.length - 1] || '';
  ok('a missing license is asked for right there', html.includes('Your license number is missing.') && html.includes('name="license"') && !html.includes('name="phone"'));
  let m = sandbox(READY, { ...KIT, missing: [] });
  await m.ctx.newCampaign();
  ok('nothing missing: straight to the campaign form', m.calls.includes('newCampaign:base'));

  console.log('One locked campaign at a time');
  let u = sandbox(READY, KIT);
  u.ctx.unlockFirst({ boost_id: 7, address: '905 Laurel Bend' });
  html = u.shown[u.shown.length - 1];
  ok('names the waiting campaign, with Unlock and Replace it', html.includes('Unlock 905 Laurel Bend first.') && html.includes('Replace it') && html.includes('>Unlock<'));

  console.log(`\n${checks} checks, ${failures} failed.`);
  if (failures) process.exit(1);
  console.log('ALL SIGNUP FLOW CHECKS PASSED');
})().catch(e => { console.error(e); process.exit(1); });
