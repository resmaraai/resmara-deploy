# Slice 1 audit: the brains vs the code (23 Nov 2026, 3:30 PM)

**Slice 1 = sign-up to first campaign:** Sign-up & Facebook connection (Engine 1), Brand kit
(Engine 2), the sign-up tour, Listing link check (Engine 3), Campaign build & pay to unlock
(Engine 4).

Read from `resmaraai/resmara-deploy` main at `fa4ddb5` (Dan's last push, 3:06 PM), against the
newest brain for each engine. Anything Dan's AI has on its own machine and hasn't pushed isn't
in here.

**Key:** ✅ in the code · 🟡 partly · ❌ missing

---

## Sign-up & Facebook connection (Engine 1)

### Part A: the account (built today by Dan's AI, from the brain)

| Brain decision | Status | Where |
|---|---|---|
| One "Log in with Facebook" door for new and returning clients | ✅ | `app/api/facebook_login.py`, `homepage.js` |
| Terms box gates it; agreement stored (version, time, IP, browser) | ✅ | `facebook_login.py` |
| Same Facebook always lands on the same account | ✅ | `users.facebook_id` unique |
| Facebook hides the email → ask once | ✅ | `PATCH /api/auth/me/email` |
| Close (reversible) vs delete (permanent) | ✅ | `/me/close`, `/facebook/reactivate` |
| Welcome + day 3 / 7 / 14 emails, stop at first launch | ✅ | `onboarding_emails.py` |
| Email to Adam on every sign-up | ✅ | `_notify_owner_new_account` |
| Bot protection | 🟡 | rate limit built; Turnstile needs keys |
| Email + password removed | 🟡 | kept on purpose as a fallback until Meta App Review approves `email` |
| No teams | ✅ | nothing models a team |

### Part B: the Meta connection (older code; the brain's "fix first" list is still true)

| Brain decision | Status | Where / what's wrong |
|---|---|---|
| An agent with no ad account still gets their Page and Instagram saved | ❌ | `oauth.py` callback saves one row **per ad account**, so no ad account → nothing saved |
| Reconnecting updates the Page and Instagram | ❌ | `existing.page_id = existing.page_id or …` never overwrites |
| The Page is chosen ("Which Page is your business?"), not guessed | ❌ | `_pick_page()` guesses from the ad account's name |
| Posting works without an ad account | ❌ | `publisher.py` joins `AdAccount.is_active == True` |
| "Connected" means a Page, not an ad account | ❌ | `onboarding.meta_connected()` checks for an ad account |
| One Page → one Resmara account ("already connected" message) | ❌ | no uniqueness on `page_id` |
| The 19 situations, each with one message and one Fix it now | ❌ | four checks only |
| Re-check on log-in, nightly, before every post/ad, on Check again | 🟡 | token sweep exists; not before every post |
| Broken connection holds due posts; reconnect sends them | ❌ | `post_retry.py` retries; nothing holds |
| Emails when a connection breaks during a live campaign (then days 3, 7) | ❌ | |
| Alert Adam if >5% of live agents disconnect at once | ❌ | |

### Part C: the audit (older code)

| Brain decision | Status | Where / what's wrong |
|---|---|---|
| Four checks: Page, admin, Instagram, ad account | ✅ | `/api/onboarding/meta-audit` |
| Shows Page / Instagram **names and photos** | ❌ | shows ids |
| Real "is an admin" check | ❌ | copies the Page line |
| Setup to-do list on Accounts that ticks itself off (one box, Engine 3 §9a) | ❌ | |
| Live checklist during sign-up from Meta's real answers | 🟡 | animation plays preview data |

---

## Brand kit (Engine 2), mostly missing

| Brain decision | Status | Where / what's wrong |
|---|---|---|
| Investigation: Facebook Page, Instagram, website, Google, YouTube, Zillow, brokerage, state license lookup | 🟡 | Page read (`brand_engine.read_page`) and website brand (R2) only; no web investigation, no license lookup |
| Runs during sign-up, in the background, saved automatically | ❌ | the "Building your brand" step is an animation |
| Brand kit fields: name, title, phone, email, website, license, brokerage, broker license, areas, each with its source | 🟡 | some fields; no sources, no broker license |
| Logo and headshot, their own logo first | 🟡 | logo from the website only |
| Palette and real Google Fonts | 🟡 | palette suggested from the Page |
| **Voice of the client** paragraph on My Brand, read by every writer | ❌ | not in the brand profile; the post writer doesn't read it |
| Positive-only and persona-not-personal guardrails | ❌ | |
| Look defaults to Match my brand | 🟡 | picker exists (Engine 4 says the picker comes off My Brand) |
| Research again rebuilds; the agent's edits survive | ❌ | |
| Missing phone, license or brokerage asked for on + Campaign | ❌ | |

---

## The sign-up tour, not built

| Brain decision | Status |
|---|---|
| Finish pop-up: brand + Facebook status, one button "Show me around" | ❌ |
| Tour: anything that needs fixing first, then the look around, ending on "Let's start your first campaign" | ❌ (an older tour exists in `onboarding.js`) |
| One setup plan pop-up (Page, Instagram, ad account) with Check again | ❌ |
| See the tutorial (Setup page videos) | ✅ videos live (PRs #25, #30) |
| Do it with our team → the **Resmara setup session** | ❌ still the Real Estate Boost Calendly link; the event isn't made yet |
| Build first, then pay to unlock (blurred campaign, card form in the card) | ❌ today it asks for a card **before** building (`app.js` "Add a card to build your campaign") |
| One locked campaign at a time | ❌ |

---

## Listing link check (Engine 3), part built

| Brain decision | Status | Where / what's wrong |
|---|---|---|
| Any link works; it identifies the house | 🟡 | reads the pasted page (`listing_check.py`) |
| AI builds the home's file from every source (Zillow, Realtor.com, Redfin, brokerage, photographer page, public records) | ❌ | only the pasted link |
| Photos from whichever source has the best set | ❌ | |
| Form nudges toward the photographer's link | ❌ | |
| Needs 14 photos, asks for more | ❌ | `MIN_PHOTOS = 4` |
| Listing video always used | 🟡 | `listing_video.py` finds it |
| Button is **Build my campaign** with no price | ❌ | `app.js` shows "Build my campaign · $49" |
| No confirm step; facts fixed in review | ✅ | |
| Accounts: one setup box, one Walk me through it, one Do it with our team | ❌ | |

---

## Campaign build & pay to unlock (Engine 4), the core built, the brain's rules mostly missing

| Brain decision | Status | Where / what's wrong |
|---|---|---|
| 14-post plan, research, photo tagging and ranking | ✅ | `content_engine.py`, `photos.py` |
| Image model is the newest, as a setting, with a bake-off | 🟡 | setting exists; default `gpt-image-2.5-sunburst` (brain: newest, 2.6) |
| Post styles replace Modern / Classic / Rustic; Your look picker off My Brand | ❌ | |
| The trend brief from real engagement numbers | 🟡 | R3 style recipe uses web search; no engagement numbers |
| The 14-day story arc (section 6) | ❌ | |
| Art Director check that redoes a weak post; checker tuned to Adam's gold set | ❌ | spelling check + one retry only |
| 👍 / 👎 on every post; learns from ratings, edits and results | 🟡 | `round_learning.py` uses results; no thumbs |
| Name, license and phone on every post, shown in varied ways | 🟡 | fixed overlay lines |
| Post writer reads the Voice of the client | ❌ | |
| Hashtags: Instagram 3–5, Facebook 0–2, local + niche + post + agent tag, rotated | 🟡 | capped at 5 (fixed last night); the rest isn't |
| Posts go out when the audience is online, 6 AM–11 PM only | ❌ | |
| The ad: true-to-the-house hook, up to 3 hook versions, hook library, all placements | ❌ | one ad |
| Ad lifetime budget | ✅ | `ad_build.py` |
| Ads never run 11 PM–6 AM (Meta ad schedule) | ❌ | |
| Video ad and static ads run together | ❌ | |
| Platform rulebook + ad-policy check before launch; fix and resubmit a rejection once | ❌ | |
| No links in Instagram captions | ❌ (not checked) | |
| Photo swap picks from the home's photos and redesigns the post | 🟡 | swap exists; replaces the design with a plain photo |
| Failed post: retry, then the fallback design and "Needs a look", never a plain photo | ❌ | |
| Calendar Gallery view | ❌ | |
| Build first, then charge; pay to unlock | ❌ | charges before building (`/billing/charge`, paywall 402) |

---

## What this means

- **Built today from the brain:** Engine 1 Part A (the Facebook door) is solid and matches the brain.
- **Everything else in slice 1 is older code** with the brains' decisions mostly missing. The biggest
  gaps, in the order an agent hits them:
  1. Engine 1 Part B: the connection saves by ad account and guesses the Page, so many real agents
     (no ad account, several Pages) connect wrong or not at all.
  2. Engine 2: no brand investigation or Voice of the client; the kit is thin.
  3. The sign-up tour and build-first, pay-to-unlock: not built; today's flow asks for a card first.
  4. Engine 3: one source only, 4-photo minimum, the $49 still on the button.
  5. Engine 4: post styles, the story arc, the Art Director check, the ad hooks, ad hours and the
     rulebook.
- **Needs a person regardless of who builds:** the Facebook login return address in the Meta app;
  Meta App Review (so real agents can log in); the Resmara setup session in Calendly; Turnstile keys.
