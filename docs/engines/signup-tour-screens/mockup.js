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
  .ob-skip,.ob-skip *{color:#12354d}
  .af-st.info{background:#e2f0f8;color:#12354d;font-weight:500}
  .tour-fix{display:flex;gap:8px;flex-wrap:wrap;margin:10px 0 2px}
  .tour-fix button{padding:9px 16px;font-size:14px}
  .campaign-primary.navy{background:#12354d!important;color:#fff!important}
  .af-save{display:flex;gap:12px;align-items:flex-start;background:#e2f0f8;border-radius:12px;padding:12px 14px;margin:14px 0 4px;color:#12354d;cursor:pointer}
  .af-save input{width:20px;height:20px;margin:2px 0 0;accent-color:#d94c0d;flex:0 0 auto}
  .sp-list{list-style:none;margin:14px 0 4px;padding:0;display:grid;gap:8px}
  .sp{display:flex;gap:12px;align-items:flex-start;border:1px solid #d8effd;background:#fff;border-radius:14px;padding:12px 14px;color:#12354d}
  .sp.open{background:#e2f0f8;border-color:#e2f0f8}
  .sp.done{background:#fff}
  .sp-num{flex:0 0 30px;height:30px;border-radius:50%;background:#d94c0d;color:#fff;display:grid;place-items:center;font-weight:700}
  .sp.done .sp-num{background:#12354d}
  .sp:not(.open):not(.done) .sp-num{background:#fff;color:#12354d;border:2px solid #12354d}
  .sp-txt{flex:1;min-width:0}.sp-txt small{display:block;font-size:13px;color:#12354d;margin-top:2px}.sp-txt p{margin:6px 0 0;font-size:14px}
  .sp .gd-steps li{background:#fff}
  .sp-note{background:#fff;border-radius:10px;padding:8px 12px}
  .sp-act{display:flex;justify-content:space-between;gap:8px;flex-wrap:wrap}
  .sp-left{display:flex;gap:8px;flex-wrap:wrap}
  .sp-tut{text-decoration:none;display:inline-flex;align-items:center}
  .sp-checking{display:flex;align-items:center;gap:8px;font-weight:600;color:#12354d}.sp-checking .robot-avatar{width:30px;height:30px}
  .sg-video{position:relative;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:4px;aspect-ratio:16/9;background:#12354d;color:#fff;border-radius:14px;margin:10px 0 12px;text-align:center;padding:14px}
  .sg-video b{color:#fff;font-size:15px}.sg-video small{color:#fff;opacity:.85;font-size:12px;letter-spacing:0;text-transform:none}
  .sg-play{width:54px;height:54px;border-radius:50%;background:#d94c0d;position:relative;margin-bottom:6px}
  .sg-play:after{content:"";position:absolute;left:21px;top:16px;border-style:solid;border-width:11px 0 11px 17px;border-color:transparent transparent transparent #fff}
  .sg-card.sg-focus{outline:3px solid #d94c0d;outline-offset:4px}
  .af-locked-card{position:relative}
  .af-locked-card img{filter:blur(4px)}
  .af-lock-tag{position:absolute;top:12px;left:12px;z-index:2;background:#12354d;color:#fff;font-weight:600;font-size:13px;border-radius:999px;padding:6px 12px}
  .sx{border:1px solid #d8effd;border-radius:14px;padding:14px;margin:12px 0 4px;background:#fff;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif}
  .sx-wallets{display:grid;grid-template-columns:1fr 1fr;gap:8px}
  .sx-wallet{background:#000;color:#fff;border-radius:8px;text-align:center;padding:10px;font-weight:600;font-size:14px}
  .sx-or{display:flex;align-items:center;gap:10px;color:#6b7c93;font-size:13px;margin:12px 0 6px}.sx-or:before,.sx-or:after{content:"";flex:1;height:1px;background:#e3e8ee}
  .sx-label{font-size:13px;color:#30313d;margin:8px 0 4px}
  .sx-box{border:1px solid #e3e8ee;border-radius:8px;overflow:hidden;box-shadow:0 1px 1px rgba(0,0,0,.03)}
  .sx-f{padding:10px 12px;color:#8792a2;font-size:15px;display:flex;justify-content:space-between;align-items:center}
  .sx-num{border-bottom:1px solid #e3e8ee}.sx-row,.sx-row2{display:grid;grid-template-columns:1fr 1fr}.sx-row .sx-f:first-child,.sx-row2 .sx-f:first-child{border-right:1px solid #e3e8ee}
  .sx-brands{display:flex;gap:4px}.sx-brands i{font-style:normal;font-size:9px;font-weight:700;border:1px solid #e3e8ee;border-radius:3px;padding:1px 3px;color:#30313d}
  .sx-err{border-color:#df1b41}.sx-msg{color:#df1b41;font-size:13px;margin-top:6px}
  .sx-foot{font-size:12px;color:#6b7c93;margin-top:10px;text-align:center}.sx-foot b{color:#635bff}
  .sx-saved{display:flex;align-items:center;gap:12px;background:#e2f0f8;border-radius:12px;padding:12px 14px;margin:12px 0 4px;color:#12354d}
  .sx-saved small{display:block;font-size:13px}.sx-saved span:nth-child(2){flex:1}.sx-saved button{padding:8px 14px;font-size:14px}
  .sx-card{background:#12354d;color:#fff;border-radius:6px;font-size:11px;font-weight:800;padding:6px 8px}
  .af-unlock{align-items:flex-start;padding-top:20px}
  #content.af-blur-wrap{position:relative;min-height:80vh}
  #content.af-blur-wrap > *:not(.af-unlock){filter:blur(7px);pointer-events:none;user-select:none}
  .af-unlock{position:absolute;inset:0;display:flex;justify-content:center;align-items:flex-start;padding-top:40px;z-index:5}
  .af-unlock-card{background:#fff;color:#12354d;border-radius:20px;box-shadow:0 20px 60px rgba(18,53,77,.25);padding:24px 26px;max-width:560px;width:100%}
  .af-unlock-card h2{margin:6px 0 6px;color:#12354d}
  .af-save small{display:block;font-size:13px;margin-top:2px;color:#12354d}`;
  const st = document.createElement('style'); st.textContent = css; document.head.appendChild(st);

  const PAGE = { name: 'Jamie Carter Realty', init: 'JC' };
  const TEAM = { name: 'Summit Home Team', init: 'SH' };
  const IG = '@jamiecarterrealty';
  // results: [page, instagram, ad]; what each row says.
  const S = {
    personal: { label: 'Personal Facebook and Instagram only', sub: 'Most agents start here: no Page, no business Instagram, no ad account yet' },
    noIg:    { label: 'Personal Facebook only, no Instagram at all', sub: 'Nothing set up for business, and no Instagram account' },
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
  const PERS = (k = sc) => k === 'personal' || k === 'noIg';

  modal.addEventListener('cancel', e => { if (modal.classList.contains('af-locked')) e.preventDefault(); });
  window.afPick = function () {
    modal.classList.remove('af-locked'); afActive = false; brandMissing = false; fixed.page = fixed.ig = fixed.ad = fixed.lic = false; tourResume = null; doneCount = 0; workspaceTourCleanup?.();
    show(`<span class="eyebrow">SIGN-UP TOUR MOCKUP</span><h2>A new client signs up.</h2><p>Pick how their Facebook looks, then click through sign-up, the finish pop-up, the tour and the first campaign’s payment.</p>
    <form onsubmit="event.preventDefault();afSignup(this.sc.value)"><div class="ob-scenarios">${Object.entries(S).map(([k, v]) => `<label><input type="radio" name="sc" value="${k}" ${k === sc ? 'checked' : ''}><span><b>${v.label}</b><small>${v.sub}</small></span></label>`).join('')}</div>
    <div class="modal-actions"><span></span><button class="campaign-primary">Start as a new client</button></div></form>`);
  };

  // 1. Resmara's Create your account pop-up: Facebook first.
  // One door for everyone: the top-right Client Login and Let's get started open the same pop-up.
  window.afSignup = function (k) {
    if (k) sc = k;
    show(`<span class="eyebrow">WELCOME TO RESMARA</span><h2>Log in with Facebook.</h2>
    <p>New or returning, it’s the same button. <b>Have an account?</b> You’re signed straight in. <b>New to Resmara?</b> We set up your account and connect your Page, Instagram and ad account in one go.</p>
    <button type="button" class="su-fb" onclick="afFb(1)"><span class="su-ico">f</span>Continue with Facebook</button>
    <div class="su-why"><b>No Facebook account?</b> You’ll need one to use Resmara, because it runs your marketing on Facebook and Instagram. It’s free: <a href="https://www.facebook.com/r.php" target="_blank" rel="noopener" style="color:#12354d;text-decoration:underline">create one on Facebook</a>, then come back here. A personal account is fine; we’ll help you set up the business side.</div>
    <p class="fine">Nothing is ever posted without your approval.</p>
    <p class="fine ob-skip">Preview (${esc(S[sc].label)}): <a href="#" style="color:#12354d;text-decoration:underline" onclick="afPick();return false">try a different Meta setup</a></p>`);
  };
  // In this mockup, the site's Client Login button opens the same pop-up.
  const baseAccess = window.clientAccess;
  window.clientAccess = function (mode) { if (state.clientSignedIn) return dashboard('campaigns'); afSignup(); };

  // 2. Facebook's own window (the real one is Facebook's, opened as a pop-up).
  function fbWin(body) {
    show(`<div class="fb-mock fbw"><div class="fb-mock-bar">facebook.com · Log in with Facebook <em>PREVIEW</em></div><div class="fb-mock-body">
    <div class="fb-head"><span class="fb-logo">f</span><span class="fb-x">⇄</span><span class="robot-avatar" style="width:34px;height:34px;margin:0" aria-hidden="true"></span></div>${body}</div></div>
    <p class="fine" style="text-align:center;margin-top:10px">This is Facebook’s own window. Resmara can’t change how it looks.</p>`);
  }
  window.afGo = function () { afStart(sc); };
  window.afFb = function (step) {
    const pages = (sc === 'noPage' || PERS()) ? [] : sc === 'several' ? [[PAGE, true], [TEAM, true]] : [[PAGE, true]];
    const igs = (sc === 'noPage' || sc === 'igPers' || PERS()) ? [] : [IG];
    const ads = (sc === 'noAd' || PERS()) ? [] : ['Jamie Carter Realty'];
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
      ['Finding your Facebook Page', (k === 'noPage' || PERS(k)) ? 'No business Page found' : k === 'several' ? 'Found 2 Pages' : 'Found ' + PAGE.name, (k === 'noPage' || PERS(k)) ? 'No business Page yet' : ''],
      ['Checking your Instagram', 'Found ' + IG, k === 'noIg' ? 'No Instagram account found' : PERS(k) ? 'Your Instagram is a personal account' : k === 'noPage' ? 'No Page to check Instagram on' : 'Instagram isn’t a business account'],
      ['Checking your ad account', 'Found Jamie Carter Realty ad account', (k === 'noAd' || PERS(k)) ? 'No ad account yet' : 'Ad account has no card on it'],
      ['Looking at your posts', PERS(k) ? 'Studied your website and public profiles' : 'Read your last 30 posts', ''],
      ['Researching you and your brokerage', 'Found your license, brokerage and website', ''],
      ['Building your brand kit', 'Your brand kit is built', '']
    ];
    const res = [true, !(k === 'noPage' || PERS(k)), !(k === 'igPers' || k === 'noPage' || PERS(k)), !(k === 'noAd' || k === 'noCard' || PERS(k)), true, true, true];
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
    const P = PERS();
    const pageOk = fixed.page || !(sc === 'noPage' || P);
    const igOk = pageOk && (fixed.ig || (!(sc === 'igPers' || sc === 'noPage' || P) && chosen === PAGE));
    const adOk = fixed.ad || !(sc === 'noAd' || sc === 'noCard' || P);
    return { pageOk, igOk, adOk, fbOk: pageOk && igOk && adOk, licOk: fixed.lic || sc !== 'noLic' };
  }
  // Sign-up tour engine, step 1: the finish pop-up. Information only: their brand and Facebook status.
  function pill(ok, txt) { return `<span class="af-st ${ok ? 'ok' : 'info'}">${ok ? '✓ ' + txt : txt}</span>`; }
  function afFinish() {
    const st = afState(), P = PERS();
    const rows = [
      ['Facebook Page', st.pageOk ? chosen.name : 'No business Page yet', st.pageOk, st.pageOk ? 'Connected' : 'Not set up yet'],
      ['Instagram', st.igOk ? IG : sc === 'noIg' ? 'No Instagram yet' : P ? 'Personal account' : !st.pageOk ? 'Needs a Page first' : chosen === TEAM ? 'None on this Page' : 'Personal account', st.igOk, st.igOk ? 'Connected' : 'Not set up yet'],
      ['Ad account', (sc === 'noAd' || P) && !fixed.ad ? 'No ad account yet' : 'Jamie Carter Realty', st.adOk, st.adOk ? 'Ready' : sc === 'noCard' ? 'No card on it' : 'Not set up yet']
    ].map(r => `<div class="fl-row"><span><b>${r[0]}:</b> ${r[1]}</span>${pill(r[2], r[3])}</div>`).join('');
    show(`<span class="robot-avatar ob-bot-lg" aria-hidden="true"></span><span class="eyebrow">SETUP COMPLETE</span><h2>You’re all set up, Jamie.</h2>
    <p>Here’s your brand and your Facebook. Let me show you around. It takes about a minute.</p>
    <div class="fl-card"><h3>Your brand</h3>
      <div class="fl-kit"><span class="fl-logo">JC</span><div><div class="fl-name">Jamie Carter Realty</div><small>Playfair Display · Jost · ${st.licOk ? 'DRE #02123456' : 'License number not found yet'}</small><div class="fl-sw">${PALETTE.map(p => `<i style="background:${p[1]}"></i>`).join('')}</div></div></div>
      <p class="fl-voice"><b>Voice of the client:</b> ${VOICE.split('. ').slice(0, 2).join('. ')}.</p></div>
    <div class="fl-card"><h3>Your Facebook</h3>${rows}</div>
    <div class="modal-actions"><span></span><button class="campaign-primary" onclick="afDone()">Show me around</button></div>
    <p class="fine ob-skip">Preview (${esc(S[sc].label)}): <a href="#" style="color:#12354d;text-decoration:underline" onclick="afPick();return false">try another setup</a></p>`);
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
    history.replaceState(null, '', location.pathname + (location.hash || '#tour'));
    paintMenu();
    if (v === 'brand') paintBrand();
    else if (v === 'accounts') paintAccounts();
    else if (v === 'credits') paintBilling();
    else if (!v || v === 'campaigns') { paintAttention(); paintLocked(); }
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
    const setup = PERS() && ['page', 'ig', 'ad'].some(k => q.includes(k));
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
  const BOOK = `<button type="button" class="campaign-primary" style="background:#12354d;color:#fff" onclick="afTourBook()">Do it with our team</button>`;
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
    show(`<div class="gd-head"><span class="robot-avatar" aria-hidden="true"></span><div><span class="eyebrow">${PERS() ? 'GETTING YOU SET UP' : 'LET’S FIX IT TOGETHER'}</span><div class="gd-count">${doneCount + 1} of ${total}</div></div></div>${inner}`);
    modal.classList.add('af-locked');
  }
  let doneCount = 0;
  window.afGuide = function (key) {
    if (!key) return;
    if (key === 'page' || key === 'ig' || key === 'ad') return afSetup(key);
    const g = guideFor(key);
    guideShell(`<h2>${g.title}</h2><p>${g.why}</p><label class="field">License number<input id="gd-lic" placeholder="e.g. DRE #02123456"></label>
      <div class="modal-actions">${BOOK}<div class="ig-switch-go"><button type="button" class="nc-cancel" onclick="afLater()">Later</button><button class="campaign-primary" onclick="afWin('lic')">Save it</button></div></div>`);
  };

  // The setup plan: everything they need for business on one pop-up, ticked off in place.
  const PLAN = [
    ['page', 'Facebook business Page', 'About 5 minutes'],
    ['ig', 'Instagram business account, linked to your Page', 'About 2 minutes'],
    ['ad', 'Ad account with a card', 'About 3 minutes. Your posts go out without it; it runs your listing ad']
  ];
  function igGuide() {
    return sc === 'noIg' ? { title: 'Create your Instagram business account.', why: 'Resmara posts your listing to Instagram too. It’s free and takes a couple of minutes.',
      steps: ['Download Instagram and tap <b>Create new account</b>. Use your business name.', 'Go to <b>Settings</b>, then <b>Account type and tools</b>, and switch to a <b>Business</b> account.', 'Open <a href="https://www.facebook.com/settings/?tab=linked_instagram" target="_blank" rel="noopener">Facebook’s linked accounts</a> as your business Page and connect it.', 'Come back here and press <b>Check again</b>.'] } : guideFor('ig');
  }
  window.afSetup = function (open, note) {
    const st = afState(), ok = { page: st.pageOk, ig: st.igOk, ad: st.adOk };
    open = open && !ok[open] ? open : PLAN.map(p => p[0]).find(k => !ok[k]);
    if (!open) return afSetupDone();
    const n = PLAN.filter(p => !ok[p[0]]).length;
    const items = PLAN.map(([k, t, time], i) => {
      if (ok[k]) return `<li class="sp done"><span class="sp-num">✓</span><div class="sp-txt"><b>${t}</b><small>${fixed[k] ? 'Done just now' : 'Already set up'}</small></div></li>`;
      if (k !== open) return `<li class="sp"><span class="sp-num">${i + 1}</span><div class="sp-txt"><b>${t}</b><small>${k === 'ig' && !ok.page ? 'After your Page' : time}</small></div></li>`;
      const g = k === 'ig' ? igGuide() : guideFor(k);
      return `<li class="sp open"><span class="sp-num">${i + 1}</span><div class="sp-txt"><b>${t}</b><p>${g.why}</p>
        ${note ? `<p class="sp-note"><b>Not quite yet.</b> Meta still shows the same thing. Sometimes it takes a few minutes to update.</p>` : ''}
        <ol class="gd-steps">${g.steps.map((x, j) => `<li><span>${j + 1}</span><div>${x}</div></li>`).join('')}</ol>
        <div class="sp-act"><span class="sp-left"><button type="button" class="campaign-primary navy" onclick="afTourBook()">Do it with our team</button><button type="button" class="campaign-primary navy" onclick="window.open(location.pathname + '#setup-guides-${k === 'ad' ? 'ads' : k === 'ig' ? 'instagram' : 'page'}', '_blank', 'noopener')">See the tutorial</button></span><button class="campaign-primary" onclick="afSetupCheck('${k}')">${note ? 'Try again' : 'Check again'}</button></div>
        <p class="fine ob-skip" style="text-align:left">Preview: <a href="#" style="color:#12354d;text-decoration:underline" onclick="afSetupCheck('${k}',true);return false">see what happens if it’s not done yet</a></p></div></li>`;
    }).join('');
    show(`<div class="gd-head"><span class="robot-avatar" aria-hidden="true"></span><div><span class="eyebrow">GETTING YOU SET UP FOR BUSINESS</span><div class="gd-count">${n === 1 ? 'One thing left' : n + ' things left'} · about ${n === 3 ? 10 : n === 2 ? 7 : 5} minutes</div></div></div>
      <h2>Let’s get you set up for business.</h2><p>To post and run ads for you, Resmara needs these three things. I’ll walk you through each one, or our team can do it with you.</p>
      <ul class="sp-list">${items}</ul>
      <div class="modal-actions"><span></span><button type="button" class="nc-cancel" onclick="afLater()">Later</button></div>`);
    modal.classList.add('af-locked');
  };
  window.afSetupCheck = function (key, fail) {
    const li = document.querySelector('.sp.open .sp-act');
    if (li) li.innerHTML = '<span class="sp-checking"><span class="robot-avatar" aria-hidden="true"></span>Checking with Meta…</span>';
    setTimeout(() => { if (!fail) fixed[key] = true; afSetup(fail ? key : null, !!fail); }, 1200);
  };
  function afSetupDone() {
    const lic = afQueue().includes('lic');
    show(`<div class="gd-win"><span class="robot-avatar" aria-hidden="true"></span><div class="gd-ok">✓</div><h2>You’re set up for business, Jamie.</h2>
      <p>I can post to your Page and Instagram and run your listing ads now.${lic ? ' One last thing: your license number.' : ''}</p></div>
      <ul class="sp-list">${PLAN.map(([k, t]) => `<li class="sp done"><span class="sp-num">✓</span><div class="sp-txt"><b>${t}</b></div></li>`).join('')}</ul>
      <div class="modal-actions"><span></span>${lic ? `<button class="campaign-primary" onclick="afGuide('lic')">Add my license number</button>` : tourResume != null ? `<button class="campaign-primary" onclick="afLater()">Continue the tour</button>` : `<button class="campaign-primary" onclick="afLater(true)">Start a campaign</button>`}</div>`);
    modal.classList.add('af-locked');
  }
  window.afWin = function (key) {
    fixed[key] = true;
    const next = afQueue()[0];
    show(`<div class="gd-win"><span class="robot-avatar" aria-hidden="true"></span><div class="gd-ok">✓</div><h2>Saved. It’s on every post now.</h2><p>${next ? 'Next, let’s get you set up for business.' : 'That’s everything. You’re ready to build your first campaign.'}</p></div>
      <div class="modal-actions"><span></span>${next ? `<button class="campaign-primary" onclick="afGuide('${next}')">Let’s go</button>` : tourResume != null ? `<button class="campaign-primary" onclick="afLater()">Continue the tour</button>` : `<button class="campaign-primary" onclick="afLater(true)">Start a campaign</button>`}</div>`);
    modal.classList.add('af-locked');
  };
  window.afLater = function (start) {
    modal.classList.remove('af-locked'); modal.close(); doneCount = 0;
    if (tourResume != null) { const i = tourResume; tourResume = null; return workspaceTour(i); }
    const v = (document.querySelector('.side-nav button.active') || {}).getAttribute ? (document.querySelector('.side-nav button.active').getAttribute('onclick') || '').match(/dashboard\('(\w+)'\)/) : null;
    dashboard(start ? 'campaigns' : (v ? v[1] : 'campaigns'));
    if (start) toast('Preview: this opens a new campaign.');
  };

  // Sign-up tour engine, step 2: the tour. Anything that needs fixing first, then where
  // everything is, ending on "Let's start your first campaign".
  let tourResume = null;
  window.afDone = function () {
    modal.classList.remove('af-locked'); modal.close();
    afActive = true; state.metaIssues = []; state.cardOnFile = false; state.firstRun = true; state.tourDone = false; state.clientSignedIn = true; state.connected = true;
    const is = issues(), P = PERS();
    const fix = (key, label) => `<div class="tour-fix"><button type="button" class="campaign-primary" onclick="afTourFix('${key}')">${label}</button><button type="button" class="campaign-primary navy" onclick="afTourBook()">Do it with our team</button></div>`;
    const steps = [];
    if (is.fb) steps.push({ page: 'accounts', sel: '.meta-card', title: P ? 'First, let’s get you set up for business.' : 'First, let’s sort out your Facebook.',
      text: sc === 'noIg' ? 'You’re starting with a personal Facebook and no Instagram yet. To post and run ads for you, I need a business Page and a business Instagram. About 10 minutes, and I’ll walk you through it.' : P ? 'Like most agents, you’re starting with a personal Facebook and Instagram. To post and run ads for you, I need a business Page and a business Instagram. About 10 minutes, and I’ll walk you through it.' : 'Before your first campaign: ' + fbReason(is.st) + '. It’s quick, and I’ll walk you through it.',
      extra: fix(afQueue().find(k => k !== 'lic'), 'Walk me through it') });
    if (is.brand) steps.push({ page: 'brand', sel: '.mb-head', title: 'One thing is missing from your brand.',
      text: 'We couldn’t find your license number. It has to go on every post. Add it now, or when you start your first campaign.', extra: fix('lic', 'Add it now') });
    const nFix = steps.length;
    if (nFix) steps.push({ page: 'campaigns', sel: '.add-campaign', title: 'Now, a quick look around.', text: 'This is the Campaign button. Click it any time to start a new campaign. All you need is your listing link.' });
    else steps.push({ page: 'campaigns', sel: '.add-campaign', title: 'This is the Campaign button.', text: 'Click it any time to start a new campaign. All you need is your listing link.' });
    steps.push({ page: 'campaigns', sel: '.camp-tabs', title: 'Your campaigns live here.', text: 'Active campaigns are running now. When one finishes it moves to Completed, where you can run it again in one click.' });
    if (!is.brand) steps.push({ page: 'brand', sel: '.mb-head', title: 'This is the brand we built for you.', text: 'Resmara made it from your Facebook, Instagram and website. Every post and ad follows it. You can change it any time.' });
    steps.push({ page: 'credits', sel: '#billing-cards', box: true, title: 'This is Billing.', text: 'Your receipts and your card live here. You don’t need a card yet: you’ll add one when you pay for your first campaign.' });
    if (!is.fb) steps.push({ page: 'accounts', sel: '.meta-card', title: 'Your accounts.', text: 'Your Facebook Page, Instagram and ad account live here. If anything ever needs attention, this is where you’ll find it.' });
    steps.push({ page: 'support', sel: '.grid2 .panel', title: 'Need a hand?', text: 'Send us a request any time. A real person reads every one and replies right here.' });
    steps.push({ page: 'campaigns', sel: '.add-campaign', final: true, title: 'Let’s start your first campaign.', text: 'All you need is your listing link.', extra: '<div class="tour-fix"><button type="button" class="campaign-primary" onclick="afStartCampaign()">Let’s start your first campaign</button></div>' });
    TOUR.splice(0, TOUR.length, ...steps);
    tourResume = nFix;
    workspaceTour(0);
  };
  // "Walk me through it" from the tour: the walkthrough, then back to the tour where it left off.
  window.afTourFix = function (key) { workspaceTourCleanup?.(); afGuide(key); };
  // "Do it with our team" from the tour: book the setup session, then carry on with the tour.
  window.afTourBook = function () {
    workspaceTourCleanup?.(); obBook(true);
    const b = modal.querySelector('.modal-actions .nc-cancel');
    if (b) { b.textContent = tourResume != null ? 'Continue the tour' : 'Back'; b.className = 'campaign-primary'; b.setAttribute('onclick', "modal.classList.remove('wide-modal');afLater()"); }
  };

  // First campaign: listing link and photo permission, build everything, then pay to unlock it.
  window.afStartCampaign = function () { workspaceTourCleanup?.(); tourDone(); newCampaign(); };
  const baseNcBuild = window.ncBuild;
  window.ncBuild = function (form) {
    if (!afActive) return baseNcBuild(form);
    if (!form.rights.checked) return;
    const addr = (typeof ncTypedAddress === 'function' && ncTypedAddress(form)) || '905 Laurel Bend, Austin, TX';
    afBuild(addr.split(',')[0]);
  };
  let afAddr = '905 Laurel Bend';
  window.afBuild = function (addr) {
    afAddr = addr || afAddr;
    show(`<span class="robot-avatar ob-bot-lg" aria-hidden="true"></span><span class="eyebrow">BUILDING YOUR CAMPAIGN</span><h2>Building ${esc(afAddr)}.</h2><p>I’m reading your listing and building your whole campaign. A few minutes.</p><div id="ob-box"></div>`);
    modal.classList.add('af-locked');
    obWalk(document.querySelector('#ob-box'), [
      ['Reading your listing', 'Read the listing and researched the home', ''],
      ['Picking your best 14 photos', 'Picked your best 14 photos', ''],
      ['Writing your 14 days of posts', 'Wrote 14 days of posts in your voice', ''],
      ['Designing your posts', 'Designed your posts in your brand', ''],
      ['Building your ad and listing page', 'Built your ad and listing page', '']
    ], [true, true, true, true, true], '', () => afUnlock());
  };
  // The built campaign stays locked until it's paid for: blurred, with one card on top.
  const lockedIdx = () => state.campaigns.findIndex(x => x.locked);
  let gateDeclined = false;
  window.afUnlock = function (declined) {
    modal.classList.remove('af-locked'); if (modal.open) modal.close();
    if (!state.campaigns.some(x => x.address === afAddr)) {
      const id = 'preview-' + afAddr.toLowerCase().replace(/[^a-z0-9]+/g, '-');
      const c = { address: afAddr, area: 'Austin, TX · $1,150,000', image: 'sample/card-3.jpg', reviewId: id, scopeFirst: true, creditUsed: 1, paid: true, day: 0, locked: !state.cardOnFile };
      try { const scope = initialCampaignScope(c); scope.start = goLiveDate(scope.start); state.reviews = state.reviews || {}; state.reviews['review-' + id] = { v: 5, approved: false, scopeConfirmed: false, calendarApproved: false, items: sampleReviewItems(c), scope }; } catch (e) {}
      state.campaigns.unshift(c);
      if (!c.locked) { dashboard('campaigns'); details(0); toast('Built and paid: $49 charged to your saved Visa ending 4242.'); return; }
    }
    gateDeclined = !!declined;
    const i = lockedIdx(); if (i < 0) return;
    dashboard('campaigns'); details(i);
  };
  const baseDetails = window.details;
  window.details = function (i) {
    baseDetails(i);
    const c = [...state.campaigns, ...examples][i];
    if (c && c.locked) paintGate(c);
  };
  // Stripe's own card form, embedded in the card (Stripe Embedded Checkout). Fields shown here are
  // a picture of it: nothing typed in this preview goes anywhere.
  const stripeForm = (err) => `<div class="sx">
    <div class="sx-wallets"><span class="sx-wallet">Apple Pay</span><span class="sx-wallet">Google Pay</span></div>
    <div class="sx-or">Or pay with card</div>
    <div class="sx-label">Card information</div>
    <div class="sx-box${err ? ' sx-err' : ''}"><div class="sx-f sx-num">1234 1234 1234 1234<span class="sx-brands"><i>VISA</i><i>MC</i><i>AMEX</i></span></div><div class="sx-row"><div class="sx-f">MM / YY</div><div class="sx-f">CVC</div></div></div>
    ${err ? '<div class="sx-msg">Your card was declined. Please check your card and try again, or use another card.</div>' : ''}
    <div class="sx-label">Name on card</div><div class="sx-box"><div class="sx-f">Jamie Carter</div></div>
    <div class="sx-label">Country and ZIP</div><div class="sx-box sx-row2"><div class="sx-f">United States</div><div class="sx-f">ZIP</div></div>
    <div class="sx-foot">Secure payment by <b>stripe</b> · Resmara never sees your card number</div></div>`;
  function paintGate(c) {
    const box = document.querySelector('#content'); if (!box) return;
    box.classList.add('af-blur-wrap');
    const price = billingMoney(BILLING_PRICE_CENTS), declined = gateDeclined; gateDeclined = false;
    const saved = state.cardOnFile && !declined;
    box.querySelector('.af-unlock')?.remove();
    box.insertAdjacentHTML('beforeend', `<div class="af-unlock" role="dialog" aria-label="Unlock your campaign"><div class="af-unlock-card">
      <div class="gd-head"><span class="robot-avatar" aria-hidden="true"></span><div><span class="eyebrow">${declined ? 'PAYMENT' : 'YOUR CAMPAIGN IS READY'}</span></div></div>
      <h2>${declined ? 'Your payment didn’t go through.' : esc(c.address) + ' is built.'}</h2>
      <p>${declined ? 'Please check your card and try again. Nothing was charged, and your campaign is saved right here.' : `Your 14 days of posts, your ad and your listing page are all here. Pay <b>${price}</b> to unlock it, then review and launch.`}</p>
      ${saved ? `<div class="sx-saved"><span class="sx-card">VISA</span><span><b>Visa ending 4242</b><small>Your saved card</small></span><button type="button" class="campaign-primary navy" onclick="state.cardOnFile=false;afUnlock()">Use another card</button></div>` : stripeForm(declined)}
      ${saved ? '' : `<label class="af-save"><input type="checkbox" checked><span><b>Save this card for future campaigns</b><small>Skip this step next time: your next campaign unlocks as soon as it’s built.</small></span></label>`}
      <div class="modal-actions"><button type="button" class="nc-cancel" onclick="dashboard('campaigns')">Later</button><button class="campaign-primary" onclick="afPaid()">${declined ? 'Try again' : 'Unlock my campaign for ' + price}</button></div>
      <p class="fine ob-skip">Preview: ${declined ? '' : '<a href="#" style="color:#12354d;text-decoration:underline" onclick="afUnlock(true);return false">see a declined card</a> · '}<a href="#" style="color:#12354d;text-decoration:underline" onclick="afPick();return false">start over</a></p></div></div>`);
    window.scrollTo(0, 0);
  }
  // Guardrail: one locked campaign at a time.
  const baseNew = window.newCampaign;
  window.newCampaign = function () {
    const c = afActive && state.campaigns.find(x => x.locked);
    if (!c) return baseNew();
    show(`<div class="gd-head"><span class="robot-avatar" aria-hidden="true"></span><div><span class="eyebrow">ONE AT A TIME</span></div></div><h2>Unlock ${esc(c.address)} first.</h2>
      <p>Your campaign for ${esc(c.address)} is built and waiting. Unlock it to start another, or replace it with a new listing.</p>
      <div class="modal-actions"><button type="button" class="campaign-primary navy" onclick="modal.close();state.campaigns=state.campaigns.filter(x=>!x.locked);baseNewCampaign()">Replace it</button><button class="campaign-primary" onclick="afUnlock()">Unlock ${esc(c.address)}</button></div>`);
  };
  window.baseNewCampaign = baseNew;
  // On My campaigns, a locked campaign says so, and opening it shows the same pay gate.
  function paintLocked() {
    const c = state.campaigns.find(x => x.locked); if (!c) return;
    document.querySelectorAll('#content article.card').forEach(card => {
      if (!card.textContent.includes(c.address) || card.querySelector('.af-lock-tag')) return;
      card.classList.add('af-locked-card');
      card.insertAdjacentHTML('afterbegin', `<span class="af-lock-tag">Built · pay to unlock</span>`);
      const btn = [...card.querySelectorAll('button')].pop(); if (btn) btn.textContent = 'Unlock my campaign';
      card.querySelectorAll('span,small,em,p,div').forEach(el => {
        if (el.children.length) return;
        const t = el.textContent.trim();
        if (t === 'Staged') el.textContent = 'Locked';
        else if (t === 'Awaiting campaign generation') el.textContent = 'Built · waiting for payment';
        else if (t === 'Draft') el.textContent = 'Not live';
      });
    });
  }
  window.afFirstCampaign = window.afUnlock;
  window.afPaid = function () {
    state.cardOnFile = true; state.campaigns.forEach(x => { x.locked = false; });
    document.querySelector('.af-unlock')?.remove();
    document.querySelector('#content')?.classList.remove('af-blur-wrap');
    toast('Paid. Your campaign is unlocked. Review it, then launch.');
  };
  window.afDeclined = function () { afUnlock(true); };
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
      show(`<span class="eyebrow">LOG IN</span><h2>This Page is already on Resmara.</h2>
      <ul class="af-found">${row(PAGE.init, '', 'Facebook Page', PAGE.name, 'Connected to another Resmara account', false, '')}</ul>
      <p>If that account is yours, log in with the Facebook you used for it. If not, contact us and we’ll sort it out.</p>
      <div class="modal-actions"><button type="button" class="campaign-primary navy" onclick="toast('Preview: this opens Support.')">Contact us</button><button class="campaign-primary" onclick="afPick()">Log in with a different Facebook</button></div>${again()}`);
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
           : { ok: false, t: sc === 'noIg' ? 'Create an Instagram business account' : 'Switch your Instagram to a business account', d: pageOk ? 'Your posts go to Facebook only until it’s switched. It takes about a minute.' : 'Do this after your Page is set up.', key: 'ig' },
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
  // Tutorials: the existing Setup page, opened at one guide, each guide with a short screen recording.
  const baseGuides = window.setupGuides;
  window.setupGuides = function (open) {
    baseGuides(open);
    document.querySelectorAll('.sg-card').forEach(card => {
      if (card.querySelector('.sg-video')) return;
      const h = card.querySelector('h3'); if (!h) return;
      h.insertAdjacentHTML('afterend', `<div class="sg-video" role="img" aria-label="Video: ${esc(h.textContent)}"><span class="sg-play"></span><b>Watch how: ${esc(h.textContent)}</b><small>A 1-minute explainer video: mock-up screens, step by step (AI-made, coming soon)</small></div>`);
    });
    const el = open && document.getElementById('sg-' + open); if (el) el.classList.add('sg-focus');
  };
  if (hash.indexOf('#setup-guides-') === 0) setTimeout(() => setupGuides(hash.slice(14)), 50);
  if (hash === '#tour') setTimeout(() => { history.replaceState(null, '', location.pathname + '#tour'); afPick(); }, 50);
  if (hash === '#audit') setTimeout(() => { history.replaceState(null, '', location.pathname + '#audit'); afPick(); }, 50);
  if (hash === '#signup') setTimeout(() => { history.replaceState(null, '', location.pathname + '#signup'); afSignup('personal'); }, 50);
})();
