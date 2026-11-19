#!/usr/bin/env node
'use strict';
/*
 * Launch-details test for static/review.js.
 *
 * The owner's report: "the confirm details and build with resmara are not working". Both buttons
 * were dead on a real draft, and neither said why:
 *
 *  1. The go-live date input carries min=today. A scope still holding a date that had already
 *     passed made the form invalid, so the browser silently refused the submit and the button
 *     did nothing at all - no toast, no request, no error.
 *  2. "Build content with Resmara" only toasted when the photo-permission box was unticked, and
 *     returned without a word when the scope was not confirmed yet.
 *
 * The real static/review.js runs inside a vm sandbox, so these pin the shipped code.
 *
 * Run:  node tests/test_review_scope.js
 */
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const SRC = fs.readFileSync(path.join(__dirname, '..', 'static', 'review.js'), 'utf8');

let checks = 0;
let failures = 0;
function ok(name, cond, extra) {
  checks++;
  if (cond) console.log('  PASS  ' + name);
  else { failures++; console.log('  FAIL  ' + name + (extra ? '  (' + extra + ')' : '')); }
}

function today() {
  const d = new Date();
  return [d.getFullYear(), String(d.getMonth() + 1).padStart(2, '0'), String(d.getDate()).padStart(2, '0')].join('-');
}

// ---- a fake browser ----------------------------------------------------------
const toasts = [];
let modalOpen = false;
let fakeForm = null;
const document = {
  querySelector(sel) { return sel === '.campaign-scope form' ? fakeForm : null; },
  querySelectorAll() { return []; },
  getElementById() { return null; },
  body: { append() {} },
};

const sandbox = {
  console, JSON, Date, Math, Number, String, Object, Array, Promise, Error, RegExp, Intl, isNaN,
  setTimeout, clearTimeout,
  document,
  localStorage: { getItem() { return null; }, setItem() {}, removeItem() {} },
  location: { hash: '' },
  navigator: { language: 'en-US' },
  state: { campaigns: [], reviews: {} },
  examples: [],
  modal: { get open() { return modalOpen; }, close() { modalOpen = false; }, querySelector() { return { innerHTML: '' }; } },
  campaignBoostId: c => (c && c.boostId != null ? c.boostId : null),
  campaignBrandProfile: () => ({}),
  normalizeWebLink: v => (v ? (/^[a-z]+:/i.test(v) ? v : 'https://' + v) : ''),
  persist() {},
  toast(t) { toasts.push(t); },
  mediaPath: p => p,
  esc: s => String(s == null ? '' : s),
  SAMPLE_POSTS: [],
  sampleReviewItems: () => [],
  demoItemImage: () => '',
  demoPropertyHighlights: () => '',
  campaignIsLive: () => false,
  hydrateReviewItems() {},
  showRerunOffer() {},
  show() { modalOpen = true; },
  untilSoldPanel: () => '',
};
sandbox.window = sandbox;
vm.createContext(sandbox);
vm.runInContext(SRC, sandbox, { filename: 'static/review.js' });

const shippedBuild = sandbox.buildCampaignFromBackend;   // keep the real one for the gate check
// A signed-in client is what the buttons require at all; the build itself is stubbed per check.
sandbox.RM = { buildCampaign() { return Promise.resolve({ status: 'done' }); }, posts() { return Promise.resolve([]); }, buildStatus() { return Promise.resolve({}); }, setPhotoPermission() { return Promise.resolve({}); } };
let built = 0;
sandbox.details = () => {};
sandbox.buildApprovedScope = () => { built++; };
sandbox.persist = () => {};

function formWith(values) {
  const elements = {};
  Object.keys(values).forEach(k => {
    elements[k] = { value: values[k], focus() {}, closest: () => null };
  });
  elements.start = { value: values.start, focus() {}, closest: () => ({ firstChild: { textContent: 'Go-live date' } }) };
  elements.budget = { value: values.budget, focus() {}, closest: () => ({ firstChild: { textContent: 'Ad budget' } }) };
  return { elements };
}
function freshReview(extra) {
  sandbox.state.campaigns = [{ address: '900 Test Reachability Ln', boostId: 6, scopeFirst: true }];
  sandbox.state.reviews = {
    'review-0': Object.assign({
      v: 5, approved: false, scopeConfirmed: false, items: [], scopeFirst: true,
      scope: {
        address: '900 Test Reachability Ln', listing: '', media: '', facts: '', highlights: '',
        photoPlan: '', start: '2026-11-02', time: '10:00', zone: 'America/Los_Angeles',
        budget: '50', destination: '',
      },
    }, extra || {}),
  };
  sandbox.ReviewStudio.active = 0;
  return sandbox.state.reviews['review-0'];
}

// ---- tests (async: the permission gate is an await) --------------------------
async function run() {

// ---- 1. a stale go-live date is never carried into the form ------------------
sandbox.state.campaigns = [{ address: '1248 Oakridge Drive', scopeFirst: true }];
sandbox.state.reviews = {};
const stale = sandbox.initialCampaignScope({ address: '1248 Oakridge Drive', start: '2026-11-02' });
ok('a past go-live date in the draft is not used', stale.start !== '2026-11-02', stale.start);
ok('it rolls forward to a future day instead', stale.start >= today(), stale.start);

const noDate = sandbox.initialCampaignScope({ address: 'x' });
ok('a draft with no date gets tomorrow, not a hardcoded day in the past', noDate.start >= today(), noDate.start);
ok('a date already in the future is kept', sandbox.goLiveDate('2099-05-04') === '2099-05-04');
ok('garbage in the date box becomes a real date', /^\d{4}-\d{2}-\d{2}$/.test(sandbox.goLiveDate('not-a-date')) === true);

const rendered = sandbox.campaignScopePanel(freshReview());
ok('the rendered date input carries a valid value', rendered.includes('value="' + sandbox.goLiveDate('2026-11-02') + '"'));
ok('the form does not lean on browser validation to explain itself', /<form novalidate/.test(rendered));

// ---- 2. Confirm details confirms even when the stored date has passed -------
let r = freshReview();
sandbox.saveCampaignScope(formWith({ address: '900 Test Reachability Ln', start: '2026-11-02', budget: '50', destination: '' }));
ok('Confirm details confirms a scope holding a past date', r.scopeConfirmed === true);
ok('the confirmed scope carries the rolled-forward date', r.scope.start >= today(), r.scope.start);
ok('and the page says the date moved', toasts.some(t => /Go-live date moved/.test(t)), toasts.join(' | '));
ok('a live draft goes straight into the build', built === 1, 'built=' + built);

// ---- 3. a missing address explains itself instead of throwing --------------
toasts.length = 0; built = 0;
r = freshReview();
let threw = null;
try {
  sandbox.saveCampaignScope(formWith({ address: '', start: '2026-11-02', budget: '50', destination: '' }));
} catch (e) { threw = e; }
ok('an empty address does not throw (hidden fields have no label)', threw === null, threw && threw.message);
ok('it names the field instead', toasts.some(t => /check the address/i.test(t)), toasts.join(' | '));
ok('and nothing is confirmed', r.scopeConfirmed === false);

// ---- 4. Build content with Resmara is never a no-op ------------------------
toasts.length = 0; built = 0;
r = freshReview();
fakeForm = formWith({ address: '900 Test Reachability Ln', start: '2026-11-02', budget: '50', destination: '' });
sandbox.rebuildLiveCampaign();
ok('Build on an unconfirmed draft confirms the scope', r.scopeConfirmed === true);
ok('and reaches the build in the same click', built === 1, 'built=' + built);

// ---- 5. the photo-permission gate explains itself and leaves no dialog ----
toasts.length = 0;
r = freshReview({ scopeConfirmed: true });
const box = {
  checked: false, focused: false,
  focus() { this.focused = true; },
  scrollIntoView() {},
  closest() { return { classList: { add() {}, remove() {} } }; },
};
sandbox.document.querySelector = sel => (sel === '#photoPermission' ? box : null);
modalOpen = true;                       // the "building" dialog is up, as it was on the real page
sandbox.rmCalled = 0;
sandbox.RM = { buildCampaign() { sandbox.rmCalled++; return Promise.resolve({ status: 'done' }); } };
await shippedBuild();
ok('the building dialog is closed, not left spinning', modalOpen === false);
ok('the permission box is focused for the agent', box.focused === true);
ok('the toast names the tick that is missing', toasts.some(t => /I have permission to use these photos/.test(t)), toasts.join(' | '));
ok('no build request is sent without permission', sandbox.rmCalled === 0);

// ---- report -----------------------------------------------------------------
console.log('\n' + (failures ? 'FAILED ' + failures + ' of ' + checks : 'ALL LAUNCH-DETAILS CHECKS PASSED (' + checks + ')'));
process.exit(failures ? 1 : 0);
}

run().catch(e => { console.error(e); process.exit(1); });
