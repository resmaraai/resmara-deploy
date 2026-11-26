# Engine 1 brain: Login and Meta integration

**Status:** greenlit, sent to Dan and merged (PR #18, 22 Nov) · **Started:** 21 Nov 2026
**Changed 22 Nov, after the merge:** Facebook is the only way in, and there are no teams or
brokerage accounts (see Part A, 10b). These changes ship in the Resmara sign-up tour engine's PR.
**Technical doc (what exists today):** `engines/login-engine.md` · **Meta spec:** `engine-specs/resmara-meta-integration-engine-spec.md`

Engine 1 has two halves that run back to back:

- **Part A: Account.** Getting a visitor into a Resmara account fast, safely, and looked after.
  (Written below.)
- **Part B: Meta connection.** Linking Facebook, Instagram and the ad account, and knowing what
  works. (Written below.)
- **Part C: The audit.** What Resmara looks at the moment they connect, and how it tells them.
  (Written below.)

---

## Part A: Account

### 1. Job

Turn a visitor into a signed-in agent in as few steps as possible, keep bots and fake accounts
out, and start looking after every new agent from minute one. Ends when the agent is signed in
and handed to Part B (Meta connection).

**Principle:** get them in fast. Ask only what we can't do without. Everything else (brokerage,
license, phone) comes later, from Meta and My Brand.

### 2. Ways in

**One way in: Continue with Facebook** (Adam, 22 Nov). Resmara runs everything through Meta, so a
Facebook account is required. A personal account is fine; a business Page is not needed to sign up.

- **One door for new and returning clients.** The top-right **Client Login** and the homepage's
  **Let's get started** open the same pop-up, "Log in with Facebook". If that Facebook account is
  already on Resmara it signs them in; if not, it creates the account and starts the Meta
  connection in the same step.
- **Agreeing to the Terms (Adam, 22 Nov; Terms §1 and §17).** In the "Log in with Facebook" pop-up,
  above the Facebook button: an **unticked** box, "I agree to the Terms of Service and Privacy
  Policy, including the arbitration agreement and class action waiver in section 17 of the Terms",
  with both links. The Facebook button stays disabled until it's ticked. Only new accounts see it;
  returning clients see it again only when the Terms version changes (a pop-up on next sign-in).
  The server records the version, time, IP and browser on the account **before** the Facebook
  redirect, and refuses to create an account without it. (The email sign-up form has this box now,
  sending `terms_accepted` and `terms_version`.)
- **No Facebook account:** "You'll need one to use Resmara. It's free: create one on Facebook,
  then come back here."
- **No email and password sign-up, and no Google sign-in.**
- No phone number and no brokerage at sign-up: either one makes people stop.
- If Facebook doesn't give us an email (some accounts hide it), ask for it once, then confirm it.
  The email is for receipts and updates, not for signing in.
- The Facebook window asks for everything at once: name and email, plus the Page, Instagram and
  ad permissions. Those last three need Meta App Review. Until it's approved, Facebook sign-up
  creates the account from name and email, and a short Connect step follows; once approved,
  that step disappears with no extra build.

### 3. Keeping bots out

All of these, quietly, without slowing a real person down:

1. **Invisible bot check** on the log-in pop-up (Cloudflare Turnstile: free, usually no puzzle
   for a real person).
2. **Real Facebook accounts only.** Every sign-in is confirmed by Meta.
3. **Limits on tries:** too many sign-ups from one place and it waits.
4. **Beta invite code (optional switch).** While it's on, sign-up asks for a code we hand out
   (for example to Founding Agents or a coach's group). No code, no account. Turn it off for
   public launch. *Already built on the server (`RESMARA_SIGNUP_CODE`); needs the sign-up screen
   to show the field when it's on.*
5. **No campaign without a card and a real Facebook login.** A bot can't spend money or post,
   because a campaign needs a confirmed card and a real Meta connection.

### 4. One person, one account (no teams)

- **Every account is one agent**: the one who signs in with their Facebook, pays and approves
  campaigns. No teams, no team members, no brokerage accounts (Adam, 22 Nov).
- If a brokerage wants to pay for an agent, the agent pays and gets reimbursed by their brokerage.
  A brokerage solution is **phase 2**, after launch.
- **One Facebook Page, one Resmara account.** A second account that tries to connect a Page
  already connected elsewhere is blocked (Part B).

### 5. Closing and coming back

Two different things, kept apart:

| Action | What happens | Coming back |
|--------|--------------|-------------|
| **Close my account** | Signs them out everywhere, stops anything scheduled, stops all emails. Their campaigns, leads and reports are kept. | Logging in says **"This account has been closed. Would you like to reactivate it?"** One click brings it all back. |
| **Delete my data** | Permanent: personal details, brand kit, Meta connection and tokens are removed (their legal right, and Meta requires it). Payment records are kept, as the law requires. | Can't be undone. They'd sign up fresh. |

*Today the site only has the permanent version (called "close"). It needs splitting into these two.*

### 6. Looking after every new agent (onboarding emails)

> **Changed 25 Nov (Adam):** these emails move to Mailchimp (Engine 9, "Welcome and check-ins")
> so every one is tracked. The app sends them only until Mailchimp is connected.

From **support@resmara.com**, written as **Adam, Resmara's customer support**. Personal, short,
one clear next step. AI writes each one from the agent's real account facts.

| When | Email | What the AI looks at |
|------|-------|----------------------|
| **Right after sign-up** | Welcome: "Hi, I'm Adam. Thanks for joining Resmara…", what to do first, and a link to book a call | Their name and how far they got (Meta connected or not) |
| **Day 3** | Check-in that matches where they are (below) | Their whole account |
| **Day 7** | Only if no campaign has launched yet: a short nudge on the one thing still in the way, with a link to book a call | Their whole account |
| **Day 14** | Only if still no campaign: a last friendly note ("I'm here when you're ready"), then the emails stop | Their whole account |

**The emails stop as soon as their first campaign launches.** From then on the campaign itself
sends their updates. Four emails at most, over two weeks, which is the usual pattern for apps
like this: enough to help, not enough to annoy.

**The day-3 check-in picks one situation** (the first that's true):

1. Hasn't logged in since signing up → "Looks like you haven't been back yet. Need a hand getting started?"
2. Meta not connected → "Connecting Facebook is the one step left. It takes two minutes, or I can do it with you."
3. Meta connected but something's missing (no Page, no ad account, personal Instagram) →
   names the exact thing, links the setup guide, offers a quick call.
4. Everything ready but no campaign yet → "You're all set. Paste a listing link and Resmara builds the whole campaign."
5. Campaign staged but not launched → "Your campaign for 905 Laurel Bend is built and waiting for you."
6. Campaign running → "Your campaign is live. Here's how it's doing so far" (lead count, reach).

**Guardrails for these emails**

- The AI only says what's true in their account. It never guesses or makes promises.
- It always picks one of the situations above. If the facts don't match any, it sends the plain welcome-style check-in.
- No sales pressure, no discounts unless a promo is actually running.
- Never sent to test accounts, closed accounts, or anyone who unsubscribed. Every email has an unsubscribe link.
- One email per step, never twice.
- Replies go to support@resmara.com and land in Support in the Team room.

### 7. Who gets told

- **Every new sign-up: Adam gets an email**, with their name, email and whether Meta connected.
  Nothing else (no Google Chat, no new Team room list; they already show in Accounts).
- If sign-ups ever get busy enough to be noise, Adam can switch it to one daily summary.
- Test accounts never trigger the email.

### 8. What the AI does in Part A

| Job | Given | Must return | Guardrail |
|-----|-------|-------------|-----------|
| Write the welcome email | Name, Meta status | Subject plus a short email in Adam's voice | Facts only; fixed links (book a call, setup guides) inserted by the system, never invented |
| Pick and write the day-3 check-in | The account facts (log-ins, Meta checks, campaigns, leads) | Which situation (1 to 6) plus subject and email | Must name a listed situation; if not, the plain check-in |
| Write the day-7 and day-14 notes | The same account facts | Subject plus a short email, or "skip" if a campaign has launched | Never sent once a campaign has launched |

Everything else in Part A (who you are, bot checks) is decided by code, never by AI.

### 9. Outcomes (what the agent sees)

| Situation | Message |
|-----------|---------|
| New, logged in with Facebook | Straight into the audit (Part C) |
| Returning, logged in with Facebook | Straight to their dashboard |
| Facebook log-in hid the email | "One more thing: what email should we use for your receipts and updates?" |
| No Facebook account | "You'll need one to use Resmara. It's free: create one on Facebook, then come back here." |
| Bot check failed | "We couldn't confirm you're a person. Try again." |
| Beta code missing or wrong | "Resmara is invite-only right now. Enter your invite code." |
| Closed account logs in | "This account has been closed. Would you like to reactivate it?" |

### 10. How we'll know it works

- Sign-up to first sign-in: under a minute.
- The same Facebook account logging in twice gets the same Resmara account, never a second one.
- A scripted bot run can't create accounts (bot check plus limits).
- Close, then reactivate: everything is back. Delete: personal data gone, payments kept.
- The day-3 email picks the right situation for each test account setup, and never emails a
  test or closed account.
- An account that launches a campaign gets no day-7 or day-14 email.

### 10a. Decided with Adam (21 Nov 2026)

- Onboarding emails: welcome, day 3, day 7 and day 14, stopping as soon as a campaign launches.
- Sign-up alerts: an email to Adam for every sign-up.
- No Google sign-in (22 Nov).

### 10b. Changed with Adam (22 Nov 2026, after PR #18 merged)

- **Facebook only.** A Facebook account is the gate to sign up; the email and password way in
  is removed. One "Log in with Facebook" pop-up for new and returning clients.
- **No teams and no brokerage accounts.** One agent per account. Brokerages that want to pay can
  reimburse the agent; a brokerage solution is phase 2, after launch.
- Both ship in the Resmara sign-up tour engine's PR.

---

## Part B: Meta connection

The full technical detail is already written in the Meta spec
(`engine-specs/resmara-meta-integration-engine-spec.md`, 20 Nov). This part is the short
version of what it must do, so Adam can greenlight it. Dan builds from the spec.

### 1. Job

Link the agent's Facebook, Instagram and ad account, know for certain what works, and get them
posting with whatever they have. Ends when Resmara knows exactly what a campaign can do for
this agent. Then the Brand engine takes over.

**Principle:** only a Facebook login is required. Anything missing limits the campaign; it
never locks the agent out.

### 2. What the agent can do with what they have

| They have | Their campaign can |
|-----------|--------------------|
| Everything (Page, business Instagram, ad account with a card) | Post to Facebook and Instagram, and run the ad |
| Page, no business Instagram | Post to Facebook and run the ad |
| Page, no ad account (or no card on it) | Post to Facebook and Instagram, no ad |
| Facebook login but no usable Page | **Download mode**: everything is built, they download and post it themselves |
| No Facebook at all | Can't sign up: "You'll need a Facebook account to use Resmara" |

The price is the same either way. Nothing here touches billing.

### 3. How it decides

- Every fact comes **straight from Meta**: the login, the Page, posting rights, whether the Page
  is published, the Instagram link, the ad account and its card. **AI never decides any of it.**
- The answers turn into one result from a fixed list (19 situations in the spec), each with one
  plain message and one **Fix it now** button.
- More than one problem: at most three lines, the most important first. Fix it now opens the
  first.
- If they have several Pages, one question: **"Which Page is your business?"** They can change
  it later in Accounts.
- **One Page, one Resmara account.** If a Page is already connected to another account, it's
  blocked: *"This Page is already connected to another Resmara account. If that account is
  yours, log in with the Facebook you used for it. If not, contact us and we'll sort it out."*
- **Brokerage-owned ad accounts:** if Meta lets us see and use the agent's ad account (even one
  owned by their brokerage's business account), it just works. If not, it's treated like no ad
  account: posts still go out, the ad is off, and they're offered the setup guide and a call.

### 4. Watching after sign-up

Connections break (passwords change, logins expire, ad accounts get disabled), so Resmara
re-checks:

- on every log-in;
- every night, for anyone with a live campaign;
- right before every post and every ad launch;
- whenever they press **Check again**.

If the connection breaks, due posts are **held, not lost**. Reconnecting (two clicks) sends
them. Past posts are never sent late.

### 5. Fixing

- **Fix it now:** one orange button that opens the single most useful fix.
- **Reconnect** and **Change Page** in Accounts.
- A setup guide for every problem, and **Book a call** always there.
- Emails only for things that break **after** onboarding while a campaign is live (login
  expired, ad account disabled or unpaid, lost Page control): once when it happens, then on
  days 3 and 7 if it's still broken. Never for things they already saw at sign-up.
- Adam gets told if more than 5% of live agents lose their connection at once (that's usually a
  Meta app problem, not the agents).

### 6. Guardrails

- Never show a fact Meta didn't give us. If Meta can't say why Instagram isn't linked, the
  message covers both cases: "Your Instagram isn't connected as a business account."
- If Meta is down, nothing changes for the agent and no alarm is shown. Resmara retries quietly,
  and only the Team room hears about it after 6 hours.
- Login tokens are stored encrypted, never shown, never emailed.
- Facebook log-in from Part A and Connect Meta are the same connection, never two.

### 7. What the AI does in Part B

| Job | Given | Must return | Guardrail |
|-----|-------|-------------|-----------|
| Explain a Meta error we haven't seen before | The error and their current checks | The closest situation from the list, plus one plain line | Must be from the list; if not, treated as "Meta unreachable" |
| Answer Meta questions in Ask Resmara | Their current result and last check | Their answer and the right button | Only their real situation, never a generic article |
| Weekly review (for Adam and Dan, not live) | The week's new errors and call notes | Suggested new situations or better wording | Nothing changes until Adam and Dan approve |

**The weekly review: where it's kept and how you see it**

- **Kept:** every Meta error the fixed list didn't recognise is saved in the existing event log,
  with the agent, the raw error and the situation the AI filed it under. Setup-call notes come
  from Support. Each Monday the review is saved as one record: the week, what it found, and its
  suggestions, each marked waiting, approved or declined.
- **Seen:** a **Weekly Meta review** card in the Team room's **System check**, plus a Monday
  morning email to Adam with the headline and a link to the card. Each suggestion shows how
  many agents it affected, an example, and **Approve** or **Decline**.
- **What approving does:** the suggestion goes on Dan's list to add to the fixed list (a new
  situation or better wording) in the next release. Nothing changes for agents until it ships.

### 8. Fix first (what's wrong on the live site today)

1. An agent with no ad account gets nothing saved, so no Page or Instagram either.
2. Reconnecting never updates the Page or Instagram, so a wrong pick is stuck forever.
3. The Page is guessed from the ad account's name, not chosen.
4. Posting is refused without an active ad account.
5. "Connected" means "has an ad account" instead of "has a Page".

### 9. How we'll know it works

- Each of the 19 situations shows the right message and the right Fix it now.
- An agent with no ad account still posts to Facebook and Instagram.
- Reconnecting changes the Page and picks up a newly linked Instagram.
- A second account can't connect a Page that's already connected; it sees the "already
  connected" message.
- A broken login holds posts; reconnecting sends them; nothing past-due goes out late.
- Meta's own test users (all set up, no ad account, no Page, personal Instagram, no card) all
  pass before every release that touches this engine.

### 9a. Decided with Adam (21–22 Nov 2026)

- Same Page, two accounts: blocked, with "If that account is yours, log in with the Facebook you
  used for it. If not, contact us." (22 Nov: no teams, so no "add you to their team".)
- Brokerage-owned ad accounts: used if Meta lists them; otherwise no ad, plus the setup guide
  and a call.

---

## Part C: The audit

The audit is the agent's first real moment with Resmara: right after the Facebook login it looks
at everything they have and tells them, in plain words, what's ready and what isn't.

### 1. Job

Show the agent exactly what they already have connected, by name, and the one thing to do next.
Then hand what it found to the Brand engine, so nobody has to type what Meta already knows.

### 2. When it runs

- **Straight after Continue with Facebook** (Part A). Sign-up and audit are one step, so a
  Facebook sign-up never sees a separate "Connect Meta" screen.
- Again whenever they press **Check again** or **Reconnect**, and quietly on the schedule in
  Part B, section 4.

### 3. What it sees (all from Meta, nothing guessed)

| Looks at | What it reads |
|----------|---------------|
| Their Facebook login | Name, and which permissions they ticked or unticked |
| Every Page they manage | Name, profile photo, published or not, whether they can post to it |
| Instagram on each Page | Handle, profile photo, business account or not |
| Their ad accounts | Name, active or not, card on file, who owns it (them or a brokerage) |

**Also picked up for the Brand engine** (read once here, not asked again): the Page's
website, phone, address, category and About text. The Brand engine decides what to do with it.

### 3a. How it decides what's broken (rules, not AI)

Seven yes-or-no questions to Meta. A "no" becomes one of the 19 known situations (Part B), each
with its message, what the campaign can still do, and what Fix it now opens.

| # | Asks Meta | Passes when |
|---|-----------|-------------|
| 1 | Is the login valid? | Yes, and not about to expire |
| 2 | Which permissions were ticked? | The posting ones |
| 3 | Which Pages do they manage? | At least one |
| 4 | Can they post to that Page? | They have posting rights |
| 5 | Is the Page published? | Yes |
| 6 | Is a business Instagram linked to the Page? | Yes |
| 7 | Is the ad account active, with a card? | Both |

Ranked: login, then Page, then Instagram, then the ad. Same answer every time, instant and free.

### 4. What the agent sees

A short live checklist while Meta answers, each line ticking as its answer comes back:

1. Signing you in with Facebook
2. Finding your Facebook Page
3. Checking your Instagram
4. Checking your ad account

Then a result screen that **names what it found**, with photos, not codes:

> **Here's what we found**
> ✓ **Facebook Page:** Adam French Realty (photo)
> ✓ **Instagram:** @adamfrenchrealty (photo)
> • **Ad account:** Adam French Realty, needs a payment method

*22 Nov: this result screen is replaced by the sign-up tour engine's finish pop-up (their brand
and Facebook status, information only, with Show me around). Anything that needs fixing is
handled in the tour.*

| Result | Headline | Buttons |
|--------|----------|---------|
| Everything works | "You're all set. Resmara can post and run your ads." | **Build my brand** |
| Works, with limits | "You're ready to go. A couple of things will make it better." Each limit says what it means ("No ad until your ad account has a payment method") | **Build my brand** · Fix it now |
| No usable Page | "Resmara can build everything, but can't post for you yet." Download mode explained in one line | **Fix it now** · Book a call · Continue anyway |
| Several Pages | "Which Page is your business?" (photos and names, "has Instagram" tag) | Pick one, then the result |
| Page already used by another account | The "already connected" message from Part B | Log in with a different Facebook · Contact us |

**Rules for this screen**

- The agent is never stopped by anything except having no Facebook at all. They can always
  carry on to the Brand step.
- At most three things to fix are shown, most important first, each one line, with one
  **Fix it now** for the first.
- **Book a call** is always on the screen when anything is missing.
- The same list lives in **Accounts** afterwards, with the time it was last checked,
  **Check again**, **Reconnect** and **Change Page**.

### 5. How it talks to the agent

- Plain words about *their* things: "Your Page Adam French Realty", never an ID number or a
  Meta error code.
- It says what a problem means for the campaign, not just that it's a problem.
- If Meta doesn't answer a check, the line says "We couldn't check this right now" and
  **Check again**. Never a false tick, never a false alarm.
- What's missing feeds the onboarding emails in Part A (day 3, 7, 14), so the follow-up names
  the exact thing still in the way.
- You (Adam) see the same result for every agent in the Team room, under Accounts.

### 5a. The setup to-do list

What the audit finds missing becomes the agent's **setup to-do list**: one list, kept on their
account, that everything else reads.

- **What's on it:** one item per thing that isn't working, in order of importance (login, then
  Page, then Instagram, then the ad account), each with what it means for their campaign,
  **Fix it now** and **Book a call**. Done items stay below with a tick and when they were done.
- **How items tick off:** never by hand. The next check that passes (log-in, Check again,
  the nightly check, or before a post) ticks it off and records when. If something breaks later,
  it comes back onto the list.
- **Where the agent sees it:** **Accounts → Your setup** ("One thing left to set up"), with the
  last-checked time, **Check again** and **Reconnect**. The dashboard notice shows the top three.
- **What else reads it:** the day 3, 7 and 14 emails (they name the first open item), Ask Resmara
  (answers from it), and the Team room (each agent's list under Accounts, plus how many agents are
  stuck on each item).
- **Where it's kept:** on the agent's Meta connection record (its list of current issues), with
  the date each item was found and fixed. No separate system.

### 6. What the AI does in Part C

Nothing. Every line is a Meta answer and every message comes from the fixed list. (The AI only
helps when Meta returns an error we haven't seen, as in Part B.)

### 7. What's wrong today

- The audit only has four lines and reads them from the ad account record, so an agent with no
  ad account looks like they have nothing.
- It shows Page and Instagram **ID numbers** instead of names and photos.
- "You are an admin of that Page" isn't actually checked; it just copies the Page line.
- The step 1 checklist ("Checking your setup") plays from preview data; on the live site it needs
  to tick from Meta's real answers as they come back.
- Nothing from the Page (website, phone, address) is passed on to the Brand engine.

### 8. How we'll know it works

- A Facebook sign-up goes from the login to the result screen with no other step.
- The result screen shows the real Page name, Instagram handle and ad account name, with photos.
- Each of Meta's test users (all set up, no ad account, no Page, personal Instagram, no card,
  several Pages) gets the right headline and buttons.
- The Brand step opens with the Page's website and phone already filled in.
- The Accounts list matches the result screen, and Check again updates it.
- Fixing something in Meta ticks it off the to-do list on the next check, with the time, and the
  day 7 email no longer mentions it.
- The Weekly Meta review card shows last week's unknown errors, and Approve puts a suggestion
  on Dan's list.

## Screens (what it should look like)

*22 Nov: screens 1 and 7–10 are replaced by the sign-up tour engine (Facebook-only log-in, and the finish pop-up instead of "Here's what we found"). See `resmara-signup-tour-engine.md`.*

From the clickable mockup Adam reviewed on 22 Nov (`engine-1-screens/mockup.js`, preview only, not
for deploy). Facebook's own window is drawn to show the journey; the real one is Facebook's.

1. **Create your account: Facebook first, email as the fallback**
   ![Create your account: Facebook first, email as the fallback](engine-1-screens/01-create-account.png)
2. **Facebook's window: Continue as Jamie?**
   ![Facebook's window: Continue as Jamie?](engine-1-screens/02-facebook-continue-as.png)
3. **Facebook's window: choose the Page, Instagram and ad account**
   ![Facebook's window: choose the Page, Instagram and ad account](engine-1-screens/03-facebook-choose-access.png)
4. **Facebook's window: review what Resmara can do**
   ![Facebook's window: review what Resmara can do](engine-1-screens/04-facebook-review-permissions.png)
5. **Facebook's window: linked**
   ![Facebook's window: linked](engine-1-screens/05-facebook-linked.png)
6. **Back in Resmara: account ready, the audit checklist ticking**
   ![Back in Resmara: account ready, the audit checklist ticking](engine-1-screens/06-checking.png)
7. **Here's what we found: everything set up**
   ![Here's what we found: everything set up](engine-1-screens/07-found-all-set.png)
8. **No ad account**
   ![No ad account](engine-1-screens/08-found-no-ad-account.png)
9. **Personal Instagram**
   ![Personal Instagram](engine-1-screens/09-found-personal-instagram.png)
10. **No Facebook business Page (download mode)**
   ![No Facebook business Page (download mode)](engine-1-screens/10-found-no-page.png)
11. **Two Pages: which Page is your business?**
   ![Two Pages: which Page is your business?](engine-1-screens/11-which-page.png)
12. **Page already on another Resmara account**
   ![Page already on another Resmara account](engine-1-screens/12-page-already-connected.png)
13. **Accounts: the setup to-do list**
   ![Accounts: the setup to-do list](engine-1-screens/13-accounts-setup-todo.png)
