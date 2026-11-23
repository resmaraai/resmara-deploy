/* Slice 1: sign-up to first campaign, on real data.
 *
 *  - Engine 1 Part C: the live checklist after Log in with Facebook, the Page picker, the
 *    "already connected" screen, the Accounts setup box and the Meta notice, all from
 *    GET /api/onboarding/meta-audit (Meta's own answers, by name and photo).
 *  - Sign-up tour engine: the finish pop-up, the tour (fix first, then a look around, ending on
 *    the first campaign), the setup plan (Walk me through it) and Do it with our team.
 *  - Build first, then pay to unlock: the blurred campaign with Stripe's form embedded in the card,
 *    and one locked campaign at a time.
 *
 * Loaded after onboarding.js; it replaces that file's preview-only flow where they overlap.
 * Every fact on screen comes from the server. Nothing here decides whether Meta works.
 */
(function () {
  const S = (window.RMSignup = { status: null, brand: null, fixed: {}, tourResume: null });
  const live = () => !!(window.RM && RM.isLoggedIn && RM.isLoggedIn());
  const get = path => RM.request(path);
  const post = (path, body) => RM.request(path, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body || {}) });
  const first = () => String((S.status && S.status.facebook_name) || state.name || '').split(' ')[0] || 'there';
  const lock = on => modal.classList.toggle('af-locked', !!on);
  const NAVY = 'campaign-primary navy';
  const timeLabel = iso => {
    if (!iso) return '';
    const d = new Date(iso), now = new Date();
    const t = d.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' });
    return d.toDateString() === now.toDateString() ? 'today at ' + t : d.toLocaleDateString([], { month: 'short', day: 'numeric' }) + ' at ' + t;
  };

  // ------------------------------------------------------------------ the Meta status
  async function metaStatus(force) {
    const r = await get('/api/onboarding/meta-audit' + (force ? '?force=1' : ''));
    S.status = r;
    if (typeof applyMetaChecks === 'function') applyMetaChecks(r);
    state.metaChecked = !!r.facebook;
    state.metaLines = r.lines || [];
    persist();
    return r;
  }
  S.metaStatus = metaStatus;
  const issues = () => (S.status && S.status.issues) || [];
  const has = k => issues().includes(k);
  // The three things the setup plan covers, each ok or not, straight from the outcome keys.
  function setupState() {
    const st = S.status || {}, caps = st.capabilities || {};
    const pageOk = !!caps.fb_post;
    const igOk = !!caps.ig_post;
    const adOk = !!caps.ad;
    return { pageOk, igOk, adOk, igNone: !(st.pages || []).some(p => p.has_instagram), noCard: has('ad_no_payment') };
  }
  const planKeys = () => { const s = setupState(); return [!s.pageOk && 'page', !s.igOk && 'ig', !s.adOk && 'ad'].filter(Boolean); };

  // ------------------------------------------------------------------ Fix it now
  // One orange button, the single most useful fix for the top issue (Meta spec 8.1).
  window.metaFixIt = function (fix) {
    fix = fix || (S.status && S.status.fix) || {};
    workspaceTourCleanup?.();
    if (fix.kind === 'dialog') return connectMeta({ rerequest: true });
    if (fix.kind === 'reconnect') return connectMeta();
    if (fix.kind === 'page_picker') return has('page_taken') ? pageTaken() : pagePicker();
    if (fix.kind === 'ig_switch') return setupPlan('ig');
    if (fix.kind === 'setup') return setupPlan(fix.step === 'ads' ? 'ad' : 'page');
    if (fix.kind === 'book') return obBook(true);
    if (fix.kind === 'meta_billing') { window.open(fix.url, '_blank', 'noopener'); return; }
    return setupPlan();
  };
  // Reconnect and re-asking for an unticked permission are the same Facebook dialog.
  const baseConnect = window.connectMeta;
  window.connectMeta = function (opts) {
    if (!(opts && opts.rerequest)) return baseConnect();
    RM.request('/api/oauth/meta/connect?rerequest=1').then(r => { if (r && r.redirect_url) location.href = r.redirect_url; })
      .catch(e => toast('Could not open Facebook: ' + (e && e.message ? e.message : 'unknown error')));
  };

  // ------------------------------------------------------------------ 1. landing after Facebook
  window.metaGateOnLogin = async function () {
    await hydrateOnboarding();
    let st = null;
    try { st = await metaStatus(false); } catch (e) { /* the dashboard still opens */ }
    if (state.firstRun && !state.tourDone) return checklist(st);
    dashboard('campaigns');
  };

  // The live checklist (Part C, section 4): each line ticks as Meta's answer comes back, while the
  // brand engine works in the background. Then the finish pop-up.
  function checklist(st) {
    st = st || {};
    const page = st.page, ig = st.instagram, ad = st.ad_account;
    const lines = [
      ['Signing you in with Facebook', 'Signed in as ' + (st.facebook_name || 'you'), true],
      ['Finding your Facebook Page', page ? 'Facebook Page: ' + page.name : has('several_pages') ? 'Found ' + (st.pages || []).length + ' Pages' : 'No business Page yet', !!page || has('several_pages')],
      ['Checking your Instagram', ig ? 'Instagram: @' + ig.username : 'No business Instagram yet', !!ig],
      ['Checking your ad account', ad ? 'Ad account: ' + ad.name : 'No ad account yet', !!ad],
      ['Building your brand kit', 'Your brand kit is ready', true]
    ];
    show(`<span class="robot-avatar ob-bot-lg" aria-hidden="true"></span><span class="eyebrow">SETTING UP YOUR ACCOUNT</span><h2>Hi ${esc(first())}. Give me a moment.</h2><p>I’m looking at your Facebook, Instagram and ad account, and building your brand while I’m at it.</p><ul class="link-checks" id="su-checks">${lines.map((l, i) => `<li data-i="${i}">${esc(l[0])}…</li>`).join('')}</ul>`);
    lock(true);
    const mark = i => { const li = modal.querySelector(`#su-checks [data-i="${i}"]`); if (li) { li.className = lines[i][2] ? 'ok' : 'info'; li.textContent = lines[i][1]; } };
    let i = 0;
    const next = () => {
      if (i < 4) { mark(i++); return setTimeout(next, 650); }
      waitForBrand().then(() => { mark(4); setTimeout(afterChecklist, 700); });
    };
    setTimeout(next, 500);
  }
  async function waitForBrand() {
    const until = Date.now() + 90000;
    while (Date.now() < until) {
      try {
        const b = await get('/api/auth/me/brand/build');
        S.brand = b.brand || {};
        const status = (b.build || {}).status;
        if (status === 'done' || status === 'failed' || status === 'not_started') return S.brand;
      } catch (e) { return S.brand || {}; }
      await new Promise(r => setTimeout(r, 2500));
    }
    return S.brand || {};
  }
  function afterChecklist() {
    if (has('page_taken')) return pageTaken(true);
    if (has('several_pages')) return pagePicker(true);
    finishPopup();
  }

  // ------------------------------------------------------------------ the Page picker
  window.pagePicker = function (fromSignup) {
    const pages = (S.status && S.status.pages) || [];
    const av = p => p.picture ? `<img class="af-av" src="${esc(p.picture)}" alt="">` : `<span class="af-av">${esc((p.name || '?')[0])}</span>`;
    show(`<span class="eyebrow">YOUR FACEBOOK PAGE</span><h2>Which Page is your business?</h2><p>Resmara posts your listings to one Page. You can change it any time in Accounts.</p>
      <ul class="af-pages">${pages.map(p => `<li><button type="button" onclick="pagePick('${esc(p.id)}',${fromSignup ? 'true' : 'false'})">${av(p)}<span class="af-txt"><b>${esc(p.name)}</b>${p.ig_username ? `<small>@${esc(p.ig_username)}</small>` : ''}</span>${p.has_instagram ? '<span class="af-tag">Has Instagram</span>' : ''}</button></li>`).join('')}</ul>
      <p class="fine" id="pp-status" role="status"></p>`);
    lock(!!fromSignup);
  };
  window.pagePick = async function (id, fromSignup) {
    const s = document.getElementById('pp-status'); if (s) s.textContent = 'Checking that Page with Meta…';
    try {
      const r = await post('/api/onboarding/meta-page', { page_id: id });
      S.status = r; if (typeof applyMetaChecks === 'function') applyMetaChecks(r); persist();
      if (fromSignup) return finishPopup();
      lock(false); modal.close(); dashboard('accounts'); toast('Saved. Resmara posts to ' + ((r.page && r.page.name) || 'that Page') + ' now.');
    } catch (e) {
      const d = (e && e.detail) || {};
      if (d.error === 'page_taken') return pageTaken(fromSignup);
      if (s) s.textContent = (e && e.message) || 'That didn’t save. Try again.';
    }
  };
  // One Page, one Resmara account (Engine 1 Part B, section 3).
  window.pageTaken = function (fromSignup) {
    show(`<span class="eyebrow">YOUR FACEBOOK PAGE</span><h2>This Page is already connected to another Resmara account.</h2><p>If that account is yours, log in with the Facebook you used for it. If not, contact us and we’ll sort it out.</p>
      <div class="modal-actions"><button type="button" class="${NAVY}" onclick="lock0();dashboard('support')">Contact us</button><div class="ig-switch-go">${(S.status && (S.status.pages || []).length > 1) ? `<button type="button" class="${NAVY}" onclick="pagePicker(${fromSignup ? 'true' : 'false'})">Choose another Page</button>` : ''}<button class="campaign-primary" onclick="lock0();RM.logout&&RM.logout();state.clientSignedIn=false;persist();clientAccess()">Log in with a different Facebook</button></div></div>
      ${fromSignup ? `<p class="fine ob-skip"><a href="#" onclick="finishPopup();return false">Carry on without a Page for now</a></p>` : ''}`);
    lock(!!fromSignup);
  };
  window.lock0 = () => { lock(false); if (modal.open) modal.close(); };

  // ------------------------------------------------------------------ 2. the finish pop-up
  window.finishPopup = function () {
    const st = S.status || {}, b = S.brand || state.brand || {}, s = setupState();
    const fonts = b.fonts || ['Playfair Display', 'Jost'];
    (fonts || []).forEach(f => typeof loadGoogleFont === 'function' && loadGoogleFont(f));
    const sw = (b.palette || []).slice(0, 5).map(p => `<i style="background:${esc(p[1])}"></i>`).join('');
    const name = b.agent || st.facebook_name || state.name || '';
    const logo = b.logoUrl ? `<img class="fl-logo" src="${esc(b.logoUrl)}" alt="">` : `<span class="fl-logo" style="font-family:'${esc(fonts[0])}',serif">${esc((name || 'R')[0])}</span>`;
    const voc = String(b.voiceOfClient || '').split(/(?<=[.!?])\s+/).slice(0, 2).join(' ');
    const row = (label, ok, okText, noText) => `<div class="fl-row"><span>${label}</span><span class="af-st ${ok ? 'ok' : 'info'}">${ok ? '✓ ' + okText : noText}</span></div>`;
    show(`<span class="robot-avatar ob-bot-lg" aria-hidden="true"></span><h2>You’re all set up, ${esc(first())}.</h2><p>Here’s your brand and your Facebook. Let me show you around. It takes about a minute.</p>
      <div class="fl-card"><h3><span class="fl-tick">✓</span>Your brand</h3><div class="fl-kit">${logo}<div><div class="fl-name" style="font-family:'${esc(fonts[0])}',serif">${esc(name)}</div><small style="font-family:'${esc(fonts[1])}',sans-serif">${esc(fonts[0])} · ${esc(fonts[1])}${b.company ? ' · ' + esc(b.company) : ''}</small>${sw ? `<div class="fl-sw">${sw}</div>` : ''}</div></div>
        <p class="fl-sub">${b.license ? 'License #' + esc(b.license) : 'License number not found yet'}</p>${voc ? `<p class="fl-voice">“${esc(voc)}”</p>` : ''}</div>
      <div class="fl-card"><h3><span class="fl-tick">✓</span>Your Facebook</h3>
        ${row('Facebook Page', s.pageOk, st.page ? 'Connected' : 'Connected', 'Not set up yet')}
        ${row('Instagram', s.igOk, 'Connected', 'Not set up yet')}
        ${row('Ad account', s.adOk, 'Ready', has('ad_no_payment') ? 'No card on it' : 'Not set up yet')}</div>
      <div class="modal-actions"><span></span><button class="campaign-primary" onclick="lock0();startTour()">Show me around</button></div>`);
    lock(true);
  };

  // ------------------------------------------------------------------ 3. the tour
  // Fix first (only when something needs it), then a quick look around, ending on the first campaign.
  window.startTour = function () {
    const s = setupState(), b = S.brand || state.brand || {};
    const personal = !s.pageOk && !s.igOk;
    const why = planKeys().map(k => ({ page: 'a business Page to post to', ig: s.igNone ? 'a business Instagram' : 'your Instagram switched to business', ad: s.noCard ? 'a card on your ad account' : 'an ad account for your listing ad' }[k]));
    const fix = `<div class="tour-fix"><button type="button" class="campaign-primary" onclick="tourFix()">Walk me through it</button><button type="button" class="${NAVY}" onclick="tourBook()">Do it with our team</button></div>`;
    const steps = [];
    if (planKeys().length) {
      steps.push({ page: 'accounts', sel: '.meta-card', title: personal ? 'First, let’s get you set up for business.' : 'First, let’s sort out your Facebook.',
        text: personal ? `Like most agents, you’re starting with a personal Facebook${s.igNone ? ' and no Instagram yet' : ' and Instagram'}. To post and run ads for you, I need ${why.join(', ')}. It’s quick, and I’ll walk you through it.`
          : `Before your first campaign: ${why.join(', ')}. It’s quick, and I’ll walk you through it.`, extra: fix });
    }
    if ((b.missing || []).includes('license')) {
      steps.push({ page: 'brand', sel: '.mb-head', title: 'One thing is missing from your brand.', text: 'We couldn’t find your license number. It has to go on every post. Add it now, or when you start your first campaign.',
        extra: `<div class="tour-fix"><button type="button" class="campaign-primary" onclick="tourLicense()">Add it now</button></div>` });
    }
    steps.push(
      { page: 'campaigns', sel: '.add-campaign', title: 'This is the Campaign button.', text: 'All you need is your listing link. Resmara builds the rest.' },
      { page: 'campaigns', sel: '.camp-tabs', title: 'Your campaigns live here.', text: 'Active campaigns are running now. When one finishes it moves to Completed, where you can run it again.' },
      { page: 'brand', sel: '.mb-head', title: 'This is the brand we built for you.', text: 'Every post and ad follows it. You can change anything, any time.' },
      { page: 'credits', sel: '#billing-cards', box: true, title: 'This is Billing.', text: 'You don’t need a card yet: you’ll add one when you pay for your first campaign.' },
      { page: 'accounts', sel: '.meta-card', title: 'Your accounts.', text: 'Your Facebook Page, Instagram and ad account live here. If anything ever needs attention, this is where you’ll find it.' },
      { page: 'support', sel: '.grid2 .panel', title: 'Need a hand?', text: 'Send us a request any time. A real person reads every one and replies right here.' },
      { page: 'campaigns', sel: '.add-campaign', final: true, title: 'Let’s start your first campaign.', text: 'All you need is your listing link.',
        extra: `<div class="tour-fix"><button type="button" class="campaign-primary" onclick="tourFirstCampaign()">Let’s start your first campaign</button></div>` }
    );
    TOUR.splice(0, TOUR.length, ...steps);
    paintMenuMarks();
    workspaceTour(0);
  };
  window.tourFix = function () { S.tourResume = currentTourStep(); workspaceTourCleanup?.(); setupPlan(); };
  window.tourBook = function () { S.tourResume = currentTourStep(); workspaceTourCleanup?.(); obBook(true); };
  window.tourLicense = function () { S.tourResume = currentTourStep(); workspaceTourCleanup?.(); licenseBox(); };
  window.tourFirstCampaign = function () { workspaceTourCleanup?.(); tourDone(); newCampaign(); };
  const currentTourStep = () => { const t = document.querySelector('.workspace-tour-tip .eyebrow'); const m = t && t.textContent.match(/(\d+) OF/); return m ? Number(m[1]) - 1 : 0; };
  function resumeTour() { const i = S.tourResume; S.tourResume = null; if (i != null && state.firstRun && !state.tourDone) workspaceTour(Math.min(i + 1, TOUR.length - 1)); }
  // An orange mark on the menu item that needs something (Accounts, My Brand).
  function paintMenuMarks() {
    const need = { accounts: planKeys().length > 0, brand: ((S.brand || state.brand || {}).missing || []).includes('license') };
    document.querySelectorAll('.side-nav button').forEach(btn => {
      const m = (btn.getAttribute('onclick') || '').match(/dashboard\('(\w+)'\)/); if (!m) return;
      const dot = btn.querySelector('.af-dot');
      if (need[m[1]] && !dot) btn.insertAdjacentHTML('beforeend', '<span class="af-dot" aria-label="Needs attention">!</span>');
      if (!need[m[1]] && dot) dot.remove();
    });
  }
  S.paintMenuMarks = paintMenuMarks;

  // ------------------------------------------------------------------ the license number
  window.licenseBox = function () {
    show(`<div class="gd-head"><span class="robot-avatar" aria-hidden="true"></span><div><span class="eyebrow">YOUR BRAND</span></div></div><h2>Let’s add your license number.</h2><p>It has to go on every post, and we couldn’t find it on your pages or in the state lookup.</p>
      <form onsubmit="event.preventDefault();licenseSave(this)"><label class="field">License number<input name="license" required maxlength="40" placeholder="e.g. DRE #02123456"></label><p class="fine" role="status"></p>
      <div class="modal-actions"><button type="button" class="${NAVY}" onclick="lock0();resumeTourAfter()">Later</button><button class="campaign-primary">Save it</button></div></form>`);
    lock(true);
  };
  window.licenseSave = async function (form) {
    const v = form.license.value.trim(); if (!v) return;
    try {
      const b = { ...(S.brand || state.brand || {}), license: v };
      const saved = await RM.saveBrandProfile(b);
      S.brand = saved; state.brand = { ...state.brand, ...saved }; persist();
      show(`<div class="gd-win"><span class="robot-avatar" aria-hidden="true"></span><div class="gd-ok">✓</div><h2>Saved. It’s on every post now.</h2></div><div class="modal-actions"><span></span><button class="campaign-primary" onclick="lock0();resumeTourAfter()">${S.tourResume != null ? 'Continue the tour' : 'Done'}</button></div>`);
      paintMenuMarks();
    } catch (e) { form.querySelector('[role=status]').textContent = (e && e.message) || 'That didn’t save.'; }
  };
  window.resumeTourAfter = resumeTour;

  // ------------------------------------------------------------------ 4. the setup plan
  const PLAN = [
    ['page', 'Facebook business Page', 'About 5 minutes'],
    ['ig', 'Instagram business account, linked to your Page', 'About 2 minutes'],
    ['ad', 'Ad account with a card', 'About 3 minutes. Your posts go out without it; it runs your listing ad']
  ];
  const GUIDE_ID = { page: 'page', ig: 'instagram', ad: 'ads' };
  function guide(k) {
    const s = setupState();
    if (k === 'page' && has('page_no_control')) return { why: 'You manage this Page, but Meta says you don’t have full control, so Resmara can’t post to it.', steps: ['Ask the Page’s owner to open <b>Settings</b>, then <b>Page access</b>, and give you <b>full control</b>.', 'Come back here and press <b>Check again</b>.'] };
    if (k === 'page' && has('page_unpublished')) return { why: 'Your Page is unpublished, so no one can see it and posts would reach no one.', steps: ['Open your Page on Facebook and go to <b>Settings</b>.', 'Turn on <b>Page visibility: published</b>.', 'Come back here and press <b>Check again</b>.'] };
    if (k === 'page') return { why: 'Resmara posts to a business Page, not your personal profile. Until you have one, you download each post and share it yourself.', steps: ['Open <a href="https://www.facebook.com/pages/create" target="_blank" rel="noopener">Facebook’s Create a Page</a>.', 'Name it for your real estate business and pick the Real Estate Agent category.', 'Add your profile photo and a cover photo, then publish it.', 'Come back here and press <b>Check again</b>.'] };
    if (k === 'ig' && s.igNone) return { title: 'Create your Instagram business account', why: 'Resmara posts your listing to Instagram too. It’s free and takes a couple of minutes.', steps: ['Download Instagram and tap <b>Create new account</b>. Use your business name.', 'Go to <b>Settings</b>, then <b>Account type and tools</b>, and switch to a <b>Business</b> account.', 'Open <a href="https://www.facebook.com/settings/?tab=linked_instagram" target="_blank" rel="noopener">Facebook’s linked accounts</a> as your business Page and connect it.', 'Come back here and press <b>Check again</b>.'] };
    if (k === 'ig') return { why: 'Meta only lets Resmara post to business Instagram accounts. It’s free, takes about a minute, and you keep all your posts and followers.', steps: ['Open <a href="https://www.facebook.com/settings/?tab=linked_instagram" target="_blank" rel="noopener">Facebook’s linked accounts</a>, acting as your business Page.', 'Click <b>Connect account</b> next to Instagram and sign in.', 'When Facebook asks, choose <b>Business</b>.', 'Come back here and press <b>Check again</b>.'] };
    if (k === 'ad' && s.noCard) return { title: 'Add a card to your ad account', why: 'Your ad account is set up, but Meta needs a payment method before it can run your listing ad.', steps: ['Open <a href="https://business.facebook.com/billing_hub" target="_blank" rel="noopener">Meta’s Billing &amp; payments</a>.', 'Choose your ad account and click <b>Add payment method</b>.', 'Come back here and press <b>Check again</b>.'] };
    return { why: 'Your posts already go out. An ad account lets Resmara run your listing ad too, and Meta bills the ad budget to it directly.', steps: ['Open <a href="https://adsmanager.facebook.com" target="_blank" rel="noopener">Meta Ads Manager</a>.', 'Follow Meta’s steps to create an ad account in your name or your business name.', 'In <b>Payment settings</b>, add a card so Meta can bill your ad budget.', 'Come back here and press <b>Check again</b>.'] };
  }
  window.setupPlan = function (open, note) {
    const s = setupState(), ok = { page: s.pageOk, ig: s.igOk, ad: s.adOk };
    open = open && !ok[open] ? open : PLAN.map(p => p[0]).find(k => !ok[k]);
    if (!open) return setupDone();
    const left = PLAN.filter(p => !ok[p[0]]).length;
    const items = PLAN.map(([k, t, time], i) => {
      const g = guide(k), title = g.title || t;
      if (ok[k]) return `<li class="sp done"><span class="sp-num">✓</span><div class="sp-txt"><b>${title}</b><small>${S.fixed[k] ? 'Done just now' : 'Already set up'}</small></div></li>`;
      if (k !== open) return `<li class="sp"><span class="sp-num">${i + 1}</span><div class="sp-txt"><b>${title}</b><small>${k === 'ig' && !ok.page ? 'After your Page' : time}</small></div></li>`;
      return `<li class="sp open"><span class="sp-num">${i + 1}</span><div class="sp-txt"><b>${title}</b><p>${g.why}</p>
        ${note ? '<p class="sp-note"><b>Not quite yet.</b> Meta still shows the same thing. Sometimes it takes a few minutes to update.</p>' : ''}
        <ol class="gd-steps">${g.steps.map((x, j) => `<li><span>${j + 1}</span><div>${x}</div></li>`).join('')}</ol>
        <div class="sp-act"><span class="sp-left"><button type="button" class="${NAVY}" onclick="planBook()">Do it with our team</button><button type="button" class="${NAVY}" onclick="window.open(location.pathname + '#setup-guides-${GUIDE_ID[k]}', '_blank', 'noopener')">See the tutorial</button></span><button class="campaign-primary" onclick="planCheck('${k}')">${note ? 'Try again' : 'Check again'}</button></div></div></li>`;
    }).join('');
    show(`<div class="gd-head"><span class="robot-avatar" aria-hidden="true"></span><div><span class="eyebrow">GETTING YOU SET UP FOR BUSINESS</span><div class="gd-count">${left === 1 ? 'One thing left' : left + ' things left'} · about ${left === 3 ? 10 : left === 2 ? 7 : 5} minutes</div></div></div>
      <h2>Let’s get you set up for business.</h2><p>To post and run ads for you, Resmara needs these three things. I’ll walk you through each one, or our team can do it with you.</p>
      <ul class="sp-list">${items}</ul>
      <div class="modal-actions"><span></span><button type="button" class="${NAVY}" onclick="planLater()">Later</button></div>`);
    lock(true);
  };
  window.planCheck = async function (k) {
    const act = document.querySelector('.sp.open .sp-act');
    if (act) act.innerHTML = '<span class="sp-checking"><span class="robot-avatar" aria-hidden="true"></span>Checking with Meta…</span>';
    try { await metaStatus(true); } catch (e) { /* treated as not yet */ }
    const ok = { page: setupState().pageOk, ig: setupState().igOk, ad: setupState().adOk };
    if (ok[k]) { S.fixed[k] = true; return setupPlan(); }
    if (S.status && S.status.checking_unavailable) { toast('We couldn’t check with Meta right now. Try again in a minute.'); }
    setupPlan(k, true);
  };
  function setupDone() {
    const lic = ((S.brand || state.brand || {}).missing || []).includes('license');
    show(`<div class="gd-win"><span class="robot-avatar" aria-hidden="true"></span><div class="gd-ok">✓</div><h2>You’re set up for business, ${esc(first())}.</h2>
      <p>I can post to your Page and Instagram and run your listing ads now.${lic ? ' One last thing: your license number.' : ''}</p></div>
      <ul class="sp-list">${PLAN.map(([k, t]) => `<li class="sp done"><span class="sp-num">✓</span><div class="sp-txt"><b>${t}</b></div></li>`).join('')}</ul>
      <div class="modal-actions"><span></span>${lic ? '<button class="campaign-primary" onclick="licenseBox()">Add my license number</button>' : S.tourResume != null ? '<button class="campaign-primary" onclick="planLater()">Continue the tour</button>' : '<button class="campaign-primary" onclick="lock0();newCampaign()">Start a campaign</button>'}</div>`);
    lock(true);
    paintMenuMarks();
  }
  window.planLater = function () { lock0(); paintMenuMarks(); if (S.tourResume != null) return resumeTour(); if (view === 'accounts') accounts(); };
  window.planBook = function () { lock(false); obBook(true); };

  // ------------------------------------------------------------------ 5. Accounts: Your setup
  // One box: what's set up and what isn't, then one way through it (Adam, 22 Nov).
  window.accounts = function () {
    $('#content').innerHTML = `<div class="welcome"><h1>Your social connections.</h1></div><div class="panel meta-card" id="acc-box"><span class="eyebrow">YOUR SETUP</span><h3>Checking with Meta…</h3></div>`;
    if (!live()) { const b = $('#acc-box'); if (b) b.innerHTML = '<span class="eyebrow">YOUR SETUP</span><h3>Log in with Facebook to connect your accounts.</h3><div class="btn-pair"><button class="campaign-primary" onclick="clientAccess()">Log in with Facebook</button></div>'; return; }
    (S.status ? Promise.resolve(S.status) : metaStatus(false)).then(paintAccounts).catch(() => paintAccounts(S.status || {}));
  };
  function paintAccounts(st) {
    const box = $('#acc-box'); if (!box) return;
    st = st || {};
    const s = setupState(), page = st.page, ig = st.instagram, ad = st.ad_account;
    const doneAt = key => { const d = (st.done || []).slice().reverse().find(r => r.key === key); return d ? 'Done ' + timeLabel(d.fixed_at) : ''; };
    const items = [
      { ok: !!st.facebook, t: 'Sign in with Facebook', d: st.facebook ? 'Signed in as ' + esc(st.facebook_name || 'you') + '.' : 'Log in with Facebook to connect.' },
      s.pageOk ? { ok: true, t: 'Connect your Facebook Page', d: esc(page.name) + '. Resmara posts here.', when: doneAt('no_page') }
        : { ok: false, t: has('page_no_control') ? 'Get full control of your Page' : has('page_unpublished') ? 'Publish your Facebook Page' : has('several_pages') ? 'Choose your business Page' : 'Create a Facebook business Page', d: 'Resmara posts to a business Page, not your personal profile. Until then you download each post and share it yourself.' },
      s.igOk ? { ok: true, t: 'Connect your Instagram', d: '@' + esc(ig.username) + ', a business account linked to your Page.', when: doneAt('ig_not_linked') }
        : { ok: false, t: s.igNone ? 'Create an Instagram business account' : 'Switch your Instagram to a business account', d: s.pageOk ? 'Your posts go to Facebook only until it’s switched. It takes about a minute.' : 'Do this after your Page is set up.' },
      s.adOk ? { ok: true, t: 'Ad account ready', d: esc(ad.name) + ', with a card on file.', when: doneAt('no_ad_account') || doneAt('ad_no_payment') }
        : { ok: false, t: s.noCard ? 'Add a card to your ad account' : has('ad_disabled') ? 'Meta disabled your ad account' : has('ad_unpaid') ? 'Pay your Meta ad balance' : has('ad_in_review') ? 'Meta is reviewing your ad account' : 'Set up your ad account', d: 'Your posts still go out. Your listing ad is off until this is done.' }
    ];
    const left = items.filter(i => !i.ok);
    const list = items.map(i => `<li class="${i.ok ? 'done' : ''}"><span class="af-num">${i.ok ? '✓' : '!'}</span><span class="af-txt"><b>${i.t}</b><p>${i.d}</p>${i.ok && i.when ? `<small>${i.when}</small>` : ''}</span></li>`).join('');
    const top = (st.lines || [])[0];
    box.innerHTML = `<span class="eyebrow">YOUR SETUP</span><h3>${left.length ? (left.length === 1 ? 'One thing left to set up' : left.length + ' things left to set up') : 'Everything is set up'}</h3>
      <p>${left.length ? 'Here’s what’s ready and what isn’t. Each one ticks off on its own as soon as Meta shows it’s done.' : 'Resmara can post to your Page and Instagram and run your listing ads.'}</p>
      ${top && ['token_dead', 'token_expiring', 'scope_declined_page', 'scope_declined_ig', 'scope_declined_ads', 'page_taken'].includes(top.key) ? `<div class="af-note-box"><span class="af-dot">!</span><div><b>${esc(top.line)}</b><p>${esc(top.means)}</p></div><button class="campaign-primary" onclick="metaFixIt()">Fix it now</button></div>` : ''}
      <ul class="af-todo acc-one">${list}</ul>
      ${left.length ? `<div class="acc-help">
        <div><button class="campaign-primary" onclick="setupPlan()">Walk me through it</button><p>I’ll take you through ${left.length === 1 ? 'it' : 'all ' + left.length} step by step, on one screen. About ${left.length > 2 ? 10 : left.length * 4} minutes.</p></div>
        <div><button class="${NAVY}" onclick="obBook(true)">Do it with our team</button><p>Book a free 30-minute screen share and one of our team sets it up with you.</p></div></div>` : ''}
      <div class="af-meta"><span>${st.checking_unavailable ? 'We couldn’t check with Meta right now' : st.last_checked_at ? 'Last checked ' + timeLabel(st.last_checked_at) : ''}</span><span class="btn-pair" style="margin:0"><button class="alt" id="metaCheckBtn" onclick="accountsCheck(this)">Check again</button><button class="alt" onclick="connectMeta()">Reconnect</button>${(st.pages || []).length > 1 ? '<button class="alt" onclick="pagePicker()">Change Page</button>' : ''}</span></div>`;
    paintMenuMarks();
  }
  window.accountsCheck = async function (btn) {
    if (btn) { btn.disabled = true; btn.textContent = 'Checking…'; }
    try { await metaStatus(true); toast('Checked with Meta just now.'); } catch (e) { toast('We couldn’t check with Meta right now.'); }
    paintAccounts(S.status);
  };

  // ------------------------------------------------------------------ 6. the Meta notice
  // On every dashboard and campaign page while anything is wrong: at most three lines, Fix it now.
  window.metaIssueBanner = function () {
    const lines = (S.status && S.status.lines) || state.metaLines || [];
    const box = document.querySelector('#content');
    if (!box || !lines.length || box.querySelector('.meta-issue') || view === 'accounts') return;
    const caps = (S.status && S.status.capabilities) || {};
    const means = !caps.fb_post ? 'Resmara still builds your campaigns. Until it’s fixed, you download each post and share it yourself.' : lines[0].means;
    box.insertAdjacentHTML('afterbegin', `<div class="meta-issue" role="alert"><b class="meta-issue-title">There’s an issue with your Meta account.</b><ul>${lines.map(l => `<li>${esc(l.line)}</li>`).join('')}</ul><p>${esc(means)}</p><div class="meta-issue-actions">${lines[0].fix && lines[0].fix.kind ? '<button type="button" class="mi-btn mi-main" onclick="metaFixIt()">Fix it now</button>' : ''}<button type="button" class="mi-btn" onclick="obBook(true)">Book a call to fix it</button><button type="button" class="mi-btn" onclick="metaStatus(true).then(()=>dashboard(view))">Check again</button></div></div>`);
  };
  window.metaStatus = metaStatus;
  // Campaigns only need the Facebook login (download mode otherwise): never block + Campaign on Meta.
  window.metaBlocked = function () { return live() ? !(S.status && S.status.facebook) && !state.metaChecked && !!state.metaRequired : false; };

  // ------------------------------------------------------------------ 7. pay to unlock
  // The campaign opens blurred with one card on top: Stripe's form embedded in it.
  let stripeJs = null;
  function loadStripe() {
    if (window.Stripe) return Promise.resolve(window.Stripe);
    if (stripeJs) return stripeJs;
    stripeJs = new Promise((res, rej) => { const s = document.createElement('script'); s.src = 'https://js.stripe.com/v3/'; s.onload = () => res(window.Stripe); s.onerror = () => rej(new Error('Stripe could not load.')); document.head.appendChild(s); });
    return stripeJs;
  }
  let checkoutInstance = null;
  window.unlockCard = async function (boostId, address, opts) {
    opts = opts || {};
    const price = (window.billingMoney && typeof BILLING_PRICE_CENTS !== 'undefined') ? billingMoney(opts.price_cents || BILLING_PRICE_CENTS) : '$49';
    const declined = opts.declined;
    show(`<div class="af-unlock-card"><span class="eyebrow">YOUR CAMPAIGN IS BUILT</span><h2>${esc(address || 'Your campaign')} is built.</h2>
      <p>Your 14 days of posts, your ad and your listing page are all here. Pay ${esc(price)} to unlock it, then review and launch.</p>
      ${declined ? `<div class="af-note-box"><span class="af-dot">!</span><div><b>Your payment didn’t go through.</b><p>Please check your card and try again. Nothing was charged, and your campaign is saved right here.</p></div></div>` : ''}
      <div id="unlock-checkout" class="unlock-checkout"><p class="fine">Loading Stripe’s secure form…</p></div>
      <label class="af-save"><input type="checkbox" id="unlock-save" ${opts.save === false ? '' : 'checked'} onchange="unlockCard(${Number(boostId)}, ${JSON.stringify(String(address || '')).replace(/"/g, '&quot;')}, {save:this.checked})"><span><b>Save this card for future campaigns</b><br>Skip this step next time: your next campaign unlocks as soon as it’s built.</span></label>
      <p class="fine">Stripe keeps your card. Resmara never sees or stores your card number. Your Meta ad budget is billed separately by Meta.</p>
      <div class="modal-actions"><span></span><button type="button" class="${NAVY}" onclick="unlockLater()">Later</button></div></div>`);
    lock(true);
    const save = document.getElementById('unlock-save');
    try {
      const Stripe = await loadStripe();
      const cfg = await RM.request('/api/billing/config');
      if (!cfg.enabled || !cfg.publishable_key) throw new Error('Card payments aren’t switched on yet.');
      if (checkoutInstance) { try { checkoutInstance.destroy(); } catch (e) {} checkoutInstance = null; }
      const stripe = Stripe(cfg.publishable_key);
      let sessionId = null;
      checkoutInstance = await stripe.initEmbeddedCheckout({
        fetchClientSecret: async () => {
          const r = await post('/api/billing/checkout', { boost_id: Number(boostId), embedded: true, save_card: !!(save && save.checked) });
          sessionId = r.session_id;
          if (r.status === 'already_paid') { unlocked(boostId); return ''; }
          return r.client_secret;
        },
        onComplete: async () => {
          const r = await get('/api/billing/checkout/' + encodeURIComponent(sessionId) + '/status').catch(() => ({}));
          if (r.status === 'paid') return unlocked(boostId);
          unlockCard(boostId, address, { declined: true });
        }
      });
      const mount = document.getElementById('unlock-checkout');
      if (mount) { mount.innerHTML = ''; checkoutInstance.mount('#unlock-checkout'); }
    } catch (e) {
      const mount = document.getElementById('unlock-checkout');
      if (mount) mount.innerHTML = `<p class="fine">${esc((e && e.message) || 'Stripe’s form didn’t load.')} Your campaign is saved; try again in a minute.</p>`;
    }
  };
  window.unlockLater = function () {
    if (checkoutInstance) { try { checkoutInstance.destroy(); } catch (e) {} checkoutInstance = null; }
    lock0(); dashboard('campaigns');
    toast('Your campaign is saved. Unlock it any time from My campaigns.');
  };
  function unlocked(boostId) {
    if (checkoutInstance) { try { checkoutInstance.destroy(); } catch (e) {} checkoutInstance = null; }
    lock0();
    const c = (state.campaigns || []).find(x => String(campaignBoostId(x)) === String(boostId));
    if (c) { c.locked = false; persist(); }
    liveCampaignsSyncedAt = 0;
    if (typeof openCampaignByBoost === 'function') openCampaignByBoost(boostId);
    if (typeof buildCampaignFromBackend === 'function') setTimeout(() => { try { reloadBuiltPosts(boostId); } catch (e) {} }, 50);
    toast('Unlocked. Review your posts, then launch.');
  }
  // After unlocking, the review screen reads the posts it couldn't read while locked.
  async function reloadBuiltPosts(boostId) {
    const r = typeof activeReview === 'function' ? activeReview() : null;
    if (!r) return;
    const posts = await RM.posts(boostId).catch(() => null);
    if (!Array.isArray(posts) || !posts.length) return;
    r.items = posts.map(p => ({ id: p.id, postId: p.id, day: p.day || 1, title: p.title || String(p.caption || 'Scheduled post').split(/[.\n]/)[0].slice(0, 42), kicker: p.kicker || '', overlay: p.overlay_text || '', room: p.photo_room || '', kind: p.kind === 'short_video' ? 'Video post' : 'Photo post', caption: p.caption || '', image: p.image_url || '', reviewed: p.client_status === 'approved' }));
    r.needsBuild = false; persist();
    if (typeof details === 'function' && typeof ReviewStudio !== 'undefined') details(ReviewStudio.active);
  }
  // One locked campaign at a time.
  window.unlockFirst = function (d) {
    show(`<span class="eyebrow">ONE AT A TIME</span><h2>Unlock ${esc(d.address)} first.</h2><p>Your campaign for ${esc(d.address)} is built and waiting. Unlock it to start another, or replace it with a new listing.</p>
      <div class="modal-actions"><button type="button" class="${NAVY}" onclick="replaceLocked(${Number(d.boost_id)})">Replace it</button><button class="campaign-primary" onclick="unlockCard(${Number(d.boost_id)}, ${JSON.stringify(String(d.address || '')).replace(/"/g, '&quot;')})">Unlock</button></div>`);
  };
  window.replaceLocked = async function (boostId) {
    try { await RM.hideBoost(boostId, true); } catch (e) { /* the list still refreshes */ }
    const c = (state.campaigns || []).find(x => String(campaignBoostId(x)) === String(boostId));
    if (c) { c.hidden = true; persist(); }
    liveCampaignsSyncedAt = 0; modal.close(); newCampaign();
  };

  // The build polls this; a locked result opens the pay card, a 409 opens the one-at-a-time card.
  const baseBuild = window.buildCampaignFromBackend;
  if (typeof baseBuild === 'function') {
    window.buildCampaignFromBackend = async function () {
      const boostId = typeof reviewCampaignBoostId === 'function' ? reviewCampaignBoostId() : null;
      const r = typeof activeReview === 'function' ? activeReview() : null;
      const out = await baseBuild.apply(this, arguments);
      if (boostId == null) return out;
      const bill = await RM.request('/api/billing/boost/' + boostId).catch(() => null);
      if (bill && bill.locked) {
        const c = (state.campaigns || []).find(x => String(campaignBoostId(x)) === String(boostId));
        if (c) { c.locked = true; persist(); }
        unlockCard(boostId, (r && r.address) || (c && c.address), { price_cents: bill.price_cents });
      }
      return out;
    };
  }

  // Locked campaigns on My campaigns: blurred, tagged, one button.
  const baseCard = window.campaignCard;
  if (typeof baseCard === 'function') {
    window.campaignCard = function (c, active) {
      const html = baseCard(c, active);
      if (!c || !c.locked) return html;
      const id = campaignBoostId(c);
      return `<div class="af-locked-card"><span class="af-lock-tag">Built · pay to unlock</span>${html.replace(/(<span class="pill[^"]*">)[^<]*(<\/span>)/, '$1Locked · Built · waiting for payment · Not live$2')}<div class="af-lock-act"><button class="campaign-primary" onclick="event.stopPropagation();unlockCard(${Number(id)}, ${JSON.stringify(String(c.address || '')).replace(/"/g, '&quot;')})">Unlock my campaign</button></div></div>`;
    };
  }
  // Opening a locked campaign shows the same pay card.
  const baseOpen = window.openCampaignByBoost;
  if (typeof baseOpen === 'function') {
    window.openCampaignByBoost = function (boostId) {
      const c = (state.campaigns || []).find(x => String(campaignBoostId(x)) === String(boostId));
      const out = baseOpen.apply(this, arguments);
      if (c && c.locked) setTimeout(() => unlockCard(boostId, c.address), 30);
      return out;
    };
  }

  // ------------------------------------------------------------------ + Campaign: what goes on every post
  // The kit never holds up sign-up; phone, license and brokerage are checked when they start a
  // campaign, and only what's missing is asked for, right here (Engine 2, section 6a).
  const baseNew = window.newCampaign;
  window.newCampaign = async function () {
    if (!live() || S.skipMissing || !state.clientSignedIn) { S.skipMissing = false; return baseNew.apply(this, arguments); }
    let r = null;
    try { r = await get('/api/auth/me/brand/build'); } catch (e) { return baseNew.apply(this, arguments); }
    S.brand = r.brand || {};
    const missing = (r.brand && r.brand.build) ? (r.missing || []) : [];
    if (!missing.length) return baseNew.apply(this, arguments);
    const label = { phone: 'Phone number', license: 'License number', brokerage: 'Brokerage' };
    const ph = { phone: 'e.g. 530-555-0101', license: 'e.g. DRE #02123456', brokerage: 'Your local office, e.g. Shasta Sotheby’s International Realty' };
    const names = missing.map(m => label[m].toLowerCase().replace('license number', 'license number'));
    const head = missing.length === 1 ? `Your ${names[0]} is missing.` : `Your ${names.slice(0, -1).join(', ')} and ${names.slice(-1)} are missing.`;
    show(`<span class="eyebrow">NEW CAMPAIGN</span><h2>${esc(head)}</h2><p>${missing.length === 1 ? 'It has' : 'They have'} to go on every post. Add ${missing.length === 1 ? 'it' : 'them'} once and ${missing.length === 1 ? 'it’s' : 'they’re'} saved on My Brand, so you’re never asked again.</p>
      <form onsubmit="event.preventDefault();missingSave(this)">${missing.map(m => `<label class="field">${label[m]}<input name="${m}" required maxlength="120" placeholder="${esc(ph[m])}"></label>`).join('')}<p class="fine" role="status"></p>
      <div class="modal-actions"><button type="button" class="${NAVY}" onclick="modal.close()">Cancel</button><button class="campaign-primary">Save and continue</button></div></form>`);
  };
  window.missingSave = async function (form) {
    const b = { ...(S.brand || {}) };
    ['phone', 'license', 'brokerage'].forEach(k => { if (form.elements[k]) b[k] = form.elements[k].value.trim(); });
    if (b.brokerage) { b.company = b.brokerage; state.company = b.brokerage; }
    try {
      const saved = await RM.saveBrandProfile(b);
      S.brand = saved; state.brand = { ...(state.brand || {}), ...saved }; persist();
      S.skipMissing = true; newCampaign();
    } catch (e) { form.querySelector('[role=status]').textContent = (e && e.message) || 'That didn’t save.'; }
  };

  // ------------------------------------------------------------------ routing
  // See the tutorial opens the Setup page at one guide, in a new tab.
  const h = location.hash || '';
  if (h.indexOf('#setup-guides-') === 0) setTimeout(() => setupGuides(h.slice(14)), 30);
  // Returning from Stripe for a redirect-based method: settle it, then open the campaign.
  const q = new URLSearchParams(location.search);
  if (q.get('checkout') === 'done' && q.get('session_id') && live()) {
    history.replaceState({}, '', location.pathname + location.hash);
    get('/api/billing/checkout/' + encodeURIComponent(q.get('session_id')) + '/status').then(r => {
      if (r.status === 'paid') { state.clientSignedIn = true; persist(); dashboard('campaigns'); unlocked(r.boost_id); }
    }).catch(() => {});
  }
  // A signed-in agent's Meta status on load, so the notice and menu marks are true from the start.
  if (live()) setTimeout(() => metaStatus(false).then(() => { paintMenuMarks(); if (typeof metaIssueBanner === 'function') metaIssueBanner(); }).catch(() => {}), 400);
})();
