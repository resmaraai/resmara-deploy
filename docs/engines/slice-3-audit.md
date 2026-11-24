# Slice 3 audit: the brains vs the code (23 Nov 2026, 7 PM)

**Slice 3 = the business side:** Billing (Engine 10), Support & Ask Resmara (Engine 11), Marketing
pages (Engine 9). Read on top of the slice 2 branch (PR #40).

**Key:** ✅ in the code · 🟡 partly · ❌ missing · 🔒 blocked on an account or a key

## Marketing (Engine 9): built by Dan on 23 Nov, not touched here

Attribution, the Marketing parent page, Digital ads, Email campaigns and Website tabs are in `app/api/marketing.py`
and `static/admin.html`, with tests. 🔒 Waiting on Resmara's own Meta ad account and token, a GA4 property,
and a Mailchimp key and audience. Nothing to build in this slice; it's Dan's engine.

## Billing (Engine 10)

| Brain decision | Status | Where / what's wrong |
|---|---|---|
| Prices only on the server, screens read `/api/billing/config` | 🟡 | server has them; `billing.js` hard-codes `BILLING_PRICE_CENTS = 4900` |
| Card form inside the Resmara pop-up (Stripe Payment Element), never Stripe's page | ❌ | `/billing/card` opens Stripe Checkout (setup mode) |
| Build first, pay to unlock; saved card charged when the build finishes | ✅ | slice 1 (#39) |
| Run it again and renewals build first, then charge | ✅ | slice 2 (#40) |
| Idempotent charges (campaign + round) | ✅ | `charge_saved_card` |
| Stripe Tax on every charge; tax shown | ❌🔒 | no `automatic_tax`; Adam switches Stripe Tax on in Stripe first |
| Change card in the pop-up; **Remove card** (refused while Run it until it sells is on) | ❌ | no remove; change opens Stripe's page |
| Card-expiring email (30 days, while Run it until it sells is on) | ❌ | |
| Billing page: card, **Coming up** with Turn off, Purchases with tax, status and **Receipt** | 🟡 | purchases list only; no Coming up, receipt or tax |
| Emails: renewal terms when turned on, yearly reminder, price change notice, refund | ❌ | (Dan has Build room tasks #65 renewal consent and #67 yearly reminder) |
| Refund from Team room → Finance with a reason | 🟡 | failed-build refund exists; no team Refund button |
| Chargeback: pause charges, alert the team, show the evidence | ❌ | no dispute webhook |
| Close my account: confirm by typing the email (no password); stops everything at once | 🟡 | `POST /auth/me/close` exists (Engine 1); asks for a password; doesn't cancel posts, pause ads, turn off renewals, take websites down or detach the card |

## Support & Ask Resmara (Engine 11)

| Brain decision | Status | Where / what's wrong |
|---|---|---|
| Chat answers from the guide, library, approved answers and the account | ✅ | `help.py` |
| First message says it's an AI assistant | ❌ | |
| Signed-out visitors get product answers | 🟡 | to check |
| Support page: Which listing?, the 1 business day promise, "We'll reply by Tuesday at 5 PM" | ❌ | subject and message only |
| Confirmation email to the agent; requests to support@resmara.com | ❌🔒 | emails operator addresses; the shared inbox doesn't exist yet |
| Each team reply emailed to the agent with See the reply | ❌ | |
| Four statuses: Received, Answered, Waiting on you, Closed; closes 7 days after an answer | ❌ | open / in_progress / resolved / closed |
| Team room: reply-by time (orange past due, Due soon), Save as a chat answer | 🟡 | misses and answers exist; no reply-by, no save-from-reply |
| Setup session: the Resmara Calendly event; bookings in the Team room | 🔒 | Adam's Calendly event |

## Build order

1. Engine 10: prices from config, the card form in the pop-up (Payment Element), Remove card, Coming up,
   receipts and tax on purchases (tax switched on by a setting once Stripe Tax is live), the refund button,
   the dispute webhook, closing an account that stops everything, the money emails.
2. Engine 11: the AI line, Which listing? and the promise, reply-by times, the four statuses and auto-close,
   reply emails, confirmation emails, Save as a chat answer.

## Built (23 Nov 2026)

**Engine 10:** every ❌ and 🟡 above is built, except the emails Dan owns in the Build room (#65 renewal
consent, #67 yearly reminder) and the price-change notice (prices are set on Render, so the 30-day notice
goes out by hand until there's a price screen).

- Prices from `/api/billing/config`; card form inside the pop-up; Change card replaces the old one; Remove
  card (refused while Run it until it sells is on); Coming up with Turn off; Purchases with what it was,
  tax, status and Receipt.
- Stripe Tax behind `RESMARA_STRIPE_TAX=1` (off until Adam turns Stripe Tax on and registers).
- Chargebacks pause the account and alert the team; Finance → Purchases → Refund (full or partial).
- Card-expiring email; Close my account by typing the email, stopping everything at once.
- **Close vs reopen:** Engine 1 (§5) says closing can be undone by logging in; Engine 10 (§10) says it
  can't and data goes within 30 days. Built as both: everything stops at once, logging in within 30 days
  reopens it, and on day 31 the details are deleted (purchases kept). Adam to confirm.

**Engine 11:** the AI line in the chat; Which listing?, the 1 business day promise and "We'll reply by
Tuesday at 5 PM" (page and email); the four statuses; the agent replies on the request; replies signed
"Adam from Resmara" with See the reply; auto-close after 7 days; Team room reply-by (orange past due,
Due soon), the listing and account snapshot on each request. Save as a chat answer already existed.

**Still blocked (🔒):** support@resmara.com (set `RESMARA_SUPPORT_EMAIL` once the inbox exists; until then
requests go to the operator addresses), email replies added to a request (needs the inbox), the Resmara
setup session Calendly event and its bookings in the Team room.

Tests: `tests/test_engine10_billing.py` (43), `tests/test_engine11_support.py` (31).
