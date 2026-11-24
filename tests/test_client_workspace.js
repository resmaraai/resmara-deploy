#!/usr/bin/env node
'use strict';
/*
 * Client-workspace test: what a brand-new client sees, and what they can read back.
 *
 * Two owner reports are pinned here:
 *
 *  1. A new client signed up and opened on ANOTHER account's campaigns (the Coggins
 *     listings). The browser's workspace lived in one localStorage key with no owner, so a
 *     second person on the same machine inherited the first one's campaigns. A brand-new
 *     account must open on the two samples, Oakridge and Willow, and nothing else.
 *  2. The password boxes had no way to see what was typed.
 *
 * The real static/homepage.js and static/app.js run inside a vm sandbox with a small fake
 * DOM + localStorage, so this exercises the shipped code, not a copy of it.
 *
 * Run:  node tests/test_client_workspace.js
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
    dataset: {}, style: {}, children: [],
    classList: { add() {}, remove() {}, contains() { return false; } },
    append() {}, appendChild() {}, remove() {}, removeChild() {}, focus() {},
    addEventListener() {}, removeEventListener() {}, setAttribute(k, v) { el[k] = v; },
    getAttribute(k) { return el[k]; }, querySelector() { return null; },
    querySelectorAll() { return []; }, closest() { return null; },
    showModal() { el.open = true; }, close() { el.open = false; },
    insertBefore() {}, setSelectionRange() {},
  };
  return el;
}

const store = {};
const localStorage = {
  getItem: k => (k in store ? store[k] : null),
  setItem: (k, v) => { store[k] = String(v); },
  removeItem: k => { delete store[k]; },
};

let logoutCalls = 0;
// The two elements app.js grabs at load: #app (the page body it paints) and #modal.
const bySelector = { '#app': makeEl('div'), '#modal': makeEl('dialog'), '#content': makeEl('div') };
const sandbox = {
  console,
  localStorage,
  document: {
    body: makeEl('body'),
    documentElement: makeEl('html'),
    createElement: makeEl,
    addEventListener() {}, removeEventListener() {},
    querySelector(sel) { return bySelector[sel] || null; }, querySelectorAll() { return []; },
  },
  MutationObserver: class { constructor() {} observe() {} disconnect() {} },
  setTimeout: () => 0, clearTimeout: () => 0, setInterval: () => 0, clearInterval: () => 0,
  fetch: () => Promise.reject(new Error('no network in this test')),
  location: { href: 'https://www.resmara.com/', hash: '', pathname: '/', search: '' },
  navigator: { userAgent: 'node' },
  SAMPLE_POSTS: [], SAMPLE_AD: {}, SAMPLE_CLOSING: '',
  RM: { isLoggedIn: () => true, logout: () => { logoutCalls++; }, me: () => Promise.resolve(null) },
  addEventListener() {}, removeEventListener() {}, matchMedia: () => ({ matches: false, addEventListener() {} }),
  scrollTo() {}, open() {}, innerWidth: 1280, innerHeight: 800,
};
sandbox.window = sandbox;
sandbox.globalThis = sandbox;
const ctx = vm.createContext(sandbox);

function load(file) {
  const src = fs.readFileSync(path.join(__dirname, '..', 'static', file), 'utf8');
  vm.runInContext(src, ctx, { filename: file });
}
load('homepage.js');
load('app.js');
const run = code => vm.runInContext(code, ctx);
// Painting the dashboard needs the whole page furniture (campaign control, leads, review);
// this test is about the state the dashboard is given, so the drawing itself is stubbed.
run('dashboard = function () {};');

// ---- 1. the samples -------------------------------------------------------
console.log('\n[the samples are Oakridge and Willow, and only those]');
const addresses = run('examples.map(e => e.address)');
ok('two samples', addresses.length === 2, JSON.stringify(addresses));
ok('Oakridge present', addresses.some(a => /1248 Oakridge Drive/.test(a)), JSON.stringify(addresses));
ok('Willow present', addresses.some(a => /76 Willow Lane/.test(a)), JSON.stringify(addresses));
ok('no Coggins listing in the samples', !addresses.some(a => /coggins/i.test(a)), JSON.stringify(addresses));
ok('no other addresses sneaked in',
   !addresses.some(a => /Juniper|Cedar|Harpole|Sycamore/i.test(a)), JSON.stringify(addresses));

// ---- 2. a different person signing in ------------------------------------
console.log('\n[a different account on this browser starts clean]');
function signInAs(email, priorEmail, campaigns) {
  const prior = priorEmail || 'previous.owner@example.com';
  const rows = campaigns || [{ address: '892 Coggins Street Redding CA', boostId: 11, live: true }];
  run(`state = ${JSON.stringify({ name: 'Previous Person', email: prior, clientSignedIn: true,
        campaigns: rows, leads: { x: 1 }, brand: { agent: 'Someone Else' }, reviews: { r: 1 },
        hiddenSamples: ['1248 Oakridge Drive'] })}`);
  const form = makeEl('form');
  form.elements = {
    clientEmail: { value: email }, clientPassword: { value: 'Password123' },
    firstName: { value: 'New' }, lastName: { value: 'Client' }, inviteCode: { value: '' },
  };
  form.querySelector = () => makeEl('p');
  sandbox.RM.register = () => Promise.resolve({ id: 99, email, name: 'New Client' });
  sandbox.RM.login = () => Promise.resolve({ access_token: 'tok', name: 'New Client' });
  sandbox.RM.setToken = () => 'tok';
  sandbox.RM.brandProfile = () => Promise.resolve({});
  sandbox.submitTestClient(form, false);
  return email;
}

signInAs('new.client@example.com');
// submitTestClient is async; give its microtasks a turn.
setTimeout(() => {}, 0);

async function after(promiseDelay) {
  await new Promise(r => setTimeout(r, promiseDelay || 20));
  return run('state');
}

(async () => {
  const s1 = await after(30);
  ok('signed in as the new client', String(s1.email) === 'new.client@example.com', String(s1.email));
  ok('no inherited campaigns', !(s1.campaigns || []).length, JSON.stringify(s1.campaigns));
  ok('no inherited leads', !Object.keys(s1.leads || {}).length, JSON.stringify(s1.leads));
  ok('no inherited brand', !Object.keys(s1.brand || {}).length, JSON.stringify(s1.brand));
  ok('a hidden sample is not inherited', !(s1.hiddenSamples || []).length, JSON.stringify(s1.hiddenSamples));

  // ---- 3. the same person signing back in keeps their own draft -----------
  console.log('\n[the same person signing back in keeps the local draft]');
  signInAs('new.client@example.com', 'new.client@example.com', [{ address: '7 Local Draft Way', live: false }]);
  const s2 = await after(30);
  ok('own draft survives the same address signing in',
     (s2.campaigns || []).some(c => c.address === '7 Local Draft Way'), JSON.stringify(s2.campaigns));

  // ---- 4. signing out empties the browser's copy -------------------------
  console.log('\n[signing out ends the workspace in this browser]');
  run(`state = {...state, campaigns:[{address:'892 Coggins Street Redding CA', boostId:11}], leads:{x:1}, brand:{agent:'A'}}`);
  run('signOutDemo()');
  const s3 = run('state');
  ok('campaigns gone', !(s3.campaigns || []).length, JSON.stringify(s3.campaigns));
  ok('leads gone', !Object.keys(s3.leads || {}).length, JSON.stringify(s3.leads));
  ok('brand gone', !Object.keys(s3.brand || {}).length, JSON.stringify(s3.brand));
  ok('email forgotten', !s3.email, String(s3.email));
  ok('not signed in', s3.clientSignedIn === false, String(s3.clientSignedIn));
  ok('the session token was dropped', logoutCalls > 0, String(logoutCalls));
  ok('stored workspace has no campaigns',
     !(JSON.parse(store.resmara || '{}').campaigns || []).length, store.resmara);

  // ---- 5. the password can be read back ----------------------------------
  console.log('\n[what was typed into a password box can be seen]');
  const input = makeEl('input');
  input.type = 'password';
  const btn = makeEl('button');
  const wrap = { querySelector: () => input };
  btn.closest = sel => (sel === '.pw-wrap' ? wrap : null);
  sandbox.__btn = btn;
  run('togglePw(__btn)');
  ok('first press reveals it', input.type === 'text', input.type);
  ok('the button says Hide', String(btn.textContent) === 'Hide', String(btn.textContent));
  ok('the button reports pressed', String(btn['aria-pressed']) === 'true', String(btn['aria-pressed']));
  run('togglePw(__btn)');
  ok('second press hides it again', input.type === 'password', input.type);
  ok('the button says Show', String(btn.textContent) === 'Show', String(btn.textContent));

  const markup = fs.readFileSync(path.join(__dirname, '..', 'static', 'homepage.js'), 'utf8');
  ok('the sign-in / sign-up password box carries the control',
     /clientPassword" type="password"[\s\S]{0,200}class="pw-eye"/.test(markup));
  ok('the reset screen carries it on both boxes',
     (markup.match(/class="pw-eye"/g) || []).length >= 3,
     String((markup.match(/class="pw-eye"/g) || []).length));
  const billing = fs.readFileSync(path.join(__dirname, '..', 'static', 'billing.js'), 'utf8');
  // Engine 10: Facebook login has no password, so closing asks for the account email instead.
  ok('closing an account asks for the email, not a password',
     /Type your email to confirm/.test(billing) && !/name="password"/.test(billing));

  console.log(`\n${checks - failures}/${checks} passed`);
  if (failures) process.exit(1);
})();
