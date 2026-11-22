# Resmara engine tracker

**Keep this table.** It's the master list of the engines on the agent's path: what each one
runs on, the AI it uses, and whether it's ready. Update a row when an engine changes. Each engine
also has a Build room ticket in the Team room (opened 21 Nov 2026, assigned to Adam).

**Started:** 21 Nov 2026 · **Focus:** infrastructure first (solid, AI-driven engines); design is
the face on top.

| # | Step | Engine | AI used | Ready? | Build room ticket |
|---|------|--------|---------|--------|-------------------|
| 1 | Sign up and connect Meta | **Login and Meta integration** | None needed: facts come straight from Meta. AI only explains unusual errors | **Partly.** Screens done. Server bug: nothing is saved without an ad account, and reconnecting doesn't update the Page or Instagram. Brain and screens in PR #18 (merged 22 Nov; account, Meta connection, audit, setup to-do list) | Engine: Login and Meta integration |
| 2 | Build their brand | **Brand** | Should study their Instagram, website and brokerage | **No.** Only a basic version exists; the onboarding step is an animation. Brain and screens in **PR #22** (22 Nov, sent to Dan; `engines/engine-2-brain.md`): a quick AI investigation during onboarding builds the kit, plus the Resmara onboarding | Engine: Brand |
| 3 | Paste the listing link | **Listing link** | Should read the page and research the home by address | **Partly.** Opening the link, finding photos and catching sold or pending listings work. No AI read of the page; research only runs after payment | Engine: Listing link |
| 4 | Pick the 14 photos | **Photo selection** (Campaign engine) | Vision AI scores every photo and rules out clutter, dark shots, bathrooms and mess | **Yes** | Engine: Campaign build |
| 5 | Write the posts | **Post planner** (Campaign engine) | AI writes the story, headlines and captions, with compliance rules | **Yes** | Engine: Campaign build |
| 6 | Design the posts | **Post design** (Campaign engine) | An image AI draws each post; a checker re-reads the text | **Partly.** One fixed layout for everyone; the style research never reaches this step; Modern, Classic and Rustic aren't built. To add (22 Nov): on + Campaign, check the brand kit has phone, license and brokerage, and ask for anything missing right in the campaign flow (saved to My Brand); the card is asked for here too, at the first campaign, not during onboarding. Also to write: design guidelines for each look (Modern, Classic, Rustic; Match my brand is the default) | Engine: Campaign build |
| 7 | The ad | **Ad** | Copy comes from the plan | Yes | Engine: Active campaign |
| 8 | The home's website | **Website** | Should write the page, sort and qualify leads, and summarise results | **Partly.** Page design and preview built; no server: no public page, no lead capture, no tracking | Engine: Website |
| 9 | Publish, watch the listing, leads, reports | **Active campaign** | AI flags buyer comments as leads and learns from results | **Mostly yes.** It won't post without an ad account. Lead totals per campaign (by ad, posts, listing page) are now kept and never go down. Still missing: what Meta actually spent on each campaign's ad, and an average-leads-per-campaign figure for marketing | Engine: Active campaign |
| 10 | Resmara's own marketing (Team room) | **Marketing** | Should be a weekly AI analyst: what's working, what's wasting money, budget moves, the next ad to test, alerts on sudden changes | **No.** The Marketing and Website pages exist but read nothing: Resmara's Meta ad account, GA4 and Clarity aren't connected, and Google Ads isn't supported. Email campaigns and the marketing overview are planned for the deployment after Engine 2 (see below). (22 Nov: PR #21 gives each agent screen its own Clarity heat map, so the Website page will have per-screen data to read) | Engine 7 · Marketing |
| 11 | Keep a listing marketed until it sells | **Run it until it sells** | Should read the last round's results to plan the next round (what reached people and got clicks), and watch the listing for pending or sold | **No (logged 21 Nov, not started).** The switch and the "How it works" pop-up are built on the campaign page. Nothing runs the renewals yet: no automatic $39 charge, no rebuild of a fresh 14 days, no automatic go-live, no stop on pending or sold | Engine 8 · Run it until it sells |

## Build order (one engine per deployment)

Engines are named **Engine 1–8**. GitHub numbers pull requests itself, so each engine's PR # is
filled in here (and on its Build room ticket) only once that PR is opened. Never plan a number
ahead: Dan's own PRs (tests, fixes) use numbers too. (Decided by Adam, 22 Nov 2026.)

| PR | What |
|----|------|
| #17 | The whole front end: look, feel, pop-ups and workflow, including the new campaign page. **Merged 22 Nov 2026.** |
| #18 | Engine 1 · Login and Meta integration: account, Meta connection, the audit and the setup to-do list. Brain and screens greenlit and sent to Dan 22 Nov, **merged 22 Nov** (`engines/engine-1-brain.md`). Built as far as possible; the last piece plugs in once the Meta app review is approved |
| #19, #20 | Dan's test PRs for his auto-merge watcher (22 Nov). Not engines |
| #21 | Side PR, not an engine: Clarity screen tracking, a heat map and recordings filter per dashboard screen, campaign stage and pop-up (`docs/clarity-screen-tracking.md` in the repo). Opened 22 Nov as a **draft** so the auto-merge watcher doesn't ship it before Dan reviews |
| #22 | Engine 2 · Brand, plus the Resmara onboarding (the robot guide: one onboarding, the tour, problems on the menu, guided fixes; card asked for at the first campaign). Brain and screens sent to Dan 22 Nov (`engines/engine-2-brain.md`). Also changes #18's results screen (noted in the PR) |
| next | **Email campaigns and marketing overview** (Team room), logged 22 Nov, see below. Not part of the Engine 2 deployment |
| then | Engine 3 · Listing link, Engine 4 · Campaign build, Engine 5 · Website, Engine 6 · Active campaign, Engine 7 · Marketing, Engine 8 · Run it until it sells, each its own PR |

## Planned: email campaigns and the marketing overview (Adam, 22 Nov 2026)

The deployment right after Engine 2. Logged now so it stays on the radar.

**Two new pages in the Team room's Business menu**, next to Growth, Marketing and Website:

1. **Email campaigns** (everything email lives here, not on Accounts):
   - **Export emails:** one button that downloads every client's email as a CSV (opens in Excel or
     Sheets, imports into Mailchimp). Test and closed accounts left out, unsubscribes marked.
   - **Mailchimp connected**, so the campaigns run there report here.
   - **What it tracks:**
     - new client onboarding emails: did each new client get all of them (welcome, day 3, 7, 14),
       and did they open them;
     - nurture emails for clients already in: the "how Resmara can transform your business"
       emails every two weeks, who's getting them and how they're doing;
     - new client acquisition emails aimed at agents who haven't signed up yet.
2. **Digital ads:** Resmara's own ad spend and ad efforts, and how they're performing.

**Marketing becomes the overview.** Email campaigns, Digital ads and Website each report into the
Marketing tab, so it shows all three side by side and marketing decisions are made on what's
working.

**Marketing consent** (needed before any marketing email goes out): one line at sign-up ("Resmara
will send you tips and updates now and then. Unsubscribe any time."), a marketing on/off setting on
each account, and an unsubscribe link in every marketing email.

## Engine docs

- Library index and layout: `engines/README.md`.
- Written:
  - `engines/login-engine.md`;
  - specs: Meta Integration, Listing Link, Brand, Post, Ad, Ask Resmara;
  - flows: New user experience, New campaign, Listing page.
- To write:
  - Run it until it sells (what it has to do: every 2 weeks while it's on, charge $39 to the card
    on file, build a fresh 14 days from the last round's results, have it ready to review 3 days
    before it starts, go live on its own, and stop when the listing shows pending or sold)
  - Brand
  - Campaign
  - Website
  - Active campaign
  - Marketing
  - Billing
  - Support
  - Team room
