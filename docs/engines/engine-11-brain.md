# Engine 11 brain: Support

**Status:** greenlit by Adam (22 Nov) · **Builds in:** PR #36 · **Started:** 22 Nov 2026
**Existing:** Ask Resmara spec v1.0 (project `engine-specs/resmara-ask-resmara-engine-spec.md`, 15 Nov), `app/api/help.py`, `static/help-kb.js`, `static/help/resmara-guide.md`, the Support page (`supportPage` in `app.js`), tickets and `notify_operators` in `app/api/resmara.py`, the Team room Support section, the setup-session booking (`obBook` in `onboarding.js`). This brain keeps the Ask Resmara spec and adds everything around it.

---

## 1. Job

Every agent gets help the moment they need it, and a real answer from a person within **1 business
day** when the chat can't help. Three doors, one inbox:

| Door | For | Answered by |
|---|---|---|
| **Ask Resmara** (the orange robot, every page) | "How do I…?", "Why didn't my post go live?" | The AI, from the guide, the answer library and the agent's own account |
| **Support page** | Anything the chat can't settle | The team, within 1 business day |
| **Setup session** | Help connecting Facebook, Instagram and the ad account | A team member on a 30-minute video call |

Everything the team needs lands in **one shared inbox, support@resmara.com** (Adam, 22 Nov), and in the
Team room's Support section.

## 2. What exists today, and what changes

| Today | Change |
|---|---|
| Chat: library matching, "Take me there", AI step, "Send to support" | Keep |
| `/api/help/ask` answers only from the approved answers, and needs sign-in | Per the Ask Resmara spec: also the **guide** and the **agent's account snapshot**; signed-out visitors get product answers |
| The chat doesn't say it's AI | First message: "I'm Ask Resmara, an AI assistant. I can answer most questions, and I'll pass anything else to our team." (Terms §3; California's bot-disclosure law) |
| Support page: subject and message | Add **Which listing?** (optional, fills in the campaign), the **1 business day** promise, and a confirmation email |
| A new request emails each operator address, or a webhook | Send it to **support@resmara.com** (one shared inbox), plus the Team room |
| Replies show on the Support page (with a badge) | Also **email the agent** each reply, with **See the reply** |
| Statuses: as stored | Four plain ones: **Received**, **Answered**, **Waiting on you**, **Closed** |
| Setup session books the Real Estate Boost onboarding event | A **Resmara setup session** event (section 6) |
| Team room: requests, and "Questions the chat couldn't answer" | Add the **reply-by time** on each request and **Save as a chat answer** on each reply (section 7) |

## 3. Ask Resmara (the chat)

Everything in the Ask Resmara spec v1.0 stands. In short:
- Answers from **the guide** (`static/help/resmara-guide.md`), **the answer library**, **approved answers**
  and the **signed-in agent's own account** (campaigns, connection, card, failed posts, open requests).
- **Take me there** opens the exact page.
- **Read-only:** it never charges, cancels, posts or changes anything.
- **Never invents:** no answer from those sources → "I'm not sure about that one," and **Send to support**
  with the question already filled in, so they never type it twice.
- Limits: 20 questions an hour per agent, 500 characters, a daily cost cap (start at $5), library only
  beyond it.
- **Signed-out visitors** (homepage) get product answers only, never account answers.
- **New:** the first message says it's an AI assistant. When a team member replies to a request it came
  from, the reply is signed with their first name ("Adam from Resmara").

## 4. Support requests

1. **Support page:** **Which listing?** (a picker of their campaigns, or "Not about a listing"),
   **Subject**, **Message**, **Send request**. Above it: "We reply within 1 business day (Monday to
   Friday, Pacific time). Most questions are answered faster in the chat."
2. **On send:** the page shows "Got it. We'll reply by Tuesday at 5 PM," and the agent gets the same
   by email. The request carries the listing, the page they were on and the account snapshot, so the team
   doesn't have to ask.
3. **It lands** in support@resmara.com (subject "Resmara support #1046: Instagram post failed") and in the
   Team room.
4. **The team replies** in the Team room. The reply shows on the Support page and goes to the agent by
   email with **See the reply**. The status becomes **Answered**, or **Waiting on you** if the team asked
   something.
5. **The agent replies** on the Support page (or to the email, which lands in support@resmara.com and is
   added to the request).
6. **Closes itself** 7 days after it's answered with no reply from the agent ("Closed. Reply any time to
   reopen it").

**1 business day** means: a request sent before 5 PM Pacific on a business day is answered by 5 PM the
next business day. US federal holidays don't count.

**Requests Resmara opens itself** (already built for failed posts, Engine 6): they appear on the Support
page as **Received**, from "Resmara", with what happened and what's being done.

## 5. What the team sees (Team room → Support)

- **Requests**, oldest first, each with the agent, the listing, the account snapshot, and a **reply-by**
  time. Past due turns orange; due within 2 hours shows "Due soon".
- **Reply** box; **Mark closed**.
- **Save as a chat answer** on any reply: turns it into an approved answer, so the chat can answer the
  next agent who asks.
- **Questions the chat couldn't answer** (exists): most asked first, **Add an answer**.
- **Setup sessions booked**: name, time, the Meet link and the agent's setup status (Engine 1's audit),
  so whoever takes the call knows what's missing before it starts.

## 6. The setup session

- A **Calendly event, "Resmara setup session"**: 30 minutes, Google Meet, from support@resmara.com's
  calendar. Questions: phone number, "Anything we should know?".
- Booked from the sign-up tour, Accounts and the chat ("Book a free setup session"), pre-filled with the
  agent's name and email (exists).
- Booking adds it to the Team room (section 5) and to the agent's Support page as an upcoming session.
- Today's link (`SETUP_CALENDLY` in `onboarding.js`) points at the Real Estate Boost onboarding event and
  changes to the new one.

## 7. Keeping answers current

- **Any front-end change an agent can see updates the guide in the same PR** (Ask Resmara spec §11).
- Every reply the team saves as a chat answer, and every miss answered in the Team room, goes into the
  approved answers the same day.
- Once a month the team looks at the top 10 questions the chat missed and adds what the guide lacks.

## 8. Rules

1. The chat and the team see the asking agent's own account only, never another agent's.
2. Nothing secret in a request or reply: no tokens, card numbers or passwords. If an agent sends a
   password, the team says not to and asks them to change it.
3. Support never changes billing on the agent's behalf except a refund (Engine 10 §9).
4. Requests and chat questions are deleted with the account (Privacy Policy).

## 9. Setup

- **support@resmara.com:** resmara.com has no email (MX) records yet. Adam picks how the shared inbox
  works (a Google Workspace mailbox on resmara.com, or forwarding to an inbox you both read). Claude adds the
  DNS records in GoDaddy with Adam's OK. Then `MAIL_FROM` and the operator address on Render point at it
  (Dan), and the Terms, Privacy and Data Deletion pages switch from resmaraai@gmail.com to
  support@resmara.com (Adam).
- **Calendly:** Adam creates the "Resmara setup session" event; the link goes into `onboarding.js`.
- **Dan:** `/api/help/ask` per the Ask Resmara spec (guide, account snapshot, signed-out answers, log
  and cost cap); requests to the shared inbox; reply emails to agents; the four statuses and auto-close;
  reply-by times; Save as a chat answer; inbound email replies added to the request; the Calendly booking
  into the Team room.
- **Adam (front end):** the AI line in the chat, Which listing? and the promise on the Support page, the
  statuses, the upcoming setup session on the Support page.

## 10. Decided with Adam (22 Nov 2026)

- Replies within 1 business day, promised on the Support page and in the confirmation email.
- One shared support inbox, support@resmara.com, for requests, chat hand-offs and setup bookings.
- The Ask Resmara spec v1.0 stands; the chat says it's an AI assistant.

## Screens

Mockups from the preview (`engine-11-screens/`, with `mockup.js`, the preview script they were taken from). Mockups only: the brain above is what to build.

| Screen | What it shows |
|---|---|
| `01-support-page.png` | The Support page: the 1 business day promise, Which listing?, the requests with their statuses, an upcoming setup session, and the chat saying it is an AI assistant |
| `02-request-sent.png` | After Send request: "Got it. We'll reply by Tuesday at 5 PM." |

Live preview: https://claude.ai/artifact/Lip2AN9HQZuLf4J5AsP8Vy#support
