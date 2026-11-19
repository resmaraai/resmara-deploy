// First-time onboarding: connect Meta (with a readiness check) -> Resmara builds the brand -> first campaign.
// Replaces the old "Set up My Brand" first step. Brand details come from the Meta connection and
// the website on the agent's Facebook Page; name, brokerage and license come from sign-up.

function obSteps(active) {
  const names = ['Connect Meta', 'Your brand', 'Quick tour'];
  return `<ol class="ob-steps">${names.map((n, i) => `<li class="${i < active ? 'done' : i === active ? 'on' : ''}"><span>${i < active ? '✓' : i + 1}</span>${n}</li>`).join('')}</ol>`;
}

// Robot walks down a checklist; results[i] true/false; then cb().
function obWalk(box, labels, results, doneText, cb) {
  box.innerHTML = `<div class="nc-msg wait nc-walk"><div class="nc-steps"><span class="robot-avatar nc-bot" aria-hidden="true"></span><ul class="link-checks">${labels.map((l, i) => `<li data-i="${i}" class="${i ? '' : 'now'}">${l[0]}…</li>`).join('')}</ul></div></div>`;
  const bot = box.querySelector('.nc-bot');
  labels.forEach((l, i) => setTimeout(() => {
    if (!box.isConnected) return;
    const li = box.querySelector(`[data-i="${i}"]`);
    li.className = results[i] ? 'ok' : 'no';
    li.textContent = results[i] ? l[1] : l[2];
    const nx = box.querySelector(`[data-i="${i + 1}"]`);
    if (nx) { nx.classList.add('now'); bot.style.transform = `translateY(${nx.offsetTop}px)`; }
    if (i === labels.length - 1) setTimeout(() => box.isConnected && cb(), 700);
  }, 900 * (i + 1)));
}

const OB_SCENARIOS = {
  ready: { label: 'Everything is set up right', results: [1, 1, 1, 1] },
  noAd: { label: 'No ad account', results: [1, 1, 1, 0] },
  igPersonal: { label: 'Instagram is a personal account', results: [1, 1, 0, 1] },
  notAdmin: { label: 'Not an admin of the Facebook Page', results: [1, 0, 1, 1] },
  noPage: { label: 'No Facebook business Page', results: [0, 0, 0, 1] }
};
const OB_FIX = [
  ['No Facebook business Page found', 'Resmara posts to a Facebook business Page, not your personal profile. You’ll need a Page for your real estate business.'],
  ['You aren’t an admin of the Page', 'You need full control of the Page. Ask whoever manages it to make you an admin, or have them connect Resmara.'],
  ['Instagram isn’t a business account', 'Switch your Instagram to a professional (business) account in Instagram’s settings and link it to your Facebook Page.'],
  ['No ad account ready to run ads', 'Your listing ads run from your own Meta ad account, with a card on file so Meta can bill your ad budget.']
];

// Preview of Facebook's own login window. In the live app, Connect with Facebook opens the real
// Facebook Login for Business pop-up for the Resmara app; the agent logs in, approves access and
// comes straight back here for the audit.
function obFbConsent(scenario) {
  show(`<div class="fb-mock"><div class="fb-mock-bar">facebook.com · Log in with Meta <em>PREVIEW</em></div><div class="fb-mock-body"><span class="robot-avatar" aria-hidden="true"></span><h3>Resmara is requesting access</h3><p>Continue as <b>${esc(state.name || 'you')}</b> to let Resmara:</p><ul><li>See and post to the Facebook Page you choose</li><li>See and post to the Instagram business account linked to it</li><li>Create and manage ads in the ad account you choose</li><li>Read how your posts and ads perform, for your reports</li></ul><p class="fine">You choose which Page, Instagram account and ad account. You can remove Resmara’s access any time in your Facebook settings.</p><div class="fb-mock-actions"><button type="button" class="fb-cancel" onclick="onboard(0)">Cancel</button><button type="button" class="fb-continue" onclick="obCheck('${scenario}')">Continue</button></div></div></div><p class="fine" style="text-align:center;margin-top:10px">In the live app this is Facebook’s own window.</p>`);
  modal.dataset.gate = 'meta';
}

// Step 1: connect Facebook.
function onboard(stage = 0) {
  if (stage === 1) return obBrand();
  if (stage === 2) return obFirstCampaign();
  const live = typeof liveCampaignsAvailable === 'function' && liveCampaignsAvailable();
  show(`${obSteps(0)}<span class="eyebrow">STEP 1 OF 3</span><h2>Connect your Meta account.</h2>
  <p>Connect your Meta account. Log in with your Facebook details and choose the Page, Instagram account and ad account Resmara can use. Resmara also learns your brand from what you already post.</p>
  <ul class="ob-list"><li>Your Facebook Page and Instagram, so Resmara can post for you</li><li>Your ad account, so your listing ads run under your name</li><li>Your posts and website, so everything looks and sounds like you</li></ul>
  <p class="fine">Nothing is ever posted without your approval.</p>
  ${live ? '' : `<p class="ob-preview">Testing: <b>${esc((OB_SCENARIOS[state.mockScenario] || OB_SCENARIOS.ready).label)}</b> · <a href="#" onclick="obPickScenario(true);return false">change</a></p>`}
  <div class="modal-actions"><button type="button" class="nc-cancel" onclick="modal.close()">Cancel</button><button class="campaign-primary ob-fb" onclick="${live ? 'connectMeta()' : "obFbConsent(state.mockScenario || 'ready')"}">Connect your Meta account</button></div>`);
  modal.dataset.gate = 'meta';
}

function obCheck(scenario) {
  let ok = true;
  show(`${obSteps(0)}<span class="eyebrow">STEP 1 OF 3</span><h2>Checking your setup.</h2><div id="ob-box"></div>`);
  const labels = [
    ['Finding your Facebook Page', 'Facebook Page found', OB_FIX[0][0]],
    ['Checking you’re an admin', 'You’re an admin of the Page', OB_FIX[1][0]],
    ['Looking for your Instagram', 'Instagram business account linked', OB_FIX[2][0]],
    ['Checking your ad account', 'Ad account ready, with a payment method', OB_FIX[3][0]]
  ];
  const results = (OB_SCENARIOS[scenario] || OB_SCENARIOS.ready).results.map(Boolean);
  ok = results.every(Boolean);
  obWalk(document.querySelector('#ob-box'), labels, results, '', () => {
    // Only the Facebook Page is required: it's where the posts go. A personal Instagram or a
    // missing ad account limits the campaign (no Instagram posts, no ad) but never locks the
    // agent out. What's missing is kept so every page can say so until it's fixed.
    const issues = results.map((r, i) => r ? null : i).filter(i => i !== null);
    const pageOk = results[0] && results[1];
    state.metaIssues = issues;
    state.metaAudit = { status: ok ? 'ready' : pageOk ? 'limited' : 'blocked', checkedAt: new Date().toISOString() };
    state.connected = pageOk; persist();
    if (ok) { show(`${obSteps(0)}<span class="eyebrow">STEP 1 OF 3</span><h2>You’re connected.</h2><div class="nc-msg ok"><span class="robot-avatar"></span><div><b>Green light.</b> Your Page, Instagram and ad account are all set. Next, Resmara builds your brand.</div></div><div class="modal-actions"><span></span><button class="campaign-primary" onclick="onboard(1)">Build my brand</button></div>`); return; }
    obNeedsSetup(issues);
  });
}

function obNeedsSetup(idx) {
  state.obIssues = idx; persist();
  const pageOk = !idx.includes(0) && !idx.includes(1);
  const issues = idx.map(i => `<b>${OB_FIX[i][0]}.</b> ${OB_FIX[i][1]}`);
  show(`${obSteps(0)}<span class="eyebrow">STEP 1 OF 3</span><h2>${pageOk ? 'You’re connected, with a couple of limits.' : 'Almost there.'}</h2>
  ${pageOk ? `<div class="nc-msg ok"><span class="robot-avatar"></span><div><b>Your Facebook Page is connected.</b> ${metaLimitLine(idx)}</div></div><p>To get the most from Resmara, fix these when you can:</p>` : '<p>Resmara can’t find a Facebook Page it can post to yet. You can still set up your account and look around while you sort it out:</p>'}
  <ul class="ob-issues">${issues.map(i => `<li>${i}</li>`).join('')}</ul>
  <div class="notice ob-help"><b>We’ll set it up with you.</b> Book a free setup call and one of our team will fix it with you, step by step. You’ll also see a reminder at the top of your dashboard until it’s sorted.</div>
  <div class="modal-actions"><button type="button" class="nc-cancel" onclick="obBook()">Book a free setup call</button><button class="campaign-primary" onclick="onboard(1)">${pageOk ? 'Continue' : 'Continue for now'}</button></div><p class="fine ob-skip"><a href="#" onclick="obCheck('ready');return false">Check again</a> · Preview: Check again acts as if you fixed it.</p>
`);
}
// What a campaign can do with what is connected, in one line.
function metaLimitLine(idx) {
  const ig = idx.includes(2), ad = idx.includes(3);
  if (idx.includes(0) || idx.includes(1)) return 'Your campaigns can’t post until a Facebook Page is connected. Your listing page still works.';
  return 'Your campaigns can still run, with limited reach: ' + (ig && ad ? 'posts go to your Facebook Page only, and your listing ad is off until it’s fixed.' : ig ? 'posts go to your Facebook Page only, not Instagram, until it’s fixed.' : 'your posts go out, but your listing ad is off until it’s fixed.');
}
// A red box at the top of every dashboard page and campaign until the Meta account is sorted.
const META_ISSUE_SHORT = ['No Facebook business Page is connected', 'You aren’t an admin of your Facebook Page', 'Your Instagram isn’t a business account', 'Your ad account can’t run ads yet'];
function metaIssueBanner() {
  const idx = state.metaIssues || [];
  const box = document.querySelector('#content');
  if (!box || !idx.length || box.querySelector('.meta-issue')) return;
  box.insertAdjacentHTML('afterbegin', `<div class="meta-issue" role="alert"><b class="meta-issue-title">There’s an issue with your Meta account.</b><ul>${idx.map(i => `<li>${META_ISSUE_SHORT[i]}.</li>`).join('')}</ul><p>${metaLimitLine(idx)}</p><div class="meta-issue-actions"><button type="button" class="meta-issue-book" onclick="obBook()">Book a call to fix it</button><button type="button" class="meta-issue-check" onclick="onboard(0)">Check again</button></div></div>`);
}

// Free setup session: the real Calendly booking page, right in the pop-up.
const SETUP_CALENDLY = 'https://calendly.com/d/d32t-m77-tmt/real-estate-boost-onboarding-session';
function obBook() {
  const [first, ...rest] = String(state.name || '').split(' ');
  const q = new URLSearchParams({ embed_type: 'Inline', embed_domain: location.hostname || 'resmara.com', hide_gdpr_banner: '1', hide_landing_page_details: '1', primary_color: 'd94c0d', name: state.name || '', email: state.email || '', first_name: first || '', last_name: rest.join(' ') });
  show(`<span class="eyebrow">FREE SETUP SESSION</span><h2>Let’s get you set up.</h2><p>Pick a time for a 30-minute video call. One of our team will connect your Facebook Page, Instagram and ad account with you.</p>
  <div class="cal-embed"><iframe src="${SETUP_CALENDLY}?${q}" title="Book your setup session" loading="lazy"></iframe></div>
  <p class="fine">Calendly not loading? <a href="${SETUP_CALENDLY}" target="_blank" rel="noopener">Open the booking page</a>.</p>
  <div class="modal-actions"><button type="button" class="nc-cancel" onclick="${state.brandBuilt ? 'modal.close()' : 'obNeedsSetup(state.obIssues||[3])'}">Back</button><span></span></div>`);
  modal.classList.add('wide-modal'); modal.dataset.gate = 'meta';
}
// When the booking is made inside the embed, Calendly tells the page.
addEventListener('message', e => {
  if (!/calendly\.com$/.test(new URL(e.origin || 'https://x.invalid').hostname)) return;
  if (e.data && e.data.event === 'calendly.event_scheduled') {
    // Stored on the account (item 8): booking a session is a fact about the agent, and it
    // has to survive a new browser the same way the Meta connection does.
    state.setupSession = { booked: new Date().toISOString() }; persist();
    if (window.RM && RM.isLoggedIn()) RM.bookSetupSession({ booked: true }).catch(() => {});
    show(`<span class="robot-avatar ob-bot-lg" aria-hidden="true"></span><span class="eyebrow">YOU’RE BOOKED IN</span><h2>See you soon.</h2><p>Calendly has emailed you the time and a video link. We’ll sort out your Meta account together on the call. Until then you can carry on as normal.</p><div class="modal-actions"><button type="button" class="nc-cancel" onclick="modal.close()">Close</button><button class="campaign-primary" onclick="onboard(1)">Build my brand</button></div>`);
  }
});

// Step 2: Resmara builds the brand on its own.
function obBrand() {
  modal.classList.remove('wide-modal');
  show(`${obSteps(1)}<span class="eyebrow">STEP 2 OF 3</span><h2>Building your brand.</h2><p>Sit tight. Resmara is learning who you are, so every post and ad looks and sounds like you.</p><div id="ob-box"></div>`);
  const labels = [
    ['Reading your Facebook Page', 'Read your Facebook Page', ''],
    ['Reviewing your Instagram posts', 'Reviewed your Instagram posts', ''],
    ['Auditing your website', 'Audited your website', ''],
    ['Building your brand kit', 'Built your brand kit', '']
  ];
  obWalk(document.querySelector('#ob-box'), labels, [true, true, true, true], '', () => {
    state.brandBuilt = true; persist();
    show(`${obSteps(1)}<span class="eyebrow">STEP 2 OF 3</span><h2>Your brand kit is ready.</h2><div class="nc-msg ok"><span class="robot-avatar"></span><div><b>Done.</b> Your colours, fonts, logo, voice and brokerage details are all in your brand kit. You can check it any time in My Brand.</div></div><div class="modal-actions"><button type="button" class="nc-cancel" onclick="modal.close();dashboard('brand')">Review my brand</button><button class="campaign-primary" onclick="onboard(2)">Next</button></div>`);
  });
}

// Step 3: a quick guided tour of the dashboard (first visit only), ending on the Campaign button.
function obFirstCampaign() {
  show(`${obSteps(2)}<span class="robot-avatar ob-bot-lg" aria-hidden="true"></span><span class="eyebrow">STEP 3 OF 3</span><h2>A quick look around.</h2><p>Let me show you where everything is. It takes about a minute.</p><div class="modal-actions"><button type="button" class="nc-cancel" onclick="finishWorkspaceTour()">Skip the tour</button><button class="campaign-primary" onclick="modal.close();workspaceTour(0)">Show me around</button></div>`);
}


const TOUR = [
  { page: 'campaigns', sel: '.add-campaign', title: 'This is the Campaign button.', text: 'Click it any time to start a new campaign. All you need is your MLS public listing link.' },
  { page: 'campaigns', sel: '.camp-tabs', title: 'Your campaigns live here.', text: 'Active campaigns are running now. When one finishes it moves to the Completed tab, where you can run it again in one click.' },
  { page: 'brand', sel: '.mb-head', title: 'This is your brand.', text: 'Update it any time. Add your headshot or logo, or anything the first audit missed. Every post and ad follows it.' },
  { page: 'credits', sel: '#billing-cards', box: true, title: 'This is Billing.', text: 'Review your purchases and the card Resmara uses to bill each campaign you run. Want to put one on file now?', extra: '<button type="button" class="tour-extra" onclick="addPaymentCard()">Add a card now</button>' },
  { page: 'accounts', sel: '.meta-card', title: 'Your accounts.', text: 'Your Facebook Page, Instagram and ad account connection lives here. If anything ever needs attention, this is where you’ll find it.' },
  { page: 'support', sel: '.grid2 .panel', title: 'Need a hand?', text: 'Send us a request any time. A real person reads every one and replies right here.' },
  { page: 'campaigns', sel: '.add-campaign', final: true, title: 'Let’s build your first campaign.', text: 'Click the Campaign button to start.' }
];
function workspaceTour(step = 0) {
  workspaceTourCleanup?.();
  if (modal.open) modal.close();
  const s = TOUR[step];
  dashboard(s.page);
  let target = document.querySelector('#content ' + s.sel);
  if (target && s.box) target = target.closest('.panel') || target;
  if (!target) { if (step < TOUR.length - 1) workspaceTour(step + 1); return; }
  target.classList.add('workspace-tour-target');
  if (s.final) target.classList.add('tour-pulse');
  const tip = document.createElement('section');
  tip.className = 'workspace-tour-tip' + (s.final ? ' final' : '');
  tip.setAttribute('aria-label', 'Dashboard tour');
  tip.innerHTML = `<div class="tour-head"><span class="robot-avatar tour-bot" aria-hidden="true"></span><span class="eyebrow">QUICK TOUR · ${step + 1} OF ${TOUR.length}</span></div><h2>${s.title}</h2><p>${s.text}</p>${s.extra || ''}<div class="modal-actions">${s.final ? '<button class="nc-cancel tour-skip" onclick="finishWorkspaceTour()">Maybe later</button><span></span>' : `<button class="nc-cancel" onclick="${step ? 'workspaceTour(' + (step - 1) + ')' : 'finishWorkspaceTour()'}">${step ? 'Back' : 'Skip tour'}</button><button class="campaign-primary" onclick="workspaceTour(${step + 1})">Next</button>`}</div>`;
  document.body.append(tip);
  target.scrollIntoView({ block: 'center' });
  function place() {
    const r = target.getBoundingClientRect();
    const left = Math.max(12, Math.min(r.right - tip.offsetWidth, innerWidth - tip.offsetWidth - 12, Math.max(r.left, 12)));
    const below = r.bottom + 14;
    const top = below + tip.offsetHeight <= innerHeight - 12 ? below : Math.max(12, r.top - tip.offsetHeight - 14);
    tip.style.left = left + 'px'; tip.style.top = top + 'px';
  }
  function onKey(e) { if (e.key === 'Escape') finishWorkspaceTour(); }
  const onTargetClick = () => { if (s.final) { workspaceTourCleanup?.(); tourDone(); } };
  target.addEventListener('click', onTargetClick);
  const observer = new MutationObserver(() => { if (!target.isConnected) workspaceTourCleanup?.(); });
  observer.observe(app, { childList: true, subtree: true });
  addEventListener('scroll', place, true); addEventListener('resize', place); addEventListener('keydown', onKey);
  workspaceTourCleanup = () => {
    observer.disconnect(); target.classList.remove('workspace-tour-target', 'tour-pulse'); target.removeEventListener('click', onTargetClick); tip.remove();
    removeEventListener('scroll', place, true); removeEventListener('resize', place); removeEventListener('keydown', onKey);
    workspaceTourCleanup = null;
  };
  place();
}
function tourDone() {
  state.firstRun = false; state.tourDone = true; persist();
  // Once per account, not once per browser: signing in on a laptop should not replay it.
  if (window.RM && RM.isLoggedIn()) RM.tourSeen().catch(() => {});
}
function finishWorkspaceTour() { workspaceTourCleanup?.(); tourDone(); if (modal.open) modal.close(); dashboard('campaigns'); }

// Card on file: opens Stripe's secure card page (live). Resmara never sees the card number.
function addPaymentCard() {
  const live = window.RM && RM.isLoggedIn && RM.isLoggedIn() && RM.addCard;
  if (live) { RM.addCard().then(r => { if (r && r.url) location.href = r.url; }).catch(e => toast(e.message)); return; }
  workspaceTourCleanup?.();
  show(`<span class="eyebrow">PAYMENT METHOD</span><h2>Add a card.</h2><p>You’ll be taken to Stripe’s secure page to add your card. Resmara never sees or stores your card number.</p><p class="fine">Preview only: no card page opens from this review copy.</p><div class="modal-actions"><button type="button" class="nc-cancel" onclick="modal.close();if(state.firstRun&&!state.tourDone)workspaceTour(3)">Back</button><button class="campaign-primary" onclick="state.cardOnFile=true;persist();modal.close();toast('Card saved (preview).');if(state.firstRun&&!state.tourDone)workspaceTour(4)">Continue to Stripe</button></div>`);
}

// ===== Review copy: start over as a brand-new client =====
if (state.freshClient && typeof examples !== 'undefined') examples.splice(0);
function newClientDemo() {
  try { localStorage.clear(); } catch (e) {}
  state = { campaigns: [], freshClient: true, connected: false };
  examples.splice(0); persist();
  location.hash = ''; home(); window.scrollTo(0, 0);
  obPickScenario(false);
}
function obPickScenario(back) {
  const cur = state.mockScenario || 'ready';
  show(`<span class="eyebrow">MOCK CLIENT WALKTHROUGH</span><h2>What should we test?</h2><p>You’ll go through every step a new client sees. The Meta connection is simulated, so pick how their Meta setup should look.</p>
  <form onsubmit="event.preventDefault();state.mockScenario=this.sc.value;persist();${back ? 'onboard(0)' : 'obSignup()'}"><div class="ob-scenarios">${Object.entries(OB_SCENARIOS).map(([k, v]) => `<label><input type="radio" name="sc" value="${k}" ${k === cur ? 'checked' : ''}><span><b>${v.label}</b>${k === 'ready' ? '<small>Passes every check</small>' : '<small>Shows what happens when it fails</small>'}</span></label>`).join('')}</div>
  <div class="modal-actions"><span></span><button class="campaign-primary">${back ? 'Use this' : 'Start the walkthrough'}</button></div></form>`);
}
function obSignup() {
  show(`<span class="eyebrow">WELCOME TO RESMARA</span><h2>Create your account.</h2><p>Just the basics. Resmara learns the rest when you connect your Meta account.</p>
  <form onsubmit="event.preventDefault();obSignupDone(this)"><div class="nc-row name-row"><label class="field">First name<input name="first" required autocomplete="given-name" value="Jamie"></label><label class="field">Last name<input name="last" required autocomplete="family-name" value="Carter"></label></div>
  <label class="field">Email address<input name="email" type="email" required autocomplete="email"></label><label class="field">Password<input name="pw" type="password" required minlength="8" autocomplete="new-password" value="mockclient"></label>
  <p class="fine">Use one of your own emails if you like. The review copy can’t send email, so nothing actually arrives.</p><div class="modal-actions"><button type="button" class="nc-cancel" onclick="modal.close()">Cancel</button><button class="campaign-primary">Create account</button></div></form>`);
}
function obSignupDone(form) {
  state = { ...state, name: form.first.value.trim() + ' ' + form.last.value.trim(), email: form.email.value.trim(), firstRun: true, metaRequired: true };
  persist(); obCheckEmail();
}
// Email confirmation: the account opens only after the agent clicks the link we email them.
function obCheckEmail() {
  show(`<span class="robot-avatar ob-bot-lg" aria-hidden="true"></span><span class="eyebrow">CHECK YOUR EMAIL</span><h2>Confirm your email address.</h2><p>We sent a confirmation link to <b>${esc(state.email || 'your email')}</b>. Click it to confirm it’s you, then sign in with your new password.</p><p class="fine">Can’t find it? Check your spam folder, or <a href="#" onclick="toast('Confirmation email sent again.');return false">send it again</a>.</p><div class="modal-actions"><span></span><button class="campaign-primary" onclick="obSignIn()">Preview: I clicked the link</button></div>`);
}
function obSignIn() {
  show(`<span class="eyebrow">EMAIL CONFIRMED</span><h2>Sign in to Resmara.</h2><form onsubmit="event.preventDefault();state.clientSignedIn=true;persist();modal.close();metaGateOnLogin()"><label class="field">Email address<input type="email" required value="${esc(state.email || '')}" autocomplete="email"></label><label class="field">Password<input type="password" required autocomplete="current-password" value="mockclient"></label><p class="fine"><a href="#" onclick="forgotPassword();return false">Forgot your password?</a></p><div class="modal-actions"><span></span><button class="campaign-primary">Sign in</button></div></form>`);
}

// ---- Meta connection is required ------------------------------------------------------------
// Resmara can't post or run ads without the agent's Meta account, so step 1 can't be skipped.
// Until it's connected (or a setup session is booked), sign-in lands on Accounts with the prompt.
function metaBlocked() { return !!state.metaRequired && !state.connected; }
// What the account has actually done, read from the server (item 8). localStorage alone let a
// cleared browser skip the required Meta step, which is the one thing that must not be
// skippable — so on every sign-in the stored answers win over the local ones.
function hydrateOnboarding() {
  if (!(window.RM && RM.isLoggedIn && RM.isLoggedIn())) return Promise.resolve(null);
  return RM.onboardingState().then(st => {
    state.connected = !!st.meta_connected;
    state.metaRequired = !st.meta_connected;
    state.setupSession = st.setup_booked ? (state.setupSession || { booked: st.setup_booked_at }) : null;
    state.tourDone = !!st.tour_seen;
    persist();
    return st;
  }).catch(() => null);
}
function metaNagging() { return metaBlocked() && !state.setupSession; }
function metaRequiredPrompt() {
  dashboard('accounts');
  show(`<span class="robot-avatar ob-bot-lg" aria-hidden="true"></span><span class="eyebrow">META ACCOUNT NEEDED</span><h2>Please connect your Meta account.</h2><p>Resmara posts and runs ads through your Facebook Page, Instagram and ad account, so we can’t run campaigns for you until they’re connected.</p><div class="modal-actions"><button type="button" class="nc-cancel" onclick="obBook()">Book a free setup session</button><button class="campaign-primary" onclick="onboard(0)">Connect your Meta account</button></div>`);
}
function metaGateOnLogin() {
  hydrateOnboarding().then(() => {
    if (metaNagging()) { dashboard('accounts'); setTimeout(() => onboard(0), 400); return; }
    dashboard('campaigns');
    if (state.firstRun && !state.tourDone) setTimeout(() => onboard(state.connected ? 1 : 0), 400);
  });
}
// Closing step 1 without connecting goes to Accounts with the prompt.
modal.addEventListener('close', () => {
  const gated = modal.dataset.gate === 'meta';
  delete modal.dataset.gate;
  if (gated && metaNagging()) setTimeout(metaRequiredPrompt, 50);
});
// Booked but not connected: the agent can look around, but can't start a campaign.
function metaBlockedNotice() {
  show(`<span class="eyebrow">META ACCOUNT NEEDED</span><h2>Connect your Meta account first.</h2><p>${state.setupSession ? 'Your setup session is booked. Once we’ve connected your Facebook Page, Instagram and ad account together, you can run your first campaign.' : 'Resmara can’t run a campaign until your Facebook Page, Instagram and ad account are connected.'}</p><div class="modal-actions"><button type="button" class="nc-cancel" onclick="modal.close()">Close</button><button class="campaign-primary" onclick="onboard(0)">Connect your Meta account</button></div>`);
}
// Accounts page for an agent who signed up here: it shows what's missing until Meta is connected.
(function () {
  const base = accounts;
  accounts = function () {
    base();
    if (!state.metaRequired) return;
    const n = $('#connNotice'), d = $('#connDetail'), btn = $('#metaConnectBtn'), chk = $('#metaCheckBtn');
    if (state.connected) {
      if (n) { n.className = 'notice page-intro'; n.textContent = 'Your Meta account is connected. Resmara can post and run ads for you.'; }
      if (btn) { btn.textContent = 'Reconnect'; btn.onclick = () => onboard(0); }
    } else {
      if (n) { n.className = 'notice page-intro'; n.innerHTML = state.setupSession ? '<b>Your setup session is booked.</b> We’ll connect your Meta account together on the call. Campaigns can’t run until it’s connected.' : '<b>Please connect your Meta account so we can run campaigns for you.</b> Resmara can’t post or run ads until your Facebook Page, Instagram and ad account are connected.'; }
      if (btn) { btn.textContent = 'Connect your Meta account'; btn.onclick = () => onboard(0); }
    }
    if (chk) chk.onclick = () => onboard(0);
  };
})();

// ---- Page explainer boxes: shown the first 2 times each page is opened, then gone ------------
let introLastView = null;
(function () {
  const base = dashboard;
  dashboard = function (v = 'campaigns') {
    base(v);
    const seen = state.introViews || (state.introViews = {});
    if (v !== introLastView) { seen[v] = (seen[v] || 0) + 1; introLastView = v; persist(); }
    if (seen[v] > 2) document.querySelectorAll('#content .notice.page-intro:not(#connNotice)').forEach(n => n.remove());
    metaIssueBanner();
  };
})();
(function () {
  const base = details;
  details = function (i) { const out = base(i); metaIssueBanner(); return out; };
})();

// ---- Support replies: orange count on Support in the sidebar -----------------------------------
// When the team answers a request, the agent gets an email and an orange number on Support until
// they open the page. In the review copy the requests live in this browser and the team "replies"
// a few seconds after you send one, so you can see the whole loop.
function supportDemoMode() { return !supportSignedIn() && !!state.clientSignedIn; }
function demoTickets() {
  if (!state.demoTickets) {
    state.demoTickets = (state.freshClient || state.metaRequired) ? [] : [
      { id: 1042, subject: 'Can I swap the photo on my ad?', status: 'Answered', created_at: '2026-11-13T16:05', messages: [
        { from: 'You', text: 'The second card on my Oakridge carousel ad shows the garage. Can I use the pool photo instead?' },
        { from: 'Resmara team', text: 'Yes. Open the campaign, click the Photo carousel ad and upload the pool photo as a replacement. It updates the ad within a few minutes.', unread: true }] },
      { id: 1039, subject: 'Day 7 report question', status: 'Answered', created_at: '2026-11-12T10:30', messages: [
        { from: 'You', text: 'What counts as a "view" in my report?' },
        { from: 'Resmara team', text: 'A view is each time one of your posts or your ad shows on someone’s screen. Reach is how many different people saw it.', unread: true }] }
    ];
    persist();
  }
  return state.demoTickets;
}
function supportUnread() {
  if (supportDemoMode()) return demoTickets().reduce((n, t) => n + t.messages.filter(m => m.unread).length, 0);
  return Number(state.supportUnread) || 0;
}
function paintSupportBadge() {
  const btn = [...document.querySelectorAll('.side-nav button')].find(b => /Support/.test(b.textContent));
  if (!btn) return;
  btn.querySelector('.nav-badge')?.remove();
  const n = supportUnread();
  if (n) btn.insertAdjacentHTML('beforeend', `<span class="nav-badge" aria-label="${n} new ${n > 1 ? 'replies' : 'reply'}">${n}</span>`);
}
(function () {
  const base = dashboard;
  dashboard = function (v = 'campaigns') {
    base(v); paintSupportBadge();
    // Live app: ask the API how many team replies the agent hasn't seen yet.
    if (supportSignedIn() && window.RM && RM.tickets) RM.tickets().then(rows => {
      state.supportUnread = (rows || []).reduce((n, t) => n + (Number(t.unread_replies) || 0), 0); persist(); paintSupportBadge();
    }).catch(() => {});
  };
})();
(function () {
  const baseLoad = loadMyTickets, baseSubmit = submitTicket, baseSupport = supportPage;
  supportPage = function () {
    baseSupport();
    if (!supportDemoMode()) return;
    // Signed in to the demo: show the form and list as if signed in.
    document.querySelectorAll('#content .notice').forEach(n => { if (/sign in first/i.test(n.textContent)) n.remove(); });
    const send = [...document.querySelectorAll('#content button')].find(b => b.textContent.trim() === 'Send request');
    if (send) send.onclick = () => submitTicket();
    [...document.querySelectorAll('#content button')].find(b => b.textContent.trim() === 'Sign in')?.remove();
    loadMyTickets();
  };
  loadMyTickets = function () {
    if (!supportDemoMode()) return baseLoad();
    const box = document.querySelector('#ticketList'); if (!box) return;
    const rows = demoTickets();
    box.innerHTML = rows.length ? rows.map(t => `<article class="panel ticket${t.messages.some(m => m.unread) ? ' has-new' : ''}" style="margin:0 0 12px">
      <div class="flex"><b>${esc(t.subject)}</b><span class="pill">${t.messages.some(m => m.unread) ? 'New reply' : esc(t.status)}</span></div>
      <p class="fine">Request #${esc(t.id)} · ${esc(niceDate(t.created_at.slice(0, 10)))}</p>
      ${t.messages.map(m => `<div class="ticket-msg${m.unread ? ' new' : ''}"><span class="eyebrow">${esc(m.from)}${m.unread ? ' · NEW' : ''}</span><p>${esc(m.text)}</p></div>`).join('')}
    </article>`).join('') : '<p class="fine">Nothing yet. Anything you send appears here with our reply.</p>';
    // Opening Support counts as reading the replies: the orange number clears.
    let changed = false; rows.forEach(t => t.messages.forEach(m => { if (m.unread) { m.unread = false; changed = true; } }));
    if (changed) { persist(); paintSupportBadge(); }
  };
  submitTicket = function () {
    if (!supportDemoMode()) return baseSubmit();
    const subject = ($('#ticketSubject') || {}).value || '', message = ($('#ticketMessage') || {}).value || '', msg = $('#ticketFormMsg');
    const say = (t, c) => { if (msg) { msg.className = 'fine ' + (c || ''); msg.textContent = t; } };
    if (!subject.trim() || !message.trim()) return say('A subject and a message, please.', 'bad');
    const t = { id: 1043 + demoTickets().length, subject: subject.trim(), status: 'Open', created_at: new Date().toISOString(), messages: [{ from: 'You', text: message.trim() }] };
    demoTickets().unshift(t); persist();
    $('#ticketSubject').value = ''; $('#ticketMessage').value = '';
    say('Sent. The Resmara team has been notified. We’ll email you and show a number on Support when we reply.', 'ok');
    loadMyTickets();
    // Preview: the team answers a few seconds later.
    setTimeout(() => {
      t.status = 'Answered';
      t.messages.push({ from: 'Resmara team', text: 'Thanks, we’re on it. (Preview reply: in the live app this is a real answer from our team.)', unread: true });
      persist(); paintSupportBadge();
      if (view === 'support') loadMyTickets(); else toast('New reply from the Resmara team. See Support.');
    }, 8000);
  };
})();


// ---- the readiness audit (step 1, item 8) ---------------------------------------------------
// Four things have to be true before Resmara can post and spend: a Page, admin rights on it, an
// Instagram professional account linked to it, and a way to pay. Each line is Meta's answer,
// and anything Meta does not answer says so instead of showing a tick.
function runMetaAudit() {
  const box = document.querySelector('#connDetail');
  const btn = document.querySelector('#metaAuditBtn');
  if (!(window.RM && RM.isLoggedIn())) { toast('Sign in first'); return; }
  if (btn) { btn.disabled = true; btn.textContent = 'Checking…'; }
  RM.onboardingAudit().then(r => {
    const rows = (r.checks || []).map(c => `<li class="audit-row ${c.ok ? 'ok' : 'bad'}"><b>${esc(c.label)}</b>` +
      `<small>${esc(c.detail || '')}</small>` + (c.ok ? '' : `<small class="fix">${esc(c.fix || '')}</small>`) + '</li>').join('');
    if (box) {
      box.innerHTML = (r.connected ? '' : `<p class="notice">${esc(state.message || 'Please connect your Meta account so we can run campaigns for you.')}</p>`) +
        `<ul class="audit-list">${rows}</ul>` +
        `<p class="fine">Once you've done this, come back here and click Check connection.</p>` +
        (r.connected ? '' : `<div class="btn-pair"><button class="campaign-primary" onclick="connectMeta()">Connect Meta</button><button class="alt" onclick="obBook()">Book a free setup session</button></div>`);
    }
    state.metaAudit = { status: r.connected && (r.checks || []).every(c => c.ok) ? 'ready' : 'blocked', checkedAt: new Date().toISOString() };
    state.connected = !!r.connected;
    persist();
    const bad = (r.checks || []).filter(c => !c.ok);
    toast(r.connected ? (bad.length ? `${bad.length} thing(s) still to fix` : 'You\'re ready to run campaigns.') : 'Meta is not connected yet.');
  }).catch(e => toast('Check failed: ' + e.message))
    .then(() => { if (btn) { btn.disabled = false; btn.textContent = 'Check again'; } });
}
