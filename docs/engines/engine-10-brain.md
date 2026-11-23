# Engine 10 brain: Billing

**Status:** greenlit by Adam (22 Nov) · **Builds in:** PR #35 · **Started:** 22 Nov 2026
**Existing:** `app/services/billing.py`, `app/api/billing.py`, `static/billing.js` (Dan and Adam), Engine 4 (build first, then pay to unlock), Engine 8 (Run it until it sells, declined cards), Terms of Service §7, §8 and §18 (PR #33). This brain pulls every money rule into one place; where it differs from the code, this brain wins.

---

## 1. Job

Take payment for what an agent orders, simply and correctly, and never surprise them. One card on file,
charged only for a campaign they built, a round they asked for, or a Run it until it sells round they
agreed to. One Billing page shows the card, what's coming up, every purchase with its receipt, and
Close my account.

**Starts:** the first campaign an agent unlocks. **Ends:** the account is closed.

## 2. What exists today, and what changes

| Today | Change |
|---|---|
| $49 a campaign; the price lives in `billing.py` **and** is hard-coded in `billing.js` (`BILLING_PRICE_CENTS`) | Prices live only on the server (section 3); the front end reads them from `/api/billing/config` |
| The first card is added on **Stripe's own Checkout page** | **Stripe's card form inside the Resmara pop-up** (Stripe Payment Element), never a separate page (Engine 4 decision) |
| Charged before the build (`/billing/charge`, paywall 402) | **Build first, then pay to unlock** (Engine 4): the campaign is built, shown blurred, then charged |
| Failed build after payment: `refund_failed_build` refunds it | Keep. Plus: with build-first, a failed build is never charged at all |
| No sales tax | **Stripe Tax** adds tax where a state requires it (section 6) |
| Purchases list: address, amount, status, date | Add tax, **Receipt** (Stripe's receipt link) and **Refunded** status; add **Coming up** (section 7) |
| One saved card shown; **Change card** opens Stripe's page | Change card in the pop-up; **Remove card** (section 4) |
| Close my account asks for the **password** | Facebook-only login has no password (Engine 1): confirm by **typing the account email**. Closing **stops everything right away** (section 10) |
| Prepaid 4-campaign pack withdrawn; old balances still honoured | Keep honouring them; nothing new |
| No dispute handling | A chargeback pauses new charges and alerts the team (section 9) |

## 3. Prices (one place)

| What | Price | Charged when |
|---|---|---|
| A listing campaign | **$49** | The build finishes and the agent unlocks it (or straight away with a saved card) |
| Run it again (a fresh round on an ended campaign) | **$39** | The new round is built |
| Run it until it sells, each round | **$39** | Each new round is built, about 3 days before the current one ends (Engine 8) |
| Ad budget | Set by the agent | **Never by Resmara:** Meta bills the agent's own ad account |

- Prices come from server config (`RESMARA_PRICE_CENTS`, `RESMARA_REPEAT_PRICE_CENTS`) and are sent to the
  front end; every screen and email reads them, so one change updates everything.
- Tax is added on top where it applies (section 6). Screens say **"$49 + tax where it applies"**
  until the agent's ZIP is known, then the real total.
- Promotional prices and codes are for the growth engine (later).

## 4. The card

- **One card on file**, saved with Stripe. Resmara never sees the number (Privacy Policy).
- **Adding it:** in the pay-to-unlock pop-up, Stripe's card form (card number, expiry, CVC, ZIP) sits
  inside the Resmara pop-up, with **"Save this card for future campaigns"** ticked by default. The ZIP is
  what Stripe Tax uses.
- **Change card:** Billing → Change card opens the same form in a pop-up. The new card replaces the old
  one for everything, including Run it until it sells.
- **Remove card:** allowed, unless Run it until it sells is on for any listing. Then the pop-up says
  "Run it until it sells is on for 1248 Oakridge Drive. Add a new card, or turn it off first." Nothing
  is ever left on with no card.
- **Card about to expire** and Run it until it sells is on: an email 30 days before ("Your card ending
  4417 expires next month. Update it to keep 1248 Oakridge Drive running."), with **Update card**.
- **Banks that ask the agent to confirm** (3-D Secure): the pop-up shows the bank's step; for an
  automatic renewal, it's treated as a decline (section 5) and the email asks them to confirm.

## 5. When charges happen

1. **A campaign (Engine 4):** built first, shown blurred with "Pay $49 to unlock it". With a saved card,
   charged when the build finishes. A failed build is never charged.
2. **Run it again:** one click, built, then charged, then live (Engine 8 §8).
3. **Run it until it sells (Engine 8):** each round is built, then charged, only with the agent's
   recorded auto-renewal consent (Terms §8, PR #33).
4. **A declined card:** nothing goes live, retried once a day up to 3 times, then the Check billing email
   and "Renewal on hold" on the card (Engine 8 §6). For a first campaign, the pop-up says "Your payment
   didn't go through. Please check your card and try again" with **Try again** and **Use another card**.
5. **Every charge is idempotent:** one charge per campaign or round (Stripe idempotency key = campaign and
   round), so a retry can never charge twice.

## 6. Sales tax (Adam, 22 Nov)

- **Stripe Tax** works out whether tax applies from the agent's ZIP and adds it to the charge. About 20
  states tax software; California doesn't tax it today. Stripe Tax keeps that table current.
- **Registration is Adam's:** Stripe Tax shows when sales in a state pass that state's threshold; Resmara
  registers there before collecting. Until registered in a state, no tax is collected there.
- Stripe Tax costs 0.5% of each sale it calculates tax on.
- Receipts and the Billing page show the tax line.

## 7. The Billing page

Top to bottom:
1. **Card on file:** "Visa ending 4417 · expires 08/28" with **Change card** and **Remove**. No card:
   "No card saved yet. You'll add one when you unlock your first campaign," with **Add a card**.
2. **Coming up** (only when Run it until it sells is on): each listing, the next charge date and amount
   ("1248 Oakridge Drive · $39 + tax · about Dec 3 · Round 3"), and **Turn off** right there. This is the
   one-click turn-off the auto-renewal law requires.
3. **Purchases:** date, listing, what it was (Campaign, Run it again, Round 3), amount, tax, status (Paid,
   Refunded, Declined) and **Receipt** (opens Stripe's receipt). Newest first.
4. A line: "Your ad budget is billed by Meta to your own ad account, so it isn't here."
5. **Close my account** at the bottom (section 10).

## 8. Emails about money

Resmara's own emails (Resend, in Resmara's look), plus Stripe's receipt for every charge:

| When | Email |
|---|---|
| A campaign or round is charged | Stripe's receipt (amount, tax, card) |
| Run it until it sells turned on | The renewal terms, how to turn it off, a **Manage** button (Terms §8; California law) |
| Each renewal | Engine 8's "Round 3 goes live Saturday" email, with the amount |
| Once a year while it's on | A reminder: it's on, $39 every 2 weeks, **Turn off** |
| Price change | At least 30 days before, for anyone with it on |
| Card declined 3 times | Engine 8's Check billing email |
| Card expiring (it's on) | Section 4 |
| Refund | "We refunded $49 for 1248 Oakridge Drive. It reaches your card in 5 to 10 days." |
| Account closed | "Your account is closed" with what stopped (section 10) |

## 9. Refunds and disputes

- **Refunds follow the Terms (§7):** automatic when a build fails after a charge (exists); otherwise only
  by the team. Team room → Finance → a purchase → **Refund** with a reason (full or partial). The agent
  gets the refund email; the purchase shows **Refunded**.
- **A chargeback** (Stripe `charge.dispute.created`): Run it until it sells and new charges pause on that
  account, the team gets an alert, and the Team room shows the dispute with what Stripe needs: the
  agreement record (Terms version, time, IP), the renewal consent, the receipt and the campaign. The team
  answers it in Stripe. Won: everything resumes. Lost: the account stays paused until the agent contacts
  support.

## 10. Closing an account (Adam, 22 Nov): everything stops right away

1. Billing → **Close my account**. The pop-up says exactly what happens: "Your posts and ads stop, Run it
   until it sells turns off, your listing websites come down, your saved card is removed, and your
   data is deleted within 30 days. Nothing is refunded. This can't be undone." The agent types their
   account email and clicks **Close my account**. No password (Facebook login).
2. Straight away: scheduled posts cancelled; ads Resmara runs paused in Meta; Run it until it sells off
   for every listing; built-but-unpaid rounds discarded; listing websites show "This page is no longer
   available"; the card detached from the Stripe customer; Meta disconnected (Data Deletion page).
3. Posts and ads already published stay on the agent's Page and ad account (they own them).
4. Purchases are kept for tax and accounting (Privacy Policy); everything else is deleted within 30 days.
5. The "Your account is closed" email confirms it.

## 11. Team room

- **Finance** (exists): each purchase gets **Refund** (section 9); disputes listed at the top in orange
  until answered.
- Revenue counts exclude refunds and tax (tax isn't Resmara's money).

## 12. Setup

- **Dan:** Stripe Payment Element in the pop-up (replaces Checkout for adding a card); Stripe Tax on the
  charges; idempotency keys; the dispute webhook; Remove card; Coming up; receipts on purchases;
  close-account steps (section 10); the emails in section 8; prices only from config.
- **Adam:** turn on Stripe Tax in the Stripe dashboard (business address, product tax code for SaaS);
  register in a state when Stripe says its threshold is near. Never enter card or bank numbers through
  Claude.

## 13. Decided with Adam (22 Nov 2026)

- One card on file; Stripe's card form inside the Resmara pop-up, never a separate Stripe page.
- Prices in one place on the server; $49 a campaign, $39 Run it again, $39 each Run it until it sells round.
- Stripe Tax collects sales tax where a state requires it.
- Closing an account stops everything right away; nothing is refunded; purchases are kept for tax.
- Refunds only as the Terms say; a chargeback pauses charges and alerts the team.

## Screens

Mockups from the preview (`engine-10-screens/`, with `mockup.js`, the preview script they were taken from). Mockups only: the brain above is what to build.

| Screen | What it shows |
|---|---|
| `01-billing-page.png` | The Billing page: card on file, Coming up (Run it until it sells, with Turn off), purchases with tax and Receipt |
| `02-change-card.png` | Change card: Stripe's card form inside the Resmara pop-up |
| `03-remove-card-until-sold.png` | Remove card while Run it until it sells is on: add a new card or turn it off first |
| `04-turn-off.png` | Turn off Run it until it sells from Coming up |
| `05-close-account.png` | Close my account: everything stops right away, confirm by typing the email |

Live preview: https://claude.ai/artifact/Lip2AN9HQZuLf4J5AsP8Vy#billing
