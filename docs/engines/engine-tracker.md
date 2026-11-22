# Resmara engine tracker

**Keep this table.** It tracks each engine through our process, not whether it's live:

1. **Brain written:** Adam explains the logic, guardrails and references, and Claude writes the brain doc.
2. **Designed:** every revision is mocked up and previewed, and Adam greenlights it.
3. **Sent to Dan:** packaged as its own PR and sent to Dan by email and Chat for implementation.

Each engine also has a Build room ticket in the Team room. **Started:** 21 Nov 2026 · **Last updated:** 22 Nov 2026

| Engine | Brain written | Designed | Sent to Dan | Brain doc |
|--------|---------------|----------|-------------|-----------|
| **Engine 1 · Login and Meta integration** (account, Meta connection, audit, setup to-do list; ends at Show me around) | ✅ Done | ✅ Greenlit | ✅ **PR #18**, 22 Nov (merged) | `engines/engine-1-brain.md` |
| **Engine 2 · Brand** (quick AI investigation during sign-up that researches the agent and builds their brand page) | ✅ Done | ✅ Greenlit | ✅ **PR #22**, 22 Nov (merged) | `engines/engine-2-brain.md` |
| **Resmara sign-up tour** (finish pop-up, fixes first, one setup plan, tour, first campaign: build then pay to unlock; carries Engine 1's Facebook-only log-in and no teams) | ✅ Done | ✅ Greenlit | ✅ **PR #23**, 22 Nov (merged) | `engines/resmara-signup-tour-engine.md` |
| **Engine 3 · Listing link** (the link identifies the house; AI builds the home's file from every source; the gate for the build; plus the one-box Accounts setup) | ✅ Done | ✅ Greenlit | ✅ **PR #24**, 22 Nov | `engines/engine-3-brain.md` |
| **Engine 4 · Campaign build** (14 one-of-a-kind posts and the ad from the brand kit, the home's file, the style profile and the trend brief; learns from 👍 / 👎, edits and results) | ✅ Done | ✅ Greenlit | ✅ Sent 22 Nov (PR number filled in when opened) | `engines/engine-4-brain.md` |
| **Engine 5 · Website** | Not started | — | — | — |
| **Engine 6 · Active campaign** (ad, publishing, leads, reports) | Not started | — | — | — |
| **Engine 7 · Marketing** | Not started | — | — | — |
| **Engine 8 · Run it until it sells** | Not started | — | — | — |
| **Engine 9 · Email campaigns, Digital ads and the Marketing overview** (Team room; moved to the end, Adam 22 Nov) | 📝 Logged | — | — | Notes below |

PR numbers are filled in only once the PR is opened, never planned ahead (Adam, 22 Nov).

## Client journey map

Every screen and branch from the website to the first live campaign, with screenshots:
https://claude.ai/artifact/X8J4hm7tRAdokpEUYsv4Kb (22 Nov). Its screenshots also go into the repo with
the sign-up tour PR, under `docs/journey/`.

## Up next

1. **Engine 5 · Website** (next): the shareable listing link with Copy link.
2. Engines 6–8 in order.
3. Engine 9 · Email campaigns, Digital ads and the Marketing overview.
4. Not engines, after them: the AI tutorial videos for the Setup page (Build room ticket, 22 Nov) and the Resmara setup session in Calendly.

## The new agent's path (decided 22 Nov)

1. **Sign up** (Engine 1), with the brand investigation running during it (Engine 2).
2. **Finish pop-up** (first step of the sign-up tour): their brand and Facebook status, information only, one button: **Show me
   around**. Anything wrong is logged on Accounts or My Brand.
3. **Sign-up tour:** anything that needs fixing first, then where everything is, ending on
   **Let's start your first campaign**.
4. **First campaign:** see Engine 4 below.

## Decided for later engines (carry into their brains)

- **Engine 4 · Campaign build:**
  - On + Campaign, check the brand kit has phone, license and brokerage, and ask for anything
    missing right in the flow (saved to My Brand).
  - **Build first, then pay to unlock** (Adam, 22 Nov): link and photo permission, Resmara builds
    the whole campaign, then shows it blurred with "Pay $49 to unlock it" and a "Save this card for
    future campaigns" tick box (on by default). With a saved card, later campaigns are charged when
    the build finishes. Today PR #17's billing takes the card before building; the server needs to
    build unpaid campaigns and lock them instead. No card at sign-up.
  - Every payment uses Stripe's card form embedded in the pop-up, never a separate Stripe page.
  - One locked (built, unpaid) campaign per account at a time.
  - If a saved card is declined: nothing is charged, the campaign stays locked, and it says "Your payment
    didn't go through. Please check your card and try again," with Try again and Use another card.
  - Write design guidelines for each look (Modern, Classic, Rustic; Match my brand is the default).
  - The post writer reads the agent's Voice of the client.
- **Engine 5 · Website (and the campaign page):** a shareable link to the listing's website
  page, shown on the campaign with a **Copy link** button (Adam, 22 Nov). Agents who post it
  themselves (download mode, no business Page connected yet) paste it into their posts, so leads
  still land on the Resmara page. Not in the front end yet: download mode copies the caption only.
- **Sign-up tour:** "Do it with our team" books a **Resmara setup session** in Calendly (not the
  Real Estate Boost onboarding session it points to today). The event isn't made yet: a team member
  who knows Meta, on a screen share with a Meet or Zoom link added by Calendly.
- **Phase 2 (after launch):** a brokerage solution. For now there are no teams or brokerage
  accounts: one agent per account, and a brokerage that wants to pay reimburses the agent
  (Adam, 22 Nov).
- **Engine 8 · Run it until it sells:** every 2 weeks while it's on, charge $39, build a fresh 14
  days from the last round's results, ready to review 3 days before, go live on its own, stop on
  pending or sold. If the $39 is declined, the next round doesn't start, the agent gets an email
  and a notice on the campaign with Update card, and it retries once the card works.

## Planned: Engine 9 · Email campaigns and the Marketing overview (Adam, 22 Nov)

**Two new pages in the Team room's Business menu**, next to Growth, Marketing and Website:

1. **Email campaigns** (everything email lives here, not on Accounts):
   - **Export emails:** one button that downloads every client's email as a CSV. Test and closed
     accounts left out, unsubscribes marked.
   - **Mailchimp connected**, so its campaigns report here.
   - **Tracks:** new client onboarding emails (welcome, day 3, 7, 14: sent and opened), nurture
     emails every two weeks for current clients, and acquisition emails to agents who haven't
     signed up.
2. **Digital ads:** Resmara's own ad spend and how it's performing.

**Marketing becomes the overview:** Email campaigns, Digital ads and Website all report into it.

**Marketing consent:** one line at sign-up ("Resmara will send you tips and updates now and then.
Unsubscribe any time."), an on/off setting on each account, and an unsubscribe link in every
marketing email.

## Other PRs (not engines)

- #17: the whole front end (merged 22 Nov).
- #19, #20: Dan's auto-merge watcher tests.
- #21: Clarity screen tracking, a heat map per screen (merged 22 Nov).
