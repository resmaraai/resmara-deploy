// Property report: the one document an agent sends to their seller.
// One renderer for the campaign page, the homepage sample and the PDF. No ad spend anywhere:
// this goes to the client.

const fmtN = n => n == null ? '—' : Number(n).toLocaleString('en-US');

// Illustrative numbers for the demo campaigns (clearly labelled as examples on the page).
function demoReportData(c, day) {
  const seed = [...String(c.address || 'x')].reduce((a, ch) => a + ch.charCodeAt(0), 0);
  const f = 0.85 + (seed % 30) / 100;
  const full = day >= 14;
  const base = full ? { reach: 14860, views: 31240, likes: 702, comments: 141, shares: 96, saves: 93, clicks: 238 }
                    : { reach: 8420, views: 16905, likes: 371, comments: 74, shares: 51, saves: 52, clicks: 126 };
  const t = {}; for (const k in base) t[k] = Math.round(base[k] * f);
  const P = typeof SAMPLE_POSTS !== 'undefined' ? SAMPLE_POSTS : [];
  const pick = full ? [[6, 6210, '212 saves'], [9, 4980, '96 comments'], [13, 4450, '71 shares']]
                    : [[6, 3940, '118 saves'], [0, 2870, '44 shares'], [1, 2610, '51 comments']];
  const curve = full ? [38, 52, 61, 49, 74, 66, 88, 63, 80, 72, 91, 84, 100, 86] : [38, 52, 61, 49, 74, 66, 88];
  const total = curve.reduce((a, b) => a + b, 0);
  const brand = typeof brandKitData === 'function' ? brandKitData() : {};
  const start = new Date(2026, 10, 2), end = new Date(2026, 10, 2 + day - 1);
  const d = x => x.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  return {
    illustrative: true, day,
    address: c.address, area: String(c.area || '').split('·')[0].trim(),
    period: `${d(start)} – ${d(end)}, 2026`,
    agent: brand.agent || 'Your agent', brokerage: brand.brokerage || '',
    hero: c.image || (P[0] && P[0].img) || '',
    totals: t,
    top: pick.map(([i, v, x]) => ({ img: P[i] && P[i].img, headline: P[i] && P[i].headline, views: Math.round(v * f), stat: x })),
    daily: curve.map(h => Math.round(t.views * h / total)),
    summary: full
      ? `Across all 14 days, ${fmtN(t.reach)} people saw this home and ${fmtN(t.clicks)} of them clicked through to the full listing. Interest built steadily, peaked on day 13 and was still strong when the campaign ended. The outdoor living posts earned the most saves, a clear sign buyers are picturing themselves there.`
      : `In its first week, ${fmtN(t.reach)} people saw this home and ${fmtN(t.clicks)} clicked through to the full listing. Views have climbed most days, and posts about the outdoor living spaces are getting the most saves.`,
    recs: full
      ? ['Run the campaign again while interest is still high. A fresh round of posts and a new ad keeps the home in front of the people who already engaged.',
         'Lead the next round with the outdoor living spaces. They earned the most saves and shares.',
         'Follow up with the people who commented and saved the posts. They are your warmest buyers.']
      : ['Week two leans into the outdoor living posts, the most-saved content so far.',
         'Weekend mornings got the most views. Resmara will put the strongest posts there.',
         'Share the listing link in your own stories to build on the clicks you already have.']
  };
}

// Real campaign data from the API. Missing sections stay empty; nothing is invented.
function liveReportData(c, day, data) {
  const organic = (data && data.organic) || {}, paid = (data && data.paid) || {}, s = organic.summary || {};
  const meta = organic.source === 'meta';
  const brand = typeof brandKitData === 'function' ? brandKitData() : {};
  return {
    illustrative: false, day, address: (data && data.address) || c.address, area: String(c.area || '').split('·')[0].trim(),
    period: ((data && data.period) || {}).label || `Day 1 to day ${day}`,
    agent: brand.agent || '', brokerage: brand.brokerage || '', hero: c.image || '',
    totals: { reach: meta ? s.reach : null, views: meta ? (s.views ?? s.impressions) : null,
      likes: meta ? s.likes : null, comments: meta ? s.comments : null, shares: meta ? s.shares : null, saves: meta ? s.saves : null,
      clicks: paid.source === 'meta' ? paid.clicks : null, engagements: meta ? s.interactions : null },
    top: (organic.top_posts || []).slice(0, 3).map(p => ({ img: p.image, headline: p.title || p.caption, views: p.views, stat: p.stat || '' })),
    daily: organic.daily || [], summary: data && data.summary || '', recs: (data && data.recommendations) || []
  };
}

function propertyReportHTML(d) {
  const t = d.totals;
  const eng = t.engagements ?? ((t.likes ?? 0) + (t.comments ?? 0) + (t.shares ?? 0) + (t.saves ?? 0) || null);
  const max = Math.max(1, ...d.daily);
  const peak = d.daily.indexOf(Math.max(...d.daily));
  return `<article class="pr-doc">
  <header class="pr-head">
    <div class="pr-head-text">
      <div class="pr-brandline"><img class="pr-logo" src="resmara-logo-white.png" alt="Resmara"><span class="pr-kicker">${d.day >= 14 ? 'FINAL REPORT · 14-DAY TOTALS' : `PROPERTY REPORT · DAY ${d.day} OF 14`}</span></div>
      <h2>${esc(d.address)}</h2>
      <p class="pr-area">${esc(d.area)}${d.area ? ' · ' : ''}${esc(d.period)}</p>
      <p class="pr-by">Prepared by ${esc(d.agent)}${d.brokerage ? ', ' + esc(d.brokerage) : ''}</p>
    </div>
    ${d.hero ? `<img class="pr-hero" src="${esc(mediaPath(d.hero))}" alt="">` : ''}
  </header>
  <section class="pr-sec">
    <span class="pr-label">${d.day >= 14 ? 'CAMPAIGN TOTALS · ALL 14 DAYS' : 'AT A GLANCE · DAYS 1–' + d.day}</span>
    <div class="pr-big">
      <div><b>${fmtN(t.reach)}</b><span>People reached</span></div>
      <div><b>${fmtN(t.views)}</b><span>Post views</span></div>
      <div><b>${fmtN(eng)}</b><span>Engagements</span></div>
      <div class="hi"><b>${fmtN(t.clicks)}</b><span>Clicks to the listing</span></div>
    </div>
    <div class="pr-small">
      <div><b>${fmtN(t.likes)}</b><span>Likes</span></div>
      <div><b>${fmtN(t.comments)}</b><span>Comments</span></div>
      <div><b>${fmtN(t.shares)}</b><span>Shares</span></div>
      <div><b>${fmtN(t.saves)}</b><span>Saves</span></div>
    </div>
  </section>
  ${d.summary && d.day < 14 ? `<section class="pr-sec pr-read"><span class="pr-label">WHAT’S HAPPENING</span><p>${esc(d.summary)}</p></section>` : ''}
  ${d.top.length ? `<section class="pr-sec"><span class="pr-label">TOP PERFORMING POSTS</span><div class="pr-top">${d.top.map((p, i) => `<figure>${p.img ? `<img src="${esc(mediaPath(p.img))}" alt="">` : '<div class="pr-noimg"></div>'}<em>#${i + 1}</em><figcaption><b>${esc(p.headline || '')}</b><small>${fmtN(p.views)} views${p.stat ? ' · ' + esc(p.stat) : ''}</small></figcaption></figure>`).join('')}</div></section>` : ''}
  ${d.daily.length ? `<section class="pr-sec"><span class="pr-label">DAILY ACTIVITY · POST VIEWS</span><div class="pr-chart">${d.daily.map((v, i) => `<div class="${i === peak ? 'peak' : ''}"><small>${i === peak ? fmtN(v) : ''}</small><i style="height:${Math.max(4, Math.round(v / max * 100))}%"></i><span>${i + 1}</span></div>`).join('')}</div><p class="pr-chart-note">Day of the campaign. Busiest day: day ${peak + 1}.</p></section>` : ''}
  ${d.recs.length ? `<section class="pr-sec pr-recs"><div class="pr-recs-head"><span class="robot-avatar" aria-hidden="true"></span><div><span class="pr-label">RECOMMENDATIONS BY RESMARA</span><b>${d.day >= 14 ? 'Summary and what to do next' : 'What happens in week two'}</b></div></div>${d.day >= 14 && d.summary ? `<p class="pr-wrap">${esc(d.summary)}</p><span class="pr-label pr-next">WHAT TO DO NEXT</span>` : ''}<ol>${d.recs.map(r => `<li>${esc(r)}</li>`).join('')}</ol></section>` : ''}
  <footer class="pr-foot"><span>Prepared with <b>Resmara</b> · resmara.com</span><span>${d.illustrative ? 'Example report · illustrative numbers' : 'Figures from Meta for this period'}</span></footer>
</article>`;
}

// Campaign page: open the report right there, under the report list.
async function openPropertyReport(index, day, btn) {
  const c = [...state.campaigns, ...examples][index];
  const box = document.querySelector('#pr-view');
  if (!c || !box) return;
  document.querySelectorAll('.pr-pick').forEach(b => b.classList.toggle('on', b === btn));
  if (box.dataset.open === String(day)) { box.dataset.open = ''; box.innerHTML = ''; btn && btn.classList.remove('on'); return; }
  box.dataset.open = String(day);
  let d = null;
  const boostId = typeof campaignBoostId === 'function' ? campaignBoostId(c) : null;
  if (boostId != null && window.RM) {
    box.innerHTML = '<p class="fine">Loading your report…</p>';
    try { d = liveReportData(c, day, await RM.report(boostId, day)); }
    catch (e) { box.innerHTML = `<p class="fine">This report isn’t available right now: ${esc(e.message)}</p>`; return; }
  } else if (examples.includes(c)) {
    d = demoReportData(c, day);
  } else {
    box.innerHTML = '<div class="notice">Your numbers appear here once Meta returns them for this campaign.</div>';
    return;
  }
  box.innerHTML = `<div class="pr-bar"><b>Day ${day} report</b><div><button type="button" class="pr-close" onclick="openPropertyReport(${index},${day},document.querySelector('.pr-pick.on'))">Close</button><button type="button" class="campaign-primary" onclick="downloadReportPDF(this)">Download PDF</button></div></div>${propertyReportHTML(d)}`;
  box.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function loadScript(src) {
  return new Promise((ok, bad) => { if (document.querySelector(`script[src="${src}"]`)) return ok(); const s = document.createElement('script'); s.src = src; s.onload = ok; s.onerror = () => bad(new Error('Could not load ' + src)); document.head.append(s); });
}

// Branded PDF, letter size, built in the browser from the same document the agent sees.
async function downloadReportPDF(btn) {
  const doc = btn.closest('#pr-view').querySelector('.pr-doc');
  const label = btn.textContent; btn.disabled = true; btn.textContent = 'Preparing PDF…';
  try {
    await loadScript('vendor/html2canvas.min.js'); await loadScript('vendor/jspdf.umd.min.js');
    const clone = doc.cloneNode(true); clone.classList.add('pr-print');
    const stage = document.createElement('div'); stage.className = 'pr-stage'; stage.append(clone); document.body.append(stage);
    await Promise.all([...clone.querySelectorAll('img')].map(i => i.complete ? 0 : new Promise(r => { i.onload = i.onerror = r })));
    // Never split a section across pages: break before any section that would cross a page edge.
    const pageH = 816 * 11 / 8.5;
    let offset = 0;
    [...clone.children].forEach(el => {
      const top = el.offsetTop + offset, bottom = top + el.offsetHeight;
      const edge = Math.ceil((top + 1) / pageH) * pageH;
      if (bottom > edge && el.offsetHeight < pageH && el.tagName !== 'HEADER') { const pad = edge - top + 36; el.style.marginTop = pad + 'px'; offset += pad; }
    });
    const canvas = await html2canvas(clone, { scale: 2, useCORS: true, backgroundColor: '#ffffff' });
    stage.remove();
    const { jsPDF } = window.jspdf;
    const pdf = new jsPDF({ unit: 'pt', format: 'letter' });
    const pw = pdf.internal.pageSize.getWidth(), ph = pdf.internal.pageSize.getHeight();
    const pxPerPage = canvas.width * ph / pw;
    for (let y = 0, n = 0; y < canvas.height; y += pxPerPage, n++) {
      const slice = document.createElement('canvas'); slice.width = canvas.width; slice.height = Math.min(pxPerPage, canvas.height - y);
      slice.getContext('2d').drawImage(canvas, 0, y, canvas.width, slice.height, 0, 0, canvas.width, slice.height);
      if (n) pdf.addPage();
      pdf.addImage(slice.toDataURL('image/jpeg', 0.92), 'JPEG', 0, 0, pw, slice.height * pw / canvas.width);
    }
    const name = (doc.querySelector('h2')?.textContent || 'Property').replace(/[^A-Za-z0-9]+/g, '-').replace(/^-|-$/g, '');
    const kt = doc.querySelector('.pr-kicker')?.textContent || ''; const day = /14-DAY/.test(kt) ? '14' : ((kt.match(/DAY (\d+)/) || [])[1] || '');
    pdf.save(`Resmara-Report-${name}-Day-${day}.pdf`);
  } catch (e) { toast('Could not make the PDF: ' + e.message); }
  btn.disabled = false; btn.textContent = label;
}
