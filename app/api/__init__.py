from fastapi import APIRouter

api_router = APIRouter()

from app.api import auth
from app.api import resmara
from app.api import oauth
from app.api import content
from app.api import engine
from app.api import billing
from app.api import costs
from app.api import finance
# Build room: /api/admin/buildroom — who is doing what, and who has it claimed. Replaces the
# outbound ChatGPT Sites tracker: the board lives inside this console now.
from app.api import buildroom

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
# Finance: /api/admin/finance — what a campaign sells for, what it costs us, what we may spend
# to win a repeat agent, and what has actually been collected.
api_router.include_router(finance.router, prefix="", tags=["finance"])
# Build room — the claim board the console's Build room section reads and writes.
api_router.include_router(buildroom.router, prefix="", tags=["buildroom"])
