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
    a: 'Click the orange ＋ Campaign button at the top of My campaigns. Paste any link to the home (your photographer’s link with all the photos and video works best), tick the photo permission box and click Build my campaign. Resmara builds 14 posts, your ad and your listing page, then you pay to unlock it, set your go-live date, review and approve.' },
  { id: 'what', topic: 'Getting started', q: 'What does Resmara do?',
    keys: ['what is resmara', 'what does resmara do', 'what do i get', 'included', 'what comes with'],
    a: 'For each listing, Resmara builds a 14-day campaign in your brand: 14 social posts for Facebook and Instagram plus one Meta ad. It posts them for you, flags people who comment with buying interest, and gives you Day 7 and Day 14 reports to share with your seller.' },
  { id: 'need', topic: 'Getting started', q: 'What do I need before I can run a campaign?',
    keys: ['need', 'requirements', 'before i start', 'what do i need', 'set up'],
    a: 'Just a Facebook login and your listing link. For the full campaign: a Facebook business Page you have full control of, a business Instagram linked to it, and a Meta ad account with a payment method. Resmara checks all of this when you log in, and you pay for each campaign after it’s built.' },

  // ---- Meta connection -------------------------------------------------------------------------
  { id: 'connect', topic: 'Your Meta account', q: 'How do I connect my Facebook and Instagram?',
    keys: ['connect', 'facebook', 'instagram', 'meta account', 'link my', 'log in with facebook'],
    a: 'Logging in with Facebook connects them: Resmara finds your Page, Instagram and ad account on its own. If you have more than one Page it asks which is your business. Accounts shows what’s set up, with Walk me through it for anything missing. Resmara then checks everything is ready to post and run ads.' },
  { id: 'required', topic: 'Your Meta account', q: 'Why do I have to connect Meta?',
    keys: ['why connect', 'skip', 'do i have to', 'without facebook', 'required', 'must connect'],
    a: 'Only a Facebook login is required. Resmara posts to your own Page and Instagram and runs ads from your own ad account; anything that isn’t set up yet limits the campaign but never locks you out. Without a Page, you download each post and share it yourself. Walk me through it in Accounts, or book a free setup session for a hand.' },
  { id: 'setup-guides', topic: 'Your Meta account', q: 'How do I set up my Facebook, Instagram and ad account for Resmara?',
    keys: ['set up facebook', 'setup guide', 'create a page', 'no facebook', 'business page', 'ad account', 'how do i set up', 'get ready'],
    a: 'Open Setup in the menu at the top of our website. There’s a short step-by-step guide for each piece: a Facebook account, a business Page, full control of the Page, a business Instagram, linking Instagram to the Page, and an ad account with a payment method. Only the Page is required. Prefer help? Book a free setup call.' },
  { id: 'no-facebook', topic: 'Your Meta account', q: 'I don’t have Facebook. Can I still use Resmara?',
    keys: ['dont have facebook', 'don’t have facebook', 'no facebook', 'without facebook'],
    a: 'You’ll need a Facebook account and a business Page first. Resmara learns your brand from Facebook and posts to your Page. It’s free and takes about 15 minutes; the Setup page on our website walks you through it, or book a free setup call and we’ll do it with you.' },
  { id: 'no-page-campaign', topic: 'Your Meta account', q: 'Can I run a campaign before my Facebook Page is connected?',
    keys: ['before my page', 'page not connected', 'download post', 'post it myself', 'without a page'],
    a: 'Yes. Resmara still builds your 14 posts, your ad and your listing page. Until your Page is connected, open each post in your campaign calendar and click Download post to save the photo and copy the caption to share yourself. Once your Page is connected, the rest go out on schedule automatically. The campaign is $49 either way.' },
  { id: 'ig-personal', topic: 'Your Meta account', q: 'It says my Instagram isn’t a business account.',
    keys: ['instagram isn', 'personal account', 'business account', 'professional account', 'creator'],
    a: 'Click Fix it now in the Meta notice at the top of your dashboard. It opens Facebook’s linked accounts page, where you click Connect account next to Instagram and choose Business when Facebook asks. That switches your account and links it to your Page in about a minute, and you keep all your posts and followers. Then come back and click Check again. Prefer help? Book a free setup call.' },
  { id: 'not-admin', topic: 'Your Meta account', q: 'It says I’m not an admin of the Page.',
    keys: ['admin', 'not an admin', 'page access', 'full control', 'manage the page'],
    a: 'Ask whoever manages the Page to give you full control in the Page’s settings, then come back to Accounts and click Check again.' },
  { id: 'no-page', topic: 'Your Meta account', q: 'I don’t have a Facebook business Page.',
    keys: ['no page', 'business page', 'facebook page', 'create a page', 'personal profile'],
    a: 'Resmara posts to a Facebook business Page, not your personal profile. Create one from Facebook’s menu › Pages › Create new Page, then come back to Accounts and click Check again. A free setup session can walk you through it.' },
  { id: 'no-ad-account', topic: 'Your Meta account', q: 'It says I have no ad account ready.',
    keys: ['ad account', 'payment method', 'ads manager', 'no ad account', 'billing in meta'],
    a: 'Your listing ad runs from your own Meta ad account, and Meta needs a card on it to bill your ad budget. Add one in Meta Ads Manager › Billing, then come back to Accounts and click Check again.' },
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
    a: 'Any link to the home works: it tells Resmara which house it is, then Resmara gathers the details and photos from every source it can reach. The link from your photographer with all the photos and video works best. An MLS public client link is fine too; it just shouldn’t need your MLS sign-in.' },
  { id: 'zillow', topic: 'Your listing', q: 'Can I use a Zillow or Realtor.com link?',
    keys: ['zillow', 'realtor.com', 'redfin', 'trulia', 'homes.com'],
    a: 'Yes. The link tells Resmara which house it is, and it looks for the photos on every source it can reach. If it still can’t get 14, it asks for your photographer’s link or an upload.' },
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
    a: 'Each campaign is $49. Resmara builds it first, then you pay to unlock it, review it and launch it. No subscription. Your ad budget is separate and paid to Meta.' },
  { id: 'when-pay', topic: 'Pricing and billing', q: 'When am I charged?',
    keys: ['when am i charged', 'when do i pay', 'charge', 'charged', 'payment'],
    a: 'After your campaign is built. It opens blurred with Pay to unlock: pay on the card right there, and tick Save this card so your next campaign unlocks as soon as it’s built. Choose Later and it waits, locked, on My campaigns. Reviewing, approving and launching don’t cost anything extra.' },
  { id: 'ad-budget', topic: 'Pricing and billing', q: 'How does the ad budget work?',
    keys: ['ad budget', 'ad spend', 'budget', 'meta bills', 'how much on ads', '$50'],
    a: 'You choose a total ad budget for the whole 14 days (default $50). Meta bills it to the card on your own ad account. Resmara keeps none of it, and it isn’t part of the $49.' },
  { id: 'card', topic: 'Pricing and billing', q: 'How do I add or change my card?',
    keys: ['add a card', 'change card', 'update card', 'credit card', 'payment method', 'stripe'],
    a: 'Go to Billing and click Add a card (or Change card). Stripe’s card form opens right in the pop-up, and Resmara never sees your card number.' },
  { id: 'receipts', topic: 'Pricing and billing', q: 'Where are my receipts?',
    keys: ['receipt', 'invoice', 'purchases', 'history'],
    a: 'Billing › Purchases lists everything you’ve paid for, with any tax, the status and a Receipt link for each.' },
  { id: 'until-sold', topic: 'Pricing and billing', q: 'Can Resmara keep running my listing until it sells?',
    keys: ['until it sells', 'until sold', 'autopilot', 'keep running', 'every 2 weeks', 'every two weeks', 'auto renew', 'automatic'],
    a: 'Yes. Turn on Run it until it sells in Launch details, or click Run until sold on the campaign card. Every 2 weeks Resmara builds a brand-new campaign, 14 new posts and a new ad, from what worked last time, and it goes live on its own the day the last one ends: set it and forget it. We email you at every turn. $39 per renewal, charged only once the new round is built, and your ad budget runs again each round, billed by Meta. If the listing goes pending it pauses (and picks up again if it comes back on the market); when it sells, it ends. If your card is declined we try again for 3 days, then email you to check your billing.' },
  { id: 'rerun', topic: 'Pricing and billing', q: 'Can I run a campaign again?',
    keys: ['again', 'rerun', 're-run', 'second campaign', 'another campaign', 'still for sale', 'renew'],
    a: 'Yes. Open a completed campaign and click Run it again ($39). Resmara builds 14 brand-new posts and a new ad with fresh angles on the same home, charges your card on file once it’s built, and it goes live the next morning. Nothing else to do.' },
  { id: 'refund', topic: 'Pricing and billing', q: 'Can I get a refund?',
    keys: ['refund', 'money back', 'cancel campaign'],
    a: 'Send the team a request from Support with the campaign’s address, and we’ll look at it with you.' },

  // ---- Building & reviewing --------------------------------------------------------------------
  { id: 'build-time', topic: 'Your campaign', q: 'How long does the build take?',
    keys: ['how long', 'build take', 'waiting', 'building'],
    a: 'Usually a minute or two. You can watch the progress, and you land on your campaign page with the calendar ready when it’s done.' },
  { id: 'launch-details', topic: 'Your campaign', q: 'What are launch details?',
    keys: ['launch details', 'go-live', 'go live date', 'start date', 'when does it start'],
    a: 'Three things at the top of your campaign: your go-live date (when posts and the ad start), where clicks go (the listing page Resmara builds for the home, unless you paste your own page), and your ad budget.' },
  { id: 'clicks', topic: 'Your campaign', q: 'Where do people go when they click?',
    keys: ['clicks go', 'send clicks', 'destination', 'my website', 'landing page', 'crm'],
    a: 'To the listing page Resmara builds for the home, in your brand, with your phone number and a form. To send them to your own page instead, paste it in Send clicks to on the campaign page.' },
  { id: 'edit-post', topic: 'Your campaign', q: 'How do I change a post?',
    keys: ['edit', 'change a post', 'caption', 'title', 'replace photo', 'swap photo', 'change photo'],
    a: 'Click any post on the calendar or in Gallery. Change its title and caption, or click Pick from this home’s photos to swap the photo (Upload your own is in there too): Resmara redraws the post on the new photo with the same words and your details. Change its date and time, then click Save and mark reviewed. Edits that describe who the home is for can’t be saved, because of Fair Housing law.' },
  { id: 'move-post', topic: 'Your campaign', q: 'Can I move a post to another day?',
    keys: ['move', 'reschedule', 'another day', 'drag', 'different date'],
    a: 'Yes, before you approve: drag it to another day on the calendar, or change its date in the post. Picking a day that already has a post swaps them.' },
  { id: 'times', topic: 'Your campaign', q: 'What time do posts go out?',
    keys: ['what time', 'posting time', 'best time', 'schedule'],
    a: 'When your audience is online most, if Meta tells us, otherwise in the evening when most people scroll, and only between 6 AM and 11 PM your time. Your ad never runs between 11 PM and 6 AM. You can change a post’s time before you approve.' },
  { id: 'thumbs', topic: 'Your campaign', q: 'What are the thumbs up and down for?',
    keys: ['thumbs', 'like this style', 'thumbs up', 'thumbs down', 'gallery', 'learn my style'],
    a: 'Tap 👍 or 👎 on any post (in Gallery or inside the post) to teach Resmara your style. No reason needed. Each campaign leans toward what you liked, with a few new styles so it never repeats. See what it learned on My Brand. Approving a campaign untouched counts as a like.' },
  { id: 'hashtags', topic: 'Your campaign', q: 'How are hashtags chosen?',
    keys: ['hashtag', 'hashtags', 'tags', '#'],
    a: 'Three to five on Instagram and up to two on Facebook, at the end of the caption: one for your area, one for your market, one for what the post shows, and your own hashtag (set it on My Brand). No giant generic tags, and they change post to post.' },
  { id: 'ig-links', topic: 'Your campaign', q: 'Why is there no link in my Instagram caption?',
    keys: ['instagram link', 'link in caption', 'link in bio', 'clickable'],
    a: 'Instagram doesn’t make links in captions clickable, and a pasted web address looks broken. So the Instagram caption ends with an invitation instead, like “Comment TOUR and I’ll send you the details”, and those comments come in as leads. The Facebook caption can carry the link.' },
  { id: 'needs-look', topic: 'Your campaign', q: 'What does Needs a look mean?',
    keys: ['needs a look', 'flagged', 'fallback'],
    a: 'Resmara checks every design. If one didn’t pass twice, it uses Resmara’s own clean layout with your words drawn exactly, and flags it so you can glance at it before you approve. Swap the photo or edit the words if you’d like it different.' },
  { id: 'approve', topic: 'Your campaign', q: 'Do I have to review every post?',
    keys: ['review every', 'approve', 'approval', 'go live without', 'skip review'],
    a: 'No. Open the ones you want to check, then approve the campaign. If you haven’t opened everything, Resmara asks if you’re sure. Nothing goes live until you approve.' },
  { id: 'after-approve', topic: 'Your campaign', q: 'Can I change things after I approve?',
    keys: ['after approve', 'locked', 'already approved', 'change after'],
    a: 'Once approved, the campaign is locked and goes out as planned. You can still pause the whole campaign from My campaigns.' },
  { id: 'ad-what', topic: 'Your campaign', q: 'What does my ad look like?',
    keys: ['what ad', 'ad look', 'carousel', 'listing ad', 'meta ad'],
    a: 'One ad for the whole 14 days, built to stop the scroll: a short, true-to-the-house hook in a few big words over your strongest photo, plus your details, in up to 3 versions so Meta can spend on the one people click. If your link had a listing video, the video ad runs alongside. It shows in the Facebook and Instagram feeds, Marketplace, Stories and Reels, between 6 AM and 11 PM.' },
  { id: 'ad-targeting', topic: 'Your campaign', q: 'Who sees my ad?',
    keys: ['who sees', 'targeting', 'audience', 'reach', 'radius', 'housing'],
    a: 'People around the listing, at least 15 miles out. Real estate ads run under Meta’s housing rules, so they can’t be targeted by age, gender or ZIP code.' },
  { id: 'compliance', topic: 'Your campaign', q: 'Are the posts Fair Housing compliant?',
    keys: ['fair housing', 'compliant', 'compliance', 'equal housing', 'license number', 'brokerage line'],
    a: 'Resmara writes about the home, never about who should buy it, and checks every caption, hashtag, ad and edit against Fair Housing law and Meta’s ad rules. Every post carries your name, phone, license number, brokerage and Equal Housing Opportunity.' },

  // ---- Running campaigns -----------------------------------------------------------------------
  { id: 'pause', topic: 'Running campaigns', q: 'How do I pause a campaign?',
    keys: ['pause', 'stop', 'pending', 'under contract', 'sold', 'off market', 'hold'],
    a: 'On My campaigns, click Pause on the campaign’s card and choose Just pause it, It’s pending or It sold. Your posts stop and your ad pauses, so Meta stops spending. Nothing is deleted. If it’s pending or sold, your website also stops taking showing requests. Resmara also checks the listing every hour and pauses on its own the moment it shows pending or sold. Click Turn it back on any time (not after it sells), and you get the paused days back.' },
  { id: 'leads', topic: 'Running campaigns', q: 'What are campaign leads?',
    keys: ['leads', 'comments', 'buyer interest', 'interested buyer', 'new lead', 'social leads', 'website leads', 'listing page', 'form', 'calls'],
    a: 'Campaign leads are people who asked about your listing. Some fill in the form or tap Call or Text on the website Resmara builds for the home; others comment on your posts or ad showing interest in buying. Resmara emails you form leads and buyer comments the moment they come in, and lists every lead under Campaign leads on the campaign: website leads first, then comments. Tick them off, remove them, or add your own.' },
  { id: 'withdraw-post', topic: 'Running campaigns', q: 'Can I stop one post?',
    keys: ['withdraw', 'stop a post', 'cancel a post', 'remove a post', 'pull a post', 'take down'],
    a: 'Yes. Once your campaign is approved the posts are locked, but you can still pull one before it goes out. Open the campaign, click the post on the calendar, then click Withdraw post. The rest of your campaign keeps running. A post that has already gone out has to be removed from your Facebook Page or Instagram.' },
  { id: 'listing-page', topic: 'Running campaigns', q: 'What is my listing page?',
    keys: ['listing page', 'website', 'landing page', 'property page', 'site', 'link', 'where do clicks go'],
    a: 'Resmara builds a website for every listing at homes.resmara.com, in your brand, with the campaign: it tells the home’s story in four chapters, with every photo, the facts, your note, your phone and a form. Every post and your ad send people there, so you never need to paste a link. Under 3 Your listing page on the campaign you can Preview your website, Copy link and Share it, and see its visits, form leads, call leads and text leads. The price shows only when the listing sites agree on it; if it changes and we can’t find the new number, we email you to set it.' },
  { id: 'reports', topic: 'Running campaigns', q: 'Where are my reports?',
    keys: ['report', 'results', 'performance', 'how is it doing', 'seller', 'pdf', 'stats'],
    a: 'Open the campaign and scroll to Reports. Day 7 and Day 14 reports open right there, and we email you when each one is ready. Download PDF gives you your full report (ad spend, cost per click, leads by source, website visits and what Resmara changed in your ad). Seller version gives you a copy in your name to send your seller, with reach, views, engagement and clicks, and never any cost or spend.' },
  { id: 'failed-post', topic: 'Running campaigns', q: 'A post didn’t go out.',
    keys: ['didn’t post', 'did not post', 'failed', 'missing post', 'not posted'],
    a: 'Resmara retries automatically and fixes what it can. If it needs you, for example if your Facebook login expired, it emails you and shows what to do. Reconnecting in Accounts sends the missed posts.' },

  // ---- Brand -----------------------------------------------------------------------------------
  { id: 'brand', topic: 'Your brand', q: 'How does Resmara know my brand?',
    keys: ['brand', 'my look', 'colours', 'colors', 'fonts', 'logo', 'style'],
    a: 'When you log in with Facebook, Resmara looks you up: your Page, Instagram, website, your brokerage and the state license lookup. It builds your brand kit, including a Voice of the client paragraph that every post is written from. Anything it couldn’t find, like a license number, stays blank and is asked for when you start a campaign. Change anything in My Brand.' },
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
    a: 'Billing › Close my account, then type your account email to confirm. Your posts and ads stop, Run it until it sells turns off, your listing websites come down and your saved card is removed. Nothing is refunded. Log in with Facebook within 30 days to reopen it; after that your details are deleted.' },
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
    const ctl = new AbortController(); const t = setTimeout(() => ctl.abort(), 12000);
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
