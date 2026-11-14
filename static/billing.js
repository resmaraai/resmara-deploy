/* Billing UI: one campaign for $49, or a prepaid pack of campaigns.
 *
 * A single campaign is bought outright; a pack is a prepaid balance of campaigns that shows up
 * as "campaigns left" and is spent one per build. The pack exists because the business is a
 * repeat one: an agent lists several homes a year and runs several campaigns on each, and
 * asking for a card every fortnight is what makes them stop.
 *
 * Loaded LAST (after homepage.js and app.js), so these same-named function declarations win
 * over the older credit versions instead of every screen being rewritten in place.
 */
'use strict';

var BILLING_PRICE_CENTS = 4900;
var BILLING_PACK = { size: 4, price_cents: 19600 };   // replaced by /api/billing/balance

function billingMoney(cents) {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' })
    .format((Number(cents) || 0) / 100);
}

// ---- balance helpers ------------------------------------------------------

// The real number from the server; 0 until the balance has loaded, never a made-up figure.
function creditBalance() { return Number(state.campaignsLeft) || 0; }

// A campaign with credits left does not need a card: the build spends one credit.
function useCampaignCredit() { return creditBalance() > 0; }

function creditQuote(quantity) {
  var n = Number(quantity) || BILLING_PACK.size;
  var unit = Math.round((BILLING_PACK.price_cents || 0) / (BILLING_PACK.size || 1));
  return { count: n, unit: unit, total: unit * n, savings: 0 };
}

function creditCalculator(fromPricePage) {
  var pack = BILLING_PACK || {};
  var packLine = pack.size
    ? `<p class="fine" style="margin:6px 0 0">Buying ${pack.size} at once (${billingMoney(pack.price_cents)})
       keeps a pack of campaigns ready — one is spent each time you build, and nothing expires.</p>`
    : '';
  return `<div class="notice"><b>${billingMoney(BILLING_PRICE_CENTS)} per campaign</b>
    <p class="fine" style="margin:6px 0 0">One 14-day listing campaign: branded posts, digital ad
    creative, and Day 7 and Day 14 reports. No subscription — you pay when you build a campaign.
    Meta ad spend is separate and paid to Meta.</p>${packLine}</div>`;
}

// ---- the paywall ----------------------------------------------------------

/* Ask for a Stripe Checkout URL and send the browser there. Returns the URL so callers can
 * open it themselves if the navigation is blocked. */
async function startCampaignCheckout(boostId) {
  if (boostId == null) { toast('Save the campaign first — there is nothing to charge for yet.'); return null; }
  try {
    var cfg = await RM.billingConfig();
    if (!cfg.enabled) {
      toast('Card payments are not switched on yet.');
      return null;
    }
    var res = await RM.checkout(boostId);
    if (res && res.status === 'already_paid') { toast('That campaign is already paid for.'); return null; }
    if (res && res.url) { window.location.href = res.url; return res.url; }
    toast('Stripe did not return a checkout page.');
  } catch (err) {
    toast((err && err.message) || 'Could not start the checkout.');
  }
  return null;
}

/* The screen a locked campaign shows: what it costs, why it is locked, one button. */
function showPaywall(boostId, detail) {
  var price = (detail && detail.price_cents) ? billingMoney(detail.price_cents)
    : billingMoney(BILLING_PRICE_CENTS);
  var pack = (detail && detail.pack) ? detail.pack : BILLING_PACK;
  var left = Number(detail && detail.campaigns_left) || 0;
  var packBlock = (pack && pack.size)
    ? `<div class="notice"><b>Or buy ${pack.size} campaigns for ${esc(pack.price_label)}</b>
        <p class="fine" style="margin:6px 0 0">${esc(billingMoney(pack.per_campaign_cents))} a campaign,
        ready to use on this house or the next one. Each build spends one; nothing expires.</p>
        <button class="alt" onclick="startPackCheckout()">Buy the ${pack.size}-campaign pack</button></div>`
    : '';
  show(`<span class="eyebrow">CAMPAIGN CHECKOUT</span>
    <h2>This campaign is ${esc(price)}</h2>
    <p>${esc((detail && detail.message) || 'Buy the campaign to build its 14 days of posts.')}</p>
    ${left > 0 ? `<p class="fine">You have ${left} prepaid campaign${left === 1 ? '' : 's'} left — building will use one.</p>` : ''}
    <p class="fine">Card details go to Stripe — Resmara never stores them. Stripe will offer the card
    you used last time, so this is the last time you type it. Meta ad spend is separate.</p>
    <div class="modal-actions">
      <button class="alt" onclick="modal.close()">Not now</button>
      <button class="campaign-primary" onclick="startCampaignCheckout(${Number(boostId)})">Pay ${esc(price)} and build →</button>
    </div>${packBlock}`);
}

/* Ask Stripe for a pack checkout and go there. The webhook is what adds the campaigns. */
async function startPackCheckout() {
  try {
    var cfg = await RM.billingConfig();
    if (cfg && cfg.pack) BILLING_PACK = cfg.pack;
    if (!cfg || !cfg.enabled) { toast('Card payments are not switched on yet.'); return null; }
    var res = await RM.packCheckout();
    if (res && res.url) { window.location.href = res.url; return res.url; }
    toast('Stripe did not return a checkout page.');
  } catch (err) {
    toast((err && err.message) || 'Could not start the checkout.');
  }
  return null;
}

/* Start the next campaign on the same house — the repeat purchase, one click. The new
 * campaign is a normal unpaid one, so it costs a credit or a fresh checkout; "again" can
 * never hand out a free campaign. */
async function campaignAgain(boostId) {
  if (boostId == null) return null;
  try {
    var res = await RM.campaignAgain(boostId);
    if (res && res.id) {
      toast('New campaign started for ' + (res.address || 'this property') + '.');
      // The campaign list caches its API read for ten seconds, so a brand-new campaign would be
      // invisible for exactly the moment the agent is looking for it. Reset that and re-read.
      try { liveCampaignsSyncedAt = 0; } catch (e) {}
      if (typeof syncLiveCampaigns === 'function') { try { await syncLiveCampaigns(); } catch (e) {} }
      if (typeof dashboard === 'function') dashboard('campaigns');
      return res;
    }
  } catch (err) {
    toast((err && err.message) || 'Could not start another campaign.');
  }
  return null;
}

// Kept for anything still wired to the old demo button: it now starts a real checkout.
function completeDemoCreditOrder(button, quantity, resume) {
  if (button && button.disabled) return;
  var boostId = (typeof reviewCampaignBoostId === 'function' && reviewCampaignBoostId()) || null;
  if (boostId != null) { startCampaignCheckout(boostId); return; }
  toast('Open the campaign first, then pay for it.');
}

// ---- screens --------------------------------------------------------------

function pricing() {
  if (typeof stopResmaraGuide === 'function') stopResmaraGuide();
  location.hash = 'pricing';
  document.title = 'Pricing — Resmara';
  app.innerHTML = `<div class="marketing-home">${siteNav('pricing')}<main>
    <section class="home-section package-page"><div>
      <span class="home-kicker">ONE PRICE PER LISTING</span>
      <h1>${billingMoney(BILLING_PRICE_CENTS)} for<br><span>one campaign.</span></h1>
      <p>Fourteen days of branded posts for Facebook and Instagram, digital ad creative, and
      Day 7 and Day 14 seller reports — for one property.</p>
      <p>No subscription, and nothing that expires. You pay when you build the
      campaign. Meta ad spend is paid separately, straight to Meta.</p>
      <button class="campaign-primary" onclick="newCampaign()">Start a campaign · ${billingMoney(BILLING_PRICE_CENTS)}</button>
    </div>${creditCalculator(true)}</section>
  </main></div>`;
}

async function myCredits() {
  // Same route the sidebar has always used ('credits'); the page is now Billing.
  // The shell paints first: an await before innerHTML leaves the previous screen on the page
  // when the network is slow, which on a free instance is most of the time.
  $('#content').innerHTML = `<div class="welcome"><h1>Billing</h1>
      <p>One property campaign costs ${billingMoney(BILLING_PRICE_CENTS)}, paid when you build it.
      Buy a pack and the campaigns wait for you — nothing expires.</p></div>
    <section class="panel"><h2>Campaigns left</h2>
      <div id="billing-balance"><p class="fine">Checking your balance…</p></div></section>
    <section class="panel"><h2>Purchases</h2>
      <div id="billing-orders"><p class="fine">Loading your purchases…</p></div></section>
    <section class="panel"><h2>Payment method</h2>
      <div id="billing-cards"><p class="fine">Checking your saved card…</p></div></section>
    <section class="panel"><h2>How it works</h2>
      <p>You pay ${billingMoney(BILLING_PRICE_CENTS)} when you build a campaign, or buy a pack up
      front and each build spends one campaign from it. Card details go to Stripe; Resmara never
      stores them. Meta ad spend is separate and paid to Meta from your own ad account.</p></section>
    <section class="panel"><h2>Your account</h2>
      <p class="fine">Closing your account removes your name, email and brand profile and stops it
      signing in. Purchases stay on record for accounting. This cannot be undone.</p>
      <button class="alt" onclick="closeAccount()">Close my account…</button></section>`;

  // The balance is the repeat-customer number: campaigns paid for, not yet built.
  var balBox = document.getElementById('billing-balance');
  if (balBox && RM.balance) {
    RM.balance().then(function (res) {
      var left = Number((res && res.campaigns_left) || 0);
      state.campaignsLeft = left;
      var pack = (res && res.pack) || BILLING_PACK;
      if (pack && pack.size) BILLING_PACK = pack;
      balBox.innerHTML = (left > 0
        ? `<p><b>${left} campaign${left === 1 ? '' : 's'} ready</b> — the next build uses one, no card needed.</p>`
        : '<p class="fine">No prepaid campaigns. You can pay for one when you build it.</p>') +
        (pack && pack.size
          ? `<div class="notice"><b>${esc(pack.label)}</b>
             <p class="fine" style="margin:6px 0 0">${esc(billingMoney(pack.per_campaign_cents))} a campaign.
             Use them on this listing or the next — they do not expire.</p>
             <button class="campaign-primary" onclick="startPackCheckout()">Buy ${pack.size} campaigns · ${esc(pack.price_label)}</button></div>`
          : '');
    }).catch(function () {
      balBox.innerHTML = '<p class="fine">Could not read your balance right now.</p>';
    });
  }

  // Saved card: Stripe keeps it on your customer record, so the next campaign is one click.
  var cardBox = document.getElementById('billing-cards');
  if (cardBox && RM.savedCards) {
    RM.savedCards().then(function (res) {
      var cards = (res && res.cards) || [];
      cardBox.innerHTML = cards.length
        ? '<ul class="campaign-report-list">' + cards.map(function (c) {
            return '<li><strong>' + esc(c.label) + '</strong><span class="fine">Stored by Stripe — ' +
              'checkout will offer it, no number to retype.</span></li>';
          }).join('') + '</ul><p class="fine">Your card number never reaches Resmara.</p>'
        : '<p class="fine">' + esc((res && res.note) || 'No card saved yet.') +
          ' Your first campaign saves it for next time.</p>';
    }).catch(function () {
      cardBox.innerHTML = '<p class="fine">Could not read your saved card right now.</p>';
    });
  }

  var box = document.getElementById('billing-orders');
  if (!box) return;
  var rows = [];
  var packs = [];
  try { rows = (await RM.orders()) || []; } catch (err) {
    box.innerHTML = '<p class="fine">Could not load your purchases. Check your connection and reload.</p>';
    return;
  }
  try { packs = ((await RM.balance()) || {}).purchases || []; } catch (err) { packs = []; }
  var date = function (v) {
    return v ? new Date(v).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }) : '—';
  };
  var campaignRows = rows.map(function (o) {
      var what = o.address || (o.boost_id ? 'Campaign #' + o.boost_id : 'Campaign');
      return `<li><strong>${esc(what)}</strong>
        <span class="fine">${esc(o.amount_label || billingMoney(o.amount_cents))} · ${esc(o.status)} · ${date(o.paid_at || o.created_at)}</span></li>`;
    }).join('');
  var packRows = packs.map(function (p) {
      return `<li><strong>${esc(p.campaigns)}-campaign pack</strong>
        <span class="fine">${esc(p.amount_label || billingMoney(p.amount_cents))} · ${esc(p.status)} · ${date(p.paid_at || p.created_at)}</span></li>`;
    }).join('');
  var allRows = campaignRows + packRows;
  box.innerHTML = allRows
    ? `<ul class="campaign-report-list">${allRows}</ul>`
    : '<p class="fine">No purchases yet. A campaign is charged when you build it.</p>';
}

// ---- returning from Stripe ------------------------------------------------

(function handleCheckoutReturn() {
  if (typeof location === 'undefined') return;
  var params = new URLSearchParams(location.search || '');
  var state_ = params.get('checkout');
  if (!state_) return;
  var boostId = Number(params.get('boost')) || null;
  // Clean the query so a refresh does not re-announce an old payment.
  var clean = location.pathname + (location.hash || '');
  window.history.replaceState({}, document.title, clean);
  if (state_ === 'success') {
    var isPack = params.get('pack') === '1';
    toast(isPack ? 'Payment received — your campaigns are ready to use.'
                 : 'Payment received — your campaign is unlocked.');
    if (typeof dashboard === 'function') setTimeout(function () { dashboard(isPack ? 'credits' : 'campaigns'); }, 400);
    if (boostId && window.RM && RM.boostBilling) {
      RM.boostBilling(boostId).then(function (b) {
        if (!b || !b.paid) toast('Stripe has not confirmed the payment yet — refresh in a moment.');
      }).catch(function () {});
    }
  } else if (state_ === 'cancelled') {
    toast('Checkout cancelled — nothing was charged.');
  }
})();

// ── closing an account ────────────────────────────────────────────────────────────
// The password is asked for again: the server refuses without it, so a token left in a
// browser cannot wipe someone's account. No `confirm()` — the typed address is stronger.
function closeAccount() {
  if (!window.RM) return;
  show(`<span class="eyebrow">CLOSE YOUR ACCOUNT</span><h2>This cannot be undone.</h2>
    <p>Your name, email and brand profile are removed and the account stops signing in.
    Purchases stay on record for accounting.</p>
    <form onsubmit="event.preventDefault();submitCloseAccount(this)">
      <label class="field">Type your email to confirm<input name="email" type="email" required autocomplete="off" placeholder="${esc(state.email || '')}"></label>
      <label class="field">Your password<input name="password" type="password" required autocomplete="current-password"></label>
      <p class="fine" role="status"></p>
      <div class="modal-actions"><button type="submit">Close my account</button>
      <button type="button" class="alt" onclick="modal.close()">Keep my account</button></div>
    </form>`);
}
async function submitCloseAccount(form) {
  var status = form.querySelector('[role="status"]');
  var typed = (form.elements.email.value || '').trim().toLowerCase();
  var password = form.elements.password.value || '';
  if (typed !== String(state.email || '').toLowerCase()) {
    status.textContent = 'That email does not match this account.';
    return;
  }
  status.textContent = 'Closing…';
  try {
    await RM.deleteAccount(password);
    state = { name: '', connected: false, campaigns: [] };
    persist();
    modal.close();
    toast('Your account is closed.');
    home();
  } catch (err) {
    status.textContent = (err && err.message) || 'Could not close the account.';
  }
}
