# Resmara engines: what's built, what's AI, what's missing

**Date:** 20 Nov 2026 · **Read from:** the code on `main` plus PR #17 · **For:** Adam and Dan

The short version: most of the machinery exists and much of it is real AI. But three things that
decide whether posts look good, and look like *that agent's* posts, are not built yet:

- the full brand engine;
- the themes (Modern, Classic, Rustic);
- the design step's layout library and art-director check.

Today every agent's posts are designed from **one fixed layout**, and the style research the
engine does is never handed to the step that draws the image. That's the "100 agents look the
same" risk, and it's the first thing to fix.

I can't see Render, so I can't confirm which of these are switched on live (for example whether
the OpenAI key and image model are set). The Team room **System check** shows the AI mode. Dan can
confirm.

---

## The engines, one by one

### 1. Meta integration (sign-up, connect, check, reconnect)

| Piece | Status | AI? |
|-------|--------|-----|
| Facebook login and storing the connection | Built | No |
| The four checks (Page, admin, Instagram, ad account) via Meta's API | Built (`/api/onboarding/meta-audit`) | No. Facts from Meta, which is right |
| Connection health sweep every 6 hours (expired or revoked logins) | Built (`token_health`) | No |
| Front end for every outcome: limited setup, Meta notice, Fix it now, Setup page | Built in PR #17 | No |
| "Connected" means Page-only; Instagram re-read on Check again; login recorded with no Page | **Not yet** (Dan, PR #17 notes) | No |
| A "reconnect" warning on the dashboard when the sweep finds a broken login | **Not yet** | No |
| AI that explains an unusual Meta error in plain English and picks the fix | **Not built** | Would be |

**Verdict:** mostly there. It needs the server items above and a written engine doc. That doc is
being written now, as the first engine spec.

### 2. Brand engine (learns the agent's look and voice)

| Piece | Status | AI? |
|-------|--------|-----|
| "Build from my Facebook Page": reads Page facts, suggests voice, colours, font and tagline | Built | Yes (small model) |
| Brand profile from the agent's website, used during a campaign build (R2) | Built | Yes |
| Social audit of their last 30 Instagram posts (Brand spec P2) | **Not built** | Yes |
| Full brand kit with web research: brokerage rules, licence, logo files (P3) | **Not built** | Yes |
| Onboarding Step 2 "Building your brand" | **Animation only.** It calls nothing | n/a |
| Refresh, merge, the agent's edits winning, learned rules | **Not built** | Partly |
| Font picker and theme picker on My Brand | **Front-end mock only**; the choice isn't used by any engine | n/a |

**Verdict:** the weakest link. Every post and the ad read the brand kit, and the kit is still
thin.

### 3. New campaign engine (link, photos, research, plan, design)

| Piece | Status | AI? |
|-------|--------|-----|
| Link check (opens the listing, finds photos and video) | Built, made real in PR #17 | No |
| Photo tagging: every photo (up to 60) gets a room, a 1–10 social score, and post yes/no with a reason. Clutter, dark, tilted, bathrooms, people, mess and rundown sheds are ruled out | Built | **Yes, vision model** |
| Photo ranking and picking: best score first, room priority, no repeats of a room on consecutive days, feature showcase (pool, view, shop) | Built | Rules on top of the AI tags |
| Property research on public pages (R1) | Built | Yes, with web search |
| Style research: how top brokerages post now, combined with this agent's brand (R3) | Built | Yes, with web search |
| The 14-post plan: story order, headlines, captions, hashtags, compliance rules (R4) | Built | Yes |
| Design step: listing photo plus brief, sent to the image model, then a checker re-reads the text and redoes it once | Built | Yes |
| **The R3 style recipe reaching the design step** | **Missing.** The design brief only gets the headline, caption, room, colours and one font. Layout is one fixed line: "headline in the lower third with a dark scrim" | — |
| Themes (Modern, Classic, Rustic) with style definitions and sample posts | **Not built** (Post spec §5) | Would guide the AI |
| Layout library (10–15 per theme; BAP's 7 Boost layouts as the seed) | **Not built**; the 7 layout prompts sit in the spec, unused | — |
| Art-director check (score each post, redo below the bar) | **Not built**; only the spelling check exists | Would be |
| Quiet-zone tags (where text can sit without covering the subject) | **Not built** | Would be |

**Verdict:** the planning brain is strong. The *drawing* step is generic. That's where the look
comes from, so that's where the work is.

On the "bedroom with the roll-up desk" post: the tagger already marks cluttered, dark and tilted
photos "post: no", and it used to stop after the first 12–20 photos (fixed). A real art-director
score on the *finished* post is the missing second check. It would catch a photo that passes the
tagger but still makes a weak post.

### 4. Publishing and tracking engine (once live)

| Piece | Status | AI? |
|-------|--------|-----|
| Publisher: posts approved posts on time to Facebook and Instagram | Built | No |
| Retry and blame on failures (ours vs a broken Meta login) | Built (`post_retry`) | No |
| The one Meta ad per campaign, built to the Ad spec | Built (`ad_build`) | Copy from the plan |
| Daily listing watcher: stops the ad when the listing shows pending or sold | Built (`listing_watch`) | No |
| Comment leads: reads comments and flags real buyer interest | Built (`leads`) | **Yes** |
| Post and ad numbers from Meta, never invented | Built (`insights`) | No |
| Next round learns from the last round's numbers | Built (`round_learning`) | Yes |
| Run until sold renewals | Built (`renewals`) | No |
| Listing page, website leads and call taps | Front end in PR #17; **server not built** (listing-page doc) | No |
| **The publisher only posts when the campaign's ad account is active** | **Conflicts** with "no ad account still posts". Must change | — |
| Learner from the agent's edits (Post spec §9) | **Not built** | Yes |

**Verdict:** solid and careful. Two fixes are needed: the ad-account gate in the publisher, and the
listing page server.

---

## What to fix first

1. **Give the design step real style.** Build the themes and the layout library:
   - write the Modern, Classic and Rustic definitions, with 3–6 sample posts each;
   - seed the layouts from BAP's 7;
   - pass the theme, the layout and the R3 recipe into every design brief;
   - add the art-director score.

   This is the "looks good and isn't the same as everyone else" fix.
2. **Build the brand engine for real** (Brand spec P2 and P3), and wire onboarding Step 2 to it.
3. **Font and theme pickers on My Brand that actually feed the engine.** Use Google Font
   dropdowns that preview each font, a headline font and a body font, and Modern, Classic or Rustic
   with a preview.
4. Meta integration server items (PR #17 notes) and the publisher's ad-account gate.
5. The listing page server.

## The engine docs (one per engine, written in turn)

| Engine | Doc | Status |
|--------|-----|--------|
| Meta integration | `engine-specs/resmara-meta-integration-engine-spec.md` | Being written now |
| Brand | `engine-specs/resmara-brand-engine-spec.md` | Exists (14 Nov) |
| New campaign (photos, plan, design, themes) | `engine-specs/resmara-post-engine-spec.md` + a new theme and style section | Exists; themes section to be expanded |
| Ad | `engine-specs/resmara-ad-engine-spec.md` | Exists |
| Publishing and tracking | new doc | Next after Meta |
