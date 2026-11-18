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
  var n = Number(cents) || 0;
  // $49, not $49.00: whole-dollar prices read cleaner, and cents only show when there are some.
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD',
    minimumFractionDigits: n % 100 ? 2 : 0, maximumFractionDigits: 2 }).format(n / 100);
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

/* Build said "this campaign isn't paid for yet" (402).
 *  - Card on file: charge it straight away and carry on building. Clicking Build is the approval,
 *    so there is no second page.
 *  - No card yet: one screen to add it. Paying the first campaign on Stripe's page saves the card,
 *    and every campaign after that is charged automatically.
 *  - Card declined (or the bank wants the agent present): Stripe's page, where they can confirm
 *    or use another card. */
async function showPaywall(boostId, detail) {
  var price = (detail && detail.price_cents) ? billingMoney(detail.price_cents)
    : billingMoney(BILLING_PRICE_CENTS);
  var live = window.RM && RM.chargeSaved && boostId != null;
  if (live) {
    show(`<span class="eyebrow">PAYMENT</span><h2>Charging your card…</h2>
      <p role="status">Paying ${esc(price)} for this campaign with your card on file.</p>`);
    try {
      var paid = await RM.chargeSaved(Number(boostId));
      if (paid && paid.status === 'paid') {
        toast(paid.already ? 'This campaign is already paid for.'
          : 'Charged ' + (paid.amount_label || price) + (paid.card ? ' to ' + paid.card.split(',')[0] : '') + '.');
        modal.close();
        if (typeof buildCampaignFromBackend === 'function') buildCampaignFromBackend();
        return;
      }
    } catch (err) {
      var d = (err && err.detail) || {};
      if (err && err.status === 402 && d.error === 'card_declined') {
        show(`<span class="eyebrow">PAYMENT</span><h2>Your card didn’t go through</h2>
          <p>${esc(d.message || 'Your card was declined.')}${d.card ? ' (' + esc(d.card.split(',')[0]) + ')' : ''}</p>
          <p class="fine">Nothing was charged. Pay on Stripe’s secure page instead, where you can confirm the payment or use another card. The card you use there becomes your card on file.</p>
          <div class="modal-actions"><button class="alt" onclick="modal.close()">Not now</button>
          <button class="campaign-primary" onclick="startCampaignCheckout(${Number(boostId)})">Pay ${esc(price)} on Stripe</button></div>`);
        return;
      }
      if (!(err && err.status === 409)) {
        // Billing switched off, Stripe down: say so plainly, no dead end.
        show(`<span class="eyebrow">PAYMENT</span><h2>We couldn’t take the payment</h2>
          <p>${esc((err && err.message) || 'Something went wrong with the payment.')}</p>
          <p class="fine">Nothing was charged. Try again in a minute.</p>
          <div class="modal-actions"><button class="campaign-primary" onclick="modal.close()">OK</button></div>`);
        return;
      }
    }
  }
  // No card on file yet: the first campaign is where it gets added.
  show(`<span class="eyebrow">ADD YOUR CARD</span>
    <h2>Add your card to build this campaign</h2>
    <p>This campaign is <b>${esc(price)}</b>. Add your card on Stripe’s secure page and this campaign is paid in the same step.</p>
    <p class="fine">Your card is saved with Stripe, not Resmara. From then on, every campaign you build is charged to it automatically, with no checkout page. Your Meta ad budget is separate.</p>
    <div class="modal-actions">
      <button class="alt" onclick="modal.close()">Not now</button>
      <button class="campaign-primary" onclick="startCampaignCheckout(${Number(boostId)})">Add card and pay ${esc(price)}</button>
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
      var addBtn = document.querySelector('.billing-add-card');
      if (addBtn) addBtn.textContent = cards.length ? 'Change card' : 'Add a card';
      cardBox.innerHTML = cards.length
        ? '<ul class="campaign-report-list">' + cards.map(function (c) {
            return '<li><strong>' + esc(c.label) + '</strong><span class="fine">Each campaign you build is charged to this card.</span></li>';
          }).slice(0, 1).join('') + '</ul><p class="fine">Stored by Stripe. Your card number never reaches Resmara.</p>'
        : '<p class="fine">' + esc((res && res.note) || 'No card saved yet.') +
          ' Add one now, or when you build your first campaign.</p>';
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
  var card = params.get('card');
  if (card) {
    window.history.replaceState({}, document.title, location.pathname + (location.hash || ''));
    toast(card === 'saved' ? 'Card saved. Each campaign you build is charged to it.'
                           : 'No card added. Nothing was charged.');
    if (typeof dashboard === 'function') setTimeout(function () { dashboard('credits'); }, 400);
    return;
  }
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
