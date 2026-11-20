// Local interaction prototype based on the Boost workflow. No engine requests or external side effects.
var ReviewStudio={active:0,building:new WeakSet()};
function reviewCampaign(){return [...state.campaigns,...examples][ReviewStudio.active]}
function reviewCampaignBoostId(){return campaignBoostId(reviewCampaign())}
// Real listing-photo count for a backend-backed campaign (falls back to nothing in the demo).
/* The strip is the engine's shortlist, not a folder listing: strongest-selling photo first, each
 * thumb labelled with the space it shows. An owner who sees the kitchen on post 3 should find the
 * kitchen at the top of this strip, not wherever the camera wrote it. */
async function refreshPhotoAssets(){
 const node=document.querySelector('.campaign-photos [data-photo-count]');if(!node)return;
 const boostId=reviewCampaignBoostId();if(boostId==null||!window.RM||!window.RM.gallery){node.textContent='No photos on this campaign yet. Import them from your listing link or upload them.';return}
 try{
  const data=(await RM.gallery(boostId))||{};
  const photos=(Array.isArray(data.photos)?data.photos:[]).filter(a=>(a.kind||'photo')==='photo');
  if(!photos.length){node.textContent='No photos on this campaign yet. Import them from your listing link or upload them.';const empty=document.querySelector('[data-photo-thumbs]');if(empty)empty.innerHTML='';return}
  const tagged=photos.filter(p=>p.room);
  const rooms=new Set(tagged.filter(p=>p.usable!==false).map(p=>p.room)).size;
  node.textContent=photos.length+' listing photo'+(photos.length===1?'':'s')
    +(tagged.length===photos.length&&rooms
      ? ' on this campaign · '+rooms+' different space'+(rooms===1?'':'s')+' · in the order Resmara will use them, best first.'
      : ' uploaded. Resmara reads each one when it builds — that is when the spaces are labelled and the strongest shot leads.');
  const strip=document.querySelector('[data-photo-thumbs]');
  // Every thumb carries its own remove: a second campaign on this listing is meant to run
  // different photos, and without this the inherited gallery could only grow.
  if(strip)strip.innerHTML=photos.map((a,i)=>'<figure class="photo-thumb'+(a.usable===false?' unusable':'')+'">'
    +'<img src="'+esc(mediaPath(a.url))+'" alt="'+esc(a.room||a.original_name||'Listing photo')+'" loading="lazy">'
    +'<button type="button" class="photo-remove" title="Remove this photo from this campaign" aria-label="Remove photo '+esc(a.room||a.original_name||String(i+1))+'" onclick="removeCampaignPhoto('+Number(a.id)+',this)">×</button>'
    +'<figcaption><b>'+(i+1)+'</b>'+(a.room?' '+esc(a.room):'')+(a.score!=null?' · '+esc(String(a.score)):'')+'</figcaption></figure>').join('');
 }catch(e){node.textContent='Could not read this campaign’s photos. Refresh and try again.'}
}
async function removeCampaignPhoto(assetId,button){
 const boostId=reviewCampaignBoostId();
 if(boostId==null||!window.RM||!window.confirm('Remove this photo from this campaign? The listing and any other campaign keep it.'))return;
 if(button)button.disabled=true;
 const status=document.querySelector('[data-photo-status]');
 try{
  await RM.deletePhoto(assetId);
  await refreshPhotoAssets();
  if(status)status.textContent='Photo removed. Rebuild the campaign and the calendar is re-planned from the photos that are left.';
 }catch(e){
  if(button)button.disabled=false;
  if(status)status.textContent=(e&&e.message)||'Could not remove that photo.';
 }
}
/* Photos the engine can actually use. Posts carry an image only when the plan names an
 * Asset, so this panel is the difference between a photo calendar and a text one. */
function photosPanel(r){
 const boostId=reviewCampaignBoostId();
 if(boostId==null)return '';
 const listing=String((r.scope&&r.scope.listing)||'');
 const seed=/^https?:\/\//i.test(listing)?esc(listing):'';
 return '<section class="panel campaign-photos"><h2 class="campaign-step-title">Listing photos</h2>'
  +'<p class="photos-status" data-photo-count>Loading your photos…</p>'
  +'<div class="photo-thumbs" data-photo-thumbs></div>'
  +'<p class="photos-help">Resmara pulls the photos from your listing link. If it misses any, or the link doesn’t work, upload them yourself.</p>'
  +'<div class="photos-row"><input id="photo-listing-url" type="url" inputmode="url" aria-label="Listing link" placeholder="Paste your listing link" value="'+seed+'">'
  +'<button class="campaign-primary" type="button" onclick="importListingPhotos(this)">Import photos</button>'
  +'<label class="alt button-like photos-upload">Upload photos<input class="photos-file" type="file" accept="image/jpeg,image/png,image/webp" multiple onchange="uploadCampaignPhotos(this)"></label></div>'
  +'<p class="fine" role="status" data-photo-status></p>'
  // The agent ticks this before Build, and the server stores the timestamp. It is their
  // signature that they may use the photographs, so the box is not pre-ticked.
  +'<label class="photo-permission"><input type="checkbox" id="photoPermission" onchange="photoPermissionChanged()"><span>I have permission to use these photos for this campaign’s posts and ads.</span></label>'
  +'</section>';
}
async function importListingPhotos(button){
 const boostId=reviewCampaignBoostId();if(boostId==null||!window.RM)return;
 const field=document.getElementById('photo-listing-url');
 const status=document.querySelector('[data-photo-status]');
 const url=((field&&field.value)||'').trim();
 if(!/^https?:\/\//i.test(url)){if(status)status.textContent='Paste the full listing link first.';if(field)field.focus();return}
 button.disabled=true;if(status)status.textContent='Pulling the gallery from that page…';
 try{
  const res=await RM.importPhotos(boostId,{listingUrl:url,limit:60});
  const n=(res&&res.imported)||0;
  if(status)status.textContent=n
   ?'Imported '+n+' photo'+(n===1?'':'s')+'. Rebuild the campaign to put them in the calendar.'
   :(res&&res.detail)||'No photos found on that page. Try direct image links or uploads.';
  await refreshPhotoAssets();
 }catch(e){if(status)status.textContent=e.message}
 finally{button.disabled=false}
}
async function uploadCampaignPhotos(input){
 const boostId=reviewCampaignBoostId();if(boostId==null||!window.RM)return;
 const files=[...(input.files||[])];if(!files.length)return;
 const status=document.querySelector('[data-photo-status]');
 if(status)status.textContent='Uploading '+files.length+' photo'+(files.length===1?'':'s')+'…';
 let ok=0,failed=[];
 // A photo that fails to upload must be named, not counted. An owner who drops 61 files and
 // reads "Uploaded 56" has no way to know which five to send again.
 for(const file of files){
  try{await RM.uploadPhoto(file,boostId,'photo');ok++}
  catch(e){failed.push(file.name+(e&&e.message?' ('+e.message+')':''))}
 }
 if(status)status.textContent=ok
  ?('Uploaded '+ok+(failed.length?' — '+failed.length+' did not go: '+failed.slice(0,3).join(', ')+(failed.length>3?', and '+(failed.length-3)+' more':''):'')+'. Rebuild the campaign to put them in the calendar.')
  :('Upload failed for '+failed.length+' photo'+(failed.length===1?'':'s')+(failed.length?' — '+failed[0]:'')+'.');
 input.value='';await refreshPhotoAssets();
}
// A live campaign's calendar must show what the backend actually stored. Opening a campaign
// in a browser that has never built it used to leave the demo tiles (stock photos, made-up
// captions) on screen, which reads as "the photos never made it". Silent: no toast, and it
// only repaints when something really changed, so it cannot loop with details().
async function hydrateReviewItems(r){
 const id=(typeof reviewCampaignBoostId==='function')?reviewCampaignBoostId():null;
 if(id==null||!window.RM||!RM.posts||!r||r._hydrating)return;
 r._hydrating=true;
 try{
  const posts=await RM.posts(id);
  if(!Array.isArray(posts)||!posts.length)return;
  const mapped=posts.map(post=>({id:post.id,postId:post.id,day:post.day||1,
   title:post.title||String(post.caption||'Scheduled post').split(/[.\n]/)[0].slice(0,42)||'Scheduled post',
   kicker:post.kicker||'',overlay:post.overlay_text||'',room:post.photo_room||'',
   kind:post.kind==='short_video'?'Video post':'Photo post',caption:post.caption||'',
   image:post.image_url||'',reviewed:post.client_status==='approved',publishStatus:post.publish_status||'',
   time:(post.publish_at||'').slice(11,16)||undefined}));
  const key=items=>items.map(x=>[x.id,x.day,x.image,x.title,x.overlay].join('|')).join(',');
  if(key(mapped)===key(r.items))return;
  r.items=mapped;r.needsBuild=false;persist();
  if(activeReview()===r&&ReviewStudio.active!=null)details(ReviewStudio.active);
 }catch(e){}finally{r._hydrating=false}
}
// A campaign that exists on the server is keyed by its id, not its position: the position
// moves as campaigns are added, so a live campaign at index 0 was opening with a demo
// campaign's saved address at the top of the page.
function reviewKey(c,index){const id=campaignBoostId(c);return 'review-'+(id!=null?'boost-'+id:(c.reviewId||index));}
function details(index){document.querySelector('#content')?.classList.remove('rerun-locked');if(ReviewStudio.active!==index)ReviewStudio.month=null;ReviewStudio.active=index;const c=[...state.campaigns,...examples][index];if(!c)return;
 // Opening one campaign is its own view, not the campaign list. Leaving view='campaigns' here is
 // why building a campaign dropped the person back on the Active campaigns list: the next
 // background sync saw view==='campaigns' and repainted the list over the page they had opened.
 if(openCampaignKey!==campaignKey(c))state.folds={};view='campaign';openCampaignKey=campaignKey(c);const key=reviewKey(c,index);state.reviews=state.reviews||{};if(!state.reviews[key]||(examples.includes(c)&&state.reviews[key].v!==5))state.reviews[key]={v:5,approved:false,items:(c.scopeFirst||campaignBoostId(c)!=null)?[]:sampleReviewItems(c)};const r=state.reviews[key];if(r.videoUrl===undefined)r.videoUrl='';if(examples.includes(c)&&typeof SAMPLE_POSTS!=='undefined')(r.items||[]).forEach(it=>{if(it.image===img||it.image===img2||!it.image)it.image=demoItemImage(it.id)});r.scopeFirst=Boolean(c.scopeFirst)||(campaignBoostId(c)!=null&&!Number(c.posts_total||0)&&!r.approved);r.liveGeneration=Boolean(c.liveGeneration)||campaignBoostId(c)!=null;r.scope ||= initialCampaignScope(c);if(r.scope&&!r.scopeConfirmed&&!r.approved)r.scope.start=goLiveDate(r.scope.start);if(examples.includes(c)&&!r.scope.demoBrief&&!r.scopeConfirmed&&!r.approved){r.scope.highlights ||= demoPropertyHighlights(c);r.scope.demoBrief=true;}const live=typeof campaignIsLive==='function'&&campaignIsLive(c);if(live&&examples.includes(c)){r.scopeConfirmed=true;r.calendarApproved=true;r.approved=true}$('#content').innerHTML=`<div class="review-heading"><h1>${esc(campaignBoostId(c)!=null?c.address:(r.scope.address||c.address))}</h1></div>${live?leadsPanel(c,index)+'<div class="live-cal">'+liveCalendar(reviewCalendar(r,c))+'</div>'+(typeof listingPagePanel==='function'?listingPagePanel(c,index):''):campaignScopePanel(r)+photosPanel(r)+reviewCalendar(r,c)}${live?'':`<div class="review-approval"><div><h2 class="campaign-step-title"><span>3</span> ${r.approved?'Campaign approved':'Approve the campaign'}</h2><p>Approve the full calendar when you’re happy with the creative.</p><p class="fine">${r.approved?'Approval saved. Nothing has been published.':!r.items.length?'Confirm your launch details to build the calendar.':r.items.filter(i=>i.reviewed).length+' of '+r.items.length+' items spot-checked · Individual review is optional. Confirm your launch details and approve the calendar first.'}</p></div>${r.approved?'<button onclick="launchOrder()">Review launch</button>'+(reviewCampaignBoostId()!=null?' <button class="alt" onclick="publishApprovedPosts()">Publish approved posts</button>':''):`<button class="campaign-primary scope-approval-button" onclick="approveReview()" ${r.scopeConfirmed&&r.calendarApproved&&r.items.length?'':'disabled'}>Approve entire campaign</button>`}</div>`}<section class="panel${live?' live-reports':''}">${live?'<h2 class="campaign-step-title"><span>4</span> Reports for this property</h2>':'<h3>Reports for this property</h3>'}<div class="pr-picks">${[7,14].map(day=>Number(c.day)>=day?`<button type="button" class="pr-pick" onclick="openPropertyReport(${index},${day},this)"><b>Day ${day} report</b><small>Ready · click to open</small></button>`:`<div class="pr-pick off"><b>Day ${day} report</b><small>${c.day?'Ready on day '+day:'Ready after launch'}</small></div>`).join('')}</div><div id="pr-view"></div></section>`;refreshPhotoAssets();hydrateReviewItems(r);persist();if(live&&typeof setupFolds==='function')setupFolds();if(typeof campaignPhase==='function'&&campaignPhase(c)==='completed'&&!c.rerunPaid)showRerunOffer(index)}
function sampleReviewItems(c){
 // One ad for the whole campaign. If the listing link had a video, the ad is a video ad and
 // the video is also the first post (day 1). Otherwise the ad is a photo ad and every post is a photo.
 const vid=!!c.hasVideo,titles=['Just listed','Property highlights','Step inside','Room spotlight','The details','A closer look','Weekend viewing','Around town','Design details','Living spaces','Key features','Viewing reminder','Outdoor living','Final spotlight'];
 const P=typeof SAMPLE_POSTS!=='undefined'?SAMPLE_POSTS:[];const cards=[6,0,2,8,13].map(k=>P[k]&&P[k].img).filter(Boolean);
 const ad={id:0,day:1,title:vid?'Video ad':'Photo carousel ad',kind:'Meta ad',adType:vid?'video':'carousel',caption:campaignSampleCaption(c,0),image:vid?'sample/card-1.jpg':(cards[0]||demoItemImage(0)),images:vid?[]:cards,reviewed:false};
 const posts=titles.map((t,k)=>({id:k+2,day:k+1,title:k===0&&vid?'Video tour':t,kind:k===0&&vid?'Video post':'Photo post',caption:campaignSampleCaption(c,k+2),image:k===0&&vid?'sample/card-1.jpg':demoItemImage(k+2),reviewed:false}));
 return [ad,...posts];
}
// Demo campaigns use the sample home's designed posts, not the illustration.
function demoItemImage(i){const P=typeof SAMPLE_POSTS!=='undefined'?SAMPLE_POSTS:null;if(!P)return i%3===0?img2:img;return i<2?P[(SAMPLE_AD.creativeDays||[7])[0]-1].img:P[(i-2)%14].img}
/* The review for the open campaign, looked up the same way details() stores it. For a campaign
 * that came from the API there is no reviewId in the browser, so a reviewId-only lookup returned
 * undefined and every button in the launch-details step threw before it could do anything -
 * another way "Confirm details" and "Build content" did nothing at all. */
function activeReview(){const c=[...state.campaigns,...examples][ReviewStudio.active]||{};return state.reviews[reviewKey(c,ReviewStudio.active)]}
function reviewCheck(k,v){const r=activeReview();if(r.approved)return;r[k]=v;persist()}
function editCampaignItem(i){
 const r=activeReview(),it=r.items[i],slot=reviewSlot(r,it),brand=r.brandProfile||campaignBrandProfile();
 const locked=r.approved||r.calendarApproved,disabled=locked?'disabled':'',ad=it.kind==='Meta ad';const isVid=it.kind==='Video post'||(ad&&it.adType==='video');const firstPost=!ad&&it.day===Math.min(...r.items.filter(x=>x.kind!=='Meta ad').map(x=>x.day));const showVid=false; // Video is parked until after launch.
 show(`<span class="eyebrow">${esc(it.kind)} · ${ad?'Days 1–14':'Day '+it.day}</span><h2>${esc(it.title)}</h2>${showVid?`<label class="field video-link-field">Link to video<input form="post-form" name="videoUrl" type="url" placeholder="Paste a Dropbox, Google Drive, Fotello or Aryeo video link" value="${esc(r.videoUrl||'')}" ${disabled}></label><p class="fine">${r.videoUrl?'Found in your listing link. Your video runs as the ad and goes out once as your first post.':'No video in your listing link. Paste one to use it for your ad and first post. Without one, they use photos.'}</p>`:''}<div class="ei-split"><div class="ei-media"><div class="review-preview" style="--agent-colour:${/^#[0-9a-f]{6}$/i.test(brand.colour)?brand.colour:'#143a50'}">${ad&&it.images&&it.images.length>1?carouselViewer(it.images):isVid?`<span class="creative-frame video-thumb"><img src="${esc(mediaPath(it.image))}" alt="Video thumbnail"><span class="play-btn" aria-hidden="true">▶</span></span><p class="fine">Video: the thumbnail is taken from your video, with no text added.</p>`:it.image?(/sample\/post-|designed/.test(it.image)||it.designed?`<span class="creative-frame designed"><img src="${esc(mediaPath(it.image))}" alt="Designed post"></span>`:`<span class="creative-frame"><img src="${esc(mediaPath(it.image))}" alt="Campaign creative">${it.overlay?`<em class="post-overlay">${esc(it.overlay)}</em>`:''}${it.kicker?`<span class="post-kicker">${esc(it.kicker)}</span>`:''}</span>`):'<p class="fine">No photo selected yet.</p>'}</div>${it.room?`<p class="fine">Photo: ${esc(it.room)} — the copy above is written for this photo.</p>`:''}</div><div class="ei-side"><p class="sp-when">◷ ${esc(reviewDateLabel(slot.date,slot.time,r.scope.zone))}</p><p class="fine">${esc(it.visualBrief||'Sample creative preview.')}</p><form id="post-form" onsubmit="event.preventDefault();saveReviewItem(${i},this)"><label class="field">Title<input name="title" required value="${esc(it.title)}" ${disabled}></label><label class="field">Caption<textarea name="caption" required ${disabled}>${esc(it.caption)}</textarea></label>${locked?'':`${isVid?'':'<label class="field">Upload a replacement photo<input name="photo" type="file" accept="image/*"></label><p class="fine">Resmara resizes and compresses it to a JPEG so it’s ready for Instagram and Facebook.</p>'}${ad?'':`<label class="field">Publishing date<input name="publishDate" type="date" required min="${esc(r.scope.start)}" max="${esc(reviewSlot(r,{day:14}).date)}" value="${esc(slot.date)}"></label><label class="field">Publishing time (${esc(r.scope.zone)})<input name="publishTime" type="time" required value="${esc(slot.time)}"></label><p class="fine">Choosing a date with another post swaps their slots.</p>`}`}<p class="fine" role="alert"></p><div class="modal-actions"><button type="button" class="nc-cancel" onclick="modal.close()">Close</button>${locked?downloadPostButton(it,i)+withdrawButton(it,i):'<button>Save and mark reviewed ✓</button>'}</div></form></div></div>`);
}
function postDay(r,date){
 const day=1+(Date.parse(date)-Date.parse(r.scope.start))/86400000;
 return Number.isInteger(day)&&day>=1&&day<=14?day:null;
}
function moveReviewPost(r,index,date){
 const item=r.items[index],day=postDay(r,date);
 if(!item||item.kind==='Meta ad'||!day||r.approved||r.calendarApproved)return false;
 const origin=reviewSlot(r,item);
 if(origin.date===date)return false;
 const other=r.items.find(post=>post!==item&&post.kind!=='Meta ad'&&reviewSlot(r,post).date===date);
 const time=reviewSlot(r,other||{day}).time;
 if(other)Object.assign(other,{day:postDay(r,origin.date),date:origin.date,time:origin.time,reviewed:false});
 Object.assign(item,{day,date,time,reviewed:false});
 return true;
}
function dropReviewPost(event,date){
 event.preventDefault();
 const value=event.dataTransfer.getData('application/x-resmara-post');
 if(!/^\d+$/.test(value))return;
 const r=activeReview();
 if(moveReviewPost(r,Number(value),date)){persist();details(ReviewStudio.active);toast('Posting order updated.')}
}
async function saveReviewItem(i,form){
 const r=activeReview(),item=r.items[i],button=form.querySelector('button:not([type])'),error=form.querySelector('[role="alert"]');
 if(!item||r.approved||r.calendarApproved||button.disabled)return;
 button.disabled=true;error.textContent='';
 const before=r.items.map(post=>({...post}));
 try{
  const file=form.elements.photo?.files[0];
  const image=file?await compressToJpeg(file):item.image;
  if(!form.isConnected||!modal.open||activeReview()!==r||r.approved||r.calendarApproved)return;
  const date=form.elements.publishDate?.value,time=form.elements.publishTime?.value;
  const oldTime=reviewSlot(r,item).time;
  if(date)moveReviewPost(r,i,date);
  if(form.elements.videoUrl)applyCampaignVideo(r,form.elements.videoUrl.value.trim());
  Object.assign(item,{title:form.elements.title.value,caption:form.elements.caption.value,image,reviewed:true});
  if(time&&(!date||date===reviewSlot(r,before[i]).date||time!==oldTime))item.time=time;
  // Approving this post is a backend call when the campaign is backed by a real boost.
  const boostId=reviewCampaignBoostId(),postId=item.postId??item.post_id;
  if(window.RM&&boostId!=null&&postId!=null){
   try{await RM.approvePost(postId)}
   catch(e){r.items=before;throw new Error('Couldn’t approve this post: '+e.message)}
  }
  // A replacement photo uploads to the backend boost; the local preview stands either way.
  if(window.RM&&boostId!=null&&file){
   try{const blob=await (await fetch(image)).blob();await RM.uploadPhoto(new File([blob],'photo.jpg',{type:'image/jpeg'}),boostId,'photo')}catch{}
  }
  try{localStorage.setItem('resmara',JSON.stringify(state))}catch{
   r.items=before;
   throw new Error('This browser couldn’t save the change. Try a smaller photo.');
  }
  modal.close();details(ReviewStudio.active);
 }catch(e){error.textContent=e.message}finally{button.disabled=false}
}
function demoPropertyHighlights(c){
 return ({
 '1248 Oakridge Drive':'Open kitchen and living area, covered outdoor seating, and a pool. Lead with the exterior and follow with the kitchen and pool.',
 '76 Willow Lane':'Bright living room, updated kitchen, and a private backyard. Lead with the front exterior and the main living spaces.',
 '309 Cedar House':'Spacious grounds and an outdoor entertaining area. Use a wide exterior first, then show the living areas and grounds.'
 })[c.address]||'';
}
function nextCampaignDate(){
 const date=new Date();date.setDate(date.getDate()+1);
 return [date.getFullYear(),String(date.getMonth()+1).padStart(2,'0'),String(date.getDate()).padStart(2,'0')].join('-');
}
function todayDate(){
 const date=new Date();
 return [date.getFullYear(),String(date.getMonth()+1).padStart(2,'0'),String(date.getDate()).padStart(2,'0')].join('-');
}
/* A go-live date that has already passed is not a launch, it is a dead button. The date input
 * carries min=today, so a scope holding last week's date makes the whole form invalid and the
 * browser refuses the submit: pressing "Confirm details" then does nothing at all - no toast,
 * no request, no error. A draft that outlives its own go-live date rolls forward to the next
 * free day instead of becoming unclickable. */
function goLiveDate(value){
 const date=String(value||'').slice(0,10);
 return /^\d{4}-\d{2}-\d{2}$/.test(date)&&date>=todayDate()?date:nextCampaignDate();
}
function dateLabel(value){
 const d=new Date(String(value||'')+'T12:00:00');
 return Number.isNaN(d.getTime())?String(value||''):d.toLocaleDateString(undefined,{month:'short',day:'numeric'});
}
function initialCampaignScope(c){
 return {address:c.address,listing:c.url||'',media:c.media||'',facts:c.research?.facts||c.area||'',highlights:c.research?.highlights||'',photoPlan:c.research?.photoPlan||'Prioritize front and rear exterior, kitchen, living room and standout features. Include a pool, waterfront or land when present. Skip routine toilet and closet photos.',start:goLiveDate(c.start),time:'10:00',zone:c.research?.zone||(examples.includes(c)?'America/Chicago':Intl.DateTimeFormat().resolvedOptions().timeZone||'UTC'),budget:'50',destination:c.destination||''};
}
const scopeFields=[
 ['address','Property address','text'],['listing','Public listing or MLS URL','url'],['media','Photo and video gallery URL','url'],['facts','Property facts (price, beds, baths, size)','textarea'],['start','Go-live date','date'],['highlights','Standout features and location','textarea'],['photoPlan','Photo priorities and exclusions','textarea'],['budget','Meta ad budget','text'],['destination','Send clicks to','url']
];
// Step 1 is only the ad budget. The address, facts, photos and story all come from the
// listing link and the engine; the agent changes anything else on the posts themselves.
// The other scope fields still travel with the form as hidden values so nothing downstream breaks.
function campaignScopePanel(r){
 const s=r.scope,locked=r.scopeConfirmed||r.approved;
 const budget=Number(s.budget)>0?Number(s.budget):50;
 const shown=['budget','start','destination'];
 const hidden=scopeFields.filter(f=>!shown.includes(f[0])).map(([key])=>`<input type="hidden" name="${key}" value="${esc(s[key]||'')}">`).join('');
 const amounts=[...new Set([50,75,100,150,200,budget])].sort((a,b)=>a-b);
 const start=goLiveDate(s.start);
 const when=new Date(start+'T12:00').toLocaleDateString(undefined,{month:'short',day:'numeric'});
 const today=new Date().toISOString().slice(0,10);
 return `<details class="panel campaign-scope" ${locked?'':'open'}><summary class="campaign-step-title"><span>1</span> Confirm your launch details ${locked?`<small>✓ Goes live ${esc(when)} · $${budget} budget</small>`:''}</summary><form novalidate onsubmit="event.preventDefault();saveCampaignScope(this)">${hidden}<fieldset ${locked?'disabled':''} class="budget-step"><legend class="sr-only">Launch details</legend><div class="ls-grid"><div class="ls-col"><label class="scope-field">Go-live date<input name="start" type="date" required value="${esc(start)}" min="${today}"></label><p class="budget-note">The day your posts and listing ad start going out.</p></div><div class="ls-col"><label class="scope-field">Send clicks to (optional)<input name="destination" type="text" inputmode="url" placeholder="https://..." value="${esc(s.destination||'')}"></label><p class="budget-note">The page people land on when they click your posts or ad. Left blank, it’s the listing page Resmara builds for this home.</p></div><div class="ls-col"><label class="scope-field">Ad budget<select name="budget">${amounts.map(a=>`<option value="${a}" ${a===budget?'selected':''}>$${a}${a===50?' · Default':''}</option>`).join('')}</select></label><p class="budget-note">Meta bills your ad spend separately from your Resmara campaign. Our default budget is $50.</p></div></div></fieldset>${untilSoldPanel(ReviewStudio.active)}<div class="scope-form-actions">${locked?`<div class="scope-locked"><strong>✓ Goes live ${esc(when)} · $${budget} budget</strong>${r.approved?'':'<button type="button" class="alt" onclick="unlockCampaignScope()">Change details</button>'}</div>`:'<button class="campaign-primary scope-approval-button">Confirm details</button>'}</div></form></details>`;
}
function unlockCampaignScope(){
 const r=activeReview();if(r.approved||ReviewStudio.building.has(r))return;
 r.scopeConfirmed=false;r.calendarApproved=false;persist();details(ReviewStudio.active);
}
function saveCampaignScope(form){
 const r=activeReview();if(r.approved||r.scopeConfirmed)return;
 const next={},rolled=[];
 for(const [key,,type] of scopeFields){
  const field=form.elements[key];
  if(!field)continue;
  let value=String(field.value||'').trim();
  // A date that slipped into the past is moved, not refused: refusing it here is what made the
  // button look broken, because the browser's own validation message never reached the page.
  if(key==='start'){const fixed=goLiveDate(value);if(fixed!==value)rolled.push([value,fixed]);value=fixed;if(field.value!==fixed)field.value=fixed}
  next[key]=type==='url'?normalizeWebLink(value):value;
  if(next[key]===null||(['address','start'].includes(key)&&!value)){
   const label=field.closest('label');
   const name=label&&label.firstChild&&label.firstChild.textContent?label.firstChild.textContent.trim().toLowerCase():key;
   toast('Check the '+name+' field.');if(field.focus)field.focus();return;
  }
 }
 if(next.start!==r.scope.start)ReviewStudio.month=null;
 r.scope={...r.scope,...next};r.brandProfile=campaignBrandProfile();r.scopeConfirmed=true;r.calendarApproved=false;r.needsBuild=r.scopeFirst;
 if(rolled.length)toast('Go-live date moved to '+dateLabel(rolled[0][1])+' — '+dateLabel(rolled[0][0])+' has already passed.');
 // The scope form already collects the photo gallery URL. Use it: a scope that names a
 // gallery but leaves the campaign with no photos is exactly the "why is my calendar blank"
 // case. Failing here must not block approval — the photos panel can still import by hand.
 const gallery=String(r.scope.media||r.scope.listing||'').trim();
 const boostId=reviewCampaignBoostId();
 if(boostId!=null&&window.RM&&/^https?:\/\//i.test(gallery)){
  RM.importPhotos(boostId,{listingUrl:gallery,limit:60}).then(res=>{
   if(res&&res.imported)toast('Imported '+res.imported+' listing photo'+(res.imported===1?'':'s')+'.');
   else if(res&&res.detail)toast(res.detail);
   refreshPhotoAssets();
  }).catch(()=>{});
 }
 persist();if(r.scopeFirst){buildApprovedScope();return}details(ReviewStudio.active);document.querySelector('.review-calendar')?.scrollIntoView({block:'start'});toast('Launch details confirmed.');
}

function reviewSlot(r,item){
 const date=new Date(r.scope.start+'T12:00:00Z');date.setUTCDate(date.getUTCDate()+(item.day||1)-1);
 return {date:item.date||date.toISOString().slice(0,10),time:item.time||(item.kind==='Meta ad'?r.scope.time:['10:00','12:00','17:30'][((item.day||1)-1)%3])};
}
function reviewDateLabel(date,time,zone){
 const d=new Date(date+'T'+time+':00Z');
 if(Number.isNaN(d.getTime()))return 'Schedule not set';
 const label=new Intl.DateTimeFormat('en-US',{weekday:'short',month:'short',day:'numeric',year:'numeric',hour:'numeric',minute:'2-digit',timeZone:'UTC'}).format(d);
 return label+' · '+zone.replace('America/','').replaceAll('_',' ');
}
function approveReview(){
 const r=activeReview();if(r.approved)return;
 if(!r.scopeConfirmed||!r.calendarApproved||!r.items.length){toast('Confirm your launch details and approve the calendar first.');document.querySelector('.campaign-scope')?.scrollIntoView({block:'start'});return}
 const unopened=r.items.filter(i=>!i.reviewed).length;
 show(unopened?`<span class="eyebrow">NOT EVERYTHING REVIEWED</span><h2>You haven’t reviewed everything.</h2><p>${unopened} of ${r.items.length} posts and ads haven’t been opened. Are you sure you want to approve the whole campaign?</p><p class="fine">Once approved, your posts and ad are locked and go live on your go-live date.</p><div class="modal-actions"><button class="nc-cancel" onclick="modal.close()">Keep reviewing</button><button class="campaign-primary" onclick="confirmCampaignApproval()">Yes, approve</button></div>`:`<h2>Approve the entire campaign?</h2><p>Your posts and ad are locked and go live on your go-live date.</p><div class="modal-actions"><button class="nc-cancel" onclick="modal.close()">Keep reviewing</button><button class="campaign-primary" onclick="confirmCampaignApproval()">Approve</button></div>`);
}
async function confirmCampaignApproval(){
 const r=activeReview();if(r.approved||!r.scopeConfirmed||!r.calendarApproved||!r.items.length)return;
 const boostId=reviewCampaignBoostId();
 if(boostId!=null&&window.RM){
  const buttons=[...modal.querySelectorAll('button')];
  buttons.forEach(b=>b.disabled=true);
  // Send the count of items nobody opened: the server refuses an approval that claims all of
  // them were read, and only takes it with an explicit confirm after the dialog (item 20).
  try{await RM.approveAll(boostId,{unreviewed:r.items.filter(i=>!i.reviewed).length,confirm:true})}
  catch(e){
   buttons.forEach(b=>b.disabled=false);
   show(`<h2>Couldn’t approve the campaign</h2><p>${esc(e.message)}</p><p class="fine">Nothing was changed. Try again once the API is reachable.</p><div class="modal-actions"><button class="alt" onclick="modal.close()">Close</button></div>`);
   return;
  }
 }
 r.approved=true;r.approvedAt=new Date().toISOString();{const c=[...state.campaigns,...examples][ReviewStudio.active];if(c&&c.rerunPaid){c.phase='republished';c.status='Republished';c.day=1}}persist();modal.close();details(ReviewStudio.active);
}

function changeReviewMonth(offset){
 const r=activeReview(),month=ReviewStudio.month||r.scope.start.slice(0,7);
 const d=new Date(month+'-01T12:00:00Z');d.setUTCMonth(d.getUTCMonth()+offset);
 ReviewStudio.month=d.toISOString().slice(0,7);
 const host=document.querySelector('.review-calendar');host.outerHTML=reviewCalendar(r,[...state.campaigns,...examples][ReviewStudio.active]);document.querySelector('.review-calendar').open=true;
}
function reviewCalendar(r,c){
 if(r.scopeFirst&&(!r.scopeConfirmed||!r.items.length||r.needsBuild||ReviewStudio.building.has(r))){
  return `<section class="panel review-calendar"><h2 class="campaign-step-title"><span>2</span> Campaign calendar</h2><p>${ReviewStudio.building.has(r)?'Resmara is building your draft posts and ads.':r.scopeConfirmed?'Your scope is approved. Build the draft to fill your calendar.':'Confirm your launch details first. Resmara will build the posts and ads for this calendar.'}</p>${r.scopeConfirmed&&!ReviewStudio.building.has(r)?(reviewCampaignBoostId()!=null?'<button class="campaign-primary" onclick="rebuildLiveCampaign()">Build my campaign</button>':'<button class="campaign-primary" onclick="buildApprovedScope()">Build campaign calendar</button>'):''}${r.scopeConfirmed&&!ReviewStudio.building.has(r)&&reviewCampaignBoostId()!=null?'<p class="fine build-charge-note">Building charges this campaign to your card on file. No card yet? You’ll add one first.</p>':''}</section>`;
 }
 // Only the weeks the campaign runs: from the week of day 1 to the week of day 14.
 const start=r.scope.start,last=reviewSlot(r,{day:14}).date;
 const first=new Date(start+'T12:00:00Z'),lastD=new Date(last+'T12:00:00Z');
 const gridStart=new Date(first);gridStart.setUTCDate(first.getUTCDate()-first.getUTCDay());
 const end=new Date(lastD);end.setUTCDate(lastD.getUTCDate()+(7-lastD.getUTCDay()));
 const fmt=d=>new Intl.DateTimeFormat('en-US',{month:'short',day:'numeric',timeZone:'UTC'}).format(d);
 const title=fmt(first)+' – '+fmt(lastD)+', '+lastD.getUTCFullYear();
 const month='';
 const posts=r.items.map((item,index)=>({item,index,...reviewSlot(r,item)}));
 const editable=!r.approved&&!r.calendarApproved;
 const ads=posts.filter(x=>x.item.kind==='Meta ad');
 const weeks=[];
 for(let cursor=new Date(gridStart);cursor<end;cursor.setUTCDate(cursor.getUTCDate()+7)){
  const dates=Array.from({length:7},(_,i)=>{const d=new Date(cursor);d.setUTCDate(d.getUTCDate()+i);return d.toISOString().slice(0,10)});
  const from=dates.findIndex(date=>date>=start&&date<=last);
  const to=dates.findLastIndex(date=>date>=start&&date<=last);
  const bars=from<0?'':ads.map(({item,index},lane)=>`<button class="review-month-ad" style="grid-column:${from+1}/${to+2};grid-row:${lane+2}" onclick="editCampaignItem(${index})" title="${esc(item.title)} · ${esc(start)}–${esc(last)}">${esc(item.title)}${item.reviewed?' ✓':''}</button>`).join('');
  weeks.push(`<div class="review-month-week" style="--post-row:${from<0?2:ads.length+2}">${dates.map((date,col)=>`<span class="review-month-date ${date>=start&&date<=last?'':'outside-month'}" style="grid-column:${col+1}">${Number(date.slice(-2))}</span>`).join('')}${bars}${dates.map((date,col)=>{
   const reportDay=[7,14].find(day=>reviewSlot(r,{day}).date===date);
   return `<div class="review-month-cell ${date>=start&&date<=last?'':'outside-month'}" style="grid-column:${col+1}" ${editable&&postDay(r,date)?`ondragover="if(event.dataTransfer.types.includes('application/x-resmara-post'))event.preventDefault()" ondrop="dropReviewPost(event,'${date}')"`:''}>${posts.filter(x=>x.item.kind!=='Meta ad'&&x.date===date).map(({item,index,time})=>`<button class="review-calendar-post${item.kind==='Video post'?' is-video':''}${item.withdrawn||item.publishStatus==='withdrawn'?' is-withdrawn':''}" ${editable?`draggable="true" ondragstart="event.dataTransfer.setData('application/x-resmara-post','${index}');event.dataTransfer.effectAllowed='move'"`:''} onclick="editCampaignItem(${index})">${item.image?`<span class="calendar-media"><img src="${esc(mediaPath(item.image))}" alt="${esc(item.room||'')}">${item.kicker?`<span class="post-kicker">${esc(item.kicker)}</span>`:''}${item.overlay?`<em class="post-overlay">${esc(item.overlay)}</em>`:''}</span>`:''}<b>${esc(item.title)}</b><small>${item.withdrawn||item.publishStatus==='withdrawn'?'Withdrawn · ':''}${item.kind==='Video post'?'<em class="vid-tag">▶ Video</em> ':''}${esc(time12(time))}${item.reviewed?' · ✓':''}</small></button>`).join('')}${reportDay?`<span class="review-calendar-report">${Number(c.day)>=reportDay?`<button class="alt" onclick="campaignReport([...state.campaigns,...examples][ReviewStudio.active],${reportDay})">● View report</button>`:'● Report due'}</span>`:''}</div>`;
  }).join('')}</div>`);
 }
 return `<details class="panel review-calendar" ${r.calendarApproved||r.approved?'':'open'}><summary class="campaign-step-title"><span>2</span> Campaign calendar ${r.calendarApproved||r.approved?'<small>✓ Calendar Approved</small>':''}</summary><p>This is your campaign calendar. Open any post or ad to check its information and creative before you approve. You only need to open the items you want to spot-check or change.</p>${editable?'<p class="fine">Drag a post to another campaign day, or change its date in the post editor.</p>':''}<div class="flex review-month-nav"><strong>${title}</strong></div>${videoNote(r)}<p class="fine">Times in ${esc(r.scope.zone)} · Ads run ${esc(niceDate(start))} at ${esc(time12(r.scope.time))} through ${esc(niceDate(last))}, end of day.</p><div class="review-month-scroll"><div class="review-month-grid"><div class="review-month-weekdays">${['Sun','Mon','Tue','Wed','Thu','Fri','Sat'].map(d=>`<span>${d}</span>`).join('')}</div>${weeks.join('')}</div></div><p class="fine">${r.liveGeneration?'Draft copy, captions and creative directions from your campaign engine'+(r.engine&&r.engine.host?' ('+esc(r.engine.host)+')':'')+'. Nothing has been published.':'Sample schedule and creative. Nothing is published from this preview.'}${r.buildNotes&&r.buildNotes.length?' '+r.buildNotes.map(esc).join(' '):''}</p><div class="scope-form-actions"><span class="fine">${r.scopeConfirmed?'Confirm the dates and creative before approving.':'Confirm your launch details first.'}</span>${r.approved?'':r.calendarApproved?'<button class="alt" onclick="unlockCampaignCalendar()">Unlock calendar</button>':`<button class="campaign-primary scope-approval-button" onclick="approveCampaignCalendar()" ${r.scopeConfirmed?'':'disabled'}>Approve campaign calendar</button>`}</div></details>`;
}

function approveCampaignCalendar(){
 const r=activeReview();if(!r.scopeConfirmed||r.approved||!r.items.length||r.needsBuild||ReviewStudio.building.has(r))return;
 r.calendarApproved=true;persist();details(ReviewStudio.active);
 document.querySelector('.review-approval')?.scrollIntoView({block:'nearest'});
}
function unlockCampaignCalendar(){
 const r=activeReview();if(r.approved)return;
 r.calendarApproved=false;persist();details(ReviewStudio.active);
}

function buildApprovedScope(){
 const r=activeReview(),account=state;
 if(!r.scopeFirst||!r.scopeConfirmed||r.approved||ReviewStudio.building.has(r))return;
 const scope={...r.scope,...(r.brandProfile||campaignBrandProfile())};
 ReviewStudio.building.add(r);r.calendarApproved=false;
 show(`<span class="eyebrow">BUILDING YOUR CAMPAIGN</span><h2>Resmara is turning your scope into a campaign.</h2><div class="audit-track campaign-build-track"><span class="robot-avatar" aria-hidden="true"></span></div><p role="status">Planning 14 days of content…</p><p class="fine">${r.liveGeneration?'Resmara is drafting the 14 days of posts, captions and the ad from your approved brief.':'Demo build · Uses your approved brief and sample images.'}</p>`);
 const progress=modal.querySelector('[role="status"]');
 if(r.liveGeneration){ReviewStudio.building.delete(r);buildCampaignFromBackend();return}
 ['Writing drafts from your approved property details…','Applying your brand to the creative previews…','Placing the posts and ads on the calendar…'].forEach((text,i)=>setTimeout(()=>{if(progress?.isConnected)progress.textContent=text},900+i*1500));
 setTimeout(()=>{
  ReviewStudio.building.delete(r);
  if(state!==account||!r.scopeConfirmed)return;
  r.items=sampleReviewItems({address:scope.address}).map(item=>{
   const feature=item.id===0||item.id===2?scope.highlights:item.id===3?scope.facts:'';
   const friendly=/friendly|warm|conversational/i.test(scope.voice);
   return {...item,caption:[(friendly?'Come take a look at ':'Discover ')+scope.address+'.',feature,scope.brokerage?'Contact '+scope.brokerage+' for listing details.':'View the listing for more details.',scope.listing].filter(Boolean).join(' ')};
  });
  r.needsBuild=false;persist();
  if(progress?.isConnected&&modal.open)modal.close();
  if(document.querySelector('.campaign-scope')&&activeReview()===r){
   details(ReviewStudio.active);
   document.querySelector('.review-calendar')?.scrollIntoView({block:'start'});
   toast('Your demo calendar is ready to review.');
  }
 },5700);
}

// Build the calendar from the real content engine (POST /api/boosts/{id}/build + GET .../posts).
function photoPermissionChanged(){
 const box=document.querySelector('#photoPermission');
 if(!box)return;
 // Never disable the build button: a disabled button cannot say why, and clicking it read as
 // broken. Un-ticking is recorded here, and Build points at this box when it is not ticked.
 const panel=box.closest('.photo-permission');
 if(panel)panel.classList.toggle('granted',box.checked);
 if(box.checked&&reviewCampaignBoostId()!=null&&window.RM&&RM.setPhotoPermission)RM.setPhotoPermission(reviewCampaignBoostId(),true).catch(()=>{});
}
async function buildCampaignFromBackend(){
 const r=activeReview(),boostId=reviewCampaignBoostId();
 if(boostId==null||!window.RM){toast('This demo campaign isn’t linked to a backend boost yet.');return}
 if(!r.scopeFirst||!r.scopeConfirmed||r.approved||ReviewStudio.building.has(r))return;
 // Build designs posts from the agent's photographs: without their permission on record the
 // server refuses, so ask for it here rather than failing after the engine has started.
 const permissionBox=document.querySelector('#photoPermission');
 if(permissionBox&&!permissionBox.checked){
  // The box sits in the photos panel below this button, so a toast alone looked like nothing
  // happened — and the "building" dialog stayed on screen with no build behind it. Close it and
  // bring the box to the front instead.
  if(modal&&modal.open)modal.close();
  details(ReviewStudio.active);
  const box=document.querySelector('#photoPermission');
  if(box){
   const panel=box.closest('.photo-permission');
   if(panel){panel.classList.add('needs-attention');setTimeout(()=>panel.classList.remove('needs-attention'),5000)}
   try{box.scrollIntoView({block:'center'})}catch(e){}
   try{box.focus({preventScroll:true})}catch(e){if(box.focus)box.focus()}
  }
  toast('One tick before Resmara can build: “I have permission to use these photos”.');
  return;
 }
 ReviewStudio.building.add(r);
 show(`<span class="eyebrow">BUILDING YOUR CAMPAIGN</span><h2>Resmara is turning your scope into a campaign.</h2><div class="audit-track campaign-build-track"><span class="robot-avatar" aria-hidden="true"></span></div><p role="status">Running the content engine…</p>`);
 const progress=modal.querySelector('[role="status"]');
 let finalStatus=null;
 try{
  const started=await RM.buildCampaign(boostId,{force:false,photo_permission:true});
  // The build is a background run (four model calls, minutes long) — a single request would be
  // cut by any hosted proxy. Poll the status, then read the posts it wrote.
  if(started&&started.status==='running'){
   const waitStart=Date.now(), limitMs=9*60*1000; let last='running';
   while(Date.now()-waitStart<limitMs){
    await new Promise(res=>setTimeout(res,3000));
    const st=(await RM.buildStatus(boostId).catch(()=>null))||{};
    if(progress?.isConnected){
     const secs=Math.round((Date.now()-waitStart)/1000);
     progress.textContent=`Running the content engine… ${secs}s${st.posts_created?` · ${st.posts_created} posts drafted`:''}`;
    }
    if(st.status==='error') throw new Error(st.error||'The content engine stopped without an error message.');
    if(st.status==='done'){finalStatus=st;last='done';break}
   }
   if(last!=='done') throw new Error('The build is still running after 9 minutes. Check the campaign again in a moment — the posts it writes are saved either way.');
  }
  const backendPosts=await RM.posts(boostId);
  const result=finalStatus||started||{};
  if(Array.isArray(backendPosts)&&backendPosts.length){
   r.items=backendPosts.map(post=>({id:post.id,postId:post.id,day:post.day||1,title:post.title||String(post.caption||'Scheduled post').split(/[.\n]/)[0].slice(0,42)||'Scheduled post',kicker:post.kicker||'',overlay:post.overlay_text||'',room:post.photo_room||'',kind:post.kind==='short_video'?'Video post':'Photo post',caption:post.caption||'',image:post.image_url||'',reviewed:post.client_status==='approved',publishStatus:post.publish_status||'',time:(post.publish_at||'').slice(11,16)||undefined}));
  }
  r.needsBuild=false;r.engine=(result&&result.engine)||null;r.buildNotes=((result&&result.notes)||[]).slice();r.buildSource=(result&&result.source)||'';
  ReviewStudio.building.delete(r);   // before the re-render: the calendar draws its "building" state otherwise
  persist();
  if(progress?.isConnected&&modal.open)modal.close();
  if(activeReview()===r){details(ReviewStudio.active);document.querySelector('.review-calendar')?.scrollIntoView({block:'start'})}
  toast('Campaign built: '+(result&&result.posts_created!=null?result.posts_created:r.items.length)+' posts created'+(r.engine&&r.engine.host?' — drafted by '+r.engine.host:'')+'.');
 }catch(e){
  // 402 = this campaign has not been paid for. The API says so in a machine-readable detail,
  // so show the price and the checkout button instead of "build paused" and a dead end.
  if(e&&e.status===402){ReviewStudio.building.delete(r);showPaywall(boostId,e.detail);return}
  if(progress?.isConnected&&modal.open)show(`<h2>Campaign build paused</h2><p>${esc(e.message)}</p><p class="fine">Your approved scope is saved. You can retry any time.</p><div class="modal-actions"><button class="alt" onclick="modal.close()">Back to campaign</button></div>`);
 }finally{ReviewStudio.building.delete(r)}
}

// Launch the approved campaign through the real API (POST /api/launch).
// A live draft whose build produced no posts: retry through the same backend path. The scope is
// already approved at that point, which is exactly why buildCampaignFromBackend()'s guard would
// otherwise return without doing anything.
async function rebuildLiveCampaign(){
 const r=activeReview(),boostId=reviewCampaignBoostId();
 // One click must either start the build or say what is missing. Returning silently is exactly
 // what "Build content with Resmara isn't working" looked like from the outside.
 if(boostId==null||!window.RM){toast('This campaign isn’t linked to a backend boost yet.');return}
 if(ReviewStudio.building.has(r)){toast('Resmara is already building this campaign.');return}
 if(!r.scopeConfirmed){
  // A build needs an approved scope. Confirming it here is the same thing "Confirm details"
  // does, so this button can never be a no-op on a fresh draft.
  const form=document.querySelector('.campaign-scope form');
  if(!form){toast('Confirm your launch details first.');return}
  saveCampaignScope(form);
  return;
 }
 const approved=r.approved;r.approved=false;r.scopeFirst=true;
 try{await buildCampaignFromBackend()}finally{r.approved=approved;persist()}
}

async function launchCampaignViaApi(){
 const boostId=reviewCampaignBoostId();
 if(boostId==null||!window.RM){toast('This demo campaign isn’t linked to a backend boost yet.');return}
 show(`<span class="eyebrow">LAUNCHING</span><h2>Launching your campaign…</h2><p role="status">Checking the budget and approvals, then creating the Meta campaign for your go-live date…</p>`);
 try{
  const result=await RM.launch(boostId,{auto_approve:false});
  if(result&&['approval_required','no_ad_account','nothing_to_launch'].includes(result.status)){
   const reasons=(Array.isArray(result.reasons)&&result.reasons.length)?result.reasons:[result.detail||result.message||'The API did not launch this campaign.'];
   const heading=result.status==='no_ad_account'?'Connect your Meta ad account first':result.status==='nothing_to_launch'?'Build and approve the campaign first':'Approval needed before launch';
   show(`<span class="eyebrow">LAUNCH HELD</span><h2>${heading}</h2><ul class="campaign-report-list">${reasons.map(reason=>`<li>${esc(reason)}</li>`).join('')}</ul><p class="fine">Nothing was published and no spend was authorised.</p><div class="modal-actions"><button class="alt" onclick="modal.close()">Close</button></div>`);
   return;
  }
  show(`<h2>Campaign launched</h2><div class="check">Meta campaign ${esc(String((result&&result.meta_campaign_id)||'created'))} scheduled for your go-live date.</div><p class="fine">${result&&result.simulated?'Simulated mode · no live Meta calls were made.':'It starts on your go-live date. You can pause it from the campaign page at any time.'}</p><div class="modal-actions"><button onclick="modal.close()">Close</button></div>`);
 }catch(e){
  show(`<h2>Launch failed</h2><p>${esc(e.message)}</p><div class="modal-actions"><button class="alt" onclick="modal.close()">Close</button></div>`);
 }
}

function campaignBrandPreview(brand){
 const image=(kind,label)=>{const source=state.brandMedia?.[brand[kind+'Id']];return source?`<img src="${esc(source)}" alt="${label}">`:''};
 return `<div class="creative-brand-strip">${image('logo','Brokerage logo')}${image('headshot','Agent headshot')}<div><strong>${esc(brand.agent||brand.brokerage||'Your agency')}</strong><small>${[brand.agent?brand.brokerage:'',brand.license?'License '+brand.license:''].filter(Boolean).map(esc).join(' · ')}</small></div></div>`;
}

function scopeResearchSources(){
 const c=[...state.campaigns,...examples][ReviewStudio.active];
 return c?.research?.sources?.length?`<details class="fine"><summary>Listing research sources</summary><ul>${c.research.sources.map(url=>`<li><a href="${esc(url)}" target="_blank" rel="noopener noreferrer">${esc(url)}</a></li>`).join('')}</ul></details>`:'';
}
// Send the approved, due posts out now (POST /api/content/publish/boost/{id}) and then read
// back exactly what Meta accepted, what is still scheduled and what failed - with its error.
async function publishApprovedPosts(){
 const boostId=reviewCampaignBoostId();
 if(boostId==null||!window.RM){toast('This demo campaign isn’t linked to a backend boost yet.');return}
 show(`<span class="eyebrow">PUBLISHING</span><h2>Sending the approved posts out…</h2><p role="status">Handing the approved, due posts to the platform…</p>`);
 const progress=modal.querySelector('[role="status"]');
 try{await RM.publishNow(boostId)}catch(e){
  if(progress?.isConnected&&modal.open)show(`<h2>Publishing stopped</h2><p>${esc(e.message)}</p><div class="modal-actions"><button class="alt" onclick="modal.close()">Close</button></div>`);
  return;
 }
 let status=null;
 try{status=await RM.publishStatus(boostId)}catch(e){}
 if(!modal.open)return;
 const posts=(status&&status.posts)||[];
 const counts=(status&&status.counts)||{};
 const published=posts.filter(p=>p.publish_status==='published');
 const failed=posts.filter(p=>p.publish_status==='failed');
 const waiting=posts.filter(p=>!p.publish_status||p.publish_status==='scheduled');
 const lines=posts.map(p=>`<li>Day ${p.day} · ${esc(p.kind||'post')} · <b>${esc(p.publish_status||'scheduled')}</b>${p.publish_target?' → '+esc(p.publish_target):''}${p.fb_post_id?' · FB '+esc(p.fb_post_id):''}${p.ig_media_id?' · IG '+esc(p.ig_media_id):''}${p.last_error?' · <span class="fine">'+esc(p.last_error)+'</span>':''}</li>`).join('');
 show(`<h2>${published.length?'Published':'Nothing published yet'}</h2><div class="check">${published.length} published · ${waiting.length} still scheduled · ${failed.length} failed</div>${posts.length?`<ul class="campaign-report-list">${lines}</ul>`:'<p class="fine">No posts to publish: build the campaign first.</p>'}${failed.length?'<p class="fine">A failed post is only retried after its error is fixed - fix the reason above, then publish again.</p>':''}${waiting.length&&!published.length?'<p class="fine">Posts go out on their scheduled day; the publisher also runs on its own schedule.</p>':''}<div class="modal-actions"><button class="alt" onclick="modal.close()">Close</button></div>`);
}

// --- Run a completed campaign again -------------------------------------------
// A completed campaign opens normally, so the agent can still see the calendar, leads and
// reports they paid for. A box under the address offers to run it again. Paying builds a
// fresh 14 days (new angles, same home); once approved it moves up to Active as Republished.
const RERUN_PRICE='$39';
function showRerunOffer(index){
 const main=document.querySelector('#content');if(!main)return;
 const c=[...state.campaigns,...examples][index];
 const box=document.createElement('div');box.className='until-sold rerun-box';
 box.innerHTML=`<b class="until-sold-title">Run this campaign again</b><p class="until-sold-sub"><b>${esc(c.address)}</b> finished its 14 days. Its calendar and reports stay below. Running it again builds a fresh 14 days of posts and a new listing ad, with new angles on the same home.</p><div class="until-sold-actions"><button type="button" class="campaign-primary" onclick="startRerun(${index})">Run it again · ${RERUN_PRICE}</button></div>`;
 const head=main.querySelector('.review-heading');
 if(head)head.after(box);else main.prepend(box);
}
function startRerun(index){
 const c=[...state.campaigns,...examples][index];if(!c)return;
 show(`<span class="eyebrow">RUNNING IT AGAIN</span><h2>Resmara is building a fresh 14 days.</h2><div class="audit-track campaign-build-track"><span class="robot-avatar" aria-hidden="true"></span></div><p role="status">Charging ${RERUN_PRICE} to your saved card…</p><p class="fine">Demo · no real payment runs here.</p>`);
 const status=modal.querySelector('[role="status"]');
 ['Looking back at what worked last time…','Planning new angles on the home…','Placing the new posts and ad on the calendar…'].forEach((t,i)=>setTimeout(()=>{if(status?.isConnected)status.textContent=t},1000+i*1400));
 setTimeout(()=>{
  c.rerunPaid=true;
  const key=reviewKey(c,index);
  const fresh={approved:false,items:sampleReviewItems(c)};
  fresh.scope=initialCampaignScope(c);fresh.scope.start=nextCampaignDate();
  state.reviews[key]=fresh;ReviewStudio.month=null;persist();
  if(modal.open)modal.close();details(index);
  toast('Your new campaign is ready. Confirm the launch details and approve it to go live.');
 },5400);
}

// Replacement photos: scale to max 1440px on the long side and save as JPEG (Instagram-safe).
function compressToJpeg(file,max=1440,quality=0.85){
 return new Promise((ok,bad)=>{
  if(!/^image\//.test(file.type))return bad(new Error('Choose a photo file.'));
  const img=new Image(),url=URL.createObjectURL(file);
  img.onload=()=>{const k=Math.min(1,max/Math.max(img.width,img.height)),c=document.createElement('canvas');c.width=Math.round(img.width*k);c.height=Math.round(img.height*k);const g=c.getContext('2d');g.fillStyle='#fff';g.fillRect(0,0,c.width,c.height);g.drawImage(img,0,0,c.width,c.height);URL.revokeObjectURL(url);ok(c.toDataURL('image/jpeg',quality))};
  img.onerror=()=>{URL.revokeObjectURL(url);bad(new Error('That photo couldn’t be read. Try another file.'))};
  img.src=url;
 });
}

function time12(t){if(!t||!/^\d{1,2}:\d{2}/.test(t))return t||'';let [h,m]=t.split(':').map(Number);const ap=h>=12?'PM':'AM';h=h%12||12;return h+':'+String(m).padStart(2,'0')+' '+ap}
function niceDate(d){try{return new Date(d+'T12:00:00Z').toLocaleDateString('en-US',{month:'short',day:'numeric',timeZone:'UTC'})}catch(e){return d}}

// The campaign has at most one video. With one: a video ad, and the video goes out once as the first post.
// Without one: a photo ad and photo posts only.
function applyCampaignVideo(r,url){
 r.videoUrl=url;const ad=r.items.find(x=>x.kind==='Meta ad');const posts=r.items.filter(x=>x.kind!=='Meta ad');
 const first=posts.reduce((a,b)=>a&&a.day<=b.day?a:b,null);
 if(ad){ad.adType=url?'video':'photo';ad.title=url?'Video ad':'Photo ad'}
 posts.forEach(p=>{if(p.kind==='Video post'&&p!==first)p.kind='Photo post'});
 if(first){first.kind=url?'Video post':'Photo post';if(url&&first.title==='Just listed')first.title='Video tour';if(!url&&first.title==='Video tour')first.title='Just listed'}
}
function videoNote(r){if(!r.items.some(i=>i.kind==='Video post'))return '<p class="video-note">No video in your listing link, so your ad is a photo carousel and every post is a photo.</p>';return true?'<p class="video-note has">▶ <b>Video found.</b> It runs as your ad and goes out once as your first post.</p>':'<p class="video-note">No video in your listing link, so your ad and posts use photos. <a href="#" onclick="editCampaignItem(activeReview().items.findIndex(x=>x.kind===\'Meta ad\'));return false">Add a video link</a></p>'}

// Photo carousel ad: flip through every card the ad will show.
function carouselViewer(imgs){
 return `<div class="ad-carousel" data-i="0"><div class="ad-car-track">${imgs.map((u,k)=>`<img src="${esc(mediaPath(u))}" alt="Ad card ${k+1}" class="${k?'':'on'}">`).join('')}</div><button type="button" class="ad-car-btn prev" aria-label="Previous card" onclick="carouselGo(this,-1)">‹</button><button type="button" class="ad-car-btn next" aria-label="Next card" onclick="carouselGo(this,1)">›</button><div class="ad-car-dots">${imgs.map((_,k)=>`<i class="${k?'':'on'}"></i>`).join('')}</div><p class="fine ad-car-count">Card <b>1</b> of ${imgs.length} · people swipe through these in the ad</p></div>`;
}
function carouselGo(btn,d){
 const box=btn.closest('.ad-carousel'),imgs=box.querySelectorAll('img'),dots=box.querySelectorAll('.ad-car-dots i');
 let i=(Number(box.dataset.i)+d+imgs.length)%imgs.length;box.dataset.i=i;
 imgs.forEach((im,k)=>im.classList.toggle('on',k===i));dots.forEach((x,k)=>x.classList.toggle('on',k===i));box.querySelector('.ad-car-count b').textContent=i+1;
}

// ---- Withdraw one post from a locked campaign ------------------------------------------------
// Once a campaign is approved nothing on it can be edited, but a single post can still be pulled
// before it goes out (a showing changed, a detail is wrong). The rest of the calendar runs as
// approved. A post that has already gone out says so instead: it is on the agent's Page now.
function postWentOut(it){
 if(['posted','published','publishing'].includes(it.publishStatus))return true;
 const c=[...state.campaigns,...examples][ReviewStudio.active];
 return campaignBoostId(c)==null&&Number(c&&c.day)>0&&it.day<Number(c.day);
}
// No Facebook Page connected yet: the agent shares posts by hand, so each live post can be
// downloaded (the image) with its caption copied. Once a Page is connected, the rest auto-post.
function downloadPostButton(it,i){
 if(state.connected||it.kind==='Meta ad'||it.withdrawn||!it.image)return '';
 return `<button type="button" class="nc-cancel" onclick="downloadPost(${i})">Download post</button>`;
}
function downloadPost(i){
 const it=activeReview().items[i];
 const a=document.createElement('a');a.href=mediaPath(it.image);a.download=(it.title||'post').replace(/[^a-z0-9]+/gi,'-').toLowerCase()+'.jpg';document.body.append(a);a.click();a.remove();
 (navigator.clipboard?navigator.clipboard.writeText(it.caption||''):Promise.reject()).then(()=>toast('Photo downloaded. Caption copied, ready to paste.'),()=>toast('Photo downloaded. Copy the caption from this post.'));
}
function withdrawButton(it,i){
 if(it.kind==='Meta ad')return '';
 if(it.withdrawn||it.publishStatus==='withdrawn')return '<span class="withdrawn-note">Withdrawn. This post won’t go out.</span>';
 if(postWentOut(it))return '<span class="withdrawn-note">This post has already gone out.</span>';
 return `<button type="button" class="campaign-primary" onclick="confirmWithdrawPost(${i})">Withdraw post</button>`;
}
function confirmWithdrawPost(i){
 const r=activeReview(),it=r.items[i],slot=reviewSlot(r,it);
 show(`<span class="eyebrow">WITHDRAW POST</span><h2>Withdraw “${esc(it.title)}”?</h2><p>It won’t go out on ${esc(reviewDateLabel(slot.date,slot.time,r.scope.zone))}. The rest of your campaign keeps running as approved.</p><p class="fine" role="alert"></p><div class="modal-actions"><button type="button" class="nc-cancel" onclick="editCampaignItem(${i})">Keep it</button><button type="button" class="campaign-primary" onclick="withdrawPost(${i},this)">Withdraw post</button></div>`);
}
async function withdrawPost(i,button){
 const r=activeReview(),it=r.items[i],postId=it.postId??it.post_id;
 if(button)button.disabled=true;
 if(window.RM&&RM.withdrawPost&&reviewCampaignBoostId()!=null&&postId!=null){
  try{await RM.withdrawPost(postId)}
  catch(e){if(button)button.disabled=false;const a=modal.querySelector('[role="alert"]');if(a)a.textContent=(e&&e.message)||'Could not withdraw that post. Try again.';return}
 }
 it.withdrawn=true;it.publishStatus='withdrawn';persist();modal.close();details(ReviewStudio.active);
 toast('Post withdrawn. It won’t go out, and the rest of your campaign keeps running.');
}
