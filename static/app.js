const $=s=>document.querySelector(s),app=$('#app'),modal=$('#modal');const img='resmara-house-complete-v1.png',img2='resmara-house-complete-v1.png';let saved;try{saved=JSON.parse(localStorage.getItem('resmara') || localStorage.getItem('listing14')||'{}')}catch{saved={}}let state={name:'',connected:false,campaigns:[],...saved},view='overview',step=0,draft={};const logo='<a href="#" class="logo resmara-logo" aria-label="Resmara home" onclick="home();return false"><img src="resmara-logo-navy.png" alt="Resmara"></a>';const esc=s=>String(s||'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));function persist(){try{localStorage.setItem('resmara',JSON.stringify(state))}catch(e){/* Embedded preview keeps state in memory when storage is unavailable. */}}function toast(t){let e=document.createElement('div');e.className='toast';e.textContent=t;document.body.append(e);setTimeout(()=>e.remove(),3500)}function howItWorks(){location.hash='how-it-works';document.title='How It Works — Resmara';app.innerHTML=`<div class="launch-home journey">${siteNav("how-it-works")}<main><section class="journey-step intro-step" data-scene="intro" data-guide="Let me show you how this works.|Your listing. My superpowers. A few simple steps."><h1>A little help.<br><span>A powerful launch.</span></h1><p>Here’s how we turn your photos and videos into a branded 14-day campaign—from connecting your accounts to sharing the results.</p></section><section class="journey-step connect-step" id="connect" data-scene="connect" data-guide="First, let’s get connected.|Your Facebook. Your Instagram. Your brand."><span class="launch-tag">01 · CONNECT</span><h2>Your accounts.<br>All connected.</h2><p>Connect your social media and ad account once. I’ll help you get set up, then remember them for your next listing.</p><div class="simple-connections"><span>f <b>Facebook</b></span><span>◎ <b>Instagram</b></span><span>↗ <b>Meta ads</b></span></div></section><section class="journey-step property-step" data-scene="property" data-guide="Now, show me the home.|One listing link. Your photos and videos. I’ll take it from there."><span class="launch-tag">02 · ADD YOUR LISTING</span><h2>You’ve got the home.<br>I’ll get to know it.</h2><p>Paste your property link and share the photos and videos you’ve already had shot.</p><p>I’ll gather the property details and learn your professional style, using your website, public brand information and the examples you share. You check that I’ve got it right.</p><div class="simple-listing-link"><span>↗</span><div><small>YOUR PROPERTY LINK</small><b>youragency.com/your-next-listing</b></div><span>✓</span></div></section><section class="journey-step build-step" id="sample-campaign" data-scene="build" data-guide="This is where my superpowers come in.|I’ll build the calendar, write the posts and create your digital ads."><span class="launch-tag">03 · WATCH IT COME TOGETHER</span><h2>One listing becomes<br>a whole campaign.</h2><p>I turn your photos, video and property details into 14 days of marketing that looks and sounds like you.</p><div class="simple-deliverables"><div><span>▦</span><b>Your calendar</b><p>Fourteen days, all lined up.</p></div><div><span>✎</span><b>Your social posts</b><p>Copy and branded creative, ready to review.</p></div><div><span>↗</span><b>Your digital ads</b><p>Photo or video ads, built from the media you supply.</p></div></div><details class="sample-discovery"><summary>See what your campaign could look like</summary><div class="sample-tabs" role="tablist" aria-label="Sample campaign outputs"><button role="tab" id="tab-social" aria-selected="true" aria-controls="sample-output" onclick="sampleOutput('social')">Social</button><button role="tab" id="tab-ad" aria-selected="false" aria-controls="sample-output" onclick="sampleOutput('ad')">Ad</button><button role="tab" id="tab-calendar" aria-selected="false" aria-controls="sample-output" onclick="sampleOutput('calendar')">Calendar</button><button role="tab" id="tab-report" aria-selected="false" aria-controls="sample-output" onclick="sampleOutput('report')">Report</button></div><div id="sample-output" role="tabpanel" aria-labelledby="tab-social"></div><p class="sample-disclosure">Illustrative creative and data. This demo doesn’t generate or publish a real campaign.</p></details></section><section class="journey-step launch-step" data-scene="launch" data-guide="Make it yours. Give it the thumbs-up.|Review the posts and ads, make your changes, then approve your launch."><span class="launch-tag">04 · APPROVE & LAUNCH</span><h2>A quick look from you.<br>A proper launch from me.</h2><p>Check the campaign, change anything you like and choose your ad spend. Nothing goes live without your approval.</p><p>Then I schedule your posts and submit your ads, with housing-ad settings checked before launch. I’ll keep you informed while Meta reviews them.</p><div class="launch-sequence"><span>You approve</span><i>→</i><span>I schedule</span><i>→</i><span>Your listing gets seen</span></div></section><section class="journey-step outcome-step" id="seller-report" data-scene="outcome" data-guide="And I’ll show you how it’s going.|Real exposure. Clear numbers. Something to share with your seller."><span class="launch-tag">05 · SEE & SHARE THE RESULTS</span><h2>“How’s the marketing going?”<br>Now you have an answer.</h2><p>I bring the results together at day 7 and day 14: what went out, who it reached, listing clicks and ad spend.</p><div class="phone-report"><div><b>Your seller update</b><span>Day 7 + Day 14</span></div><ul><li>What was published</li><li>People reached and listing clicks</li><li>How your ad budget was used</li></ul><button class="alt" onclick="campaignReport(examples[0],7)">See a sample report</button></div><p>Less time making marketing. More time being the agent your clients count on.</p></section><section class="journey-step start-step" data-scene="start" data-guide="Ready to do this?|Your whole campaign. All working together."><span class="launch-tag">YOUR EXPERTISE. SUPERPOWERED.</span><h2>Ready to supercharge<br>your next listing?</h2><p>And when the next home comes along? We’ll be ready to do it again.</p><button class="journey-start" onclick="newCampaign()">Let’s get started</button><span class="journey-demo">Interactive prototype · No live posts, ads or payments.</span></section></main><footer class="launch-footer"><span>Resmara</span><span>Real Estate Social Marketing,<br>Analytics & Reporting Assistant</span></footer></div>`;if(window.mountResmaraGuide)mountResmaraGuide();if(window.sampleOutput)sampleOutput('social')}

// The two sample listings every account sees. They are the only campaigns a brand-new
// account opens on, and they are the same for every customer (owner: Oakridge and Willow).
const examples=[{address:'1248 Oakridge Drive',area:'Austin, TX · $845,000',day:7,status:'Demo · Active',phase:'active',image:'sample/card-1.jpg'},{address:'76 Willow Lane',area:'Austin, TX · $625,000',day:3,status:'Demo · Republished',phase:'republished',image:'sample/card-2.jpg'}];function dashboard(v='campaigns'){if(window.stopResmaraGuide)stopResmaraGuide();view=v;location.hash='dashboard';app.innerHTML=`<div class="shell"><aside class="sidebar">${logo}<span class="eyebrow" style="margin:16px 12px -15px;color:#52778f">YOUR WORKSPACE</span><nav class="side-nav">${[['campaigns','◫','My campaigns'],['brand','✦','My Brand'],['credits','◇','Billing'],['accounts','◎','Accounts'],['support','✉','Support']].map(([id,icon,label])=>`<button class="${v===id?'active':''}" onclick="dashboard('${id}')">${icon} &nbsp; ${label}</button>`).join('')}</nav>${themeToggle()}${state.priorDemos?.length?'<button class="alt" onclick="restorePriorDemo()">Switch to previous demo</button>':''}<button class="alt" onclick="signOutDemo()">Sign out</button><a class="small" onclick="home()">Back to homepage</a><p class="side-legal"><a href="privacy.html" target="_blank" rel="noopener">Privacy</a> · <a href="data-deletion.html" target="_blank" rel="noopener">Data deletion</a> · <a href="terms.html" target="_blank" rel="noopener">Terms</a></p></aside><main class="main workspace-main"><div id="content"></div></main></div>`;if(v==='accounts')accounts();else if(v==='brand')myBrand();else if(v==='credits')myCredits();else if(v==='support')supportPage();else campaignList()}// Pull the campaigns that actually exist in the API and keep them in the same list as local
// drafts, so a client sees their real campaign after a reload or on another device.
let liveCampaignsSyncedAt=0;
function liveStatusLabel(b){
 const stage=String((b&&b.stage)||'').toUpperCase();
 if(b&&b.meta_campaign_id)return 'Ad campaign created · paused';
 if(stage==='APPROVED')return 'Approved · ready to launch';
 if(stage==='DEPLOYED'||stage==='LIVE')return 'Launched';
 return (b&&b.posts_total)?'Built · awaiting approval':'Draft';
}
async function syncLiveCampaigns(){
 if(!liveCampaignsAvailable()||Date.now()-liveCampaignsSyncedAt<10000)return;
 liveCampaignsSyncedAt=Date.now();
 try{
  const rows=await RM.boosts();
  const list=Array.isArray(rows)?rows:(rows&&rows.boosts)||[];
  // Signature includes the cover photo: a card that swaps stock art for the property photo is
  // a visible change and must repaint, even though the campaign list itself is unchanged.
  // until_sold is in the signature too: turning autopilot on or off (here or on a phone) is a
  // visible change and the card must repaint, not wait for a reload.
  const signature=list=>list.map(c=>[campaignBoostId(c),c.image||'',c.status,c.until_sold?'on':'off',Number(c.new_leads||0),c.launched_at||''].join(':')).join(',').slice(0,4000);
  const before=signature(state.campaigns);
  list.forEach(b=>{
   if(!b||b.id==null)return;
   const card={address:b.address,area:(b.campaign_days||14)+'-day campaign · $'+Number(b.ad_budget_usd||0).toFixed(0)+'/day',status:liveStatusLabel(b),boostId:b.id,live:true,day:0,hidden:b.hidden===true,posts_total:b.posts_total||0,posts_approved:b.posts_approved||0,posts_published:b.posts_published||0,url:'',media:'',image:b.image||undefined,budget:'$'+Number(b.ad_budget_usd||0).toFixed(0)+'/day',until_sold:b.until_sold===true,until_sold_at:b.until_sold_at||null,new_leads:b.new_leads||0,launched_at:b.launched_at||null,stage:b.stage||null};
   const existing=state.campaigns.find(c=>String(campaignBoostId(c))===String(b.id));
   if(existing)Object.assign(existing,card);else state.campaigns.push(card);
  });
  persist();
  if(before!==signature(state.campaigns)&&typeof view!=='undefined'&&view==='campaigns')campaignList();
 }catch(e){}
}
// --- Hiding and deleting campaigns -----------------------------------------
// A campaign is either the customer's own (it has a boost id and the account owns it) or one of
// the built-in samples. Hiding is reversible on both; deleting is only offered for the customer's
// own campaigns, and the server decides whether deleting is allowed (a paid campaign is not).
function isSample(campaign){return !campaignBoostId(campaign)}
function campaignKey(campaign){return isSample(campaign)?'sample:'+campaign.address:'boost:'+campaignBoostId(campaign)}
function campaignByKey(key){return [...state.campaigns,...examples].find(c=>campaignKey(c)===key)}
function campaignHidden(campaign){
 if(isSample(campaign))return (state.hiddenSamples||[]).includes(campaign.address);
 return campaign.hidden===true;
}
function visibleCampaigns(){return [...state.campaigns,...examples].filter(c=>!campaignHidden(c))}
function hiddenCampaigns(){return [...state.campaigns,...examples].filter(campaignHidden)}
function hideCampaign(key){
 const c=campaignByKey(key);if(!c)return;
 if(isSample(c)){state.hiddenSamples=[...(state.hiddenSamples||[]),c.address];persist();campaignList();toast('Moved to Completed campaigns.');return}
 RM.hideBoost(campaignBoostId(c),true).then(()=>{c.hidden=true;persist();campaignList();toast('Moved to Completed campaigns.')})
  .catch(e=>toast('Could not hide that campaign: '+((e&&e.message)||'unknown error')));
}
function unhideCampaign(key){
 const c=campaignByKey(key);if(!c)return;
 if(isSample(c)){state.hiddenSamples=(state.hiddenSamples||[]).filter(a=>a!==c.address);persist();campaignList();return}
 RM.hideBoost(campaignBoostId(c),false).then(()=>{c.hidden=false;persist();campaignList();toast('Campaign is back in your list.')})
  .catch(e=>toast('Could not restore that campaign: '+((e&&e.message)||'unknown error')));
}
function deleteCampaign(key){
 const c=campaignByKey(key);if(!c)return;
 if(isSample(c)){hideCampaign(key);return}
 const id=campaignBoostId(c);
 if(id==null||!window.RM){toast('This campaign is not linked to a workspace yet.');return}
 // An in-page confirm, not window.confirm: Chrome stops showing native dialogs on a tab once the
 // owner ticks "prevent this page from creating additional dialogs", and after that Delete looked
 // like a dead button. This one cannot be suppressed, and it says what is about to go.
 show(`<span class="eyebrow">DELETE CAMPAIGN</span><h2>Delete “${esc(c.address)}”?</h2><p>Its posts, ads and photos are removed from Resmara and cannot be brought back. Anything already published to Facebook or Instagram stays in Meta Ads Manager.</p><p class="fine" role="alert"></p><div class="modal-actions"><button type="button" class="alt" onclick="modal.close()">Keep campaign</button><button type="button" class="danger" onclick="confirmDeleteCampaign('${esc(String(id))}')">Delete campaign</button></div>`);
}
function confirmDeleteCampaign(id){
 const error=modal.querySelector('[role="alert"]'),button=modal.querySelector('.danger');
 if(button){button.disabled=true;button.textContent='Deleting…'}
 RM.deleteBoost(id).then(()=>{
   state.campaigns=state.campaigns.filter(x=>String(campaignBoostId(x))!==String(id));
   persist();dashboard('campaigns');toast('Campaign deleted.');
 }).catch(e=>{
   if(error)error.textContent=(e&&e.message)||'Could not delete that campaign. Try again.';
   if(button){button.disabled=false;button.textContent='Delete campaign'}
   toast(((e&&e.message)||'Could not delete that campaign.'));
 });
}
// A campaign is Active (running), Republished (renewed and running again) or Completed.
// Completed campaigns leave the top list and sit in "Completed campaigns" below.
function campaignPhase(c){
 if(c.phase)return c.phase;
 const st=String(c.status||'').toLowerCase();
 if(c.renewed||st.includes('republish'))return 'republished';
 if(c.completed||st.includes('complete')||(c.live&&c.posts_total&&c.posts_published>=c.posts_total))return 'completed';
 return 'active';
}
const PHASE_LABEL={active:'Active',republished:'Republished',completed:'Completed'};
// A campaign's photo comes from the API as "/uploads/<file>", which only resolves when this
// app is served at the domain root. Under the Command Center's /resmara/ mount the path has
// to carry that prefix (api.js owns the rule). Guarded so a page without api.js still paints.
function mediaPath(u){return typeof mediaUrl==='function'?mediaUrl(u):u}
function campaignCard(c,top){
 const ph=campaignPhase(c),key=encodeURIComponent(campaignKey(c));
 return `<article class="card">${typeof newLeadCount==='function'&&newLeadCount(c)?`<button type="button" class="card-leads" onclick="openLeads(${[...state.campaigns,...examples].indexOf(c)})">${newLeadCount(c)} new lead${newLeadCount(c)>1?'s':''}</button>`:''}${c.image?`<img src="${esc(mediaPath(c.image))}" alt="${esc(c.address)}">`:(c.live?`<div class="card-noimg">No photos yet — import the listing link</div>`:`<img src="${img}" alt="Illustrative property photo">`)}<div class="card-body"><div class="card-status-row"><span class="pill phase-${ph}${campaignPaused(c)?' is-paused':''}">${campaignPaused(c)?'Paused':PHASE_LABEL[ph]}</span><span class="card-actions">${untilSoldButton(c)}${pauseButton(c)}</span></div><h3>${esc(c.address)}</h3><p>${esc(c.area||'Your saved campaign draft')}</p><div class="progress"><i style="width:${c.live?Math.min(100,(c.posts_published||0)/Math.max(c.posts_total||14,1)*100):(c.day||0)/14*100}%"></i></div><div class="flex small"><span>${c.live?(c.posts_total||0)+' posts · '+(c.posts_published||0)+' published':c.day?'Day '+c.day+' of 14':'Awaiting campaign generation'}</span><span>${c.live?esc(c.status==='Draft'?'Not built yet':'Meta ad'):c.day?'Facebook + Instagram':'Draft'}</span></div><button class="alt" onclick="details(${[...state.campaigns,...examples].indexOf(c)})">${c.day||c.live?'View campaign':'Review draft'} &nbsp;</button></div></article>`;
}
function campaignList(){
 syncLiveCampaigns();
 // Tabs: Active (Active + Republished, as cards) and Completed (a list). The status tag decides the tab.
 const all=[...state.campaigns,...examples],active=all.filter(c=>campaignPhase(c)!=='completed'),done=all.filter(c=>campaignPhase(c)==='completed');
 const tab=state.campTab==='completed'?'completed':'active';
 const tabs=`<div class="camp-tabs" role="tablist"><button role="tab" aria-selected="${tab==='active'}" class="${tab==='active'?'on':''}" onclick="state.campTab='active';persist();campaignList()">Active campaigns <span>${active.length}</span></button><button role="tab" aria-selected="${tab==='completed'}" class="${tab==='completed'?'on':''}" onclick="state.campTab='completed';persist();campaignList()">Completed campaigns <span>${done.length}</span></button></div>`;
 const body=tab==='active'
  ?`<div class="cards">${active.map(c=>campaignCard(c,true)).join('')||`<div class="panel"><b>No active campaigns.</b><p class="small">Start a campaign with ＋ Campaign.</p></div>`}</div>`
  :(done.length?`<div class="done-list">${done.map(c=>`<button class="done-row" onclick="details(${all.indexOf(c)})">${c.image?`<img src="${esc(mediaPath(c.image))}" alt="">`:'<span class="done-noimg"></span>'}<span class="done-main"><b>${esc(c.address)}</b><small>${esc(c.area||'')}</small></span><span class="pill phase-completed">Completed</span><span class="done-go">View campaign</span></button>`).join('')}</div>`:`<div class="panel"><b>No completed campaigns yet.</b><p class="small">When a campaign finishes its 14 days, it moves here.</p></div>`);
 $('#content').innerHTML=`<div class="welcome flex"><div><h1>My campaigns</h1></div><button class="campaign-primary add-campaign" onclick="newCampaign()">＋ Campaign</button></div><div class="notice page-intro">Every listing you launch lives here. Active campaigns are running now, and finished ones move to Completed, where you can run them again. Open any campaign to see its posts, its ad and your seller reports.</div>${tabs}${body}`;
}
function details(i){const c=[...state.campaigns,...examples][i]||visibleCampaigns()[0];$('#content').innerHTML=`<a onclick="dashboard('campaigns')" class="small">All campaigns</a><div class="welcome flex" style="margin-top:22px"><div><span class="pill">${esc(c.status)}</span><h1>${esc(c.address)}</h1><p>${esc(c.area||'Campaign draft · saved in this browser')}</p></div><button class="alt" onclick="campaignReport([...state.campaigns,...examples][${i}]||c,7)">View report</button></div>${!c.day?`<div class="notice">This draft is saved locally. Listing import, creative generation, payment and launch need to be connected to your production engine.</div><div class="panel"><b>Listing link</b><p>${esc(c.url)}</p><b>Photo and video folder</b><p>${esc(c.media)}</p><b>Meta ad budget</b><p>${esc(c.budget||'Use default spend (amount to be confirmed)')}</p></div>`:`<div class="notice">Sample campaign and illustrative schedule. No posts or ads are running.</div>`}<div class="panel"><div class="flex"><div><span class="eyebrow">THE CAMPAIGN PLAN</span><h3>Your 14 days, at a glance.</h3></div><span class="pill">Meta ad · Days 1–14</span></div><div class="calendar">${['Just listed','Property highlights','Room spotlight','Lifestyle story','Video walkthrough','Weekend viewing','Day 7 report','Neighborhood','Design details','Property reel','Key features','Viewing reminder','Final spotlight','Day 14 report'].map((t,j)=>`<div class="day ${j===6||j===13?'report':''}"><b>DAY ${j+1}</b>${t}<em>${j===6||j===13?'Performance report':'Social content concept'}</em></div>`).join('')}</div><p class="fine">Illustrative content plan. Final assets and posting frequency come from your campaign engine.</p></div>`}
function accounts(){$('#content').innerHTML=`<div class="welcome"><h1>Your social connections.</h1></div><div class="notice connection-notice" id="connNotice">Prototype only. Sign in to connect a real Meta account.</div><div class="panel meta-card"><span class="eyebrow">META</span><h3>Facebook Page, Instagram and ad account</h3><p id="connDetail">Choose the account you want to use for property marketing.</p><p id="connHealth" class="small" hidden></p><div class="btn-pair"><button id="metaConnectBtn" class="campaign-primary" onclick="connectMeta()">Connect Meta</button><button class="alt" id="metaCheckBtn" onclick="checkConnections()">Check connection</button></div></div>`;if(RM.isLoggedIn()){loadConnections()}else{const n=$('#connNotice');if(n)n.textContent='You are signed out, so no Meta account can be connected yet.';}}function disconnect(){state.connected=false;state.metaAudit=null;persist();dashboard('accounts')}
// --- Reports ---------------------------------------------------------------
// A backend-backed campaign carries the boost id the API needs. Local demo
// campaigns do not, so every caller falls back to the local behaviour.
function campaignBoostId(campaign){
 if(!campaign)return null;
 const id=campaign.boostId!=null?campaign.boostId:campaign.boost_id;
 return id===undefined||id===null||id===''?null:id;
}
function reportMoney(value){return value==null?'—':new Intl.NumberFormat('en-US',{style:'currency',currency:'USD'}).format(Number(value))}
function reportMetricTiles(tiles){return tiles.map(([label,value])=>`<div><span>${esc(label)}</span><b>${value==null?'—':value}</b></div>`).join('')}
// The four headline tiles for a real report payload. A section whose source is not
// 'meta' carries no numbers, so it renders an em dash - never an invented figure.
function liveReportTiles(data){
 const organic=(data&&data.organic)||{},paid=(data&&data.paid)||{},summary=organic.summary||{};
 return [['People reached',organic.source==='meta'?summary.reach:null],['Engagements',organic.source==='meta'?summary.interactions:null],['Listing clicks',paid.source==='meta'?paid.clicks:null],['Ad spend',paid.source==='meta'?reportMoney(paid.spend):null]];
}
async function campaignReport(property,day){
 if(!property)return;
 const boostId=campaignBoostId(property);
 if(boostId!=null&&window.RM){
  show(`<span class="eyebrow">SELLER REPORT · DAY ${day}</span><h2>${esc(property.address||'')}</h2><p role="status">Loading the real report from the Resmara API…</p>`);
  try{
   const data=await RM.report(boostId,day);
   const organic=(data&&data.organic)||{},paid=(data&&data.paid)||{},posts=(data&&data.posts)||{};
   const notes=[];
   if(organic.source!=='meta')notes.push('Meta has not returned organic post data yet'+(organic.reason?': '+organic.reason:'.'));
   if(paid.source!=='meta')notes.push('Meta has not returned ad data yet'+(paid.reason?': '+paid.reason:'.'));
   const when=((data&&data.period)||{}).label||('Day 1 to Day '+day);
   show(`<span class="eyebrow">SELLER REPORT · DAY ${day}</span><h2>${esc((data&&data.address)||property.address||'')}</h2><p>${esc(when)}</p><div class="home-report-metrics">${reportMetricTiles(liveReportTiles(data))}</div><div class="check">${posts.published||0} of ${posts.total||0} posts published · ${posts.approved||0} approved</div>${notes.length?`<p class="fine">${notes.map(esc).join(' ')}</p>`:'<p class="fine">Live Meta figures for this period.</p>'}<div class="modal-actions"><button class="alt" onclick="modal.close()">Close</button></div>`);
  }catch(e){
   show(`<h2>Report unavailable</h2><p>${esc(e.message)}</p><div class="modal-actions"><button class="alt" onclick="modal.close()">Close</button></div>`);
  }
  return;
 }
 // Local demo campaign: report only facts we actually hold (scheduled/approved) and say
 // plainly that Meta has not returned data. No sample metric is rendered as real.
 if(Number(property.day)<day)return;
 const campaigns=[...state.campaigns,...examples];
 const review=state.reviews&&state.reviews[typeof reviewKey==='function'?reviewKey(property,campaigns.indexOf(property)):'review-'+(property.reviewId||campaigns.indexOf(property))];
 const items=(review&&review.items)||[];
 show(`<span class="eyebrow">SELLER REPORT · DAY ${day}</span><h2>${esc(property.address||'')}</h2><p>Local demo campaign · not connected to a backend boost.</p><div class="home-report-metrics">${reportMetricTiles([['People reached',null],['Engagements',null],['Listing clicks',null],['Ad spend',null]])}</div><div class="check">${items.length} posts scheduled · ${items.filter(item=>item.reviewed).length} spot-checked</div><p class="fine">Meta has not returned data yet. Connect a backend boost to see published, organic and paid figures.</p><div class="modal-actions"><button class="alt" onclick="modal.close()">Close</button></div>`);
}
function normalizeWebLink(value){
 const link=value.trim();
 if(!link)return '';
 if(/\s/.test(link))return null;
 try{
  const url=new URL(/^[a-z][a-z0-9+.-]*:\/\//i.test(link)?link:'https://'+link);
  if(!['https:','http:'].includes(url.protocol)||!url.hostname.includes('.')||url.username||url.password)return null;
  return url.href;
 }catch{return null}
}
function show(html){modal.classList.remove("wide-modal");delete modal.dataset.gate;html=html.replace(/<input\b[^>]*>/g,input=>input.replace('type="url"','type="text" inputmode="url" data-web-link'));modal.innerHTML=`<button class="close" aria-label="Close" onclick="modal.close()">×</button>${html}`;const form=modal.querySelector('form');
 if(form?.querySelector('[data-web-link]')){
  form.addEventListener('input',event=>{if(event.target.matches('[data-web-link]'))event.target.setCustomValidity('')});
  form.addEventListener('submit',event=>{
   for(const field of form.querySelectorAll('[data-web-link]')){
    const url=normalizeWebLink(field.value);
    if(url===null||(field.required&&!url)){
     event.preventDefault();event.stopImmediatePropagation();
     field.setCustomValidity('Enter a website address, such as www.bap.digital.');
     field.reportValidity();return;
    }
    field.value=url;
   }
  },true);
 }
 if(!modal.open)modal.showModal()}// New campaign: the brand is built at sign-up, so the only questions are the listing link,
// the go-live date and (optionally) where the ad should send people. The address, facts and
// photos come from the listing. The ad budget is confirmed on the campaign page.
function firstCampaignOffer(){return !state.campaigns.some(c=>!examples.includes(c))}
function listingAddressFromLink(url){
 try{const u=new URL(url);const slug=decodeURIComponent(u.pathname).split('/').filter(Boolean).find(p=>/^\d+[-\s]/.test(p));
  if(slug)return slug.replace(/[-_]+/g,' ').replace(/\b(\w)/g,m=>m.toUpperCase()).replace(/\s+\d{5}.*$/,'').trim();}catch(e){}
 return 'Your new listing';
}
function newCampaign(){if(!state.clientSignedIn){clientAccess();return}if(typeof metaBlocked==='function'&&metaBlocked()){metaBlockedNotice();return}draft={};
 show(`<span class="eyebrow">NEW CAMPAIGN</span><h2>Listing details.</h2><form class="nc-form" data-state="empty" onsubmit="event.preventDefault();ncGo(this)"><span class="nc-title">MLS public listing link</span><p class="field-help nc-sub">Paste the public link your MLS makes when you share a listing with a client.</p><details class="nc-help"><summary>How do I get this link?</summary><p>Every MLS does this a little differently, but the idea is the same:</p><ol><li>Open the listing in your MLS.</li><li>Click <b>Share</b>, <b>Email</b> or <b>Send to client</b>. The name depends on your MLS.</li><li>Choose the option to <b>copy the link</b>. Pick the public or client link, not one that needs your MLS login.</li><li>Check it: open the link in a private browser window. If you can see the listing without signing in, it’s the right one.</li><li>Paste it here.</li></ol><p>If your MLS will only email the listing, send it to yourself and copy the link from that email.</p></details><input name="url" type="url" class="nc-url" aria-label="MLS public listing link" placeholder="https://..." oninput="ncReset(this.form)"><div class="nc-result" role="status" aria-live="polite"></div><div class="nc-address"><span class="nc-title">Property address</span><label class="field">Street address<input name="street" autocomplete="address-line1" oninput="ncReady(this.form)"></label><div class="nc-row3"><label class="field">City<input name="city" autocomplete="address-level2" oninput="ncReady(this.form)"></label><label class="field">State<input name="state" autocomplete="address-level1" maxlength="2" oninput="ncReady(this.form)"></label><label class="field">ZIP<input name="zip" inputmode="numeric" autocomplete="postal-code" maxlength="10" oninput="ncReady(this.form)"></label></div></div><div class="nc-upload"><span class="nc-title">Your photos</span>${ncDrop('files')}<p class="field-help">Upload the ones you want to use, or all of them. Minimum 14; Resmara picks the best 14.</p></div><label class="nc-rights"><input type="checkbox" name="rights" onchange="ncReady(this.form)"><span>I have permission to use these photos and listing details to market this property on social media and in ads.</span></label><div class="modal-actions"><button type="button" class="nc-cancel" onclick="modal.close()">Cancel</button><button class="campaign-primary nc-build" disabled>Check my link</button></div></form>`)}
// Review copy: listing pages give details and photos; Zillow-type sites that block automated
// reading give details only; login pages give nothing. Dan's listing reader decides this for real.
function ncReset(form){form.dataset.state='empty';form.querySelector('.nc-result').innerHTML='';ncReady(form)}
function ncGo(form){const st=form.dataset.state;if(st==='ok'||st==='details'||st==='manual'){ncBuild(form);return}ncCheck(form)}
function ncManual(btn){const form=btn.closest('form');form.dataset.state='manual';btn.closest('.nc-msg').querySelector('.nc-manual').remove();ncReady(form);form.street.focus()}
function ncCheck(form){
 const url=form.url.value.trim(),out=form.querySelector('.nc-result');let host='';try{host=new URL(url).hostname}catch{}
 const fail=why=>{form.dataset.state='none';out.innerHTML=`<div class="nc-msg no"><b>We can’t get what we need from this link.</b>${why} Please use another link, or enter the details yourself and upload your photos.<button type="button" class="nc-manual" onclick="ncManual(this)">Enter it manually</button></div>`;ncReady(form)};
 if(!host||!host.includes('.')){fail(' It doesn’t look like a complete web link.');return}
 form.dataset.state='checking';ncReady(form);
 out.innerHTML=`<div class="nc-msg wait nc-walk"><b>Resmara is checking your link…</b><div class="nc-steps"><span class="robot-avatar nc-bot" aria-hidden="true"></span><ul class="link-checks"><li data-k="open" class="now">Opening the link…</li><li data-k="details">Looking for the home’s details…</li><li data-k="photos">Looking for the photos…</li><li data-k="video">Looking for a video…</li></ul></div></div>`;
 const unreadable=/login|signin|sign-in|my\.flexmls/i.test(url),noPhotos=/zillow|realtor\.com|redfin|trulia|homes\.com/i.test(host);
 const hasVideo=/video|tour/i.test(url),order=['open','details','photos','video'],bot=out.querySelector('.nc-bot');const mark=(k,ok,t)=>{const li=out.querySelector(`[data-k=${k}]`);if(li){li.className=ok?'ok':'no';li.textContent=t}const nx=out.querySelector(`[data-k=${order[order.indexOf(k)+1]}]`);if(nx&&bot){nx.classList.add('now');bot.style.transform=`translateY(${nx.offsetTop}px)`}};
 setTimeout(()=>mark('open',!unreadable,unreadable?'This link needs an MLS sign-in':'Link opened'),800);
 setTimeout(()=>mark('details',!unreadable,unreadable?'Couldn’t read the home’s details':'Found the home’s details'),1600);
 setTimeout(()=>{
  mark('photos',!(unreadable||noPhotos),unreadable||noPhotos?'Couldn’t get the photos':'Found 24 photos');
  setTimeout(()=>{
  const vid=hasVideo&&!unreadable&&!noPhotos;
  mark('video',true,vid?'Found a listing video':'No video, so your ad will be a photo carousel');
  setTimeout(()=>{
   draft={url,address:listingAddressFromLink(url),addressSource:'link',photoSource:'listing',media:url,photos:[],hasVideo:vid};
   if(unreadable){fail(' It needs an MLS sign-in to open.')}
   else if(noPhotos){form.dataset.state='details';out.innerHTML=`<div class="nc-msg part"><b>We have the home’s details, but we can’t get the photos from this link.</b>Upload your photos below and you’re ready to go.</div>`;ncReady(form)}
   else{form.dataset.state='ok';out.innerHTML=`<div class="nc-msg ok"><span class="robot-avatar" aria-hidden="true"></span><div><b>Green light.</b> We have the home’s details and 24 photos${vid?', plus a listing video. Your video will be your ad and your first post.':'.'} You’re ready to build.</div></div>`;ncReady(form)}
  },500);
  },800);
 },2400);
}
function ncReady(form){const st=form.dataset.state,n=form.files.files.length,addr=['street','city','state','zip'].every(k=>form[k].value.trim()),btn=form.querySelector('.nc-build');
 const build=st==='ok'||st==='details'||st==='manual';
 btn.textContent=st==='checking'?'Checking…':build?'Build my campaign · $49':'Check my link';
 btn.disabled=(build&&!form.rights.checked)||st==='checking'||(st==='empty'&&!form.url.value.trim())||(st==='none')||(st==='details'&&n<14)||(st==='manual'&&!(n>=14&&addr))}
function ncBuild(form){const st=form.dataset.state;if(!form.rights.checked)return;draft.photoRightsConfirmed=new Date().toISOString();
 if(st==='manual')Object.assign(draft,{address:[form.street.value.trim(),form.city.value.trim(),form.state.value.trim()+' '+form.zip.value.trim()].join(', '),addressSource:'manual'});
 if(st!=='ok')Object.assign(draft,{photoSource:'upload',uploadCount:form.files.files.length});
 reviewDraft()}
// Photos: from the listing link (when the form offers it), a photo link, or an upload.
function ncPhotos(start){const tabs=(start==='listing'?[['listing','From my listing link']]:[]).concat([['link','Paste a photo link'],['upload','Upload photos']]);
 return `<div class="nc-photos" data-mode="${start}"><span class="nc-label">Photos</span><div class="nc-tabs" role="tablist">${tabs.map(([m,l])=>`<button type="button" class="${m===start?'on':''}" onclick="ncMode(this,'${m}')">${l}</button>`).join('')}</div><div class="nc-pane" data-pane="listing"><p class="field-help">Resmara takes the photos from your listing link. If it can’t get them, it will ask you for a photo link or an upload.</p></div><div class="nc-pane" data-pane="link"><label class="field">Photo link<input name="photourl" type="url" placeholder="https://..."></label><p class="field-help">The link your photographer sent you: Fotello, Aryeo, Dropbox or Google Drive.</p></div><div class="nc-pane" data-pane="upload">${ncDrop('files')}<p class="field-help">Add at least 14 photos, or all of them. Resmara picks the best 14.</p></div></div>`}
// Photo drop box, shared by the form and the "link didn't give us the photos" step.
function ncDrop(name){return `<label class="nc-drop"><input name="${name}" type="file" accept="image/*" multiple onchange="ncCount(this)"><b>＋</b><span>Drop your photos here or click to choose</span><small>Minimum 14</small></label>`}
function ncCount(input){if(input.form&&input.form.classList.contains('nc-form'))setTimeout(()=>ncReady(input.form));const n=input.files.length,box=input.closest('.nc-drop');box.querySelector('span').textContent=n?n+' photo'+(n===1?'':'s')+' selected':'Drop your photos here or click to choose';box.classList.toggle('short',n>0&&n<14);box.querySelector('small').textContent=n&&n<14?'Add '+(14-n)+' more (minimum 14)':'Minimum 14'}
function ncMode(btn,mode){const box=btn.closest('.nc-photos');box.dataset.mode=mode;box.querySelectorAll('.nc-tabs button').forEach(b=>b.classList.toggle('on',b===btn))}
function ncSubmit(form){
 const mode=form.querySelector('.nc-photos').dataset.mode,url=form.url.value.trim(),photoUrl=form.photourl.value.trim(),files=[...form.files.files],err=form.querySelector('[data-nc-error]');
 if(mode==='upload'&&files.length<14){err.textContent=files.length?'Add at least 14 photos ('+files.length+' selected).':'Add your listing photos (at least 14).';return}
 if(mode==='link'&&!photoUrl){err.textContent='Paste your photo link, or choose another way to add photos.';return}
 const address=listingAddressFromLink(url);
 draft={address,addressSource:'link',url,photoSource:mode,photoUrl:mode==='link'?photoUrl:'',uploadCount:files.length,media:mode==='link'?photoUrl:url,photos:[]};
 testListingLink();
}
// Review copy: listing pages give the details; their photos come through except on sites that
// block automated reading (Zillow, Realtor.com, Redfin and similar). Photo links from Dropbox,
// Google Drive, Aryeo and Fotello always come through.
const hostOf=u=>{try{return new URL(u).hostname}catch{return ''}};
const photoHostOk=u=>/dropbox\.com|drive\.google\.com|aryeo\.com|fotello/i.test(hostOf(u));
const listingPhotosOk=u=>!/zillow|realtor\.com|redfin|trulia|homes\.com/i.test(hostOf(u));
function testListingLink(){
 const mode=draft.photoSource;
 show(`<span class="eyebrow">CHECKING YOUR LINKS</span><h2>Resmara is reading your listing.</h2><div class="audit-track campaign-build-track"><span class="robot-avatar" aria-hidden="true"></span></div><ul class="link-checks"><li data-k="open">Opening your listing link…</li><li data-k="details">Looking for the home's details…</li><li data-k="photos">${mode==='upload'?'Checking your photos…':'Looking for the photos…'}</li></ul>`);
 const ok=mode==='upload'?true:mode==='link'?photoHostOk(draft.photoUrl):listingPhotosOk(draft.url);
 const mark=(k,good,text)=>{const li=modal.querySelector(`[data-k=${k}]`);if(li){li.className=good?'ok':'no';li.textContent=text}};
 setTimeout(()=>mark('open',true,'Listing link opened'),900);
 setTimeout(()=>mark('details',true,'Found the home’s details'),1900);
 setTimeout(()=>{
  if(ok){mark('photos',true,mode==='upload'?draft.uploadCount+' photos ready':mode==='link'?'Found the photos on your photo link':'Found 24 photos on your listing');setTimeout(()=>reviewDraft(),900);return}
  mark('photos',false,mode==='link'?'Couldn’t get the photos from your photo link':'Couldn’t get the photos from your listing link');
  setTimeout(()=>ncNeedPhotos(),1100);
 },3000);
}
// The listing gave us the details but not the photos: ask for a photo link or an upload.
function ncNeedPhotos(){
 show(`<span class="eyebrow">ONE MORE STEP</span><h2>We need your photos.</h2><p>We have the home’s details, but that link isn’t letting us get the photos. Paste the link your photographer sent you, or upload them.</p><form onsubmit="event.preventDefault();ncPhotosOnly(this)">${ncPhotos(draft.photoSource==='link'?'upload':'link')}<p class="fine" data-nc-error role="alert"></p><div class="modal-actions"><button type="button" class="alt" onclick="modal.close()">Cancel</button><button class="campaign-primary">Continue</button></div></form>`)}
function ncPhotosOnly(form){
 const mode=form.querySelector('.nc-photos').dataset.mode,photoUrl=form.photourl.value.trim(),files=[...form.files.files],err=form.querySelector('[data-nc-error]');
 if(mode==='upload'&&files.length<14){err.textContent=files.length?'Add at least 14 photos ('+files.length+' selected).':'Add at least 14 photos.';return}
 if(mode==='link'&&!photoUrl){err.textContent='Paste your photo link, or upload your photos.';return}
 draft.photoSource=mode;draft.photoUrl=mode==='link'?photoUrl:'';draft.uploadCount=files.length;testListingLink();
}

function reviewDraft(){
 // No credit gate: a campaign is $49 and Stripe charges for it when it is built, so the
 // draft can always be prepared. Losing the sale before the person has seen their calendar
 // was the worst part of the credit flow.
 show(`<h2>Reading your listing…</h2><p role="status">One moment.</p><button hidden id="start-campaign-scope" type="button">Start campaign</button>`);
 startCampaignScope(modal.querySelector('#start-campaign-scope'));
}
function saveDraft(paidDraft){if(!paidDraft?.scopeFirst){reviewDraft();return;}state.campaigns.unshift({...paidDraft,reviewId:Date.now().toString(),status:'Draft',day:0});persist();modal.close();dashboard('campaigns');details(0);toast('Your campaign is ready. Confirm your launch details to build it.')}
// The sign-up confirmation link (item 8). It calls the API straight from the URL, so the link
// works in whatever browser it is opened in - including one that has never seen Resmara.
function confirmPage(token){
 if(!token){toast('That link is missing its code.');return home()}
 RM.request('/api/auth/confirm?token='+encodeURIComponent(token)).then(r=>{
  toast('Email confirmed - sign in to continue.');
 }).catch(e=>toast((e&&e.message)||'That link has already been used or has expired.'))
 .then(()=>{state.clientSignedIn=false;persist();clientAccess()});
}

// A browser that remembers "signed in" but holds a session that has ended must not open the
// dashboard on a dead token: it lands on the sign-in instead.
if(state.clientSignedIn&&window.RM&&!RM.isLoggedIn()){state.clientSignedIn=false;persist();}
if(/\/confirm\/?$/.test(location.pathname)){confirmPage(new URLSearchParams(location.search).get('token')||'')}
else if(/\/reset\/?$/.test(location.pathname)){resetPasswordPage(new URLSearchParams(location.search).get('token')||'')}
else if(location.hash==='#pricing'||(!location.hash&&document.body.dataset.page==='pricing'))pricing();else if(location.hash==='#dashboard'&&state.clientSignedIn)dashboard();else if(document.body.dataset.page==='how-it-works'||location.hash==='#how-it-works')howItWorks();else home();
// If a bearer token is stored, refresh the session from the backend (best effort).
// A token that has already passed its expiry is dropped by RM.isLoggedIn(), so this only
// asks when there is a real session to ask about.
if(window.RM&&RM.isLoggedIn())RM.me().then(u=>{if(u&&u.email){// A stored token can belong to a different person than the workspace in this browser holds
// (a shared machine, or a token left behind). The session wins, and the other account's
// cached campaigns, leads and brand are dropped rather than shown as this account's.
if(state.email&&String(state.email).toLowerCase()!==String(u.email).toLowerCase()&&typeof clearAccountWorkspace==='function')clearAccountWorkspace();
state.name=u.name||state.name;state.email=u.email;state.clientSignedIn=true;state.isAdmin=!!u.is_admin;persist();// The dashboard is already drawn when this answer arrives, so put the operators' door in now.
}}).catch(()=>{});
// A profile kept on the account is the one that survives a cleared browser; a browser with
// no local brand takes it back rather than showing an empty My Brand form.
if(window.RM&&RM.isLoggedIn()&&RM.brandProfile)RM.brandProfile().then(remote=>{
 if(!remote||!Object.keys(remote).length)return;
 if(state.brand&&Object.keys(state.brand).length)return;
 state.brand={...remote};
 if(remote.brokerage&&!state.company)state.company=remote.brokerage;
 if(remote.agent&&!state.name)state.name=remote.agent;
 persist();if(view==='brand')myBrand();
}).catch(()=>{});
// When the backend stops accepting the session, say so once and stop pretending to be signed in.
if(window.RM&&RM.onSessionLost)RM.onSessionLost(()=>{
 state.clientSignedIn=false;persist();
 toast('Your session ended. Sign in again to keep working.');
 if(location.hash==='#dashboard'){const n=$('#connNotice');if(n)n.textContent='You are signed out, so no Meta account can be connected yet.';}
});

// Resmara stays available across the workspace and homepage.
const pipDock=document.createElement('div');pipDock.id='pip-dock';pipDock.innerHTML='<button class="pip-launcher" onclick="togglePip()" aria-label="Ask Resmara for help"><span class="robot-avatar" role="img" aria-label="Resmara, your three-dimensional robot guide"></span><span>Ask Resmara</span><span class="pip-online"></span></button><section id="pip-chat" class="pip-chat" hidden aria-label="Resmara support chat"><header class="flex"><div class="flex"><span class="robot-avatar" role="img" aria-label="Resmara, your three-dimensional robot guide"></span><div><b>Resmara</b><small>Real Estate Social Marketing, Analytics & Reporting Assistant</small></div></div><button class="pip-close" onclick="togglePip()" aria-label="Close Resmara chat">×</button></header><div id="pip-messages" class="pip-messages" aria-live="polite"><div class="pip-reply">Hi, I’m Resmara! I’ll help you get settled, build your campaign and find your way around. What can I help with?</div></div><div class="pip-questions"><button onclick="pipAnswer(0)">Start my first campaign</button><button onclick="pipAnswer(1)">Connect social accounts</button><button onclick="pipAnswer(2)">Fees and ad spend</button><button onclick="pipAnswer(3)">Find my reports</button></div><form class="pip-input" onsubmit="event.preventDefault();pipFreeText(this.question.value);this.reset()"><input name="question" aria-label="Message Resmara" required placeholder="Ask Resmara a question…"><button aria-label="Send message">↑</button></form><p class="pip-demo-note">Guided answers · anything else can be sent to the team as a real support request.</p></section>';document.body.append(pipDock);function togglePip(){const panel=document.querySelector('#pip-chat');panel.hidden=!panel.hidden}function pipMessage(t,mine=false){const e=document.createElement('div');e.className=mine?'pip-user':'pip-reply';e.textContent=t;document.querySelector('#pip-messages').append(e);e.scrollIntoView({block:'nearest'})}function pipAnswer(n){const questions=['How do I start my first campaign?','How do I connect my social accounts?','How do fees and ad spend work?','Where are my reports?'];const answers=['Start with My Brand, then add the listing: the address, the MLS or listing link, and your photos and videos. Resmara builds the 14-day calendar and you approve it before anything goes out. A campaign is $49, paid when you build it.','Open Accounts and connect your Facebook Page and Instagram account. Publishing runs through Meta, so the connection has to be yours — Resmara never posts without it.','One property campaign is $49, paid once when you build it. No subscription, no credits, nothing to top up. Meta ad spend is separate and goes to Meta from your own ad account.','Open the campaign’s report for the day 7 and day 14 views. Before a campaign has been running there are no numbers to show; it fills in from your connected accounts.'];pipMessage(questions[n],true);pipMessage(answers[n])}function pipFreeText(q){if(/start|first|campaign|listing/i.test(q))return pipAnswer(0);if(/connect|facebook|instagram|meta account/i.test(q))return pipAnswer(1);if(/cost|fee|price|budget|spend|pay/i.test(q))return pipAnswer(2);if(/report|result|performance/i.test(q))return pipAnswer(3);pipMessage(q,true);pipMessage('I keep to the guided answers above for setup, social connections, fees and reports. For anything else, send it to the team and a person will reply on your Support page.');pipOfferTicket(q)}


function confirmDemoCampaignCredit(button){
 if(button.disabled||!draft.address||!draft.url)return;
 // Payment comes first: no card on file means adding one before anything is built.
 if(!state.cardOnFile){buildNeedsCard();return}
 button.disabled=true;demoBuildCampaign();
}
// No card yet: the page blurs behind this and nothing is built until a card is added.
function buildNeedsCard(){
 show(`<span class="eyebrow">ADD A PAYMENT METHOD</span><h2>Add a card to build your campaign.</h2><p>Each campaign is <b>$49</b>, charged when you click Build my campaign. Add a card once and every campaign after that is one click.</p><p class="fine">You’ll add your card on Stripe’s secure page. Resmara never sees or stores your card number. Your ad budget is billed separately by Meta.</p><p class="fine">Preview only: no card page opens and nothing is charged in this review copy.</p><div class="modal-actions"><button type="button" class="nc-cancel" onclick="modal.close()">Cancel</button><button class="campaign-primary" onclick="state.cardOnFile=true;persist();demoBuildCampaign()">Add card and build · $49</button></div>`);
}
// The full build: charge, read the listing, write the posts, design the ad, lay out the calendar.
function demoBuildCampaign(){
 const account=state,paidDraft={...draft,creditUsed:1,paid:true,image:'sample/card-1.jpg',phase:'active'};
 const steps=['$49 charged to your card','Read your listing','Picked the best photos','Wrote your 14 posts',(draft.hasVideo?'Set up your video ad':'Designed your carousel ad'),'Laid out your campaign calendar'],per=1500;
 show(`<span class="eyebrow">BUILDING YOUR CAMPAIGN</span><h2>Resmara is building your campaign.</h2><p>This takes a minute or two. You can stay here and watch.</p><div class="build-bar"><div class="build-fill"></div><span class="robot-avatar build-bot" aria-hidden="true"></span></div><p class="build-status" role="status"></p><p class="fine">Demo · no real payment or listing research runs here.</p>`);
 const fill=modal.querySelector('.build-fill'),bot=modal.querySelector('.build-bot'),status=modal.querySelector('.build-status');
 const go=pct=>{fill.style.width=pct+'%';bot.style.left=pct+'%'};
 requestAnimationFrame(()=>go(4));
 steps.forEach((t,i)=>setTimeout(()=>{if(!status.isConnected)return;status.classList.remove('in');setTimeout(()=>{status.innerHTML='<span class="build-tick">✓</span> '+t;status.classList.add('in')},250);go(Math.round((i+1)/steps.length*100))},per*i+400));
 setTimeout(()=>{if(state===account&&state.clientSignedIn&&modal.open&&status.isConnected)saveBuiltCampaign(paidDraft)},per*steps.length+900);
}
function saveBuiltCampaign(c){state.campaigns.unshift({start:typeof nextCampaignDate==='function'?nextCampaignDate():undefined,...c,reviewId:Date.now().toString(),status:'Draft',day:0});persist();modal.close();dashboard('campaigns');details(0);toast('Your campaign is built. Set your go-live date, then review and approve it.')}

function demoAddressMatches(value){
 const words=value.toLowerCase().match(/[a-z0-9]+/g)||[];
 return words.join('').length>=3&&words.every(word=>['983','mission','de','oro','drive','dr','suite','e','redding','california','ca'].some(part=>part.startsWith(word)));
}
function updateListingAddress(input){
 const form=input.form;
 form.elements.placeId.value='';
 form.elements.addressSource.value='manual';
 const match=!liveCampaignsAvailable()&&demoAddressMatches(input.value);
 form.querySelector('#listing-address-options').hidden=!match;
 form.querySelector('#listing-address-status').textContent=liveCampaignsAvailable()?'Manual address · enter the street, city and state.':match?'Select the demo match below the address field.':input.value.trim()?'No demo match. You can continue with the address you entered.':'Try 983 Mission De Oro, or enter another address manually.';
}
function pickDemoListingAddress(button){
 const form=button.closest('form');
 form.elements.address.value='983 Mission De Oro Dr, Suite E, Redding, CA';
 form.elements.addressSource.value='demo';
 form.elements.placeId.value='';
 form.querySelector('#listing-address-options').hidden=true;
 form.querySelector('#listing-address-status').textContent='Demo address selected · not verified by Google.';
 form.elements.address.focus();
}
let listingMapsLoad;
function loadListingMaps(key){
 if(window.google?.maps?.importLibrary)return Promise.resolve();
 if(!listingMapsLoad)listingMapsLoad=new Promise((resolve,reject)=>{
  const script=document.createElement('script');
  const timer=setTimeout(()=>finish(false),12000);
  function finish(ok){
   clearTimeout(timer);
   delete window.resmaraMapsReady;
   if(ok)resolve();else{script.remove();reject(new Error('Google Maps did not load.'))}
  }
  window.resmaraMapsReady=()=>finish(true);
  script.onerror=()=>finish(false);
  script.src='https://maps.googleapis.com/maps/api/js?'+new URLSearchParams({key,v:'weekly',loading:'async',callback:'resmaraMapsReady'});
  document.head.append(script);
 }).catch(error=>{listingMapsLoad=null;throw error});
 return listingMapsLoad;
}
async function mountListingAddressLookup(){
 const target=document.querySelector('#listing-address-lookup');
 if(!target)return;
 const form=target.closest('form'),manual=form.querySelector('#listing-address-manual');
 const address=form.elements.address,status=form.querySelector('#listing-address-status');
 const fallback=message=>{
  target.replaceChildren();
  manual.hidden=false;
  address.required=true;
  status.textContent=message;
 };
 try{
  if(!window.google?.maps?.importLibrary){
   // No Maps key is configured for this app, so the address is typed by hand. (This used to
   // ask a separate local test server for a key; that server no longer exists.)
   return;
  }
  const {PlaceAutocompleteElement}=await google.maps.importLibrary('places');
  if(!target.isConnected||address.value)return;
  const lookup=new PlaceAutocompleteElement();
  lookup.placeholder='Start typing a street address';
  lookup.setAttribute('aria-label','Property address');
  const label=document.createElement('b');
  label.textContent='Property address';
  const manualButton=document.createElement('button');
  manualButton.type='button';
  manualButton.className='alt';
  manualButton.textContent='Enter address manually';
  manualButton.onclick=()=>{fallback('Enter the full street address, city and state.');address.focus()};
  target.append(label,lookup,manualButton);
  manual.hidden=true;
  status.textContent='Type a street address, then select the match. Add the city to narrow results.';
  let selection=0;
  lookup.addEventListener('gmp-select',async ({placePrediction})=>{
   const request=++selection;
   try{
    const place=placePrediction.toPlace();
    await place.fetchFields({fields:['id','formattedAddress']});
    if(!lookup.isConnected||request!==selection)return;
    if(!place.formattedAddress)throw new Error('Missing address');
    address.value=place.formattedAddress;
    form.elements.addressSource.value='google-places';
    form.elements.placeId.value=place.id;
    fallback('Google Places address selected. Add a suite or unit if needed.');
    address.focus();
   }catch{if(lookup.isConnected&&request===selection)fallback('Google couldn’t load that address. Enter it manually.')}
  });
  lookup.addEventListener('gmp-error',()=>fallback('Google Places couldn’t load suggestions. Enter the address manually.'));
  form.addEventListener('submit',event=>{
   if(!lookup.isConnected||address.value)return;
   event.preventDefault();event.stopImmediatePropagation();
   status.textContent='Select a Google suggestion or choose Enter address manually.';
   lookup.focus();
  },true);
  address.required=false;
 }catch{if(target.isConnected)fallback('Google Places is unavailable. Enter the address manually.')}
}

/* Retired: the prototype generator used to run on its own server on port 8092, so every
 * live-generation hook also doubled as an origin check. That server is gone and the engine
 * now runs inside this app (review.js drives it through RM.buildCampaign / RM.posts /
 * RM.approveAll / RM.launch), so this gate is false everywhere and the hooks below stay on
 * the local demo path. Left in place deliberately: it is the honest fallback, not a bug.
 */
// A signed-in client runs the real thing: the boost is created through the API and the
// campaign engine lives inside this app. Signed-out visitors keep the demo path. (The old
// build was gated on the page being served from a standalone test server on 127.0.0.1:8092,
// which is why a real campaign was never created from the UI.)
function liveCampaignsAvailable(){return !!(window.RM&&RM.isLoggedIn())}
async function campaignEngineAvailable(){return liveCampaignsAvailable()}
// The first connected ad account, or null. The launch step needs one; building does not.
async function firstAdAccountId(){
 try{
  const rows=await RM.adAccounts();
  const list=Array.isArray(rows)?rows:(rows&&(rows.accounts||rows.items))||[];
  const real=list.find(a=>a&&a.id!=null&&!a.simulated)||list.find(a=>a&&a.id!=null);
  return real?real.id:null;
 }catch{return null}
}
async function startCampaignScope(button){
 if(button.disabled)return;button.disabled=true;
 const account=state,submitted={...draft};
 const live=await campaignEngineAvailable();
 if(state!==account||!modal.open||!button.isConnected)return;
 if(!live){
  button.disabled=false;
  confirmDemoCampaignCredit(button);return
 }
 show(`<span class="eyebrow">SETTING UP YOUR CAMPAIGN</span><h2>Resmara is preparing your campaign.</h2><div class="audit-track campaign-build-track"><span class="robot-avatar" aria-hidden="true"></span></div><p role="status">Saving the listing to your workspace and linking your ad account…</p>`);
 const progress=modal.querySelector('[role="status"]');
 try{
  const adAccountId=await firstAdAccountId();
  const boost=await RM.createBoost({address:submitted.address,campaign_days:14,ad_budget_usd:50,ad_account_id:adAccountId,property_facts:[submitted.facts,submitted.url?'Listing: '+submitted.url:''].filter(Boolean).join('\n')||undefined});
  if(!boost||boost.id==null)throw new Error('The API did not return a campaign id.');
  // Bring the gallery in now: a post can only show a photo that exists as an asset, so an
  // empty gallery here means a text-only calendar later. A bot-walled listing is not fatal.
  if(progress?.isConnected)progress.textContent='Finding the photos on your listing…';
  try{
   const pulled=await RM.importPhotos(boost.id,{listingUrl:submitted.url||undefined,urls:[...(submitted.photos||[])].slice(0,20),limit:20});
   if(progress?.isConnected&&pulled&&pulled.imported)progress.textContent='Imported '+pulled.imported+' listing photos. Linking your ad account…';
  }catch(photoError){/* keep going: the photos can be added from the campaign page */}
  liveCampaignsSyncedAt=0;
  if(state===account&&state.clientSignedIn&&modal.open&&progress?.isConnected)saveDraft({...submitted,creditUsed:1,scopeFirst:true,liveGeneration:true,boostId:boost.id,adAccountId:adAccountId||undefined});
 }catch(error){
  if(state===account&&modal.open&&progress?.isConnected){
   show(`<h2>We could not set up the campaign</h2><p>${esc(error.message)}</p><p>Nothing was charged and nothing was saved.</p><button class="alt" onclick="reviewDraft()">Try again</button>`);
  }
 }
}

/* --- Support: the client's side of the support desk -------------------------
 * The Support page and the in-page assistant both go through RM.createTicket /
 * RM.tickets, so a question the guided answers cannot cover becomes a real ticket the
 * operator answers in the console - instead of a dead end that says "not connected".
 */
function supportSignedIn(){return !!(window.RM&&RM.isLoggedIn())}
function supportPage(){
 const signedIn=supportSignedIn();
 $('#content').innerHTML=`<div class="welcome"><h1>Support.</h1></div>
 ${signedIn?'':'<div class="notice">Requests live in your workspace, so sign in first and we can see which campaign you mean and answer you in the same place.</div>'}
 <div class="grid2">
  <div class="panel"><span class="eyebrow">OPEN A REQUEST</span><h3>Tell us what you need.</h3>
   <label class="field">Subject<input id="ticketSubject" maxlength="120" placeholder="e.g. Instagram post failed on day 1"></label>
   <label class="field">Message<textarea id="ticketMessage" rows="5" maxlength="4000" placeholder="What happened, and what did you expect instead?"></textarea></label>
   <p class="fine" id="ticketFormMsg" role="status"></p>
   <button class="campaign-primary" onclick="${signedIn?'submitTicket()':'toast(\'Sign in first so we can answer you in your workspace.\')'}">Send request</button>
   ${signedIn?'':'<button class="alt" onclick="clientAccess()" style="margin-left:8px">Sign in</button>'}
  </div>
  <div class="panel"><span class="eyebrow">YOUR REQUESTS</span><h3>What we have from you.</h3>
   <div id="ticketList">${signedIn?'<p class="fine">Loading your requests…</p>':'<p class="fine">Sign in to see your requests and our replies.</p>'}</div>
  </div>
 </div>`;
 if(signedIn)loadMyTickets();
}
async function loadMyTickets(){
 const box=document.querySelector('#ticketList');if(!box)return;
 try{
  const rows=await RM.tickets();
  if(!rows.length){box.innerHTML='<p class="fine">Nothing yet. Anything you send appears here with our reply.</p>';return}
  box.innerHTML=rows.map(t=>`<article class="panel" style="margin:0 0 12px">
   <div class="flex"><b>${esc(t.subject)}</b><span class="pill">${esc(t.status)}</span></div>
   <p class="fine">Request #${esc(t.id)} · raised ${esc(String(t.created_at||'').replace('T',' ').slice(0,16))} UTC</p>
   ${(t.messages||[]).map(m=>`<div class="${m.unread?'ticket-msg-new':''}" style="border-left:2px solid ${m.unread?'#e8892b':'#c7e2f2'};padding-left:10px;margin:8px 0">
     <span class="eyebrow">${esc(m.from||'')}${m.unread?' · NEW':''}</span><p style="white-space:pre-wrap;margin:2px 0 0">${esc(m.text||'')}</p></div>`).join('')}
  </article>`).join('');
  // Opening this page is reading the replies: clear the badge server-side so it stays
  // cleared in the next browser too, not just this tab. The list above was drawn before the
  // clear, so the NEW marker on it is turned off by hand afterwards — the reply is still
  // worth seeing marked once, it just must not stay marked after being read.
  if(RM.markSupportRead)RM.markSupportRead().then(()=>{
    state.supportUnread=0;persist();if(typeof paintSupportBadge==='function')paintSupportBadge();
    document.querySelectorAll('#ticketList .ticket-msg-new').forEach(el=>{
      el.classList.remove('ticket-msg-new');el.style.borderLeftColor='#c7e2f2';
      const tag=el.querySelector('.eyebrow');if(tag)tag.textContent=tag.textContent.replace(/\s*·\s*NEW$/,'');
    });
  }).catch(()=>{});
 }catch(error){
  const detail=(error&&error.status===401)?'Sign in to see your requests.':((error&&error.message)||'Could not load your requests.');
  box.innerHTML='<p class="fine">'+esc(detail)+'</p>';
 }
}
async function submitTicket(){
 const subject=(document.querySelector('#ticketSubject')||{}).value||'';
 const message=(document.querySelector('#ticketMessage')||{}).value||'';
 const msg=document.querySelector('#ticketFormMsg');
 const say=(text,cls)=>{if(msg){msg.className='fine '+(cls||'');msg.textContent=text}};
 if(!supportSignedIn())return say('Sign in first - a request is attached to your workspace.','bad');
 if(!subject.trim()||!message.trim())return say('A subject and a message, please.','bad');
 say('Sending…');
 try{
  const t=await RM.createTicket(subject.trim(),message.trim());
  say('Sent as request #'+t.id+'. The answer appears on this page.','ok');
  document.querySelector('#ticketSubject').value='';
  document.querySelector('#ticketMessage').value='';
  loadMyTickets();
 }catch(error){say('Not sent: '+((error&&error.message)||'unknown error'),'bad')}
}
function pipOfferTicket(q){
 const panel=document.querySelector('#pip-messages');if(!panel)return;
 const wrap=document.createElement('div');wrap.className='pip-reply';
 const lead=document.createElement('p');lead.textContent='I don’t have an answer for that yet. Send it to the team and a person will reply on your Support page, and I’ll learn the answer for next time.';
 wrap.append(lead);
 const btn=document.createElement('button');btn.type='button';btn.className='alt';btn.textContent='Send to support';
 btn.addEventListener('click',async()=>{
  if(!supportSignedIn()&&typeof supportDemoMode==='function'&&supportDemoMode()){const t={id:1043+demoTickets().length,subject:String(q||'').slice(0,120)||'Question from the Resmara assistant',status:'Open',created_at:new Date().toISOString(),messages:[{from:'You',text:String(q||'')}]};demoTickets().unshift(t);persist();pipMessage('Sent to the team as request #'+t.id+'. We’ll email you, and the reply will show on your Support page.');btn.remove();return}
  if(!supportSignedIn()){pipMessage('Sign in first - a request is attached to your workspace, and the reply lands on your Support page.');return}
  btn.disabled=true;btn.textContent='Sending…';
  try{
   const t=await RM.createTicket(String(q||'').slice(0,120)||'Question from the Resmara assistant',String(q||''));
   pipMessage('Sent as request #'+t.id+'. The answer will appear on your Support page.');
   btn.remove();
  }catch(error){btn.disabled=false;btn.textContent='Send to support';pipMessage('Could not send that: '+((error&&error.message)||'unknown error'))}
 });
 wrap.append(btn);panel.append(wrap);wrap.scrollIntoView({block:'nearest'});
}


// ---- Meta connection (real, not the demo walkthrough) ----------------------
// The browser leaves the app for Facebook's consent screen and comes back through
// /api/oauth/meta/callback, which redirects to the app root with ?meta=… .
// One line per account, saying what Meta currently thinks of it: whether our access still
// works, and whether the customer's own card is on the account that pays for the ads.
// Nothing here is guessed - an unmeasured status says so.
function accountHealthLine(a){
 if(a.needs_reconnect)return 'Needs reconnecting: '+(a.token_note||'Meta will not accept this connection any more.');
 if(a.token_status==='simulated')return 'Demo connection — no Meta account is used and nothing is billed.';
 if(!a.token_status)return 'Not checked yet — run Check connection.';
 if(a.token_status==='expiring')return 'Access expires soon — '+(a.token_refresh_note||a.token_note||'reconnect before it does')+'.';
 const bits=['Access valid'];
 if(a.token_expires_at)bits.push('until '+String(a.token_expires_at).slice(0,10));
 if(a.funding_status==='has_funding')bits.push('payment method on file — the client is billed by Meta directly');
 else if(a.funding_status==='no_funding')bits.push('no payment method on the ad account — ads cannot run until one is added in Meta');
 else bits.push('payment method not checked yet');
 bits.push('ad account '+(a.account_status_label||'status not read'));
 return bits.join(' · ');
}
function loadConnections(){
 RM.adAccounts().then(rows=>{
  const list=(Array.isArray(rows)?rows:[]).filter(a=>a.platform==='meta');
  const n=$('#connNotice'),d=$('#connDetail'),h=$('#connHealth');if(!n)return;
  const live=list.filter(a=>a.is_active!==false);
  if(live.length){
   const broken=live.filter(a=>a.needs_reconnect);
   n.textContent=live.length+' Meta ad account'+(live.length>1?'s':'')+' connected to your account.'
    +(broken.length?' — '+broken.length+' need'+(broken.length>1?'':'s')+' reconnecting.':'');
   if(d)d.textContent=live.map(a=>(a.account_name||a.advertiser_id)+' ('+a.advertiser_id+', '+a.currency+')').join(' · ');
   if(h){h.hidden=false;h.innerHTML=live.map(a=>'<b>'+esc(a.account_name||a.advertiser_id)+'</b>: '+esc(accountHealthLine(a))).join('<br>');}
  }else{
   n.textContent='No Meta account is connected yet. Connect one to post and run ads.';
   if(d)d.textContent='Choose the account you want to use for property marketing.';
   if(h)h.hidden=true;
  }
 }).catch(e=>{const n=$('#connNotice');if(n)n.textContent='Could not read your connections: '+e.message;});
}
// Ask the backend - and through it, Meta - for the current state of every connection.
function checkConnections(){
 if(!RM.isLoggedIn()){toast('Sign in first');return;}
 const b=$('#metaCheckBtn');if(b){b.disabled=true;b.textContent='Checking…';}
 const done=()=>{if(b){b.disabled=false;b.textContent='Check connection';}loadConnections();};
 RM.checkConnections().then(r=>{
  const broken=(r&&r.needs_reconnect)||[],unfunded=(r&&r.not_ready_to_spend)||[];
  if(broken.length)toast('Reconnect needed: '+broken.join(', '));
  else if(unfunded.length)toast('Ad account cannot run ads yet: '+unfunded.join(', '));
  // One button does both checks: the login and ad account (above), then the readiness checklist
  // (Page, admin rights, Instagram, payment), which says "You're ready" itself when all is well.
 }).catch(()=>{}).then(()=>{done();if(typeof runMetaAudit==='function')runMetaAudit();});
}
function connectMeta(){
 // No session, no consent: send them to the sign-in form instead of letting the request
 // come back 401 and reporting that as a Meta problem.
 if(!RM.isLoggedIn()){toast('Sign in first — then Connect Meta.');if(window.clientAccess)clientAccess('signin');return;}
 const b=$('#metaConnectBtn');if(b){b.disabled=true;b.textContent='Opening Facebook…';}
 const reset=()=>{if(b){b.disabled=false;b.textContent='Connect Meta';}};
 RM.metaConnect().then(r=>{
  if(r&&r.redirect_url){location.href=r.redirect_url;return;}
  reset();
  toast(r&&r.demo_mode?'Meta is not configured on the server yet.':'Meta did not return a consent link.');
 }).catch(e=>{
  reset();
  if(e&&e.status===401){toast('Your session ended — sign in again, then Connect Meta.');if(window.clientAccess)clientAccess('signin');return;}
  toast('Could not start the Meta connection: '+(e&&e.message?e.message:'unknown error'));
 });
}
// Landing back from Meta: say what actually happened, then open the connections page.
function metaReturnNotice(){
 const p=new URLSearchParams(location.search),m=p.get('meta');if(!m)return;
 const n=document.createElement('div');n.className='notice connection-notice';
 if(m==='connected')n.textContent='Meta connected — '+p.get('accounts')+' ad account(s) and '+p.get('pages')+' Page(s) authorised.';
 else if(m==='no_accounts')n.textContent='Meta authorised, but this login can see no ad accounts. Add the ad account to the Meta app, or connect a login that owns it.';
 else n.textContent='Meta connection failed: '+(p.get('reason')||m);
 document.body.prepend(n);
 history.replaceState(null,'',location.pathname+location.hash);
 if(RM.isLoggedIn()){state.clientSignedIn=true;state.name=state.name||'there';persist();dashboard('accounts');}
}
window.addEventListener('load',()=>{try{metaReturnNotice();}catch(e){}});
