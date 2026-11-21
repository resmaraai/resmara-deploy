# Resmara engine tracker

**Keep this table.** It's the master list of the engines on the agent's path: what each one
runs on, the AI it uses, and whether it's ready. Update a row when an engine changes. Each engine
also has a Build room ticket in the Team room (opened 21 Nov 2026, assigned to Adam).

**Started:** 21 Nov 2026 · **Focus:** infrastructure first (solid, AI-driven engines); design is
the face on top.

| # | Step | Engine | AI used | Ready? | Build room ticket |
|---|------|--------|---------|--------|-------------------|
| 1 | Sign up and connect Meta | **Login and Meta integration** | None needed: facts come straight from Meta. AI only explains unusual errors | **Partly.** Screens done. Server bug: nothing is saved without an ad account, and reconnecting doesn't update the Page or Instagram | Engine: Login and Meta integration |
| 2 | Build their brand | **Brand** | Should study their Instagram, website and brokerage | **No.** Only a basic version exists; the onboarding step is an animation | Engine: Brand |
| 3 | Paste the listing link | **Listing link** | Should read the page and research the home by address | **Partly.** Opening the link, finding photos and catching sold or pending listings work. No AI read of the page; research only runs after payment | Engine: Listing link |
| 4 | Pick the 14 photos | **Photo selection** (Campaign engine) | Vision AI scores every photo and rules out clutter, dark shots, bathrooms and mess | **Yes** | Engine: Campaign build |
| 5 | Write the posts | **Post planner** (Campaign engine) | AI writes the story, headlines and captions, with compliance rules | **Yes** | Engine: Campaign build |
| 6 | Design the posts | **Post design** (Campaign engine) | An image AI draws each post; a checker re-reads the text | **Partly.** One fixed layout for everyone; the style research never reaches this step; Modern, Classic and Rustic aren't built | Engine: Campaign build |
| 7 | The ad | **Ad** | Copy comes from the plan | Yes | Engine: Active campaign |
| 8 | The home's website | **Website** | Should write the page, sort and qualify leads, and summarise results | **Partly.** Page design and preview built; no server: no public page, no lead capture, no tracking | Engine: Website |
| 9 | Publish, watch the listing, leads, reports | **Active campaign** | AI flags buyer comments as leads and learns from results | **Mostly yes.** It won't post without an ad account | Engine: Active campaign |
| 10 | Resmara's own marketing (Team room) | **Marketing** | Should be a weekly AI analyst: what's working, what's wasting money, budget moves, the next ad to test, alerts on sudden changes | **No.** The Marketing and Website pages exist but read nothing: Resmara's Meta ad account, GA4 and Clarity aren't connected, and Google Ads isn't supported | Engine 7 · Marketing |
| 11 | Keep a listing marketed until it sells | **Run it until it sells** | Should read the last round's results to plan the next round (what reached people and got clicks), and watch the listing for pending or sold | **No (logged 21 Nov, not started).** The switch and the "How it works" pop-up are built on the campaign page. Nothing runs the renewals yet: no automatic $39 charge, no rebuild of a fresh 14 days, no automatic go-live, no stop on pending or sold | Engine 8 · Run it until it sells |

## Build order (one engine per deployment)

| PR | What |
|----|------|
| #17 | The whole front end: look, feel, pop-ups and workflow, including the new campaign page. Deploy first. |
| #18 | Engine 1 · Login and Meta integration. Built as far as possible; the last piece plugs in once the Meta app review is approved |
| #19 | Engine 2 · Brand |
| #20 | Engine 3 · Listing link |
| then | Engine 4 · Campaign build, Engine 5 · Website, Engine 6 · Active campaign, Engine 7 · Marketing, Engine 8 · Run it until it sells, each its own PR |

PR numbers can shift if other pull requests land in between. The Build room ticket titles say
which is which.

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
