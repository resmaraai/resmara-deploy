// Preview only (not for deploy): the Engine 1 and 2 clickable mockup Adam reviewed on 22 Nov 2026.
// Loaded by the review preview after preview-boot.js. Routes: #signup (Facebook sign-up, personal-only agent) and #audit (pick a setup).
// Review copy only: Engine 1, Part C mockup (PR #18). Not part of PR #17.
//   #audit  Continue with Facebook -> live checklist -> "Here's what we found".
(function () {
  const css = `
  .af-pick{display:grid;gap:8px;margin:14px 0}
  .af-pick label{display:flex;gap:10px;align-items:flex-start;border:1px solid #d8effd;background:#fff;border-radius:12px;padding:10px 12px;cursor:pointer;color:#12354d}
  .af-pick small{display:block;color:#12354d;opacity:.8}
  .af-found{list-style:none;margin:14px 0;padding:0;display:grid;gap:8px}
  .af-found li{display:flex;gap:12px;align-items:center;background:#e2f0f8;border-radius:12px;padding:10px 12px;color:#12354d}
  .af-av{flex:0 0 44px;height:44px;border-radius:50%;background:#12354d;color:#fff;display:grid;place-items:center;font-weight:600;font-size:15px}
  .af-av.ig{background:#d94c0d}.af-av.none{background:#fff;color:#12354d;border:1px dashed #12354d}
  .af-txt{flex:1;min-width:0}.af-txt small{display:block;color:#12354d;opacity:.85}
  .af-txt em{font-style:normal;font-size:12px;letter-spacing:.06em;text-transform:uppercase;display:block;margin-bottom:1px}
  .af-st{flex:0 0 auto;font-weight:600;font-size:13px;padding:4px 10px;border-radius:999px}
  .af-st.ok{background:#12354d;color:#fff}.af-st.bad{background:#d94c0d;color:#fff}
  .af-mean{margin:4px 0 0;font-size:13px;color:#12354d}
  .af-pages{list-style:none;margin:14px 0;padding:0;display:grid;gap:8px}
  .af-pages button{width:100%;display:flex;gap:12px;align-items:center;text-align:left;background:#fff;border:1px solid #d8effd;border-radius:12px;padding:10px 12px;color:#12354d;cursor:pointer}
  .af-pages button:hover{background:#eef8ff}
  .af-tag{margin-left:auto;font-size:12px;background:#e2f0f8;color:#12354d;border-radius:999px;padding:3px 9px}
  .af-note{font-size:13px;color:#12354d;margin-top:10px}
  .fl-card{background:#e2f0f8;border-radius:14px;padding:14px 16px;margin-top:12px;color:#12354d}
  .fl-card h3{margin:0 0 8px;font-size:17px;color:#12354d;display:flex;align-items:center;gap:8px}
  .fl-tick{width:22px;height:22px;border-radius:50%;background:#12354d;color:#fff;display:inline-grid;place-items:center;font-size:12px}
  .fl-tick.todo{background:#d94c0d}
  .fl-kit{display:flex;gap:14px;align-items:center;background:#fff;border-radius:12px;padding:12px}
  .fl-logo{flex:0 0 52px;height:52px;border-radius:50%;background:#2F4F3E;color:#fff;display:grid;place-items:center;font:600 18px 'Playfair Display',serif}
  .fl-sw{display:flex;gap:5px;margin-top:6px}.fl-sw i{width:22px;height:22px;border-radius:6px;border:1px solid #d8effd}
  .fl-name{font:600 19px 'Playfair Display',serif;color:#2F4F3E}
  .fl-voice{font-size:13px;margin:8px 0 0;color:#12354d}
  .fl-row{display:flex;justify-content:space-between;align-items:center;gap:10px;padding:7px 0;border-top:1px solid #d8effd;font-size:14px}
  .fl-row:first-of-type{border-top:0}
  .fl-row .af-st{font-size:12px;padding:3px 9px}
  .fl-sub{font-size:13px;margin:6px 0 0}
  .fl-btns{display:flex;justify-content:flex-end;gap:8px;margin-top:10px;flex-wrap:wrap}
  .fl-btns button{padding:9px 16px;font-size:14px}
  .vc-sec textarea{width:100%;min-height:150px;font-size:15px;line-height:1.5}
  .vc-note{font-size:13px;color:#12354d;margin-top:6px}
  .mb-field.miss input{border:2px solid #d94c0d!important;background:#fff6f1}
  .mb-field.miss span{color:#d94c0d}
  #modal.af-locked > .close{display:none}
  .af-dot{display:inline-grid;place-items:center;width:20px;height:20px;border-radius:50%;background:#d94c0d;color:#fff;font-size:12px;font-weight:700;margin-left:auto;flex:0 0 auto}
  .side-nav button{display:flex;align-items:center}
  .af-attn{display:flex;align-items:center;gap:10px;background:#e2f0f8;color:#12354d;border-radius:12px;padding:10px 14px;margin:0 0 18px;font-size:15px}
  .af-attn .af-dot{margin-left:0}
  .af-attn span:nth-child(2){flex:1}.af-attn button{padding:8px 16px;font-size:14px}
  .af-bot{width:40px;height:40px;flex:0 0 40px}
  .gd-head{display:flex;gap:12px;align-items:center;margin-bottom:6px}
  .gd-head .robot-avatar{width:54px;height:54px;flex:0 0 54px}
  .gd-steps{list-style:none;padding:0;margin:14px 0;display:grid;gap:8px}
  .gd-steps li{display:flex;gap:12px;align-items:flex-start;background:#e2f0f8;border-radius:12px;padding:10px 12px;color:#12354d}
  .gd-steps li span{flex:0 0 26px;height:26px;border-radius:50%;background:#d94c0d;color:#fff;display:grid;place-items:center;font-weight:700;font-size:13px}
  .gd-steps a{color:#12354d;text-decoration:underline}
  .gd-win{text-align:center}.gd-win .robot-avatar{width:84px;height:84px;margin:0 auto 6px;display:block}
  .gd-ok{width:56px;height:56px;border-radius:50%;background:#12354d;color:#fff;display:grid;place-items:center;font-size:28px;margin:6px auto}
  .gd-count{font-size:13px;color:#12354d}
  .af-note-box{display:flex;align-items:center;gap:14px;background:#e2f0f8;color:#12354d;border-radius:14px;padding:14px 18px;margin:0 0 18px}
  .af-note-box .af-dot{margin-left:0}.af-note-box div{flex:1}.af-note-box p{margin:2px 0 0;font-size:14px}
  .ns{background:#fff;border:1px solid #d8effd;border-radius:16px;padding:18px 20px;margin:0 0 22px;color:#12354d}
  .ns h2{margin:0 0 4px;font-size:22px}
  .ns > p{margin:0 0 10px}
  .mb-field.miss em{color:#d94c0d!important}.mb-field.miss em:before,.mb-field.miss em:after{content:none!important}
  .su-or{display:flex;align-items:center;gap:10px;margin:16px 0 6px;color:#12354d;font-size:13px}
  .su-or:before,.su-or:after{content:"";flex:1;height:1px;background:#d8effd}
  .su-fb,.su-g{width:100%;display:flex;align-items:center;justify-content:center;gap:10px;border-radius:999px;padding:13px 18px;font-weight:600;font-size:16px;cursor:pointer;border:0}
  .su-fb{background:#1877f2;color:#fff;margin-top:14px}
  .su-g{background:#fff;color:#12354d;border:1px solid #12354d;margin-top:10px}
  .su-ico{width:22px;height:22px;border-radius:50%;display:grid;place-items:center;font-weight:800;font-family:Arial,sans-serif;font-size:15px}
  .su-fb .su-ico{background:#fff;color:#1877f2}.su-g .su-ico{background:#12354d;color:#fff;font-size:13px}
  .su-why{background:#e2f0f8;border-radius:12px;padding:10px 14px;color:#12354d;font-size:14px;margin-top:12px}
  .fbw .fb-mock-body{text-align:left}
  .fbw .fb-head{display:flex;gap:10px;align-items:center;justify-content:center;margin-bottom:10px}
  .fbw .fb-logo{width:30px;height:30px;border-radius:50%;background:#1877f2;color:#fff;display:grid;place-items:center;font:800 20px Arial,sans-serif}
  .fbw .fb-x{color:#606770;font-size:18px}
  .fbw .fb-av{width:64px;height:64px;border-radius:50%;background:#12354d;color:#fff;display:grid;place-items:center;font-weight:700;font-size:22px;margin:4px auto 10px}
  .fbw .fb-center{text-align:center}
  .fbw .fb-sec{margin:14px 0 0}
  .fbw .fb-sec b{display:block;font-size:14px;color:#1c1e21;margin-bottom:6px}
  .fbw .fb-item{display:flex;align-items:center;gap:10px;border:1px solid #dde1e6;border-radius:8px;padding:8px 10px;margin-top:6px;font-size:14px;color:#1c1e21}
  .fbw .fb-item input{width:18px;height:18px;margin:0;accent-color:#1877f2}
  .fbw .fb-sq{width:28px;height:28px;border-radius:6px;background:#e4e6eb;display:grid;place-items:center;font-size:11px;font-weight:700;color:#1c1e21}
  .fbw .fb-none{font-size:13px;color:#606770;padding:6px 0}
  .fbw .fb-perm{display:flex;justify-content:space-between;align-items:center;gap:12px;padding:9px 0;border-bottom:1px solid #eef0f2;font-size:14px;color:#1c1e21}
  .fbw .fb-tog{width:38px;height:22px;border-radius:999px;background:#1877f2;position:relative;flex:0 0 auto}
  .fbw .fb-tog:after{content:"";position:absolute;right:3px;top:3px;width:16px;height:16px;border-radius:50%;background:#fff}
  .fbw .fb-fine{font-size:12px;color:#606770;margin-top:10px}
  .fbw .fb-done{width:54px;height:54px;border-radius:50%;background:#e7f3ff;color:#1877f2;display:grid;place-items:center;font-size:28px;margin:6px auto 10px}
  .af-todo{list-style:none;margin:14px 0 0;padding:0;display:grid;gap:10px}
  .af-todo li{display:flex;gap:14px;align-items:flex-start;background:#e2f0f8;border-radius:14px;padding:14px 16px;color:#12354d}
  .af-todo li.done{background:#fff;border:1px solid #d8effd}
  .af-num{flex:0 0 32px;height:32px;border-radius:50%;background:#d94c0d;color:#fff;display:grid;place-items:center;font-weight:700}
  .af-todo li.done .af-num{background:#12354d}
  .af-todo .af-txt p{margin:4px 0 0;font-size:14px}
  .af-todo .af-act{display:flex;gap:8px;margin-top:10px;flex-wrap:wrap}
  .af-todo .af-act button{padding:8px 14px;font-size:14px}
  .af-meta{display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap;margin-top:16px;color:#12354d;font-size:14px}
  .ob-skip,.ob-skip *{color:#12354d}`;
  const st = document.createElement('style'); st.textContent = css; document.head.appendChild(st);

  const PAGE = { name: 'Jamie Carter Realty', init: 'JC' };
  const TEAM = { name: 'Summit Home Team', init: 'SH' };
  const IG = '@jamiecarterrealty';
  // results: [page, instagram, ad]; what each row says.
  const S = {
    personal: { label: 'Personal Facebook and Instagram only', sub: 'Most agents start here: no Page, no business Instagram, no ad account yet' },
    ready:   { label: 'Everything is set up', sub: 'Page, business Instagram, ad account with a card' },
    noAd:    { label: 'No ad account', sub: 'Most common for new agents' },
    noCard:  { label: 'Ad account, no card on it', sub: 'Meta can’t bill the ad budget' },
    igPers:  { label: 'Instagram is a personal account', sub: 'Or not linked to the Page' },
    noPage:  { label: 'No Facebook business Page', sub: 'Personal profile only' },
    several: { label: 'Manages two Pages', sub: 'Their own Page and a team Page' },
    taken:   { label: 'Page already on another Resmara account', sub: 'A teammate connected it first' },
    noLic:   { label: 'Everything set up, but no license number found', sub: 'Brand kit has a gap' }
  };
  let sc = 'personal', chosen = PAGE;

  modal.addEventListener('cancel', e => { if (modal.classList.contains('af-locked')) e.preventDefault(); });
  window.afPick = function () {
    modal.classList.remove('af-locked'); afActive = false; brandMissing = false; fixed.fb = fixed.lic = fixed.card = false; doneCount = 0; workspaceTourCleanup?.();
    show(`<span class="eyebrow">ENGINE 1 MOCKUP · PR #18</span><h2>The audit.</h2><p>What a new agent sees straight after Continue with Facebook. Pick how their Meta setup looks.</p>
    <form onsubmit="event.preventDefault();afSignup(this.sc.value)"><div class="ob-scenarios">${Object.entries(S).map(([k, v]) => `<label><input type="radio" name="sc" value="${k}" ${k === sc ? 'checked' : ''}><span><b>${v.label}</b><small>${v.sub}</small></span></label>`).join('')}</div>
    <div class="modal-actions"><span></span><button class="campaign-primary">Start as a new client</button></div></form>`);
  };

  // 1. Resmara's Create your account pop-up: Facebook first.
  window.afSignup = function (k) {
    if (k) sc = k;
    show(`<span class="eyebrow">WELCOME TO RESMARA</span><h2>Create your account.</h2>
    <p>The quickest way is with Facebook. It creates your account and connects your Page, Instagram and ad account in one go.</p>
    <button type="button" class="su-fb" onclick="afFb(1)"><span class="su-ico">f</span>Continue with Facebook</button>
    <div class="su-or">or use your email</div>
    <form onsubmit="event.preventDefault();toast('Email sign-up: confirm your email, then Connect your Meta account comes next.')"><div class="nc-row name-row"><label class="field">First name<input name="first" autocomplete="given-name"></label><label class="field">Last name<input name="last" autocomplete="family-name"></label></div>
    <label class="field">Email address<input name="email" type="email" autocomplete="email"></label><label class="field">Password<input name="pw" type="password" autocomplete="new-password"></label>
    <div class="modal-actions"><button type="button" class="nc-cancel" onclick="modal.close()">Cancel</button><button class="campaign-primary">Create account</button></div></form>
    <p class="fine">Nothing is ever posted without your approval. Already have an account? <a href="#" style="color:#12354d;text-decoration:underline" onclick="return false">Sign in</a></p>
    <p class="fine ob-skip">Preview (${esc(S[sc].label)}): <a href="#" style="color:#12354d;text-decoration:underline" onclick="afPick();return false">try a different Meta setup</a></p>`);
  };

  // 2. Facebook's own window (the real one is Facebook's, opened as a pop-up).
  function fbWin(body) {
    show(`<div class="fb-mock fbw"><div class="fb-mock-bar">facebook.com · Log in with Facebook <em>PREVIEW</em></div><div class="fb-mock-body">
    <div class="fb-head"><span class="fb-logo">f</span><span class="fb-x">⇄</span><span class="robot-avatar" style="width:34px;height:34px;margin:0" aria-hidden="true"></span></div>${body}</div></div>
    <p class="fine" style="text-align:center;margin-top:10px">This is Facebook’s own window. Resmara can’t change how it looks.</p>`);
  }
  window.afGo = function () { afStart(sc); };
  window.afFb = function (step) {
    const pages = (sc === 'noPage' || sc === 'personal') ? [] : sc === 'several' ? [[PAGE, true], [TEAM, true]] : [[PAGE, true]];
    const igs = (sc === 'noPage' || sc === 'igPers' || sc === 'personal') ? [] : [IG];
    const ads = (sc === 'noAd' || sc === 'personal') ? [] : ['Jamie Carter Realty'];
    const item = (sq, name, on) => `<label class="fb-item"><input type="checkbox" ${on ? 'checked' : ''}><span class="fb-sq">${sq}</span>${name}</label>`;
    const none = t => `<div class="fb-none">${t}</div>`;
    if (step === 1) return fbWin(`<div class="fb-center"><div class="fb-av">JC</div><h3>Continue as Jamie?</h3>
      <p>Resmara will receive your name, profile picture and email address.</p></div>
      <div class="fb-mock-actions" style="flex-direction:column;align-items:stretch"><button type="button" class="fb-continue" onclick="afFb(2)">Continue as Jamie</button><button type="button" class="fb-cancel" onclick="afSignup()">Cancel</button></div>
      <p class="fb-fine" style="text-align:center">Resmara’s Privacy Policy and Terms</p>`);
    if (step === 2) return fbWin(`<h3 style="text-align:center">Choose what Resmara can access</h3><p style="text-align:center">Pick the Page, Instagram account and ad account for your listings.</p>
      <div class="fb-sec"><b>Pages</b>${pages.length ? pages.map(([p, on]) => item(p.init, p.name, on)).join('') : none('You don’t manage any Pages.')}</div>
      <div class="fb-sec"><b>Instagram accounts</b>${igs.length ? igs.map(i => item('IG', i, true)).join('') : none('No Instagram business accounts are linked to your Pages.')}</div>
      <div class="fb-sec"><b>Ad accounts</b>${ads.length ? ads.map(a => item('Ad', a, true)).join('') : none('You don’t have any ad accounts.')}</div>
      <div class="fb-mock-actions"><button type="button" class="fb-cancel" onclick="afFb(1)">Back</button><button type="button" class="fb-continue" onclick="afFb(3)">Continue</button></div>`);
    if (step === 3) return fbWin(`<h3 style="text-align:center">Review what Resmara can do</h3>
      <div class="fb-sec">${['Create and manage posts on your Page', 'Publish posts to your Instagram account', 'Create and manage ads in your ad account', 'Read how your posts and ads perform', 'Receive messages and comments from your Page'].map(t => `<div class="fb-perm">${t}<span class="fb-tog"></span></div>`).join('')}</div>
      <p class="fb-fine">You can change or remove Resmara’s access at any time in your Facebook settings.</p>
      <div class="fb-mock-actions"><button type="button" class="fb-cancel" onclick="afFb(2)">Back</button><button type="button" class="fb-continue" onclick="afFb(4)">Save</button></div>`);
    return fbWin(`<div class="fb-center"><div class="fb-done">✓</div><h3>You’ve now linked Resmara to Facebook</h3><p>Resmara can now access what you chose.</p></div>
      <div class="fb-mock-actions"><button type="button" class="fb-continue" onclick="afGo()">Got it</button></div>`);
  };

  window.afStart = function (k) {
    sc = k; chosen = PAGE;
    show(`<span class="eyebrow">STEP 1 OF 3</span><h2>Welcome, Jamie. Your account is ready.</h2><p>Now Resmara is checking your Facebook and building your brand kit. This takes a couple of minutes.</p><div id="ob-box"></div>`);
    modal.classList.add('af-locked');
    const labels = [
      ['Signing you in with Facebook', 'Signed in as Jamie Carter', ''],
      ['Finding your Facebook Page', (k === 'noPage' || k === 'personal') ? 'No business Page found' : k === 'several' ? 'Found 2 Pages' : 'Found ' + PAGE.name, (k === 'noPage' || k === 'personal') ? 'No business Page yet' : ''],
      ['Checking your Instagram', 'Found ' + IG, k === 'personal' ? 'Your Instagram is a personal account' : k === 'noPage' ? 'No Page to check Instagram on' : 'Instagram isn’t a business account'],
      ['Checking your ad account', 'Found Jamie Carter Realty ad account', (k === 'noAd' || k === 'personal') ? 'No ad account yet' : 'Ad account has no card on it'],
      ['Looking at your posts', k === 'personal' ? 'Studied your website and public profiles' : 'Read your last 30 posts', ''],
      ['Researching you and your brokerage', 'Found your license, brokerage and website', ''],
      ['Building your brand kit', 'Your brand kit is built', '']
    ];
    const res = [true, !(k === 'noPage' || k === 'personal'), !(k === 'igPers' || k === 'noPage' || k === 'personal'), !(k === 'noAd' || k === 'noCard' || k === 'personal'), true, true, true];
    obWalk(document.querySelector('#ob-box'), labels, res, '', () => k === 'several' ? afPages() : k === 'taken' ? afResult() : afFinish());
  };

  function afPages() {
    show(`<span class="eyebrow">STEP 1 OF 3</span><h2>Which Page is your business?</h2><p>You manage two Facebook Pages. Pick the one Resmara should post to. You can change it later in Accounts.</p>
    <ul class="af-pages">
      <li><button onclick="afChoose(0)"><span class="af-av">${PAGE.init}</span><span><b>${PAGE.name}</b><small style="display:block">Real estate agent</small></span><span class="af-tag">Has Instagram</span></button></li>
      <li><button onclick="afChoose(1)"><span class="af-av">${TEAM.init}</span><span><b>${TEAM.name}</b><small style="display:block">Real estate team</small></span></button></li>
    </ul>`);
  }
  window.afChoose = function (i) { chosen = i ? TEAM : PAGE; afFinish(); };

  function row(av, avCls, kind, name, detail, ok, mean) {
    return `<li><span class="af-av ${avCls}">${av}</span><span class="af-txt"><em>${kind}</em><b>${name}</b>${detail ? `<small>${detail}</small>` : ''}${mean ? `<p class="af-mean">${mean}</p>` : ''}</span><span class="af-st ${ok ? 'ok' : 'bad'}">${ok ? '✓ Ready' : 'Needs a fix'}</span></li>`;
  }


  // The onboarding finish line: brand kit + Facebook + card + first campaign, on one screen.
  const PALETTE = [['Primary', '#2F4F3E'], ['Accent', '#C46A3C'], ['Text', '#2B2B2B'], ['Tint', '#EEF2EC'], ['Page', '#FFFFFF']];
  const VOICE = 'Jamie is warm, upbeat and very local. She sells mostly in Redding and Shasta Lake, with a lot of first-time buyers and young families moving up. Her posts read like a friendly neighbour: short, encouraging, a bit of humour, and she often says “Let’s get you home.” She celebrates clients at closing and shares local spots. Keep it personal and upbeat; avoid hype words and anything that sounds like a big-brokerage ad.';
  function frow(label, name, ok, mean) {
    return `<div class="fl-row"><span><b>${label}:</b> ${name}${mean ? `<br><small>${mean}</small>` : ''}</span><span class="af-st ${ok ? 'ok' : 'bad'}">${ok ? '✓ Ready' : 'Needs a fix'}</span></div>`;
  }
  const fixed = { page: false, ig: false, ad: false, lic: false };
  function afState() {
    const P = sc === 'personal';
    const pageOk = fixed.page || !(sc === 'noPage' || P);
    const igOk = pageOk && (fixed.ig || (!(sc === 'igPers' || sc === 'noPage' || P) && chosen === PAGE));
    const adOk = fixed.ad || !(sc === 'noAd' || sc === 'noCard' || P);
    return { pageOk, igOk, adOk, fbOk: pageOk && igOk && adOk, licOk: fixed.lic || sc !== 'noLic' };
  }
  function afFinish() {
    const { pageOk } = afState();
    show(`<span class="robot-avatar ob-bot-lg" aria-hidden="true"></span><span class="eyebrow">SETUP COMPLETE</span><h2>You’re all set up, Jamie.</h2>
    <p>${sc === 'personal' ? 'Your brand kit is built from your website and public profiles. Next, I’ll help you set up your business Page and Instagram so I can post for you. First, a quick look around.' : 'Your brand kit is built' + (pageOk ? ' and your Facebook is connected' : '') + '. Let me show you around your dashboard. It takes about a minute.'}</p>
    <div class="fl-card"><h3><span class="fl-tick">✓</span>Your brand kit is built</h3>
      <div class="fl-kit"><span class="fl-logo">JC</span><div><div class="fl-name">Jamie Carter Realty</div><small>Playfair Display · Jost</small><div class="fl-sw">${PALETTE.map(p => `<i style="background:${p[1]}"></i>`).join('')}</div></div></div>
      <p class="fl-voice"><b>Voice of the client:</b> ${VOICE.split('. ').slice(0, 2).join('. ')}.</p></div>
    <div class="modal-actions"><span></span><button class="campaign-primary" onclick="afDone()">Show me around</button></div>${again()}`);
    modal.classList.add('af-locked');
  }
  // After setup: a clean dashboard, the Resmara tour, and notices that live on the menu items.
  let afActive = false, brandMissing = false;
  const baseDashboard = window.dashboard;
  function issues() {
    const st = afState();
    return { brand: !st.licOk || (brandMissing && !fixed.lic), card: false, fb: !st.fbOk, st };
  }
  function fbReason(st) {
    return !st.pageOk ? 'there’s no Facebook business Page connected yet'
      : !st.igOk ? 'your Instagram isn’t a business account, so posts go to Facebook only'
      : 'your ad account ' + (sc === 'noAd' ? 'is missing' : 'has no card on it') + ', so your listing ad can’t run yet';
  }
  window.dashboard = function (v) {
    if (afActive && v === 'brand') prepBrand();
    baseDashboard(v);
    if (!afActive) return;
    history.replaceState(null, '', location.pathname + '#audit');
    paintMenu();
    if (v === 'brand') paintBrand();
    else if (v === 'accounts') paintAccounts();
    else if (v === 'credits') paintBilling();
    else if (!v || v === 'campaigns') paintAttention();
  };
  function paintMenu() {
    const is = issues();
    const flag = { brand: is.brand, credits: is.card, accounts: is.fb };
    document.querySelectorAll('.side-nav button').forEach(btn => {
      const key = (btn.getAttribute('onclick') || '').match(/dashboard\('(\w+)'\)/);
      if (key && flag[key[1]] && !btn.querySelector('.af-dot')) btn.insertAdjacentHTML('beforeend', '<span class="af-dot">!</span>');
    });
  }
  function paintAttention() {
    const q = afQueue();
    if (!q.length) return;
    const c = document.querySelector('#content'); if (!c || c.querySelector('.af-attn')) return;
    const setup = sc === 'personal' && ['page', 'ig', 'ad'].some(k => q.includes(k));
    const msg = setup ? `<b>Let’s get you set up for business.</b> ${q.filter(k => k !== 'lic').length} quick steps so I can post and run ads for you. About 10 minutes.`
      : `<b>${q.length === 1 ? 'One thing needs' : 'A few things need'} your attention.</b> Want me to walk you through ${q.length === 1 ? 'it' : 'them'}?`;
    c.insertAdjacentHTML('afterbegin', `<div class="af-attn"><span class="robot-avatar af-bot" aria-hidden="true"></span><span>${msg}</span>${setup ? `<button class="campaign-primary" style="background:#12354d;color:#fff" onclick="obBook(true)">Do it with our team</button>` : ''}<button class="campaign-primary" onclick="afGuide(afQueue()[0])">${setup ? 'Let’s do it' : 'Let’s fix it'}</button></div>`);
  }
  function paintBilling() {
    return; // the card is asked for at the first campaign, not during onboarding
    if (state.cardOnFile) return;
    const c = document.querySelector('#content'); if (!c) return;
    c.insertAdjacentHTML('afterbegin', `<div class="af-note-box"><span class="af-dot">!</span><div><b>You don’t have a card on file.</b><p>You need one to build a campaign. You pay per listing, only when you launch.</p></div><button class="campaign-primary" onclick="afGuide('card')">Add a card</button></div>`);
  }

  // Resmara walks them through each thing that needs attention, one at a time.
  window.afQueue = function () { const st = afState(); return [!st.pageOk && 'page', !st.igOk && 'ig', !st.adOk && 'ad', !st.licOk && 'lic'].filter(Boolean); };
  const BOOK = `<button type="button" class="campaign-primary" style="background:#12354d;color:#fff" onclick="obBook(true)">Do it with our team</button>`;
  function guideFor(key) {
    const st = afState();
    if (key === 'page') return { title: 'Let’s set up your Facebook business Page.', why: 'Resmara posts to a business Page, not your personal profile. Until you have one, you download each post and share it yourself.',
      steps: ['Open <a href="https://www.facebook.com/pages/create" target="_blank" rel="noopener">Facebook’s Create a Page</a>.', 'Name it for your real estate business and pick the Real Estate Agent category.', 'Add your profile photo and a cover photo, then publish it.', 'Come back here and press <b>Check again</b>.'] };
    if (key === 'ig') return { title: 'Let’s switch your Instagram to a business account.', why: 'Meta only lets Resmara post to business Instagram accounts. It’s free, takes about a minute, and you keep all your posts and followers.',
      steps: ['Open <a href="https://www.facebook.com/settings/?tab=linked_instagram" target="_blank" rel="noopener">Facebook’s linked accounts</a>, acting as your business Page.', 'Click <b>Connect account</b> next to Instagram and sign in.', 'When Facebook asks, choose <b>Business</b>.', 'Come back here and press <b>Check again</b>.'] };
    if (key === 'ad' && sc !== 'noCard') return { title: 'Let’s set up your ad account.', why: 'Your posts already go out. An ad account lets Resmara run your listing ad too, and Meta bills the ad budget to it directly.',
      steps: ['Open <a href="https://adsmanager.facebook.com" target="_blank" rel="noopener">Meta Ads Manager</a>.', 'Follow Meta’s steps to create an ad account in your name or your business name.', 'In <b>Payment settings</b>, add a card so Meta can bill your ad budget.', 'Come back here and press <b>Check again</b>.'] };
    if (key === 'ad') return { title: 'Let’s add a card to your ad account.', why: 'Your ad account is set up, but Meta needs a payment method before it can run your listing ad.',
      steps: ['Open <a href="https://business.facebook.com/billing_hub" target="_blank" rel="noopener">Meta’s Billing &amp; payments</a>.', 'Choose your ad account and click <b>Add payment method</b>.', 'Come back here and press <b>Check again</b>.'] };
    if (key === 'lic') return { title: 'Let’s add your license number.', why: 'It has to go on every post, and we couldn’t find it on your pages or in the state lookup.', field: true };
    return { title: 'Let’s add your card.', why: 'You pay per listing, only when you launch a campaign. Stripe keeps your card; Resmara never sees the number.', card: true };
  }
  function guideShell(inner) {
    const q = afQueue(), total = q.length + doneCount;
    show(`<div class="gd-head"><span class="robot-avatar" aria-hidden="true"></span><div><span class="eyebrow">${sc === 'personal' ? 'GETTING YOU SET UP' : 'LET’S FIX IT TOGETHER'}</span><div class="gd-count">${doneCount + 1} of ${total}</div></div></div>${inner}`);
    modal.classList.add('af-locked');
  }
  let doneCount = 0;
  window.afGuide = function (key) {
    if (!key) return;
    const g = guideFor(key);
    if (g.field) return guideShell(`<h2>${g.title}</h2><p>${g.why}</p><label class="field">License number<input id="gd-lic" placeholder="e.g. DRE #02123456"></label>
      <div class="modal-actions">${BOOK}<div class="ig-switch-go"><button type="button" class="nc-cancel" onclick="afLater()">Later</button><button class="campaign-primary" onclick="afWin('lic')">Save it</button></div></div>`);
    if (g.card) return guideShell(`<h2>${g.title}</h2><p>${g.why}</p>
      <div class="modal-actions"><button type="button" class="nc-cancel" onclick="afLater()">Later</button><button class="campaign-primary" onclick="afWin('card')">Add a card</button></div><p class="fine">Preview: Add a card goes to Stripe’s secure page, then comes straight back here.</p>`);
    guideShell(`<h2>${g.title}</h2><p>${g.why}</p><ol class="gd-steps">${g.steps.map((t, i) => `<li><span>${i + 1}</span><div>${t}</div></li>`).join('')}</ol>
      <div class="modal-actions">${BOOK}<div class="ig-switch-go"><button type="button" class="nc-cancel" onclick="afLater()">Later</button><button class="campaign-primary" onclick="afCheck('${key}')">Check again</button></div></div>
      <p class="fine ob-skip">Preview: <a href="#" style="color:#12354d;text-decoration:underline" onclick="afCheck('${key}',true);return false">see what happens if it’s not fixed yet</a></p>`);
  };
  window.afCheck = function (key, fail) {
    guideShell(`<h2>Checking with Meta…</h2><div id="ob-box"></div>`);
    obWalk(document.querySelector('#ob-box'), [['Asking Meta about your account', fail ? 'Not fixed yet' : 'It’s fixed', 'Not fixed yet']], [!fail], '', () => {
      if (fail) {
        const g = guideFor(key);
        return guideShell(`<h2>Not quite yet.</h2><p>Meta still shows the same thing. Sometimes it takes a few minutes to update. Check the steps once more, or book a session and we’ll fix it with you.</p>
          <ol class="gd-steps">${g.steps.map((t, i) => `<li><span>${i + 1}</span><div>${t}</div></li>`).join('')}</ol>
          <div class="modal-actions">${BOOK}<div class="ig-switch-go"><button type="button" class="nc-cancel" onclick="afLater()">Later</button><button class="campaign-primary" onclick="afCheck('${key}')">Try again</button></div></div>`);
      }
      afWin(key);
    });
  };
  window.afWin = function (key) {
    fixed[key] = true; doneCount++;
    const next = afQueue()[0];
    const nextLine = next === 'lic' ? 'Next, let’s add your license number.' : next === 'ig' ? 'Next, let’s switch your Instagram to a business account.' : next === 'ad' ? 'Next, let’s get your ad account ready.' : 'That’s everything. You’re ready to build your first campaign.';
    show(`<div class="gd-win"><span class="robot-avatar" aria-hidden="true"></span><div class="gd-ok">✓</div><h2>${key === 'lic' ? 'Saved. It’s on every post now.' : key === 'page' ? 'Congratulations, your Page is connected!' : key === 'ig' ? 'Congratulations, your Instagram is ready!' : 'Congratulations, your ad account is ready!'}</h2><p>${nextLine}</p></div>
      <div class="modal-actions"><span></span>${next ? `<button class="campaign-primary" onclick="afGuide('${next}')">Let’s go</button>` : `<button class="campaign-primary" onclick="afLater(true)">Start a campaign</button>`}</div>`);
    modal.classList.add('af-locked');
  };
  window.afLater = function (start) {
    modal.classList.remove('af-locked'); modal.close(); doneCount = 0;
    const v = (document.querySelector('.side-nav button.active') || {}).getAttribute ? (document.querySelector('.side-nav button.active').getAttribute('onclick') || '').match(/dashboard\('(\w+)'\)/) : null;
    dashboard(start ? 'campaigns' : (v ? v[1] : 'campaigns'));
    if (start) toast('Preview: this opens a new campaign.');
  };

  window.afDone = function () {
    modal.classList.remove('af-locked'); modal.close();
    afActive = true; state.metaIssues = []; state.cardOnFile = false; state.firstRun = true; state.tourDone = false;
    const is = issues();
    TOUR[2].title = 'This is the brand we built for you.';
    TOUR[2].text = 'Resmara made it from your Facebook, Instagram and website. It’s what makes every post and ad look and sound like you. You can change it any time.' + (is.brand ? ' One thing is missing: your license number. Add it here before your first campaign.' : '');
    TOUR[3].text = 'Your receipts and your card live here. You don’t need a card yet: you’ll add one when you build your first campaign.'; TOUR[3].extra = '';
    TOUR[4].text = sc === 'personal' && is.fb ? 'This is your Facebook connection. Like most agents, you’re starting with a personal Facebook and Instagram. I’ll walk you through setting up your business Page and Instagram, about 10 minutes, or our team can do it with you.' : is.fb ? 'This is your Facebook connection. It looks like it needs attention: ' + fbReason(is.st) + '. Everything you need to fix it is here.' : 'Your Facebook Page, Instagram and ad account connection lives here. If anything ever needs attention, this is where you’ll find it.';
    workspaceTour(0);
  };
  window.afFinish = afFinish;

  // My Brand with the Voice of the client section (and the phone and broker license fields).
  window.afBrand = function (missing) {
    modal.classList.remove('af-locked'); modal.close();
    afActive = true; if (missing) brandMissing = true;
    dashboard('brand');
  };
  function prepBrand() {
    const missing = issues().brand;
    Object.assign(SAMPLE_BRAND, { agent: 'Jamie Carter', brokerage: 'Shasta Summit Realty', license: missing ? '' : 'DRE #02123456', website: 'https://jamiecarterrealty.com',
      market: 'Redding and Shasta Lake', brandLink: 'https://instagram.com/jamiecarterrealty', palette: PALETTE, fonts: ['Playfair Display', 'Jost'], voice: VOICE,
      use: ['Let’s get you home', 'Welcome home', 'Your Redding agent'], avoid: ['Stunning', 'Must-see', 'Hurry!'], theme: 'Match my brand',
      legal: ['Jamie Carter · REALTOR® · ' + (missing ? 'License number needed' : 'DRE #02123456'), 'Shasta Summit Realty · DRE #01987654', 'Equal Housing Opportunity'],
      sources: [['Facebook', 'Jamie Carter Realty'], ['Instagram', '@jamiecarterrealty'], ['Website', 'jamiecarterrealty.com'], ['State license lookup', 'DRE'], ['Brokerage', 'Shasta Summit Realty']], researched: 'Today, 9:16 AM' });
    state.name = 'Jamie Carter';
  }
  function paintBrand() {
    const missing = issues().brand;
    const form = document.querySelector('form.mb'); if (!form) return;
    form.querySelectorAll('.mb-mono').forEach(x => { x.textContent = 'JC'; });
    const hd = document.querySelector('.mb-id div'); if (hd) hd.innerHTML = '<b>Jamie Carter Realty</b><small>Jamie Carter · Shasta Summit Realty · Redding and Shasta Lake</small>';
    const grid = form.querySelector('.mb-grid');
    const fld = (name, label, value, src) => `<label class="mb-field"><span>${label}<em>${src}</em></span><input name="${name}" value="${esc(value)}"></label>`;
    grid.insertAdjacentHTML('beforeend', fld('phone', 'Phone', '(530) 555-0142', 'Facebook Page') + fld('brokerLicense', 'Broker license number', 'DRE #01987654', 'State license lookup'));
    form.querySelector('[name=agent]').closest('.mb-field').querySelector('em').textContent = 'Facebook Page';
    form.querySelector('[name=license]').closest('.mb-field').querySelector('em').textContent = missing ? 'Not found' : 'State license lookup';
    // Swap the small Voice box for the full Voice of the client section.
    const voiceSec = [...form.querySelectorAll('.mb-sec')].find(x => x.querySelector('h4') && x.querySelector('h4').textContent === 'VOICE');
    const pair = voiceSec.parentNode; voiceSec.remove();
    pair.insertAdjacentHTML('afterend', `<section class="mb-sec vc-sec"><h4>VOICE OF THE CLIENT</h4><textarea name="voice" rows="6">${esc(VOICE)}</textarea>
      <p class="vc-note">Resmara wrote this from your Facebook, Instagram and website. It’s how every post, caption, ad and listing page will sound. Rewrite anything that isn’t you, then save.</p>
      <div class="mb-chips">${SAMPLE_BRAND.use.map(w => `<span class="ok">“${esc(w)}”</span>`).join('')}${SAMPLE_BRAND.avoid.map(w => `<span class="no">${esc(w)}</span>`).join('')}</div></section>`);
    pair.style.gridTemplateColumns = '1fr';
    if (missing) document.querySelector('#content').insertAdjacentHTML('afterbegin', `<div class="af-attn"><span class="robot-avatar af-bot" aria-hidden="true"></span><span><b>Your license number is missing.</b> It has to go on every post.</span><button class="campaign-primary" onclick="afGuide('lic')">Add it with me</button></div>`);
    if (missing) { const f = form.querySelector('[name=license]').closest('.mb-field'); f.classList.add('miss');  }
    const c = document.querySelector('#content');
    c.insertAdjacentHTML('beforeend', `<p class="fine ob-skip" style="margin-top:14px;text-align:center">Preview: <a href="#" style="color:#12354d;text-decoration:underline" onclick="afMissing();return false">see the “license missing” check when they start a campaign</a> · <a href="#" style="color:#12354d;text-decoration:underline" onclick="afPick();return false">start over</a></p>`);
  }

  // The Campaign build engine's check on + Campaign (logged on Engine 4).
  window.afMissing = function () {
    show(`<div class="gd-head"><span class="robot-avatar" aria-hidden="true"></span><div><span class="eyebrow">BEFORE WE BUILD</span></div></div><h2>Your license number is missing.</h2>
    <p>It has to go on every post. Add it here and Resmara saves it to your brand, so you’re never asked again.</p><label class="field">License number<input placeholder="e.g. DRE #02123456"></label>
    <div class="modal-actions"><button type="button" class="nc-cancel" onclick="modal.close()">Cancel</button><button class="campaign-primary" onclick="modal.close();toast('Saved to My Brand. Building your campaign (preview).')">Save and continue</button></div>`);
  };


  function afResult() {
    const pageOk = sc !== 'noPage';
    const igOk = !(sc === 'igPers' || sc === 'noPage') && chosen === PAGE;
    const adOk = !(sc === 'noAd' || sc === 'noCard');
    if (sc === 'taken') {
      show(`<span class="eyebrow">STEP 1 OF 3</span><h2>This Page is already on Resmara.</h2>
      <ul class="af-found">${row(PAGE.init, '', 'Facebook Page', PAGE.name, 'Connected to another Resmara account', false, '')}</ul>
      <p>Ask the account holder to add you to their team. You’ll sign in with your own email and work on the same campaigns.</p>
      <div class="modal-actions"><button type="button" class="nc-cancel" onclick="obBook(true)">Book a call</button><button class="campaign-primary" onclick="afPick()">Sign out</button></div>${again()}`);
      return;
    }
    const rows = [
      pageOk ? row(chosen.init, '', 'Facebook Page', chosen.name, 'Published · you can post to it', true, '')
             : row('?', 'none', 'Facebook Page', 'No business Page found', 'Only your personal profile', false, 'Resmara still builds everything. You download each post and share it yourself until a Page is connected.'),
      pageOk ? (igOk ? row('IG', 'ig', 'Instagram', IG, 'Business account, linked to your Page', true, '')
                     : row('IG', 'none', 'Instagram', chosen === TEAM ? 'No Instagram on this Page' : IG, chosen === TEAM ? 'Nothing linked to ' + TEAM.name : 'Personal account, so Resmara can’t post to it', false, 'Your posts go to Facebook only until it’s a business account.'))
             : row('IG', 'none', 'Instagram', 'Not checked', 'Needs a Facebook Page first', false, ''),
      sc === 'noAd' ? row('Ad', 'none', 'Ad account', 'No ad account', '', false, 'Your posts still go out. Your listing ad is off until you have one.')
                    : row('Ad', adOk ? '' : 'none', 'Ad account', 'Jamie Carter Realty', adOk ? 'Active · card on file' : 'Active · no card on it', adOk, adOk ? '' : 'No ad until it has a payment method. Your posts still go out.')
    ];
    const allOk = pageOk && igOk && adOk;
    const head = allOk ? 'You’re all set.' : pageOk ? 'You’re ready to go.' : 'Resmara can build everything, but can’t post for you yet.';
    const lead = allOk ? 'Resmara can post to your Page and Instagram and run your listing ads.'
      : pageOk ? ([igOk, adOk].filter(x => !x).length > 1 ? 'A couple of things will make it better.' : 'One thing will make it better.') + ' Fix it now or any time from Accounts.'
      : 'Connect a Facebook business Page and the rest goes out on schedule.';
    const btns = allOk ? `<span></span><button class="campaign-primary" onclick="modal.close()">Build my brand</button>`
      : pageOk ? `<button type="button" class="nc-cancel" onclick="obBook(true)">Book a call</button><div class="ig-switch-go"><button type="button" class="nc-cancel" onclick="${igOk ? "setupGuides('ads');modal.close()" : 'obIgSwitch()'}">Fix it now</button><button class="campaign-primary" onclick="modal.close()">Build my brand</button></div>`
      : `<button type="button" class="nc-cancel" onclick="obBook(true)">Book a call</button><div class="ig-switch-go"><button type="button" class="nc-cancel" onclick="modal.close()">Continue anyway</button><button class="campaign-primary" onclick="setupGuides('page');modal.close()">Fix it now</button></div>`;
    show(`<span class="eyebrow">STEP 1 OF 3</span><h2>${head}</h2><p>${lead}</p><h3 style="margin:14px 0 0;color:#12354d">Here’s what we found</h3><ul class="af-found">${rows.join('')}</ul>
    ${pageOk ? '<p class="af-note">We also picked up your website and phone from your Page, so your brand kit starts filled in.</p>' : ''}
    <div class="modal-actions">${btns}</div>${again()}`);
  }
  function again() { return `<p class="fine ob-skip">Preview: <a href="#" style="color:#12354d;text-decoration:underline" onclick="afPick();return false">try another setup</a> · <a href="#" style="color:#12354d;text-decoration:underline" onclick="afAccounts();return false">see their setup to-do list in Accounts</a></p>`; }

  // The setup to-do list: what the audit found missing, in order, each ticked off by the next
  // check that passes. Lives in Accounts; drives the notice, the emails, Ask Resmara and the Team room.
  window.afAccounts = function () {
    modal.classList.remove('af-locked'); modal.close();
    afActive = true; dashboard('accounts');
  };
  function paintAccounts() {
    const { pageOk, igOk, adOk } = afState();
    const items = [
      { ok: true, t: 'Sign in with Facebook', d: 'Signed in as Jamie Carter.', when: 'Done today, 9:14 AM' },
      pageOk ? { ok: true, t: 'Connect your Facebook Page', d: chosen.name + '. Resmara posts here.', when: 'Done today, 9:14 AM' }
             : { ok: false, t: 'Create a Facebook business Page', d: 'Resmara posts to a business Page, not your personal profile. Until then you download each post and share it yourself.', key: 'page' },
      igOk ? { ok: true, t: 'Connect your Instagram', d: IG + ', a business account linked to your Page.', when: 'Done today, 9:14 AM' }
           : { ok: false, t: 'Switch your Instagram to a business account', d: pageOk ? 'Your posts go to Facebook only until it’s switched. It takes about a minute.' : 'Do this after your Page is set up.', key: 'ig' },
      adOk ? { ok: true, t: 'Ad account ready', d: 'Jamie Carter Realty, with a card on file.', when: 'Done today, 9:14 AM' }
           : { ok: false, t: sc !== 'noCard' ? 'Set up your ad account' : 'Add a card to your ad account', d: 'Your posts still go out. Your listing ad is off until this is done.', key: 'ad' }
    ];
    const left = items.filter(i => !i.ok);
    let n = 0;
    const list = [...left, ...items.filter(i => i.ok)].map(i => `<li class="${i.ok ? 'done' : ''}"><span class="af-num">${i.ok ? '✓' : ++n}</span><span class="af-txt"><b>${i.t}</b><p>${i.d}</p>${i.ok ? `<small>${i.when}</small>` : `<div class="af-act"><button class="campaign-primary" onclick="afGuide('${i.key}')">Walk me through it</button><button class="campaign-primary" style="background:#12354d;color:#fff" onclick="obBook(true)">Do it with our team</button></div>`}</span></li>`).join('');
    document.querySelector('#content').innerHTML = `<div class="welcome"><h1>Your social connections.</h1></div>
    <div class="panel meta-card"><span class="eyebrow">YOUR SETUP</span><h3>${left.length ? (left.length === 1 ? 'One thing left to set up' : left.length + ' things left to set up') : 'Everything is set up'}</h3>
    <p>${left.length ? 'Each one ticks off on its own as soon as Meta shows it’s done.' : 'Resmara can post to your Page and Instagram and run your listing ads.'}</p>
    <ul class="af-todo">${list}</ul>
    <div class="af-meta"><span>Last checked today at 9:14 AM</span><span class="btn-pair" style="margin:0"><button class="alt" onclick="toast('Checked just now. Nothing has changed.')">Check again</button><button class="alt" onclick="afPick()">Reconnect</button>${sc === 'several' ? '<button class="alt" onclick="afPick()">Change Page</button>' : ''}</span></div></div>
    <p class="fine ob-skip" style="margin-top:14px">Preview: <a href="#" style="color:#12354d;text-decoration:underline" onclick="afPick();return false">try another setup</a></p>`;
  }

  const hash = window.__previewHash || location.hash;
  if (hash === '#audit') setTimeout(() => { history.replaceState(null, '', location.pathname + '#audit'); afPick(); }, 50);
  if (hash === '#signup') setTimeout(() => { history.replaceState(null, '', location.pathname + '#signup'); afSignup('personal'); }, 50);
})();
