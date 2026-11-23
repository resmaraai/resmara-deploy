const GOOGLE_FONTS=["Playfair Display", "Jost", "Inter", "Roboto", "Open Sans", "Lato", "Montserrat", "Poppins", "Raleway", "Nunito", "Source Sans 3", "Work Sans", "DM Sans", "DM Serif Display", "Libre Baskerville", "Lora", "Merriweather", "Cormorant Garamond", "EB Garamond", "Crimson Text", "Cinzel", "Bodoni Moda", "Libre Caslon Text", "Spectral", "Prata", "Marcellus", "Italiana", "Josefin Sans", "Josefin Slab", "Archivo", "Archivo Black", "Manrope", "Outfit", "Plus Jakarta Sans", "Sora", "Urbanist", "Figtree", "Mulish", "Karla", "Rubik", "Barlow", "Barlow Condensed", "Oswald", "Bebas Neue", "Anton", "League Spartan", "Kumbh Sans", "Lexend", "Quicksand", "Cabin", "PT Sans", "PT Serif", "Noto Sans", "Noto Serif", "IBM Plex Sans", "IBM Plex Serif", "Fraunces", "Newsreader", "Syne", "Space Grotesk", "Red Hat Display", "Albert Sans", "Epilogue", "Hanken Grotesk", "Instrument Sans", "Instrument Serif", "Gilda Display", "Tenor Sans", "Forum", "Bellefair", "Cormorant", "Old Standard TT", "Abril Fatface", "Yeseva One", "Alegreya", "Alegreya Sans", "Vollkorn", "Cardo", "Domine", "Arvo", "Roboto Slab", "Zilla Slab", "Bitter", "Rokkitt", "Great Vibes", "Allura", "Parisienne", "Dancing Script", "Sacramento", "Pinyon Script", "Satisfy", "Kaushan Script", "Caveat", "Amatic SC", "Teko", "Exo 2", "Titillium Web", "Ubuntu", "Hind", "Assistant", "Heebo", "Varela Round", "Nanum Myeongjo", "Gloock", "Bricolage Grotesque", "Onest", "Geologica", "Golos Text", "Literata", "Petrona", "Young Serif"];
function home(){if(typeof brandLeaveGuard==='function'&&brandLeaveGuard(()=>home()))return;
 if(window.stopResmaraGuide)stopResmaraGuide();
 location.hash='';document.title='Resmara — Your listing marketing. Done for you.';
 app.innerHTML=`<div class="marketing-home rmh">
 ${siteNav("home")}
 <main>

<div class="rh-wrap">
<section class="rh-hero">
<div>
<div class="rh-eyebrow">Done-for-you listing marketing for real estate agents</div>
<h1>Your listing marketing.<br><span>Done for you.</span></h1>
<p class="rh-lead">Connect your Facebook once. Then for every listing, Resmara builds a website for the home, posts for 14 days, runs your ads, catches every lead and reports on all of it.</p>
<div class="rh-hero-video-m"><div class="rh-video"><video src="video/resmara-explainer.mp4" poster="video/resmara-explainer.jpg" playsinline preload="metadata" aria-label="How Resmara markets your listing: website, posts, ads, leads and reports" onended="this.removeAttribute('controls');this.load();this.nextElementSibling.hidden=false"></video><button type="button" class="hpv-play" aria-label="Play the video" onclick="const v=this.previousElementSibling;this.hidden=true;v.controls=true;v.play()"><span></span></button></div></div>
<div class="rh-price-chip"><b>$49</b><span>per listing · no subscription</span></div>
<div class="rh-actions"><a class="rh-btn rh-btn-o" href="#" onclick="newCampaign();return false">Get started</a><a class="rh-plain" href="#what" onclick="homeGo('what');return false">See what’s included</a></div>
</div>
<div class="rh-hero-art"><div class="rh-video"><video src="video/resmara-explainer.mp4" poster="video/resmara-explainer.jpg" playsinline preload="metadata" aria-label="How Resmara markets your listing: website, posts, ads, leads and reports" onended="this.removeAttribute('controls');this.load();this.nextElementSibling.hidden=false"></video><button type="button" class="hpv-play" aria-label="Play the video" onclick="const v=this.previousElementSibling;this.hidden=true;v.controls=true;v.play()"><span></span></button></div></div>
</section>
</div>

<section class="rh-band-dark">
<div class="rh-wrap rh-problem">
<div>
<span class="rh-kicker">The problem</span>
<h2>You have clients.<br><span>Not hours to market a listing.</span></h2>
<p>Doing a listing justice means a website, two weeks of posts, ads, answering every comment and a report for your seller. Most agents don’t have those hours, so the listing gets one “Just listed” post and the momentum fades.</p>
</div>
<div class="rh-robot">${homeWorld()}</div>
</div>
</section>

<div class="rh-wrap">
<section class="rh-sec" id="what">
<div class="rh-sec-head">
<div><span class="rh-k2">What you get</span><h2>One link.<br><span>Everything your listing needs.</span></h2></div>
<p>You paste your listing link. Resmara builds the whole campaign in your brand, runs it for 14 days and shows you exactly how it worked.</p>
</div>
<div class="rh-grid6">
<div class="rh-card rh-hi"><div class="rh-ic"><svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="3" y="4" width="18" height="16" rx="2"></rect><path d="M3 9h18"></path></svg></div><b>A website for the home</b><p>A beautiful listing page that every post and ad sends people to, with its own lead form.</p></div>
<div class="rh-card"><div class="rh-ic"><svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="3" y="5" width="18" height="16" rx="2"></rect><path d="M8 3v4M16 3v4M3 10h18"></path></svg></div><b>14 days of posts</b><p>Designed in your brand and posted to Facebook and Instagram when your audience is online.</p></div>
<div class="rh-card"><div class="rh-ic"><svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M3 11l15-6v14L3 13z"></path><path d="M7 13v5"></path></svg></div><b>Digital ads</b><p>An ad your local market will actually see. Every dollar of ad budget goes to Meta.</p></div>
<div class="rh-card rh-hi"><div class="rh-ic"><svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M4 4h16v12H8l-4 4z"></path></svg></div><b>Every lead, caught</b><p>Comments, ad replies and website inquiries are tracked, flagged and emailed to you right away.</p></div>
<div class="rh-card"><div class="rh-ic"><svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 20V10M12 20V4M19 20v-7"></path></svg></div><b>Reports for your seller</b><p>Clear day 7 and day 14 reports on reach, clicks and leads, ready to hand to your homeowner.</p></div>
<div class="rh-card"><div class="rh-ic"><svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 3l2.5 5.5L20 9l-4 4 1 6-5-3-5 3 1-6-4-4 5.5-.5z"></path></svg></div><b>Smarter every listing</b><p>It learns from your edits and your results, so each campaign beats the last.</p></div>
</div>
</section>

<section class="rh-sec" id="see">
<div class="rh-sec-head">
<div><span class="rh-k2">See it</span><h2>Here’s what<br><span>you’d get.</span></h2></div>
<p>A real sample campaign for 1248 Oakridge Drive. Pick a piece to look at.</p>
</div>
${homeTabs()}
<div class="rh-show"><div class="rh-panel" data-tab="site"><div class="rh-frame lp-view" id="home-site-view"></div><span class="rh-frame-hint">↓ Scroll to see the whole website</span></div><div class="rh-panel" data-tab="posts" hidden><div class="rh-frame">${homePostsPanel()}</div><span class="rh-frame-hint">↓ Scroll to see all 14 days</span></div><div class="rh-panel" data-tab="ad" hidden><div class="rh-frame rh-narrow" id="home-ad-view"></div><span class="rh-frame-hint">↓ Scroll to see the whole ad</span></div><div class="rh-panel" data-tab="leads" hidden><div class="rh-leads">
<div class="rh-leads-h"><b>Campaign leads · 1248 Oakridge Drive</b><span class="rh-badge">3 new</span></div>
<div class="rh-lead-row"><span class="rh-av">SM</span><div><b>Sarah Mitchell</b><span class="rh-src">Instagram comment</span><p>“Is this still available? We’d love to see it this weekend.”</p></div></div>
<div class="rh-lead-row"><span class="rh-av">JO</span><div><b>James Ortiz</b><span class="rh-src">Listing website</span><p>Asked for a private showing on Saturday morning.</p></div></div>
<div class="rh-lead-row"><span class="rh-av">PS</span><div><b>Priya Shah</b><span class="rh-src">Facebook ad</span><p>“What are the HOA fees on this one?”</p></div></div>
<div class="rh-mail"><svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#8ae8ff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="3" y="5" width="18" height="14" rx="2"></rect><path d="M3 7l9 6 9-6"></path></svg><span>Each one is emailed to you the moment it comes in.</span></div>
<p class="rh-sample">Sample leads</p>
</div></div><div class="rh-panel" data-tab="report" hidden><div class="rh-frame" id="home-report-preview"></div><span class="rh-frame-hint">↓ Scroll to see the whole report</span></div><div class="rh-show-text"><h3 id="home-tab-title"></h3><p id="home-tab-text"></p></div></div>
</section>

<section class="rh-sec" id="how">
<div class="rh-sec-head">
<div><span class="rh-k2">How it works</span><h2>Two steps for you.<br><span>We do the rest.</span></h2></div>
<p>No design work, no ad manager, no spreadsheets.</p>
</div>
<div class="rh-steps">
<div class="rh-step"><div class="rh-num">1</div><b>Connect your Facebook</b><p>Once. If your Page, Instagram or ad account isn’t ready, we walk you through it or set it up with you.</p></div>
<div class="rh-step"><div class="rh-num">2</div><b>Paste your listing link</b><p>Resmara checks the home’s details and photos, then builds the website, posts and ad in your brand.</p></div>
<div class="rh-step"><div class="rh-num">3</div><b>Approve, and we run it</b><p>14 days of posts and ads, every lead tracked, and reports on day 7 and day 14.</p></div>
</div>
</section>
</div>

<section class="rh-band-dark" id="pricing">
<div class="rh-wrap rh-price">
<div>
<span class="rh-kicker">Pricing</span>
<div class="rh-big">$49<small>per listing</small></div>
<h2 class="rh-price-h">No subscription.<br><span>No contract.</span></h2>
<p>Pay when you build a campaign. Want two more weeks on the same home? A fresh round of posts and a new ad is $39.</p>
<p class="rh-fine">Your ad budget is separate. You choose it, and every dollar goes straight to Meta.</p>
</div>
<div class="rh-list">
<b>Every listing launch includes</b>
<div class="rh-li"><span class="rh-tick"><svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 12l5 5 9-10"></path></svg></span><span>A website built for the home</span></div><div class="rh-li"><span class="rh-tick"><svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 12l5 5 9-10"></path></svg></span><span>14 designed posts with captions</span></div><div class="rh-li"><span class="rh-tick"><svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 12l5 5 9-10"></path></svg></span><span>A digital ad, set up and run for you</span></div><div class="rh-li"><span class="rh-tick"><svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 12l5 5 9-10"></path></svg></span><span>Posting at the best times for your area</span></div><div class="rh-li"><span class="rh-tick"><svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 12l5 5 9-10"></path></svg></span><span>Every lead tracked and emailed to you</span></div><div class="rh-li"><span class="rh-tick"><svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 12l5 5 9-10"></path></svg></span><span>Day 7 and day 14 seller reports</span></div><div class="rh-li"><span class="rh-tick"><svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 12l5 5 9-10"></path></svg></span><span>Your brand, learned and kept up to date</span></div>
<div class="rh-list-go"><a class="rh-btn rh-btn-o" href="#" onclick="newCampaign();return false">Launch your next listing</a></div>
</div>
</div>
</section>

<div class="rh-wrap">
<section class="rh-finish">
<h2>Let’s give your next listing<br><span>a proper launch.</span></h2>
<a class="rh-btn rh-btn-o" href="#" onclick="newCampaign();return false">Get started</a>
</section>
</div>
 </main><footer class="home-footer">${logo}<span>Your expertise. Superpowered.</span>${footerLinks()}</footer></div>`;
 homeCalendarState={start:new Date('2026-11-02T12:00:00'),month:new Date('2026-11-01T12:00:00'),selected:0};renderHomeMonth();homeSellerReport(7);homeSitePreview();
 homeShowTab('site');
}
// The homepage "See it" box: one sample campaign, one piece at a time. Every piece is the real
// sample the app renders (listing website, calendar, ad, seller report), in a box you scroll.
const HOME_TABS={
 site:{label:'Listing website',title:'A website for every home',text:'Every listing gets its own page in your brand. All posts and ads send people here, and every inquiry is captured and sent to you.'},
 posts:{label:'14 days of posts',title:'Two weeks, all lined up',text:'Fourteen designed posts that tell the home’s story, each scheduled for when your audience is most active. Tap a post to open it.'},
 ad:{label:'Digital ad',title:'An ad campaign, run for you',text:'Resmara builds the ad from your best photos, sets your budget and audience, follows housing-ad rules and runs it for 14 days. Several versions run so Meta can show the one that works best.'},
 leads:{label:'Lead tracking',title:'Every lead, from everywhere',text:'Comments on your posts, replies to your ad and inquiries on the listing website all land in one list on your campaign, and each one is emailed to you the moment it comes in.'},
 report:{label:'Seller report',title:'Proof for your seller',text:'On day 7 and day 14 you get a clear report on reach, clicks and leads, ready to send to your homeowner.'}
};
function homeTabs(){return `<div class="rh-tabs" role="tablist" aria-label="Sample campaign">${Object.keys(HOME_TABS).map(k=>`<button type="button" role="tab" class="rh-tab" data-tab="${k}" aria-selected="false" onclick="homeShowTab('${k}')">${HOME_TABS[k].label}</button>`).join('')}</div>`}
function homePostsPanel(){return `<div class="home-calendar home-calendar-preview"><div class="home-calendar-head"><div><span>YOUR CAMPAIGN, BEFORE IT GOES LIVE</span><h3>See what’s going live.<br>And exactly when.</h3></div><div class="home-calendar-legend"><span><i class="lg-time"></i>Best time to post, picked for your area</span><span><i class="lg-ad"></i>Your listing ad, running all 14 days</span></div></div><div class="home-calendar-preview-body"><div class="flex home-preview-month"><strong id="home-month-title"></strong><span class="fine">Sample schedule · Pacific time</span></div><div class="review-month-grid" aria-label="Campaign calendar preview"><div class="review-month-weekdays">${['Sun','Mon','Tue','Wed','Thu','Fri','Sat'].map(d=>'<span>'+d+'</span>').join('')}</div><div id="home-month-grid"></div></div></div><div id="home-calendar-selection" hidden></div><p id="home-calendar-range" class="home-calendar-caption" hidden></p></div>`}
function homeShowTab(k){const t=HOME_TABS[k];if(!t)return;
 document.querySelectorAll('.rmh .rh-tab').forEach(b=>{const on=b.dataset.tab===k;b.classList.toggle('rh-on',on);b.setAttribute('aria-selected',String(on))});
 document.querySelectorAll('.rmh .rh-panel').forEach(p=>{p.hidden=p.dataset.tab!==k;const f=p.querySelector('.rh-frame');if(f&&!p.hidden)f.scrollTop=0});
 const ad=document.querySelector('#home-ad-view');if(k==='ad'&&ad&&!ad.innerHTML&&typeof sampleAdMarkup==='function')ad.innerHTML=sampleAdMarkup();
 if(k==='posts')homeFitCalendar();
 const h=document.querySelector('#home-tab-title'),p=document.querySelector('#home-tab-text');if(h)h.textContent=t.title;if(p)p.textContent=t.text;
}
// The sample calendar is laid out at full width and scaled to fit its box, so it reads like the real one.
function homeFitCalendar(){const f=document.querySelector('.rmh .rh-panel[data-tab="posts"] .rh-frame'),c=f&&f.querySelector('.home-calendar-preview');if(!c||!f.clientWidth)return;const z=Math.min(1,f.clientWidth/880);c.style.zoom=z}
window.addEventListener('resize',()=>{if(document.querySelector('.rmh'))homeFitCalendar()});
// Nav links to homepage sections work from any page: they open the homepage first if needed.
function homeGo(id){const go=()=>{const el=document.getElementById(id);if(el)el.scrollIntoView({behavior:'smooth',block:'start'})};if(!document.querySelector('.rmh')){home();setTimeout(go,60)}else go()}
function homeWorld(){return `<div class="home-world" role="img" aria-label="Resmara orchestrating social posts, digital advertising, a campaign calendar and analytics around your property"><span class="home-world-card hw-social"></span><span class="home-world-card hw-ad"></span><span class="home-world-card hw-calendar"></span><span class="home-world-card hw-report"></span><img class="home-world-house" src="resmara-house-complete-v1.png" alt=""><img class="home-world-robot" src="resmara-robot-clean-v1.png" alt=""></div>`}
let homeCalendarState;
const homePostTitles=SAMPLE_POSTS.map(p=>p.headline);
const homePostTimes=SAMPLE_POSTS.map(p=>p.time);
function calendarDateOffset(a,b){return Math.round((Date.UTC(a.getFullYear(),a.getMonth(),a.getDate())-Date.UTC(b.getFullYear(),b.getMonth(),b.getDate()))/86400000)}
function renderHomeMonth(){
 const state=homeCalendarState,host=document.querySelector('#home-month-grid');if(!host)return;
 document.querySelector('#home-month-title').textContent=state.month.toLocaleDateString(undefined,{month:'long',year:'numeric'});
 host.innerHTML=sampleCalendarWeeks(state);
 const end=new Date(state.start);end.setDate(end.getDate()+13);
 const f=new Intl.DateTimeFormat(undefined,{month:'short',day:'numeric'});
 document.querySelector('#home-calendar-range').textContent=f.format(state.start)+'–'+f.format(end);
}
function sampleCalendarWeeks(state,mini=false){
 const first=new Date(state.month);first.setDate(1-first.getDay());
 return (mini?[0,1]:[0,1,2]).map(week=>{
  const dates=Array.from({length:7},(_,col)=>{const d=new Date(first);d.setDate(first.getDate()+week*7+col);return d});
  const days=dates.map(date=>calendarDateOffset(date,state.start));
  const from=days.findIndex(day=>day>=0&&day<14),to=days.findLastIndex(day=>day>=0&&day<14);
  const bars=from<0?'': ['Listing ad · Facebook + Instagram'].map((title,lane)=>`<button class="review-month-ad" style="grid-column:${from+1}/${to+2};grid-row:${lane+2}" onclick="openCalendarAd(${lane})">${title}</button>`).join('');
  if(week===2)return `<div class="review-month-week home-calendar-fade-week" aria-hidden="true" style="--post-row:2">${dates.map((date,col)=>`<span class="review-month-date" style="grid-column:${col+1}">${date.getDate()}</span><div class="review-month-cell" style="grid-column:${col+1}"></div>`).join('')}</div>`;
  return `<div class="review-month-week" style="--post-row:${bars?3:2}">${dates.map((date,col)=>`<span class="review-month-date" style="grid-column:${col+1}">${date.getDate()}</span>`).join('')}${bars}${days.map((day,col)=>`<div class="review-month-cell" style="grid-column:${col+1}">${day>=0&&day<14?`<button class="review-calendar-post" onclick="openCalendarPost(${day})"><img src="${SAMPLE_POSTS[day].img}" alt=""><b>${homePostTitles[day]}</b><small>◷ ${homePostTimes[day]}</small></button>${day===6?`<span class="review-calendar-report"><button class="alt" onclick="${mini?'campaignReport(examples[0],7)':'openCalendarReport(7)'}">● View report</button></span>`:''}`:''}</div>`).join('')}</div>`;
 }).join('');
}
function samplePostPreview(day){
 const date=new Date(2026,10,2,12);date.setDate(date.getDate()+day);
 return `<img src="${day%3===0?img2:img}" alt="Property creative preview"><p>${date.toLocaleDateString(undefined,{weekday:'short',month:'short',day:'numeric'})} · ${homePostTimes[day]} Pacific · best time for your area</p><p>Branded property post · Facebook + Instagram</p>`;
}
function homeSellerReport(day){const target=document.querySelector('#home-report-preview');if(!target)return;document.querySelectorAll('.home-report-switch button').forEach(b=>b.setAttribute('aria-selected',String(b.id==='seller-tab-'+day)));target.setAttribute('aria-labelledby','seller-tab-'+day);
 target.innerHTML=`<div class="pr-home">${propertyReportHTML(demoReportData({address:'The Oakridge House',area:'Austin, TX',image:'sample/post-01.jpg'},day))}</div>${scrollHint('Scroll to see the full report')}`;target.scrollTop=0;target.classList.remove('scrolled');armScrollHint(target)}

function siteNav(active){
 const sec=[['what','What you get'],['how','How it works'],['pricing','Pricing']];
 return `<header class="home-nav shared-nav">${logo}<nav aria-label="Main navigation">${sec.map(([id,label])=>`<a class="nav-sec" href="#${id}" onclick="homeGo('${id}');return false">${label}</a>`).join('')}<a href="#setup-guides" ${active==='setup-guides'?'aria-current="page"':''} onclick="setupGuides();return false">Resources</a></nav><button class="alt" onclick="clientAccess()">${state.clientSignedIn?'My Dashboard':'Log in'}</button></header>`;
}
function footerLinks(){
 return `<span style="display:flex;gap:22px;flex-wrap:wrap;align-items:center;font-size:12px"><a href="privacy.html">Privacy</a><a href="data-deletion.html">Data deletion</a><a href="terms.html">Terms</a><a href="mailto:resmaraai@gmail.com" target="_blank" rel="noopener">Contact</a><a href="admin.html">Team room</a></span>`;
}
// Signing out ends this browser's copy of the workspace too. Two agents can share one machine,
// and the next account must never open on the last one's listings: a new client signed up here
// after another account and was shown that account's Coggins campaigns as if they were its own.
// Everything account-scoped goes; the theme and the API token are handled separately.
function clearAccountWorkspace(){
 state.campaigns=[];state.leads={};state.reviews={};state.brand={};state.supportUnread=0;state.hiddenSamples=[];
 state.priorDemos=[];state.firstRun=false;state.tourDone=false;state.metaRequired=false;state.connected=false;
 state.company='';state.email='';state.isAdmin=false;
}
function signOutDemo(){clearAccountWorkspace();if(window.RM&&RM.logout)RM.logout();state.name='';state.clientSignedIn=false;persist();home();window.scrollTo(0,0)}
// Show what was typed into a password box. Chrome's own reveal is not available on every
// browser and does not exist inside the app's modal, so the form carries its own control.
function togglePw(btn){
 const wrap=btn.closest('.pw-wrap'),input=wrap&&wrap.querySelector('input');
 if(!input)return;
 const show=input.type==='password';
 input.type=show?'text':'password';
 btn.textContent=show?'Hide':'Show';
 btn.setAttribute('aria-label',show?'Hide password':'Show password');
 btn.setAttribute('aria-pressed',show?'true':'false');
}
function clientAccessEmail(mode='signin'){
 // state.clientSignedIn is a browser memory, not a session. Ask the API client whether the
 // token is still alive, or a customer whose session ended can never reach the form to fix it.
 if(state.clientSignedIn&&window.RM&&RM.isLoggedIn()){dashboard();return}
 if(state.clientSignedIn){state.clientSignedIn=false;persist()}
 const creating=mode==='create';
 show(`<span class="eyebrow">RESMARA CLIENT AREA</span><h2>${creating?'Create an account':'Client Login'}</h2><p>${creating?'Just your name, email and a password. Resmara learns the rest when you connect your Meta account.':'Enter your email and password.'}</p><form onsubmit="event.preventDefault();submitTestClient(this,${creating})">${creating?'<div class="nc-row name-row"><label class="field">First name<input name="firstName" required maxlength="60" autocomplete="given-name"></label><label class="field">Last name<input name="lastName" required maxlength="60" autocomplete="family-name"></label></div>':''}<label class="field">Email address<input name="clientEmail" type="email" required maxlength="254" autocomplete="email"></label><label class="field">Password<span class="pw-wrap"><input name="clientPassword" type="password" required minlength="${creating?8:1}" autocomplete="${creating?'new-password':'current-password'}"><button type="button" class="pw-eye" onclick="togglePw(this)" aria-label="Show password" aria-pressed="false">Show</button></span></label>${creating?'<details class="invite-toggle"><summary>Have an invite code?</summary><label class="field">Invite code<input name="inviteCode" maxlength="64" autocomplete="off" spellcheck="false" placeholder="From your invitation"></label></details><label class="terms-agree" style="display:flex;gap:10px;align-items:flex-start;margin:14px 0 4px;font-size:14px;line-height:1.45;color:#12354d;cursor:pointer"><input type="checkbox" name="agreeTerms" required style="margin-top:3px;width:18px;height:18px;flex:0 0 18px"><span>I agree to the <a href="terms.html" target="_blank" rel="noopener" style="color:#12354d;font-weight:700;text-decoration:underline">Terms of Service</a> and <a href="privacy.html" target="_blank" rel="noopener" style="color:#12354d;font-weight:700;text-decoration:underline">Privacy Policy</a>, including the <b>arbitration agreement and class action waiver</b> in section 17 of the Terms.</span></label>':''}<p class="fine" role="status"></p><div class="modal-actions"><button>${creating?'Create account':'Sign in'}</button><button type="button" class="alt" onclick="clientAccessEmail('${creating?'signin':'create'}')">${creating?'Back to sign in':'Create an account'}</button></div></form>${state.name&&!state.email?'<button class="alt" onclick="resumeDemo()">Resume previous demo</button>':''}<p class="fine">${creating?'Passwords need at least 8 characters.':'<a href="#" onclick="forgotPassword();return false">Forgot your password?</a>'}</p>`);
}
// Engine 1 Part A: "Log in with Facebook" is the door (Adam, 22 Nov). One pop-up for new and
// returning clients - an existing Facebook signs in, a new one creates the account and starts
// the Meta connection in the same step. The email form stays underneath as the fallback until
// Meta's App Review approves the email permission for customers, and that is said on screen.
function clientAccess(mode = 'signin') {
 // state.clientSignedIn is a browser memory, not a session: ask the API client whether the
 // token is still alive, or a customer whose session ended can never reach the form to fix it.
 if (state.clientSignedIn && window.RM && RM.isLoggedIn()) { dashboard(); return; }
 if (state.clientSignedIn) { state.clientSignedIn = false; persist(); }
 fbLoginPopup();
}

const FB_TERMS = '<label class="terms-agree" style="display:flex;gap:10px;align-items:flex-start;margin:14px 0 4px;font-size:14px;line-height:1.45;color:#12354d;cursor:pointer">'
 + '<input type="checkbox" id="fbTerms" style="margin-top:3px;width:18px;height:18px;flex:0 0 18px" onchange="var g=document.getElementById(\'fbGo\');if(g)g.disabled=!this.checked">'
 + '<span>I agree to the <a href="terms.html" target="_blank" rel="noopener" style="color:#12354d;font-weight:700;text-decoration:underline">Terms of Service</a> and '
 + '<a href="privacy.html" target="_blank" rel="noopener" style="color:#12354d;font-weight:700;text-decoration:underline">Privacy Policy</a>, including the '
 + '<b>arbitration agreement and class action waiver</b> in section 17 of the Terms.</span></label>';

function fbLoginPopup() {
 show(`<span class="eyebrow">RESMARA CLIENT AREA</span><h2>Log in with Facebook</h2>
 <p>Resmara does everything through Facebook: your Page, your Instagram and your ad account. Logging in connects them, so there is nothing else to set up first.</p>
 ${FB_TERMS}
 <p class="fine" id="fbStatus" role="status"></p>
 <div class="modal-actions">
  <button type="button" class="alt" onclick="clientAccessEmail()">Use email and password instead</button>
  <button type="button" class="campaign-primary" id="fbGo" disabled onclick="fbLoginBegin()">Continue with Facebook</button>
 </div>
 <p class="fine">No Facebook account? You'll need one to use Resmara. It's free: <a href="https://www.facebook.com/reg/" target="_blank" rel="noopener">create one on Facebook</a>, then come back here.</p>`);
}

async function fbLoginBegin() {
 const status = document.getElementById('fbStatus');
 const go = document.getElementById('fbGo');
 if (!window.RM || !RM.facebookStart) { if (status) status.textContent = 'The API client is unavailable in this browser.'; return; }
 const box = document.getElementById('fbTerms');
 if (!box || !box.checked) { if (status) status.textContent = 'Tick the box agreeing to the Terms first.'; return; }
 if (go) { go.disabled = true; go.textContent = 'Opening Facebook…'; }
 try {
  const reply = await RM.facebookStart(RM.termsVersion ? RM.termsVersion() : undefined);
  if (reply && reply.redirect_url) { location.href = reply.redirect_url; return; }
  throw new Error('Facebook did not answer with a login window.');
 } catch (err) {
  if (status) status.textContent = (err && err.message) || 'Facebook login could not start.';
  if (go) { go.disabled = false; go.textContent = 'Continue with Facebook'; }
 }
}

// Facebook's return trip: a one-time ticket, never a token in the URL.
async function fbReturn() {
 const query = new URLSearchParams(location.search);
 const outcome = query.get('fb');
 if (!outcome) return false;
 history.replaceState({}, '', location.pathname + location.hash);
 if (outcome === 'login') {
  show(`<span class="eyebrow">SIGNING YOU IN</span><h2>Just a moment…</h2><p>Facebook said yes. Resmara is opening your account.</p>`);
  try {
   const reply = await RM.facebookExchange(query.get('ticket') || '');
   state.clientSignedIn = true; state.firstRun = true; persist();
   if (reply && reply.needs_email) { fbAskEmail(); return true; }
   if (modal.open) modal.close();
   metaGateOnLogin();
  } catch (err) { fbLoginFailed((err && err.message) || 'Signing in did not finish.'); }
  return true;
 }
 if (outcome === 'closed') { fbReactivatePrompt(query.get('ticket') || ''); return true; }
 if (outcome === 'cancelled') { toast('Facebook sign-in was cancelled - nothing changed.'); clientAccess(); return true; }
 fbLoginFailed(query.get('reason') || 'Facebook did not finish the sign-in.');
 return true;
}

function fbLoginFailed(reason) {
 show(`<span class="eyebrow">FACEBOOK SIGN-IN</span><h2>That didn't finish.</h2><p>${esc(reason)}</p><div class="modal-actions"><button type="button" class="alt" onclick="clientAccessEmail()">Use email and password</button><button type="button" class="campaign-primary" onclick="clientAccess()">Try Facebook again</button></div>`);
}

// Some Facebook accounts hide the email. We ask once - for receipts, never to sign in.
function fbAskEmail() {
 show(`<span class="eyebrow">ONE MORE THING</span><h2>What email should we use?</h2><p>Facebook didn't share one. We only use it for receipts and updates - you'll keep signing in with Facebook.</p>
 <form onsubmit="event.preventDefault();fbSaveEmail(this)"><label class="field">Email address<input name="email" type="email" required maxlength="254" autocomplete="email"></label><p class="fine" role="status"></p><div class="modal-actions"><span></span><button class="campaign-primary">Save it</button></div></form>`);
}

async function fbSaveEmail(form) {
 const status = form.querySelector('[role="status"]');
 status.textContent = 'Saving…';
 try {
  await RM.setEmail(form.elements.email.value.trim());
  modal.close(); metaGateOnLogin();
 } catch (err) { status.textContent = (err && err.message) || 'That did not save.'; }
}

// "This account has been closed. Would you like to reactivate it?" - one click, all back.
function fbReactivatePrompt(ticket) {
 show(`<span class="eyebrow">ACCOUNT CLOSED</span><h2>Welcome back.</h2><p>This account has been closed. Would you like to reactivate it? Everything is still here - your campaigns, leads and reports.</p>
 <div class="modal-actions"><span></span><button type="button" class="campaign-primary" onclick="fbReactivate('${esc(ticket)}')">Reactivate my account</button></div>`);
}

async function fbReactivate(ticket) {
 try {
  const reply = await RM.facebookReactivate(ticket);
  state.clientSignedIn = true; persist();
  if (reply && reply.needs_email) { fbAskEmail(); return; }
  if (modal.open) modal.close();
  metaGateOnLogin();
 } catch (err) { fbLoginFailed((err && err.message) || 'Reactivating did not finish.'); }
}

function forgotPassword(){
 show(`<span class="eyebrow">PASSWORD HELP</span><h2>Reset your password</h2><p>Enter the email address on your account and we will send a link to choose a new password.</p><form onsubmit="event.preventDefault();requestResetLink(this)"><label class="field">Email address<input name="email" type="email" required maxlength="254" autocomplete="email" value="${esc(state.email||'')}"></label><p class="fine" role="status"></p><div class="modal-actions"><button>Send reset link</button><button type="button" class="alt" onclick="clientAccess()">Back to sign in</button></div></form><p class="fine">The link works once and expires in an hour.</p>`);
}
async function requestResetLink(form){
 const status=form.querySelector('[role="status"]');
 const email=form.elements.email.value.trim();
 if(!window.RM){status.textContent='The API client is unavailable in this browser.';return}
 status.textContent='Sending…';
 try{
  const reply=await RM.requestPasswordReset(email);
  if(reply&&reply.delivery==='email'){
   show(`<span class="eyebrow">CHECK YOUR EMAIL</span><h2>Link sent</h2><p>If an account exists for ${esc(email)}, a reset link is on its way. It expires in ${reply.expires_minutes||60} minutes.</p><div class="modal-actions"><button onclick="clientAccess()">Back to sign in</button></div>`);
   return;
  }
  // No mail provider yet: say so plainly and give the customer a real way through, instead
  // of a page that claims a letter was sent when nothing left the server.
  show(`<span class="eyebrow">EMAIL NOT CONNECTED</span><h2>We cannot send the link yet</h2><p>Email is not connected to Resmara, so the reset link cannot be delivered automatically. Use the Contact link in the footer and we will send you a one-time link from the operator console.</p><div class="modal-actions"><button onclick="clientAccess()">Back to sign in</button><a class="alt" href="mailto:resmaraai@gmail.com?subject=Password%20reset%20request" target="_blank" rel="noopener">Email us</a></div>`);
 }catch(err){
  status.textContent=(err&&err.message)||'Could not start the reset.';
 }
}
// The sign-up email's link lands on /confirm?token=... (see app.js), and this is the screen a
// new agent sees when the confirmation was actually sent.
function confirmEmailPage(email){
 show(`<span class="eyebrow">CHECK YOUR EMAIL</span><h2>Confirm your address</h2><p>We sent a link to ${esc(email||'your inbox')}. Open it and you are in - the account is ready, it just needs the address proved first.</p><p class="fine" role="status">Nothing after a minute? Check the spam folder, then ask for another link.</p><div class="modal-actions"><button onclick="resendConfirm('${esc(String(email||'').replace(/'/g,''))}')">Send it again</button><button type="button" class="alt" onclick="clientAccess()">Back to sign in</button></div>`);
}
async function resendConfirm(email){
 const box=document.querySelector('[role="status"]');
 if(box)box.textContent='Sending…';
 try{
  const r=await RM.request('/api/auth/confirm/resend?email='+encodeURIComponent(email||''),{method:'POST'});
  if(box)box.textContent=(r&&r.delivery==='sent')?'Another link is on its way.':'Email is not connected yet, so there is nothing to resend - tell us and we will confirm it by hand.';
 }catch(e){if(box)box.textContent=(e&&e.message)||'Could not resend that link.'}
}

function resetPasswordPage(token){
 // Same pop-up card as Client Login, over the homepage, so a reset looks like the rest of the client area.
 document.title='Choose a new password — Resmara';
 if(typeof home==='function')home();
 show(`<span class="eyebrow">RESMARA CLIENT AREA</span><h2>Choose a new password</h2>${token?'<p>Type it twice. This link works once.</p>':'<p>This link is missing its reset code. Ask for a new one from Client Login.</p>'}<form onsubmit="event.preventDefault();submitNewPassword(this)" data-token="${esc(token)}"><label class="field">New password<span class="pw-wrap"><input name="password" type="password" required minlength="8" autocomplete="new-password"><button type="button" class="pw-eye" onclick="togglePw(this)" aria-label="Show password" aria-pressed="false">Show</button></span></label><label class="field">Type it again<span class="pw-wrap"><input name="confirm" type="password" required minlength="8" autocomplete="new-password"><button type="button" class="pw-eye" onclick="togglePw(this)" aria-label="Show password" aria-pressed="false">Show</button></span></label><p class="fine" role="status"></p><div class="modal-actions"><button${token?'':' disabled'}>Save new password</button><button type="button" class="alt" onclick="clientAccess()">Back to sign in</button></div></form>`);
}
async function submitNewPassword(form){
 const status=form.querySelector('[role="status"]');
 const password=form.elements.password.value, confirm=form.elements.confirm.value;
 if(password!==confirm){status.textContent='Those two passwords do not match.';return}
 if(password.length<8){status.textContent='Use at least 8 characters.';return}
 if(!window.RM){status.textContent='The API client is unavailable in this browser.';return}
 status.textContent='Saving…';
 try{
  await RM.confirmPasswordReset(form.dataset.token,password);
  show(`<span class="eyebrow">RESMARA CLIENT AREA</span><h2>Password changed</h2><p>You're set. Sign in with your new password.</p><div class="modal-actions"><button onclick="clientAccess()">Sign in</button></div>`);
 }catch(err){
  status.textContent=(err&&err.message)||'This reset link is invalid or has expired.';
 }
}
function resumeDemo(){state.clientSignedIn=true;persist();modal.close();dashboard()}
function submitTestClient(form,creating){
 const email=form.elements.clientEmail.value.trim().toLowerCase();
 const password=form.elements.clientPassword?form.elements.clientPassword.value:'test123';
 const name=creating?[form.elements.firstName.value.trim(),form.elements.lastName.value.trim()].filter(Boolean).join(' '):'';
 const invite=creating&&form.elements.inviteCode?form.elements.inviteCode.value.trim():'';
 const status=form.querySelector('[role="status"]');
 // Who this browser was last signed in as. A different address signing in here is a different
 // person: they get their own empty workspace and the two samples, never the last account's.
 const priorOwner=String(state.email||'').trim().toLowerCase();
 if(priorOwner&&priorOwner!==email)clearAccountWorkspace();
 if(creating&&!name){status.textContent='Enter your name.';return}
 // The clickwrap (Terms, section 1): no account without the unchecked-by-default box ticked.
 if(creating&&form.elements.agreeTerms&&!form.elements.agreeTerms.checked){status.textContent='Please agree to the Terms of Service and Privacy Policy to create your account.';return}
 if(!window.RM){status.textContent='The API client is unavailable in this browser.';return}
 status.textContent=creating?'Creating your account…':'Signing in…';
 // Register/login now go through the shared API client (RM) instead of a hand-rolled fetch.
 (async()=>{
  let account;
  if(creating){
   account=await RM.register(email,password,name,invite);
   // Register returns the account (no token), so sign in to obtain one. Best effort - except
   // when the account is waiting on its confirmation email (item 8): then there is nothing to
   // sign in to yet, and pretending otherwise lands them in an empty dashboard.
   try{const session=await RM.login(email,password);if(session&&session.access_token)RM.setToken(session.access_token)}catch(err){
    if(/confirm/i.test(String((err&&err.message)||''))){confirmEmailPage(email);return}
   }
  }else{
   account=await RM.login(email,password);
   if(account&&account.access_token)RM.setToken(account.access_token);
  }
  // The same person signing back in keeps the browser's copy: this used to be `state={...blank}`
  // and it threw away the brand profile, logo/headshot and a campaign built while signed out.
  // A different person keeps nothing (clearAccountWorkspace ran above); their own campaigns come
  // back from /api/boosts, so an empty local list here is never a lost listing.
  state={...state,name:(account&&account.name)||state.name||name,email,clientSignedIn:true,campaigns:priorOwner&&priorOwner!==email?[]:(state.campaigns||[]),connected:!!state.connected};
  try{localStorage.setItem('resmara',JSON.stringify(state))}catch{}
  modal.close();if(creating){state.firstRun=true;state.metaRequired=true;persist();dashboard();setTimeout(()=>onboard(0),400)}else if(typeof metaGateOnLogin==='function'){metaGateOnLogin();toast('Signed in as '+email)}else{dashboard();if(state.firstRun&&!state.tourDone)setTimeout(()=>onboard(0),400);else toast('Signed in as '+email);}
  if(window.RM&&RM.brandProfile){RM.brandProfile().then(remote=>{
    if(!remote||typeof remote!=='object')return;
    // The account's own profile, if it has one, is the copy to keep - it is the one that
    // survives a cleared browser. Local-only brand still wins until the server is told.
    if(!state.brand||!Object.keys(state.brand||{}).length){state.brand={...remote};persist();if(view==='brand')myBrand()}
  }).catch(()=>{})}
 })().catch(e=>{
  if(e&&e.status){ // a real API answer (400/401/403): show the server's reason
   status.textContent=e.message||'Login failed';
   return;
  }
  // API unreachable (offline): keep the local demo usable so the prototype still renders.
  state={...state,name:name||state.name,email,clientSignedIn:true,campaigns:state.campaigns||[],connected:false};
  try{localStorage.setItem('resmara',JSON.stringify(state))}catch{}
  modal.close();dashboard();toast('Offline demo session · '+email);
 });
}
function restorePriorDemo(){
 const prior=state.priorDemos||[];if(!prior.length)return;
 const {priorDemos,...current}=state;
 state={...prior.at(-1),clientSignedIn:true,priorDemos:[...prior.slice(0,-1),current]};
 persist();dashboard()
}
function openCalendarPost(day){
 const p=SAMPLE_POSTS[day],date=new Date(2026,10,2,12);date.setDate(date.getDate()+day);
 show(`<span class="eyebrow">DAY ${p.day} OF 14 · ${p.kicker}</span><div class="sp-modal"><img class="sp-img" src="${p.img}" alt="Designed post: ${esc(p.headline)}"><div class="sp-side"><p class="sp-when">◷ ${date.toLocaleDateString(undefined,{weekday:'long',month:'short',day:'numeric'})} · ${p.time}<br><small>Best time for your area · Facebook + Instagram</small></p><div class="sp-caption"><p>${esc(p.caption)}</p><p>${esc(p.cta)}</p><p class="sp-close">${esc(SAMPLE_CLOSING)}</p><p class="sp-tags">${p.tags.map(esc).join(' ')}</p></div><div class="sp-actions"><span>Before you approve: swap the photo, rewrite the headline or caption, or move it.</span><span>After you approve: it’s locked in. You can only withdraw it.</span></div></div></div><p class="fine">Sample campaign · AI-generated photos of a fictional home, designed by the Resmara engine.</p>`);
}
function openCalendarAd(){
 const a=SAMPLE_AD,c=SAMPLE_POSTS[(a.creativeDays||[7])[0]-1];
 show(`<span class="eyebrow">YOUR LISTING AD · FACEBOOK + INSTAGRAM</span><h2>One ad, three of your best posts.</h2><div class="sp-ad"><div class="sp-ad-card"><div class="sp-ad-head"><span>M</span><div><b>Morgan Ellis</b><small>Sponsored</small></div></div><p>${esc(a.primaryText)}</p><img src="${c.img}" alt=""><div class="sp-ad-link"><div><small>OAKRIDGE HOUSE</small><b>${esc(a.headline)}</b></div><span>Learn more</span></div></div><div class="sp-ad-facts"><div><small>BUDGET</small><b>$50 total</b><span>Paid to Meta from your ad account</span></div><div><small>RUNS</small><b>14 days</b><span>Starts on your go-live date</span></div><div><small>REACH</small><b>Around the listing</b><span>15+ mile radius · housing rules applied</span></div><div><small>CREATIVES</small><b>3 posts</b><span>Meta favours the best performer</span></div></div></div>`);
}
function openCalendarReport(day){
 const current=document.querySelector('#seller-tab-14').getAttribute('aria-selected')==='true'?14:7;
 homeSellerReport(day);const preview=document.querySelector('#home-report-preview').innerHTML;homeSellerReport(current);show(preview);
}

function onboard(stage=0){
 if(stage===0){
  show(`<span class="eyebrow">FIRST CAMPAIGN · STEP 1 OF 3</span><h2>Set up My Brand.</h2><p>Start with three details. Resmara can use your public website to draft a brand profile for you to review later.</p>${brandProfileForm(true)}`);return
 }
 if(liveCampaignsAvailable()){
  // A signed-in client connects for real: Facebook Login hands the app an ad account it may
  // manage, and Meta bills the client's own card. No demo audit is pretended here.
  show(`<span class="eyebrow">FIRST CAMPAIGN · STEP 2 OF 3</span><h2>Connect your Meta business assets.</h2><p>Facebook Login lets you choose the Business Portfolio, Page and ad account Resmara may manage. Ad spend is billed by Meta to your own card; Resmara never handles your money.</p><div class="notice checkout-notice" id="live-meta-step">Reading your connected accounts…</div><div class="modal-actions"><button class="alt" onclick="onboard()">Back</button><button class="campaign-primary" onclick="modal.close();newCampaign()">Continue</button></div>`);
  renderLiveMetaStep();return
 }
 show(`<span class="eyebrow">FIRST CAMPAIGN · STEP 2 OF 3</span><h2>Connect your Meta business assets.</h2><p>In the live app, Facebook Login for Business will let you select your Business Portfolio, Facebook Page and ad account. You can also select Instagram if you publish there.</p><div class="notice checkout-notice">Preview mode · no Facebook login, permissions or live account checks.</div><label class="field">Try an account scenario<select id="demo-meta-scenario"><option value="ready">Business, Page and ad account ready</option><option value="blocked">Ad account needs attention</option></select></label><div class="modal-actions"><button class="alt" onclick="onboard()">Back</button><button onclick="runMetaAudit(document.querySelector('#demo-meta-scenario').value)">Run demo connection check</button></div>`);
}
// Shows the ad accounts that are really connected, and offers the real Facebook login when
// there are none. Never invents a "connected" state.
async function renderLiveMetaStep(){
 const box=document.getElementById('live-meta-step');if(!box||!window.RM)return;
 try{
  const rows=await RM.adAccounts();
  const list=Array.isArray(rows)?rows:(rows&&(rows.accounts||rows.items))||[];
  if(!list.length){box.innerHTML='No Meta account is connected yet — a campaign needs your Facebook Page and an ad account. <button class="alt" type="button" onclick="connectMeta()">Connect Meta</button>';return}
  box.innerHTML=list.map(a=>esc([a.name||'Ad account',a.ad_account_id||a.external_id||'',a.simulated?'(demo)':''].filter(Boolean).join(' · '))).join('<br>');
 }catch(error){box.textContent='Could not read your connected accounts: '+error.message}
}
function campaignBrandProfile(){
 return {...state.brand,agent:state.name||'',brokerage:state.company||''};
}
// My Brand: the brand engine fills this in from the agent's website, socials and brokerage.
// The agent only checks it and changes what is wrong. Signed-out review copies show a sample kit.
const SAMPLE_BRAND={agent:'Morgan Ellis',brokerage:'Morgan & Co. Property Advisors',license:'TX #0712345',website:'https://morganandco.example',market:'West Austin, Lakeway and the Hill Country',brandLink:'https://instagram.com/morganellis.example',
 palette:[['Primary','#143A50'],['Accent','#B8925A'],['Text','#2B2B2B'],['Tint','#E9E1D3'],['Page','#FAF7F1']],
 fonts:['Playfair Display','Jost'],voice:'Warm. Assured. Unhurried. Speaks like a neighbor who knows the area, never like an ad.',use:['Come walk it with me','Room to breathe','Slow mornings'],avoid:['Stunning','Must-see','Hurry!'],
 theme:'Modern',legal:['Morgan Ellis · REALTOR® · TX #0712345','Morgan & Co. Property Advisors','Equal Housing Opportunity'],
 sources:[['Website','morganandco.example'],['Instagram','@morganellis'],['Facebook','Morgan Ellis Realtor'],['Brokerage profile','Morgan & Co.']],researched:'Nov 14, 2026'};
function brandKitData(){
 const b=campaignBrandProfile()||{},demo=!(window.RM&&RM.isLoggedIn&&RM.isLoggedIn())&&!b.website,d=demo?SAMPLE_BRAND:{};
 const palette=b.palette||(b.colours?String(b.colours).split(/[,\s]+/).filter(x=>/^#?[0-9a-f]{6}$/i.test(x)).map((h,i)=>[['Primary','Accent','Text','Tint','Page'][i]||'Colour',h[0]==='#'?h:'#'+h]):null)||d.palette||[];
 return {demo,agent:b.agent||state.name||d.agent||'',brokerage:b.brokerage||state.company||d.brokerage||'',license:b.license||d.license||'',website:b.website||d.website||'',market:b.market||d.market||'',brandLink:b.brandLink||d.brandLink||'',
  palette,fonts:b.fonts||d.fonts||['Playfair Display','Jost'],voice:b.voice||d.voice||'',use:b.use||d.use||[],avoid:b.avoid||d.avoid||[],theme:b.theme||d.theme||'Match my brand',legal:b.legal||d.legal||[],sources:b.sources||d.sources||[],researched:b.researched||d.researched||'',
  logo:state.brandMedia?.[b.logoId]||'',headshot:state.brandMedia?.[b.headshotId]||''};
}
function brandKitSections(k){
 const initials=(k.brokerage||k.agent||'R').replace(/[^A-Za-z ]/g,'').split(' ').filter(Boolean).slice(0,1).map(w=>w[0]).join('')||'R';
 const field=(name,label,value,src,mode='text')=>`<label class="mb-field"><span>${label}${src?`<em>${src}</em>`:''}</span><input name="${name}" inputmode="${mode}" value="${esc(value)}"></label>`;
 const img=(kind,label,url,found)=>`<div class="mb-asset"><div class="mb-asset-img ${kind}">${url?`<img src="${esc(url)}" alt="${label}">`:(kind==='logo'?`<span class="mb-mono">${esc(initials)}</span>`:'<span class="mb-face"></span>')}</div><div><b>${label}</b><small>${url||k.demo?found:'Not found yet. Add one.'}</small><label class="mb-replace">Replace<input name="${kind}" type="file" accept="image/png,image/jpeg,image/webp" hidden></label></div></div>`;
  return `
  <header class="mb-head"><div class="mb-id">${k.logo?`<img src="${esc(k.logo)}" alt="Logo">`:`<span class="mb-mono lg">${esc(initials)}</span>`}<div><b>${esc(k.brokerage||k.agent)}</b><small>${esc(k.agent)}${k.market?' · '+esc(k.market):''}</small></div></div><span class="mb-tag">BRAND KIT</span></header>
  <section class="mb-sec"><h4>YOU</h4><div class="mb-grid">${field('agent','Agent name',k.agent,'Website')}${field('company','Brokerage',k.brokerage,'Brokerage profile')}${field('license','License number',k.license,'Brokerage profile')}${field('website','Website',k.website,'','url')}${field('market','Markets you serve',k.market,'Your listings')}${field('brandLink','Instagram or brand guide',k.brandLink,'Found','url')}</div></section>
  <section class="mb-sec"><h4>LOGO &amp; HEADSHOT</h4><div class="mb-assets">${img('logo','Logo',k.logo,'Found on your website')}${img('headshot','Headshot',k.headshot,'Found on your brokerage profile')}</div></section>
  <section class="mb-sec"><h4>COLOURS</h4><div class="mb-swatches">${k.palette.map(([role,hex],i)=>`<label class="mb-sw"><input type="color" value="${esc(hex)}" oninput="this.nextElementSibling.querySelector('code').textContent=this.value.toUpperCase();brandColoursSync(this.form)"><span><b>${esc(role)}</b><code>${esc(hex.toUpperCase())}</code></span></label>`).join('')}</div><small>Click a colour to change it.</small><input type="hidden" name="colours" value="${esc(k.palette.map(p=>p[1]).join(', '))}"></section>
  <div class="mb-two"><section class="mb-sec"><h4>TYPOGRAPHY</h4><p class="mb-type-h" style="font-family:'${esc(k.fonts[0])}',serif">The long view</p>${fontPicker('fontHead','Headlines',k.fonts[0],'.mb-type-h')}<p class="mb-type-b" style="font-family:'${esc(k.fonts[1])}',sans-serif">Morning light, wide oak floors and room to breathe.</p>${fontPicker('fontBody','Body',k.fonts[1],'.mb-type-b')}<small>Resmara picked these to match your brand. Change either one any time.</small></section>
  <section class="mb-sec"><h4>VOICE</h4><textarea name="voice" rows="2">${esc(k.voice)}</textarea><div class="mb-chips">${k.use.map(w=>`<span class="ok">“${esc(w)}”</span>`).join('')}${k.avoid.map(w=>`<span class="no">${esc(w)}</span>`).join('')}</div></section></div>
  <div class="mb-two"><section class="mb-sec"><h4>YOUR LOOK</h4><input type="hidden" name="theme" value="${esc(k.theme)}"><div class="mb-looks">${['Modern','Classic','Rustic','Match my brand'].map(t=>`<button type="button" class="${t===k.theme?'on':''}" onclick="const f=this.form;f.elements.theme.value='${t}';this.parentNode.querySelectorAll('button').forEach(x=>x.classList.toggle('on',x===this));brandMarkDirty()">${t}</button>`).join('')}</div><small>Change your look any time. New campaigns use it once you save.</small></section>
  <section class="mb-sec"><h4>ON EVERY POST</h4><ul class="mb-legal">${k.legal.map(l=>`<li>${esc(l)}</li>`).join('')}</ul><small>Your brokerage’s rules, checked.</small></section></div>
  <section class="mb-sec"><h4>WHERE RESMARA LOOKED</h4><div class="mb-sources">${k.sources.map(([t,v])=>`<span>✓ <b>${esc(t)}</b> ${esc(v)}</span>`).join('')}</div></section>
  `}
function myBrand(){
 const k=brandKitData();
 $('#content').innerHTML=`<div class="welcome mb-page-head"><h1>My Brand</h1></div><div class="notice page-intro">This is the brand kit Resmara built from your website, socials and brokerage. Every post and ad follows it, so check it over, fix anything that’s off and save.</div>
 <form class="mb" onsubmit="saveBrandProfile(event,this,false)" oninput="brandMarkDirty()" onchange="brandMarkDirty()">${brandKitSections(k)}<p class="fine" data-brand-error role="alert"></p>
  <div class="mb-foot"><div class="mb-status"><button class="mb-research" type="button" onclick="brandResearchAgain(this)">Research again</button><span>✓ Researched ${esc(k.researched||'from your website')}</span><span class="mb-unsaved" hidden>Unsaved changes</span></div><button class="campaign-primary">Save my brand</button></div>
 </form>`;
 window.brandDirty=false;
 [k.fonts[0],k.fonts[1]].forEach(loadGoogleFont);
}
// ---- My Brand: fonts, unsaved changes ------------------------------------------------------
// Any Google font: the name is loaded from Google Fonts on the fly so the preview shows it.
function loadGoogleFont(name){
 name=String(name||'').trim();if(!name)return;const id='gf-'+name.replace(/\W+/g,'-').toLowerCase();if(document.getElementById(id))return;
 const l=document.createElement('link');l.id=id;l.rel='stylesheet';l.href='https://fonts.googleapis.com/css2?family='+encodeURIComponent(name).replace(/%20/g,'+')+':wght@400;600;700&display=swap';document.head.appendChild(l);
}
// A font picker that looks like our drop-downs: the button shows the current font in itself;
// the list shows every font written in its own typeface with a short sample, with a search box.
// Any Google font can be used: type its name and choose "Use … from Google Fonts".
function fontPicker(name,label,value,target){
 return `<div class="mb-font"><span>${label}</span><input type="hidden" name="${name}" value="${esc(value)}"><button type="button" class="mb-fontpick" data-target="${target}" onclick="openFontPicker(this)" style="font-family:'${esc(value)}',${target==='.mb-type-h'?'serif':'sans-serif'}"><b>${esc(value)}</b><i class="mb-fontpick-chev" aria-hidden="true"></i></button></div>`;
}
function loadFontBatch(names,sample){
 const fresh=names.filter(n=>!loadFontBatch.done.has(n));if(!fresh.length)return;fresh.forEach(n=>loadFontBatch.done.add(n));
 for(let i=0;i<fresh.length;i+=20){
  const fam=fresh.slice(i,i+20).map(n=>'family='+encodeURIComponent(n).replace(/%20/g,'+')).join('&');
  const chars=[...new Set((fresh.slice(i,i+20).join('')+sample+'0123456789').split(''))].join('');
  const l=document.createElement('link');l.rel='stylesheet';l.href='https://fonts.googleapis.com/css2?'+fam+'&display=swap&text='+encodeURIComponent(chars);document.head.appendChild(l);
 }
}
loadFontBatch.done=new Set();
function openFontPicker(btn){
 closeFontPicker();
 const wrap=btn.closest('.mb-font'),input=wrap.querySelector('input[type=hidden]'),head=btn.dataset.target==='.mb-type-h';
 const sample=head?'The long view':'Morning light and room to breathe.';
 loadFontBatch(GOOGLE_FONTS,sample+'Use from Google Fonts');
 const panel=document.createElement('div');panel.className='mb-fontlist';
 panel.innerHTML=`<input type="search" class="mb-fontsearch" placeholder="Search Google fonts" aria-label="Search fonts"><div class="mb-fontopts" role="listbox"></div>`;
 document.body.appendChild(panel);panel.dataset.for=input.name;
 // Fixed to the button, so the brand kit's rounded card can't clip it.
 const place=()=>{const r=btn.getBoundingClientRect(),below=window.innerHeight-r.bottom;panel.style.left=r.left+'px';panel.style.width=r.width+'px';
  if(below<300&&r.top>below){panel.style.top='';panel.style.bottom=(window.innerHeight-r.top+6)+'px'}else{panel.style.bottom='';panel.style.top=(r.bottom+6)+'px'}};
 place();panel._place=place;
 const opts=panel.querySelector('.mb-fontopts'),search=panel.querySelector('.mb-fontsearch');
 const draw=()=>{
  const q=search.value.trim().toLowerCase();
  const list=GOOGLE_FONTS.filter(f=>!q||f.toLowerCase().includes(q));
  opts.innerHTML=list.map(f=>`<button type="button" role="option" class="mb-fontopt${f===input.value?' on':''}" data-font="${esc(f)}" style="font-family:'${esc(f)}',${head?'serif':'sans-serif'}"><b>${esc(f)}</b><span>${esc(sample)}</span></button>`).join('')+
   (q&&!list.length?`<button type="button" class="mb-fontopt use" data-font="${esc(search.value.trim())}"><b>Use “${esc(search.value.trim())}” from Google Fonts</b><span>Any font on fonts.google.com works</span></button>`:'')+
   (!list.length&&!q?'<p class="fine">No fonts.</p>':'');
 };
 draw();search.addEventListener('input',draw);
 opts.addEventListener('click',e=>{const o=e.target.closest('.mb-fontopt');if(!o)return;const f=o.dataset.font;input.value=f;loadGoogleFont(f);
  btn.querySelector('b').textContent=f;btn.style.fontFamily="'"+f.replace(/'/g,'')+"',"+(head?'serif':'sans-serif');
  const prev=btn.form&&btn.form.querySelector(btn.dataset.target);if(prev)prev.style.fontFamily=btn.style.fontFamily;
  brandMarkDirty();closeFontPicker();});
 setTimeout(()=>{search.focus();opts.querySelector('.on')?.scrollIntoView({block:'nearest'})},0);
}
function closeFontPicker(){document.querySelectorAll('.mb-fontlist').forEach(p=>p.remove())}
document.addEventListener('click',e=>{if(!e.target.closest('.mb-fontlist')&&!e.target.closest('.mb-fontpick'))closeFontPicker()});
document.addEventListener('keydown',e=>{if(e.key==='Escape')closeFontPicker()});
window.addEventListener('scroll',()=>document.querySelectorAll('.mb-fontlist').forEach(p=>p._place&&p._place()),true);window.addEventListener('resize',closeFontPicker);
function brandMarkDirty(){window.brandDirty=true;const u=document.querySelector('.mb-unsaved');if(u)u.hidden=false}
// Research again rebuilds the kit from the agent's Facebook Page and website. What they typed is
// kept; Meta's facts only fill empty fields (brandFromPage).
function brandResearchAgain(btn){
 if(window.RM&&RM.brandFromMeta&&(state.metaConnected||(state.connected&&state.connected.meta)))return brandFromPage(btn);
 toast('Resmara is researching your brand again. This takes a minute.');
}
// Leaving My Brand with unsaved changes asks first. Returns true when it stopped the move.
let brandAfterSave=null;
function brandLeaveGuard(go){
 if(!window.brandDirty||!document.querySelector('form.mb'))return false;
 show(`<span class="eyebrow">MY BRAND</span><h2>Save your changes before you leave?</h2><p>You changed your brand kit but haven’t saved it. New campaigns only use what’s saved.</p><div class="modal-actions"><button type="button" class="nc-cancel" onclick="window.brandDirty=false;modal.close();brandPendingGo()">Leave without saving</button><button type="button" class="campaign-primary" onclick="modal.close();brandSaveThenGo()">Save changes</button></div>`);
 brandLeaveGuard.go=go;return true;
}
function brandPendingGo(){const go=brandLeaveGuard.go;brandLeaveGuard.go=null;if(go)go()}
function brandSaveThenGo(){const f=document.querySelector('form.mb');if(!f)return brandPendingGo();brandAfterSave=brandLeaveGuard.go;brandLeaveGuard.go=null;f.requestSubmit()}
window.addEventListener('beforeunload',e=>{if(window.brandDirty&&document.querySelector('form.mb')){e.preventDefault();e.returnValue=''}});
// Brand Engine section 4: the kit is built from the Page the agent connected. Meta's facts fill
// only the fields that are empty - the agent's own words are never overwritten - and the model's
// suggestions are shown for a yes/no, not applied silently.
async function brandFromPage(btn){
 if(!window.RM||!RM.brandFromMeta){toast('Sign in first.');return}
 if(!state.metaConnected&&!(state.connected&&state.connected.meta)){toast('Connect Facebook first - Resmara reads your Page from that connection.');return}
 if(btn){btn.disabled=true;btn.textContent='Reading your Page…'}
 try{
  const kit=await RM.brandFromMeta();
  const f=kit.facts||{},p=kit.proposed||{};
  state.brand={...(state.brand||{})};
  const fill=(k,v)=>{if(v&&!state.brand[k])state.brand[k]=v};
  fill('company',f.name);fill('website',f.website);fill('phone',f.phone);
  if(f.address)fill('market',f.address);
  if(f.logo_url&&!state.brandMedia)state.brandMedia={...(state.brandMedia||{}),logo:f.logo_url};
  const suggested=[];
  if(p.colors&&p.colors.length){suggested.push('Colours: '+p.colors.join(', '));fill('colours',p.colors.join(', '))}
  if(p.voice){suggested.push('Voice: '+p.voice);fill('voice',p.voice)}
  if(p.font)suggested.push('Type: '+p.font);
  if(p.tagline)suggested.push('Tagline: '+p.tagline);
  persist();myBrand();
  show(`<span class="eyebrow">FROM YOUR FACEBOOK PAGE</span><h2>Resmara read your Page.</h2>
   <p>These are Meta's own facts, now filled in below. Anything you had already typed was left alone.</p>
   <p class="fine">${esc(f.name||'Your Page')}${f.phone?' · '+esc(f.phone):''}${f.website?' · '+esc(f.website):''}</p>
   ${suggested.length?`<p class="notice">Suggestions to look over, not applied: ${esc(suggested.join(' · '))}</p>`:''}
   <p class="fine">Nothing is saved as your brand until you press Save my brand.</p>
   <div class="modal-actions"><button onclick="modal.close();document.querySelector('.mb')?.scrollIntoView({block:'start'})">Review and save</button></div>`);
 }catch(e){toast((e&&e.message)||'Could not read your Page. Connect Facebook and try again.')}
 finally{if(btn){btn.disabled=false;btn.textContent='Build from my Facebook Page'}}
}
function brandColoursSync(form){const v=[...form.querySelectorAll('.mb-sw input')].map(i=>i.value.toUpperCase()).join(', ');form.elements.colours.value=v}
function brandProfileForm(onboarding){
 const b=campaignBrandProfile();
 const text=(name,label,value,required=false,mode='text')=>`<label class="field">${label}<input name="${name}" inputmode="${mode}" value="${esc(value)}" ${required?'required':''}></label>`;
 if(onboarding)return `<form onsubmit="saveBrandBasics(event,this)"><div class="brand-fields">${text('agent','Agent name',b.agent,true)}${text('license','Agent license number',b.license,true)}${text('website','Personal, team or brokerage website',b.website,true,'url')}</div><p class="fine">Use the website that best represents the brand you want on your listings.</p><p class="fine" data-brand-error role="alert"></p><div class="modal-actions"><button class="campaign-primary">Save and continue</button></div></form>`;
 const suggestion=b.suggestion||{};
 const asset=(kind,label)=>{const current=state.brandMedia?.[b[kind+'Id']];return `<div class="brand-upload"><label class="field">${label} (optional)<input name="${kind}" type="file" accept="image/png,image/jpeg,image/webp"></label>${current?`<img src="${esc(current)}" alt="Saved ${label.toLowerCase()}"><label class="brand-remove"><input type="checkbox" name="remove_${kind}"> Remove saved image</label>`:''}</div>`};
 return `<form onsubmit="saveBrandProfile(event,this,${onboarding})">${b.suggestion?'<p class="notice checkout-notice">Website research draft. Review the suggested details below and save to use them in future campaigns.</p>':''}<div class="brand-fields">${text('agent','Agent name',b.agent,true)}${text('company','Brokerage',b.brokerage||suggestion.brokerage)}${text('license','Agent license number',b.license)}${text('website','Website',b.website,true,'url')}${text('market','Markets you serve',b.market||suggestion.market)}${text('colours','Brand colours',b.colours||b.colour||suggestion.colours)}${text('brandLink','Public social or brand guide URL (optional)',b.brandLink,false,'url')}<label class="field">Social voice and style<textarea name="voice" rows="2" placeholder="Warm, direct, neighborhood-focused">${esc(b.voice||suggestion.voice)}</textarea></label>${asset('logo','Logo')}${asset('headshot','Headshot')}</div><p class="fine">PNG, JPEG, or WebP, up to 500 KB per image. Your details are saved to your account; a logo or headshot stays in this browser.</p><p class="fine" data-brand-error role="alert"></p><div class="modal-actions"><button class="campaign-primary">${onboarding?'Save brand and continue':'Save My Brand'}</button></div></form>`;
}
// The profile also lives on the account, so clearing this browser or signing in on another
// machine does not lose what the customer typed. Images stay in the browser's own copy.
function pushBrandToAccount(brand,name,company){
 if(!window.RM||!RM.saveBrandProfile||!RM.isLoggedIn())return Promise.resolve(false);
 const payload={...(brand||{})};
 if(name&&!payload.agent)payload.agent=name;
 // The brokerage is held as state.company in this app but belongs to the profile: without
 // it a restored profile has no brokerage line on the creative.
 if(company&&!payload.brokerage)payload.brokerage=company;
 return RM.saveBrandProfile(payload).then(()=>true).catch(()=>false);
}
function saveBrandBasics(event,form){
 event.preventDefault();
 const fields=form.elements,error=form.querySelector('[data-brand-error]');
 const name=fields.agent.value.trim(),license=fields.license.value.trim(),website=normalizeWebLink(fields.website.value);
 if(!name||!license||!website){error.textContent='Enter your name, license number and a valid website.';return}
 const brand={...state.brand,license,website};
 if(website!==state.brand?.website)delete brand.suggestion;
 const next={...state,name,brand};
 try{localStorage.setItem('resmara',JSON.stringify(next))}catch{error.textContent='This browser couldn’t save your brand.';return}
 state=next;onboard(1);
 pushBrandToAccount(brand,name);
 draftWebsiteBrand(next,name,website);
}
// Brand suggestions are drafted by the campaign engine when a campaign is built (the
// boost's brand profile), so there is nothing to fetch here. My Brand stays manual.
async function draftWebsiteBrand(){return}
function readBrandImage(file){
 return new Promise((resolve,reject)=>{
  if(!['image/png','image/jpeg','image/webp'].includes(file.type)||file.size>500000){reject(new Error('Choose a PNG, JPEG, or WebP image under 500 KB.'));return}
  const reader=new FileReader();reader.onload=()=>resolve(reader.result);reader.onerror=()=>reject(new Error('That image couldn’t be read. Try another file.'));reader.readAsDataURL(file);
 });
}
async function saveBrandProfile(event,form,onboarding){
 event.preventDefault();const account=state,fields=form.elements,button=form.querySelector('button:not([type=button])'),error=form.querySelector('[data-brand-error]');
 if(button.disabled)return;button.disabled=true;error.textContent='';
 try{
  const website=normalizeWebLink(fields.website.value),brandLink=normalizeWebLink(fields.brandLink.value);
  if(!website||brandLink===null)throw new Error('Enter a valid website or public profile link, such as www.bap.digital.');
  const name=fields.agent.value.trim(),company=fields.company.value.trim(),market=fields.market.value.trim();
  if(!name)throw new Error('Enter your agent name.');
  const brand={...state.brand,website,brandLink,market,license:fields.license.value.trim(),colours:fields.colours.value.trim(),voice:fields.voice.value.trim()};
  if(fields.fontHead&&fields.fontBody)brand.fonts=[fields.fontHead.value.trim()||'Playfair Display',fields.fontBody.value.trim()||'Jost'];
  if(fields.theme)brand.theme=fields.theme.value;
  if(fields.colours&&form.querySelector('.mb-sw'))brand.palette=[...form.querySelectorAll('.mb-sw')].map(l=>[l.querySelector('b').textContent,l.querySelector('input').value.toUpperCase()]);
  delete brand.suggestion;
  brand.colour=brand.colours;
  const brandMedia={...state.brandMedia};
  for(const kind of ['logo','headshot']){
   const file=fields[kind].files[0];
   if(file){const image=await readBrandImage(file);const id=kind+'-'+Date.now()+'-'+Math.random().toString(36).slice(2);brandMedia[id]=image;brand[kind+'Id']=id;}
   else if(fields['remove_'+kind]?.checked)delete brand[kind+'Id'];
  }
  if(state!==account||!form.isConnected)return;
  const next={...state,name,company,brand,brandMedia};
  try{localStorage.setItem('resmara',JSON.stringify(next))}catch{throw new Error('This browser couldn’t save the profile. Try smaller images or use the Chrome preview.')}
  Object.assign(state,next);
  const synced=await pushBrandToAccount(brand,name,company);
  window.brandDirty=false;
  if(onboarding)onboard(1);else{const go=brandAfterSave;brandAfterSave=null;myBrand();toast(synced?'Brand saved. New campaigns use it.':'Brand saved in this browser — sign in to keep it on your account.');if(go)go()}
 }catch(e){brandAfterSave=null;error.textContent=e.message}finally{button.disabled=false}
}
function runMetaAudit(scenario){
 show(`<span class="eyebrow">FIRST CAMPAIGN · STEP 3 OF 3</span><h2>Resmara is checking your setup.</h2><div class="audit-track"><span class="robot-avatar" aria-hidden="true"></span></div><p role="status">Checking business access, Page permissions and ad account readiness…</p><p class="fine">Simulated check. No access to your Meta account.</p>`);
 const status=modal.querySelector('[role="status"]');
 setTimeout(()=>{if(!modal.open||!status?.isConnected)return;state.metaAudit={status:scenario==='ready'?'ready':'blocked',checkedAt:new Date().toISOString()};state.connected=state.metaAudit.status==='ready';persist();showMetaResult()},1800)
}
function showMetaResult(){
 const ready=state.metaAudit?.status==='ready';
 if(ready){
 show(`<span class="robot-avatar" aria-hidden="true"></span><span class="eyebrow">DEMO CHECK COMPLETE</span><h2>Congratulations, you’re ready to run your first campaign.</h2><p>In this scenario your Business Portfolio, Page access and ad account passed the check.</p><div class="check">1. Add your listing and media, then start the campaign for $49.</div><div class="check">2. Review the branded draft and approve it.</div><div class="check">3. Approve your campaign when you’re ready to launch.</div><div class="modal-actions"><button class="alt" onclick="finishWorkspaceTour()">Skip for now</button><button onclick="workspaceTour(0)">Show me my dashboard</button></div>`);return
 }
 show(`<span class="eyebrow">DEMO CHECK · ACTION NEEDED</span><h2>Your ad account needs attention.</h2><p>You can still build a draft. Launch stays on hold until the account passes the check.</p><div class="check">✓ Business Portfolio and Facebook Page found in this scenario.</div><div class="notice"><strong>Ad account access needs to be granted.</strong><br>In Meta Business Settings, select the ad account and confirm your profile has permission to manage campaigns. Then reconnect and check again.</div><p>Want a hand? Try booking a setup session with Adam. No meeting or invitation will be created.</p><div class="modal-actions"><button class="alt" onclick="onboard(1)">Reconnect and recheck</button><button class="alt" onclick="mockHelpBooking()">Try booking help</button><button onclick="newCampaign()">Build a draft anyway</button></div>`);
}
function campaignSampleCaption(c,i){
 const agent=state.company||state.name||'your local real estate team';
 return (i===0?'Take a closer look at ':i===1?'See what’s on offer at ':homePostTitles[(i-2)%14]+' · ')+c.address+'. '+(state.brand?.market?'Explore the listing in '+state.brand.market+' and contact '+agent+' to arrange a viewing.':'Explore the listing and contact '+agent+' to arrange a viewing.')
}
function launchOrder(){
 const live=reviewCampaignBoostId()!=null&&!!(window.RM&&RM.isLoggedIn());
 if(!live&&state.metaAudit?.status!=='ready'){show(`<h2>Check your Meta setup first.</h2><p>Your draft is saved. Complete a readiness check before proceeding to launch.</p><button onclick="onboard(1)">Check Meta setup</button>`);return}
 if(!activeReview()?.approved)return;
 if(live){
  show(`<span class="eyebrow">LAUNCH PREVIEW</span><h2>Ready to launch your property?</h2><div class="check">One property · 14-day campaign · Approved</div><p>Ad spend is billed to your own connected ad account. Nothing further is charged at launch. The campaign is created paused, and you activate it in Meta Ads Manager.</p><div class="modal-actions"><button class="alt" onclick="modal.close()">Back to your campaign</button><button class="campaign-primary" onclick="launchCampaignViaApi()">Launch on Meta</button></div>`);
  return;
 }
 show(`<span class="eyebrow">LAUNCH PREVIEW</span><h2>Ready to launch your property?</h2><div class="check">One property · 14-day campaign · Approved</div><p>Meta ad spend is separate. Nothing further is charged at launch. Publishing is not connected in this demo.</p><div class="modal-actions"><button class="alt" onclick="modal.close()">Back to your campaign</button>${reviewCampaignBoostId()!=null?'<button class="campaign-primary" onclick="launchCampaignViaApi()">Launch on Meta</button>':''}</div>`);
}

function mockHelpBooking(){
 show(`<span class="eyebrow">DEMO HELP BOOKING</span><h2>Meta setup with Adam</h2><p>We’ll review the ad account permissions and help you reconnect. These are example appointments.</p><form onsubmit="event.preventDefault();confirmMockHelp(this.slot.value)"><label class="field">Choose an example time<select name="slot"><option>Tuesday · 10:00 AM Pacific</option><option>Thursday · 2:00 PM Pacific</option></select></label><div class="modal-actions"><button type="button" class="alt" onclick="showMetaResult()">Back</button><button>Confirm demo booking</button></div></form>`);
}
function confirmMockHelp(slot){
 state.mockHelpSlot=slot;persist();
 show(`<span class="eyebrow">DEMO BOOKING CONFIRMED</span><h2>Your setup session preview</h2><div class="check">${esc(slot)} · Adam · Meta setup</div><p>No real meeting was booked. After the permissions are fixed, return here to reconnect and check again.</p><div class="modal-actions"><button class="alt" onclick="modal.close()">Close</button><button onclick="onboard(1)">Reconnect and recheck</button></div>`);
}

function pricing(){
 if(typeof stopResmaraGuide==='function')stopResmaraGuide();
 location.hash='pricing';document.title='Pricing — Resmara';
 app.innerHTML=`<div class="marketing-home">${siteNav('pricing')}<main><section class="home-section package-page"><div><span class="home-kicker">$49 PER CAMPAIGN</span><h1>One listing.<br><span>One campaign.</span><br>Forty-nine dollars.</h1><p>A 14-day branded campaign for one property: the creative, the calendar, the publishing and the day 7 and day 14 seller reports.</p><p>No subscription, no packs, nothing to top up. You pay the $49 when the campaign is ready to build, through Stripe Checkout. Meta ad spend is separate and goes to your own ad account.</p><p class="fine">Preparing a campaign — the scope, the captions, the calendar — costs nothing. You only pay to build it.</p></div><div class="home-price-detail"><h3>What the $49 buys</h3><ul><li>A 14-day social campaign for that listing</li><li>Caption and photo pairings from your own gallery</li><li>Digital ad creative and campaign setup</li><li>Your calendar, review and approval</li><li>Scheduled social publishing</li><li>A website for the home that tracks its leads</li><li>Day 7 and day 14 seller reports</li></ul><button class="home-primary" onclick="newCampaign()">Start a campaign</button></div></section></main><footer class="home-footer">${logo}<span>Your expertise. Superpowered.</span>${footerLinks()}</footer></div>`;
 window.scrollTo(0,0);
}
let workspaceTourCleanup;
function workspaceTour(step=0){
 workspaceTourCleanup?.();
 if(modal.open)modal.close();
 const steps=[
  ['My Campaigns','This is where all your properties live. Open any campaign to see its scope, calendar and seller reports.','.welcome h1','campaigns'],
  ['Add a campaign','Use this button to add the property address, listing link and media. The $49 is charged only when the campaign is built.','.welcome [onclick="newCampaign()"]','campaigns'],
  ['Property Scope','Resmara fills in the property brief. Check the facts and pick a go-live date. Approving the scope starts the campaign build.','.campaign-scope summary','example'],
  ['Campaign Calendar','The posts and ads appear here when the build is done. Open any item to edit it, then approve the calendar.','.review-calendar summary','example'],
  ['Approve the campaign','Once the scope and calendar are approved, you can approve the full campaign here.','.review-approval h2','example'],
  ['Billing','Every campaign purchase and its status lives here. One campaign is $49.','.welcome h1','credits']
 ];
 const [title,description,selector,page]=steps[step];
 dashboard(page==='example'?'campaigns':page);
 if(page==='example')details(state.campaigns.length);
 const target=document.querySelector('#content '+selector);
 if(!target)return;
 target.classList.add('workspace-tour-target');
 const tip=document.createElement('section');
 tip.className='workspace-tour-tip';
 tip.setAttribute('aria-label','Dashboard tour');
 tip.innerHTML=`<span class="eyebrow">DASHBOARD TOUR · ${step+1} OF ${steps.length}</span><h2>${title}</h2><p>${description}</p><div class="modal-actions"><button class="alt" onclick="${step?'workspaceTour('+(step-1)+')':'finishWorkspaceTour()'}">${step?'Back':'Skip tour'}</button><button class="campaign-primary" onclick="${step===steps.length-1?'finishWorkspaceTour()':'workspaceTour('+(step+1)+')'}">${step===steps.length-1?'Finish tour ✓':'Next'}</button></div>`;
 document.body.append(tip);
 target.scrollIntoView({block:'center'});
 function place(){
  const rect=target.getBoundingClientRect();
  const left=Math.max(12,Math.min(rect.left,innerWidth-tip.offsetWidth-12));
  const below=rect.bottom+12;
  const top=below+tip.offsetHeight<=innerHeight-12?below:Math.max(12,rect.top-tip.offsetHeight-12);
  tip.style.left=left+'px';tip.style.top=top+'px';
 }
 function onKey(event){if(event.key==='Escape')finishWorkspaceTour()}
 const observer=new MutationObserver(()=>{if(!target.isConnected)workspaceTourCleanup?.()});
 observer.observe(app,{childList:true,subtree:true});
 addEventListener('scroll',place,true);addEventListener('resize',place);addEventListener('keydown',onKey);
 workspaceTourCleanup=()=>{
  observer.disconnect();target.classList.remove('workspace-tour-target');tip.remove();
  removeEventListener('scroll',place,true);removeEventListener('resize',place);removeEventListener('keydown',onKey);
  workspaceTourCleanup=null;
 };
 place();tip.querySelector('.campaign-primary').focus({preventScroll:true});
}
function finishWorkspaceTour(){workspaceTourCleanup?.();dashboard()}

// Scrollable homepage boxes: a fade and a pill at the bottom until the visitor scrolls.
function scrollHint(text){return `<div class="scroll-hint" aria-hidden="true"><span>${text} ↓</span></div>`}
function armScrollHint(el){if(!el||el.dataset.hintArmed)return;el.dataset.hintArmed='1';el.classList.add('has-hint');el.addEventListener('scroll',()=>el.classList.toggle('scrolled',el.scrollTop>30),{passive:true})}
document.addEventListener('DOMContentLoaded',()=>{});
new MutationObserver(()=>{document.querySelectorAll('#home-brand .mb-preview,#home-report-preview').forEach(armScrollHint)}).observe(document.documentElement,{childList:true,subtree:true});

// Light / dark for the agent dashboard. Each person's choice is remembered on their device.
function themeToggle(){const dark=document.documentElement.classList.contains('dark');return `<button class="theme-toggle" role="switch" aria-checked="${dark}" onclick="toggleTheme()"><span>Dark mode</span><i></i></button>`}
function toggleTheme(){const dark=!document.documentElement.classList.contains('dark');document.documentElement.classList.toggle('dark',dark);try{localStorage.setItem('resmara_theme',dark?'dark':'light')}catch{}const b=document.querySelector('.theme-toggle');if(b){b.setAttribute('aria-checked',String(dark));0}}

// ---- Setup guides: how to get Facebook, Instagram and the ad account ready for Resmara ---------
// One page, one short guide per piece. The onboarding screens and the red box link straight to the
// guide they need (setupGuides('instagram') opens that one).
const SETUP_GUIDES = [
 { id: 'facebook', video: true, title: 'Create a Facebook account', need: 'Required', time: '5 minutes',
   why: 'Every Facebook business Page is run from a personal account. Your personal posts and details never show on your Page.',
   steps: ['Go to facebook.com and click Create new account.', 'Use your real name and an email or phone number you check.', 'Confirm the code Facebook sends you.'],
   link: ['Open Facebook', 'https://www.facebook.com/'] },
 { id: 'page', video: true, title: 'Create your Facebook business Page', need: 'Required', time: '10 minutes',
   why: 'Resmara posts your listings to a business Page, never to your personal profile.',
   steps: ['On a computer, log in to Facebook and open Pages in the left menu, then Create Page.', 'Use your business name, for example “Jamie Carter, Realtor”, and pick the Real Estate Agent category.', 'Add a headshot or logo, a cover photo, and your website, phone and email.'],
   link: ['Create a Page', 'https://www.facebook.com/pages/create'] },
 { id: 'admin', video: true, title: 'Make sure you have full control of your Page', need: 'Required', time: '2 minutes',
   why: 'Resmara can only post to a Page you fully control. Pages made by a brokerage, an old assistant or a marketing company are often owned by someone else.',
   steps: ['On Facebook, switch into your Page.', 'Open Settings, then Page access.', 'Check your name is listed with full control. If it isn’t, ask whoever is listed to give you full control.'] },
 { id: 'instagram', video: true, title: 'Switch your Instagram to a business account', need: 'Recommended', time: '1 minute',
   why: 'Meta only lets apps like Resmara post to business (Professional) Instagram accounts. It’s free, and you keep all your posts and followers. Your account becomes public.',
   steps: ['In the Instagram app, go to your profile and open the menu.', 'Under For professionals, tap Account type and tools, then Switch to professional account.', 'Pick a category such as Real Estate Agent, choose Business and tap Next.'],
   note: 'No Instagram yet? Make one in the Instagram app first. Without Instagram, Resmara posts to your Facebook Page only.' },
 { id: 'link', video: true, title: 'Link your Instagram to your Facebook Page', need: 'Recommended', time: '2 minutes',
   why: 'Resmara finds your Instagram through your Facebook Page, so the two have to be linked.',
   steps: ['On Facebook, switch into your Page and open Settings.', 'Open Linked accounts, then Instagram, and click Connect account.', 'Log in to your Instagram and confirm. If it’s still a personal account, Facebook offers to switch it to business right here.'],
   note: 'An Instagram can be linked to one Page at a time. If it’s linked to an old Page, disconnect it there first.',
   link: ['Open linked accounts', 'https://www.facebook.com/settings/?tab=linked_instagram'] },
 { id: 'ads', video: true, title: 'Set up your ad account and payment method', need: 'Recommended', time: '5 minutes',
   why: 'Your listing ad runs from your own Meta ad account. Meta bills your ad budget to your card directly. Resmara never charges or keeps any of it.',
   steps: ['Every Facebook account already comes with an ad account. Go to adsmanager.facebook.com to open yours.', 'In the left menu, open Billing & payments, then Payment settings, and click Add payment method. Check your country and currency are right first: they can’t be changed later.', 'Enter your card and click Save. Meta may place a small temporary charge to check the card. That’s normal.'],
   note: 'Without a card on your ad account your posts still go out. Only the listing ad is off.',
   link: ['Open Ads Manager', 'https://adsmanager.facebook.com/'] },
 { id: 'connect', video: true, title: 'Connect it all to Resmara', need: 'Last step', time: '1 minute',
   why: 'Logging in to Resmara with Facebook connects your Page, Instagram and ad account. Your Accounts page shows whether each one is ready.',
   steps: ['Log in to Resmara with Facebook. That’s what connects you.', 'Open Accounts to see your Facebook business Page, business Instagram and ad account, each marked ready or not set up yet. Anything not set up has a guide above, or book a session and we’ll do it with you.', 'If you ever see “We can’t access your accounts” (say, after changing your Facebook password), click Sign in again and log in with Facebook.'] }
];
function setupGuides(open) {
 if (typeof stopResmaraGuide === 'function') stopResmaraGuide();
 if (typeof modal !== 'undefined' && modal.open) modal.close();
 location.hash = 'setup-guides'; document.title = 'Setup — Resmara';
 const jump = id => `document.getElementById('sg-${id}').scrollIntoView({behavior:'smooth',block:'start'});return false`;
 // Each guide with a tutorial has a short whiteboard video at the top (static/video/setup/). Nothing loads until play.
 const video = g => g.video ? `<div class="sg-video"><video src="video/setup/setup-${g.id}.mp4" poster="video/setup/setup-${g.id}.jpg" playsinline preload="none" aria-label="Video: ${g.title}" onended="this.removeAttribute('controls');this.load();this.nextElementSibling.hidden=false"></video><button type="button" class="hpv-play" aria-label="Play the tutorial: ${g.title}" onclick="const v=this.previousElementSibling;this.hidden=true;v.controls=true;v.play()"><span></span></button></div>` : '';
 const card = (g, n) => `<li class="sg-card" id="sg-${g.id}"><span class="home-step-num">${n + 1}</span><small>${g.need.toUpperCase()} · ${g.time.toUpperCase()}</small><h3>${g.title}</h3>${video(g)}<p>${g.why}</p>
  <ol class="sg-steps">${g.steps.map(t => `<li>${t}</li>`).join('')}</ol>${g.note ? `<p class="sg-note">${g.note}</p>` : ''}${g.link ? `<a class="home-primary sg-btn" href="${g.link[1]}" target="_blank" rel="noopener">${g.link[0]}</a>` : ''}</li>`;
 app.innerHTML = `<div class="marketing-home">${siteNav('setup-guides')}<main>
  <section class="home-section sg-hero"><div class="home-section-heading"><div><span class="home-kicker">SETUP</span><h2>Set up once.<br><span>Resmara does the rest.</span></h2></div><p>Resmara posts, advertises and reports through your own Facebook Page, Instagram and Meta ad account. Get these three ready and your campaigns run in full from day one. Each step below takes a few minutes.</p></div>
   <ol class="home-steps sg-need">
    <li><span class="home-step-num">1</span><small>REQUIRED</small><h3>A Facebook business Page</h3><p>That you fully control. Resmara posts your listings here.</p><a href="#sg-page" onclick="${jump('page')}">See how</a></li>
    <li><span class="home-step-num">2</span><small>RECOMMENDED</small><h3>A business Instagram</h3><p>Linked to your Page. Without it, posts go to Facebook only.</p><a href="#sg-instagram" onclick="${jump('instagram')}">See how</a></li>
    <li><span class="home-step-num">3</span><small>RECOMMENDED</small><h3>A Meta ad account</h3><p>With a payment method. Without it, your posts run but your listing ad is off.</p><a href="#sg-ads" onclick="${jump('ads')}">See how</a></li>
   </ol></section>
  <section class="home-section sg-guides"><div class="home-section-heading"><div><span class="home-kicker">STEP BY STEP</span><h2>Seven quick steps.<br><span>About 25 minutes in all.</span></h2></div><p>Already have some of these? Skip to the ones you need. When you’re done, connect in your Resmara dashboard and it checks everything for you.</p></div>
   <ol class="sg-grid">${SETUP_GUIDES.map(card).join('')}</ol></section>
  <section class="home-finish"><span class="home-mini-robot" aria-hidden="true"></span><h2>Rather do it together?</h2><p>Book a free 30-minute setup call and one of our team will set it all up with you.</p><button type="button" class="home-primary" onclick="obBook(true)">Book a free setup call</button></section>
 </main><footer class="home-footer">${logo}<span>Your expertise. Superpowered.</span>${footerLinks()}</footer></div>`;
 const el = open && document.getElementById('sg-' + open);
 if (el) setTimeout(() => el.scrollIntoView({ block: 'start', behavior: 'smooth' }), 50); else window.scrollTo(0, 0);
}

// Section C on the homepage: the sample listing website, the same page agents get, read-only.
function homeSitePreview(){
 const box=document.querySelector('#home-site-view');if(!box||typeof listingSiteHTML!=='function')return;
 const c=examples.find(e=>e.address==='1248 Oakridge Drive')||{address:'1248 Oakridge Drive',area:'Austin, TX · $845,000',image:'sample/card-1.jpg'};
 box.innerHTML=`<div inert>${listingSiteHTML(c,0)}</div>${scrollHint('Scroll to see the whole website')}`;
 if(typeof loadListingFonts==='function'&&typeof listingSiteData==='function')loadListingFonts(listingSiteData(c).fonts||[]);
 armScrollHint(box);
}
