"""Ad spend, visitors and heat maps: what the readers do with a key, and without one.

Why this file exists: three third-party numbers the console previously could not show at all. The
rules that matter are (a) with a credential the page gets the real number, (b) without one it gets
a sentence naming the env var, never a zero and never a 500, and (c) a third party that errors is
a warn, not a crash. All HTTP is faked here - these tests never leave the machine.

Run:  cd /Users/dan/resmara && venv/bin/python tests/test_analytics_wiring.py
"""

import os
import sys
import tempfile
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# --- environment BEFORE the app is imported: a throwaway database, never the real one ---
_tmp = tempfile.NamedTemporaryFile(prefix="resmara-analytics-", suffix=".db", delete=False)
_tmp.close()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp.name}"
os.environ.pop("RESMARA_SIMULATE", None)
os.environ["RESMARA_ADMIN_EMAILS"] = "owner@resmara.com"

from app.services import analytics                                        # noqa: E402

checks = 0
failures = 0


def ok(name, cond, extra: object = ""):
    global checks, failures
    checks += 1
    if cond:
        print(f"  PASS  {name}")
    else:
        failures += 1
        print(f"  FAIL  {name}" + (f"  ({extra})" if extra else ""))


def clear_env():
    for name in ("META_AD_ACCOUNT_ID", "META_SYSTEM_TOKEN", "GA4_PROPERTY_ID", "GA4_TOKEN",
                 "GA4_SA_JSON", "CLARITY_PROJECT_ID", "CLARITY_TOKEN", "GA4_MEASUREMENT_ID", "META_PIXEL_ID"):
        os.environ.pop(name, None)
        os.environ.pop("RESMARA_" + name, None)


class FakeResponse:
    def __init__(self, status=200, payload=None, text=""):
        self.status_code = status
        self._payload = payload if payload is not None else {}
        self.text = text or str(self._payload)

    def json(self):
        return self._payload


class FakeClient:
    """Stands in for httpx.Client: a queue of canned responses, and a record of the calls."""

    calls = []
    queue = []

    def __init__(self, *args, **kwargs):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def _answer(self, method, url, params=None, json=None, data=None, headers=None, content=None):
        FakeClient.calls.append({"method": method, "url": url, "params": params,
                                 "json": json, "data": data, "headers": headers})
        return FakeClient.queue.pop(0) if FakeClient.queue else FakeResponse(200, {})

    def get(self, url, params=None, headers=None, follow_redirects=False):
        return self._answer("GET", url, params=params, headers=headers)

    def post(self, url, json=None, data=None, headers=None, content=None):
        return self._answer("POST", url, json=json, data=data, headers=headers, content=content)


# Patching analytics.httpx.Client patches the httpx module itself, which starlette's TestClient
# also uses, so the real class is kept and put back before the endpoint checks below.
_real_httpx_client = analytics.httpx.Client
analytics.httpx.Client = FakeClient
start = datetime.utcnow() - timedelta(days=30)
end = datetime.utcnow()


# --------------------------------------------------------------------- Meta, with and without a key
print("\n[ad spend: no credential means a sentence, not a zero]")
clear_env()
result = analytics.meta_insights(None, start, end)
ok("no account is not connected", result["connected"] is False)
ok("and names both env vars", "META_AD_ACCOUNT_ID" in result["why"] and "META_SYSTEM_TOKEN" in result["why"],
   result["why"])
ok("spend stays None, not 0", result["spend_usd"] is None and result["clicks"] is None)

print("\n[ad spend: with a key it reads Meta's own numbers]")
os.environ["META_AD_ACCOUNT_ID"] = "act_1234567890"
os.environ["META_SYSTEM_TOKEN"] = "token-not-real"
FakeClient.queue = [FakeResponse(200, {"data": [
    {"date_start": "2026-11-01", "spend": "10.50", "impressions": "1000", "clicks": "25"},
    {"date_start": "2026-11-08", "spend": "9.99", "impressions": "800", "clicks": "12"},
]})]
FakeClient.calls = []
result = analytics.meta_insights(None, start, end)
ok("it is connected", result["connected"] is True, result.get("why"))
ok("spend is summed", result["spend_usd"] == 20.49, result["spend_usd"])
ok("clicks are summed", result["clicks"] == 37, result["clicks"])
ok("the weeks come back one per Meta row", len(result["weeks"]) == 2, result["weeks"])
ok("the token went to Meta and nowhere else", FakeClient.calls and "access_token" in
   (FakeClient.calls[0]["params"] or {}))
ok("the token was not put in the URL", "token-not-real" not in str(FakeClient.calls[0]["url"]))

print("\n[ad spend: Meta refusing is a warn with the reason]")
FakeClient.queue = [FakeResponse(400, {"error": {"message": "Ad account not authorized"}})]
result = analytics.meta_insights(None, start, end)
ok("a 400 is not connected", result["connected"] is False)
ok("and quotes Meta", "400" in result["why"] and "not authorized" in result["why"], result["why"])

print("\n[ad spend: a week with no delivery is a real zero]")
FakeClient.queue = [FakeResponse(200, {"data": [
    {"date_start": "2026-11-01", "spend": "0", "impressions": "0", "clicks": "0"}]})]
result = analytics.meta_insights(None, start, end)
ok("connected with zero spend", result["connected"] is True and result["spend_usd"] == 0.0, result)


# --------------------------------------------------------------------- GA4
print("\n[visitors: without a property there is a sentence]")
clear_env()
result = analytics.ga4_visitors(start, end)
ok("not connected", result["connected"] is False)
ok("names GA4_PROPERTY_ID", "GA4_PROPERTY_ID" in result["why"], result["why"])

print("\n[visitors: a property without a key says which key]")
os.environ["GA4_PROPERTY_ID"] = "123456789"
result = analytics.ga4_visitors(start, end)
ok("still not connected", result["connected"] is False)
ok("names the two ways to authenticate", "GA4_SA_JSON" in result["why"] and "GA4_TOKEN" in result["why"],
   result["why"])

print("\n[visitors: with a token it reads the report]")
os.environ["GA4_TOKEN"] = "ya29.not-a-real-token"
FakeClient.queue = [
    FakeResponse(200, {"rows": [{"metricValues": [{"value": "412"}, {"value": "88"}]}]}),   # totals
    FakeResponse(200, {"rows": [{"metricValues": [{"value": "301"}]}]}),                   # previous
    FakeResponse(200, {"rows": [
        {"dimensionValues": [{"value": "Organic Search"}], "metricValues": [{"value": "210"}]},
        {"dimensionValues": [{"value": "Direct"}], "metricValues": [{"value": "120"}]}]}), # channels
    FakeResponse(200, {"rows": [
        {"dimensionValues": [{"value": "/"}], "metricValues": [{"value": "900"}]}]}),      # pages
]
FakeClient.calls = []
result = analytics.ga4_visitors(start, end)
ok("connected", result["connected"] is True, result.get("why"))
ok("visitors", result["visitors"] == 412, result["visitors"])
ok("new visitors", result["new_visitors"] == 88, result["new_visitors"])
ok("the previous window is compared", result["visitors_prev"] == 301, result["visitors_prev"])
ok("channels arrive", [s["name"] for s in result["sources"]] == ["Organic Search", "Direct"],
   result["sources"])
ok("pages arrive", result["pages"] and result["pages"][0]["views"] == 900, result["pages"])
ok("the bearer token is in the header only", FakeClient.calls[0]["headers"]["Authorization"].startswith("Bearer ")
   and "ya29" not in str(FakeClient.calls[0]["url"]))

print("\n[visitors: Google erroring is a warn]")
FakeClient.queue = [FakeResponse(403, {"error": {"message": "PERMISSION_DENIED"}})]
result = analytics.ga4_visitors(start, end)
ok("a 403 is not connected", result["connected"] is False)
ok("and says Analytics answered with an error", "error" in result["why"], result["why"])


# --------------------------------------------------------------------- Clarity
print("\n[heat maps: no project means a sentence]")
clear_env()
result = analytics.clarity_sessions()
ok("not connected", result["connected"] is False)
ok("names both env vars", "CLARITY_PROJECT_ID" in result["why"] and "CLARITY_TOKEN" in result["why"],
   result["why"])

print("\n[heat maps: with a token it sums the live window]")
os.environ["CLARITY_PROJECT_ID"] = "abcdefghij"
os.environ["CLARITY_TOKEN"] = "clarity-not-real"
FakeClient.queue = [FakeResponse(200, [
    {"metricName": "Traffic", "information": [
        {"totalSessionCount": "40", "totalBotSessionCount": "5", "distantUserCount": "31"},
        {"totalSessionCount": "7", "totalBotSessionCount": "1", "distantUserCount": "6"}]},
    {"metricName": "Engagement", "information": [{"totalSessionCount": "999"}]},
])]
FakeClient.calls = []
result = analytics.clarity_sessions()
ok("connected", result["connected"] is True, result.get("why"))
ok("sessions are summed from Traffic only", result["sessions"] == 47, result["sessions"])
ok("the window is stated as three days", result["window_days"] == 3)
ok("a dashboard link is offered", result["url"].startswith("https://clarity.microsoft.com/"), result["url"])
ok("only Traffic was counted", FakeClient.calls[0]["params"] == {"numOfDays": 3}, FakeClient.calls[0]["params"])

print("\n[heat maps: Clarity refusing is a warn]")
FakeClient.queue = [FakeResponse(429, {"error": "rate limited"})]
result = analytics.clarity_sessions()
ok("a 429 is not connected", result["connected"] is False)
ok("and quotes the status", "429" in result["why"], result["why"])

# --------------------------------------------------------------------- the two pages, for real
print("\n[both pages answer as pages, with no key at all]")
analytics.httpx.Client = _real_httpx_client
# A property that decrypts (AdAccount.access_token) cannot be filtered in SQL, and a naive
# datetime compared to Postgres' timestamptz is exactly the kind of thing that passes on sqlite
# and 500s in production. These two calls catch both, because they go through the endpoints.
from fastapi.testclient import TestClient                             # noqa: E402

from app.core.security import get_password_hash                        # noqa: E402
from app.db.session import Base, SessionLocal, User, engine            # noqa: E402
from app.main import app                                               # noqa: E402

Base.metadata.create_all(bind=engine)
session = SessionLocal()
session.add(User(email="owner@resmara.com", name="Owner", is_admin=True, team_super_admin=True,
                 hashed_password=get_password_hash("pw-123456")))
session.commit()
session.close()

client = TestClient(app)
token = client.post("/api/auth/login",
                    data={"username": "owner@resmara.com", "password": "pw-123456"}).json().get("access_token")
ok("the operator signs in", bool(token))
for path in ("/api/admin/marketing", "/api/admin/website"):
    response = client.get(path, headers={"Authorization": f"Bearer {token}"})
    ok(f"{path} answers 200 with nothing connected", response.status_code == 200,
       str(response.status_code) + " " + response.text[:200])
    body = response.json() if response.status_code == 200 else {}
    ok(f"{path} says it is not connected", body.get("connected") is False, body.get("connected"))
    ok(f"{path} lists what is missing", bool(body.get("unavailable")), body.get("unavailable"))
    ok(f"{path} never invents a figure",
       all(body.get(k) is None for k in ("visitors", "spend_usd", "impressions", "clicks")),
       {k: body.get(k) for k in ("visitors", "spend_usd", "impressions", "clicks")})

# --------------------------------------------------------------------- the tag injector
print("\n[tracking tags: the ids come from the server, and unset means nothing is injected]")
clear_env()
response = client.get("/api/public/tags")
ok("the tag endpoint is public", response.status_code == 200, str(response.status_code))
ok("with nothing set it returns three empty ids",
   response.json() == {"ga4": "", "clarity": "", "meta_pixel": ""}, response.json())
home = client.get("/").text
ok("the homepage loads the injector", "tags.js" in home, home[:120])
ok("the homepage does not carry a pasted tag", "googletagmanager.com/gtag/js" not in home)

os.environ["GA4_MEASUREMENT_ID"] = "G-TEST123456"
os.environ["RESMARA_CLARITY_PROJECT_ID"] = "abcdefghij"
os.environ["META_PIXEL_ID"] = "1109032311944744"
response = client.get("/api/public/tags")
ok("all three ids come back when set",
   response.json() == {"ga4": "G-TEST123456", "clarity": "abcdefghij", "meta_pixel": "1109032311944744"},
   response.json())
clear_env()

clear_env()
print()
if failures:
    print(f"{failures} of {checks} FAILED")
    sys.exit(1)
print(f"{checks} checks, 0 failed.\nALL ANALYTICS WIRING TESTS PASSED")
