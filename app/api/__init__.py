from fastapi import APIRouter

api_router = APIRouter()

from app.api import auth
from app.api import resmara
from app.api import oauth
from app.api import content
from app.api import engine
from app.api import billing
from app.api import costs
# Filings: /api/admin/filings — the paperwork with a deadline on it (FBN, publication, 1065,
# 565) and what each one costs, so a window is never missed silently.
from app.api import filings
from app.api import finance
# Build room: /api/admin/buildroom — who is doing what, and who has it claimed. Replaces the
# outbound ChatGPT Sites tracker: the board lives inside this console now.
from app.api import buildroom
# Onboarding: /api/onboarding/state|meta-audit|setup-session|tour-seen — what the account has
# actually done, so the Meta gate and the Accounts page cannot be skipped by a browser.
from app.api import onboarding
# Ask Resmara: /api/help/misses|answers — the questions the chat could not answer, and the
# answers the team approved from real support replies.
from app.api import help
# The Team room: /api/admin/campaigns|posts/failed|connections|activity, /api/admin/system-check|
# releases, /api/admin/team. Each one asks app/services/team_access before it answers.
from app.api import console
from app.api import system
from app.api import team
from app.api import marketing
# The two ids a browser needs before it can be measured: /api/public/tags. Nothing secret.
from app.api import public
# Social leads (Post Engine §10.4): /api/boosts/{id}/leads and the scan the scheduler calls.
# Before this router existed the panel was a browser mockup with sample comments.
from app.api import leads
# Engine 1 Part A: "Log in with Facebook" (start -> callback -> ticket), the reversible
# "Close my account" and the one-question email ask. Before this router existed the only door
# into Resmara was email and password.
from app.api import facebook_login
# The four onboarding emails, run by the clock, plus the one-click unsubscribe they carry.
from app.api import onboarding_emails
# Terms, renewal consent and the three money emails: /api/admin/consent/reminders (the clock)
# and /api/admin/price-notice (the operator). The service behind them is app/services/consent.py.
from app.api import consent

api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(resmara.router, prefix="", tags=["resmara"])
api_router.include_router(oauth.router, prefix="/oauth", tags=["oauth"])
api_router.include_router(content.router, prefix="/content", tags=["content"])
# Campaign engine: /api/boosts/{id}/build|approve|launch, /api/adflow/credits/precheck/
api_router.include_router(engine.router, prefix="", tags=["engine"])
# Billing: /api/billing/config|checkout|webhook|orders. A campaign is $49, bought outright.
api_router.include_router(billing.router, prefix="", tags=["billing"])
# Start-up costs: /api/admin/costs — what the project cost, who paid, receipts, subscriptions.
api_router.include_router(costs.router, prefix="", tags=["costs"])
api_router.include_router(filings.router, prefix="", tags=["filings"])
# Finance: /api/admin/finance — what a campaign sells for, what it costs us, what we may spend
# to win a repeat agent, and what has actually been collected.
api_router.include_router(finance.router, prefix="", tags=["finance"])
# Build room — the claim board the console's Build room section reads and writes.
api_router.include_router(buildroom.router, prefix="", tags=["buildroom"])
# After the launch: /api/boosts/{id}/launch-details|pause|resume|ad-performance|again and the
# daily listing watcher. Everything an approved campaign needs once it is running.
from app.api import boost_control
# Ask Resmara's answer library — the chat's misses and the answers the team approved.
api_router.include_router(help.router, prefix="", tags=["help"])
api_router.include_router(boost_control.router, prefix="", tags=["campaign control"])
api_router.include_router(onboarding.router, prefix="", tags=["onboarding"])
# The Team room's data. Mounted after everything else because the paths are all under
# /api/admin/* except the help chat, and nothing here shadows an existing route.
api_router.include_router(console.router, prefix="", tags=["console"])
api_router.include_router(system.router, prefix="", tags=["console"])
api_router.include_router(team.router, prefix="", tags=["console"])
api_router.include_router(marketing.router, prefix="", tags=["console"])
# Public, unauthenticated, and safe: a GA4 measurement id and a Clarity project id are printed in
# the source of every site that uses them. The homepage fetches these to install its tags.
api_router.include_router(public.router, prefix="", tags=["public"])
api_router.include_router(leads.router, prefix="", tags=["leads"])
api_router.include_router(facebook_login.router, prefix="/auth", tags=["facebook login"])
api_router.include_router(onboarding_emails.router, prefix="", tags=["onboarding emails"])
api_router.include_router(consent.router, prefix="", tags=["consent"])
