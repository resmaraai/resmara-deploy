# Resmara engines: what is built, what is next, what is blocked

**Date:** 25 Nov 2026 · **Read from:** the code, the live bundle on www.resmara.com
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

### Part B - Meta connection

| Piece | Status | Notes |
|-------|--------|-------|
| Connect / reconnect Meta, token stored encrypted, health sweep | **Built** | `app/api/oauth.py`, `token_health.py` |
| Page, Instagram and ad account read from Meta | **Built** | `meta-audit` |
| "Connected" means Page, not ad account | **Not built** | today `connected` still requires an ad account row |
| The 19 situations with one message and one "Fix it now" | **Not built** | the audit has four lines, no situation list |
| One Page → one Resmara account | **Not built** | no uniqueness on `ad_accounts.page_id` |
| Posts held (not lost) while the connection is broken | **Partial** | `post_retry.py` retries; nothing holds a due post for a reconnect |
| Emails when a connection breaks while a campaign is live | **Not built** | |
| Weekly Meta review card + Monday email | **Not built** | |

### Part C - The audit

| Piece | Status | Notes |
|-------|--------|-------|
| Four checks (Page, admin, Instagram, ad account) | **Built** | `/api/onboarding/meta-audit` |
| Shows page/Instagram **names and photos**, not IDs | **Not built** | today it prints ids |
| Real "is an admin" check | **Not built** | copies the Page line |
| Setup to-do list on the account, ticking itself off | **Not built** | |
| Page facts (website, phone, address) handed to the Brand engine | **Built** | `brand_engine.read_page` / `/me/brand/from-meta` |
| Checklist ticking from Meta's live answers | **Partial** | plays from preview data on the live site |

---

## Engine 2 · Brand - **mostly not built**

| Piece | Status |
|-------|--------|
| "Build from my Facebook Page" (facts + proposed voice, colours, tagline) | **Built** (`brand_engine`, `design.brand_from_meta`) |
| Brand profile from the agent's website during a build (R2) | **Built** |
| Social audit of the last 30 Instagram posts (spec P2) | **Not built** |
| Full brand kit with web research: brokerage rules, licence, logo files (P3) | **Not built** |
| Onboarding step 2 "Building your brand" | **Not built** (animation only, calls nothing) |
| Refresh / merge / the agent's edits always winning | **Not built** |
| Font and theme pickers that feed the design step | **Not built** (mock only) |

---

## Engine 3 · Listing link - **part built**

| Piece | Status |
|-------|--------|
| Paste a link, open the listing, find photos and video | **Built** (`listing_check.py`, `listing_video.py`, `photos.py`) |
| AI builds the home's file from every source | **Partial** (photos, facts, research; no single "home file" object) |
| The link is a gate for the build | **Not built** |
| One-box Accounts setup | **Not built** |

---

## Engine 4 · Campaign build - **brain built, drawing generic**

| Piece | Status |
|-------|--------|
| 14-post plan, research, style research, photo tagging and ranking | **Built** |
| Design step (image edit + spelling check + one retry) | **Built** (`design.py`) |
| The R3 style recipe reaching the design step | **Not built** |
| Themes (Modern / Classic / Rustic) and a layout library | **Not built** |
| Art-director check that redoes a weak post | **Not built** |
| Quiet-zone tags | **Not built** |
| Learns from 👍 / 👎, edits and results | **Partial** (`round_learning.py`) |

---

## Engine 5 · Website - **blocked on measurement, page itself built**

| Piece | Status |
|-------|--------|
| A branded page for every home, with Preview / Copy link / Share | **Built** (`listing-site.js`, `listing-site` routes) |
| Visitor tracking on that page (GA4 + Meta pixel + Clarity) | **Partial - Blocked** → GA4 property id + service-account JSON, `META_AD_ACCOUNT_ID` + `META_SYSTEM_TOKEN`, Clarity project id. The page works; the numbers say "not connected yet" until those exist. |

---

## Engine 6 · Active campaign - **built**

Posting on time, retries, the ad, comment and website leads, the listing watcher, pause/resume,
insights, the agent report and the seller version: all real (`publisher.py`, `post_retry.py`,
`leads.py`, `listing_watch.py`, `insights.py`, `report_pdf.py`).

Open from the brain: the live ad audit inside the campaign (spend vs the plan, paused by Meta).

---

## Engine 8 · Run it until it sells - **part built**

`renewals.py` (14-day rounds, decline, stop when sold) is real. Still missing: the emails at every
turn (offer, reminder, start of a new round), and "Run it again" for any finished campaign.

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
| Money emails: acknowledgment when Run it until it sells is turned on, yearly reminder, 30-day price notice | **Built** — `app/services/consent.py`, the clock's daily reminder and `POST /api/admin/price-notice` |

---

## Engine 11 · Support - **built; the shared inbox is what is left**

| Piece | Status |
|-------|--------|
| Tickets from the client sidebar, replies, "not measured" honesty | **Built** |
| Ask Resmara answers from the account's real state | **Built** (`help.py`) |
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

Nothing else on the list is waiting on anyone. The terms and renewal-consent record is built
(accepted at sign-up, re-asked when the version changes, stored on the campaign with the time, IP
and browser, and the three money emails: acknowledgment, yearly reminder, 30-day price notice).
What remains is the brains' "not built" rows above (Engine 1 Part B/C connection + audit, Engine 2
full kit, Engine 3 gate, Engine 4 themes/layout library/art director, Engine 8's remaining emails).
