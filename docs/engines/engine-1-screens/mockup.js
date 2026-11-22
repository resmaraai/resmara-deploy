// Preview only (not for deploy): the Engine 1 clickable mockup Adam reviewed on 22 Nov 2026.
// Loaded by the review preview after preview-boot.js. Routes: #signup (Facebook sign-up) and #audit (pick a Meta setup).
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
    ready:   { label: 'Everything is set up', sub: 'Page, business Instagram, ad account with a card' },
    noAd:    { label: 'No ad account', sub: 'Most common for new agents' },
    noCard:  { label: 'Ad account, no card on it', sub: 'Meta can’t bill the ad budget' },
    igPers:  { label: 'Instagram is a personal account', sub: 'Or not linked to the Page' },
    noPage:  { label: 'No Facebook business Page', sub: 'Personal profile only' },
    several: { label: 'Manages two Pages', sub: 'Their own Page and a team Page' },
    taken:   { label: 'Page already on another Resmara account', sub: 'A teammate connected it first' }
  };
  let sc = 'ready', chosen = PAGE;

  window.afPick = function () {
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
    const pages = sc === 'noPage' ? [] : sc === 'several' ? [[PAGE, true], [TEAM, true]] : [[PAGE, true]];
    const igs = (sc === 'noPage' || sc === 'igPers') ? [] : [IG];
    const ads = sc === 'noAd' ? [] : ['Jamie Carter Realty'];
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
    show(`<span class="eyebrow">STEP 1 OF 3</span><h2>Welcome, Jamie. Your account is ready.</h2><p>Now Resmara is checking what’s connected to your Facebook. This takes a few seconds.</p><div id="ob-box"></div>`);
    const labels = [
      ['Signing you in with Facebook', 'Signed in as Jamie Carter', ''],
      ['Finding your Facebook Page', k === 'noPage' ? 'No business Page found' : k === 'several' ? 'Found 2 Pages' : 'Found ' + PAGE.name, k === 'noPage' ? 'No business Page found' : ''],
      ['Checking your Instagram', k === 'igPers' ? 'Instagram isn’t a business account' : 'Found ' + IG, k === 'igPers' || k === 'noPage' ? (k === 'noPage' ? 'No Page to check Instagram on' : 'Instagram isn’t a business account') : ''],
      ['Checking your ad account', 'Found Jamie Carter Realty ad account', k === 'noAd' ? 'No ad account' : 'Ad account has no card on it']
    ];
    const res = [true, k !== 'noPage', !(k === 'igPers' || k === 'noPage'), !(k === 'noAd' || k === 'noCard')];
    obWalk(document.querySelector('#ob-box'), labels, res, '', () => k === 'several' ? afPages() : afResult());
  };

  function afPages() {
    show(`<span class="eyebrow">STEP 1 OF 3</span><h2>Which Page is your business?</h2><p>You manage two Facebook Pages. Pick the one Resmara should post to. You can change it later in Accounts.</p>
    <ul class="af-pages">
      <li><button onclick="afChoose(0)"><span class="af-av">${PAGE.init}</span><span><b>${PAGE.name}</b><small style="display:block">Real estate agent</small></span><span class="af-tag">Has Instagram</span></button></li>
      <li><button onclick="afChoose(1)"><span class="af-av">${TEAM.init}</span><span><b>${TEAM.name}</b><small style="display:block">Real estate team</small></span></button></li>
    </ul>`);
  }
  window.afChoose = function (i) { chosen = i ? TEAM : PAGE; afResult(); };

  function row(av, avCls, kind, name, detail, ok, mean) {
    return `<li><span class="af-av ${avCls}">${av}</span><span class="af-txt"><em>${kind}</em><b>${name}</b>${detail ? `<small>${detail}</small>` : ''}${mean ? `<p class="af-mean">${mean}</p>` : ''}</span><span class="af-st ${ok ? 'ok' : 'bad'}">${ok ? '✓ Ready' : 'Needs a fix'}</span></li>`;
  }

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
    modal.close();
    dashboard('accounts');
    history.replaceState(null, '', location.pathname + '#audit');
    const pageOk = sc !== 'noPage', igOk = !(sc === 'igPers' || sc === 'noPage') && chosen === PAGE, adOk = !(sc === 'noAd' || sc === 'noCard');
    const items = [
      { ok: true, t: 'Sign in with Facebook', d: 'Signed in as Jamie Carter.', when: 'Done today, 9:14 AM' },
      pageOk ? { ok: true, t: 'Connect your Facebook Page', d: chosen.name + '. Resmara posts here.', when: 'Done today, 9:14 AM' }
             : { ok: false, t: 'Create a Facebook business Page', d: 'Resmara posts to a business Page, not your personal profile. Until then you download each post and share it yourself.', fix: "setupGuides('page')" },
      igOk ? { ok: true, t: 'Connect your Instagram', d: IG + ', a business account linked to your Page.', when: 'Done today, 9:14 AM' }
           : { ok: false, t: 'Switch your Instagram to a business account', d: pageOk ? 'Your posts go to Facebook only until it’s switched. It takes about a minute.' : 'Do this after your Page is set up.', fix: pageOk ? 'obIgSwitch()' : "setupGuides('instagram')" },
      adOk ? { ok: true, t: 'Ad account ready', d: 'Jamie Carter Realty, with a card on file.', when: 'Done today, 9:14 AM' }
           : { ok: false, t: sc === 'noAd' ? 'Create a Meta ad account' : 'Add a card to your ad account', d: 'Your posts still go out. Your listing ad is off until this is done.', fix: "setupGuides('ads')" }
    ];
    const left = items.filter(i => !i.ok);
    let n = 0;
    const list = [...left, ...items.filter(i => i.ok)].map(i => `<li class="${i.ok ? 'done' : ''}"><span class="af-num">${i.ok ? '✓' : ++n}</span><span class="af-txt"><b>${i.t}</b><p>${i.d}</p>${i.ok ? `<small>${i.when}</small>` : `<div class="af-act"><button class="campaign-primary" onclick="${i.fix}">Fix it now</button><button class="campaign-primary" style="background:#12354d;color:#fff" onclick="obBook(true)">Book a call</button></div>`}</span></li>`).join('');
    document.querySelector('#content').innerHTML = `<div class="welcome"><h1>Your social connections.</h1></div>
    <div class="panel meta-card"><span class="eyebrow">YOUR SETUP</span><h3>${left.length ? (left.length === 1 ? 'One thing left to set up' : left.length + ' things left to set up') : 'Everything is set up'}</h3>
    <p>${left.length ? 'Each one ticks off on its own as soon as Meta shows it’s done.' : 'Resmara can post to your Page and Instagram and run your listing ads.'}</p>
    <ul class="af-todo">${list}</ul>
    <div class="af-meta"><span>Last checked today at 9:14 AM</span><span class="btn-pair" style="margin:0"><button class="alt" onclick="toast('Checked just now. Nothing has changed.')">Check again</button><button class="alt" onclick="afPick()">Reconnect</button>${sc === 'several' ? '<button class="alt" onclick="afPick()">Change Page</button>' : ''}</span></div></div>
    <p class="fine ob-skip" style="margin-top:14px">Preview: <a href="#" style="color:#12354d;text-decoration:underline" onclick="afPick();return false">try another setup</a></p>`;
  };

  const hash = window.__previewHash || location.hash;
  if (hash === '#audit') setTimeout(() => { history.replaceState(null, '', location.pathname + '#audit'); afPick(); }, 50);
  if (hash === '#signup') setTimeout(() => { history.replaceState(null, '', location.pathname + '#signup'); afSignup('ready'); }, 50);
})();
