// Your listing page: the simple website Resmara builds for every listing, in the agent's brand.
// Every post and the ad send people here, so the agent never has to supply a link. The form and
// the Call button report back to Resmara, which lists them under Campaign leads and emails the
// agent. This file draws the page (from the brand kit and the campaign) and section 3 of a live
// campaign: the page's numbers and a preview of it.

const LISTING_DEMO = {
  '1248 Oakridge Drive': {
    price: '$845,000', city: 'Austin, TX 78738', beds: 4, baths: 3.5, sqft: '3,420', lot: '1.2 acres',
    photos: ['sample/card-1.jpg', 'sample/card-2.jpg', 'sample/card-3.jpg', 'sample/card-4.jpg'],
    about: 'A calm, light-filled Hill Country home on a wooded acre. Limestone and glass open to a long pool, a covered outdoor room with a fireplace, and views that run all the way to the lake.',
    visits: 412
  },
  '76 Willow Lane': {
    price: '$625,000', city: 'Austin, TX 78746', beds: 3, baths: 2.5, sqft: '2,180',
    photos: ['sample/card-2.jpg', 'sample/card-3.jpg', 'sample/card-4.jpg', 'sample/card-1.jpg'],
    about: 'An easy, open single-story home with a pool, a shaded patio and room to spread out.',
    visits: 96
  }
};

function listingSlug(address) {
  return String(address || 'listing').toLowerCase().split(',')[0].replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
}
function listingPageAddress(c) { return 'homes.resmara.com/' + listingSlug(c.address); }

// Everything the page needs, from the brand kit and the campaign. Nothing is invented for a real
// campaign: a fact the campaign does not have is left off the page.
function listingSiteData(c) {
  const k = typeof brandKitData === 'function' ? brandKitData() : {};
  const demo = LISTING_DEMO[c.address] || null;
  const colour = name => ((k.palette || []).find(p => p[0] === name) || [])[1];
  const area = String(c.area || '');
  const price = (demo && demo.price) || (area.match(/\$[\d,]+/) || [''])[0];
  const photos = (demo && demo.photos) || [c.image].concat(c.photos || []).filter(Boolean);
  return {
    address: c.address, city: (demo && demo.city) || area.replace(/\s*·\s*\$[\d,]+/, ''), price,
    beds: demo && demo.beds, baths: demo && demo.baths, sqft: demo && demo.sqft, lot: demo && demo.lot,
    about: (demo && demo.about) || c.description || '',
    photos: photos.length ? photos : ['resmara-house-complete-v1.png'],
    agent: k.agent || state.name || 'Your name', brokerage: k.brokerage || state.company || '',
    license: k.license || '', phone: (state.brand && state.brand.phone) || state.phone || (k.demo || demo ? '(512) 555-0148' : ''),
    logo: k.logo || '', headshot: k.headshot || '',
    legal: (k.legal || []).filter(l => !/equal housing/i.test(l)),
    primary: colour('Primary') || '#13324b', accent: colour('Accent') || '#e8552b',
    tint: colour('Tint') || '#eef3f7', page: colour('Page') || '#ffffff', text: colour('Text') || '#1c2733',
    fonts: k.fonts && k.fonts.length ? k.fonts : ['Playfair Display', 'Jost']
  };
}

let listingFontsLoaded = '';
function loadListingFonts(fonts) {
  const key = fonts.join('|');
  if (listingFontsLoaded === key) return;
  listingFontsLoaded = key;
  const link = document.createElement('link');
  link.rel = 'stylesheet';
  link.href = 'https://fonts.googleapis.com/css2?' + fonts.map(f => 'family=' + encodeURIComponent(f) + ':wght@400;500;700').join('&') + '&display=swap';
  document.head.appendChild(link);
}

// The page itself. `index` lets the form add a lead to the campaign it belongs to.
function listingSiteHTML(c, index) {
  const d = listingSiteData(c);
  loadListingFonts(d.fonts);
  const facts = [d.beds && d.beds + ' beds', d.baths && d.baths + ' baths', d.sqft && d.sqft + ' sq ft', d.lot].filter(Boolean);
  const first = d.agent.split(' ')[0];
  const tel = d.phone.replace(/[^\d+]/g, '');
  return `<div class="lsite" style="--ls-primary:${esc(d.primary)};--ls-accent:${esc(d.accent)};--ls-tint:${esc(d.tint)};--ls-page:${esc(d.page)};--ls-text:${esc(d.text)};--ls-head:'${esc(d.fonts[0])}',Georgia,serif;--ls-body:'${esc(d.fonts[1] || d.fonts[0])}',system-ui,sans-serif">
  <header class="ls-top">${d.logo ? `<img class="ls-logo" src="${esc(d.logo)}" alt="${esc(d.brokerage)}">` : `<b class="ls-brand">${esc(d.brokerage || d.agent)}</b>`}${d.phone ? `<a class="ls-btn" href="tel:${esc(tel)}" onclick="listingCallTap(event,${index})">Call ${esc(first)}</a>` : ''}</header>
  <section class="ls-hero" style="background-image:url('${esc(d.photos[0])}')"><div class="ls-hero-text">${d.price ? `<span class="ls-price">${esc(d.price)}</span>` : ''}<h1>${esc(d.address)}</h1><p>${esc(d.city)}</p></div></section>
  ${facts.length ? `<div class="ls-facts">${facts.map(f => `<span>${esc(f)}</span>`).join('')}</div>` : ''}
  <div class="ls-body">
    <div class="ls-main">
      ${d.about ? `<h2>About this home</h2><p>${esc(d.about)}</p>` : ''}
      <div class="ls-gallery">${d.photos.slice(0, 8).map(p => `<img src="${esc(p)}" alt="" loading="lazy">`).join('')}</div>
    </div>
    <aside class="ls-side">
      <div class="ls-agent">${d.headshot ? `<img src="${esc(d.headshot)}" alt="">` : `<span class="ls-initials">${esc(d.agent.split(' ').map(w => w[0]).slice(0, 2).join(''))}</span>`}<div><b>${esc(d.agent)}</b><small>${esc(d.brokerage)}</small>${d.phone ? `<small>${esc(d.phone)}</small>` : ''}</div></div>
      <form class="ls-form" onsubmit="event.preventDefault();listingFormSent(this,${index})">
        <h3>Ask about this home</h3>
        <input name="name" required placeholder="Your name" aria-label="Your name">
        <input name="email" type="email" required placeholder="Email" aria-label="Email">
        <input name="phone" type="tel" placeholder="Phone (optional)" aria-label="Phone">
        <textarea name="message" rows="3" placeholder="I’d like to see this home." aria-label="Message"></textarea>
        <button class="ls-btn">Send to ${esc(first)}</button>
        <p class="ls-fine">Your details go only to ${esc(d.agent)}.</p>
      </form>
    </aside>
  </div>
  <footer class="ls-foot">${d.legal.map(l => `<span>${esc(l)}</span>`).join('')}<span>Equal Housing Opportunity</span></footer>
</div>`;
}

function listingPageStats(c) {
  const leads = (typeof leadsIsServer === 'function' && leadsIsServer(c))
    ? (((typeof leadCache === 'function' && leadCache(c)) || {}).rows || [])
    : (typeof campaignLeads === 'function' ? campaignLeads(c) : []);
  const demo = LISTING_DEMO[c.address];
  return {
    visits: Number(c.page_visits != null ? c.page_visits : (demo ? demo.visits : 0)),
    forms: leads.filter(l => l.source === 'web').length,
    calls: leads.filter(l => l.source === 'call').length
  };
}

// Section 3 of a live campaign.
function listingPagePanel(c, index) {
  const s = listingPageStats(c);
  return `<section class="panel listing-page-panel" id="listing-page">
  <h2 class="campaign-step-title"><span>3</span> Your listing page</h2>
  <p class="fine">Resmara built this page for the home in your brand. Every post and your ad send people here, and anyone who fills in the form or taps Call comes straight to you.</p>
  <div class="lp-stats"><div><b>${s.visits.toLocaleString()}</b><small>Visits</small></div><div><b>${s.forms}</b><small>Form leads</small></div><div><b>${s.calls}</b><small>Calls</small></div></div>
  <div class="lp-frame"><div class="lp-bar">${esc(listingPageAddress(c))}</div><div class="lp-view">${listingSiteHTML(c, index)}</div></div>
  <button type="button" class="campaign-primary" onclick="openListingPage(${index})">View full page</button>
</section>`;
}

function openListingPage(index) {
  const c = [...state.campaigns, ...examples][index];
  closeListingPage();
  const wrap = document.createElement('div');
  wrap.id = 'listing-page-full';
  wrap.innerHTML = `<div class="lpf-bar"><span>${esc(listingPageAddress(c))}</span><button type="button" class="campaign-primary" onclick="closeListingPage()">Close</button></div><div class="lpf-page">${listingSiteHTML(c, index)}</div>`;
  document.body.appendChild(wrap);
  document.body.classList.add('lpf-open');
}
function closeListingPage() {
  document.getElementById('listing-page-full')?.remove();
  document.body.classList.remove('lpf-open');
}

function refreshListingPanel(index) {
  const c = [...state.campaigns, ...examples][index], el = document.querySelector('#listing-page');
  if (el) el.outerHTML = listingPagePanel(c, index);
}

// In the review copy the form and the Call button add a lead right here, so the whole loop can be
// seen: the page, the lead under Campaign leads and the count above. On the live site the page
// posts to Resmara, which stores the lead and emails the agent.
function listingFormSent(form, index) {
  const c = [...state.campaigns, ...examples][index];
  const name = form.name.value.trim(), email = form.email.value.trim(), phone = form.phone.value.trim();
  const text = form.message.value.trim() || 'I’d like to see this home.';
  if (typeof campaignLeads === 'function' && !(typeof leadsIsServer === 'function' && leadsIsServer(c))) {
    campaignLeads(c).unshift({ id: Date.now(), source: 'web', name, where: 'Listing page form', ago: 'Just now', text, email, phone, done: false });
    persist();
  }
  form.innerHTML = `<h3>Thanks, ${esc(name.split(' ')[0])}.</h3><p class="ls-fine">Your message is on its way. Expect a reply soon.</p>`;
  if (typeof refreshLeads === 'function') refreshLeads(index);
  refreshListingStats(index);
  toast('New lead from your listing page. In the live version, you’d get an email now.');
}
function listingCallTap(event, index) {
  event.preventDefault();
  const c = [...state.campaigns, ...examples][index];
  if (typeof campaignLeads === 'function' && !(typeof leadsIsServer === 'function' && leadsIsServer(c))) {
    campaignLeads(c).unshift({ id: Date.now(), source: 'call', name: 'Call from your listing page', where: 'Listing page call button', ago: 'Just now', text: 'Tapped Call on your listing page.', done: false });
    persist();
  }
  if (typeof refreshLeads === 'function') refreshLeads(index);
  refreshListingStats(index);
  toast('Call tap counted. On a phone this opens the dialer.');
}
// Only the numbers change; redrawing the whole section would wipe a form mid-thank-you.
function refreshListingStats(index) {
  const c = [...state.campaigns, ...examples][index], s = listingPageStats(c);
  document.querySelectorAll('.lp-stats').forEach(el => {
    el.innerHTML = `<div><b>${s.visits.toLocaleString()}</b><small>Visits</small></div><div><b>${s.forms}</b><small>Form leads</small></div><div><b>${s.calls}</b><small>Calls</small></div>`;
  });
}
