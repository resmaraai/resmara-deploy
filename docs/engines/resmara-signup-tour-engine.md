# Resmara sign-up tour engine brain

**Status:** written and greenlit with Adam, sent to Dan 22 Nov · **Builds in:** PR #23 · **Started:** 22 Nov 2026
**Client journey map:** every screen and branch from the website to the first live campaign,
with screenshots: https://claude.ai/artifact/X8J4hm7tRAdokpEUYsv4Kb (a copy is in the repo at
`docs/journey/index.html`). **Clickable mockup:** `signup-tour-screens/mockup.js` (preview only, not
for deploy).

This PR also carries **changes to Engine 1** (Facebook-only log-in, no teams) and to **billing**
(build first, pay to unlock, Stripe's form embedded). They're listed in section 9.

---

## 1. Job

Take a new agent from **Show me around** to their **first campaign**, quickly, without them ever
feeling lost. Keep the excitement, keep it simple, and don't lose anyone at onboarding. The
Resmara robot is the guide the whole way.

**Starts:** the moment sign-up finishes (Engine 1's checks and Engine 2's brand build are done).
**Ends:** they pay for and unlock their first campaign.

**Principle:** nothing blocks them except having no Facebook account. Anything that needs setting
up is offered first, with help, but they can always carry on.

## 2. The path

1. **The finish pop-up** (replaces PR #18's "Here's what we found" screen).
2. **The tour, first stop:** anything that needs fixing, with **Walk me through it** (the setup plan)
   or **Do it with our team**.
3. **The tour, a quick look around:** the Campaign button, campaigns, My Brand, Billing, Accounts,
   Support.
4. **The tour ends:** "Let's start your first campaign."
5. **The first campaign:** listing link and photo permission, Resmara builds everything, then the
   campaign opens blurred with **Pay to unlock**.

## 3. The finish pop-up

Information only. Their brand and their Facebook status, and one button.

- **"You're all set up, Jamie."** "Here's your brand and your Facebook. Let me show you around. It
  takes about a minute."
- **Your brand:** logo, name, fonts, colours, license number (or "License number not found yet"),
  and the first lines of their Voice of the client.
- **Your Facebook:** Facebook Page, Instagram, Ad account. Each says **✓ Connected / ✓ Ready** or,
  in light blue, **Not set up yet / No card on it** (never orange here: nothing to fix on this screen).
- **One button: Show me around.** The pop-up stays until they press it.
- Anything that isn't set up is logged on its page: **Accounts** (Facebook) or **My Brand** (a
  missing license). A missing card is never flagged: the card comes at the first campaign.

## 4. The tour

Built on PR #17's tour (`TOUR`, `workspaceTour`), with new steps and words.

### 4a. First stop: anything that needs fixing

Only when something needs it. The robot opens on that page, and the menu item gets an orange mark.

| Situation | Where | What the robot says |
|-----------|-------|---------------------|
| Personal Facebook and Instagram only | Accounts | "First, let's get you set up for business. Like most agents, you're starting with a personal Facebook and Instagram. To post and run ads for you, I need a business Page and a business Instagram. About 10 minutes, and I'll walk you through it." |
| No Instagram at all | Accounts | "You're starting with a personal Facebook and no Instagram yet…" (same ending) |
| Page, but Instagram is personal / no Page / no ad account / ad account has no card | Accounts | "First, let's sort out your Facebook. Before your first campaign: [the reason]. It's quick, and I'll walk you through it." |
| License number missing | My Brand | "One thing is missing from your brand. We couldn't find your license number. It has to go on every post. Add it now, or when you start your first campaign." |
| Nothing to fix | | Skips straight to the look around |

Buttons: **Walk me through it** (or **Add it now** for the license) · **Do it with our team** ·
**Next** (leave it for later; it waits on Accounts) · **Skip tour**.

### 4b. The setup plan (Walk me through it)

**One pop-up for the whole job, not one per step.** It shows all three things up front:

1. **Facebook business Page** (about 5 minutes)
2. **Instagram business account, linked to your Page** (about 2 minutes). With no Instagram at all
   it's "Create your Instagram business account" instead of "switch".
3. **Ad account with a card** (about 3 minutes. Posts go out without it; it runs the listing ad.)
   If the ad account exists but has no card, the step is "add a payment method".

- Header: "Getting you set up for business · 3 things left · about 10 minutes". Anything they
  already have shows ticked ("Already set up").
- **The open item** has one line on why, numbered steps with a link to the exact Meta page, and
  three buttons: **Do it with our team** · **See the tutorial** · **Check again**.
- **Check again** asks Meta right then (Engine 1's checks). Pass: the item ticks in place ("Done
  just now") and the next one opens. Not yet: "Not quite yet. Meta still shows the same thing.
  Sometimes it takes a few minutes to update." inside the item, with **Try again**.
- **One celebration at the end:** "You're set up for business, Jamie. I can post to your Page and
  Instagram and run your listing ads now." with **Continue the tour** (or **Add my license number**
  if that's still missing).
- **Later** at the bottom: back to the tour where it left off. Stopping halfway is fine: ticks stay,
  the rest waits on Accounts.
- **The license number** is its own small pop-up: typed and saved right there ("Saved. It's on
  every post now.").

### 4c. See the tutorial

Opens that item's guide on the site's existing **Setup** page (`setupGuides`), in a new tab, so
the setup plan stays where it is. Each guide gets a **short explainer video** at the top, above the
written steps.

**The videos are AI-generated, never filmed by a person** (Adam, 22 Nov): mock-ups of the current
Facebook and Instagram screens, a whiteboard-style walkthrough and a voiceover, about a minute
each. Still to make: create a Facebook account, create the business Page, full control of the
Page, switch or create a business Instagram, link Instagram to the Page, the ad account with a
card. They need refreshing when Meta changes its screens.

### 4d. Do it with our team

Books a **Resmara setup session** in Calendly: a 30-minute screen share with a team member who
knows Meta (Calendly adds the Meet or Zoom link). **Continue the tour** brings them back.
*The Calendly event isn't made yet; today the button points to the Real Estate Boost onboarding
session (`SETUP_CALENDLY`), which must change.*

### 4e. The look around and the end

Short stops with **Back** and **Next**: the Campaign button ("All you need is your listing link"),
your campaigns, My Brand ("the brand we built for you… you can change it any time"), Billing ("You
don't need a card yet: you'll add one when you pay for your first campaign"), Accounts, Support.

**The last stop:** "Let's start your first campaign. All you need is your listing link." with
**Let's start your first campaign** (opens + Campaign) and **Maybe later**.

## 5. The first campaign: build first, then pay to unlock

1. **+ Campaign** as today: MLS public listing link and the photo permission tick. **No card here.**
2. **Resmara builds the whole campaign** with a live checklist: reading the listing, picking the
   best 14 photos, writing 14 days of posts in their voice, designing them, building the ad and
   the listing page.
3. **The campaign opens blurred**, with one card on top:
   - "905 Laurel Bend is built. Your 14 days of posts, your ad and your listing page are all here.
     Pay $49 to unlock it, then review and launch."
   - **Stripe's card form, embedded in the card** (card fields, Apple Pay, Google Pay).
   - **Save this card for future campaigns**, ticked by default: "Skip this step next time: your
     next campaign unlocks as soon as it's built."
   - **Unlock my campaign for $49** · **Later**.
4. **Paid:** the blur lifts and they review and launch as today (PR #17).
5. **Declined:** "Your payment didn't go through. Please check your card and try again. Nothing was
   charged, and your campaign is saved right here." The form stays, with **Try again**.
6. **Later:** the campaign stays **locked**. On My campaigns its card is blurred, tagged "Built ·
   pay to unlock", status "Locked · Built · waiting for payment · Not live", button **Unlock my
   campaign**. Opening it shows the same pay card. Nothing can be reviewed, edited, downloaded or
   launched, and nothing posts, until it's paid. (The day-3 email already covers this.)
7. **With a saved card:** later campaigns are charged when the build finishes and open unlocked. A
   declined saved card shows the declined card above.

**Guardrail: one locked campaign at a time.** Starting another while one is locked: "Unlock 905
Laurel Bend first. Your campaign for 905 Laurel Bend is built and waiting. Unlock it to start
another, or replace it with a new listing." with **Unlock** and **Replace it**.

## 6. What the AI does

Nothing new. The tour words are fixed; every Facebook fact comes from Engine 1's checks; the build
is the existing Campaign build engine.

## 7. Guardrails

- Nothing blocks them except having no Facebook account. Every setup step has **Later**.
- **Do it with our team** is on every setup step, not hidden as a last resort.
- The finish pop-up never shows a problem list; problems live on their pages.
- No card is asked for before the first campaign is built.
- Nothing posts or launches from a locked campaign.
- Stripe holds every card. Resmara never sees or stores a card number.

## 8. How we'll know it works

- A personal-only agent goes from Show me around through the setup plan to "You're set up for
  business" without leaving the pop-up, and Check again ticks each item when Meta confirms it.
- Each situation in 4a opens on the right page with the right words; nothing to fix skips to the
  look around.
- See the tutorial opens the right guide in a new tab; Do it with our team opens the Resmara setup
  booking; both bring them back to the tour.
- The first campaign builds with no card, opens blurred, and unlocks only after payment, with the
  card saved when the tick is on.
- A second campaign while one is locked shows the one-at-a-time message.
- With a saved card, the next campaign opens already unlocked.

## 9. Changes this PR makes to other engines

### Engine 1 (Login and Meta) · see `engine-1-brain.md`, Part A 10b

- **Facebook is the only way in.** No email and password sign-up. A Facebook account is required;
  a personal one is fine.
- **One door for everyone.** The top-right **Client Login** and the homepage's **Let's get started**
  open the same pop-up: "Log in with Facebook. New or returning, it's the same button. Have an
  account? You're signed straight in. New to Resmara? We set up your account and connect your Page,
  Instagram and ad account in one go." Then **Continue with Facebook** and "No Facebook account?
  You'll need one to use Resmara. It's free: create one on Facebook, then come back here."
- **No teams and no brokerage accounts.** One agent per account. Brokerages that want to pay can
  reimburse the agent; a brokerage solution is phase 2, after launch. A Page already on another
  account: "If that account is yours, log in with the Facebook you used for it. If not, contact us
  and we'll sort it out." with **Contact us** and **Log in with a different Facebook**.
- Once signed in, **+ Campaign** opens the campaign form, never the log-in pop-up.

### Billing (PR #17's `billing.js` and the Stripe checkout)

- **Build first, then pay to unlock** (section 5). Today the server refuses an unpaid build (402)
  and asks for the card first; it needs to build unpaid campaigns and lock them instead, with the
  one-locked-campaign guardrail.
- **Every payment uses Stripe's form embedded in the pop-up** (Stripe Embedded Checkout), never a
  jump to Stripe's hosted page: the unlock card, a declined card, Billing's Add a card, and the $39
  Run it until it sells renewal's Update card. The "Save this card" tick sets Stripe's save-for-later
  option (`payment_intent_data.setup_future_usage`).

## 10. Decided with Adam (22 Nov 2026)

- The finish pop-up is information only, with Show me around; problems live on Accounts or My Brand.
- The tour takes them to anything that needs fixing first, and ends on "Let's start your first campaign".
- One setup plan pop-up for the Page, Instagram and ad account, ticking in place, one celebration.
- See the tutorial on each step; the videos are AI-generated explainers, no human filming.
- Do it with our team books a Resmara setup session (Calendly event to create).
- Facebook account is the gate; one Log in with Facebook pop-up for new and returning clients.
- No teams, no brokerage accounts (brokerages: phase 2).
- Build first, pay to unlock, card saved by default; Stripe's form embedded everywhere.
- One locked campaign at a time.
- Shelved to Engine 5: a shareable link to the listing website with Copy link, for agents posting
  themselves.

## Screens

From the clickable mockup Adam reviewed on 22 Nov. The full set, with every branch, is the journey
map (`../journey/index.html`).

1. **Log in with Facebook (one door)**
   ![Log in with Facebook](../journey/img/s02-login.jpg)
2. **The finish pop-up: personal Facebook and Instagram only**
   ![Finish pop-up](../journey/img/s05-finish-personal.jpg)
3. **Tour, first stop: get set up for business**
   ![Tour first stop](../journey/img/s06-tour-personal.jpg)
4. **The setup plan: the Page open**
   ![Setup plan](../journey/img/s07-plan-page.jpg)
5. **The setup plan: not done yet**
   ![Not quite yet](../journey/img/s07-plan-notyet.jpg)
6. **The setup plan: Page ticked, Instagram open**
   ![Instagram open](../journey/img/s07-plan-ig-switch.jpg)
7. **The setup plan: ad account**
   ![Ad account](../journey/img/s07-plan-ad.jpg)
8. **You're set up for business**
   ![Done](../journey/img/s07-plan-done.jpg)
9. **Do it with our team: the booking pop-up**
   ![Do it with our team](../journey/img/s07-team.jpg)
10. **See the tutorial: the Setup page with a video slot**
    ![Tutorial](../journey/img/s07-tutorial-page.jpg)
11. **The tour ends: Let's start your first campaign**
    ![Tour end](../journey/img/s09-tour-end.jpg)
12. **Building the campaign**
    ![Building](../journey/img/s11-building.jpg)
13. **Pay to unlock, with Stripe's form embedded**
    ![Pay to unlock](../journey/img/s12-gate.jpg)
14. **Card declined**
    ![Declined](../journey/img/s12-declined.jpg)
15. **Later: the locked campaign on My campaigns**
    ![Locked](../journey/img/s12-later-list.jpg)
16. **One locked campaign at a time**
    ![One at a time](../journey/img/s12-one-at-a-time.jpg)
17. **Page already on another Resmara account (Engine 1 change)**
    ![Page taken](../journey/img/s04-taken.jpg)
