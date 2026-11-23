# Engine 6 brain: Active campaign

**Status:** greenlit by Adam (22 Nov) · **Builds in:** PR #28 · **Started:** 22 Nov 2026
**Existing specs:** `engine-specs/resmara-ad-engine-spec.md` (v1.3: launch, pause, listing watcher, ad results), `engine-specs/resmara-post-engine-spec.md` (publishing, leads, reports), `claude/dan-deploy-package.md`. This brain sets the direction; where they differ, this brain wins.

---

## 1. Job

Run the campaign from **Approve and launch** to the end of the 14 days (or until the house goes
pending or sold): post every post, run the ad and keep it healthy, catch every lead and put it in
front of the agent, and report the results to the agent and, through the agent, to the seller.

**Starts:** the agent clicks Approve and launch (everything Engine 4 built is approved and locked).
**Ends:** day 14 (or pending, sold, or paused by the agent). Run it until it sells is Engine 8.

**The agent shouldn't have to do anything while it runs** except answer their leads. Resmara only
asks them for something when it truly needs them (a broken Meta connection, a payment problem on
their ad account).

## 2. What already exists (keep it)

| Piece | Code | What it does |
|---|---|---|
| Launch gate | `launch.py` | Checks the ad account can spend and everything is approved, then creates campaign, ad set and ad |
| Publisher | `publisher.py` | Posts approved posts when due; never posts anything unapproved; claims a post before sending so it never posts twice |
| Failed posts | `post_retry.py` | Our fault → retry; the agent's Meta connection broke → email them and repost by itself on reconnect; Meta rejected it → say so |
| Connection health | `token_health.py` | Warns before the agent's Meta connection expires (~60 days) or if their ad account has no payment method |
| Comment leads | `leads.py` | Reads comments on the posts and the ad every 15 minutes, judges buying interest, emails the agent |
| Website leads | Engine 5 | Form, call and text leads from the listing website |
| Lead totals | `lead_counts.py` | Counts every lead by source; removing one from the list never lowers the count |
| Listing watcher | `listing_watch.py` | Reads the agent's link every 6 hours and word-matches it; pauses the ad on Sold or a removed page (not on Pending, not the posts, no email). Rebuilt in section 7 |
| Real numbers | `insights.py` | Meta's numbers for the posts and the ad; never invents a number |
| Reports | `report.js`, `report_pdf.py` | Day 7 and day 14, PDF download |
| Learning | `round_learning.py` | This campaign's results feed the next round |

## 3. Launch (go-live day)

- **Approve and launch** locks the campaign. The card shows **Ready to go live** until the go-live
  date, then **Active · Day N of 14**.
- **The ad** is created and submitted for Meta's review ahead of the go-live date (review can take up
  to a day), with everything Engine 4 fixed in code: Housing category, 15-mile radius, lifetime
  budget, start 8:00 AM on the go-live date, **no delivery 11 PM to 6 AM**, runs as the agent's Page
  and Instagram, clicks to the listing website with tracking tags.
- **The posts** go out one a day at the agent's best audience time, between 6 AM and 11 PM (Engine 4).
- **If the ad can't run** (no payment method, account disabled, connection broken): the posts still
  go out, the ad waits, and the agent gets one email with one fix. Checked again before every launch
  by `token_health.py`.

## 4. Posting

As `publisher.py` and `post_retry.py` do today, plus:
- Facebook gets the caption with the website link; Instagram gets the caption with **no link**
  (Engine 4, 9c).
- Hashtags at the end of the caption, within each platform's limits (Engine 4, 9f).
- A post that fails and can't be retried shows **Couldn't post** on the calendar with the reason in
  plain words; the team is alerted when it's our fault.
- **Withdraw post:** on the live calendar, any post that hasn't gone out yet can be withdrawn.

## 5. The live ad audit (Adam, 22 Nov)

Resmara checks the ad **several times a day** to make sure it's running right, and fixes what it can
on its own. It never changes the budget, the targeting or the dates the agent approved.

**What it checks:**
- **Approved and delivering:** Meta approved it, and it's actually getting shown (impressions are
  rising during ad hours).
- **Rejected or limited by Meta:** read Meta's reason, fix the creative or text against the platform
  rulebook (Engine 4, 9b), resubmit once automatically, and add the lesson to the rulebook. If it's
  still rejected, the team is alerted and the agent is told only what they need to know.
- **Spending on pace:** the lifetime budget is on track to be spent evenly over the 14 days, not
  stuck at zero or burning out early.
- **The hooks:** once each hook has had a fair amount of showing (about 1,000 impressions), a hook
  getting far fewer clicks than the others is paused and replaced with a fresh hook for this home
  from the hook library, still true to the house and checked against the rulebook. Never more than
  one swap a day, and never in the last 2 days.
- **Frequency:** if the same people are seeing the ad too often (more than about 4 times each), a new
  hook is rotated in so it doesn't go stale.
- **The website is up** and the ad's link works.
- **The Meta connection and payment method** are still healthy.

**Who hears about it:** the agent only hears when they need to do something. Everything else goes
in the **ad audit log**, which shows in the agent's report ("Day 3: hook 3 had few clicks, replaced
with a new hook"), and anything we couldn't fix alerts the team.

## 6. Leads (Adam, 22 Nov)

- **Comments:** every 15 minutes, read the comments on the posts and the ad (Facebook and Instagram).
  The AI judges each new comment for buying interest ("Is this still available?", "TOUR", "Can I see
  it Saturday?"). A likely buyer becomes a lead.
- **No automatic replies or messages.** Resmara never answers the commenter. It puts the lead on the
  agent's board (section 1, Campaign leads) and emails the agent: "You have a new comment that looks
  like an interested buyer", with the comment, the post it's on and a link to answer it.
- **Website leads** (Engine 5): form leads are emailed; call and text leads are listed.
- **Email only. No text messages (SMS)** to the agent: too complicated for now.
- Every lead shows on the board with where it came from: the ad, a post, the website form, a call or
  a text. The agent can mark it contacted, add a note or remove it.

## 7. Pending and sold: stop marketing right away (Adam, 22 Nov)

**The rule:** the moment a listing goes **pending** (or contingent, or sold), the agent has to stop
promoting and marketing it. So Resmara **pauses right away**, then tells the agent. It never waits
for the agent to confirm.

**How Resmara knows (replaces today's word-matching):**
1. **Read the status field, not the words on the page.** The big listing sites put a status field in
   the data behind every listing page (for example `homeStatus: PENDING`). Engine 3 already reads that
   hidden data for photos. Resmara checks it on the agent's own link and on the same home on Zillow,
   Redfin, Realtor.com and Trulia (which Engine 3 finds and saves on the home's file).
2. **Act on a clear signal:** a clear status field on any one source, or two sources agreeing. Words
   elsewhere on a page ("Recently sold nearby", "Similar homes · Pending", filter menus) never count.
3. **Never act on a guess:** a page that can't be read, sources that disagree, or a photographer's
   page (Aryeo, Fotello, Dropbox) that has been taken down are **not** a sale. Resmara keeps checking
   and, if it can't read any source for a day, tells the team.
4. **The agent can tell us (kept as the fail-safe, Adam 22 Nov):** the campaign card's **Pause**
   pop-up has **Just pause it**, **It's pending**, **It sold** and **Keep running**. The listing sites
   can lag a day or more behind the MLS, and sometimes no source can be read, so this lets the agent
   stop marketing immediately. It pauses everything the same way.
5. **How often:** **every hour** (today it's every 6 hours), so a pending home stops within the hour.
   This runs on Render's scheduled jobs (see "The clock" below; decided with Adam, 22 Nov).
6. **The agent's own posts (Adam, 22 Nov).** Agents often announce first on their own socials. Once a
   day Resmara reads the new posts on the agent's **business Facebook Page and Instagram** (through
   their Meta connection) and the AI looks for posts about **this home** (its address or street, its
   own photos or the listing link): "Under contract!" or "Just sold!" pauses everything the same way;
   "Price improved" takes the price off the website (Engine 5, section 3a). It must quote the post it
   found; a post about another home never counts. Personal profiles can't be read.
7. **Later iteration (not now):** an MLS feed gives the true status straight from the source.

**Self-healing: how it finds the status when the usual way fails (Adam, 22 Nov).** The check
tries each layer in order and stops at the first clear answer:
1. **The known spot:** the status field where each site normally keeps it. Fast and exact.
2. **The standard spot:** the standard listing description most sites publish for search engines
   (schema.org data), if the known spot has moved.
3. **The AI reads the page, only when the faster ways fail:** it finds the status the way a person
   would ("Pending" by the price, "Under contract" in the status line) and the listing agent. It must
   **quote the exact words it found**; lists like "Recently sold nearby" or "Similar homes" never
   count. No clear line → "unknown", never a guess.
4. **Another source:** if a site blocks the visit or can't be read, try the same home on the other
   sources Engine 3 saved (Zillow, Redfin, Realtor.com, Trulia, the agent's own link).
5. **It notices patterns:** if the known spot stops working on one site for every listing, that site
   changed its layout; the team is alerted to fix the fast way, while layers 2 to 4 keep the checks
   running.

The rule doesn't change: act on a clear Pending or Sold, never on a guess. The listing agent is read
the same way (section on falling through).


**What happens the moment it's pending or sold, all at once:**
- **The ad is paused** in Meta (campaign, ad set and ad).
- **Every post that hasn't gone out is paused** (today the watcher only pauses the ad, and the
  publisher keeps posting; this must be fixed). Posts already published stay on the agent's page.
- **The website stops marketing the home:** a **Pending** (or **Sold**) banner at the top; **Schedule
  a showing** becomes **Ask about similar homes**, and the form and the agent's contact details stay,
  so late visitors still reach the agent (Engine 5).
- **Run it until it sells stops** (Engine 8): no more rounds, no more charges.
- **On Pending, the agent gets an email straight away:** "Your listing shows Pending, so we paused your
  ad, your posts and your website's showing requests. Fell through? Turn it back on anytime." with a
  **Turn it back on** button. Today the watcher sends nothing; this must be added. **On Sold, no
  email:** the campaign just updates to Sold.
- The campaign card shows **Paused · Pending** (or **Sold**), and it's in the reports and the audit log.

**Pending and Sold are two different states, always shown clearly (Adam, 22 Nov):**

| | Pending (or contingent) | Sold |
|---|---|---|
| What it means | Under contract; it **can still fall through** | Closed; final |
| Campaign card | **Paused · Pending** | **Completed · Sold** |
| Website | "This home is under contract" banner | "This home has sold" banner |
| Agent's email | "…shows Pending, so we paused everything. Fell through? Turn it back on." | **None** (Adam, 22 Nov): the campaign simply updates to Sold and stays marked Sold |
| Keeps checking the listing? | **Yes, every hour** | No |
| Can it be turned back on? | Yes | No (a new listing is a new campaign) |

Resmara never mixes the two: a pending home is never called sold, and if a source says pending
while another says sold, it shows **Pending** until a clear Sold status appears.

**How we know it fell through:**
1. **Resmara keeps checking paused pending listings every hour** (today the watcher skips paused
   campaigns entirely; this must change). If a clear status field shows the home **back to For Sale
   / Active** (or two sources agree), Resmara emails the agent: "Your listing shows For Sale again.
   Want to turn your campaign back on?" with **Turn it back on**. It does **not** restart on its own:
   the agent confirms, because it starts spending their ad budget again.
2. **The agent can always tell us:** **Turn it back on** on the campaign card (the Resume button).
3. Turning it back on resumes the ad and the remaining posts, gives back the paused days (section 8),
   removes the website's banner and brings back Schedule a showing. If Resmara still reads the listing
   as pending at that moment, it asks the agent to confirm first ("Your listing still shows Pending.
   Turn it back on anyway?").
4. **Only if it's still this agent's listing (Adam, 22 Nov).** Before suggesting anything, Resmara
   checks the listing agent shown on the listing (name, license number or brokerage, read from the
   same status data) matches this Resmara agent. If another agent now has the listing, or it can't
   confirm it's the same agent, Resmara does nothing: an agent who lost the listing must never be
   prompted to market it again.
5. **If it's still pending when the 14 days would have ended,** the campaign closes as
   **Completed · Pending**. For 30 days Resmara keeps watching, and only if it comes back on the market
   **with the same agent** does that agent get the email above, with a fresh-campaign offer (Engine 8).
   Nothing ever restarts on its own.

**The clock that runs all of this:** today posting, comment leads and the listing check are run by a
timer on a Mac Mini, because Render's free plan has no scheduled jobs. If that computer sleeps or goes
offline, nothing posts and nothing is checked. **Move the timer onto Render** (a paid plan includes
scheduled jobs) before launch.

## 8. Pause and Resume

On the campaign card: **Pause** stops the ad and the remaining posts (nothing is deleted).
**Resume** inside the 14 days gives back the paused days: the ad's end date moves out and the
remaining posts reschedule from today. After the 14 days, it offers a fresh campaign (Engine 8).

## 9. Reports (Adam, 22 Nov)

Two versions on **day 7** and **day 14**, in section 4 of the campaign page, and emailed to the agent
when they're ready:

**The agent report (full):**
- Everything in the seller version, plus:
- **The ad:** spend so far, cost per click, clicks, click rate, reach, frequency, and each hook side by
  side (which one won).
- **Leads by source:** ad comments, post comments, website form, calls, texts.
- **Website:** visits, and which post or ad sent them.
- **Every post:** reach, views, likes, comments, shares, saves, clicks.
- **The ad audit log:** what Resmara checked and changed.
- **Recommendations for the agent** (what to do next, who to follow up with).

**The seller version (client-ready):** what exists today: reach, views, engagements, clicks to the
listing, top posts, daily activity, and Resmara's summary. **No cost, no spend, no cost per click
anywhere.** In the agent's brand ("Prepared by Morgan Ellis, Morgan & Co."). Downloadable as a PDF
from the agent report with one button, for the agent to send to their seller themselves.

Numbers come from Meta only; anything Meta hasn't returned shows as a dash, never a guess.

## 10. When it ends

Day 14: the final reports, the campaign card shows **Completed**, and the website stays up 30 days
(Engine 5). Results are saved for the next round (Engine 8) and for the hook library and the agent's
style profile (Engine 4).

## 11. Decided with Adam (22 Nov 2026)

- No automatic replies to commenters: comment leads go on the agent's board with an email alert.
- Email only to the agent; no SMS.
- Resmara audits the ad live and fixes what it can on its own.
- Two reports: the agent's full report, and a client version with no cost or spend that the agent
  downloads and sends.
- Pending or sold pauses everything right away (ad, posts, the website's showing requests, Run it
  until it sells) and then emails the agent: legally they must stop marketing it once it's pending.
- The listing check reads the listing's status field across sources, every hour, and never acts on a
  guess; the agent can also mark it pending or sold.
- Pending and Sold are separate, always shown clearly; Sold closes the campaign, Pending can come back.
- A fell-through deal: Resmara keeps checking paused pending listings (today it skips paused campaigns;
  fix that) and emails the agent when it's back on the market **with the same listing agent**; the
  agent turns it back on (never automatic).
- No email when it sells: the campaign just updates to Sold.
- The status check heals itself: known spot, then the standard spot, then the AI (only when the faster
  ways fail, quoting what it found), then another source; layout changes alert the team.
- The Pause pop-up keeps It's pending and It sold as the agent's fail-safe.
- Move the scheduler (posting, leads, listing checks) from the Mac Mini onto Render's scheduled jobs.
- MLS feed: a later iteration.
- The agent's own business Page and Instagram are read daily for pending, sold and price-change posts about this home.

## Screens

Mockups from the preview (`engine-6-screens/`, with `mockup.js`, the preview script they were taken
from). Mockups only: the brain above is what to build.

| Screen | What it shows |
|---|---|
| `01-agent-report-top.png` | The day 7 report: Your report / Seller version, Download seller version (PDF), the ad's numbers (for the agent only), the hooks |
| `02-agent-report-hooks-leads.png` | Leads by source and where website visits came from |
| `03-agent-report-posts.png` | Every post's numbers |
| `04-agent-report-audit.png` | The ad audit log and "What to do next" |
| `05-seller-version.png` | The seller version: no cost or spend anywhere |
| `06-pause-popup.png` | Pause: Just pause it, It's pending, It sold, Keep running |
| `07-card-paused-pending.png` | The card after It's pending: Paused · Pending, Resume still there |
| `08-website-pending.png` | The website once pending: banner, status chip, Ask about similar homes |
| `09-card-sold.png` | The card after Sold: Completed · Sold, no Resume |

Live preview: https://claude.ai/artifact/Lip2AN9HQZuLf4J5AsP8Vy#website (Reports) and `#pending`.

**Also in this PR:** an Engine 5 change that arrived after PR #27 merged: the website stops marketing
the home once it's pending or sold (`engine-5-brain.md`, section 5).
