#!/usr/bin/env node
'use strict';
/*
 * New-campaign flow test for static/app.js.
 *
 * Two owner reports are pinned here:
 *
 *  1. "When I enter the url when making a campaign it just keeps pulling up that same address
 *     even if I type a different address." The address typed into the form was thrown away -
 *     the campaign was created from whatever the link's slug said - and a check that was still
 *     waiting painted its result over the link the person had already replaced.
 *  2. A built campaign dropped the person on the Active campaigns list instead of the campaign
 *     they had just built, because the page kept view='campaigns' and the next background sync
 *     repainted the list over the open campaign.
 *
 * The real static/app.js runs in a vm sandbox, with real timers queued by hand so a check's
 * late answer can be delivered after the form has moved on - the exact race that was reported.
 *
 * Run:  node tests/test_new_campaign_flow.js
 */
const fs = require('fs');
const path = require('path');
const vm = require('vm');

let checks = 0;
let failures = 0;
function ok(name, cond, extra) {
  checks++;
  if (cond) console.log('  PASS  ' + name);
  else { failures++; console.log('  FAIL  ' + name + (extra ? '  (' + extra + ')' : '')); }
}

// ---- a small fake browser -------------------------------------------------
function makeEl(tag) {
  const el = {
    tagName: (tag || 'div').toUpperCase(),
    innerHTML: '', textContent: '', value: '', type: '', open: false,
    dataset: {}, style: {}, children: [], files: [],
    classList: { add() {}, remove() {}, contains() { return false; }, toggle() {} },
    append() {}, appendChild() {}, remove() {}, removeChild() {}, focus() {},
    addEventListener() {}, removeEventListener() {}, dispatchEvent() { return true; },
    setAttribute() {}, getAttribute() { return ''; },
    querySelector() { return null; }, querySelectorAll() { return []; }, closest() { return null; },
    showModal() { el.open = true; }, close() { el.open = false; },
    insertBefore() {}, setSelectionRange() {}, scrollIntoView() {},
  };
  return el;
}

const store = {};
const localStorage = {
  getItem: k => (k in store ? store[k] : null),
  setItem: (k, v) => { store[k] = String(v); },
  removeItem: k => { delete store[k]; },
};

const bySelector = { '#app': makeEl('div'), '#modal': makeEl('dialog'), '#content': makeEl('div') };

// Timers are a queue the test flushes, so "a check answers later" is something we can control.
const timers = [];
const sandbox = {
  console, URL, URLSearchParams, TextEncoder, TextDecoder, RegExp, Promise, JSON, Date, Math,
  localStorage,
  document: {
    body: makeEl('body'),
    documentElement: makeEl('html'),
    createElement: makeEl,
    addEventListener() {}, removeEventListener() {},
    querySelector(sel) { return bySelector[sel] || null; },
    querySelectorAll() { return []; },
  },
  MutationObserver: class { constructor() {} observe() {} disconnect() {} },
  Event: class { constructor(type) { this.type = type; } },
  CustomEvent: class { constructor(type) { this.type = type; } },
  setTimeout: fn => { timers.push(fn); return timers.length; },
  clearTimeout: () => 0, setInterval: () => 0, clearInterval: () => 0,
  fetch: () => Promise.reject(new Error('no network in this test')),
  location: { href: 'http://127.0.0.1:8083/', hash: '', pathname: '/', search: '' },
  navigator: { userAgent: 'node', language: 'en-US' },
  SAMPLE_POSTS: [], SAMPLE_AD: {}, SAMPLE_CLOSING: '', img: '', img2: '',
  RM: { isLoggedIn: () => true, logout() {}, me: () => Promise.resolve(null) },
  addEventListener() {}, removeEventListener() {}, matchMedia: () => ({ matches: false, addEventListener() {} }),
  scrollTo() {}, open() {}, innerWidth: 1280, innerHeight: 800,
};
sandbox.window = sandbox;
sandbox.globalThis = sandbox;
const ctx = vm.createContext(sandbox);
// app.js boots into homepage.js's routing on load, so homepage.js has to be there.
for (const file of ['homepage.js', 'app.js', 'review.js']) {
  vm.runInContext(fs.readFileSync(path.join(__dirname, '..', 'static', file), 'utf8'), ctx,
                  { filename: file });
}
const run = code => vm.runInContext(code, ctx);
function flush() {
  while (timers.length) timers.shift()();
}

const URL_A = 'https://www.flexmls.com/share/EpNjd/892-Coggins-Street,-Redding,-CA-96003';
const URL_B = 'https://www.flexmls.com/share/Qm4Tt/742-Evergreen-Terrace,-Springfield,-OR-97403';

function formWith(url, address) {
  const f = makeEl('form');
  const inputs = {
    url: makeEl('input'), street: makeEl('input'), city: makeEl('input'),
    state: makeEl('input'), zip: makeEl('input'), rights: makeEl('input'), files: makeEl('input'),
  };
  inputs.url.value = url || '';
  inputs.files.files = [];
  inputs.rights.checked = true;
  if (address) Object.assign(inputs, {
    street: Object.assign(inputs.street, { value: address[0] }),
    city: Object.assign(inputs.city, { value: address[1] }),
    state: Object.assign(inputs.state, { value: address[2] }),
    zip: Object.assign(inputs.zip, { value: address[3] }),
  });
  Object.assign(f, inputs);
  f.dataset = { state: 'empty' };
  f.classList = { contains: c => c === 'nc-form' };
  f.querySelector = sel => (sel === '.nc-result' ? makeEl('div') : sel === '.nc-build' ? makeEl('button') : null);
  f.isConnected = true;
  return f;
}

(async () => {
let shippedDetails = null;
// review.js owns the campaign page and its photo panel; the panel's own fetches are stubbed.
run('refreshPhotoAssets = function () {}; hydrateReviewItems = function () {};');
run('untilSoldPanel = function () { return ""; }; leadsPanel = function () { return ""; };');
run('liveCalendar = function (h) { return h; }; campaignIsLive = function () { return false; };');
run('showRerunOffer = function () {}; openPropertyReport = function () {};');
run('RM.gallery = function () { return Promise.resolve([]); };');

// The address flow ends in reviewDraft(), which starts a real build; this test stops one step
// earlier and watches what the build would carry.
run('reviewDraft = function () {};');

// ---- 1. the address the agent types is the address that is built -------------
console.log('\n[the typed address wins over the link slug]');
{
  const f = formWith(URL_A, ['742 Evergreen Terrace', 'Springfield', 'OR', '97403']);
  ok('the typed address is read as one line',
     run('ncTypedAddress')(f) === '742 Evergreen Terrace, Springfield, OR 97403', run('ncTypedAddress')(f));
  run("draft = {url:'" + URL_A + "', address:'892 Coggins Street, Redding, CA'}");
  run('ncBuild')(f);
  const d = run('draft');
  ok('the campaign is built for the typed property', d.address === '742 Evergreen Terrace, Springfield, OR 97403',
     d.address);
  ok('...and says the address came from the agent, not the link', d.addressSource === 'manual', d.addressSource);
}

console.log('\n[an empty address is filled from the link, and can still be edited]');
{
  const f = formWith(URL_A);
  run('draft = {}');
  run('ncCheck')(f);
  flush();
  const d = run('draft');
  ok('the link slug becomes the address', /892 Coggins/.test(d.address || ''), d.address);
  ok('...and is shown in the fields so it can be corrected', /892 Coggins/.test(f.street.value), f.street.value);
  ok('the link still carries the green light', f.dataset.state === 'ok', f.dataset.state);
  f.street.value = '900 Other Street';
  f.city.value = 'Redding'; f.state.value = 'CA'; f.zip.value = '96002';
  run('ncBuild')(f);
  ok('a correction typed after the check still wins', run('draft').address === '900 Other Street, Redding, CA 96002',
     run('draft').address);
}

// ---- 2. a late answer for the old link cannot overwrite the new one ---------
console.log('\n[a check still waiting cannot paint over the link you replaced]');
{
  const f = formWith(URL_A);
  run('draft = {}');
  run('ncCheck')(f);                 // timers queued, nothing delivered yet
  f.url.value = URL_B;               // the person pastes the next listing
  run('ncReset')(f);                 // what the input handler does
  flush();                           // the first check finally answers
  const d = run('draft');
  ok('the replaced link writes no draft', !d || !d.address, JSON.stringify(d));
  ok('the form is not painted green for the old link', f.dataset.state === 'empty', f.dataset.state);
  run('ncCheck')(f);
  flush();
  ok('the new link checks on its own', /742 Evergreen|Springfield|OR/.test(run('draft').address || ''),
     run('draft').address);
}

// ---- 3. building a campaign opens that campaign, not the list ---------------
console.log('\n[a built campaign opens as its own view]');
{
  let listPaints = 0;
  run('dashboard = function () {};');
  run('campaignList = function () { listPaints++; };');
  shippedDetails = run('details');
  run('details = function (i) { return "opened " + i; };');
  run(`state = { clientSignedIn: true, campaigns: [] }`);
  run('saveDraft')({ scopeFirst: true, boostId: 5, address: '742 Evergreen Terrace', url: URL_B });
  ok('the campaign page is the view after building', run('view') === 'campaign', run('view'));
  ok('the campaign that was just built is the one open', run('openCampaignKey') === 'boost:5',
     run('openCampaignKey'));
  ok('the list is not painted after the build', listPaints === 0, String(listPaints));
}

console.log('\n[a background sync does not replace an open campaign with the list]');
{
  let listPaints = 0;
  run('campaignList = function () { listPaints++; };');
  run(`state = { clientSignedIn: true, campaigns: [{ address: '742 Evergreen Terrace', boostId: 5, live: true }] }`);
  run('view = "campaign"; openCampaignKey = "boost:5"; liveCampaignsSyncedAt = 0;');
  sandbox.RM.boosts = () => Promise.resolve([
    { id: 5, address: '742 Evergreen Terrace', campaign_days: 14, ad_budget_usd: 50, posts_total: 14 },
    { id: 6, address: '12 New Listing Way', campaign_days: 14, ad_budget_usd: 50, posts_total: 14 },
  ]);
  run('syncLiveCampaigns')();
  await new Promise(r => setTimeout(r, 30));
  ok('the open campaign stays on screen', listPaints === 0, String(listPaints));
  ok('the new campaign is still in state for the list', run('state').campaigns.length === 2,
     String(run('state').campaigns.length));
}

// ---- report -----------------------------------------------------------------
// ---- 4. the shipped campaign page marks the view --------------------------
console.log('\n[opening a campaign is a view, not the list]');
{
  sandbox.details = shippedDetails;      // the real campaign page, restored from section 3
  run(`state = { clientSignedIn: true, reviews: {}, campaigns: [
        { address: '742 Evergreen Terrace', boostId: 5, live: true, posts_total: 14 }] }`);
  run('view = "campaigns"; openCampaignKey = null;');
  run('details')(0);
  ok('the campaign page sets view=campaign', run('view') === 'campaign', run('view'));
  ok('...and remembers which campaign is open', run('openCampaignKey') === 'boost:5', run('openCampaignKey'));
}

// ---- report -----------------------------------------------------------------
console.log('\n' + (failures ? 'FAILED ' + failures + ' of ' + checks : 'ALL NEW-CAMPAIGN CHECKS PASSED (' + checks + ')'));
process.exit(failures ? 1 : 0);
})();
