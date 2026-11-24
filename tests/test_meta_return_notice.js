#!/usr/bin/env node
'use strict';
/*
 * Landing back from Facebook with more than one Page must not read as a failure.
 *
 * Adam's report (24 Nov 2026): when an agent manages several Pages the callback lands on
 * ?meta=several_pages, and the app painted a red "Meta connection failed: several_pages" bar
 * instead of opening "Which Page is your business?". The chooser worked from Change Page, so the
 * only thing wrong was how the return was read: a normal choice looked like a broken login, in
 * the same window someone records App Review videos in.
 *
 * The shipped static/app.js runs inside a vm sandbox with a fake DOM, so this pins the real
 * metaReturnNotice() rather than a copy of it.
 *
 * Run:  node tests/test_meta_return_notice.js
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

function makeEl(tag) {
  const el = {
    tagName: (tag || 'div').toUpperCase(),
    innerHTML: '', textContent: '', value: '', type: '', open: false,
    dataset: {}, style: {}, children: [], parentNode: null,
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

const body = makeEl('body');
const prepended = [];
body.prepend = el => { prepended.push(el); };
const bySelector = { '#app': makeEl('div'), '#modal': makeEl('dialog'), '#content': makeEl('div') };
const replaced = [];

const sandbox = {
  console, localStorage, URLSearchParams,
  document: {
    body,
    documentElement: makeEl('html'),
    createElement: makeEl,
    addEventListener() {}, removeEventListener() {},
    querySelector(sel) { return bySelector[sel] || null; }, querySelectorAll() { return []; },
  },
  history: { replaceState(state, title, url) { replaced.push(url); }, pushState() {} },
  MutationObserver: class { constructor() {} observe() {} disconnect() {} },
  setTimeout: () => 0, clearTimeout: () => 0, setInterval: () => 0, clearInterval: () => 0,
  fetch: () => Promise.reject(new Error('no network in this test')),
  location: { href: 'https://www.resmara.com/', hash: '#dashboard', pathname: '/', search: '' },
  navigator: { userAgent: 'node' },
  SAMPLE_POSTS: [], SAMPLE_AD: {}, SAMPLE_CLOSING: '',
  RM: { isLoggedIn: () => true, logout: () => {}, me: () => Promise.resolve(null) },
  addEventListener() {}, removeEventListener() {}, matchMedia: () => ({ matches: false, addEventListener() {} }),
  scrollTo() {}, open() {}, innerWidth: 1280, innerHeight: 800,
};
sandbox.window = sandbox;
sandbox.globalThis = sandbox;
const ctx = vm.createContext(sandbox);
const run = code => vm.runInContext(code, ctx);

function load(file) {
  vm.runInContext(fs.readFileSync(path.join(__dirname, '..', 'static', file), 'utf8'), ctx, { filename: file });
}
load('homepage.js');
load('app.js');

// app.js's own dashboard() paints the whole page; this test only needs to know which section it
// was asked for. Reassigning the global is how tests/test_client_workspace.js does it too.
run('dashboard = function (tab) { __dashTabs = (__dashTabs || []).concat(String(tab)); };');
const dashTabs = () => JSON.parse(run('JSON.stringify(__dashTabs || [])'));

// The Page chooser and the audit call app.js reaches for; both counted so the test can see them.
let picked = 0, audits = 0;
sandbox.pagePicker = () => { picked++; };

function land(search, signup) {
  prepended.length = 0; replaced.length = 0; picked = 0; audits = 0;
  run('__dashTabs = [];');
  sandbox.location.search = search;
  sandbox.location.href = 'https://www.resmara.com/' + search + '#dashboard';
  sandbox.RMSignup = signup === undefined ? undefined : signup;
  run('metaReturnNotice()');
  return prepended[0] || {};
}

(async () => {
  console.log('\n[several Pages: the chooser opens, nothing says "failed"]');
  const many = {
    status: { pages: [{ id: '1', name: 'Alpha Homes' }, { id: '2', name: 'Beta Realty' }] },
    metaStatus: () => { audits++; return Promise.resolve({ pages: [] }); },
  };
  let el = land('?meta=several_pages&pages=2&issues=several_pages', many);
  ok('a notice is shown', !!el.textContent, JSON.stringify(el));
  ok('it does not say the connection failed', !/failed/i.test(String(el.textContent)), String(el.textContent));
  ok('it names the Pages it found', /2 Pages/.test(String(el.textContent)), String(el.textContent));
  ok('it tells them to choose one', /choose/i.test(String(el.textContent)), String(el.textContent));
  ok('the Page chooser opens by itself', picked === 1, String(picked));
  ok('the audit is not re-fetched when the list is already there', audits === 0, String(audits));
  ok('the connection page still opens behind it', dashTabs().includes('accounts'), JSON.stringify(dashTabs()));
  ok('the query is stripped so a reload does not replay it',
     replaced.length === 1 && !/meta=/.test(String(replaced[0])), JSON.stringify(replaced));

  console.log('\n[a tab that landed straight from Facebook has no Page list yet]');
  const cold = {
    status: {},
    metaStatus: () => { audits++; sandbox.RMSignup.status = many.status; return Promise.resolve(many.status); },
  };
  el = land('?meta=several_pages&pages=3', cold);
  await new Promise(r => setTimeout(r, 10));
  ok('the audit is fetched before choosing', audits === 1, String(audits));
  ok('  ...and the chooser opens once it answers', picked === 1, String(picked));
  ok('  ...still without an error bar', !/failed/i.test(String(el.textContent)), String(el.textContent));

  console.log('\n[the other landings keep their own reading]');
  el = land('?meta=connected&accounts=1&pages=1&page_id=9', many);
  ok('connected: the bar is a confirmation', /^Meta connected/.test(String(el.textContent)), String(el.textContent));
  ok('  ...and no chooser opens', picked === 0, String(picked));
  el = land('?meta=limited&issues=no_page', many);
  ok('limited: reported as a failure with the reason', /failed: limited/.test(String(el.textContent)), String(el.textContent));
  el = land('?meta=error&reason=access_denied', many);
  ok('error: keeps the reason Meta gave', /access_denied/.test(String(el.textContent)), String(el.textContent));
  el = land('', many);
  ok('no query: nothing is shown at all', !el.textContent, JSON.stringify(el));

  console.log(`\n${checks - failures}/${checks} passed`);
  if (failures) process.exit(1);
})();
