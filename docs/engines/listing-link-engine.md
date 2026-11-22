# Resmara · Listing Link Engine — Build Spec v1.0

**Date:** 21 Nov 2026 · **For:** Dan (backend) and Adam (front end)
**Companions:**
- `docs/flows/new-campaign.md` (the screens);
- *Meta Integration Engine* (what can post);
- *Post Engine spec* (what's built from the property file).

**Scope:** from the moment the agent pastes a link (or types an address and uploads photos) to a
**property file** the campaign build can trust, *before* the agent is charged.

---

## 1. What this engine must do

1. **Get everything it can from whatever the agent pastes**: an MLS share link, Zillow, Realtor,
   Redfin, a brokerage site, a photographer's delivery page (Fotello, Aryeo), Dropbox or Drive.
2. **Never take money for a campaign it can't build.** The agent pays only once there's an
   address and enough usable photos.
3. **Never invent a fact.** Every detail is either found (with where it came from) or left out.
4. **When the link gives nothing, switch smoothly to the manual path**: the address and photo
   uploads, then research the home by address.
5. **Tell the agent, in plain words, what it found**, and the one thing it needs from them.

---

## 2. The engine at a glance

```
LINK ─► 1 VALIDATE ─► 2 OPEN ─► 3 PHOTOS ─► 4 VIDEO ─► 5 AI PAGE AUDIT ─► 6 RESEARCH BY ADDRESS ─► VERDICT
 or                                                                                                  │
ADDRESS + UPLOADS ─────────────────────────────────────────────────────────► 6 RESEARCH BY ADDRESS ──┘
                                                                                                     ▼
                         PERMISSION TICK ─► PAY ($49) ─► PROPERTY FILE ─► campaign build (Post Engine)
```

What the agent watches while it runs (the New campaign pop-up already shows these lines):

- Opening your link
- Looking for the home's details
- Looking for the photos
- Checking for a video
- Researching the home online

---

## 3. The stages

| # | Stage | Status today | AI? |
|---|-------|--------------|-----|
| 1 | **Validate.** A real web address; not an MLS sign-in page | Built (`listing_check`) | No |
| 2 | **Open.** Read the page through the hosted reader; dead link, sold, pending | Built (`listing_watch.read_listing`, `classify`) | No |
| 3 | **Photos.** The gallery, up to 60, trying four ways: the page's own data, the hosted reader, the page it points to (MLS viewers and iframes), then the same home on Trulia by address | Built (`photos.discover`) | No |
| 4 | **Video.** A tour video on the page | Built (`listing_video.find`) | No |
| 5 | **AI page audit.** Read the page and pull out the property file (section 4) | **Not built.** Today the check only looks for listing words and an address in the link | **Yes** |
| 6 | **Research by address.** Fill the gaps from public pages | Built as R1, but it only runs **during the build, after payment**. Move a light version to check time | **Yes**, with web search |

### Stage 5: the AI page audit (new)

- **Input:**
  - the page text (scripts and styles stripped, first 40,000 characters);
  - any JSON-LD or `__NEXT_DATA__` blocks;
  - the link;
  - the address taken from the link.
- **Model:** a small, fast model in JSON mode. Every field comes back with
  `{value, source: "page" | "link", quote}`, where `quote` is the exact words on the page it took
  the value from.
- **Rule:** if there's no quote, the value is dropped. That's the "never invent" guard, and it's
  checked in code, not trusted to the model.

### Stage 6: research by address, at check time (moved earlier)

- Runs when stage 5 leaves gaps, and always on the manual path.
- It's the same R1 prompt (public listing pages and records, web search), asked for the
  missing fields only.
- Anything found here is marked `source: "research"`. It shows to the agent as **"Found online,
  please confirm"**, never as fact.
- The full R1 still runs during the build for the story and context, as today.

---

## 4. The property file (what the engine hands over)

```json
{
  "address": {"line": "4821 Maple Ridge Ct", "city": "Redding", "state": "CA", "zip": "96001", "source": "page"},
  "price": {"value": 845000, "source": "page", "quote": "$845,000"},
  "beds": {"value": 4, "source": "page"}, "baths": {"value": 3, "source": "page"},
  "sqft": {...}, "lot": {...}, "year_built": {...}, "type": {...},
  "description": {"value": "...", "source": "page"},
  "features": [{"value": "pool", "source": "page"}],
  "status": "active | pending | sold | unknown",
  "listing_agent": {"name": "...", "brokerage": "...", "source": "page"},
  "open_house": [...],
  "photos": {"found": 32, "source": "link | upload | trulia", "urls": [...]},
  "video": {"found": true, "url": "..."},
  "permission_confirmed_at": "2026-11-21T20:30:00Z",
  "needs_confirmation": ["year_built"],
  "link": "https://...", "checked_at": "..."
}
```

It's stored on the campaign (`boosts.property_file`). The Post Engine reads facts **only** from
here plus its own R1 research, and anything in `needs_confirmation` is never stated as fact in a
caption.

---

## 5. Verdict: every outcome, and what the agent sees

| Outcome | When | Agent sees | Next |
|---------|------|------------|------|
| `ok` | Address, details and 14 or more usable photos | "We have the home's details and N photos." | Permission tick, then pay |
| `few_photos` | Details and 4–13 photos | "We found N photos. Add more for a full 14-day campaign, or continue with these." | Upload more (optional), then pay. The post engine reuses its best photos with different crops and stories |
| `no_photos` | Details, gallery blocked or missing | "We have the home's details, but we can't get the photos from this link." | Upload photos (14 to 60), then pay |
| `no_listing` | No home found at all | "We couldn't find a home for sale at this link." | **Enter it manually** (address plus uploads) |
| `sign_in` | MLS sign-in link | "This link needs an MLS sign-in to open. Use your MLS's public share link." plus a short how-to | Paste another link, or enter manually |
| `dead_link` | 404 or 410 | "There's no page at this link. It may have been taken down or typed wrong." | Paste another link, or enter manually |
| `sold` / `pending` | Page says so | "This listing shows as sold/pending, so it can't be advertised." | Stop |
| `other_agent` | The page names a listing agent who isn't this agent (by name or brokerage) | "This listing shows a different listing agent. Only advertise it if you have their permission." | The permission tick covers it, and the note is stored |
| `not_a_link` | Not a web address | "That doesn't look like a complete web link." | Fix it |

The manual path's own checks:

- the address is required;
- at least 14 photos (up to 60);
- the permission tick.

Stage 6 then researches the address. Uploads are converted to JPEG and checked for broken files
(`photos.looks_incomplete`, exists).

---

## 6. Photos: pick the best, keep only what's used

- **All found photos are tagged** by the vision model (room, a 1–10 social score, post yes/no with
  a reason, features). This is built.
- **The best 14 for posts, plus the ad's images,** are picked by score and the photo rules (Post
  Engine spec). Those are the only photos **copied into Resmara's storage**.
- **The rest are kept as links only** (their tags and source address) for 30 days. That way a
  swap can offer "other photos from your listing" without storing a gallery that isn't used.
- **Swaps happen inside each post** (the calendar), never in a box at the top of the page.
  Options:
  - pick another photo from the listing;
  - upload your own (resized and converted to JPEG, already built).
- Photo permission is required before anything is copied or built, and its time is stored.

---

## 7. Pay before build

The order on screen: checks pass, then the permission tick, then the payment step, then the
build.

- **Card on file:** the button reads **Build my campaign · $49**, and the click is the approval
  (Billing rules). The card is charged straight away and the build starts. This is built
  (`billing.js`).
- **No card:** "Add a card to build your campaign." This goes to Stripe's secure page, then
  comes back to the same step with the link and photos kept.
- **If the build fails after charging:** the build retries once. If it still fails, refund
  automatically and tell the agent. They're never charged for nothing.
- **The charge only happens once the property file has an address and enough photos.** A
  failed check never reaches the payment step.

---

## 8. Where AI is used, and the guardrails

| Where | What it does | Guardrail |
|-------|--------------|-----------|
| Stage 5 page audit | Reads the page and fills the property file | Every value needs an exact quote from the page, checked in code |
| Stage 6 research | Fills gaps by address | Marked "found online, please confirm"; never stated as fact in posts |
| Photo tagging | Scores and filters every photo | Built. "Post: no" photos are never used |
| Unknown failures | When a link fails in a new way, it records the page's first 2,000 characters and the reason for the weekly review | Operator only. The agent always sees a known outcome |

---

## 9. Tests

1. **A link corpus:** 30 real links with the expected outcome for each. Cover:
   - MLS public share links from at least 5 MLSs;
   - Zillow, Realtor.com, Redfin, Homes.com, Compass;
   - Fotello and Aryeo deliveries;
   - Dropbox and Drive folders;
   - a sold and a pending listing, a dead link and an MLS sign-in link.

   Run on every change and **nightly**, because portals change their pages without warning.
2. **Stage 5 unit tests** with saved pages: every extracted value has a quote that appears on
   the page.
3. **The manual path:** address plus 14 uploads builds. 13 uploads asks for one more.
4. **Payment:** no card goes to Stripe and returns to the same step; a failed build is refunded.

---

## 10. Build split and order

**Dan, backend**

1. Stage 5 page audit, plus the `property_file` on the campaign.
2. Move a light stage 6 (gaps only) to check time; return `needs_confirmation`.
3. Outcomes `few_photos`, `other_agent` and `dead_link` in `listing_check`.
4. Store only the used photos; keep the rest as links for 30 days; a "photos from your listing"
   endpoint for swaps.
5. Refund on a failed build.
6. The link corpus and the nightly run.

**Adam, front end**

1. **Done (next PR):** the draft page with no photo box and no "Send clicks to"; approvals per
   block; listing page preview.
2. Next:
   - the check screen shows the found details ("4 bd · 3 ba · $845,000", with "please confirm"
     items);
   - the `few_photos` choice;
   - "photos from your listing" in the post editor.
