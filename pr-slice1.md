**Ready for Dan: slice 1, sign-up to first campaign.** Engines 1 (Parts B and C), 2, the sign-up tour, 3 and 4, built end to end from their newest brains: server, screens, tests and help guide. Engine 1 Part A (your Facebook door from today) is untouched and is what this builds on.

The brain-vs-code audit this started from is in `docs/engines/slice-1-audit.md`. One PR rather than five because the pieces depend on each other (the sign-up screens read the Meta engine, the brand engine and the unlock rules). Each engine is its own commit, so it reads in order.

## What's in it

**Engine 1, Parts B and C: the Meta connection** (`app/services/meta_engine.py`, new `meta_connections` table)
- One connection per agent, saved on every Facebook login (with or without a Page or ad account) and overwritten on every reconnect and Check again. This fixes all five "fix first" items: no ad account still saves the Page and Instagram; reconnect updates them; the Page is chosen, not guessed; posting never needs an ad account; "connected" means a Page.
- Checks C1-C7 straight from Meta, and the fixed outcome table from the spec (every key with its line, what the campaign can still do, and Fix it now), at most three lines.
- Which Page is your business? / Change Page (`POST /api/onboarding/meta-page`). One Page, one Resmara account.
- A broken login holds due posts instead of failing them. Reconnecting sends them; anything held over a day is never sent late. With no usable Page, download mode sends nothing.
- Re-checks: every sign-in (10-minute cache), Check again, before posting, and the existing `/meta/check-all` sweep for agents with live campaigns. Breakage emails go out once, then on days 3 and 7. The 5% alert goes to the first `RESMARA_ADMIN_EMAILS`, at most once a day.
- `/api/onboarding/meta-audit` keeps its four-line `checks` shape, now from real answers with names and photos, plus the full status.

**Engine 2: the brand engine** (`app/services/brand_investigator.py`)
- Runs in the background from the Facebook sign-in. It reads the Page facts from the connection and the agent's website, then does a web search (Responses API with `web_search`) across Google, the brokerage, the state license lookup, YouTube, Zillow and Realtor.com.
- Facts that print on posts need a source or stay empty. Missing ones are asked for on + Campaign.
- The Voice of the client paragraph (persona, never personal; positive only) is read by the post writer on every build. My Brand gains phone and broker license fields, where each fact was found, and a real Research again (`POST /api/auth/me/brand/research`).
- The agent's edits are remembered and always survive Research again. A brand typed before this existed is kept as theirs.

**Sign-up tour** (`static/signup.js`, loaded last)
- The live checklist after Log in with Facebook, then the finish pop-up, the tour (anything to set up first, then the look around, ending on Let's start your first campaign) and the setup plan (Check again asks Meta and ticks in place).
- The Accounts "Your setup" box, the Meta notice from the server's lines, and Fix it now routing.

**Build first, then pay to unlock** (`app/api/billing.py`)
- The build no longer asks for a card. A built, unpaid campaign is locked: review, approval, posting and launch answer 402 `locked`, and the posts list gives three pictures for the blurred preview.
- One locked campaign at a time (409 `unlock_first`).
- A saved card is charged as soon as the build finishes. Stripe Embedded Checkout (`ui_mode=embedded`) is in the card, with Save this card mapped to `setup_future_usage`. `GET /api/billing/checkout/{id}/status` settles straight away and shares one settle step with the webhook.

**Engine 3: the listing link**
- Any link identifies the house. The research then builds the home's file from every source (added beside the pinned R1 prompt, not inside it).
- Short of 14 photos, the bigger gallery between the link and the address lookup wins.
- 14 photos are required. The form nudges toward the photographer's link, and the build button has no price.

**Engine 4: the campaign build** (`app/services/post_rules.py`, `ad_hooks.py`, `ad_rulebook.py`, `static/campaign-build.js`)
- Hashtags: Instagram 3-5, Facebook 0-2, rotated. Instagram captions never carry a link. Posting times follow the audience, only 6 AM-11 PM local.
- The story arc and six post styles (Your look is gone from My Brand), with variety rules, liked posts as references, and the Art Director score in the checker.
- A post that still fails gets a code-drawn fallback design flagged Needs a look: never a plain photo.
- The ad: up to 3 hook versions checked against the rulebook, drawn in 4:5 and 9:16. Placements include Marketplace, Stories and Reels, and the ad never runs 11 PM-6 AM (`adset_schedule`).
- 👍/👎, server-saved edits with Fair Housing on every edit, photo swaps that redraw the post, the Gallery view, and What Resmara learned about you.

**Three existing bugs this fixes**
1. Post times were saved as `09:00`/`19:00` with no time zone, but the publisher compares against `utcnow()`. A "9 AM" post went out around 1 AM Pacific. They're now stored in UTC for the listing's local hour.
2. The publisher appended the hashtags to captions that already ended with them, so every post went out with its tags twice.
3. A caption edited in review was only saved in the browser, so the server published the original. Edits now save on the server.

## Dan's build list

1. **Review and merge.** CI runs the suite. New tests: `test_meta_engine`, `test_brand_investigator`, `test_unlock`, `test_engine3_listing_link`, `test_engine4_rules`, plus `test_signup_flow.js` and `test_campaign_build.js` (added to `scripts/run_tests.sh`). Locally everything passes except `test_team_room`, which fails the same way on main whenever a GitHub token is in the environment.
2. **Migrations run on boot.** The new `meta_connections` table is created, seven `posts` columns are ALTERed in, and there's a unique index on `meta_connections.page_id`. Checked against an existing database: "7 columns added".
3. **Image model.** The default is now `gpt-image-2.6-sunburst` (confirmed on OpenAI's model page). If `RESMARA_MODEL_DESIGN` is set on Render, update it or remove it.
4. **Stripe Embedded Checkout.** It uses the existing keys. Check that the live domain is allowed for embedded Checkout in the Stripe Dashboard if it asks. The hosted page still works for old links.
5. **Scheduler.** `/api/oauth/meta/check-all` now also runs the full connection check for agents with live campaigns. No new job is needed.
6. **`FB_LOGIN_SCOPES`.** Once App Review approves the Page, Instagram and ads permissions, set the Facebook login to ask for them. Until then an agent sees "Resmara needs your permission to post to your Facebook Page" with Fix it now, which opens Connect Meta.
7. **Slice 2 carry-overs (Engine 6):** launching the 3 hook versions (and the video ad alongside the static ones) from `plan.ad.hooks`, fixing and resubmitting a rejected ad once, and comment leads from the Instagram invitation ("Comment TOUR").

## Needs a person (not code)
- The Facebook login return address (`https://www.resmara.com/api/auth/facebook/callback`) in the Meta app's Valid OAuth Redirect URIs (Adam).
- Meta App Review for the Page, Instagram and ads permissions.
- The Resmara setup session event in Calendly. `SETUP_CALENDLY` still points to the Real Estate Boost session.
- Turnstile keys. The trend brief's engagement numbers need Business Discovery.
- Adam's gold set for the Art Director, and the image-model bake-off.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

https://claude.ai/code/session_01Dh4Jk6ixVzuRZDPBUadB1y
