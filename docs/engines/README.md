# Resmara engine library

Resmara is built as **separate engines**, one for each stage of an agent's life in the app. Each
engine has one document here. It records what the engine does, the code behind it, the AI it
uses, the data it touches, and the settings you can change. That way any engine can be pulled
out, understood and adjusted without reading the whole app.

## How we know it's done: the five stages (Adam and Dan, 23 Nov 2026)

Every engine is always at exactly one stage. **The Build room is where it's tracked**: one task per
engine, moving down this table, closing only at Live.

| Stage | Means | Done when | Whose | In the Build room |
|---|---|---|---|---|
| **1. Planned** | We know what to build | The brain is written and Adam approved the clickable mockup | Adam and Claude | To do, assigned to Adam |
| **2. Ready for Dan** | The front end is built and Dan has a clear build list | The handoff checklist below is all ticked | Adam and Claude | To do, assigned to Dan |
| **3. Built** | The server side is done | It works on the PR's preview link with real data, not "coming soon" | Dan | Review |
| **4. Tested** | Used start to finish | Adam ran it on the preview with a real account and nothing broke | Adam | Tested ticked |
| **5. Live** | Agents have it | Merged, deployed and checked on resmara.com | Dan merges, Claude checks | Done |

**Ready for Dan, the handoff checklist.** All five must be true:
1. The screens are real code in `static/` (not a mockup) and look exactly like what Adam approved.
2. They run on the PR's preview link; anything still waiting on the server shows a plain "coming soon" state, never a broken page.
3. The PR has **Dan's build list**: every endpoint the screens call, what each sends and gets back, and any new tables or scheduled jobs, in build order. Build from that list; the brain is the background.
4. Adam approved it on the preview link.
5. The help guide (`static/help/resmara-guide.md`) is updated for anything an agent will see.

**PR titles start with the stage:** `Plan:` (brain, screenshots, mockup: no app code, never counts as
progress), `Ready for Dan:`, `Built:` or `Fix:`.

**Note:** the engine PRs up to #36 were plans (brain, screenshots and a preview mockup). They changed
no app code. Every engine is at **1. Planned** as of 23 Nov 2026.

## The engines

| # | Engine | Runs when | Doc | Status |
|---|--------|-----------|-----|--------|
| 1 | **Login** | An agent logs in with Facebook (new or returning) and connects Meta | `login-engine.md`, brain: `engine-1-brain.md` (PR #18) | Written |
| 1b | **Sign-up tour** | From Show me around to the first campaign unlocked: finish pop-up, setup plan, tour, pay to unlock | `resmara-signup-tour-engine.md` | Brain written (22 Nov) |
| 2 | **Brand** | During the new client sign-up, right after the Facebook sign-in; Research again on My Brand | `engine-2-brain.md` | Brain written (22 Nov) |
| 3 | **Listing link** | From + Campaign to the home's file: the link identifies the house, AI researches every source, the gate for the build | `engine-3-brain.md` | Brain written (22 Nov) |
| 4 | **Campaign build** | From the home's file to a built campaign behind pay to unlock: 14 posts, the ad, the calendar | `engine-4-brain.md` (PR #26) | Brain written (22 Nov) |
| 5 | **Website** | Built with every campaign: the home's story-based website in the agent's brand, where the ad and posts send people; Preview, Copy link and Share in section 3 | `engine-5-brain.md` (PR #27) | Brain written (22 Nov) |
| 6 | **Active campaign** | From Approve and launch to the end: posting, the live ad audit, comment and website leads, pending and sold (pauses right away), pause, the agent report and the seller version | `engine-6-brain.md` (PR #28) | Brain written (22 Nov) |
| 8 | **Run it until it sells** | Set it and forget it: a fresh 14 days every 2 weeks for $39 (built, then charged, then live automatically) until it sells; pending pauses it, back on the market picks it up, emails at every turn; Run it again · $39 for everyone else | `engine-8-brain.md` (PR #29) | Brain written (22 Nov) |
| 9 | **Marketing** | Team room: Marketing is the parent page (is each channel paying for itself?), with Website, Email campaigns (Mailchimp) and Digital ads (every campaign and ad) under it; every sign-up stamped with its source, each paying agent counted once | `engine-9-brain.md` (PR #31) | Brain written (22 Nov) |
| 10 | **Billing** | Every money rule in one place: one card (Stripe's form in the pop-up), $49 / $39 prices from the server, Stripe Tax, Coming up and Turn off, receipts, refunds, chargebacks, Close my account stops everything | `engine-10-brain.md` (PR #35) | Brain written (22 Nov) |
| 11 | **Support** | Ask Resmara (AI, says so), the Support page (Which listing?, 1 business day), one shared inbox support@resmara.com, the Team room's Support with reply-by times, the Resmara setup session | `engine-11-brain.md` (PR #36) | Brain written (22 Nov) |
| 7 | **Team room** | Operator console: accounts, releases, system checks | `team-room-engine.md` | To write |

How they hand off:

```
LOGIN ──► BRAND ──► CAMPAIGN ──► ACTIVE CAMPAIGN ──► (renew) ──► CAMPAIGN
  │                    │                │
  └────── BILLING ◄────┴────────────────┘        SUPPORT and TEAM ROOM sit beside all of them
```

Rules for each engine:

- It reads other engines' outputs only through what they store, never by reaching into their
  internals. For example, the Campaign engine reads the brand kit from `users.brand`, not from
  the Brand engine's code.

Related docs:

- **Flow docs** (`docs/flows/`) describe what the agent **sees**.
- **Engine docs** describe what **runs**.
- **Specs** (the Resmara project's `engine-specs/`) are the build plans for what isn't built
  yet.

## The standard layout (every engine doc)

1. **What it does.** One paragraph: where it starts and where it ends.
2. **Status.** Each piece: built, partly built, or not built.
3. **When it runs.** The triggers.
4. **Steps.** The flow, in order.
5. **AI it uses.** For each call: the model, where the prompt lives, what goes in, what comes
   out, and the guardrail.
6. **Code map.** Backend files and functions, endpoints, front-end files and functions.
7. **Data.** The tables and columns it reads and writes.
8. **Outcomes.** Every result and the exact message the agent sees.
9. **Settings you can adjust.** Environment variables and constants, with their current values.
10. **Connections.** What it takes from other engines and what it hands on.
11. **Tests.** What exists and what's missing.
12. **Open work.** What's left, with links to the spec.

**When an engine changes, its doc changes in the same pull request.**
