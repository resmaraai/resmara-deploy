# Resmara engine library

Resmara is built as **separate engines**, one for each stage of an agent's life in the app. Each
engine has one document here. It records what the engine does, the code behind it, the AI it
uses, the data it touches, and the settings you can change. That way any engine can be pulled
out, understood and adjusted without reading the whole app.

## The engines

| # | Engine | Runs when | Doc | Status |
|---|--------|-----------|-----|--------|
| 1 | **Login** | An agent logs in with Facebook (new or returning) and connects Meta | `login-engine.md`, brain: `engine-1-brain.md` (PR #18) | Written |
| 1b | **Sign-up tour** | From Show me around to the first campaign unlocked: finish pop-up, setup plan, tour, pay to unlock | `resmara-signup-tour-engine.md` | Brain written (22 Nov) |
| 2 | **Brand** | During the new client sign-up, right after the Facebook sign-in; Research again on My Brand | `engine-2-brain.md` | Brain written (22 Nov) |
| 3 | **Campaign** | From **+ Campaign** to **Approve and launch**: link check, payment, build, review | `campaign-engine.md` | To write (specs: Listing Link Engine, Post Engine, Ad Engine) |
| 4 | **Active campaign** | From launch to sold or ended: publishing, the ad, the listing watch, leads, reports, Run until sold | `active-campaign-engine.md` | To write |
| 5 | **Billing** | Adding a card, charging a campaign, renewals, refunds | `billing-engine.md` | To write |
| 6 | **Support** | The Ask Resmara help chat, setup calls, emails to the agent | `support-engine.md` | To write (spec: Ask Resmara spec) |
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
