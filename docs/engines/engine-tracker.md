# Resmara engine tracker

The engines, their brains and their stage. Each engine has one Build room task in the Team room. **Started:** 21 Nov 2026 · **Last updated:** 25 Nov 2026

**Stages now live in the Build room** (one task per engine; the five stages are defined in
`docs/engines/README.md`). This list is the engines and their brains. As of 23 Nov 2026 every engine
was at **1. Planned**: the PRs below were plans with no app code. Slice 1 is now built in PR #39
(Ready for Dan), slice 2 in #40 and slice 3 in #41. Engine 1 Part A and Engine 9 were built by Dan on 23 Nov. #39, #40 and #41 are merged and live. On 25 Nov every brain was checked line by line against the live code; the gaps found are built in the brain-gaps PR (see `implementation-status.md`).

| Engine | Build room task | Brain (plan PR) | Stage |
|--------|-----------------|-----------------|-------|
| Sign-up & Facebook connection (Engine 1) | #26 | `engine-1-brain.md` (#18) | 5. Live (#39) · gaps in the brain-gaps PR |
| Brand kit (Engine 2) | #27 | `engine-2-brain.md` (#22) | 5. Live (#39) · gaps in the brain-gaps PR |
| Sign-up tour | #83 | `resmara-signup-tour-engine.md` (#23) | 5. Live (#39) |
| Listing link check (Engine 3) | #28 | `engine-3-brain.md` (#24) | 5. Live (#39) · gaps in the brain-gaps PR |
| Campaign build & pay to unlock (Engine 4) | #29 | `engine-4-brain.md` (#26) | 5. Live (#39) · gaps in the brain-gaps PR |
| Listing website (Engine 5) | #30 | `engine-5-brain.md` (#27, #28) | 5. Live (#40) |
| Live campaign: posting, ads, leads & reports (Engine 6) | #31 | `engine-6-brain.md` (#28) | 5. Live (#40) · gaps in the brain-gaps PR |
| Run it until it sells (Engine 8) | #33 | `engine-8-brain.md` (#29) | 5. Live (#40) · gaps in the brain-gaps PR |
| Marketing pages in the Team room (Engine 9) | #84 | `engine-9-brain.md` (#31) | Built by Dan (waiting on credentials) · gaps in the brain-gaps PR |
| Billing (Engine 10) | #85 | `engine-10-brain.md` (#35) | 5. Live (#41) |
| Support & Ask Resmara (Engine 11) | #86 | `engine-11-brain.md` (#36) | 5. Live (#41) · gaps in the brain-gaps PR |

(Engine 7 was folded into Engine 9.)

**Build order: three slices, all needed for launch.**
1. **Sign-up to first campaign:** Engines 1, 2, the sign-up tour, 3 and 4.
2. **The live campaign:** Engines 5, 6 and 8.
3. **The business side:** Engines 10, 11 and 9.

PR numbers are filled in only once the PR is opened, never planned ahead (Adam, 22 Nov).

> **A merged PR is not a built engine.** Step 3 sends the design to Dan; the engine exists only
> when `app/` or `static/` changed and its page answers in the Team room. Engine 9 went out as a
> docs-only PR on 22 Nov and was read as delivered; it was built on 23 Nov. Before a row is
> treated as live, check that the code moved - `git show --stat <merge>` listing only `docs/` is
> the tell.

## Client journey map

Every screen and branch from the website to the first live campaign, with screenshots:
https://claude.ai/artifact/X8J4hm7tRAdokpEUYsv4Kb (22 Nov). Its screenshots also go into the repo with
the sign-up tour PR, under `docs/journey/`.

## Up next

1. **Slice 2** (Engines 5, 6, 8): built, Ready for Dan in #40 (stacked on #39; audit in `slice-2-audit.md`).
2. **Slice 3** (Engines 10, 11; 9 built by Dan): built, Ready for Dan in #41 (stacked on #40; audit in `slice-3-audit.md`).
3. Not engines: the Resmara setup session in Calendly, the support@resmara.com inbox, and turning on Stripe Tax (Adam). The AI tutorial videos are done (PRs #25 and #30).
4. Later: the growth plan engine (Founding Agents, coach codes).

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
  - Looks (Modern, Classic, Rustic, Match my brand) are dropped: post styles instead (Engine 4 brain, section 4).
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

## Engine 9 · Marketing (Adam, 22 Nov)

Written up in full in `engines/engine-9-brain.md` (Marketing as the parent page, Website, Email
campaigns and Digital ads under it, how each number is counted).

## Other PRs (not engines)

- #17: the whole front end (merged 22 Nov).
- #19, #20: Dan's auto-merge watcher tests.
- #21: Clarity screen tracking, a heat map per screen (merged 22 Nov).
