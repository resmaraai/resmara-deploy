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
| 5 | Building | Waits about a minute. Resmara researches the home, picks the best 14 photos, writes and designs the posts and the ad, and builds the website | The campaign page (staged), calendar already built |
| 6 | 1 Confirm your launch details | Sets the go-live date and ad budget, clicks **Run it until it sells** if wanted. **Confirm details** | Block 2 |
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
- **Charge and build are one step (Adam, 21 Nov).** The moment the agent clicks Build my campaign,
  the card is charged and the engine runs straight away: it picks the photos, checks the link for a
  video (a video becomes the ad and the day 1 post), writes the 14 posts, builds the ad and the
  home's website. The agent lands on the campaign page with the calendar already built. Nothing
  waits for the launch details. (Back end: the build is started from the create step, not from
  launch details. Engine 3 Listing link and Engine 4 Campaign build.)

---

## 3. The staged campaign page (paid for, not launched)

A paid campaign that hasn't launched is **Staged** (orange pill on its card, button **Review staged
campaign**). Its page has four numbered blocks. Blocks 1 to 3 **open collapsed** with a drop-down
arrow; the agent opens the ones they want.

| Block | Shows | The one button | Unlocks |
|-------|-------|----------------|---------|
| **1 Confirm your launch details** | Go-live date (defaults to the next day), ad budget ($50 default; "Meta bills your ad spend separately from your Resmara campaign"), and the navy **Run it until it sells** box: "Tell your sellers" line, an orange **Run it until it sells** button and **How it works** (a pop-up with Got it). Once it's on, both buttons go and a white box on the right says "✓ Run it until it sells is on" (with Turn off until the details are confirmed). No "Send clicks to" field: everything links to the home's website | **Confirm details** | Block 2's button |
| **2 Campaign calendar** | Already built when the page opens: the 14 posts and the ad. Opening a post lets the agent edit the title and caption, upload a replacement photo, and move the date | **Approve calendar** | Block 4's button |
| **3 Your listing page** | The website Resmara built for the home, in a scrollable preview, plus **View full page**. No numbers yet | (View full page only) | — |
| **4 Ready to go?** | What happens next, and how many posts were opened (opening them is optional) | **Approve and launch** | Launch |

- **After Confirm details**, block 1's header reads "✓ Goes live Nov 22 · $50 ad budget · Runs
  until it sells" with a **Change** link (until launch). Confirming doesn't rebuild the calendar.
- If a paid campaign ever opens without its calendar (the build was interrupted), the page starts
  the build itself.
- **Approve calendar:** if any post or the ad wasn't marked reviewed (Save and mark reviewed in
  the post editor), it asks first: "You haven't reviewed everything. 12 of 15 posts and ads haven't
  been marked as reviewed. Are you sure?" with **Keep reviewing** or **Yes, approve calendar**.
- **Approve and launch:** a plain "Approve and launch?" check, then it launches.
- **Removed on purpose:**
  - "Send clicks to": everything goes to the listing website;
  - the photo box at the top: photos are swapped inside posts;
  - Reports before launch;
  - the Run until sold button on the campaign card: once it's on, the card shows a "Run until sold
    is on" tag instead.

---

## 4. After launch (the live campaign page)

Launching switches the page straight to its live layout. The four sections all start closed:

1. Campaign leads
2. Campaign calendar (locked; **Withdraw post** for posts not yet out)
3. Your listing page (with visits, form leads and calls)
4. Reports

---

## 5. What the server has to do (Dan)

1. **The property file and the new check outcomes:** Listing Link Engine, sections 4 and 5.
2. **Charge and build in one step:** start the build from the create step (photos, video check,
   posts, ad, website), so the calendar exists before the agent lands on the page. Refund on a
   failed build.
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
- Open **905 Laurel Bend** (Staged): every block opens collapsed, the calendar is already built,
  and each button only turns on once the block above is confirmed.
- After **Approve and launch**, the page shows 1 Campaign leads at the top.
