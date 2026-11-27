"""The brand kit is built from the Page the agent connected (Brand Engine v1.0 §4).

Two things are being proved here, both of them things that went wrong in the old build: the kit's
*facts* come from Meta and its *proposals* do not overwrite what the agent typed; and a token that
cannot read the Page produces a reason, not an empty kit that looks like success.
"""
import json
import os
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DB_DIR = tempfile.mkdtemp(prefix="brand-")
os.environ["RESMARA_DB"] = os.path.join(DB_DIR, "app.db")
os.environ["DATABASE_URL"] = f"sqlite:///{os.path.join(DB_DIR, 'app.db')}"
os.environ["RESMARA_UPLOAD_DIR"] = os.path.join(DB_DIR, "uploads")

from fastapi.testclient import TestClient  # noqa: E402

GRAPH = {"base": "", "pages": None, "page_error": None}


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, format, *args):
        pass

    def _json(self, payload, code=200):
        raw = json.dumps(payload).encode()
        self.send_response(code)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        path = self.path.split("?")[0]
        if path.endswith("/me/accounts"):
            if GRAPH["pages"] is None:
                return self._json({"error": {"message": "no page permission"}}, 403)
            return self._json({"data": GRAPH["pages"]})
        if "/business" in self.path:
            return self._json({"business": {"id": "biz-1", "name": "Dana Realty Group"}})
        if GRAPH["page_error"]:
            return self._json({"error": {"message": GRAPH["page_error"]}}, 400)
        return self._json({"id": "page-1", "name": "Dana Realty", "category": "Real Estate Agent",
                           "about": "Homes in south Austin.", "phone": "512-555-0100",
                           "website": "https://danarealty.example",
                           "picture": {"data": {"url": "https://cdn/logo.png"}}})


server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
GRAPH["base"] = f"http://127.0.0.1:{server.server_address[1]}/v21.0"
threading.Thread(target=server.serve_forever, daemon=True).start()

import app.services.token_health as token_health  # noqa: E402
token_health._base = lambda base_url=None: GRAPH["base"]  # point the engine at the stand-in

from app.db.session import AdAccount, SessionLocal, User  # noqa: E402
from app.main import app  # noqa: E402

FAILS = []


def check(name, ok, detail=""):
    print(("ok   " if ok else "FAIL ") + name + (f"  [{detail}]" if detail and not ok else ""))
    if not ok:
        FAILS.append(name)


def account(client, email, token="page-token"):
    client.post("/api/auth/register", json={"terms_accepted": True, "email": email, "password": "long enough",
                                            "name": "Agent"})
    tok = client.post("/api/auth/login", data={"username": email, "password": "long enough"}
                      ).json()["access_token"]
    db = SessionLocal()
    user = db.query(User).filter(User.email == email).first()
    db.add(AdAccount(user_id=user.id, platform="meta", advertiser_id="act_1",
                     access_token=token, currency="USD"))
    db.commit()
    db.close()
    return {"Authorization": f"Bearer {tok}"}


with TestClient(app) as client:
    print("=== an agent with no Facebook connection is told so ===")
    client.post("/api/auth/register", json={"terms_accepted": True, "email": "nometa@example.com",
                                            "password": "long enough", "name": "Agent"})
    tok = client.post("/api/auth/login", data={"username": "nometa@example.com",
                                               "password": "long enough"}).json()["access_token"]
    r = client.post("/api/auth/me/brand/from-meta", headers={"Authorization": f"Bearer {tok}"})
    check("400, not an empty kit", r.status_code == 400, str(r.status_code))
    check("  ...and it says to connect first", "connect" in r.text.lower(), r.text[:200])

    print("\n=== the facts come from the Page Meta shows us ===")
    GRAPH["pages"] = [{"id": "page-1", "name": "Dana Realty", "category": "Real Estate Agent"}]
    h = account(client, "dana@example.com")
    r = client.post("/api/auth/me/brand/from-meta", headers=h)
    check("the kit is returned", r.status_code == 200, r.text[:200])
    kit = r.json()
    facts = kit.get("facts") or {}
    check("  ...the Page name is a fact", facts.get("name") == "Dana Realty", str(facts)[:200])
    check("  ...so is the phone", facts.get("phone") == "512-555-0100")
    check("  ...and the website", facts.get("website") == "https://danarealty.example")
    check("  ...and the logo URL", facts.get("logo_url") == "https://cdn/logo.png")
    check("nothing is saved or confirmed by building it", kit.get("confirmed") is False, str(kit)[:200])
    check("  ...and the brand on the account is untouched",
          client.get("/api/auth/me/brand", headers=h).json()["brand"] == {}, "brand was written")

    print("\n=== a Page the token cannot read is a reason, not a blank kit ===")
    GRAPH["page_error"] = "Permissions error"
    r = client.post("/api/auth/me/brand/from-meta", headers=h)
    check("502 with Meta's own words", r.status_code == 502 and "Permissions error" in r.text,
          r.text[:200])
    GRAPH["page_error"] = None

    print("\n=== an account with no Page is a different problem ===")
    GRAPH["pages"] = []
    r = client.post("/api/auth/me/brand/from-meta", headers=h)
    check("the answer says there is no Page", r.status_code == 502 and "no Page" in r.text,
          r.text[:200])
    GRAPH["pages"] = [{"id": "page-1", "name": "Dana Realty"}]

    print("\n=== saving the confirmed kit is the existing route, unchanged ===")
    put = client.put("/api/auth/me/brand", headers=h,
                     json={"brand": {"name": "Dana Realty", "voice": "warm",
                                     "colors": ["#14342B"]}})
    check("the agent's own save still works", put.status_code == 200
          and put.json()["brand"]["voice"] == "warm", put.text[:150])

server.shutdown()
print()
if FAILS:
    print(f"{len(FAILS)} FAILED: " + "; ".join(FAILS))
    raise SystemExit(1)
print("ALL BRAND ENGINE TESTS PASSED")
