# Engine 5 brain: Website

**Status:** greenlit by Adam (22 Nov) · **Builds in:** PR #27 · **Started:** 22 Nov 2026
**Existing spec:** `flows/listing-page.md` (19 Nov: how the page is served, the slug, links, the lead endpoints, page states). This brain sets the direction; where they differ, this brain wins.

---

## 1. Job

Every campaign gets **a beautiful one-page website for the home**, in the agent's brand, built
automatically with the campaign. It's where the ad and the posts send people, and where interested
buyers ask for a showing or call. The agent gets the link on their dashboard to preview, copy and
share with anyone ("Can I see the home?" → here's the link).

**Starts:** Engine 4 finishes the build (the home's file, the photos, the story, the highlights).
**Ends:** the page is live at `homes.resmara.com/<street-address>`, and the agent has the link.

**Today:** the page design exists in the front end (`static/listing-site.js`) and is shown on live
campaigns (section 3, "Your listing page"). **Nothing is served publicly yet:** the backend has no
public route and no lead endpoints. This engine builds that, and upgrades the page itself.

## 2. What it pulls from (nothing is invented)

1. **The home's file** (Engine 3): address, price, beds, baths, square feet, lot, year built,
   garage, every photo, the listing video. A fact the file doesn't have is left off. Facts marked
   "please check" are never shown until the agent confirms them in review.
2. **The campaign** (Engine 4): the story of the home, the 3 highlights the ad hooks were built
   from (pool, view, kitchen…), the best photos in order, and the open house if one is set.
3. **The brand kit** (Engine 2): logo, fonts, colours, headshot, name, brokerage, license number,
   phone, the legal lines, and the Voice of the client for the words.

## 3. The page tells the story of the home (Adam, 22 Nov)

Resmara is story-based. The posts tell the home's story over 14 days; **the website tells the same
story in one place**, written out in full. It reads like a walk through the house, not a spec sheet.
The story comes from Engine 4's plan (same angle, same moments, same voice), so the page, the posts
and the ad all feel like one campaign.

Top to bottom:

1. **Header** that stays at the top: their logo (or brokerage name), Photos · Details ·
   Neighborhood · Contact, and **Schedule a showing**.
2. **Hero:** the best exterior photo, full width, with a slow zoom; **the listing video plays here
   instead when there is one** (muted, looping, sound on tap). A status chip (Just listed, Open house
   Saturday, Price improved, Pending, Sold), the address, city, price, beds, baths, square feet, lot,
   and two buttons: **Schedule a showing** and **See all N photos**.
3. **Quick facts band** right under the hero, in their main colour: price, bedrooms, bathrooms,
   living area, lot, year built, garage (only what the file has). Buyers get the numbers in one
   glance, then the story.
4. **The story:** a headline for the home ("A Hill Country home built around the view"), then **4
   chapters**, each a moment in the house with a big photo, a smaller second photo, a chapter number,
   a short title and a paragraph. The AI picks the chapters to fit the home, for example:
   - **The arrival:** the approach, the front door, the first view inside.
   - **The heart of the house:** the main living space and the kitchen.
   - **The evenings:** the outdoor spaces, the pool, the sunset.
   - **The mornings:** the primary suite, the quiet spots.
   Other homes get other chapters (the workshop, the garden, the view from the loft). Chapters
   alternate left and right on a computer and stack on a phone.
5. **Every photo:** a gallery grid of the best 8, then **View all photos**, a full-screen viewer
   (swipe on phones) with every photo from the home's file.
6. **Open house** band, only when one is set.
7. **The neighborhood:** drive times to the places that matter there (downtown, the lake, the
   airport, shopping) and **Open in Maps**. Facts only: never "great schools", "safe area" or
   anything about who lives there (Fair Housing).
8. **Contact, closing the story:** a short **note from the agent** in their voice ("Come at golden
   hour if you can…"), their headshot, name, brokerage, license number and phone, **Call** and
   **Text** buttons, and a form with one choice, **Schedule a showing** or **Ask a question**.
9. **Footer:** the brokerage's legal lines, the license, the Equal Housing Opportunity logo, and
   "Information is believed accurate but not guaranteed."

**On phones,** a bar stays at the bottom: **Call · Text · Schedule a showing.**

**The words** are written by the AI from the home's file, Engine 4's story and the Voice of the
client. Every sentence has to be backed by the file or a photo (no invented features), and passes
the same Fair Housing check as every post (Engine 4, 9f). The agent can edit any of it in review.

## 4. Beautiful on every screen

- **Phone first.** Most visitors come from Facebook and Instagram on their phones. Everything
  stacks into one column, buttons are big, the bottom bar is always in reach.
- **Fast.** Photos are resized for the screen they're on and load as you scroll; the hero loads
  first. Target: the page is usable in under 2 seconds on a phone on mobile data.
- **One template, filled from the brand kit** (Adam, 22 Nov). The website is a templated site: our
  single best design, customised with what the brand kit (Engine 2) already holds. No new research
  of the agent's own website: that was done when the brand kit was built.
  | From the brand kit | Where it goes on the page |
  |---|---|
  | Logo | The header |
  | Heading font, body font | All headings; all text |
  | Main colour | The facts band, the dark buttons, the contact section |
  | Accent colour | The main button, the chapter labels and numbers, the status chip |
  | Tint and page colours | The backgrounds |
  | Text colour | The body text |
  | Headshot, name, brokerage, license, phone | The contact section and the footer |
  | Legal lines | The footer |
  | Voice of the client | The words of the story and the agent's note |
  Plus the house itself from the home's file (photos, facts, video). If a brand kit field is
  empty, the template's own default is used (initials instead of a logo or headshot).
- **Built to showcase the home:** big photos first, generous space, few words per screen.
- **Inside the in-app browsers** (Facebook, Instagram), which is where ad clicks open: tested there.

## 5. Built with everything else (Adam, 22 Nov)

The website isn't a separate step and there's no "live or not live" switch for the agent. **It's
built in the same build as the campaign:** while Engines 3 and 4 research the home and build the
posts and the ad, this engine builds the website. When the build finishes, it all lands on the
campaign together, ready to review: the launch details, the calendar and the website.

| Campaign | Section 3 |
|---|---|
| Built, waiting to be unlocked | There, blurred with everything else behind pay to unlock |
| Unlocked, in review | **3 Your listing page:** the preview, Preview your website, Copy link, Share. The link works, so the agent can send it to anyone. (Steps: 1 Confirm your launch details, 2 Campaign calendar, 3 Your listing page, 4 Ready to go?) |
| Live | **3 Your listing page** with its numbers (1 Campaign leads, 2 Campaign calendar, 3 Your listing page, 4 Reports) |
| Pending or sold (Engine 6, the moment it's detected or the agent marks it) | **Stops marketing the home** (legally required once it's pending): a Pending or Sold banner, the status chip changes, **Schedule a showing becomes Ask about similar homes**, the video stops; the agent's contact details and the form stay so late visitors still reach the agent |
| Ended | Stays up 30 days, then becomes the agent card and form only: "This home is no longer available. Ask about similar homes." |

Changes made in review (a fact, a photo) show on the website straight away.

## 6. The link and sharing (Adam, 22 Nov)

- **The address:** `homes.resmara.com/<street-address>` (e.g. `/1248-oakridge-drive`). Unique,
  saved on the campaign, never changes; Run it until it sells keeps the same link.
- **It all lives in section 3 of the campaign page, "Your listing page"** (Adam, 22 Nov), with the
  other numbered steps (1 Campaign leads, 2 Campaign calendar, 3 Your listing page). Nothing about
  the website goes at the top of the page. Section 3 holds the numbers (section 8), a scrollable
  preview of the page with its link, and three buttons:
  - **Preview your website:** opens the page as visitors see it.
  - **Copy link.**
  - **Share:** on a phone, the phone's own share sheet (Messages, WhatsApp, email, anything). On a
    computer, a small pop-up with Copy link, Email it and Text it.
- **It looks good when it's shared:** the link carries a preview card (the hero photo, the address
  and the price), so it shows up as a picture in texts, emails and social posts, not a bare URL.
- **Every post and the ad link here** (Engine 4): the ad's clicks and the Facebook captions, each
  tagged so the report knows which post or ad brought each visitor. Instagram captions never carry a
  link (Engine 4, 9c).
- **Agents posting by hand** (no Page connected yet) copy the link into their own posts, so their
  leads still land on Resmara.

## 7. Leads

- **Form:** name, email, phone (optional), message, and whether they want a showing or have a
  question. Stored as a lead on the campaign and **emailed to the agent within a minute**.
- **Call taps and Text taps count as leads, and are counted separately** (Adam, 22 Nov): a tap on
  Call is a **call lead**, a tap on Text is a **text lead** (each at most one per visitor per day),
  no email. They're listed as their own lead types and have their own numbers. New endpoint next to
  the spec's `/call`: `POST /api/public/listing/{slug}/text` (stored with `source='text'`,
  `channel='Listing page text button'`).
- **Spam:** the hidden trap field and a limit per visitor, as in the spec.
- All of it shows under **Campaign leads → From your listing page**, and in the day 7 and 14 reports.

## 8. Numbers

On the campaign page (section 3, "Your listing page") and in the reports: **Visits, Form leads,
Call leads, Text leads**, each its own number, and which post or ad brought them.

## 9. How every website is built, stored and served, automatically (for Dan)

**The short version:** no website is deployed per listing, and nobody touches anything. Every build
saves a **site record** for the home, the photos sit in **Cloudflare R2**, and one route in the app
we already run on Render draws the page from the record when anyone opens the link, and passes the
photos through from R2. One template, in code, for every site.

**Why not a Cloudflare Pages site per listing** (the first idea): every campaign would need its own
build and deploy, a second hosting setup, and its own copy of the design, so a design fix would mean
redeploying hundreds of sites. With one route and one template, a fix reaches every website at once,
and there's nothing to deploy when a campaign is built.

### How each house gets its own address (no DNS work per house)

The DNS change above is the **only** DNS change, ever. It points the whole of `homes.resmara.com`
at the app. Every house is then just a path under it, created by the system on every build:

1. **The build makes the slug** from the street address in the home's file (Engine 3):
   `1248 Oakridge Drive` → `1248-oakridge-drive`. Code does this, not the AI, so it's always the
   same rule: lowercase, letters, numbers and dashes. If it's already taken (same street name in
   another city, or an older campaign of another agent's), add the city (`-austin`), then `-2`, `-3`.
2. **It saves the slug on the site record** (and the campaign), and never changes it, so links
   already shared keep working. A new round of Run it until it sells reuses it.
3. **The app answers every `homes.resmara.com/<anything>`**: it looks the slug up in `listing_sites`
   and draws that home's page. Unknown slug: a friendly "This home isn't here" page with a link to
   Resmara, never an error page.
4. **The link is what goes everywhere automatically:** section 3 of the campaign, the Facebook
   captions and the ad's destination (Engine 4, with tracking tags), the share card, the reports.
   Nobody types or pastes it.

**Where the AI comes in:** the AI writes the website's words (the story, the chapters, the note) and
picks the photos for each chapter during the build. The address, the storage and the serving are
plain code, so they work the same way every time.

### What happens on every campaign, step by step

1. **The build runs** (after the link is in and the campaign is purchased, alongside Engines 3 and 4).
2. **Photos:** every photo from the home's file is saved to R2 in three sizes (phone, computer,
   full screen), plus the listing video if there is one. R2 already holds the listing photos
   (`app/services/storage.py`); for websites it must be **on in production** (today it falls back to
   the database when it isn't set up, which is fine for the app but too slow for public pages).
3. **The site record:** one row per home in a new `listing_sites` table, written by this engine:
   - the **slug** (`1248-oakridge-drive`, unique; on a clash `-2`, `-3`), which never changes;
   - the facts, the story headline, the 4 chapters, the agent's note, the neighborhood times and
     the open house, all from Engines 3 and 4;
   - the photo and video addresses in R2, in order;
   - a **snapshot of the brand kit** (logo, fonts, colours, headshot, name, brokerage, license, phone,
     legal lines), so a later brand change doesn't silently restyle a live listing (a "Refresh my
     website" button can update it on purpose);
   - status (built, live, pending, sold, ended) and a version number.
4. **The share image:** a 1200×630 picture (hero photo, address, price) is made once and saved in
   R2. It's what shows when the link is texted or posted.
5. **Checks before it's ready** (same idea as Engine 4's checks): every required field is there,
   every photo loads, the words pass the Fair Housing check, the page renders without errors, and
   the share image exists. If something fails, that part is retried once, then a safe default is used
   (for example, a chapter is dropped rather than shown broken), and the team is alerted if the page
   still can't be built. Nothing is charged until unlock, as with Engine 4.
6. **It lands in section 3** of the campaign with the rest of the build, and the link is live once
   the campaign is unlocked.

### How the page is served

- **`homes.resmara.com/<slug>`** points at the Render app (one DNS record Adam adds at GoDaddy).
- The app's route (`/l/<slug>`) reads the site record and **returns the finished page as HTML**,
  drawn with the same template code the dashboard preview uses, so the preview and the real page
  can't drift apart. Returning finished HTML (not a blank page that draws itself) matters: Facebook,
  iMessage and Google read the page title and share image from it.
- **Caching:** the app keeps each finished page in memory until its record changes, so a burst of ad
  clicks doesn't rebuild the page every time. Cloudflare's edge cache can sit in front later (see
  Setup).
- Leads (form, call, text) and visits go to the public endpoints in section 7.

### Keeping it current, automatically

- **The agent edits something in review** (a fact, a photo, a chapter): the record updates, the
  version goes up, the cache is cleared. The page is current on the next load.
- **Status changes** from Engine 6 (pending, sold) or the campaign ending: the record's status
  changes and the page shows the banner, or after 30 days the "no longer available" version.
- **Run it until it sells** (Engine 8): same slug, the record is refreshed with the new round's story
  and photos, so every link already shared keeps working.

### Keeping it consistent and good

- **One template, versioned in the code.** No per-site copies. Any design improvement reaches every
  website on the next deploy.
- **A test page per release:** the template is rendered with 3 sample brand kits (light, dark, bold)
  and checked on a phone and a computer before a release goes out.
- **A daily check:** every live website is fetched once a day; any that doesn't load, or has a broken
  photo, is flagged to the team.

### What this costs

Close to nothing: R2 is about a tenth of a cent per campaign a year past its free tier (see
`storage.py`), and the pages are served by the app we already run.

### Setup (one time)

Checked in GoDaddy on 22 Nov: `resmara.com` is an A record to Render (216.24.57.1) and `www` is a
CNAME to `resmara.onrender.com` (the live `resmara` service). DNS is at GoDaddy, not Cloudflare.

- **DNS: done (22 Nov 2026, 4:48 PM).** `homes` is a CNAME to `resmara.onrender.com` in GoDaddy, the
  same target as `www`. GoDaddy says it takes effect within an hour (up to 48).
- **Render (Dan):** add `homes.resmara.com` as a custom domain on the `resmara` service (Render then
  issues its certificate). **Move the service off the free plan before launch:** a free web service
  sleeps after about 15 minutes idle, so the first person to tap an ad would wait while it wakes up.
- **R2 in production (Dan):** confirm it's on (the Team room's finance tab shows the storage mode).
- **Photos load through the app (decided with Adam, 22 Nov):** the website asks for each photo at
  `homes.resmara.com/photos/<file>`, and the app fetches it from R2 and sends it on (with a long
  cache header). Visitors only ever touch Render, so R2 needs no public address and **the DNS stays
  at GoDaddy; no move to Cloudflare.** Not a Render disk: a disk stops zero-downtime deploys and pins
  the app to one server.
- **Later, only if traffic needs it:** moving the DNS to Cloudflare would add edge caching and a direct
  photo address. No code changes are needed for that.

## 10. Decided with Adam (22 Nov 2026)

- Every campaign gets its own website, built automatically, in the agent's brand.
- Beautiful and fast on phones and computers.
- The ad and the posts drive traffic to it.
- "Preview your website", Copy link and Share on the campaign dashboard, so the agent can send the
  home to anyone.
- The website tells the story of the home, the same story-based approach as the posts.
- The brand kit is baked into the design; the layout is chosen to showcase the home best.
- Call taps and Text taps are leads, counted separately (call leads, text leads).
- Templated: one best design, filled from the brand kit; no research of the agent's own website.
- Everything about the website lives in section 3 of the campaign page, never at the top.
- Built in the same build as the campaign; it lands with the calendar, ready to review (section 5).
- The listing video plays in the hero when there is one.

## Screens

Mockups of what the agent and the buyer see, from the preview (`engine-5-screens/`, with
`mockup.js`, the preview script they were taken from). The sample brand kit is "Morgan & Co."
(navy, gold, serif headings). Mockups only: the brain above is what to build.

| Screen | What it shows |
|---|---|
| `01-hero.png` | The hero: status chip, address, price, facts, Schedule a showing, See all photos, where the video plays |
| `02-story-opening.png` | The quick facts band and the story headline |
| `03-chapter.png` | A story chapter: big photo, inset photo, number, label, title, paragraph |
| `04-photos.png` | The gallery grid and View all photos |
| `05-neighborhood.png` | Drive times and Open in Maps |
| `06-contact.png` | The agent's note, Call, Text and the showing/question form |
| `07-section-3-live.png` | Section 3 on a live campaign: Visits, Form leads, Call leads, Text leads |
| `08-section-3-buttons.png` | Preview your website, Copy link, Share |
| `09-share.png` | Share on a computer: Copy link, Email it, Text it |
| `10-phone-hero.png`, `11-phone-chapter.png`, `12-phone-contact.png` | The same page on a phone, with the Call · Text · Schedule a showing bar |
| `13-section-3-in-review.png` | Section 3 during review (steps 1 to 4) |

Live preview: https://claude.ai/artifact/Lip2AN9HQZuLf4J5AsP8Vy#website
