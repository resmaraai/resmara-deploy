function home(){
 if(window.stopResmaraGuide)stopResmaraGuide();
 location.hash='';document.title='Resmara — Your listing gets attention. Your clients get you.';
 app.innerHTML=`<div class="marketing-home">
 ${siteNav("home")}
 <main>
 <section class="home-hero">
  <div class="home-hero-copy"><h1>More eyes on<br> your listing.<br><span>More time for<br> your clients.</span></h1><p>Resmara takes hours of marketing off your plate. It learns your brand, turns every listing into 14 days of designed posts and digital ads, then launches them, tracks social engagement and leads, and reports on it all for you. While you sleep and work, it keeps your listing in front of the market, so you can spend your time with your clients. And every campaign makes your next one better.</p><div class="home-actions"><button class="home-primary" onclick="newCampaign()">Let’s get started</button><a href="#home-how" onclick="document.querySelector('#home-how').scrollIntoView({behavior:'smooth'});return false">See how it works</a></div></div>
  <div class="home-visual"><div class="home-hello"><b>Hi, I’m Resmara.</b><span>Your Real Estate Social Marketing, Analytics &amp; Reporting Assistant.</span></div>${homeWorld()}</div>
 </section>
 <section class="home-workload"><div class="home-section home-workload-inner"><div><span class="home-kicker">THE PROBLEM</span><h2>You have clients.<br><span>Not hours to<br>make content.</span></h2><p>A new listing has a short window to get noticed. Doing it properly means two weeks of posts, branded creative, ad setup, scheduling, watching the numbers and reporting back to your seller.</p><p>Most agents don’t have those hours. So the listing gets one “Just listed” post, and the momentum fades.</p></div><div class="home-problem-video"><video src="video/resmara-new-listing-30s.mp4" poster="video/resmara-new-listing-30s.jpg" playsinline preload="metadata" aria-label="Resmara in 30 seconds: from a new listing to a running campaign" onended="this.removeAttribute('controls');this.load();this.nextElementSibling.hidden=false"></video><button type="button" class="hpv-play" aria-label="Play the 30-second video" onclick="const v=this.previousElementSibling;this.hidden=true;v.controls=true;v.play()"><span></span></button></div></div></section>
 <section class="home-section home-how" id="home-how"><div class="home-section-heading"><div><span class="home-kicker">WHAT RESMARA DOES FOR YOU</span><h2>Learn. Link. Build.<br><span>Manage.</span></h2></div></div>
  <ol class="home-steps">
   <li><span class="home-step-num">1</span><small>ONCE</small><h3>It learns you</h3><p>Using AI, Resmara audits your business, your brand and your look and feel, and builds your brand kit for you. You just check it’s right.</p><a href="#home-brand" onclick="document.querySelector('#home-brand').scrollIntoView({behavior:'smooth'});return false">See a brand profile</a></li>
   <li class="home-step-you"><span class="home-step-num">2</span><small>YOU · 30 SECONDS</small><h3>You add your link</h3><p>Put in the link to your listing. Resmara checks it has everything it needs to go live. That’s your part.</p><a href="#home-link" onclick="document.querySelector('#home-link').scrollIntoView({behavior:'smooth'});return false">See how</a></li>
   <li><span class="home-step-num">3</span><small>MINUTES</small><h3>It builds the whole campaign</h3><p>It picks the best photos, writes one story about this home across 14 designed posts, and builds the ads. Change anything you like, or just hit go live.</p><a href="#home-campaign" onclick="document.querySelector('#home-campaign').scrollIntoView({behavior:'smooth'});return false">See a campaign</a></li>
   <li><span class="home-step-num">4</span><small>14 DAYS</small><h3>It launches, manages and reports</h3><p>Posts go out at the best times for your area, the ads run, buyer interest gets flagged for you, and you get day 7 and day 14 reports to share with your seller.</p><a href="#home-report" onclick="document.querySelector('#home-report').scrollIntoView({behavior:'smooth'});return false">See a report</a></li>
  </ol>
 </section>
 <section class="home-section home-samples" id="home-brand"><div class="home-section-heading"><div><span class="home-kicker">STEP 1 · IT LEARNS YOU</span><h2>Your brand.<br><span>Down to the details.</span></h2></div><p>You don’t have to do a thing. Through the power of AI, Resmara audits who you are: your business, your brand, your look and your feel. It builds a complete brand kit for you, and every post and ad is made from it, so your content is custom and unique to you. You just make sure it’s right.</p></div><div class="home-sample-layout"><div class="home-brand-profile mb mb-preview"><div inert>${brandKitSections({...SAMPLE_BRAND,demo:true,logo:'',headshot:''})}<div class="mb-foot"><div class="mb-status"><span>✓ Researched ${esc(SAMPLE_BRAND.researched||'')}</span></div></div></div>${scrollHint('Scroll to see the whole brand kit')}</div><div class="home-brand-creative"><div class="sample-tabs" role="tablist" aria-label="Branded creative previews"><button role="tab" id="tab-social" aria-selected="true" aria-controls="sample-output" onclick="sampleOutput('social')">Social post</button><button role="tab" id="tab-ad" aria-selected="false" aria-controls="sample-output" onclick="sampleOutput('ad')">Digital ad</button></div><div id="sample-output" role="tabpanel" aria-labelledby="tab-social"></div></div></div></section>
 <section class="home-workload home-link-band" id="home-link"><div class="home-section home-link"><div class="home-link-layout"><div><span class="home-kicker">STEP 2 · YOU ADD YOUR LINK</span><h2>One link.<br><span>That’s your part.</span></h2><p>Put the link to your listing into Resmara. It researches the home, audits everything in it and makes sure it has everything it needs to go live. If anything’s missing, it lets you know and gives you the option to add it yourself.</p></div>
<div class="home-link-demo" aria-hidden="true"><span class="eyebrow">NEW CAMPAIGN</span><b class="hl-title">MLS public listing link</b><div class="hl-input">https://share.mlslink.com/listing/4821-maple-ridge-court</div><div class="nc-msg wait nc-walk"><b>Resmara is checking your link…</b><div class="nc-steps"><ul class="link-checks"><li class="ok">Link opened</li><li class="ok">Found the home’s details</li><li class="ok">Found 24 photos</li></ul></div></div><div class="nc-msg ok"><span class="robot-avatar"></span><div><b>Green light.</b> We have the home’s details and 24 photos. You’re ready to build.</div></div></div></div></div></section>
 <section class="home-section home-campaign" id="home-campaign"><div class="home-section-heading"><div><span class="home-ab">A</span><span class="home-kicker">STEP 3 · IT BUILDS THE WHOLE CAMPAIGN</span><h2>Two weeks.<br><span>One powerful launch.</span></h2></div><p>Resmara goes to work building your campaign strategy over 14 days: posts that tell one story about this home, plus digital ads, all in your brand. You set the go-live date and we launch it. Every post is scheduled for when your local audience is most likely to be online.</p></div>
 <div class="home-calendar home-calendar-preview"><div class="home-calendar-head"><div><span>YOUR CAMPAIGN, BEFORE IT GOES LIVE</span><h3>See what’s going live.<br>And exactly when.</h3></div><div class="home-calendar-legend"><span><i class="lg-time"></i>Best time to post, picked for your area</span><span><i class="lg-ad"></i>Your listing ad, running all 14 days</span></div></div><div class="home-calendar-preview-body"><div class="flex home-preview-month"><strong id="home-month-title"></strong><span class="fine">Sample schedule · Pacific time</span></div><div class="review-month-grid" aria-label="Campaign calendar preview"><div class="review-month-weekdays">${['Sun','Mon','Tue','Wed','Thu','Fri','Sat'].map(d=>'<span>'+d+'</span>').join('')}</div><div id="home-month-grid"></div></div></div><div id="home-calendar-selection" hidden></div><p id="home-calendar-range" class="home-calendar-caption" hidden></p></div>
 <div class="home-control-row"><div><b>Change anything.</b><span>Open a post to swap the photo, rewrite the headline or caption, or move it to another day.</span></div><div><b>Or don’t.</b><span>Hit <em>Go live</em> and it runs exactly as built. Your choice, every campaign.</span></div><div><b>Pause in one click.</b><span>Went pending? Pause everything instantly, and turn it back on if it falls through.</span></div></div>
 <div class="home-leads-layout home-leads-in-campaign"><div><span class="home-ab">B</span><span class="home-kicker">WHILE IT RUNS · BUYER INTEREST</span><h3 class="home-leads-title">It tracks buyer interest. And tells you.</h3><p>While your campaign runs, Resmara watches every comment on your Facebook and Instagram posts and your ad. When one sounds like real interest, like a question about the price, a showing or “is it still available?”, it tags it as a lead.</p><ul class="home-leads-points"><li><b>On your campaign.</b> A “new leads” badge, with each person’s name, what they said and which post.</li><li><b>In your inbox.</b> An email the moment it happens, with a button to reply.</li><li><b>Your call.</b> Mark leads handled, remove ones that aren’t, or add your own.</li></ul></div>
<div class="lead-mail home-lead-mail" aria-label="Sample lead alert email"><div class="lead-mail-meta"><div><b>From</b> Resmara &lt;support@resmara.com&gt;</div><div><b>Subject</b> New lead on The Oakridge House: Sarah Mitchell</div></div><div class="lead-mail-body"><div class="lead-mail-top"><img class="pr-logo" src="resmara-logo-white.png" alt="Resmara"><span>NEW SOCIAL LEAD</span></div><h3>Sarah Mitchell is interested in The Oakridge House.</h3><div class="lead-mail-quote"><p>“Is this still available? We’d love to see it this weekend.”</p><small>Instagram · on “Where summer actually happens”</small></div><p>Reply while they’re still looking. Resmara spotted this comment and thinks it shows real interest in the home.</p><div class="lead-mail-btns"><span class="lm-primary">Reply on Instagram</span><span class="lm-secondary">See all leads in Resmara</span></div></div></div></div>
 </section>
 <section class="home-results" id="home-report"><div class="home-section home-results-layout"><div><span class="home-kicker">STEP 4 · CLEAR RESULTS. BETTER CONVERSATIONS.</span><h2>Go back to your<br><span>seller with confidence.</span></h2><p>“How’s the marketing going?” now has a real answer. On day 7 and day 14 you get clear reports that are easy to understand, for you and your client: how many people saw the home, which posts did best and how many people clicked through to the listing.</p><div class="home-report-moments"><div><span>07</span><div><h3>A confident check-in.</h3><p>Reach, engagement and listing clicks so far, plus your top posts.</p></div></div><div><span>14</span><div><h3>A clear way forward.</h3><p>The whole campaign in one place, and the option to run a fresh round if the home is still on the market.</p></div></div></div></div><div class="home-seller-preview"><div class="home-report-switch" role="tablist" aria-label="Seller report previews"><button role="tab" id="seller-tab-7" aria-selected="true" aria-controls="home-report-preview" onclick="homeSellerReport(7)">Day 7</button><button role="tab" id="seller-tab-14" aria-selected="false" aria-controls="home-report-preview" onclick="homeSellerReport(14)">Day 14</button></div><div id="home-report-preview" role="tabpanel" aria-labelledby="seller-tab-7"></div></div></div></section>
 <section class="home-learn"><div class="home-section home-learn-inner"><div><span class="home-kicker">WHAT MAKES RESMARA DIFFERENT</span><h2>The secret?<br><span>Every campaign makes the next one smarter.</span></h2><p>Resmara doesn’t start from scratch each time. It keeps learning what you like and what your audience responds to, so every listing you launch looks more like you and works harder than the last.</p><div class="home-learn-points"><div><span>✎</span><div><b>It learns from your edits</b><small>Shorten a caption or swap a twilight shot for daytime, and it remembers for next time.</small></div></div><div><span>↗</span><div><b>It learns from what performs</b><small>The posts and ads that get the most reach, saves and clicks shape what it makes next.</small></div></div><div><span>◷</span><div><b>It posts when your people are online</b><small>Posting times are tuned to when your audience is most active, and adjusted as the numbers come in.</small></div></div></div></div>
  <div class="home-learned-card"><div class="home-learned-head"><span class="robot-avatar" aria-hidden="true"></span><div><b>What Resmara learned about you</b><small>After 3 campaigns · you can change any of these</small></div></div><ul><li><i>✎</i>Keeps captions under 40 words</li><li><i>✎</i>Prefers daytime exteriors to twilight</li><li><i>✎</i>No emoji in captions</li><li><i>↗</i>Question posts get 2× the comments on your page</li><li><i>↗</i>Kitchen and pool photos lead to the most listing clicks</li><li><i>◷</i>Your audience is most active around 7:40 AM and 6:15 PM</li></ul><div class="home-learned-growth"><span>LISTING CLICKS PER CAMPAIGN</span><div><i style="--h:46%"><b>1st</b></i><i style="--h:68%"><b>2nd</b></i><i style="--h:92%"><b>3rd</b></i></div><small>Illustrative example</small></div></div></div></section>
 <section class="home-section home-setup"><div><span class="home-kicker">BEFORE YOUR FIRST CAMPAIGN</span><h2>Get your accounts ready.<br><span>Resmara does the rest.</span></h2><p>Resmara posts and advertises through your own Facebook Page, Instagram and Meta ad account. Our setup guides walk you through each one in a few minutes.</p></div><div class="home-setup-side"><ul class="sg-check"><li><b>Facebook business Page</b> <span class="sg-tag req">Required</span></li><li><b>Business Instagram</b> <span class="sg-tag">Recommended</span></li><li><b>Meta ad account</b> <span class="sg-tag">Recommended</span></li></ul><button type="button" class="home-primary" onclick="setupGuides()">See the setup guides</button></div></section><section class="home-section home-price" id="home-pricing"><div><span class="home-kicker">DONE FOR YOU. ON YOUR TERMS.</span><h2>All that.<br>$49 per listing.<br><span>No subscription.</span></h2><p>One listing, one 14-day campaign, one price. You pay when the campaign is built, and nothing renews. Want another two weeks on the same home? A fresh round of all-new posts and a new ad is $39.</p></div><div class="home-price-detail"><h3>Every listing launch includes</h3><ul><li>Your brand profile, built and kept up to date</li><li>14 designed posts with captions and hashtags</li><li>A digital ad, set up and run for you</li><li>Posting at the best times for your area</li><li>Go live, review first, or pause anytime</li><li>Day 7 and day 14 seller reports</li></ul><p>You choose the ad budget ($50 suggested). Ad spend is paid to Meta from your own ad account, separate from your Resmara fee.</p><button class="home-primary" onclick="newCampaign()">Launch your next listing</button></div></section>
 <section class="home-finish"><span class="home-mini-robot" aria-hidden="true"></span><h2>Let’s give your next listing<br>a proper launch.</h2><button class="home-primary" onclick="newCampaign()">Let’s get started</button></section>
 </main><footer class="home-footer">${logo}<span>Your expertise. Superpowered.</span>${footerLinks()}</footer></div>`;
 homeCalendarState={start:new Date('2026-11-02T12:00:00'),month:new Date('2026-11-01T12:00:00'),selected:0};renderHomeMonth();homeSellerReport(7);if(window.sampleOutput)sampleOutput('social');
}
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
 const links=[];
 return `<header class="home-nav shared-nav">${logo}<nav aria-label="Main navigation">${links.map(([id,label,fn])=>`<a href="#${id==='home'?'':id}" ${active===id?'aria-current="page"':''} onclick="${fn}();return false">${label}</a>`).join('')}</nav><button class="alt" onclick="clientAccess()">${state.clientSignedIn?'My Dashboard':'Client Login'}</button></header>`;
}
function footerLinks(){
 return `<span style="display:flex;gap:22px;flex-wrap:wrap;align-items:center;font-size:12px"><a href="privacy.html">Privacy</a><a href="data-deletion.html">Data deletion</a><a href="terms.html">Terms</a><a href="#setup-guides" onclick="setupGuides();return false">Setup guides</a><a href="mailto:resmaraai@gmail.com" target="_blank" rel="noopener">Contact</a><a href="admin.html">Team room</a></span>`;
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
function clientAccess(mode='signin'){
 // state.clientSignedIn is a browser memory, not a session. Ask the API client whether the
 // token is still alive, or a customer whose session ended can never reach the form to fix it.
 if(state.clientSignedIn&&window.RM&&RM.isLoggedIn()){dashboard();return}
 if(state.clientSignedIn){state.clientSignedIn=false;persist()}
 const creating=mode==='create';
 show(`<span class="eyebrow">RESMARA CLIENT AREA</span><h2>${creating?'Create an account':'Client Login'}</h2><p>${creating?'Just your name, email and a password. Resmara learns the rest when you connect your Meta account.':'Enter your email and password.'}</p><form onsubmit="event.preventDefault();submitTestClient(this,${creating})">${creating?'<div class="nc-row name-row"><label class="field">First name<input name="firstName" required maxlength="60" autocomplete="given-name"></label><label class="field">Last name<input name="lastName" required maxlength="60" autocomplete="family-name"></label></div>':''}<label class="field">Email address<input name="clientEmail" type="email" required maxlength="254" autocomplete="email"></label><label class="field">Password<span class="pw-wrap"><input name="clientPassword" type="password" required minlength="${creating?8:1}" autocomplete="${creating?'new-password':'current-password'}"><button type="button" class="pw-eye" onclick="togglePw(this)" aria-label="Show password" aria-pressed="false">Show</button></span></label>${creating?'<details class="invite-toggle"><summary>Have an invite code?</summary><label class="field">Invite code<input name="inviteCode" maxlength="64" autocomplete="off" spellcheck="false" placeholder="From your invitation"></label></details>':''}<p class="fine" role="status"></p><div class="modal-actions"><button>${creating?'Create account':'Sign in'}</button><button type="button" class="alt" onclick="clientAccess('${creating?'signin':'create'}')">${creating?'Back to sign in':'Create an account'}</button></div></form>${state.name&&!state.email?'<button class="alt" onclick="resumeDemo()">Resume previous demo</button>':''}<p class="fine">${creating?'Passwords need at least 8 characters.':'<a href="#" onclick="forgotPassword();return false">Forgot your password?</a>'}</p>`);
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
  <section class="mb-sec"><h4>COLOURS</h4><div class="mb-swatches">${k.palette.map(([role,hex],i)=>`<label class="mb-sw"><input type="color" value="${esc(hex)}" oninput="this.nextElementSibling.querySelector('code').textContent=this.value.toUpperCase();brandColoursSync(this.form)"><span><b>${esc(role)}</b><code>${esc(hex.toUpperCase())}</code></span></label>`).join('')}</div><input type="hidden" name="colours" value="${esc(k.palette.map(p=>p[1]).join(', '))}"></section>
  <div class="mb-two"><section class="mb-sec"><h4>TYPOGRAPHY</h4><p class="mb-type-h" style="font-family:'${esc(k.fonts[0])}',serif">The long view</p><small>Headlines · ${esc(k.fonts[0])}</small><p class="mb-type-b" style="font-family:'${esc(k.fonts[1])}',sans-serif">Morning light, wide oak floors and room to breathe.</p><small>Body · ${esc(k.fonts[1])}</small></section>
  <section class="mb-sec"><h4>VOICE</h4><textarea name="voice" rows="2">${esc(k.voice)}</textarea><div class="mb-chips">${k.use.map(w=>`<span class="ok">“${esc(w)}”</span>`).join('')}${k.avoid.map(w=>`<span class="no">${esc(w)}</span>`).join('')}</div></section></div>
  <div class="mb-two"><section class="mb-sec"><h4>YOUR LOOK</h4><div class="mb-looks">${['Modern','Classic','Rustic','Match my brand'].map(t=>`<button type="button" class="${t===k.theme?'on':''}" onclick="state.brand={...state.brand,theme:'${t}'};persist();this.parentNode.querySelectorAll('button').forEach(x=>x.classList.toggle('on',x===this))">${t}</button>`).join('')}</div><small>Change your look any time. New campaigns use it.</small></section>
  <section class="mb-sec"><h4>ON EVERY POST</h4><ul class="mb-legal">${k.legal.map(l=>`<li>${esc(l)}</li>`).join('')}</ul><small>Your brokerage’s rules, checked.</small></section></div>
  <section class="mb-sec"><h4>WHERE RESMARA LOOKED</h4><div class="mb-sources">${k.sources.map(([t,v])=>`<span>✓ <b>${esc(t)}</b> ${esc(v)}</span>`).join('')}</div></section>
  `}
function myBrand(){
 const k=brandKitData();
 $('#content').innerHTML=`<div class="welcome mb-page-head"><h1>My Brand</h1></div><div class="notice page-intro">This is the brand kit Resmara built from your website, socials and brokerage. Every post and ad follows it, so check it over, fix anything that’s off and save.</div>
 <form class="mb" onsubmit="saveBrandProfile(event,this,false)">${brandKitSections(k)}<p class="fine" data-brand-error role="alert"></p>
  <div class="mb-foot"><div class="mb-status"><button class="mb-research" type="button" onclick="toast('Resmara is researching your brand again. This takes a minute.')">Research again</button><button class="mb-research" type="button" onclick="brandFromPage(this)">Build from my Facebook Page</button><span>✓ Researched ${esc(k.researched||'from your website')}</span></div><button class="campaign-primary">Save my brand</button></div>
 </form>`;
}
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
  if(onboarding)onboard(1);else{myBrand();toast(synced?'Brand profile saved to your account.':'Brand profile saved in this browser — sign in to keep it on your account.')}
 }catch(e){error.textContent=e.message}finally{button.disabled=false}
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
 app.innerHTML=`<div class="marketing-home">${siteNav('pricing')}<main><section class="home-section package-page"><div><span class="home-kicker">$49 PER CAMPAIGN</span><h1>One listing.<br><span>One campaign.</span><br>Forty-nine dollars.</h1><p>A 14-day branded campaign for one property: the creative, the calendar, the publishing and the day 7 and day 14 seller reports.</p><p>No subscription, no packs, nothing to top up. You pay the $49 when the campaign is ready to build, through Stripe Checkout. Meta ad spend is separate and goes to your own ad account.</p><p class="fine">Preparing a campaign — the scope, the captions, the calendar — costs nothing. You only pay to build it.</p></div><div class="home-price-detail"><h3>What the $49 buys</h3><ul><li>A 14-day social campaign for that listing</li><li>Caption and photo pairings from your own gallery</li><li>Digital ad creative and campaign setup</li><li>Your calendar, review and approval</li><li>Scheduled social publishing</li><li>Day 7 and day 14 seller reports</li></ul><button class="home-primary" onclick="newCampaign()">Start a campaign</button></div></section></main><footer class="home-footer">${logo}<span>Your expertise. Superpowered.</span>${footerLinks()}</footer></div>`;
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
 { id: 'facebook', title: 'Create a Facebook account', need: 'Required', time: '5 minutes',
   why: 'Every Facebook business Page is run from a personal account. Your personal posts and details never show on your Page.',
   steps: ['Go to facebook.com and click Create new account.', 'Use your real name and an email or phone number you check.', 'Confirm the code Facebook sends you.'],
   link: ['Open Facebook', 'https://www.facebook.com/'] },
 { id: 'page', title: 'Create your Facebook business Page', need: 'Required', time: '10 minutes',
   why: 'Resmara posts your listings to a business Page, never to your personal profile.',
   steps: ['On a computer, log in to Facebook and open Pages in the left menu, then Create Page.', 'Use your business name, for example “Jamie Carter, Realtor”, and pick the Real Estate Agent category.', 'Add a headshot or logo, a cover photo, and your website, phone and email.'],
   link: ['Create a Page', 'https://www.facebook.com/pages/create'] },
 { id: 'admin', title: 'Make sure you have full control of your Page', need: 'Required', time: '2 minutes',
   why: 'Resmara can only post to a Page you fully control. Pages made by a brokerage, an old assistant or a marketing company are often owned by someone else.',
   steps: ['On Facebook, switch into your Page.', 'Open Settings, then Page access.', 'Check your name is listed with full control. If it isn’t, ask whoever is listed to give you full control.'] },
 { id: 'instagram', title: 'Switch your Instagram to a business account', need: 'Recommended', time: '1 minute',
   why: 'Meta only lets apps like Resmara post to business (Professional) Instagram accounts. It’s free, and you keep all your posts and followers. Your account becomes public.',
   steps: ['In the Instagram app, go to your profile and open the menu.', 'Under For professionals, tap Account type and tools, then Switch to professional account.', 'Pick a category such as Real Estate Agent, choose Business and tap Next.'],
   note: 'No Instagram yet? Make one in the Instagram app first. Without Instagram, Resmara posts to your Facebook Page only.' },
 { id: 'link', title: 'Link your Instagram to your Facebook Page', need: 'Recommended', time: '2 minutes',
   why: 'Resmara finds your Instagram through your Facebook Page, so the two have to be linked.',
   steps: ['On Facebook, switch into your Page and open Settings.', 'Open Linked accounts, then Instagram, and click Connect account.', 'Log in to your Instagram and confirm. If it’s still a personal account, Facebook offers to switch it to business right here.'],
   note: 'An Instagram can be linked to one Page at a time. If it’s linked to an old Page, disconnect it there first.',
   link: ['Open linked accounts', 'https://www.facebook.com/settings/?tab=linked_instagram'] },
 { id: 'ads', title: 'Set up your ad account and payment method', need: 'Recommended', time: '5 minutes',
   why: 'Your listing ad runs from your own Meta ad account. Meta bills your ad budget to your card directly. Resmara never charges or keeps any of it.',
   steps: ['Open Meta Business Suite, then Settings, Accounts and Ad accounts.', 'Click Add, then Create a new ad account. Enter a name, your time zone and currency, and give yourself full control.', 'In Ads Manager, open Billing & payments and add a card or PayPal.'],
   note: 'Without an ad account your posts still go out. Only the listing ad is off.',
   link: ['Open Meta Business Suite', 'https://business.facebook.com/'] },
 { id: 'connect', title: 'Connect it all to Resmara', need: 'Last step', time: '1 minute',
   why: 'One Facebook login gives Resmara your Page, Instagram and ad account.',
   steps: ['In your Resmara dashboard, open Accounts and click Connect your Meta account.', 'Log in with Facebook and choose your Page, your Instagram and your ad account.', 'Resmara checks everything. If anything still needs fixing, it tells you what, and you click Check again once it’s done.'] }
];
function setupGuides(open) {
 if (typeof stopResmaraGuide === 'function') stopResmaraGuide();
 if (typeof modal !== 'undefined' && modal.open) modal.close();
 location.hash = 'setup-guides'; document.title = 'Setup guides — Resmara';
 const card = g => `<details class="sg-guide" id="sg-${g.id}" ${g.id === open ? 'open' : ''}><summary><span class="sg-title">${g.title}</span><span class="sg-tag${g.need === 'Required' ? ' req' : ''}">${g.need}</span><span class="sg-time">${g.time}</span><span class="fold-chev" aria-hidden="true"></span></summary>
  <div class="sg-body"><p>${g.why}</p><ol class="ig-switch-steps">${g.steps.map((s, i) => `<li><span>${i + 1}</span><div>${s}</div></li>`).join('')}</ol>${g.note ? `<p class="fine">${g.note}</p>` : ''}${g.link ? `<a class="sg-open" href="${g.link[1]}" target="_blank" rel="noopener">${g.link[0]}</a>` : ''}</div></details>`;
 app.innerHTML = `<div class="marketing-home">${siteNav('setup-guides')}<main><section class="home-section sg-page"><div class="sg-head"><span class="home-kicker">SETUP GUIDES</span><h1>Get your accounts<br><span>ready for Resmara.</span></h1>
  <p>Resmara works best when you have a Facebook business Page, a business Instagram linked to it, and a Meta ad account. Then Resmara posts, advertises and reports for you from day one. Here’s how to set up each one.</p>
  <ul class="sg-check"><li><b>Facebook business Page</b> you fully control <span class="sg-tag req">Required</span></li><li><b>Business Instagram</b> linked to the Page <span class="sg-tag">Recommended</span></li><li><b>Meta ad account</b> with a payment method <span class="sg-tag">Recommended</span></li></ul></div>
  <div class="sg-list">${SETUP_GUIDES.map(card).join('')}</div>
  <div class="sg-help"><b>Rather do it together?</b> Book a free 30-minute setup call and one of our team will set it all up with you.<button type="button" class="home-primary" onclick="obBook(true)">Book a free setup call</button></div></section></main><footer class="home-footer">${logo}<span>Your expertise. Superpowered.</span>${footerLinks()}</footer></div>`;
 const el = open && document.getElementById('sg-' + open);
 if (el) setTimeout(() => el.scrollIntoView({ block: 'start', behavior: 'smooth' }), 50); else window.scrollTo(0, 0);
}
