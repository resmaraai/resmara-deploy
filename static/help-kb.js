/* Ask Resmara: the help assistant's answer library.
 *
 * Every answer here was written from how Resmara actually works. The assistant matches the
 * agent's question to the closest entry by its keywords; if nothing fits, it says so and offers
 * to send the question to the team.
 *
 * How it learns (backend, see Dan's package §19):
 *   - Every question it couldn't answer is logged (POST /api/help/misses).
 *   - When the team answers a support request, the operator console offers "Add to Resmara's
 *     answers"; approved answers come back from GET /api/help/answers and are merged in below,
 *     so the next agent who asks gets the answer straight away.
 */
'use strict';

var HELP_KB = [
  // ---- Getting started ------------------------------------------------------------------------
  { id: 'start', topic: 'Getting started', q: 'How do I start my first campaign?',
    keys: ['start', 'first campaign', 'new campaign', 'begin', 'how do i use', 'get started', 'create campaign', 'launch'],
    a: 'Click the orange ＋ Campaign button at the top of My campaigns. Paste your MLS public listing link, tick the photo permission box and click Build my campaign. Resmara builds 14 posts and your ad, then you set your go-live date, review and approve.' },
  { id: 'what', topic: 'Getting started', q: 'What does Resmara do?',
    keys: ['what is resmara', 'what does resmara do', 'what do i get', 'included', 'what comes with'],
    a: 'For each listing, Resmara builds a 14-day campaign in your brand: 14 social posts for Facebook and Instagram plus one Meta ad. It posts them for you, flags people who comment with buying interest, and gives you Day 7 and Day 14 reports to share with your seller.' },
  { id: 'need', topic: 'Getting started', q: 'What do I need before I can run a campaign?',
    keys: ['need', 'requirements', 'before i start', 'what do i need', 'set up'],
    a: 'A Facebook business Page you’re an admin of, an Instagram professional account linked to it, a Meta ad account with a payment method, and a card on file with Resmara. Resmara checks all of this when you connect your Meta account.' },

  // ---- Meta connection -------------------------------------------------------------------------
  { id: 'connect', topic: 'Your Meta account', q: 'How do I connect my Facebook and Instagram?',
    keys: ['connect', 'facebook', 'instagram', 'meta account', 'link my', 'log in with facebook'],
    a: 'Go to Accounts and click Connect your Meta account. Log in with your own Facebook details and choose your Page, Instagram account and ad account. Resmara then checks everything is ready to post and run ads.' },
  { id: 'required', topic: 'Your Meta account', q: 'Why do I have to connect Meta?',
    keys: ['why connect', 'skip', 'do i have to', 'without facebook', 'required', 'must connect'],
    a: 'Resmara posts to your own Page and Instagram and runs ads from your own ad account, so it can’t do anything until they’re connected. You can book a free setup session if you’d like a hand.' },
  { id: 'ig-personal', topic: 'Your Meta account', q: 'It says my Instagram isn’t a business account.',
    keys: ['instagram isn', 'personal account', 'business account', 'professional account', 'creator'],
    a: 'In the Instagram app go to Settings › Account type and tools › Switch to professional account, then link it to your Facebook Page. Once you’ve done this, come back to Accounts and click Check again.' },
  { id: 'not-admin', topic: 'Your Meta account', q: 'It says I’m not an admin of the Page.',
    keys: ['admin', 'not an admin', 'page access', 'full control', 'manage the page'],
    a: 'Ask whoever manages the Page to give you full control (admin) in the Page’s settings, then come back here and click Check again.' },
  { id: 'no-page', topic: 'Your Meta account', q: 'I don’t have a Facebook business Page.',
    keys: ['no page', 'business page', 'facebook page', 'create a page', 'personal profile'],
    a: 'Resmara posts to a Facebook business Page, not your personal profile. Create one from Facebook’s menu › Pages › Create new Page, then come back and click Check again. A free setup session can walk you through it.' },
  { id: 'no-ad-account', topic: 'Your Meta account', q: 'It says I have no ad account ready.',
    keys: ['ad account', 'payment method', 'ads manager', 'no ad account', 'billing in meta'],
    a: 'Your listing ad runs from your own Meta ad account, and Meta needs a card on it to bill your ad budget. Add one in Meta Ads Manager › Billing, then come back and click Check again.' },
  { id: 'portfolio', topic: 'Your Meta account', q: 'Do I need a Meta Business portfolio?',
    keys: ['business manager', 'business portfolio', 'business suite', 'meta business'],
    a: 'No. You connect with your own Facebook login. You just need your Page, Instagram professional account and ad account.' },
  { id: 'setup-session', topic: 'Your Meta account', q: 'Can someone help me set it up?',
    keys: ['help me set up', 'setup session', 'book', 'call', 'appointment', 'walk me through', 'stuck'],
    a: 'Yes. Book a free 30-minute setup session from the Meta connection step, and one of our team will connect your Page, Instagram and ad account with you on a video call.' },
  { id: 'disconnect', topic: 'Your Meta account', q: 'How do I remove Resmara’s access?',
    keys: ['disconnect', 'remove access', 'revoke', 'take away access'],
    a: 'In Facebook go to Settings › Business integrations and remove Resmara. Campaigns can’t post or run ads after that.' },

  // ---- Listing link & photos -------------------------------------------------------------------
  { id: 'mls-link', topic: 'Your listing', q: 'Which link do I paste?',
    keys: ['which link', 'mls link', 'listing link', 'public link', 'share link', 'get this link', 'url'],
    a: 'The public link your MLS makes when you share a listing with a client. Open the listing in your MLS, click Share, Email or Send to client, and copy the public link. Check it opens in a private browser window without signing in.' },
  { id: 'zillow', topic: 'Your listing', q: 'Can I use a Zillow or Realtor.com link?',
    keys: ['zillow', 'realtor.com', 'redfin', 'trulia', 'homes.com'],
    a: 'Those sites don’t let us collect the photos, so Resmara reads the home’s details and asks you to upload your photos instead. Your MLS public link usually works best.' },
  { id: 'link-fails', topic: 'Your listing', q: 'Resmara can’t read my link.',
    keys: ['can’t read', 'cant read', 'link failed', 'didn’t work', 'error', 'sign-in', 'login link'],
    a: 'The link probably needs your MLS sign-in. Use the public client link instead, or click Enter it manually to type the address and upload your photos.' },
  { id: 'photos-upload', topic: 'Your listing', q: 'How many photos do I need?',
    keys: ['how many photos', 'upload photos', 'minimum', 'my own photos', 'photographer'],
    a: 'At least 14. Upload as many as you like and Resmara picks the best 14, skipping bathrooms, closets, clutter and anything with people in it.' },
  { id: 'permission', topic: 'Your listing', q: 'What is the photo permission checkbox?',
    keys: ['permission', 'checkbox', 'rights', 'copyright', 'allowed to use'],
    a: 'Before building, you confirm you have permission to use the listing’s photos and details to market the property on social media and in ads, for example from your photographer or brokerage.' },

  // ---- Video -----------------------------------------------------------------------------------
  { id: 'video', topic: 'Video', q: 'Can my campaign use a video?',
    keys: ['video', 'tour video', 'reel', 'walkthrough', 'film'],
    a: 'Yes, if your listing link includes a video. Resmara finds it, makes it your ad, and posts it as your first post on your go-live date. If there’s no video, your ad is a photo carousel and every post is a photo.' },
  { id: 'video-missing', topic: 'Video', q: 'Why didn’t Resmara find my video?',
    keys: ['no video', 'didn’t find my video', 'video missing', 'youtube'],
    a: 'The video has to be on the listing link itself and playable without a sign-in. YouTube videos can’t be posted to Facebook or Instagram directly, so Resmara uses photos instead.' },

  // ---- Pricing & billing -----------------------------------------------------------------------
  { id: 'price', topic: 'Pricing and billing', q: 'How much does it cost?',
    keys: ['cost', 'price', 'how much', 'fee', 'pricing', '$49', 'subscription'],
    a: 'Each campaign is $49, charged when you click Build my campaign. No subscription. Your ad budget is separate and paid to Meta.' },
  { id: 'when-pay', topic: 'Pricing and billing', q: 'When am I charged?',
    keys: ['when am i charged', 'when do i pay', 'charge', 'charged', 'payment'],
    a: 'When you click Build my campaign. If you have no card yet, Resmara asks you to add one first. Reviewing, approving and launching don’t cost anything extra.' },
  { id: 'ad-budget', topic: 'Pricing and billing', q: 'How does the ad budget work?',
    keys: ['ad budget', 'ad spend', 'budget', 'meta bills', 'how much on ads', '$50'],
    a: 'You choose a total ad budget for the whole 14 days (default $50). Meta bills it to the card on your own ad account. Resmara keeps none of it, and it isn’t part of the $49.' },
  { id: 'card', topic: 'Pricing and billing', q: 'How do I add or change my card?',
    keys: ['add a card', 'change card', 'update card', 'credit card', 'payment method', 'stripe'],
    a: 'Go to Billing and click Add a card. You add it on Stripe’s secure page, and Resmara never sees your card number.' },
  { id: 'receipts', topic: 'Pricing and billing', q: 'Where are my receipts?',
    keys: ['receipt', 'invoice', 'purchases', 'history'],
    a: 'Billing › Purchases lists every campaign you’ve paid for.' },
  { id: 'until-sold', topic: 'Pricing and billing', q: 'Can Resmara keep running my listing until it sells?',
    keys: ['until it sells', 'until sold', 'autopilot', 'keep running', 'every 2 weeks', 'every two weeks', 'auto renew', 'automatic'],
    a: 'Yes. Turn on Run it until it sells in Launch details, or click Until it sells on the campaign card. Every 2 weeks Resmara builds a brand-new campaign, 14 new posts and a new ad, tuned from how the last ad did. Each round is ready to look over 3 days before it starts. $39 per renewal, and your ad budget runs again each round, billed by Meta. It stops by itself when the listing shows pending or sold.' },
  { id: 'rerun', topic: 'Pricing and billing', q: 'Can I run a campaign again?',
    keys: ['again', 'rerun', 're-run', 'second campaign', 'another campaign', 'still for sale', 'renew'],
    a: 'Yes. Open a completed campaign and click Run it again ($39). Resmara builds 14 brand-new posts and a new ad with fresh angles on the same home.' },
  { id: 'refund', topic: 'Pricing and billing', q: 'Can I get a refund?',
    keys: ['refund', 'money back', 'cancel campaign'],
    a: 'Send the team a request from Support with the campaign’s address, and we’ll look at it with you.' },

  // ---- Building & reviewing --------------------------------------------------------------------
  { id: 'build-time', topic: 'Your campaign', q: 'How long does the build take?',
    keys: ['how long', 'build take', 'waiting', 'building'],
    a: 'Usually a minute or two. You can watch the progress, and you land on your campaign page with the calendar ready when it’s done.' },
  { id: 'launch-details', topic: 'Your campaign', q: 'What are launch details?',
    keys: ['launch details', 'go-live', 'go live date', 'start date', 'when does it start'],
    a: 'Three things at the top of your campaign: your go-live date (when posts and the ad start), where clicks go (your listing link unless you paste your own page), and your ad budget.' },
  { id: 'clicks', topic: 'Your campaign', q: 'Where do people go when they click?',
    keys: ['clicks go', 'send clicks', 'destination', 'my website', 'landing page', 'crm'],
    a: 'To your listing link by default. To send them to your own page instead, paste it in Send clicks to on the campaign page.' },
  { id: 'edit-post', topic: 'Your campaign', q: 'How do I change a post?',
    keys: ['edit', 'change a post', 'caption', 'title', 'replace photo', 'swap photo', 'change photo'],
    a: 'Click any post on the calendar. You can change its title and caption, upload a replacement photo and change its date and time. Click Save and mark reviewed.' },
  { id: 'move-post', topic: 'Your campaign', q: 'Can I move a post to another day?',
    keys: ['move', 'reschedule', 'another day', 'drag', 'different date'],
    a: 'Yes, before you approve: drag it to another day on the calendar, or change its date in the post. Picking a day that already has a post swaps them.' },
  { id: 'times', topic: 'Your campaign', q: 'What time do posts go out?',
    keys: ['what time', 'posting time', 'best time', 'schedule'],
    a: 'Resmara picks the times your audience in that area is most active, and keeps fine-tuning them. You can change a post’s time before you approve.' },
  { id: 'approve', topic: 'Your campaign', q: 'Do I have to review every post?',
    keys: ['review every', 'approve', 'approval', 'go live without', 'skip review'],
    a: 'No. Open the ones you want to check, then approve the campaign. If you haven’t opened everything, Resmara asks if you’re sure. Nothing goes live until you approve.' },
  { id: 'after-approve', topic: 'Your campaign', q: 'Can I change things after I approve?',
    keys: ['after approve', 'locked', 'already approved', 'change after'],
    a: 'Once approved, the campaign is locked and goes out as planned. You can still pause the whole campaign from My campaigns.' },
  { id: 'ad-what', topic: 'Your campaign', q: 'What does my ad look like?',
    keys: ['what ad', 'ad look', 'carousel', 'listing ad', 'meta ad'],
    a: 'One ad for the whole 14 days: a photo carousel people swipe through, or your listing video if your link had one. Open it from the calendar to flip through it.' },
  { id: 'ad-targeting', topic: 'Your campaign', q: 'Who sees my ad?',
    keys: ['who sees', 'targeting', 'audience', 'reach', 'radius', 'housing'],
    a: 'People around the listing, at least 15 miles out. Real estate ads run under Meta’s housing rules, so they can’t be targeted by age, gender or ZIP code.' },
  { id: 'compliance', topic: 'Your campaign', q: 'Are the posts Fair Housing compliant?',
    keys: ['fair housing', 'compliant', 'compliance', 'equal housing', 'license number', 'brokerage line'],
    a: 'Resmara writes about the home, never about who should buy it, and every caption ends with your name, phone, license number, brokerage and Equal Housing Opportunity.' },

  // ---- Running campaigns -----------------------------------------------------------------------
  { id: 'pause', topic: 'Running campaigns', q: 'How do I pause a campaign?',
    keys: ['pause', 'stop', 'pending', 'under contract', 'sold', 'off market', 'hold'],
    a: 'On My campaigns, click Pause on the campaign’s card. Your posts stop and your ad pauses, so Meta stops spending. Nothing is deleted. Click Resume any time.' },
  { id: 'leads', topic: 'Running campaigns', q: 'What are social leads?',
    keys: ['leads', 'comments', 'buyer interest', 'interested buyer', 'new lead'],
    a: 'When someone comments on your posts or ad showing interest in buying, Resmara emails you and lists them under Social leads on the campaign. Tick them off, remove them, or add your own.' },
  { id: 'reports', topic: 'Running campaigns', q: 'Where are my reports?',
    keys: ['report', 'results', 'performance', 'how is it doing', 'seller', 'pdf', 'stats'],
    a: 'Open the campaign and scroll to Reports. Day 7 and Day 14 reports open right there, with Download PDF to send your seller. They show reach, views, engagement and top posts, never your ad spend.' },
  { id: 'failed-post', topic: 'Running campaigns', q: 'A post didn’t go out.',
    keys: ['didn’t post', 'did not post', 'failed', 'missing post', 'not posted'],
    a: 'Resmara retries automatically and fixes what it can. If it needs you, for example if your Facebook login expired, it emails you and shows what to do. Reconnecting in Accounts sends the missed posts.' },

  // ---- Brand -----------------------------------------------------------------------------------
  { id: 'brand', topic: 'Your brand', q: 'How does Resmara know my brand?',
    keys: ['brand', 'my look', 'colours', 'colors', 'fonts', 'logo', 'style'],
    a: 'It studies your Facebook Page, Instagram and website when you connect, and builds your brand kit: colours, fonts, logo, voice and brokerage details. Check or change it any time in My Brand.' },
  { id: 'brand-wrong', topic: 'Your brand', q: 'My brand kit is wrong.',
    keys: ['brand wrong', 'wrong logo', 'wrong colour', 'update brand', 'research again'],
    a: 'Open My Brand, change anything that’s off and click Save. Research again rebuilds it from your latest pages and keeps the changes you made.' },

  // ---- Account & support -----------------------------------------------------------------------
  { id: 'password', topic: 'Your account', q: 'I forgot my password.',
    keys: ['password', 'forgot', 'reset', 'can’t log in', 'cant log in', 'locked out'],
    a: 'Click Client Login, then Forgot your password? We’ll email you a link to set a new one.' },
  { id: 'email-confirm', topic: 'Your account', q: 'I didn’t get the confirmation email.',
    keys: ['confirmation email', 'didn’t get email', 'verify email', 'no email'],
    a: 'Check your spam or promotions folder for an email from support@resmara.com. Still nothing? Send us a request from Support.' },
  { id: 'close', topic: 'Your account', q: 'How do I close my account?',
    keys: ['close account', 'delete account', 'cancel account', 'delete my data', 'data deletion'],
    a: 'Billing › Close my account. It removes your name, email and brand profile. The Data deletion page in the footer explains every option.' },
  { id: 'support', topic: 'Your account', q: 'How do I contact a person?',
    keys: ['contact', 'person', 'human', 'support', 'team', 'talk to someone'],
    a: 'Open Support and send a request. We’ll email you when we reply, and you’ll see an orange number on Support.' },
  { id: 'privacy', topic: 'Your account', q: 'What does Resmara do with my data?',
    keys: ['privacy', 'data', 'safe', 'secure', 'what do you store'],
    a: 'Only what’s needed to run your campaigns. The Privacy page in the footer lists exactly what Resmara reads from Meta and why.' }
];

// Answers the team approved from support replies (live app only), merged in on load.
if (window.RM && RM.isLoggedIn && RM.isLoggedIn() && window.fetch) {
  fetch('/api/help/answers', { credentials: 'include' }).then(r => r.ok ? r.json() : [])
    .then(rows => (rows || []).forEach(x => x && x.a && HELP_KB.push({ id: 'team-' + x.id, topic: x.topic || 'From our team', q: x.q, keys: x.keys || [], a: x.a })))
    .catch(() => {});
}

function helpNorm(s) { return String(s || '').toLowerCase().replace(/[’']/g, '’').replace(/[^a-z0-9’$.\s-]/g, ' ').replace(/\s+/g, ' ').trim(); }
// Everyday words agents use, mapped onto the words the library is written in, so
// "how do I add a house" finds "How do I start my first campaign?".
const HELP_SYNONYMS = [
  [/\b(house|home|homes|houses|property|properties|listing|listings|address|place)\b/g, 'campaign'],
  [/\b(add|create|make|launch|post|set up|setup|upload|put up|list)\b(?= (a |an |my |new |another )?(campaign|campaigns))/g, 'start'],
  [/\b(price|pricing|charge|charged|pay|paying|bill|billed|fee)\b/g, 'cost'],
  [/\b(ig|insta|fb)\b/g, 'instagram'],
  [/\b(stats|numbers|analytics|insights|results)\b/g, 'report'],
  [/\b(didnt|didn t|did not|never|wont|won t)\b (go live|post|publish|show|show up|appear)/g, 'didn’t post'],
  [/\b(quit|stop using|leave|unsubscribe)\b/g, 'close account'],
];

HELP_KB.push(
  { id: 'add-house', q: 'How do I add a house?', keys: ['add a house', 'add a home', 'add a listing', 'new listing', 'another listing', 'list a house', 'add property'],
    a: 'Each house is its own campaign. Click the orange + Campaign button on My campaigns, paste the listing link (or upload your photos), tick that you have permission to use the photos, then click Build my campaign. It’s $49 for that house, charged when you build it.' },
  { id: 'after-14', q: 'What happens after the 14 days?', keys: ['after 14 days', 'after the 14', 'when it ends', 'campaign ends', 'finished campaign', 'campaign is over', 'after two weeks'],
    a: 'The posts stop and the ad switches off on its own. The campaign moves to Completed, where your final seller report stays. If the house is still for sale, you can run it again from there.' },
  { id: 'cancel', q: 'Can I cancel?', keys: ['cancel', 'cancel my', 'stop paying', 'subscription', 'monthly fee'],
    a: 'There’s no subscription to cancel. You only pay $49 when you build a campaign. To stop a running campaign, use Pause on its card. To close your account completely, go to Billing and click Close my account at the bottom.' },
  { id: 'how-many', q: 'Can I run more than one house at once?', keys: ['more than one', 'multiple', 'several houses', 'two listings', 'at the same time', 'at once'],
    a: 'Yes. Each house is its own campaign, and you can have as many running at the same time as you like. They all show on My campaigns.' },
  { id: 'what-posts', q: 'What gets posted?', keys: ['what gets posted', 'what posts', 'how many posts', 'what will it post', 'post every day', 'daily posts'],
    a: 'Fourteen days of posts on your Facebook Page and Instagram, one a day, written in your voice from the listing. Day 1 is the listing video if there is one. Alongside them runs one ad for the house. You can read and change every post before it goes live.' },
  { id: 'where-posts', q: 'Where do the posts go?', keys: ['where do posts go', 'which page', 'my page', 'post to', 'where will it post'],
    a: 'To the Facebook Page and Instagram account you connected under Accounts. Nothing posts anywhere else.' }
);

const HELP_GO = { start: 'new-campaign', 'add-house': 'new-campaign', 'how-many': 'new-campaign', connect: 'accounts', required: 'accounts',
  'ig-personal': 'accounts', 'not-admin': 'accounts', 'no-page': 'accounts', 'no-ad-account': 'accounts', disconnect: 'accounts',
  card: 'add-card', receipts: 'billing', price: 'billing', 'when-pay': 'billing', cancel: 'close-account', close: 'close-account', refund: 'support',
  brand: 'brand', 'brand-wrong': 'brand', support: 'support', 'failed-post': 'support', reports: 'reports', leads: 'campaigns',
  pause: 'campaigns', rerun: 'campaigns', 'until-sold': 'campaigns', 'after-14': 'campaigns', 'edit-post': 'campaigns', 'move-post': 'campaigns', approve: 'campaigns', password: 'password' };
HELP_KB.forEach(e => { if (!e.go && HELP_GO[e.id]) e.go = HELP_GO[e.id]; });
const HELP_GO_LABEL = { campaigns: 'Open My campaigns', 'new-campaign': 'Start a campaign', brand: 'Open My Brand', billing: 'Open Billing',
  'add-card': 'Add a card', 'close-account': 'Go to Close my account', accounts: 'Open Accounts', support: 'Open Support', reports: 'Open my campaigns', password: 'Reset my password' };
function helpGo(where){
  const signed = typeof state !== 'undefined' && state.clientSignedIn;
  if (where === 'password' || !signed) { if (typeof clientAccess === 'function') clientAccess(); return; }
  if (where === 'new-campaign') { if (typeof newCampaign === 'function') newCampaign(); return; }
  const v = { campaigns: 'campaigns', reports: 'campaigns', brand: 'brand', billing: 'credits', 'add-card': 'credits', 'close-account': 'credits', accounts: 'accounts', support: 'support' }[where];
  if (v && typeof dashboard === 'function') dashboard(v);
  if (where === 'add-card' && typeof addPaymentCard === 'function') setTimeout(addPaymentCard, 300);
  if (where === 'close-account') setTimeout(() => { const b = document.querySelector('.billing-close'); if (b) { b.scrollIntoView({behavior: 'smooth', block: 'center'}); b.classList.add('pulse'); } }, 400);
}
function helpGoButton(where){
  const panel = document.querySelector('#pip-messages'); if (!panel || !where || !HELP_GO_LABEL[where]) return;
  const b = document.createElement('button'); b.type = 'button'; b.className = 'pip-go'; b.textContent = HELP_GO_LABEL[where] + '';
  b.addEventListener('click', () => helpGo(where)); panel.append(b); panel.scrollTop = panel.scrollHeight;
}
function helpCanon(q){ let s = ' ' + helpNorm(q) + ' '; HELP_SYNONYMS.forEach(([re, to]) => { s = s.replace(re, to); }); return s; }
function helpScore(q, e){
  const words = q.trim().split(' ').filter(w => w.length > 3);
  let s = 0;
  e.keys.forEach(k => { if (q.includes(helpNorm(k))) s += 3 + helpNorm(k).split(' ').length; });
  words.forEach(w => { if (helpNorm(e.q).includes(w)) s += 1; });
  return s;
}
function helpMatch(question) {
  const q1 = ' ' + helpNorm(question) + ' ', q2 = helpCanon(question);
  let best = null, bestScore = 0;
  HELP_KB.forEach(e => {
    const s = Math.max(helpScore(q1, e), helpScore(q2, e));
    if (s > bestScore) { bestScore = s; best = e; }
  });
  return bestScore >= 3 ? best : null;
}
function helpLogMiss(question) {
  state.helpMisses = (state.helpMisses || []).concat({ q: String(question).slice(0, 300), at: new Date().toISOString() }).slice(-50);
  persist();
  if (window.RM && RM.isLoggedIn && RM.isLoggedIn() && window.fetch) {
    fetch('/api/help/misses', { method: 'POST', credentials: 'include', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ question: String(question).slice(0, 300) }) }).catch(() => {});
  }
}

// The chat itself: quick buttons for the four most asked, then free text matched to the library.
const HELP_QUICK = ['start', 'connect', 'price', 'reports'];
pipAnswer = function (n) {
  const e = HELP_KB.find(x => x.id === HELP_QUICK[n]) || HELP_KB[0];
  pipMessage(e.q, true); pipMessage(e.a); helpGoButton(e.go);
};
pipFreeText = function (q) {
  if (!String(q || '').trim()) return;
  pipMessage(q, true);
  helpAskAI(q);
};
// Needs POST /api/help/ask from the back end: it sends the question and this library to the
// model and returns {answer, sure}. The model may only use what the library says; when it is not
// sure it says so, and the question goes to the team as before.
async function helpAskAI(q){
  const panel = document.querySelector('#pip-messages');
  const wait = document.createElement('div'); wait.className = 'pip-reply pip-typing'; wait.textContent = 'Thinking…';
  if (panel) { panel.append(wait); panel.scrollTop = panel.scrollHeight; }
  let r = null;
  try {
    const ctl = new AbortController(); const t = setTimeout(() => ctl.abort(), 9000);
    const headers = { 'Content-Type': 'application/json' };
    try { const tok = localStorage.getItem('resmara_token'); if (tok) headers.Authorization = 'Bearer ' + tok; } catch (x) {}
    const res = await fetch('/api/help/ask', { method: 'POST', credentials: 'include', headers, signal: ctl.signal,
      body: JSON.stringify({ question: String(q).slice(0, 500), page: typeof view !== 'undefined' ? view : '', history: helpHistory.slice(-6) }) });
    clearTimeout(t);
    if (res.ok) r = await res.json();
  } catch (err) {}
  wait.remove();
  if (r && r.answer && r.sure !== false) { pipMessage(r.answer); helpGoButton(r.go); helpHistory.push({q: q, a: r.answer}); return; }
  // No AI (or it was not sure): the built-in library, then a person.
  const e = helpMatch(q);
  if (e) { pipMessage(e.a); helpGoButton(e.go); helpHistory.push({q: q, a: e.a}); if (e.ticket) pipOfferTicket(q); return; }
  helpLogMiss(q);
  pipOfferTicket(q);
}
const helpHistory = [];
(function () {
  const box = document.querySelector('.pip-questions');
  // No suggested questions: the agent just asks.
  if (box) box.remove();
  const note = document.querySelector('.pip-demo-note');
  if (note) note.textContent = 'Ask me anything about Resmara. If I don’t know, I’ll pass it to the team.';
})();
