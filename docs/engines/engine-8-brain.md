# Engine 8 brain: Run it until it sells

**Status:** greenlit by Adam (22 Nov) · **Builds in:** PR #29 · **Started:** 22 Nov 2026
**Existing:** `app/services/renewals.py` and `scripts/until_sold_due.py` (Dan), `claude/until-it-sells-pr6-for-dan.md` (front end, PR #6), Ad Engine spec §7 (Run it again). This brain sets the direction; where they differ, this brain wins.

---

## 1. Job

**Set it and forget it (Adam, 22 Nov).** When an agent turns on **Run it until it sells**, Resmara keeps
marketing the home with a brand-new 14-day campaign every 2 weeks, **$39 each**, until the listing
sells. The agent doesn't approve anything and doesn't need to log in: it's the same house, renewed
with fresh content. Resmara talks to them **by email** at every turn that matters.

Agents whose campaign ends **without** it turned on get the **Run it again · $39** offer (section 8).

**Starts:** the agent turns it on (in Confirm your launch details, or on the campaign card).
**Ends:** the listing sells, or the agent turns it off.

## 2. What exists today (Dan's `renewals.py`), and what changes

| Today | Change |
|---|---|
| 3 days before a round ends: **charge $39, then build** | **Build first, charge only when the build succeeds** (Engine 4). A failed build is never charged; it retries, then alerts the team |
| Emails "ready to look over" | **Goes live automatically** on day 15. The email says it's renewed and going live; there's nothing to do |
| The publisher only posts approved posts, so a round may never launch | A renewed round is **approved automatically** (the agent approved the whole series when they turned it on) |
| Declined card: round removed, retried daily, **no email** | Retry up to **3 times** (once a day), then email with **Check billing** (section 6) |
| Stops on pending/sold from the old 6-hour word-matching check, and **turns itself off** | Uses Engine 6's hourly self-healing check. **Pending pauses it; it stays on** and continues if the deal falls through. **Sold ends it** (section 5) |
| Learns from the last round (best photos and formats, new words, no repeated headlines) | Keep. Plus a fresh look at the listing each round (section 4) |
| Same ad budget each round, billed by Meta | Keep |
| At most 3 renewals per run (a safety limit) | Keep |

## 3. A round, step by step

1. **3 days before the current round ends**, Resmara re-reads the listing (Engine 3) for anything new:
   status, new photos, an open house, a changed price (section 4).
2. **It builds the next 14 days** (Engine 4) from the last round's results (`round_learning.py`):
   - leads with the photos, formats and styles that earned the most attention;
   - **never repeats** a story angle, headline or hook from earlier rounds; leads with photos not
     used yet;
   - **new ad hooks** from the hook library (Engine 4); hooks that won last time can return with
     new words;
   - the same website link, refreshed with the new story (Engine 5).
3. **It runs the same checks as a first build** (Engine 4's Art Director check, the checker, Fair
   Housing, the platform rulebook for the ad).
4. **When the build succeeds, it charges $39** to the card on file.
5. **It's approved automatically** and **goes live on day 15**, right when the current round ends, with
   the same ad budget and the same ad hours (no ads 11 PM to 6 AM).
6. **The agent gets one email** (section 7): "Round 3 for 1248 Oakridge Drive is ready and goes live
   Saturday. Nothing to do."
7. Engine 6 runs it like any live campaign: posting, the ad audit, leads, reports.

## 4. Each round re-reads the listing, and pricing

- **New photos** on the listing are added to the home's file and used first.
- **An open house** added to the listing becomes a post and the website's open house band.
- **Pricing (Adam, 22 Nov):** Resmara stays away from promoting prices. **Only if a price change is
  validated** (the same new price on the agent's listing and at least one other source, read from
  the listing's price field, never guessed), the next round can lead with it, worded only as
  **"Improved price"** or **"Updated pricing"**. **Never a number, never "price reduction" or "price
  drop"**, never the old price. If the price can't be validated, the round says nothing about price.

## 5. Pending, sold and falling through (with Engine 6)

| What happens | Run it until it sells | Email to the agent |
|---|---|---|
| **Goes pending** | Everything pauses right away (Engine 6). **It stays on**, paused, and **no round is built or charged** while it's pending | "Looks like 1248 Oakridge Drive went pending, so we paused your campaign. We'll keep checking every day: if it comes back on the market we'll pick up where we left off, and if it sells we'll close it out." |
| **Comes back on the market, same listing agent** | **Picks up automatically** (set it and forget it): the paused round resumes with its remaining days, and the renewals continue | "1248 Oakridge Drive is back on the market, so your campaign is running again." |
| **Back on the market, different listing agent** (or can't confirm it's the same agent) | Does nothing; stays paused (Engine 6, section 7) | None |
| **Sells** | **Ends**: the campaign closes as **Completed · Sold**, no more rounds, no more charges | None (Adam: it just shows Sold) |
| **The agent turns it off** | The current round finishes; no more rounds | None |
| **The agent pauses it** | No round is built or charged until they resume | None |

**Note:** for campaigns **without** Run it until it sells, a deal that falls through still waits for the
agent to click **Turn it back on** (Engine 6). The automatic pick-up is only for agents who chose set
it and forget it.

## 6. A declined card (Adam, 22 Nov)

1. The build is done but the charge is declined: **nothing is charged, nothing goes live**, and the
   current round keeps running to its end.
2. Resmara **tries again once a day, up to 3 times**.
3. After the 3rd decline, it emails the agent: **"We couldn't renew your campaign for 1248 Oakridge
   Drive because your card was declined. Please check your billing on Resmara."** with a **Check
   billing** button that opens Billing. The campaign card shows **Renewal on hold: card declined ·
   Check billing**.
4. **As soon as a working card is saved**, Resmara charges it and the waiting round goes live
   (or, if the old round has already ended, the new one goes live the next morning). No other step.
5. The built round is kept for 14 days; after that it's rebuilt fresh when the card works, so the
   content is never stale.

## 7. The emails (the agent's main window into it)

Agents on set it and forget it may not open Resmara for months, so **email is how Resmara talks to
them**. Every email is short, in Resmara's look, with one button.

| When | Subject | Button |
|---|---|---|
| A round is renewed (built and charged) | "Round 3 for 1248 Oakridge Drive goes live Saturday" | **See the campaign** |
| It goes pending | "1248 Oakridge Drive went pending, so we paused your campaign" | **See the campaign** |
| Back on the market (same agent) | "1248 Oakridge Drive is back on the market. Your campaign is running again" | **See the campaign** |
| Card declined 3 times | "We couldn't renew your campaign for 1248 Oakridge Drive" | **Check billing** |
| A day 7 and day 14 report is ready (Engine 6) | "Your day 7 report for 1248 Oakridge Drive" | **See your report** |

The receipt for each $39 charge is Stripe's, as today.

## 8. Run it again · $39 (campaigns without it turned on) (Adam, 22 Nov)

It's an upsell and Resmara pushes it:
- **Day 12 of a campaign without Run it until it sells:** an email "Keep the momentum going on 1248
  Oakridge Drive" with **Run it again · $39** and **Turn on Run it until it sells**.
- **When the campaign completes:** the card offers **Run it again · $39** (built in PR #1), and the same
  email goes out once more if they haven't acted.
- **One click** builds a fresh round the same way as section 3 (build, then charge the saved card,
  then it goes live), with the launch details pre-filled.
- **Not sent** when Run it until it sells is on, or when the listing is pending or sold.

## 9. Decided with Adam (22 Nov 2026)

- Set it and forget it: rounds go live automatically; the agent approves nothing after turning it on.
- Email is the way Resmara talks to set-and-forget agents.
- Pending pauses it and it stays on; back on the market with the same agent picks up automatically;
  sold ends it (no email).
- A declined card is retried up to 3 times, then an email with Check billing; it continues as soon as
  the card works.
- No limit and no check-ins: it runs until it sells or they turn it off.
- Price changes only when validated, worded "Improved price" or "Updated pricing", never a number.
- Run it again · $39 keeps going out to campaigns without it turned on.

## Screens

Mockups from the preview (`engine-8-screens/`, with `mockup.js`, the preview script they were taken
from). Mockups only: the brain above is what to build. The emails go out from Resmara's own email
(Resend, as today) in Resmara's look.

| Screen | What it shows |
|---|---|
| `01-email-renewed.png` | A round is renewed and goes live Saturday; nothing to do |
| `02-email-pending.png` | It went pending: paused, checking every day |
| `03-email-back-on-market.png` | Back on the market with the same agent: running again |
| `04-email-card-declined.png` | Card declined after 3 tries: Check billing |
| `05-email-run-it-again-day-12.png` | Campaigns without it on: Run it again · $39 or Run it until it sells |
| `06-card-renewal-on-hold.png` | The campaign card when a renewal is on hold |

Live preview: https://claude.ai/artifact/Lip2AN9HQZuLf4J5AsP8Vy#emails
