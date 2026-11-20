// Campaign leads: people who asked about the home on its Resmara listing page (the form or the
// call button) and comments on the campaign's posts and ad that read like buying interest.
// The server reads Meta and judges the comments (app/services/leads.py); this file shows what it
// found and writes back the agent's own actions. Until Nov 2026 this panel was a mockup: sample
// comments for the demo campaigns and a localStorage list for real ones, so a lead seen on a
// phone did not exist on a laptop. The demo addresses still carry sample comments, because a
// demo has to look alive; a real campaign asks the server.

function campaignIsLive(c) {
  // A campaign is live when the server says it was launched (launched_at) or it has run at
  // least one day. "It has published posts" used to be part of this test, and because the
  // publisher stores "posted" while one endpoint counted "published", a launched campaign
  // read as un-launched and opened on the pre-launch approval screen forever.
  return Number(c && c.day) > 0 || Boolean(c && c.live && c.launched_at);
}
function leadsKey(c) { return 'leads-' + (c.reviewId || c.address); }
// A campaign the account actually owns has a boost id; the sample addresses do not.
function leadsIsServer(c) { return typeof campaignBoostId === 'function' && campaignBoostId(c) != null; }

const DEMO_LEADS = {
  '1248 Oakridge Drive': [
    { source: 'web', name: 'Emily Carter', where: 'Listing page form', ago: '40m ago', text: 'We’re relocating from Denver in January. Could we tour this Saturday morning?', email: 'emily.carter@example.com', phone: '(512) 555-0193' },
    { source: 'call', name: 'Call from (512) 555-0127', where: 'Listing page call button', ago: '3h ago', text: 'Tapped Call on your listing page.', phone: '(512) 555-0127' },
    { name: 'Sarah Mitchell', where: 'Instagram', post: 'Where summer actually happens', ago: '2h ago', text: 'Is this still available? We’d love to see it this weekend.' },
    { name: 'James Ortega', where: 'Facebook ad', post: 'The day starts at the threshold', ago: '5h ago', text: 'What’s the asking price? And is the pool heated?' },
    { name: 'Priya Shah', where: 'Facebook', post: 'How much room is enough?', ago: 'Yesterday', text: 'Sending this to my husband. Do you have a virtual tour?' }
  ],
  '76 Willow Lane': [
    { name: 'Megan Cole', where: 'Instagram', post: 'Just listed', ago: '1h ago', text: 'Open house this Sunday? 😍' }
  ],
  '309 Cedar House': [
    { name: 'Daniel Reyes', where: 'Facebook ad', post: 'Leave the lights on awhile', ago: '3d ago', text: 'Is the seller open to offers?', done: true },
    { name: 'Lauren Park', where: 'Instagram', post: 'Would you pause here awhile?', ago: '4d ago', text: 'Can we book a showing?', done: true }
  ]
};

// Sample campaigns keep their comments in state; a real campaign's leads live on the server and
// are cached here only for the moment they are on screen.
function campaignLeads(c) {
  state.leads = state.leads || {};
  const k = leadsKey(c);
  if (!state.leads[k]) state.leads[k] = (examples.includes(c) ? (DEMO_LEADS[c.address] || []) : []).map((l, i) => ({ id: Date.now() + i, done: false, ...l }));
  return state.leads[k];
}
function newLeadCount(c) {
  if (!campaignIsLive(c)) return 0;
  // The server's count is the truth a reload, a phone and the console all agree on.
  if (leadsIsServer(c)) return Number(c.new_leads || 0);
  return campaignLeads(c).filter(l => !l.done).length;
}

// ---- the server side ------------------------------------------------------------------------
// Deliberately NOT on `state`: state is written to localStorage, and a cache that was mid-fetch
// during a reload came back as a permanent "Checking the comments…" that nothing could clear.
let leadCacheStore = {};
function leadCache(c) { return leadCacheStore[campaignBoostId(c)] || null; }
function setLeadCache(c, value) {
  const k = campaignBoostId(c);
  if (value === null || value === undefined) delete leadCacheStore[k];
  else leadCacheStore[k] = value;
}
function leadTimeAgo(iso) {
  if (!iso) return '';
  // The server's timestamps carry no offset in SQLite, so "2026-11-18T20:17:40" would be read
  // as local time and a comment from a minute ago could say "5h from now". Treat it as UTC.
  const s = String(iso);
  const hasZone = /([zZ]|[+-]\d\d:?\d\d)$/.test(s);
  const then = new Date(hasZone ? s : s + 'Z');
  if (isNaN(then.getTime())) return '';
  const mins = Math.round((Date.now() - then.getTime()) / 60000);
  if (mins < 1) return 'Just now';
  if (mins < 60) return mins + 'm ago';
  const hrs = Math.round(mins / 60); if (hrs < 24) return hrs + 'h ago';
  const days = Math.round(hrs / 24); return days === 1 ? 'Yesterday' : days + 'd ago';
}
function leadFromServer(row) {
  return { id: row.id, remoteId: row.id, name: row.author_name || 'Someone',
    where: row.channel || (row.platform === 'instagram' ? 'Instagram' : 'Facebook'),
    ago: leadTimeAgo(row.comment_at || row.created_at), text: row.text || '',
    post: row.post_label || '', done: row.status === 'handled', status: row.status || 'new',
    permalink: row.permalink || null,
    source: row.source || 'comment', email: row.email || '', phone: row.phone || '' };
}
function ensureLeads(c, index) {
  const cache = leadCache(c);
  if (cache && (cache.loading || cache.rows || cache.error)) return;
  if (!window.RM || !RM.leads) return;
  setLeadCache(c, { loading: true });
  RM.leads(campaignBoostId(c)).then(function (data) {
    setLeadCache(c, {
      loading: false,
      rows: (data.leads || []).map(leadFromServer),
      scan: data.scan || null
    });
    refreshLeads(index);
  }).catch(function (err) {
    setLeadCache(c, { loading: false, error: (err && err.message) || 'Could not load leads.' });
    refreshLeads(index);
  });
}
function checkLeadsNow(index) {
  const c = [...state.campaigns, ...examples][index];
  if (!leadsIsServer(c) || !window.RM || !RM.scanLeads) return;
  setLeadCache(c, { loading: true });
  refreshLeads(index);
  RM.scanLeads(campaignBoostId(c)).then(function () {
    setLeadCache(c, null);
    ensureLeads(c, index);
    toast('Checked the comments on this campaign.');
  }).catch(function (err) {
    setLeadCache(c, { loading: false, error: (err && err.message) || 'Could not check for comments just now.' });
    refreshLeads(index);
  });
}

function leadsPanel(c, index) {
  const server = leadsIsServer(c);
  if (server) ensureLeads(c, index);
  const cache = server ? leadCache(c) : null;
  const leads = server ? ((cache && cache.rows) || []) : campaignLeads(c);
  const open = server ? Number(c.new_leads || 0) : leads.filter(l => !l.done).length;
  const initials = n => String(n || '?').split(' ').map(w => w[0]).slice(0, 2).join('').toUpperCase();
  let body;
  if (server && cache && cache.loading) {
    body = '<p class="leads-empty">Checking the comments on your posts and ad…</p>';
  } else if (server && cache && cache.error) {
    body = `<p class="leads-empty">Could not check for comments just now: ${esc(cache.error)}</p>`;
  } else if (leads.length) {
    const row = (l, i) => `<li class="${l.done ? 'done' : ''}">
    <span class="lead-av${l.source === 'web' || l.source === 'call' ? ' web' : ''}">${esc(initials(l.name))}</span>
    <div class="lead-body"><b>${esc(l.name)}</b><span class="lead-where">${esc(l.where)} · ${esc(l.ago)}</span><p>${l.source === 'call' ? esc(l.text) : '“' + esc(l.text) + '”'}</p>${(l.email || l.phone) && l.source !== 'call' ? `<small class="lead-contact">${[l.email, l.phone].filter(Boolean).map(esc).join(' · ')}</small>` : ''}${l.post ? `<small>On: ${esc(l.post)}</small>` : ''}</div>
    <div class="lead-actions"><button type="button" class="lead-tick" title="${l.done ? 'Mark as new' : 'Mark as handled'}" aria-pressed="${l.done}" onclick="toggleLead(${index},${i})">${l.done ? '✓ Handled' : '✓ Mark handled'}</button><button type="button" class="lead-remove" title="Not a lead" aria-label="Remove lead" onclick="removeLead(${index},${i})">✕</button></div>
  </li>`;
    const fromPage = leads.map((l, i) => [l, i]).filter(([l]) => l.source === 'web' || l.source === 'call');
    const fromSocial = leads.map((l, i) => [l, i]).filter(([l]) => !(l.source === 'web' || l.source === 'call'));
    body = `<h3 class="leads-group">From your listing page</h3>${fromPage.length ? `<ul class="leads-list">${fromPage.map(([l, i]) => row(l, i)).join('')}</ul>` : '<p class="leads-empty">No form or call leads yet.</p>'}
    <h3 class="leads-group">From your posts and ad</h3>${fromSocial.length ? `<ul class="leads-list">${fromSocial.map(([l, i]) => row(l, i)).join('')}</ul>` : '<p class="leads-empty">No comment leads yet.</p>'}`;
  } else {
    body = '<p class="leads-empty">No leads yet. When someone fills in the form or taps Call on your listing page, or comments with interest in the home, they show up here.</p>';
  }
  const scan = server ? (cache && cache.scan) : null;
  const scanLine = server
    ? `<p class="fine">${scan && scan.checked_at ? 'Last checked ' + esc(leadTimeAgo(scan.checked_at)) : 'Not checked yet.'}${scan && scan.note ? ' · ' + esc(scan.note) : ''}</p>`
    : '';
  return `<section class="panel leads-panel" id="leads">
  <div class="leads-head"><div><h2 class="campaign-step-title"><span>1</span> Campaign leads ${open ? `<span class="lead-count">${open} new</span>` : ''}</h2><p class="fine">People who asked about the home on your listing page, and people who commented on your posts or ad and sound interested. Resmara emails you the moment one comes in.</p>${scanLine}</div>${server ? `<div class="leads-head-btns"><button type="button" class="leads-email" onclick="checkLeadsNow(${index})">Check now</button></div>` : ''}</div>
  ${body}
  <button type="button" class="lead-add" onclick="addLead(${index})">＋ Add a lead</button>
</section>`;
}

function leadActionFailed(err) { toast((err && err.message) || 'Could not save that just now. Try again.'); }

function toggleLead(index, i) {
  const c = [...state.campaigns, ...examples][index];
  if (leadsIsServer(c)) {
    const cache = leadCache(c); const l = cache && cache.rows && cache.rows[i];
    if (!l) return;
    const next = l.done ? 'new' : 'handled';
    RM.setLeadStatus(l.remoteId, next).then(function (saved) {
      l.done = saved.status === 'handled'; l.status = saved.status;
      c.new_leads = Math.max(0, Number(c.new_leads || 0) + (next === 'handled' ? -1 : 1));
      persist(); refreshLeads(index);
    }).catch(leadActionFailed);
    return;
  }
  const l = campaignLeads(c)[i]; l.done = !l.done; persist(); refreshLeads(index);
}
function removeLead(index, i) {
  const c = [...state.campaigns, ...examples][index];
  if (leadsIsServer(c)) {
    const cache = leadCache(c); const l = cache && cache.rows && cache.rows[i];
    if (!l) return;
    RM.removeLead(l.remoteId).then(function () {
      cache.rows.splice(i, 1);
      if (!l.done) c.new_leads = Math.max(0, Number(c.new_leads || 0) - 1);
      persist(); refreshLeads(index);
      toast('Removed. Resmara won’t flag that comment again.');
    }).catch(leadActionFailed);
    return;
  }
  campaignLeads(c).splice(i, 1); persist(); refreshLeads(index); toast('Removed. Resmara won’t flag that comment again.');
}
function refreshLeads(index) { const c = [...state.campaigns, ...examples][index], el = document.querySelector('#leads'); if (el) el.outerHTML = leadsPanel(c, index); setupFolds(); }
function addLead(index) {
  show(`<span class="eyebrow">CAMPAIGN LEADS</span><h2>Add a lead.</h2><form onsubmit="event.preventDefault();saveLead(${index},this)"><label class="field">Name<input name="name" required placeholder="Who is it?"></label><label class="field">Where<select name="where"><option>Instagram</option><option>Facebook</option><option>Facebook ad</option><option>Phone or text</option><option>Email</option><option>Other</option></select></label><label class="field">What they said<textarea name="text" rows="3" required></textarea></label><div class="modal-actions"><button type="button" class="nc-cancel" onclick="modal.close()">Cancel</button><button class="campaign-primary">Add lead</button></div></form>`);
}
function saveLead(index, form) {
  const c = [...state.campaigns, ...examples][index];
  const where = form.where.value, text = form.text.value.trim(), name = form.name.value.trim();
  if (leadsIsServer(c)) {
    RM.addLead(campaignBoostId(c), { name: name, text: text, where: where }).then(function (row) {
      const cache = leadCache(c) || (setLeadCache(c, { loading: false, rows: [] }), leadCache(c));
      cache.rows = cache.rows || [];
      cache.rows.unshift(leadFromServer(row));
      c.new_leads = Number(c.new_leads || 0) + 1;
      persist(); modal.close(); refreshLeads(index);
    }).catch(leadActionFailed);
    return;
  }
  campaignLeads(c).unshift({ id: Date.now(), name: name, where: where, text: text, post: 'Added by you', ago: 'Just now', done: false });
  persist(); modal.close(); refreshLeads(index);
}

// What the agent receives the moment a lead comes in.
function previewLeadEmail(index) {
  const c = [...state.campaigns, ...examples][index];
  // The preview shows a real lead when there is one: sample copy for a sample campaign, the
  // newest open lead for a campaign the server is reading.
  const cache = leadsIsServer(c) ? leadCache(c) : null;
  const pool = cache && cache.rows && cache.rows.length ? cache.rows : campaignLeads(c);
  const l = pool.find(x => !x.done) || pool[0] || { name: 'Sarah Mitchell', where: 'Instagram', post: 'Just listed', text: 'Is this still available?' };
  const brand = typeof brandKitData === 'function' ? brandKitData() : {};
  show(`<span class="eyebrow">EMAIL PREVIEW</span><div class="lead-mail">
   <div class="lead-mail-meta"><div><b>From</b> Resmara &lt;support@resmara.com&gt;</div><div><b>To</b> ${esc(brand.agent || 'You')}</div><div><b>Subject</b> New lead on ${esc(c.address)}: ${esc(l.name)}</div></div>
   <div class="lead-mail-body">
    <div class="lead-mail-top"><img class="pr-logo" src="resmara-logo-white.png" alt="Resmara"><span>NEW SOCIAL LEAD</span></div>
    <h3>${esc(l.name)} is interested in ${esc(c.address)}.</h3>
    <div class="lead-mail-quote"><p>“${esc(l.text)}”</p><small>${esc(l.where)} · on “${esc(l.post)}”</small></div>
    <p>Reply while they’re still looking. Resmara spotted this comment and thinks it shows real interest in the home.</p>
    <div class="lead-mail-btns"><span class="lm-primary">Reply on ${esc(/Instagram/.test(l.where) ? 'Instagram' : 'Facebook')}</span><span class="lm-secondary">See all leads in Resmara</span></div>
    <small class="lead-mail-foot">You get these because you have an active campaign in Resmara.</small>
   </div></div>
   <div class="modal-actions"><button class="campaign-primary" onclick="modal.close()">Close</button></div>`);
}
function openLeads(index) { details(index); setTimeout(() => document.querySelector('#leads')?.scrollIntoView({ behavior: 'smooth', block: 'start' }), 50); }
// A live campaign's calendar: always open, view-only, no approval controls.
function liveCalendar(html) {
  return html.replace('<details class="panel review-calendar" ', '<details class="panel review-calendar" open ')
    .replace('This is your campaign calendar. Open any post or ad to check its information and creative before you approve. You only need to open the items you want to spot-check or change.', 'Your campaign is live. Open any post or ad to see it.')
    .replace(/campaignReport\(\[\.\.\.state\.campaigns,\.\.\.examples\]\[ReviewStudio\.active\],(\d+)\)/g, 'openReportFromCalendar($1)');
}
function openReportFromCalendar(day) {
  const btn = [...document.querySelectorAll('.pr-pick')].find(b => b.textContent.includes('Day ' + day + ' report'));
  if (btn && btn.tagName === 'BUTTON') { if (!btn.classList.contains('on')) btn.click(); else document.querySelector('#pr-view')?.scrollIntoView({ behavior: 'smooth' }); }
}

// ---- Pause / resume a running campaign ------------------------------------------------------
// Pausing stops the scheduled posts and pauses the Meta ad. Nothing is deleted.
function campaignPaused(c) { return (state.pausedCampaigns || []).includes(c && c.address); }
function pauseButton(c) {
  if (!campaignIsLive(c) || campaignPhase(c) === 'completed') return '';
  const i = [...state.campaigns, ...examples].indexOf(c);
  return campaignPaused(c)
    ? `<button type="button" class="card-pause resume" onclick="resumeCampaign(${i})">▶ Resume</button>`
    : `<button type="button" class="card-pause" onclick="pauseCampaign(${i})">❚❚ Pause</button>`;
}
function pauseCampaign(i) {
  const c = [...state.campaigns, ...examples][i];
  show(`<span class="eyebrow">PAUSE CAMPAIGN</span><h2>Pause ${esc(c.address)}?</h2><p>Your scheduled posts stop and your listing ad pauses, so Meta stops spending your ad budget. Nothing is deleted.</p><p>Resume any time and it picks up where it left off.</p><div class="modal-actions"><button type="button" class="nc-cancel" onclick="modal.close()">Keep running</button><button class="campaign-primary" onclick="setCampaignPaused(${i},true)">Pause campaign</button></div>`);
}
function resumeCampaign(i) { setCampaignPaused(i, false); }

// ---- Run it until it sells (autopilot) -------------------------------------------------------
// When on, Resmara builds a brand-new 14-day round (new posts + a new ad, never a repeat) every
// 2 weeks, tuned from how the last round's ad did, until the listing goes pending or sells.
// Set in Launch details while setting up, or from the campaign card once it's running.
const UNTIL_SOLD_LINE = 'We’ll market your home with fresh content and ads every 2 weeks until it’s under contract.';
// The server is the record. A campaign that exists as a row carries until_sold; sample/demo cards
// have no row, so they keep the old per-browser answer. Reading the row first is what stops the
// card saying "On" for a campaign the server has never heard of - the mismatch that made the
// interface a promise with nothing behind it.
function untilSoldServer(c) {
  if (typeof campaignBoostId !== 'function' || campaignBoostId(c) == null) return null;
  if (c.until_sold === undefined || c.until_sold === null) return null;
  return !!c.until_sold;
}
function untilSoldOn(c) {
  const server = untilSoldServer(c);
  if (server !== null) return server;
  return (state.untilSoldCampaigns || []).includes(c && c.address);
}
function untilSoldButton(c) {
  if (!campaignIsLive(c) || campaignPhase(c) === 'completed') return '';
  const i = [...state.campaigns, ...examples].indexOf(c);
  return untilSoldOn(c)
    ? `<button type="button" class="card-pause until-sold-on" onclick="untilSoldInfo(${i},'card')" title="A fresh campaign every 2 weeks until it’s under contract">✓ Running until sold</button>`
    : `<button type="button" class="card-pause" onclick="untilSoldInfo(${i},'card')" title="A fresh campaign every 2 weeks until it’s under contract">Run until sold</button>`;
}
function untilSoldPanel(i) {
  const c = [...state.campaigns, ...examples][i], on = untilSoldOn(c);
  return `<div class="until-sold"><b class="until-sold-title">Run it until it sells</b><p class="until-sold-sub">A fresh campaign every 2 weeks until it’s under contract. $39 per renewal.</p><div class="until-sold-line"><div class="eyebrow">TELL YOUR SELLERS</div><p>“${UNTIL_SOLD_LINE}”</p></div><div class="until-sold-actions">${on
    ? `<strong class="until-sold-running">✓ Running until it sells</strong><button type="button" class="until-sold-how" onclick="setUntilSold(${i},false,'scope')">Turn off</button>`
    : `<button type="button" class="campaign-primary" onclick="setUntilSold(${i},true,'scope')">Run it until it sells</button>`}<button type="button" class="until-sold-how" onclick="untilSoldInfo(${i},'scope')">How it works</button></div></div>`;
}
function untilSoldInfo(i, from) {
  const c = [...state.campaigns, ...examples][i], on = untilSoldOn(c);
  const r = state.reviews && state.reviews[typeof reviewKey === 'function' ? reviewKey(c, i) : 'review-' + (c.reviewId || i)];
  const budget = r && Number(r.scope && r.scope.budget) > 0 ? Number(r.scope.budget) : 50;
  show(`<span class="eyebrow">RUN IT UNTIL IT SELLS</span><h2>Fresh marketing every 2 weeks, until it’s under contract.</h2><ul class="until-sold-list"><li><b>A brand-new campaign every 2 weeks.</b> 14 new posts and a new ad each round. Nothing is repeated.</li><li><b>Every round gets smarter.</b> Resmara looks at which posts and ad reached the most people and got the most clicks, and builds the next round around what worked.</li><li><b>You stay in control.</b> The next round is ready to look over 3 days before it starts. Change anything you like, or leave it and it goes live on its own.</li><li><b>$39 per renewal</b>, charged to your card on file when the new round is built. Your $${budget} ad budget runs again each round and is billed by Meta, as always.</li><li><b>It stops by itself</b> when your listing shows pending or sold. You can turn it off any time.</li></ul><div class="until-sold-quote"><span class="eyebrow">TELL YOUR SELLERS</span><p>“${UNTIL_SOLD_LINE}”</p></div>${from === 'scope'
    ? `<div class="modal-actions"><button type="button" class="nc-cancel" onclick="modal.close()">Got it</button></div>`
    : `<div class="modal-actions"><button type="button" class="nc-cancel" onclick="modal.close()">${on ? 'Keep it on' : 'Not now'}</button>${on
      ? `<button class="campaign-primary" onclick="setUntilSold(${i},false,'${from}')">Turn off</button>`
      : `<button class="campaign-primary" onclick="setUntilSold(${i},true,'${from}')">Run it until it sells</button>`}</div>`}</div>`);
}
function setUntilSold(i, on, from) {
  const c = [...state.campaigns, ...examples][i];
  const boostId = (typeof campaignBoostId === 'function') ? campaignBoostId(c) : null;
  // A real campaign writes to the record, and only re-renders when the server has accepted it: a
  // refusal (409 for a pending or sold listing, 401 for an ended session) leaves the card showing
  // the truth instead of flipping a switch that did nothing.
  if (boostId != null && window.RM && RM.setUntilSold) {
    RM.setUntilSold(boostId, on).then(function (saved) {
      c.until_sold = !!(saved && saved.until_sold !== undefined ? saved.until_sold : on);
      c.until_sold_at = (saved && saved.until_sold_at) || null;
      if (Array.isArray(state.untilSoldCampaigns)) {          // clear any stale browser copy
        state.untilSoldCampaigns = state.untilSoldCampaigns.filter(function (a) { return a !== c.address; });
        persist();
      }
      if (modal.open) modal.close();
      if (from === 'scope') details(i); else dashboard('campaigns');
      toast(on ? 'On. Resmara will run a fresh campaign every 2 weeks until this home sells.'
               : 'Turned off. This campaign ends after its 14 days.');
    }).catch(function (err) {
      toast((err && err.message) || 'Could not save that just now. Try again.');
    });
    return;
  }
  const list = (state.untilSoldCampaigns || []).filter(a => a !== c.address);
  if (on) list.push(c.address);
  state.untilSoldCampaigns = list; persist();
  if (modal.open) modal.close();
  if (from === 'scope') details(i); else dashboard('campaigns');
  toast(on ? 'On. Resmara will run a fresh campaign every 2 weeks until this home sells.' : 'Turned off. This campaign ends after its 14 days.');
}
function setCampaignPaused(i, on) {
  const c = [...state.campaigns, ...examples][i];
  const list = (state.pausedCampaigns || []).filter(a => a !== c.address);
  if (on) list.push(c.address);
  state.pausedCampaigns = list; persist();
  if (modal.open) modal.close();
  dashboard('campaigns');
  toast(on ? 'Campaign paused. Posts and your ad are on hold.' : 'Campaign resumed. Posts and your ad are running again.');
}

// ---- Open and close the sections of a live campaign ---------------------------------------
// Each section (leads, calendar, listing page, reports) folds up to its heading, so an agent can
// work through one at a time. A chevron on the right of the heading shows which way it goes, and
// the choice is remembered on this device.
const FOLDS = [['#leads', 'leads', '.leads-head h2'], ['.live-cal .review-calendar', 'calendar', 'summary'],
  ['#listing-page', 'page', 'h2.campaign-step-title'], ['.live-reports', 'reports', 'h2.campaign-step-title']];
function setupFolds() {
  state.folds = state.folds || {};
  FOLDS.forEach(([sel, key, h]) => {
    const sec = document.querySelector(sel), head = sec && sec.querySelector(h);
    if (!head) return;
    // state.folds[key] true = opened. Every section starts closed each time a campaign is opened.
    const closed = !state.folds[key];
    sec.classList.add('fold'); sec.classList.toggle('folded', closed);
    head.setAttribute('aria-expanded', String(!closed));
    if (head.dataset.fold) return;
    head.dataset.fold = key; head.classList.add('fold-head'); head.setAttribute('role', 'button'); head.tabIndex = 0;
    head.insertAdjacentHTML('beforeend', '<span class="fold-chev" aria-hidden="true"></span>');
    const flip = e => { if (e.target.closest('button,a')) return; e.preventDefault(); state.folds[key] = !state.folds[key]; persist(); setupFolds(); };
    head.addEventListener('click', flip);
    head.addEventListener('keydown', e => { if (e.key === 'Enter' || e.key === ' ') flip(e); });
  });
}
