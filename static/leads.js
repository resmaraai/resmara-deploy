// Social leads: comments on the campaign's posts and ad that read like buying interest.
// Resmara's AI flags them; the agent ticks them off, removes the ones that aren't leads, or adds one.
// Review copy: demo campaigns carry sample comments. Live campaigns fill this from Meta comments.

function campaignIsLive(c) { return Number(c && c.day) > 0 || Boolean(c && c.live && Number(c.posts_published) > 0); }
function leadsKey(c) { return 'leads-' + (c.reviewId || c.address); }

const DEMO_LEADS = {
  '1248 Oakridge Drive': [
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

function campaignLeads(c) {
  state.leads = state.leads || {};
  const k = leadsKey(c);
  if (!state.leads[k]) state.leads[k] = (examples.includes(c) ? (DEMO_LEADS[c.address] || []) : []).map((l, i) => ({ id: Date.now() + i, done: false, ...l }));
  return state.leads[k];
}
function newLeadCount(c) { return campaignIsLive(c) ? campaignLeads(c).filter(l => !l.done).length : 0; }

function leadsPanel(c, index) {
  const leads = campaignLeads(c), open = leads.filter(l => !l.done).length;
  const initials = n => n.split(' ').map(w => w[0]).slice(0, 2).join('').toUpperCase();
  return `<section class="panel leads-panel" id="leads">
  <div class="leads-head"><div><h2 class="campaign-step-title"><span>1</span> Social leads ${open ? `<span class="lead-count">${open} new</span>` : ''}</h2><p class="fine">People who commented on your posts or ad and sound interested in the home. Resmara emails you the moment one comes in.</p></div><button type="button" class="leads-email" onclick="previewLeadEmail(${index})">See the alert email</button></div>
  ${leads.length ? `<ul class="leads-list">${leads.map((l, i) => `<li class="${l.done ? 'done' : ''}">
    <span class="lead-av">${esc(initials(l.name))}</span>
    <div class="lead-body"><b>${esc(l.name)}</b><span class="lead-where">${esc(l.where)} · ${esc(l.ago)}</span><p>“${esc(l.text)}”</p><small>On: ${esc(l.post)}</small></div>
    <div class="lead-actions"><button type="button" class="lead-tick" title="${l.done ? 'Mark as new' : 'Mark as handled'}" aria-pressed="${l.done}" onclick="toggleLead(${index},${i})">${l.done ? '✓ Handled' : '✓ Mark handled'}</button><button type="button" class="lead-remove" title="Not a lead" aria-label="Remove lead" onclick="removeLead(${index},${i})">✕</button></div>
  </li>`).join('')}</ul>` : '<p class="leads-empty">No leads yet. When someone comments with interest in the home, they show up here.</p>'}
  <button type="button" class="lead-add" onclick="addLead(${index})">＋ Add a lead</button>
</section>`;
}

function toggleLead(index, i) { const c = [...state.campaigns, ...examples][index], l = campaignLeads(c)[i]; l.done = !l.done; persist(); refreshLeads(index); }
function removeLead(index, i) { const c = [...state.campaigns, ...examples][index]; campaignLeads(c).splice(i, 1); persist(); refreshLeads(index); toast('Removed. Resmara won’t flag that comment again.'); }
function refreshLeads(index) { const c = [...state.campaigns, ...examples][index], el = document.querySelector('#leads'); if (el) el.outerHTML = leadsPanel(c, index); }
function addLead(index) {
  show(`<span class="eyebrow">SOCIAL LEADS</span><h2>Add a lead.</h2><form onsubmit="event.preventDefault();saveLead(${index},this)"><label class="field">Name<input name="name" required placeholder="Who is it?"></label><label class="field">Where<select name="where"><option>Instagram</option><option>Facebook</option><option>Facebook ad</option><option>Phone or text</option><option>Email</option><option>Other</option></select></label><label class="field">What they said<textarea name="text" rows="3" required></textarea></label><div class="modal-actions"><button type="button" class="nc-cancel" onclick="modal.close()">Cancel</button><button class="campaign-primary">Add lead</button></div></form>`);
}
function saveLead(index, form) {
  const c = [...state.campaigns, ...examples][index];
  campaignLeads(c).unshift({ id: Date.now(), name: form.name.value.trim(), where: form.where.value, text: form.text.value.trim(), post: 'Added by you', ago: 'Just now', done: false });
  persist(); modal.close(); refreshLeads(index);
}

// What the agent receives the moment a lead comes in.
function previewLeadEmail(index) {
  const c = [...state.campaigns, ...examples][index], l = campaignLeads(c).find(x => !x.done) || campaignLeads(c)[0] || { name: 'Sarah Mitchell', where: 'Instagram', post: 'Just listed', text: 'Is this still available?' };
  const brand = typeof brandKitData === 'function' ? brandKitData() : {};
  show(`<span class="eyebrow">EMAIL PREVIEW</span><div class="lead-mail">
   <div class="lead-mail-meta"><div><b>From</b> Resmara &lt;support@resmara.com&gt;</div><div><b>To</b> ${esc(brand.agent || 'You')}</div><div><b>Subject</b> New lead on ${esc(c.address)}: ${esc(l.name)}</div></div>
   <div class="lead-mail-body">
    <div class="lead-mail-top"><img class="pr-logo" src="resmara-logo-white.png" alt="Resmara"><span>NEW SOCIAL LEAD</span></div>
    <h3>${esc(l.name)} is interested in ${esc(c.address)}.</h3>
    <div class="lead-mail-quote"><p>“${esc(l.text)}”</p><small>${esc(l.where)} · on “${esc(l.post)}”</small></div>
    <p>Reply while they’re still looking. Resmara spotted this comment and thinks it shows real interest in the home.</p>
    <div class="lead-mail-btns"><span class="lm-primary">Reply on ${esc(/Instagram/.test(l.where) ? 'Instagram' : 'Facebook')} →</span><span class="lm-secondary">See all leads in Resmara</span></div>
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
function untilSoldOn(c) { return (state.untilSoldCampaigns || []).includes(c && c.address); }
function untilSoldButton(c) {
  if (!campaignIsLive(c) || campaignPhase(c) === 'completed') return '';
  const i = [...state.campaigns, ...examples].indexOf(c);
  return untilSoldOn(c)
    ? `<button type="button" class="card-pause until-sold-on" onclick="untilSoldInfo(${i},'card')">↻ Until it sells · On</button>`
    : `<button type="button" class="card-pause" onclick="untilSoldInfo(${i},'card')">↻ Until it sells</button>`;
}
function untilSoldPanel(i) {
  const c = [...state.campaigns, ...examples][i], on = untilSoldOn(c);
  return `<div class="until-sold"><div class="until-sold-copy"><b class="until-sold-title">Run it until it sells</b><p class="budget-note">Every 2 weeks, Resmara builds a brand-new campaign for this home: 14 new posts and a new ad, never a repeat. Each round learns from how the last ad did. It stops on its own when the listing goes pending or sells.</p><button type="button" class="until-sold-how" onclick="untilSoldInfo(${i},'scope')">How it works</button></div><div class="until-sold-seller"><span class="eyebrow">TELL YOUR SELLERS</span><p>“${UNTIL_SOLD_LINE}”</p>${on
    ? `<div class="until-sold-state"><strong>✓ Running until it sells · $39 per renewal</strong><button type="button" class="until-sold-off" onclick="setUntilSold(${i},false,'scope')">Turn off</button></div>`
    : `<div class="until-sold-state"><button type="button" class="campaign-primary" onclick="setUntilSold(${i},true,'scope')">Run it until it sells →</button><span class="until-sold-price">$39 per renewal</span></div>`}</div></div>`;
}
function untilSoldInfo(i, from) {
  const c = [...state.campaigns, ...examples][i], on = untilSoldOn(c);
  const r = state.reviews && state.reviews['review-' + (c.reviewId || i)];
  const budget = r && Number(r.scope && r.scope.budget) > 0 ? Number(r.scope.budget) : 50;
  show(`<span class="eyebrow">RUN IT UNTIL IT SELLS</span><h2>Fresh marketing every 2 weeks, until it’s under contract.</h2><ul class="until-sold-list"><li><b>A brand-new campaign every 2 weeks.</b> 14 new posts and a new ad each round. Nothing is repeated.</li><li><b>Every round gets smarter.</b> Resmara looks at which posts and ad reached the most people and got the most clicks, and builds the next round around what worked.</li><li><b>You stay in control.</b> The next round is ready to look over 3 days before it starts. Change anything you like, or leave it and it goes live on its own.</li><li><b>$39 per renewal</b>, charged to your card on file when the new round is built. Your $${budget} ad budget runs again each round and is billed by Meta, as always.</li><li><b>It stops by itself</b> when your listing shows pending or sold. You can turn it off any time.</li></ul><div class="until-sold-quote"><span class="eyebrow">TELL YOUR SELLERS</span><p>“${UNTIL_SOLD_LINE}”</p></div><div class="modal-actions"><button type="button" class="nc-cancel" onclick="modal.close()">${on ? 'Keep it on' : 'Not now'}</button>${on
    ? `<button class="campaign-primary" onclick="setUntilSold(${i},false,'${from}')">Turn off</button>`
    : `<button class="campaign-primary" onclick="setUntilSold(${i},true,'${from}')">Run it until it sells →</button>`}</div>`);
}
function setUntilSold(i, on, from) {
  const c = [...state.campaigns, ...examples][i];
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
