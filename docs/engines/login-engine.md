# Login engine

**Part of:** the Resmara engine library (`docs/engines/README.md`) · **Last updated:** 21 Nov 2026
**Detailed specs:** *Meta Integration Engine* (`docs/engines/meta-integration-engine.md`)
**What the agent sees:** `docs/flows/new-user-experience.md`

---

## 1. What it does

It takes a visitor from **Client Login** to a signed-in agent whose Meta connection is checked
and understood, ready for the Brand engine. Along the way it handles:

- creating the account;
- the confirmation email;
- signing in and staying signed in;
- password resets;
- connecting Facebook, Instagram and the ad account through one Facebook login;
- checking what works and what doesn't, and telling the agent;
- keeping an eye on the connection afterwards;
- the onboarding steps (Connect Meta, Your brand, Quick tour).

It ends when the agent lands on **My campaigns** with the tour done (or skipped).

---

## 2. Status

| Piece | Status |
|-------|--------|
| Sign up (name, email, password) | Built |
| Confirmation email before first sign-in | Built |
| Sign in, stay signed in (7 days) | Built |
| Password reset by email | Built |
| Facebook login (Meta's dialog) | Built |
| Saving the Meta connection | **Partly.** Saved only per ad account, so no ad account means nothing is saved. Reconnecting never updates the Page or Instagram (Meta Integration spec §3) |
| The four checks (Page, admin, Instagram, ad account) | Built |
| Partial setup allowed (only a Facebook login required) | Front end built (PR #17); server rules **not yet** |
| Meta notice, Fix it now, Instagram switch, Setup page | Built (PR #17) |
| Connection sweep (refresh before expiry, flag dead logins) | Built, every 6 hours |
| Dashboard warning when the sweep finds a dead login | **Not built** |
| Page picker for agents with several Pages | **Not built** |
| Onboarding steps and first-login tour | Built; the tour is remembered on the account |
| Step 2 "Your brand" | **Animation only.** Hands off to the Brand engine, which isn't wired in yet |

---

## 3. When it runs

- **Client Login → Create an account:** sign-up.
- **The link in the confirmation email:** confirm.
- **Client Login → Sign in:** sign-in, then the Meta re-check.
- **Forgot password:** reset request, then the link, then a new password.
- **Step 1 Connect your Meta account, Reconnect, or Fix it now:** the Facebook login and the
  checks.
- **Check again** (Meta notice, Step 1, Instagram pop-up): the checks, forced.
- **Every 6 hours** (scheduler): the connection sweep for every account.

---

## 4. Steps

```
SIGN UP ─► confirmation email ─► CONFIRM ─► SIGN IN ─► META GATE
                                                         │
               ┌─────────────────────────────────────────┤
               ▼                                         ▼
     never connected: lands on Accounts,       connected: re-check (applyMetaChecks)
     Step 1 Connect Meta                       ─► Meta notice if anything's missing
               │                                         │
               ▼                                         ▼
     Facebook login dialog ─► CALLBACK saves the connection ─► CHECKS (4) ─► RESULT SCREEN
               │                                                              │
     "Don't have Facebook?" ─► no-Facebook screen (the one stop)              ▼
                                                          Step 2 Your brand ─► Step 3 Tour ─► My campaigns
```

---

## 5. AI it uses

**None today, on purpose.** Every fact in this engine (who you are, what Meta granted, whether
there's a Page) comes from a password check, a signed token, or Meta's own API.

Planned, from the Meta Integration spec §10:

| Call | What it does | Guardrail |
|------|--------------|-----------|
| Unknown Meta error explainer | When Meta returns an error that isn't in the outcome table, a small model picks the closest outcome and writes one plain line | Must return a known outcome key, or it becomes "Meta unreachable" with no agent alert |
| Help-chat context | Ask Resmara gets the agent's current Meta outcome, so it can answer "why isn't my post on Instagram?" with their answer | Reads the stored outcome only; never re-decides it |

---

## 6. Code map

**Backend**

| What | Where |
|------|-------|
| Sign up, sign in, confirm, resend, me, password change, delete account | `app/api/auth.py`: `register`, `login`, `confirm_email`, `resend_confirmation`, `me`, `/me/password`, `/me` DELETE |
| Password reset | `app/api/auth.py`: `request_reset`, `confirm_reset` |
| Passwords and sign-in tokens | `app/core/security.py`: `get_password_hash`, `verify_password`, `create_access_token` (JWT), `get_current_user` |
| Emails | `app/services/mail.py`: `send_email` tries Resend first, then SMTP, and never pretends it sent |
| Facebook login | `app/api/oauth.py`: `meta_connect` builds the dialog link with a signed `state`; `meta_callback` exchanges the code for a long-lived token and saves the connection |
| Permissions asked for | `app/api/oauth.py`: `META_SCOPES` (env `META_SCOPES`) |
| The four checks | `app/api/onboarding.py`: `meta_audit` (`GET /api/onboarding/meta-audit`) |
| Onboarding facts | `app/api/onboarding.py`: `onboarding_state`, `/setup-session`, `/tour-seen` |
| Connection sweep | `app/api/oauth.py`: `meta_check_all` (`POST /api/oauth/meta/check-all`, system token) and `app/services/token_health.py` |
| Can the ad account spend | `spend_readiness()` (used by the audit and the ad engine) |

**Endpoints:**

- `/api/auth/register`, `/login`, `/confirm`, `/confirm/resend`, `/me`,
  `/password-reset/request`, `/password-reset/confirm`;
- `/api/oauth/meta/connect`, `/meta/callback`, `/meta/check-all`, `/meta/demo-connect`;
- `/api/onboarding/state`, `/setup-session`, `/tour-seen`, `/meta-audit`.

**Front end**

| What | Where |
|------|-------|
| Client Login, sign-up form, sign-in | `static/homepage.js`: `clientAccess`, `submitTestClient` |
| Confirm-email screen | `static/homepage.js`: `confirmEmailPage` |
| After sign-in: Meta gate and re-check | `static/onboarding.js`: `metaGateOnLogin`, `hydrateOnboarding`, `applyMetaChecks` |
| Step 1 Connect Meta and result screens | `static/onboarding.js`: `onboard`, `obCheck`, `obNeedsSetup`, `obNoFacebook` |
| Meta notice, Fix it now, Instagram pop-up | `static/onboarding.js`: `metaIssueBanner`, `metaFixAction`, `obIgSwitch` |
| Accounts page and Connect | `static/app.js`: `accounts`, `connectMeta` |
| Steps 2 and 3 | `static/onboarding.js`: `obBrand` (animation), the tour |
| Setup page | `static/homepage.js`: `setupGuides`, `SETUP_GUIDES` |
| API calls | `static/api.js`: `RM.*` |

---

## 7. Data

| Table and columns | Written by | Read by |
|-------------------|------------|---------|
| `users`: `email`, `hashed_password`, `name`, `is_active`, `last_login` | sign-up, sign-in | everything |
| `users`: `email_confirmed_at`, `confirm_token_hash` (hashed), `confirm_sent_at` | sign-up, confirm | sign-in (blocks until confirmed) |
| `users`: `meta_connected_at`, `setup_booked_at`, `tour_seen_at` | callback, booking, tour | the Meta gate, the tour |
| `password_resets`: `user_id`, token (hashed), `expires_at` | reset request | reset confirm |
| `ad_accounts`: token (encrypted), `page_id`, `ig_user_id`, `token_status`, `expires_at` | callback, sweep | checks, publisher, ad engine |
| `events`: `email_confirmed`, `user_registered`, connection changes | throughout | Team room |
| Browser: `state.metaIssues`, `state.connected`, `state.metaChecked`, `state.tourDone` | front end | the Meta notice, the + Campaign gate |

**Planned** (Meta Integration spec §4): a `meta_connections` table, one per agent, saved on every
login and overwritten on every reconnect.

---

## 8. Outcomes

**Account**

| Outcome | Message |
|---------|---------|
| Password under 8 characters | "Use at least 8 characters for the password" |
| Email already used | "Email already registered" |
| Wrong email or password | "Incorrect email or password" |
| Not confirmed yet | Sign-in is blocked, with "Send it again" |
| Confirm link expired (48 hours) | "That link has expired - sign in and ask for a new one." |
| Reset link expired (60 minutes) | "This reset link is invalid or has expired" |
| Email couldn't be sent | "We could not email a link. Contact support and we will send you one." |

**Meta:** all 19 outcomes, their messages and the fix each one opens are in the Meta Integration
spec §6.2. The four the front end shows today are:

- Page missing;
- not an admin;
- Instagram not connected as a business account;
- no ad account that can spend.

Plus the no-Facebook stop.

---

## 9. Settings you can adjust

| Setting | Where | Now |
|---------|-------|-----|
| How long a sign-in lasts | env `ACCESS_TOKEN_EXPIRE_MINUTES` | 10080 (7 days) |
| Confirmation link life | `CONFIRM_TTL_HOURS` in `auth.py` | 48 |
| Reset link life | `RESET_TTL_MINUTES` in `auth.py` | 60 |
| Minimum password length | `auth.py` | 8 |
| Facebook permissions asked for | env `META_SCOPES` (fallback: `_DEFAULT_SCOPES` in `app/api/oauth.py`, kept identical by `tests/test_meta_scopes.py`) | ads_management, ads_read, pages_manage_ads, read_insights, business_management, pages_read_engagement, pages_show_list, pages_manage_posts, instagram_basic, instagram_content_publish, instagram_manage_insights, instagram_manage_comments, pages_read_user_content, email |
| Meta app and API version | env `META_CLIENT_ID`, `META_REDIRECT_URI`, `META_API_VERSION` | set on Render |
| Email providers | env `RESEND_API_KEY`, `MAIL_FROM`, `SMTP_*` | Resend first, then SMTP |
| Sweep frequency | the scheduler (`DEPLOY.md`) | every 6 hours |
| Meta notice wording | `META_ISSUE_SHORT`, `metaLimitLine()` in `onboarding.js` | — |
| Which Setup step each issue opens | `META_GUIDE` in `onboarding.js` | page, admin, instagram, ads |

---

## 10. Connections

- **Hands on:**
  - to the **Brand engine**: the signed-in agent plus their Facebook Page and Instagram (Step
    2);
  - to the **Campaign engine**: whether campaigns are allowed (a Facebook login happened) and
    the capabilities (Facebook posts, Instagram posts, the ad);
  - to the **Active campaign engine**: the token and Page the publisher posts with, and
    whether posts must be held.
- **Takes from the Support engine:** setup-call booking (`/onboarding/setup-session`).

---

## 11. Tests

**Exist:**

- `tests/test_oauth_callback.py`
- `tests/test_onboarding_gate.py`
- `tests/test_token_health.py`
- `tests/test_new_campaign_flow.js` (the + Campaign gate)

**Missing:**

- one test per Meta outcome (Meta Integration spec §11);
- a reconnect that changes the Page and Instagram;
- a login with no ad account still saves the connection.

---

## 12. Open work

In the Meta Integration spec §12:

1. The `meta_connections` table; save on every login; overwrite on reconnect.
2. The seven checks and the outcome table in one service; "connected" means a Page.
3. Checks on sign-in, Check again (forced), nightly, and before publishing and launch.
4. Page picker; dashboard warning for dead logins; breakage emails.
5. The AI error explainer and the help-chat context.
6. Wire Step 2 to the Brand engine.
