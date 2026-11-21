# Resmara · Meta Integration Engine — Build Spec v1.0

**Date:** 20 Nov 2026 · **For:** Dan (backend) and Adam (front end)
**Companion docs:**
- `docs/flows/new-user-experience.md` (what the agent sees);
- *Resmara engine status* (what's built today).

**Scope:** everything between "Connect your Meta account" and a campaign that can post. It
covers:

- how Resmara connects to Facebook, Instagram and the ad account;
- how it checks each one and decides what the agent can do;
- how it keeps watching, how the agent fixes things, and how they reconnect;
- where AI helps.

---

## 1. What this engine must do

1. **Get the agent posting as fast as possible**, with whatever they have. Only a Facebook login
   is required. Everything else limits the campaign; it never locks the agent out.
2. **Know the truth about every connection, all the time**, using Meta's own answers. Never
   guess, and never show a fact Meta didn't give us.
3. **Tell the agent in plain words** what works, what doesn't, and the one thing to do next.
4. **Keep watching** after sign-up, because connections break: passwords change, logins expire,
   ad accounts get disabled. Catch it before a post fails.
5. **Make fixing it one click**, and make sure nothing is lost while it's broken.

---

## 2. The engine at a glance

```
CONNECT ─► SAVE ─► CHECK ─► DECIDE ─► TELL
                     ▲                  │
                     │                  ▼
                  RE-CHECK ◄──── FIX (Fix it now · Setup guide · setup call · Reconnect)
                     ▲
                   WATCH  (every sign-in · every 15 min token sweep · daily full check ·
                           before every publish and every ad launch)
```

- **CONNECT:** the Facebook login dialog.
- **SAVE:** one Meta connection per agent (section 4).
- **CHECK:** asks Meta about the login, the Page, Instagram and the ad account (section 5).
- **DECIDE:** turns the answers into one outcome and a set of capabilities (section 6).
- **TELL:** the screens, the Meta notice and the emails (section 9).
- **WATCH, FIX and RE-CHECK:** sections 7 and 8.

---

## 3. What's wrong with how it works today (fix first)

Found in `app/api/oauth.py`, `meta_callback()`:

1. **The connection is only saved per ad account.** The callback loops over the agent's ad
   accounts and saves one row for each. An agent with **no ad account** gets nothing saved: no
   login, no Page, no Instagram. Every "no ad account" scenario in the flow doc depends on this
   being fixed.
2. **Reconnecting never updates the Page or Instagram.** It uses
   `existing.page_id = existing.page_id or page_id_val`, and the same for `ig_user_id`. Once a
   value is stored it can't change. An agent who picked the wrong Page, or who later switched
   Instagram to business, stays stuck.
3. **The Page is guessed, not chosen.** `_pick_page()` matches the ad account's name. An agent
   with several Pages (a personal brand plus a team Page) can end up on the wrong one with no way
   to see or change it.
4. **The publisher refuses to post unless the ad account is active.** That breaks posting for
   agents without an ad account (`publisher.py`).
5. **"Connected" means "has an active ad account"** (`meta_connected()`), not "has a Page".

The data model in section 4 and the rules in section 6 fix all five.

---

## 4. What's saved: one Meta connection per agent

A new table, separate from ad accounts:

```
meta_connections(
  id, user_id UNIQUE,
  fb_user_id, fb_user_name,
  token_enc,                       -- long-lived user token, encrypted (as today)
  token_expires_at, token_status,  -- healthy | expiring | needs_reconnect | unknown
  scopes_granted JSON, scopes_declined JSON,
  page_id, page_name, page_tasks JSON, page_published BOOL,
  pages_available JSON,            -- [{id, name, tasks, ig_id}] so the agent can switch
  ig_user_id, ig_username,
  ad_account_id NULL,              -- FK to ad_accounts when there is one
  issues JSON,                     -- the current outcome keys, section 6
  capabilities JSON,               -- {fb_post, ig_post, ad, download_mode}
  last_checked_at, last_check_source,  -- connect | sign_in | check_again | sweep | daily | pre_publish
  first_connected_at, updated_at
)
```

Rules:

- **Created on every successful Facebook login, even with no Page and no ad account.** That's
  how "the Facebook login happened" is known (flow doc section 2).
- **Every reconnect and every Check again overwrites** `page_*`, `ig_*` and `ad_account_id` with
  what Meta says now. Never `or` an old value.
- **Ad accounts stay in `ad_accounts`** for the ad engine and billing. The connection points at
  the one in use.
- **`meta_connected()` means:** the connection exists, the token is healthy, and there's a Page
  the agent can post to.

---

## 5. The checks (what we ask Meta)

Every check is a direct Meta call. No AI is involved in deciding a fact.

| # | Check | Meta call | Pass when |
|---|-------|-----------|-----------|
| C1 | Login is valid | `GET /debug_token` | `is_valid` true. Store `expires_at` and the scopes. |
| C2 | Permissions granted | `GET /me/permissions` | The posting scopes are `granted`. Each `declined` scope maps to an issue (an Instagram scope declined → the Instagram issue). |
| C3 | Pages | `GET /me/accounts?fields=id,name,tasks,is_published,instagram_business_account{id,username}` | At least one Page. Save the full list to `pages_available`. |
| C4 | Can post to the Page | the chosen Page's `tasks` | Includes `CREATE_CONTENT` (posting). `MANAGE` is full control. |
| C5 | Page is published | `is_published` | true. An unpublished Page can't be seen, so posts would reach no one. |
| C6 | Instagram is a linked business account | `GET /{page-id}?fields=instagram_business_account{id,username}` | Present. **Always re-queried, never read from storage.** |
| C7 | Ad account can spend | `GET /me/adaccounts?fields=id,name,account_status,funding_source_details` and the existing `spend_readiness()` | `account_status` = 1 (active) and a funding source is present. |

What Meta *can't* tell us, so we never claim it: whether an Instagram that isn't linked is
personal or simply linked to another Page. The wording covers both: "Your Instagram isn't
connected as a business account."

`account_status` values and how to treat them:

- **1 active:** OK.
- **2 disabled, 101 closed:** the ad is off, with an issue.
- **3 unsettled, 8 pending settlement:** an unpaid balance. The ad is off.
- **7 pending review, 9 grace period:** the ad is held. The notice says Meta is reviewing it.
- **Anything else:** `unknown`. Never alarm; re-check later.

---

## 6. Decide: every outcome, and what happens

Each check result becomes an **outcome key**. The keys decide three things:

- the **capabilities** (what the campaign can do);
- the **message** (one line, from a fixed table);
- the **fix** (what **Fix it now** opens).

### 6.1 Capabilities

| Capability | True when |
|------------|-----------|
| `fb_post` | C1, C3, C4 and C5 pass |
| `ig_post` | `fb_post` and C6 pass |
| `ad` | `fb_post` and C7 pass |
| `download_mode` | the Facebook login happened but `fb_post` is false |
| `campaigns_allowed` | the Facebook login happened (a connection row exists) |

### 6.2 Outcome table

| Key | Situation | Capabilities | Agent sees (Meta notice line) | Fix it now opens |
|-----|-----------|--------------|-------------------------------|------------------|
| `ok` | Everything passes | all | No notice | — |
| `no_facebook` | Agent says they have no Facebook (or never completes a login) | none; `campaigns_allowed` false | "You'll need a Facebook account first" screen | Setup: Facebook account |
| `login_cancelled` | Closed or cancelled the Facebook dialog | none | Step 1 again; Accounts prompt | the Facebook dialog |
| `scope_declined_page` | Unticked the Page permissions | download mode | "Resmara can't post to your Page because a permission was turned off." | the Facebook dialog with `auth_type=rerequest` |
| `scope_declined_ig` | Unticked the Instagram permissions | `fb_post`, `ad` | "Instagram posting was turned off when you connected." | the Facebook dialog with `auth_type=rerequest` |
| `scope_declined_ads` | Unticked the ad permissions | `fb_post`, `ig_post` | "Ads were turned off when you connected." | the Facebook dialog with `auth_type=rerequest` |
| `no_page` | No Facebook Page | download mode | "No Facebook business Page is connected." | Setup: business Page |
| `page_no_control` | Page exists, but no posting rights | download mode | "You don't have full control of your Facebook Page." | Setup: full control |
| `page_unpublished` | Page is unpublished | download mode | "Your Facebook Page is unpublished, so no one can see it." | Setup: business Page (publish step) |
| `several_pages` | More than one Page could be the business | as chosen | Picker: "Which Page is your business?" (section 8.3) | the Page picker |
| `ig_not_linked` | No business Instagram linked to the Page | `fb_post`, `ad` | "Your Instagram isn't connected as a business account." | Instagram switch pop-up |
| `no_ad_account` | No ad account | `fb_post`, `ig_post` | "You don't have a Meta ad account yet, so your listing ad is off." | Setup: ad account |
| `ad_no_payment` | Ad account with no funding source | `fb_post`, `ig_post` | "Your ad account can't run ads yet. It needs a payment method." | Setup: ad account (payment step) |
| `ad_disabled` | Status 2 or 101 | `fb_post`, `ig_post` | "Meta has disabled your ad account." | Book a call (Meta appeals need a person) |
| `ad_unpaid` | Status 3 or 8 | `fb_post`, `ig_post` | "Your ad account has an unpaid balance with Meta." | Meta Billing & payments (new tab) |
| `ad_in_review` | Status 7 or 9 | `fb_post`, `ig_post` | "Meta is reviewing your ad account. Your ad will start when it's cleared." | none (Check again later) |
| `token_expiring` | Expires within 7 days and the silent refresh failed | all, until expiry | "Your Meta connection needs a quick refresh." | Reconnect |
| `token_dead` | Expired, password changed, access removed, or the app removed | none; posts **held** | "Your Meta connection needs refreshing. Your posts are on hold until you reconnect." | Reconnect |
| `meta_unreachable` | Meta down, a timeout or a rate limit | unchanged from the last good check | **No notice.** Retry with backoff. After 6 hours of failures, an operator alert, never an agent alert | — |

Several issues at once:

- Show at most **three lines**, most important first: `token_dead`, then Page issues, then
  Instagram, then the ad.
- **Fix it now** opens the fix for the first one.
- `page_no_control` is hidden when `no_page` is present (it would only repeat it).

### 6.3 What the other engines do with the capabilities

- **Publisher:** posts to Facebook only when `fb_post`, and to Instagram only when `ig_post`. It
  **never** requires the ad account (fixes section 3, item 4). With `download_mode`, nothing is
  sent and the posts stay downloadable. With `token_dead`, due posts are marked **held** (not
  failed); reconnecting releases them (`post_retry.requeue_connection_failures`, which exists).
- **Ad engine:** builds and launches only when `ad`. Without it, the ad step is skipped and
  logged, not errored.
- **Mid-campaign upgrades:** when a capability turns on (say the Page connects on day 5), only
  posts still in the future go out. Past ones aren't sent late.
- **Price:** $49 whatever the capabilities. Nothing in this engine touches billing.

---

## 7. Watch: when the checks run

| When | What runs | Notes |
|------|-----------|-------|
| Connect (the callback) | C1–C7 | Then the Page picker if `several_pages` |
| Every sign-in | C1–C7, unless checked in the last 10 minutes | Keeps the Meta notice true |
| **Check again** (any screen) | C1–C7, forced, ignores the cache | Re-queries Instagram; this is the fix for a stale `ig_user_id` |
| Every 15 minutes | C1 only (token health; exists in `token_health`) | Silent refresh when within 7 days of expiry |
| Daily, overnight | C1–C7 for every agent with an active campaign | Catches a disabled ad account or a removed Page before the next post |
| Before each publish batch | C1, plus C4 and C6 for the posts' targets | A failure marks posts held, then a full check |
| Before an ad launch | C7, plus the existing `spend_readiness` | Refuses to launch on an account that can't spend (exists) |

Every check writes `issues`, `capabilities`, `last_checked_at` and `last_check_source`, and logs an
Event when the outcome **changes**, so the Team room can show when and why.

---

## 8. Fix: the agent's paths, simplest first

### 8.1 Fix it now
One orange button on the Meta notice and on the Step 1 result. It opens the single most useful
fix for the top issue (the "Fix it now opens" column in 6.2):

- the Instagram switch pop-up;
- a Setup step;
- the Facebook dialog with `rerequest`;
- the Page picker;
- a Reconnect.

### 8.2 Reconnect
- Lives in the **Accounts** page and on the notice when the token is the issue.
- It's the same Facebook dialog. Facebook remembers the earlier choices, so it's two clicks.
- After it: overwrite the connection (section 4), run C1–C7, release held posts, and show the
  result. Campaigns, brand and leads are untouched.

### 8.3 The Page picker
- Shown when the login grants more than one Page and no single obvious business Page exists,
  and from Accounts anytime ("Change Page").
- One question: "Which Page is your business?" Each Page shows its name and photo, plus a
  "has Instagram" tag.
- The pick is saved to `page_id`, then C4–C7 re-run for that Page.
- With one Page, there's no picker.

### 8.4 Setup guides and the setup call
- Every issue links to its Setup step (the website's Setup page, flow doc section 8).
- **Book a call to fix it** is always there. Booking stops the reminder emails for 7 days, but
  doesn't hide the notice.

---

## 9. Tell: what the agent sees and hears

| Where | What |
|-------|------|
| Step 1 result | The outcome screen per the flow doc (connected, limited, one thing to fix, no Facebook) |
| Meta notice | Every dashboard and campaign page while any issue is present (pink, calm, three buttons) |
| Accounts page | Each check as a row with a tick or a note, last checked time, **Check again**, **Reconnect**, **Change Page** |
| Email (only for things that change *after* onboarding) | `token_dead`, `ad_disabled`, `ad_unpaid` and `page_no_control` when the agent has a live campaign. Sent once when it happens, then on days 3 and 7 if still open. Never for issues the agent already saw at sign-up. |
| Help chat | Answers about Meta read the agent's **current** outcome (section 10) |
| Team room | Count of agents per outcome key; a list of agents with live campaigns and `token_dead` or `ad_*` issues; unknown Meta errors |

All wording comes from the outcome table. The front end's `META_ISSUE_SHORT`, `metaLimitLine()`
and `metaFixAction()` already implement the first four outcomes. They move to reading the
server's `issues` keys directly.

---

## 10. Where AI helps (and where it must not)

**Not for the checks.** Every fact above comes straight from Meta. A model never decides whether
a Page or token is OK. That keeps it exact, instant and free.

AI earns its place in three spots:

1. **Explaining unexpected Meta errors.** Most errors map to the table (Meta error codes 190, 200,
   10, 100 and the ad statuses). When Meta returns something new:
   - a small model reads the error and the agent's current checks;
   - it picks the closest outcome key and writes a one-line plain-English explanation;
   - the key must be from the table (anything else becomes `meta_unreachable`, so the engine
     can't invent a state);
   - the raw error is logged for the weekly review.
2. **The help chat (Ask Resmara).** It gets the agent's outcome, capabilities and last check
   time, so it can answer "why isn't my post on Instagram?" with *their* answer and the right
   button, not a generic article.
3. **Weekly review (operator, not live).** It groups the week's unknown errors and setup-call
   notes, and suggests new outcome rows or better wording for Dan and Adam to approve. That's how
   the table keeps improving.

Cost guard: AI is called only on an error that isn't in the table, or a help question. That's
expected to be well under a cent per agent per month.

---

## 11. Tests

1. **Unit tests, one per outcome key.** Fake Meta responses for C1–C7 go in, and the test checks
   the outcome key, capabilities, message and fix action. All 19 keys are covered, plus mixes (no
   Page and no ad; token dead plus Instagram).
2. **Reconnect tests:**
   - the Page changes;
   - Instagram becomes linked (proves the `or` bug is gone);
   - held posts are released;
   - campaigns are untouched.
3. **Publisher tests** per capability set: Facebook only, Facebook plus Instagram, download
   mode, held.
4. **Meta test users** (Meta's app dashboard can create them). One per main scenario: everything,
   no ad account, no Page, personal Instagram, an ad account with no card. Run before every
   release that touches this engine.
5. **The preview** keeps a scenario picker (`#new`) and `#instagram` for front-end review.
6. **Monitoring:** the Team room alerts when more than 5% of agents with live campaigns are
   `token_dead`. That usually means a Meta app problem, not the agents.

---

## 12. Build split and order

**Dan, backend (in this order)**

1. The `meta_connections` table, plus saving on every login (with or without an ad account), and
   overwrite on reconnect. Fixes section 3, items 1 and 2.
2. Checks C1–C7 in one service (`meta_engine.check(user, source)`), plus the outcome table and
   capabilities. Fold in the existing `meta-audit`, `token_health` and `spend_readiness`.
3. `meta_connected()` means a Page connection. The publisher reads capabilities, with no
   ad-account gate.
4. When the checks run (section 7): sign-in with a 10-minute cache, forced Check again, the daily
   sweep, and before publish and launch.
5. The Page picker endpoints: list `pages_available`, and set the Page.
6. Emails for post-onboarding breakages; Team room counts.
7. The AI error explainer and the help-chat context.

**Adam, front end**

1. **Done in PR #17:** Step 1 outcomes, the Meta notice, Fix it now, the Instagram pop-up, the
   Setup page and download mode.
2. Next:
   - read the server's `issues` keys instead of the four indexes;
   - the Accounts page check list;
   - the Page picker;
   - Reconnect and Change Page buttons.

**First milestone:** items 1–3. That alone makes every flow-doc scenario true on the live site.

---

## 13. Open questions

1. Should a 60-day token be refreshed automatically when the agent signs in (the silent refresh),
   or only by the sweep? Suggested: both.
2. Should agents on Business Manager-owned ad accounts be supported in v1 (`/me/adaccounts` only
   lists accounts the person has access to)? Suggested: yes, if listed. Otherwise the ad
   account issue plus a setup call.
3. Email sender for the breakage emails: `support@resmara.com` once Workspace is set up.
