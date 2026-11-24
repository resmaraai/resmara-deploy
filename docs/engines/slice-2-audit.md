# Slice 2 audit: the brains vs the code (23 Nov 2026, 5 PM)

**Slice 2 = the live campaign:** Listing website (Engine 5), Live campaign (Engine 6), Run it until
it sells (Engine 8). Read on top of the slice 1 branch (PR #39).

**Key:** ✅ in the code · 🟡 partly · ❌ missing

## Listing website (Engine 5): the page design exists, nothing is served

| Brain decision | Status | Where / what's wrong |
|---|---|---|
| A page per home at `homes.resmara.com/<street>` | ❌ | no `listing_sites` table, no public route |
| Slug from the address by code, never changes, `-city` / `-2` on a clash | ❌ | |
| Served as finished HTML with a share card (title, hero, price) | ❌ | `listing-site.js` draws in the dashboard only |
| Brand kit snapshot, story in 4 chapters, facts band, gallery, contact, footer | 🟡 | the template exists in `listing-site.js`; no story chapters |
| Built in the same build as the campaign | ❌ | |
| Section 3 "Your listing page": Preview, Copy link, Share | 🟡 | front end exists, no real link |
| Leads: form (emailed within a minute), call taps, text taps | ❌ | no public lead endpoints |
| Visits and which post/ad sent them | ❌ | |
| Price only when sources agree; hidden on a change; one email with Set a new price / Don't show a price | ❌ | |
| Pending/Sold banner; Schedule a showing becomes Ask about similar homes | ❌ | |
| Ended: stays 30 days, then the agent card only | ❌ | |
| Photos through the app from R2 (`homes.resmara.com/photos/…`) | ❌ | R2 exists in `storage.py` |
| Daily check that every live page loads | ❌ | |
| DNS (`homes` CNAME) | ✅ | done 22 Nov; Render custom domain is Dan's |

## Live campaign (Engine 6): the core runs; the brain's new rules are mostly missing

| Brain decision | Status | Where / what's wrong |
|---|---|---|
| Launch: Housing, 15 miles, lifetime budget, runs as the agent | ✅ | `launch.py`, `ad_build.py` |
| No ad delivery 11 PM-6 AM, all placements | ✅ | slice 1 |
| The ad's 3 hook versions (+ the video ad alongside) launched in one ad set | ❌ | one ad today; hooks are built in slice 1 |
| Clicks go to the listing website with tracking tags | 🟡 | UTM tags exist; the website doesn't |
| Facebook caption with the website link, Instagram with none | 🟡 | no link yet (no website) |
| Couldn't post, Withdraw post | ✅ | `post_retry.py`, withdraw |
| **Live ad audit** several times a day (delivering, rejected → fix and resubmit once, pacing, weak hook swap, frequency, website up) and the audit log | ❌ | |
| Comment leads every 15 min, no automatic replies, email the agent | ✅ | `leads.py` |
| Pending/sold: read the status field across sources, self-healing, hourly | ❌ | word-matching every 6 hours on one link |
| On pending/sold pause the ad **and the posts** | 🟡 | pauses the ad only; posts keep going out |
| Pending email with Turn it back on; no email on Sold | ❌ | no email |
| Keep checking paused pending listings; fell through with the same listing agent → email | ❌ | paused campaigns are skipped |
| Pause pop-up: Just pause it / It's pending / It sold / Keep running | ❌ | plain pause |
| The agent's own Page/Instagram posts read daily for pending, sold, price change | ❌ | |
| Pending vs Sold as separate states on the card | ❌ | |
| Resume gives back the paused days | ✅ | `boost_control.py` |
| Reports day 7 and 14, PDF | ✅ | `report_pdf.py` |
| Agent report vs seller version (no cost or spend anywhere) | ❌ | one report, shows ad spend |
| Reports emailed when ready | ❌ | |
| Scheduler on Render | ✅ | `render_clock.py` cron (listing check every 6 h → brain says hourly) |

## Run it until it sells (Engine 8): rounds run; order and emails are wrong

| Brain decision | Status | Where / what's wrong |
|---|---|---|
| Build first, charge only when the build succeeds | ❌ | `renewals.py` charges, then builds |
| Round approved automatically, goes live day 15 | ❌ | needs approval |
| Declined: retry daily up to 3 times, then email with Check billing; continue when a card works | 🟡 | retried daily, no email, no cap |
| Pending pauses and it stays on; back on market (same agent) picks up; Sold ends it | ❌ | turns itself off |
| Never repeats angles; leads with unused photos; new hooks | 🟡 | `round_learning.py`; hooks are new (slice 1) |
| Validated price change worded "Improved price", never a number | ❌ | |
| Emails: renewed, pending, back on market, declined, report ready | ❌ | |
| Run it again · $39: day 12 email and on completion | 🟡 | the button exists; no emails |
| Safety limit 3 renewals per run | ✅ | |

## Build order

1. Engine 5's server: `listing_sites`, the public page and photos, leads, visits, the share card, built with the campaign.
2. Engine 6's listing check rebuilt (status field, sources, hourly, pauses posts too, pending/sold states, emails, fell through), the Pause pop-up, the seller report.
3. Engine 8 reordered (build then charge, auto-approve, pending stays on), declines and emails.
4. Engine 6's hook versions at launch and the live ad audit.
