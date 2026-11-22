# Clarity screen tracking: how it's supposed to work

**What:** gives every agent screen its own heat map and recordings filter in Microsoft Clarity, so
we can see where agents get stuck on My Brand, a campaign page, Billing and so on.
**Files:** `static/screens.js` (new), one `<script>` line added at the end of `static/index.html`.
Front end only. No server change, no new keys: it rides on the Clarity tag `tags.js` already loads.

## The problem it fixes

The agent app is one page. Every dashboard screen sits at `resmara.com/#dashboard`, and Clarity
ignores everything after `#` when it decides which page someone is on. So every dashboard screen
was landing in ONE heat map.

## What happens now

On every screen change `screens.js`:

1. Adds `?screen=<name>` to the address with `history.replaceState`. Back button, refresh and the
   existing `#` routing behave as before. Clarity watches replaceState and starts a new page
   when the address changes before the `#`, so each screen gets its own heat map.
2. Sets the Clarity custom tag `screen` and sends a custom event `screen: <name>`.
3. If the agent is signed in, calls `clarity("identify", email, …, friendlyName=email)` so we can
   pull up a given agent's recordings when they contact support, and sets `signed_in` yes/no.

It works by wrapping the existing screen functions (`dashboard`, `details`, `newCampaign` …)
after they run. It never changes what they draw, and every call is in try/catch.

## Screen names (what shows in Clarity)

| Screen | Name |
|---|---|
| Homepage, How it works, Pricing, Setup guides | `home`, `how-it-works`, `pricing`, `setup-guides` |
| Confirm email, reset password | `confirm-email`, `reset-password` |
| Dashboard menu | `my-campaigns`, `my-brand`, `billing`, `accounts`, `support` |
| A campaign page | `campaign-review` (before launch), `campaign-live`, `campaign-republished`, `campaign-completed`; the starter sample is `sample-campaign` |
| Pop-ups | `sign-in`, `sign-up`, `new-campaign`, `new-campaign-pay`, `listing-website-preview` |
| Onboarding | `onboarding-connect-meta…`, `onboarding-meta-needs-setup`, `onboarding-no-facebook`, `onboarding-brand`, `onboarding-first-campaign`, `tour-step-1…` |

When a pop-up closes, the screen switches back to the page underneath it.

Campaign pages are named by **stage**, not by address, so every campaign at the same stage feeds
one heat map.

## Step events (funnels, no new heat map)

`new campaign: link checked` · `typed address instead` · `asked for photos` · `build started` ·
`campaign: post opened` · `calendar approved` · `approved` · `post withdrawn` · `report opened` ·
`report downloaded` · `leads opened` · `brand: saved` · `research again` · `font picker opened` ·
`billing: add card` · `accounts: connect meta` · `support: ticket sent` · `tour: finished`

## How Adam uses it in Clarity

- **Heatmaps:** URL *contains* `screen=my-brand` (or any name above).
- **Recordings:** filter by the custom tag `screen`, or by *rage clicks* / *dead clicks* /
  *excessive scrolling* on a screen.
- **One agent:** search recordings by their email (custom user ID).
- **Funnels / Smart events:** build from the `screen:` and step events.

## For Dan

- When a new screen or pop-up is added, add one line to `MAP` (or `STEPS`) in `screens.js`.
- If a function in the map is renamed, its tracking silently stops (wrap skips missing names).
  Nothing breaks.
- New tag values show up in Clarity's filters within about 30 minutes to 2 hours.
- Privacy: the privacy page doesn't mention Clarity, GA4 or the Meta pixel yet. It should say we
  use analytics and session recording, and that agent emails go to Clarity as a user ID.
  Clarity masks typed form fields by default. Card details stay in Stripe's own page.

Tested headless (Chromium, Clarity stubbed): each dashboard screen, campaign page and pop-up got
its own address, tag and event. No page errors.
