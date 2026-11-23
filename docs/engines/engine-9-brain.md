# Engine 9 brain: Marketing (Website, Email campaigns, Digital ads) in the Team room

**Status:** greenlit by Adam (22 Nov) · **Builds in:** PR #31 · **Started:** 22 Nov 2026
**Includes what was Engine 7 (Marketing)** (Adam, 22 Nov). The growth plan (Founding Agents, coach referral codes) is a separate engine, later.

---

## 1. Job

Give the team one place to see whether Resmara's own marketing is working, and the detail behind it.
**Marketing is the parent page**; its three channels sit under it in the Team room's **Business** menu:

| Business menu | What it shows |
|---|---|
| Growth | Sales against the monthly goal (as today) |
| **Marketing** (the parent) | All three channels together: cost, sign-ups, paying agents, money back, and a verdict for each. **Is it working?** |
| &nbsp;&nbsp;Website | resmara.com: visitors, where they come from, sign-ups, top pages, Clarity (today's page, plus where each visitor is counted) |
| &nbsp;&nbsp;Email campaigns (new) | Every marketing email Resmara sends, through Mailchimp |
| &nbsp;&nbsp;Digital ads (new) | Every campaign and ad on Resmara's own Meta ad account (today's Marketing numbers move here) |

These are **Resmara's own** marketing, not the agents' campaigns.

## 1a. How the numbers are counted (the glue)

1. **Every sign-up is stamped with where it came from** when the account is made: the ad (its tracking
   tags on the link to resmara.com), or the website on its own (Google, typed in, shared links).
   Saved on the account; never changed after.
2. **Each paying agent counts once**, for the **last** thing that got them to buy their first
   campaign: the ad they came from, the email they clicked (Mailchimp click tracking, within 7 days
   before buying), or the website. Signed up from an ad, then bought from the day 5 email: counts for
   Email. Nothing is counted twice, so the channel rows add up to the total.
3. **Money back** = every campaign those agents bought in the period, at what they paid ($49 a
   campaign today; Run it again and Run it until it sells counted at their real price).
4. **Cost:** ad spend is read from Meta on its own. The Mailchimp plan and the website hosting are
   monthly amounts typed in once in **Settings** (editable), spread evenly across the weeks.
5. **Verdict:** **Working** = the agents a channel brought in paid more than it cost. **Not working** =
   it cost more than it brought back. Same rule on each ad.

## 1b. Marketing (the parent page)

- **Top band**, last 30 days: spent on marketing, sign-ups, paying agents, cost per paying agent, money
  back (campaigns × price).
- **Is each channel paying for itself?** One row each for Digital ads, Email campaigns, Website: cost,
  sign-ups, paying agents, per paying agent, money back, back for every $1, verdict. An **All marketing**
  total row. Click a row to open that channel's page.
- **Paying agents each week:** by channel, with the total and what was spent that week.
- **How the numbers are counted:** the three rules above, in plain words, on the page.

## 2. Email campaigns

**Mailchimp, through its API (Adam, 22 Nov).**
- Resmara has its own Mailchimp account. Adam sets it up and gives Claude access; **Claude builds every
  email in Mailchimp in Resmara's look**. The API key goes to Dan for Render; it's never sent by email
  or chat.
- **The audience syncs itself:** every client account's email goes into a Mailchimp audience
  ("Resmara clients") automatically when they sign up. Closed accounts and test accounts come off.
  Each contact is tagged: *signed up, no campaign yet* · *has run a campaign* · *Run it until it sells
  on*. **Export emails (CSV)** stays as a backup button (test and closed accounts left out,
  unsubscribes marked).
- **The series** (each written once and approved by Adam; each starts on its own from the contact's tag):
  1. **Welcome**, everyone who signs up: day 0, 3, 7, 14.
  2. **Start your first campaign**, signed up but no campaign yet: day 2, 5, 10. (No outside lists:
     the people who haven't bought yet are already Resmara accounts.)
  3. **Tips and updates**, current clients: every 2 weeks.
- **Campaign emails stay in the app** (leads, renewals, reports, pending, price changes: Engines 6 and
  8), sent by Resmara itself through Resend. They're not marketing and always go out.
- **Consent:** one line at sign-up ("Resmara will send you tips and updates now and then. Unsubscribe
  any time."), an on/off setting on each account that syncs to Mailchimp, and Mailchimp's unsubscribe
  link in every marketing email. Someone who unsubscribes is never emailed marketing again.

**The page tracks:**
- At the top, last 30 days: people on the list, opened, clicked, **paying agents who bought after an
  email**, unsubscribed.
- **Mailchimp:** connected or not, the audience, contacts, last sync; **Export emails (CSV)** and
  **Open Mailchimp**.
- **Every email we're running:** each series and each email in it, with sent, opened and clicked
  (read from Mailchimp's reports), and whether the series is on.
- **What the emails brought in:** paying agents, campaigns bought and money back by series. Its total
  is the Email campaigns row on Marketing.
- **Who's on the list:** how many contacts carry each tag, and how many unsubscribed.

## 3. Digital ads

A new page. Today's Marketing numbers (spend, leads, cost per lead, new paying agents, "From ad to
paying agent", "Each week") move here, plus:
- **Every campaign and ad we're running:** each campaign in Resmara's own Meta ad account (we run
  several at once), with spend, clicks, sign-ups, paying agents, per paying agent, money back and
  status. Click a campaign to open its ads; each ad has the same numbers, where it runs, running or
  paused, and its verdict. Pause or run an ad from its status button. An **All ads** total row, which
  is the Digital ads row on Marketing.
- **Sign-ups and paying agents are matched to the ad that brought them** (section 1a).
- Today's "Is it worth it?" box comes off: the verdict lives on Marketing now.
- Until Resmara's ad account is connected (`META_AD_ACCOUNT_ID`, `META_SYSTEM_TOKEN`), it says so, as
  today; sign-ups and paying agents still show, because they're counted from Resmara's own database.

## 3a. Website

Today's page stays (Google Analytics, Clarity, PageSpeed), plus:
- Top band: visitors, sign-ups, visitors who sign up (%), **came on their own**, **paying agents
  credited to the website**.
- **Who came, and where they're counted:** visitors who clicked an ad (counted under Digital ads), came
  on their own (counted under **Website**), clicked an email (counted under Email campaigns), each with
  visitors, sign-ups and paying agents. Everyone lands on the site, so this page shows all of it; the
  Website row on Marketing only counts the people who came on their own.

## 4. Setup

- **Adam:** create Resmara's Mailchimp account; give Claude access to build the emails; connect
  Resmara's own Meta ad account.
- **Dan:** the Mailchimp API key on Render; the audience sync and tags; the reports read; the consent
  setting; the Business menu change; the source stamp on every sign-up and the paying-agent credit (1a); the
  Marketing parent page; the campaign and ad list; the Mailchimp and hosting costs in Settings.
- **Sending domain:** Mailchimp needs resmara.com verified (two DNS records in GoDaddy). Claude can add
  them with Adam's OK once Mailchimp shows them.

## 5. Decided with Adam (22 Nov 2026)

- Engine 7 is folded in here; the growth plan is a separate engine later.
- **Marketing stays and is the parent page**; Website, Email campaigns and Digital ads sit under it,
  each with its own tracking. Marketing brings them together and answers "is it working, and is it
  worth what it costs?"
- Each paying agent counts once, for the last thing that got them to buy; every sign-up is stamped
  with where it came from.
- Mailchimp through its API for automated marketing emails; a fixed series approved by Adam; Claude
  builds them in Mailchimp in Resmara's look.
- The audience is Resmara's own client accounts (synced, with a CSV export); no outside lists.

## Screens

Clickable preview (sample numbers): https://claude.ai/artifact/UYQnJ1FtEf77oiNUbD91ty

| Screen | File |
|---|---|
| Marketing (the parent) | `engine-9-screens/01-marketing.png` |
| Digital ads | `engine-9-screens/02-digital-ads.png` |
| Email campaigns | `engine-9-screens/03-email-campaigns.png` |
| Website | `engine-9-screens/04-website.png` |
| Preview source (one self-contained page) | `engine-9-screens/preview.html` |

## Built (23 Nov 2026)

PR #31 carried this brain and the screens and no code, so the tabs were never in the Team room.
The build is in `app/` and `static/admin.html`:

| Piece | Where |
|---|---|
| The three rules (stamp, one credit per agent, nothing counted twice) | `app/services/attribution.py` |
| The stamp at sign-up (utm tags, `fbclid`, ad or campaign id, referrer) | `POST /api/auth/register` via `static/api.js`; stored on `users.signup_source` |
| The credit at payment | `app/api/billing.py` writes `boosts.paid_source` |
| Marketing (the parent), Digital ads, Email campaigns, Website | `app/api/marketing.py`; the Business menu in `static/admin.html` |
| Mailchimp: audience, tags, series, reports, CSV, click lookup | `app/services/mailchimp.py` |
| Meta: campaigns, ads, pause/run | `app/services/marketing_ads.py` |
| The two monthly costs | Settings, stored in `marketing_settings` |
| Tests | `tests/test_engine9_marketing.py` |

**Still Adam's:** the Mailchimp account and its API key (to Render, never by email or chat), the two
Mailchimp DNS records in GoDaddy, Resmara's own Meta ad account connected, and the emails
themselves built in Mailchimp in Resmara's look. Until those exist the pages say so and keep
showing the numbers we own: sign-ups, paying agents and money back.
