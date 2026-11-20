# Listing page: how it's supposed to work

**Owner:** Adam (front end) · **Backend:** Dan · **Last updated:** PR #10, 19 Nov 2026

Every campaign gets a simple one-page website for the home, in the agent's brand. Every post and
the ad link to it, so the agent never has to find or paste a link. People who are interested fill
in the form or tap Call. Both land under **Campaign leads** and email the agent.

If the app and this doc disagree, one of them is wrong. Flag it rather than guess.

---

## 1. What the agent and the buyer see

| Who | Where | What |
|-----|-------|------|
| Agent | Live campaign page, section **3 Your listing page** | The page address, 3 numbers (views, form leads, call taps), a scrollable preview, and **View full page** |
| Agent | Campaign page, section **1 Campaign leads** | **From your listing page** (form and call leads) listed above **From your posts and ad** (comment leads) |
| Agent | Their inbox | One email per new lead, the same alert email as comment leads |
| Buyer | `homes.resmara.com/<slug>` | Header with the brokerage logo and a **Call [first name]** button; photo hero with price and facts; about the home; gallery; agent card; **Ask about this home** form; legal footer with Equal Housing |

Everything on the page comes from the campaign (address, price, facts, photos, description) and
the agent's **My Brand** (logo, colours, fonts, headshot, phone, brokerage, license). If a fact
isn't known, it's left off. Nothing is made up.

---

## 2. The recommended setup (simplest that works)

**Serve every page from the app we already run on Render. Don't deploy a site per listing.**

1. **One public route in the existing FastAPI app:** `GET /l/{slug}`, no sign-in.
   - It returns a small HTML shell that loads `static/listing-site.js` and the page's data as JSON,
     and sets `window.LISTING_PUBLIC = { slug }`.
   - The page draws itself with `listingSiteHTML()`, the same code the dashboard preview uses. The
     preview and the real page can't drift apart, and there's one design to maintain.
2. **The domain:** point `homes.resmara.com` at Render as a custom domain. That's one CNAME at
   GoDaddy, which Adam can add. Make `homes.resmara.com/{slug}` serve `/l/{slug}`.
3. **Photos:** they already live in Cloudflare R2 (`app/services/storage.py`). The page uses the
   same URLs. Nothing new to host.
4. **Later, only if traffic needs it:** put Cloudflare in front of `homes.resmara.com` for caching.
   No code changes are needed for that.

Why not Cloudflare Pages per listing (the first idea): every new campaign would need a build and a
deploy, a second hosting account, and a copy of the page design. The route above gets the same
result with nothing extra to run.

---

## 3. The address (slug)

- Built from the street address: `4821 Maple Ridge Ct` becomes `4821-maple-ridge-ct`. This is
  `listingSlug()` in `listing-site.js`.
- It must be unique. On a clash, add `-2`, `-3` and so on. Store it on the campaign (`boosts.slug`),
  so it never changes once posts have gone out with it.
- A **Run it again** campaign on the same home **keeps the same slug**. The page simply shows the
  newest campaign's details.

---

## 4. Links in posts and the ad

- **Every post and the ad link to the page** by default:
  `https://homes.resmara.com/{slug}?utm_source={facebook|instagram}&utm_content={post-3|ad}`.
- The `utm_content` value tells us which post brought each visitor, which feeds the reports.
- If the agent filled in **Send clicks to** on the campaign, that address wins instead. When it's
  left blank, it's the listing page.

---

## 5. Leads: the two public endpoints

The front end is already wired to these (live mode in `listingFormSent()` and `listingCallTap()`).

| Endpoint | Body | Server does |
|----------|------|-------------|
| `POST /api/public/listing/{slug}/lead` | `{name, email, phone, message, website}` | Store a `Lead` with `source='web'` and `channel='Listing page form'`, then email the agent. Return 201. |
| `POST /api/public/listing/{slug}/call` | (none; sent with `sendBeacon`) | Store a `Lead` with `source='call'` and `channel='Listing page call button'`, text "Tapped Call on your listing page", **no email**. Return 204. |

Rules:

- **Spam:**
  - `website` is a hidden trap field. If it has any value, return 201 and store nothing.
  - Rate-limit by IP: about 5 form posts an hour per slug.
- **The `Lead` table** needs `email` and `phone` columns. The panel already reads `row.email` and
  `row.phone`, but the model doesn't have them yet.
- **Call taps:** count at most one per visitor per day, so one person tapping twice isn't two leads.
- **Page views:** count them in `GET /l/{slug}`, one per visitor per day, stored per campaign per
  day. Section 3's "views" number reads this.

---

## 6. When the page is live

| Campaign state | Page shows |
|----------------|------------|
| Draft or in review | Not public. `/l/{slug}` returns 404. |
| Approved or live | The full page |
| Paused (pending or sold) | The full page with a "Pending" or "Sold" banner, and the form still works |
| Campaign ended | Stays up **30 days**, then switches to the agent card and the form only ("This home is no longer available. Ask about similar homes"), so late visitors still become leads |

The pause and the 30 days are a suggestion. Adam and Dan can change them.

---

## 7. Without a Facebook Page (see `new-user-experience.md`)

The listing page works with no Meta connection at all. An agent who downloads their posts and
shares them by hand still gets a page to link to, and still gets the leads.

---

## 8. How to test it

- Preview: https://claude.ai/artifact/Lip2AN9HQZuLf4J5AsP8Vy
- Open the Oakridge campaign. Section 3 shows the page and its numbers.
- **View full page** opens it. Sending the form or tapping Call adds a lead to section 1 and bumps
  the numbers. In the preview this happens right there. Live, it goes through section 5.
- Live check: send the form from a phone on mobile data. Confirm the lead appears under
  **From your listing page** and the agent gets the email within a minute.
