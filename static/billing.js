/* Billing UI: one campaign for $49. Nothing else is for sale.
 *
 * There is no pack and no subscription: a repeat customer buys another campaign, and the one
 * click that starts it is "Another campaign" on the campaign card (same listing, fresh photos
 * and new copy). A prepaid balance bought before packs were withdrawn is still honoured, which
 * is the only reason "campaigns left" exists here.
 *
 * Loaded LAST (after homepage.js and app.js), so these same-named function declarations win
 * over the older credit versions instead of every screen being rewritten in place.
 */
'use strict';

var BILLING_PRICE_CENTS = 4900;

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
  var n = Number(quantity) || 1;
  var unit = BILLING_PRICE_CENTS;
  return { count: n, unit: unit, total: unit * n, savings: 0 };
}

function creditCalculator(fromPricePage) {
  return `<div class="notice"><b>${billingMoney(BILLING_PRICE_CENTS)} per campaign</b>
    <p class="fine" style="margin:6px 0 0">One 14-day listing campaign: branded posts, digital ad
    creative, and Day 7 and Day 14 reports. No subscription and no packs — you pay when you build a
    campaign, and another campaign on the same listing is another ${billingMoney(BILLING_PRICE_CENTS)}.
    Meta ad spend is separate and paid to Meta.</p></div>`;
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
  var left = Number(detail && detail.campaigns_left) || 0;
  show(`<span class="eyebrow">CAMPAIGN CHECKOUT</span>
    <h2>This campaign is ${esc(price)}</h2>
    <p>${esc((detail && detail.message) || 'Buy the campaign to build its 14 days of posts.')}</p>
    ${left > 0 ? `<p class="fine">You have ${left} prepaid campaign${left === 1 ? '' : 's'} left — building will use one.</p>` : ''}
    <p class="fine">Card details go to Stripe — Resmara never stores them. Stripe will offer the card
    you used last time, so this is the last time you type it. Meta ad spend is separate.</p>
    <div class="modal-actions">
      <button class="alt" onclick="modal.close()">Not now</button>
      <button class="campaign-primary" onclick="startCampaignCheckout(${Number(boostId)})">Pay ${esc(price)} and build</button>
    </div>`);
}

/* Start another campaign on the same listing — one click. Same house and brand, but a fresh
 * campaign: the photos come along so any can be swapped, the calendar opens on a different photo
 * and the copy is written new. It is a normal unpaid campaign, so it costs a checkout like any
 * other; "again" can never hand out a free build. */
async function campaignAgain(boostId) {
  if (boostId == null) return null;
  try {
    var res = await RM.campaignAgain(boostId);
    if (res && res.id) {
      toast('Another campaign started for ' + (res.address || 'this property') +
            ' — same photos, new calendar and new copy. Swap any photo before you build.');
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
  $('#content').innerHTML = `<div class="welcome billing-head"><h1>Billing</h1></div><div class="notice page-intro">Your Resmara purchases and the card we charge when you build a campaign. Your ad budget is billed by Meta to your own ad account, so it doesn’t show here.</div>
    <section class="panel billing-panel"><h3>Purchases</h3>
      <div id="billing-orders"><p class="fine">Loading your purchases…</p></div></section>
    <section class="panel billing-panel"><div class="billing-pm-head"><h3>Payment method</h3><button type="button" class="nc-cancel billing-add-card" onclick="addPaymentCard()">Add a card</button></div>
      <div id="billing-cards"><p class="fine">Checking your saved card…</p></div></section>
    <div class="billing-close"><button class="campaign-primary" onclick="closeAccount()">Close my account</button></div>`;

  // The balance is the repeat-customer number: campaigns paid for, not yet built.
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
  var legacy = [];
  try { rows = (await RM.orders()) || []; } catch (err) {
    box.innerHTML = '<p class="fine">Could not load your purchases. Check your connection and reload.</p>';
    return;
  }
  try { legacy = ((await RM.balance()) || {}).purchases || []; } catch (err) { legacy = []; }
  var date = function (v) {
    return v ? new Date(v).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }) : '—';
  };
  var campaignRows = rows.map(function (o) {
      var what = o.address || (o.boost_id ? 'Campaign #' + o.boost_id : 'Campaign');
      return `<li><strong>${esc(what)}</strong>
        <span class="fine">${esc(o.amount_label || billingMoney(o.amount_cents))} · ${esc(o.status)} · ${date(o.paid_at || o.created_at)}</span></li>`;
    }).join('');
  // A pack bought before they were withdrawn is still a real payment; it stays on the receipt list.
  var legacyRows = legacy.map(function (p) {
      return `<li><strong>${esc(p.campaigns)}-campaign pack <span class="fine">(no longer sold)</span></strong>
        <span class="fine">${esc(p.amount_label || billingMoney(p.amount_cents))} · ${esc(p.status)} · ${date(p.paid_at || p.created_at)}</span></li>`;
    }).join('');
  var allRows = campaignRows + legacyRows;
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
    // A legacy pack return (pack=1) has no campaign to open: it lands on the billing page.
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
