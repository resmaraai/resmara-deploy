# Resmara engines: what is built, what is next, what is blocked

**Date:** 25 Nov 2026 (corrected the same day after a line-by-line check of every brain against the code, PR "Fix: brain gaps") · **Read from:** the code, the live bundle on www.resmara.com
(`a26cc0fa0508`), and the eleven engine brains in `docs/engines/`.

**Shipped since the 23 Nov version of this file.** Slices 1–3 are merged and inside the live build:
PR #39 (`4158799`, sign-up to first campaign — Engines 1B/C, 2, tour, 3, 4), PR #40 (`1e6d60b`,
the live campaign — Engines 5, 6, 8) and PR #41 (`1ee7591`, the business side — Engines 10 and 11),
plus Engine 9 in PR #31 (`30496f9`). Each PR's commit was checked as an ancestor of the live build
with GitHub's compare API, not from the PR badge. So Engine 9 is live (not "undeployed"), the
sign-up tour is live, and Engines 10 and 11 are built except the three money emails the Build room
still carries as #66, #67 and #68.

The tracker's column "Sent to Dan" means *designed and delivered*. Every engine PR (#18, #22–#36)
touched only `docs/` - zero app files - so nothing in them reached a customer. This file is the
other column: what a customer can actually click. It is updated as each engine is built.

Legend: **Built** = code in the repo with a test · **Partial** = some of it real, some still a
mock · **Not built** = the screen exists only in a mockup · **Blocked** = cannot be finished from
this machine (a credential, an approval, or a purchase).

---

## Engine 1 · Login and Meta integration

### Part A - Account (built 23 Nov 2026, `app/api/facebook_login.py`)

| Piece | Status | Evidence |
|-------|--------|----------|
| "Log in with Facebook" as the door (new and returning, one pop-up) | **Built** | `POST /api/auth/facebook/start`, `GET /api/auth/facebook/callback`; 35 checks in `tests/test_facebook_login.py` |
| Terms box unticked → Facebook cannot start; consent stored with version, time, IP, browser | **Built** | the checkbox gates the button, the server refuses without it, the account is stamped |
| Same Facebook always lands on the same account | **Built** | `users.facebook_id` unique; test proves a second sign-in creates nothing |
| JWT never in a URL (one-time ticket instead) | **Built** | `facebook_login_codes`, single use proven |
| Facebook hides the email → ask once | **Built** | `needs_email` + `PATCH /api/auth/me/email` |
| Close my account (reversible) vs delete my data (permanent) | **Built** | `POST /api/auth/me/close`, `POST /api/auth/facebook/reactivate`; `DELETE /api/auth/me` unchanged |
| Welcome + day 3 / 7 / 14 emails, stopping at the first launched campaign | **Built** | `app/services/onboarding_emails.py`, run by the Render clock at 14:00 UTC |
| New-sign-up email to Adam | **Built** | `_notify_owner_new_account` |
| Unlimited-tries protection | **Built** | per-IP attempt counter (30/hour), 429 after that |
| Invisible bot check (Cloudflare Turnstile) | **Partial - Blocked** | code path exists (`RESMARA_TURNSTILE_SECRET`), no Turnstile keys, so it is skipped |
| Customers (not just test accounts) can use Facebook login | **Blocked** | Meta App Review must approve `email` (and later the Page/Instagram/ads permissions). Until then only app admins/testers can complete the dialog. This is a Meta dashboard fact, not something the API reports. |
| Email + password removed entirely | **Held deliberately** | kept as the fallback until the App Review above lands; the pop-up offers it under "Use email and password instead" |
| No teams / brokerage accounts | **Built by absence** | nothing in the schema or UI models a team; one agent per account |

### Part B - Meta connection (`app/services/meta_engine.py`, `tests/test_meta_engine.py`)

| Piece | Status | Evidence |
|-------|--------|----------|
| "Connected" means a Page, not an ad account | **Built** | `meta_connected()`; test "connected means a Page" |
| The situation list, one message and one "Fix it now" each | **Built** | `OUTCOMES` (16 situations + "ok" and "couldn't check right now"), one test per key |
| One Page → one Resmara account | **Built** | `page_taken` situation |
| Posts held (not lost) while the connection is broken; past posts never sent late | **Built** | `publisher.py` marks due posts `held`; Reconnect sends them |
| Emails when a connection breaks while a campaign is live (once, day 3, day 7) | **Built** | `breakage_emails_due` / `send_breakage_emails` |
| Adam told when more than 5% of live agents lose their connection | **Built** | the overnight sweep in `meta_engine` |
| Errors the list doesn't know: AI files them under the closest situation, otherwise "couldn't check right now" | **Built 25 Nov** | `file_unknown_error`; only errors the list doesn't recognise reach the AI |
| Weekly Meta review: Monday record, System check card, email to Adam, Approve puts a task on Dan's Build room list | **Built 25 Nov** | `weekly_review`, `decide_suggestion`, `/api/admin/meta/weekly-review*`, Render clock on Mondays |

### Part C - The audit

| Piece | Status | Evidence |
|-------|--------|----------|
| Page, Instagram and ad account shown by **name and photo** | **Built** | `status()` returns `page{name,picture}`, `instagram{username}`, `ad_account{name}` |
| Real "is an admin" check | **Built** | `page_no_control` situation |
| Setup to-do list on the account, ticking itself off | **Built** | `status()["todo"]` / `["done"]` |
| Day-3 email names the open setup item | **Built 25 Nov** | `onboarding_emails.situation()` → `meta_gap`, names the item and links to Accounts |
| Team room: how many agents are stuck on each setup item | **Built 25 Nov** | `GET /api/admin/connections/setup`, "Where agents are stuck on setup" card in Connections |
| Invite code honoured on the Facebook door, and the visit's tags kept through Facebook | **Built 25 Nov** | `/auth/facebook/start` saves source + invite; the callback reads them back (feeds Engine 9 attribution) |
| Page facts (website, phone, address) handed to the Brand engine | **Built** | `brand_engine.read_page` |

---

## Engine 2 · Brand - **built** (`brand_investigator.py`, `tests/test_brand_investigator.py`)

| Piece | Status |
|-------|--------|
| Investigate: Page, Instagram, website, web search for license, brokerage, logo | **Built** |
| Onboarding step "Building your brand" runs the real build | **Built** (`build_for_user` from sign-up) |
| The agent's edits always win over Research again | **Built** (`edited` fields are never overwritten) |
| Study of the last 30 Instagram posts and the Page's recent posts (posting habits, best posts, sign-off, look) | **Built 25 Nov** (`social_posts`, `social_audit`) |
| Each fact marked confirmed / found once / not found | **Built 25 Nov** (`fact_confidence`; shown next to each source) |
| Runs again automatically when a business Page or Instagram is connected after sign-up | **Built 25 Nov** |
| Look is always "Match my brand" (no Modern / Classic / Rustic pickers) | **Built** - the brain dropped the pickers |

---

## Engine 3 · Listing link - **built** (`tests/test_engine3_listing_link.py`)

| Piece | Status |
|-------|--------|
| Paste a link, open the listing, find photos and video | **Built** (`listing_check.py`, `listing_video.py`, `photos.py`) |
| The link is the gate for the build | **Built** |
| One box on Accounts | **Built** (`static/signup.js`) |
| The home's file: every fact with its source; facts only found online are "please check" (decided in code) and never stated as fact in posts | **Built 25 Nov** (`content_engine.home_file`, `please_check_note`) |
| The checking screen names each stage ("Searching Zillow, Realtor.com, Redfin…", "Building the home's file") | **Built 25 Nov** (`static/review.js`) |

---

## Engine 4 · Campaign build - **built** (`tests/test_content_engine.py`, `tests/test_engine4_rules.py`)

| Piece | Status |
|-------|--------|
| 14-post plan, research, post styles, photo tagging and ranking | **Built** |
| Design step (image edit + spelling check + one retry) | **Built** (`design.py`) |
| Post styles reach the design step (replaces Modern / Classic / Rustic) | **Built** (`post_rules.style_words`) |
| Art Director check that redoes a weak post | **Built** (`ART_DIRECTOR_MIN` in `design.py`) |
| Learns from 👍 / 👎, edits and results | **Built** (`round_learning.py`) |
| Hook library across agents (which hooks win, by feature and market) feeds new hooks | **Built 25 Nov** (`learning_library.hook_library`) |
| Meta's past rejections read back into new hooks | **Built 25 Nov** (`learning_library.lessons_note`) |
| Monthly platform-rules refresh and banned hashtags | **Built 25 Nov** (`refresh_platform_rules`, `post_rules.allowed`; Render clock on the 1st) |
| Weekly market trend brief, shared per market | **Built 25 Nov** from web research; **the local top-agent numbers are Blocked** on Meta App Review (Instagram Business Discovery) |

---

## Engine 5 · Website - **built**

| Piece | Status |
|-------|--------|
| A branded page for every home, with Preview / Copy link / Share | **Built** (`listing-site.js`, `listing-site` routes) |
| Visitor tracking on that page (GA4 + Meta pixel + Clarity) | **Built** - the keys were set on Render on 24 Nov |

---

## Engine 6 · Active campaign - **built**

Posting on time, retries, the ad and its live audit (`ad_audit.py`), comment and website leads, the
listing watcher, pause/resume, insights, the agent report and the seller version: all real
(`publisher.py`, `post_retry.py`, `leads.py`, `listing_watch.py`, `insights.py`, `report_pdf.py`).

Built 25 Nov: the on-screen agent report now shows the ad (spend, cost per click, click rate,
frequency), leads by source, website visits, each hook side by side with the winner, every post's
numbers, and the audit log; and live reports get Resmara's summary and recommendations
(`content.report_reading`, `report_hooks`, `_fill_post_numbers`).

---

## Engine 8 · Run it until it sells - **built** (`tests/test_until_sold*.py`)

`renewals.py` (14-day rounds, decline, stop when sold), Run it again · $39, and the emails at each
turn (`campaign_emails.py`). Built 25 Nov: a price change confirmed by the listing and a second
source leads the next round as "Improved price", never with a number.

---

## Engine 9 · Marketing (Website, Email campaigns, Digital ads) - **built and live**

`app/api/marketing.py`, `marketing_ads.py`, `mailchimp.py`, `attribution.py`, the Marketing /
Website / Digital ads tabs in `static/admin.html`, and `tests/test_engine9_marketing.py` shipped in
PR #31 (`30496f9`), inside the live build.

| Channel | Status |
|---------|--------|
| Marketing parent page + per-channel rows | **Built, live** |
| Attribution: where each sign-up came from | **Built, live** |
| Digital ads read-out | **Built, live** → reads Resmara's own Meta ad account id + system token (set on Render) |
| Website channel | **Built, live** → GA4 property + service account, Clarity and PageSpeed keys are set |
| Email campaigns (Mailchimp) | **Built - Blocked** → needs a Mailchimp API key and audience id |

---

## Engine 10 · Billing - **built; the money emails and Stripe Tax are what is left**

| Piece | Status |
|-------|--------|
| $49 campaign, packs, webhook, refunds, saved cards | **Built**, live (Stripe live account, `enabled: true`) |
| Card form inside our own pop-up (Stripe Elements), Change/Remove card, Coming up, receipts | **Built** (PR #41) |
| Stripe Tax | **Built behind `RESMARA_STRIPE_TAX=1`** → blocked on switching Stripe Tax on in the Stripe dashboard (Dan/Adam) and registering in the states that require it |
| Receipts, refunds, chargebacks, closing an account stops billing | **Built** (PR #41) |
| Money emails: acknowledgment when Run it until it sells is turned on, yearly reminder, 30-day price notice | **Not built** — Build room #66, #67, #68 |

---

## Engine 11 · Support - **built; the shared inbox is what is left**

| Piece | Status |
|-------|--------|
| Tickets from the client sidebar, replies, "not measured" honesty | **Built** |
| Ask Resmara answers from the guide and the account's real state; signed-out visitors get product answers; 20 questions an hour and a daily cost cap | **Built 25 Nov** (`help.py`; before this it only matched approved answers) |
| One shared `support@resmara.com` inbox | **Blocked** → the mailbox has to exist (domain is on GoDaddy; Resend can send from it, nothing receives yet) |
| Which listing? + 1 business-day promise + reply-by times | **Built** (PR #41) |

---

## Sign-up tour (PR #23) - **built and live**

Finish pop-up (brand + Facebook status, "Show me around"), fixes-first order, one setup plan, the
tour itself, then "Let's start your first campaign" — shipped in PR #39 behind the Facebook door.

---

# Everything blocked, in one list

| # | Blocked item | Engines | What unblocks it | Who |
|---|--------------|---------|------------------|-----|
| 1 | Real customers cannot finish "Log in with Facebook" | 1 | Meta App Review: `email` (advanced), then `pages_show_list`, `pages_read_engagement`, `pages_manage_posts`, `instagram_basic`, `instagram_content_publish`, `ads_read`, `ads_management`, `pages_manage_ads`, `read_insights`, `instagram_manage_insights` | Meta dashboard (Dan's Facebook login) |
| 2 | No invisible bot check | 1 | Cloudflare Turnstile site + secret key (free) → `RESMARA_TURNSTILE_SECRET` | Dan (Cloudflare) |
| 3 | Facebook login callback must be allow-listed | 1 | Facebook Login → Valid OAuth Redirect URIs += `https://www.resmara.com/api/auth/facebook/callback` | Meta dashboard |
| 4 | ~~Website numbers ("not connected yet")~~ **resolved 24 Nov** | 5, 9 | `GA4_PROPERTY_ID` + `GA4_SA_JSON`, `META_AD_ACCOUNT_ID` + `META_SYSTEM_TOKEN`, `CLARITY_PROJECT_ID`/`CLARITY_TOKEN` are all set on Render; Website and Digital ads read real data | done |
| 5 | ~~Digital ads channel~~ **resolved 24 Nov** | 9 | same keys as #4 — Resmara's own ad account 1151413287580354 is wired | done |
| 6 | Email campaigns (Mailchimp) | 9 | Mailchimp API key + audience id | Adam/Dan |
| 7 | Stripe Tax | 10 | the code is behind `RESMARA_STRIPE_TAX=1`; switch Stripe Tax on in the Stripe dashboard and register where required | Dan/Adam |
| 8 | Receiving mail at support@resmara.com | 11 | an actual mailbox (MX) for the domain, or a forwarding rule to an inbox we read | Dan/Adam |
| 9 | Facebook Page/Instagram/ad permissions in the same login window | 1 | same App Review as #1 (the code already reads `META_SCOPES`; no build needed) | Meta |
| 10 | Preview environments per PR | - | Render workspace upgrade ($25/mo) - not needed for launch | Dan (spend) |

| 11 | Local top-agent numbers in the weekly trend brief | 4 | Instagram Business Discovery permission in the same App Review as #1 | Meta |
| 12 | Any new build (posts, brand, Ask Resmara) | 2, 3, 4, 11 | Credits on the OpenAI account whose key is in `OPENAI_API_KEY` on Render; builds have failed since 19 Nov | Adam |
| 13 | Pay to unlock and Add card can't open the card form | 10 | `STRIPE_PUBLISHABLE_KEY` is empty on Render | Dan |

Nothing else on the list is waiting on anyone: the remaining engine work is the three money emails
(Build room #66, #67, #68) and the terms/renewal-consent records (#61, #62, #64, #65). Every other
row in every brain is built.
