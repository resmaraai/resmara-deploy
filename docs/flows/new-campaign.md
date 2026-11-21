# New campaign: how it's supposed to work

**Owner:** Adam (front end) · **Backend:** Dan · **Last updated:** 21 Nov 2026
**Logic behind it:** *Listing Link Engine* spec (link check, property file, pay before build).

The goal: an agent gets from **+ Campaign** to a live, paid campaign in as few steps as possible.
All they decide is the **go-live date**, the **ad budget**, and whether to **keep it running
until it sells**.

---

## 1. The path at a glance

| # | Step | Agent does | Ends at |
|---|------|------------|---------|
| 1 | + Campaign | Pastes the listing link | Link check |
| 2 | Link check | Watches it check. If it finds nothing: types the address and uploads photos | "We have the home's details and N photos" |
| 3 | Permission | Ticks "I have permission to use these photos…" | Payment step |
| 4 | Pay | Clicks **Build my campaign · $49**. That click is the approval: the card on file is charged. No card: "Add a card to build your campaign" first, through Stripe | Building |
| 5 | Building | Waits about a minute. Resmara researches the home, picks the best 14 photos, writes and designs the posts and the ad, and builds the website | The campaign page (draft) |
| 6 | 1 Launch details | Sets the go-live date and ad budget, ticks "Keep it running until it sells" if wanted. **Approve launch details** | Block 2 |
| 7 | 2 Campaign calendar | Opens any post to change copy or swap the photo. **Approve calendar** | Block 4 |
| 8 | 3 Your listing page | Looks at the website Resmara built (optional) | — |
| 9 | 4 Ready to go? | **Approve and launch** | The live campaign page |
| 10 | Live | Leads come in at the top | — |

---

## 2. The New campaign pop-up

- **Link field:** one field, "Paste your listing link". A short "How do I get this link?" helps
  with MLS public share links.
- **Check:** shows the five progress lines from the Listing Link Engine.
- **Results:** every outcome and its message is listed in the Listing Link Engine, section 5.
  - On success it shows what was found (and, next, the key details to confirm).
  - On "couldn't find it" it switches to **Enter it manually**: the address, plus photo uploads
    (14 to 60).
- **Permission tick:** required before the button turns on.
- **Payment step:**
  - the button reads **Build my campaign · $49**, and clicking it approves the charge;
  - card on file: charged straight away ("Paying $49 for this campaign with your card on file");
  - no card: "Add a card to build your campaign" goes to Stripe and comes back to the same step;
  - if the build fails after the charge, it's refunded automatically.

---

## 3. The draft campaign page (before launch)

Four numbered blocks, top to bottom. Each block has **one** button.

| Block | Shows | The one button | Unlocks |
|-------|-------|----------------|---------|
| **1 Launch details** | Go-live date (defaults to the next day), ad budget ($50 default; Meta bills it directly), the **Keep it running until it sells** checkbox ($39 every 2 weeks until under contract, with a "How it works" link), and a note that every post and the ad link to the home's website | **Approve launch details** | Block 2's button |
| **2 Campaign calendar** | The 14 posts and the ad. Opening a post lets the agent edit the title and caption, upload a replacement photo, and move the date | **Approve calendar** | Block 4's button |
| **3 Your listing page** | The website Resmara built for the home, in a scrollable preview, plus **View full page**. No numbers yet | (View full page only) | — |
| **4 Ready to go?** | What happens next, and how many posts were opened (opening them is optional) | **Approve and launch** | Launch |

- **After approving block 1**, it collapses to one line: "✓ Goes live Nov 22 · $50 ad budget ·
  Runs until it sells" with a **Change** link (until launch).
- **Approve and launch:** if some posts weren't opened, it asks "You haven't reviewed everything.
  Approve anyway?" Then it launches.
- **Removed on purpose:**
  - "Send clicks to": everything goes to the listing website;
  - the photo box at the top: photos are swapped inside posts;
  - Reports before launch;
  - the separate Run until sold buttons: it's now a checkbox in block 1.

---

## 4. After launch (the live campaign page)

Launching switches the page straight to its live layout. The four sections all start closed:

1. Campaign leads
2. Campaign calendar (locked; **Withdraw post** for posts not yet out)
3. Your listing page (with visits, form leads and calls)
4. Reports

The campaign card on My campaigns shows it as Active.

---

## 5. What the server has to do (Dan)

1. **The property file and the new check outcomes:** Listing Link Engine, sections 4 and 5.
2. **Charge before build:** refund on a failed build.
3. **Save launch details** (start, budget, until-sold) in one call. Until-sold uses the existing
   `RM.setUntilSold`.
4. **Approve and launch** = the existing `approveAll`. It sets `launched_at`, so the live layout
   shows right away (front end: `campaignIsLive()` also accepts `launched`).
5. **Destination:** always the listing website (`homes.resmara.com/<slug>`). The old
   `destination` field can stay in the data for now, but the page no longer sets it.

---

## 6. How to test it

- Preview: https://claude.ai/artifact/Lip2AN9HQZuLf4J5AsP8Vy#client (reload), then **+ Campaign**
  and paste any listing link.
- Walk every block in order and check that each button only turns on once the block above is
  approved.
- After **Approve and launch**, the page shows 1 Campaign leads at the top.
