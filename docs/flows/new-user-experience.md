# New user experience: how it's supposed to work

**Owner:** Adam (front end) · **Backend:** Dan · **Last updated:** PR #10, 19 Nov 2026

This doc describes what a brand-new agent sees from sign-up to their first live campaign:

- every screen and what each button does;
- where each step sends them;
- what changes when their Meta setup isn't right;
- what the server has to do for each step to work.

If the app and this doc disagree, one of them is wrong. Flag it rather than guess.

> **The rule for every PR from now on.** If a PR changes how an agent moves through the app, it
> updates the flow doc for that part (or adds one in `docs/flows/`). The PR description links to
> it. Read the doc first, then review the code against it.

---

## 1. The journey at a glance

| # | Stage | What the agent does | Where it ends |
|---|-------|---------------------|---------------|
| 1 | Sign up | Clicks **Client Login**, then **Create an account**. Enters first name, last name, email and password. | Confirm-email screen |
| 2 | Confirm email | Clicks the link in the email, then signs in. | Accounts page, with Step 1 open on top |
| 3 | Step 1: Connect Meta | Logs in with Facebook. Resmara checks 4 things (section 3). | Green light, or "connected, with limits", or "You're in, with one thing to fix" (no Page), or the no-Facebook stop |
| 4 | Step 2: Your brand | Nothing. Resmara builds the brand kit on its own. | "Your brand kit is ready", with **Next** |
| 5 | Step 3: Quick tour | Clicks through 7 tips, or **Skip the tour**. | My campaigns, with the **+ Campaign** button pulsing |
| 6 | First campaign | Clicks **+ Campaign** and pastes the listing link. Resmara checks the link. | Campaign page (draft) |
| 7 | Build and pay | Clicks **Build my campaign**. Adds a card first if there isn't one ($49). | Campaign calendar to review |
| 8 | Approve | Approves the campaign. | Live campaign page, which is locked |

The step bubbles on the pop-ups read **1 Connect Meta · 2 Your brand · 3 Quick tour**.

---

## 2. Where the agent lands (redirect map)

| Event | Lands on | Pop-up shown |
|-------|----------|--------------|
| New account created and email not confirmed yet | Homepage | "Confirm your address", with **Send it again** |
| First sign-in after confirming | **Accounts** | Step 1: Connect Meta |
| Sign-in when the Meta Page is still **not** connected and no setup call is booked | **Accounts** | Step 1: Connect Meta |
| Sign-in after the Facebook login worked but no Page was found | My campaigns | None. The **red box** shows at the top, and campaigns can be built |
| Sign-in when Facebook was never connected but a setup call **is** booked | My campaigns | None. **+ Campaign** shows "Connect your Meta account first" |
| Sign-in when the Page is connected but Instagram or the ad account isn't | My campaigns | None. The **red box** shows at the top |
| Sign-in with everything connected, tour not done | My campaigns | Step 2 (or Step 1 if not connected) |
| Sign-in with everything done | My campaigns | None. A "Signed in as…" toast |
| Agent closes Step 1 without connecting | **Accounts** | "Please connect your Meta account" (unless a call is booked) |
| **+ Campaign** clicked before any Facebook login | Stays put | "Connect your Meta account first" |
| **Don't have Facebook?** clicked on Step 1 | Stays put | "You'll need a Facebook account first" |

"Connected" means **the Facebook Page is connected and the agent is an admin of it**. Instagram
and the ad account are *not* needed to be connected (section 3).

**What unlocks campaigns** is the Facebook login itself (`state.metaChecked`), not the Page. An
agent with Facebook but no Page can build and pay for campaigns. They download their posts until
the Page is connected (section 6). Only an agent with **no Facebook at all** is blocked.

All sign-ins go through `metaGateOnLogin()` in `static/onboarding.js`. It reads the account state
from `/api/onboarding/state` and then the four checks from `/api/onboarding/meta-audit`.

---

## 3. The Meta check: the five scenarios

Step 1 checks four things, in this order. The numbers are the indexes the front end uses
(`state.metaIssues`):

| Index | Check (server key) | Required? | If it fails |
|-------|--------------------|-----------|-------------|
| 0 | Facebook Page found (`page`) | **Yes** | Campaigns can't post |
| 1 | Agent is admin of the Page (`page_admin`) | **Yes** | Campaigns can't post |
| 2 | Instagram is a business (Professional) account linked to the Page (`instagram`) | No | Posts go to Facebook only |
| 3 | Ad account with a payment method (`ad_account`) | No | Posts go out, but the listing ad is off |

**The rule:** only a Facebook login is required to use Resmara. Everything after that limits the
campaign but never locks the agent out:

- **No Page:** posts are downloaded and shared by hand.
- **No Instagram:** posts go to Facebook only.
- **No ad account:** no ad.

**Price:** $49 per campaign whatever is connected. Every campaign costs the same to build (posts,
listing page and ad creative are all made by the AI either way), so there's no cheaper version.
We'll revisit only if agents ask for one.

### What the agent sees in each case

To test these in the preview, pick one in the **What should we test?** list after **Client Login**
(section 9).

| Scenario | Result screen | Main button | Can run campaigns? | Red box |
|----------|---------------|-------------|--------------------|---------|
| Everything set up | "You're connected." (green) | **Build my brand** | Yes, full: Facebook, Instagram and the ad | None |
| No ad account | "You're connected, with a couple of limits." | **Continue** | Yes: Facebook and Instagram posts, **no ad** | Yes |
| Instagram is personal | "You're connected, with a couple of limits." | **Continue** | Yes: **Facebook posts only**, plus the ad | Yes |
| Not an admin of the Page | "You're in, with one thing to fix." | **Continue** | Yes, but posts are **downloaded** until the Page is connected; no ad | Yes |
| No Facebook business Page | "You're in, with one thing to fix." | **Continue** | Yes, but posts are **downloaded** until the Page is connected; no ad | Yes |
| No Facebook account at all | "You'll need a Facebook account first." | **Open Facebook** (new tab) and **I've set it up** | **No.** They can look around; + Campaign is blocked | None. Accounts shows the connect prompt |

Every non-green result screen also has:

- **Book a free setup call** (opens the Calendly booking inside the pop-up);
- a **Check again** link;
- a dark-blue note: "We'll set it up with you…".

The limits line the agent reads (`metaLimitLine()`):

- **Instagram personal:** "Your campaigns can still run, with limited reach: posts go to your Facebook Page only, not Instagram, until it's fixed."
- **No ad account:** "…your posts go out, but your listing ad is off until it's fixed."
- **Both:** "…posts go to your Facebook Page only, and your listing ad is off until it's fixed."
- **Page missing or not admin:** "Resmara still builds your campaigns and listing page. Until a Facebook Page is connected, you download each post and share it yourself. Once it's connected, the rest go out on schedule."

### Other situations, and what should happen

These can't be picked in the preview, but the app has to handle them. The ones marked **server**
are Dan's.

| Situation | What should happen |
|-----------|--------------------|
| Agent closes or cancels the Facebook login window | Back to Step 1, still not connected. Closing Step 1 lands on Accounts with the connect prompt. |
| Agent unticks Instagram or the ad account in Facebook's permission screen | Shows as that check failing (same as no Instagram or no ad account). The red box explains it, and reconnecting fixes it. |
| Agent has several Pages and picked the wrong one | Accounts, **Reconnect**, then choose the right Page. |
| Instagram is linked to a different Page (an old one, or the brokerage's) | Same as Instagram not connected. The guide says to disconnect it from the old Page first. |
| Ad account exists but has no card, or Meta disabled it | Same as no ad account: "Your ad account can't run ads yet". Posts still go out. |
| **server:** connection breaks later (Facebook password changed, access removed, token expired) | Red box "Your Meta connection needs refreshing", with **Reconnect**. Scheduled posts are held, not lost, and go out after reconnecting. |
| **server:** Page connected after a campaign has started | From then on, posts go out on schedule. Posts whose time has already passed are **not** sent late; the agent had them to download. |
| Agent doesn't know how to fix something | Every screen links to the matching **Setup** step (section 8) and to **Book a free setup call**. |

---

## 4. The red box (every dashboard page and campaign)

- **When it shows:** the last Meta check found any issue (`state.metaIssues` is not empty).
- **Where:** the top of every dashboard page (My campaigns, My Brand, Billing, Accounts, Support)
  and every campaign page.
- **What it says:**
  - Title: "There's an issue with your Meta account."
  - One bullet per issue, for example "Your Instagram isn't connected as a business account."
  - The limits line from section 3.
- **Buttons:**
  - Three buttons in one row, all the same size: **Fix it now** (orange), **Book a call to fix it**
    and **Check again** (dark blue).
  - **Fix it now** opens the Instagram pop-up (section 5) when that's the issue and a Page is
    connected. Otherwise it opens the Setup step for the first issue (`metaFixAction()`).
  - **Book a call to fix it** opens the setup-call booking. **Check again** re-runs Step 1.
- With no Page, the "not an admin" bullet is hidden, because it would only repeat the first one.
- **When it goes away:** the next check passes all four items. The check runs on every sign-in
  and every time **Check again** is clicked.

---

## 5. The Instagram switch pop-up

- **Why it exists:** Meta has no API that lets an app turn a personal Instagram into a Professional
  account. Facebook's own **Connect account** flow does convert it, while it links the Instagram
  to the Page. This pop-up explains that and then sends the agent there.
- **Opened from:**
  - **Fix it now** in the red box;
  - **Fix it now** on the Step 1 result screen (it sits next to **Continue**).
- **Content:**
  - Title: "Switch your Instagram to a business account."
  - Four facts: it's free and takes about a minute; posts and followers stay; they gain a
    Contact button and post stats; the account must be public.
  - Five numbered steps.
- **Buttons:**
  - **Back:** returns to the Step 1 result, or closes the pop-up if onboarding is done.
  - **Check again:** re-runs the check.
  - **Open Facebook to switch** (orange): opens
    `https://www.facebook.com/settings/?tab=linked_instagram` in a new tab.
  - "Stuck? See the full guide or book a free setup call" links at the bottom.

---

## 6. Brand, tour and first campaign

- **Step 2, Your brand.**
  - Resmara reads the Facebook Page, Instagram posts and website, then builds the brand kit.
  - The agent answers nothing.
  - Buttons: **Review my brand** (goes to My Brand) or **Next**.
- **Step 3, Quick tour.** First login only. It's stored on the account, so a new browser doesn't
  replay it. The tips, in order:
  1. + Campaign
  2. Campaign tabs
  3. My Brand
  4. Billing, with **Add a card now**
  5. Accounts
  6. Support
  7. "Let's build your first campaign", with + Campaign pulsing
- **New campaign.**
  - The agent pastes the listing link. Resmara opens the link for real
    (`POST /api/content/listing/check`).
  - Results:
    - a sign-in page, a dead link or no listing **fails**, with a message;
    - a portal with no photos asks for a photo upload;
    - a good listing gets a green light.
- **Build my campaign.**
  - $49, charged to the card on file.
  - With no card, the agent sees "Add a card to build your campaign" first and goes to Stripe's
    page.
  - Ad spend is billed by Meta, separately.
- **Live campaign page.** Four sections, in this order, each collapsible:
  1. Campaign leads (website leads above comment leads)
  2. Campaign calendar
  3. Your listing page
  4. Reports
- **Locked.** Once live, nothing can be edited except **Withdraw post** (orange) in a post's pop-up,
  for posts that haven't gone out yet.
- **No Page connected.** Each post's pop-up also has **Download post**. It saves the photo and copies
  the caption, with the toast "Photo downloaded. Caption copied, ready to paste." The listing page
  still works, so the agent can share its link (see `listing-page.md`).

---

## 7. What the server has to do (Dan)

The front end in PR #10 depends on these. The items marked **check** may not be true yet.

1. **`GET /api/onboarding/meta-audit`** returns `checks` with keys `page`, `page_admin`,
   `instagram`, `ad_account`. It already does. The front end now maps these straight into the red
   box (`applyMetaChecks()`).
2. **check: "connected" must mean the Page only.** `meta_connected()` currently needs an
   active `AdAccount` row with a token. An agent with a Page but **no ad account** has to come out
   as connected. Otherwise they're sent back to Accounts on every sign-in, and + Campaign stays
   blocked.
2a. **check: the Facebook login is recorded even with no Page.** An agent who logs in with Facebook
   but has no Page must still get a stored connection. The audit's checks then come back as
   answered (not "Not connected"), which is how the front end knows to unlock campaigns. Creating
   and paying for a campaign must not require a Page on the server either.
3. **check: Check again must re-read Instagram from Meta.** `ig_ok` is read from the stored
   `account.ig_user_id`. After the agent switches and links their Instagram on Facebook, the stored
   value is still empty. The audit needs to re-query the Page
   (`/{page-id}?fields=instagram_business_account`) and save the new id. If it doesn't, Check
   again never turns green without a full reconnect.
4. **check: the publisher posts to what's connected.**
   - No `ig_user_id` means Facebook posts only.
   - No Page means nothing is sent; the posts stay downloadable.
   - Neither case fails the campaign or marks it failed.
   - When a Page is connected mid-campaign, only posts still in the future go out.
5. **check: no ad account means no ad.** The campaign's posts still run, and the ad step is
   skipped, not errored. The price stays $49 (section 3).
6. **New in PR #10:**
   - `POST /api/content/listing/check` (the real link check);
   - `PATCH /api/posts/{id}/withdraw` (refuses with 409 if the post has already gone out).

---

## 8. Setup page (website)

- **Where:** **Setup** in the top menu of the website, next to **Home** (`#setup-guides`). It's
  also linked from:
  - the "Before your first campaign" band on the homepage;
  - the no-Facebook screen;
  - the Step 1 result;
  - **Fix it now** in the red box;
  - the Instagram pop-up;
  - the help chat.
- **The page:** a "what you need" row (Page, Instagram, ad account) and then seven step cards,
  in the homepage's own card, number-bubble and button style.
- **The seven steps:**
  1. Facebook account
  2. Business Page
  3. Full control of the Page
  4. Business Instagram
  5. Link Instagram to the Page
  6. Ad account with a payment method
  7. Connect it all to Resmara
- **How they open:** `setupGuides('instagram')` opens one guide directly. The red box opens the
  guide for the first issue: `page`, `admin`, `instagram` or `ads`.
- **Keeping them current:** Meta renames menus from time to time. If an agent says a step doesn't
  match, update `SETUP_GUIDES` in `static/homepage.js`.

---

## 9. How to test it

Preview copy: https://claude.ai/artifact/Lip2AN9HQZuLf4J5AsP8Vy

- **`#new`:** start as a brand-new client. Click **Client Login** and pick a Meta scenario from
  section 3. Then go through sign-up, the confirm email, sign-in and Step 1.
- **`#setup-guides`:** the Setup page.
- **`#instagram`:** jumps straight to a signed-in agent with a personal Instagram. The red box and
  **Fix it now** are showing.
- **No hash:** the normal demo agent, everything connected.
- In the hosted preview, **reload the page after changing the `#` part of the address**. The
  preview only reads it when the page loads.
- Preview only: **Check again** acts as if the agent fixed everything.

On the live site, test each scenario with a real Facebook test user. Use one with no ad account,
then one with a personal Instagram. Confirm each lands where section 2 says.
