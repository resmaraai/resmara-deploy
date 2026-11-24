"""The brand engine (Engine 2): the investigator's answer becomes the kit on My Brand.

Checks the brain's guardrails, not the model: facts that print on posts need a source, persona
not personal, their edits survive Research again, the Voice of the client reaches the post
writer, and the kit lands on the account in the background at sign-up.
"""

import asyncio
import os
import tempfile

_tmp = tempfile.NamedTemporaryFile(prefix="resmara-brand-inv-", suffix=".db", delete=False)
_tmp.close()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp.name}"

from app.db.session import Base, engine, SessionLocal, User, MetaConnection  # noqa: E402
from app.services import brand_investigator as bi, llm  # noqa: E402
from app.services.content_engine import voice_of_client_rules  # noqa: E402

Base.metadata.create_all(bind=engine)
checks, failures = 0, 0


def ok(name, cond, extra=""):
    global checks, failures
    checks += 1
    print(("  PASS  " if cond else "  FAIL  ") + name + ("" if cond else f"  ({extra})"))
    if not cond:
        failures += 1


FOUND = {
    "agent": "Jamie Carter", "title": "REALTOR®",
    "phone": "530-555-0101", "phone_source": "https://jamiecarter.example/contact",
    "license": "02123456", "license_source": "https://www2.dre.ca.gov/lookup",
    "company": "Shasta Sotheby's International Realty", "company_source": "https://shastasir.example",
    "brokerLicense": "01999999", "brokerLicense_source": "",
    "market": "Redding and Shasta Lake", "instagram": "@jamiecarterhomes",
    "colors": ["#2f4f3e", "c9a96e", "not-a-colour"], "colors_from": "their website",
    "fonts": ["Playfair Display", "Jost"],
    "voiceOfClient": ("Jamie is warm, upbeat and very local. She sells mostly in Redding and Shasta Lake, "
                      "with lots of first-time buyers. Her husband and kids help at open houses. "
                      "Her posts read like a friendly neighbour and she often says Let's get you home."),
    "voice": "Warm and local", "use": ["Let's get you home", "Pray for rain"], "avoid": ["hype words"],
    "signoff": "Let's get you home!",
    "sources": [{"title": "Website", "url": "https://jamiecarter.example"}],
}
facts = {"agent": "Jamie C", "page": "Jamie Carter Realty", "phone": "", "website": "jamiecarter.example",
         "instagram": "jamiecarterhomes", "page_picture": "https://cdn.example/pic.jpg", "email": "j@example.com",
         "category": "Real Estate Agent", "about": "", "address": ""}

print("Assembling the kit")
kit = bi.assemble(FOUND, facts)
ok("facts with a source are kept, with where they came from",
   kit["phone"] == "530-555-0101" and kit["license"] == "02123456"
   and kit["factSources"]["license"].startswith("https://www2.dre.ca.gov"), kit.get("factSources"))
ok("a post fact with no source is never guessed (broker license left empty)", kit["brokerLicense"] == "")
ok("the local office, as found", kit["company"] == "Shasta Sotheby's International Realty")
ok("colours become editable swatches, bad values dropped",
   kit["palette"] == [["Primary", "#2F4F3E"], ["Accent", "#C9A96E"]], kit["palette"])
ok("two real Google Fonts", kit["fonts"] == ["Playfair Display", "Jost"])
ok("persona, not personal: family is scrubbed from the Voice of the client",
   "husband" not in kit["voiceOfClient"] and "warm, upbeat" in kit["voiceOfClient"], kit["voiceOfClient"])
ok("  ...and from the phrases", "Pray for rain" not in kit["use"] and "Let's get you home" in kit["use"])
ok("Look defaults to Match my brand", kit["theme"] == "Match my brand")
ok("the legal line on every post", kit["legal"][-1] == "Equal Housing Opportunity"
   and "License #02123456" in kit["legal"], kit["legal"])
ok("judgement calls are marked for the agent to confirm", {"palette", "fonts", "voiceOfClient"} <= set(kit["chosen"]))
ok("where Resmara looked", ["Facebook Page", "Jamie Carter Realty"] in kit["sources"])
ok("their headshot falls back to the Page photo", kit["headshotUrl"] == "https://cdn.example/pic.jpg")
ok("nothing missing when phone, license and brokerage were found", kit["missing"] == [])

thin = bi.assemble({"agent": "Sam", "license": "999"}, {**facts, "phone": ""})
ok("missing stays missing, for the campaign flow to ask", thin["missing"] == ["phone", "license", "brokerage"],
   thin["missing"])
paged = bi.assemble({}, {**facts, "phone": "530-555-0199"})
ok("a phone on their Facebook Page counts as a source", paged["phone"] == "530-555-0199"
   and paged["factSources"]["phone"] == "Your Facebook Page")

print("Their edits survive Research again")
saved = dict(kit)
saved["voiceOfClient"] = "My own words."
saved["edited"] = ["voiceOfClient"]
redo = bi.merge(saved, bi.assemble({**FOUND, "voiceOfClient": "A new AI paragraph."}, facts))
ok("an edited field is never overwritten", redo["voiceOfClient"] == "My own words.")
ok("an unedited field is refreshed", redo["phone"] == "530-555-0101")

print("The post writer reads it")
rules = voice_of_client_rules(kit)
ok("the Voice of the client goes to every caption", "VOICE OF THE CLIENT" in rules and "warm, upbeat" in rules)
ok("with the positive-only rule", "never political" in rules)
ok("no kit, no rules", voice_of_client_rules({}) == "")

print("Built in the background at sign-up")
db = SessionLocal()
u = User(email="jamie@example.com", hashed_password="x", name="Jamie Carter", facebook_id="fb1")
db.add(u)
db.commit()
db.add(MetaConnection(user_id=u.id, page_name="Jamie Carter Realty", ig_username="jamiecarterhomes",
                      page_info={"phone": "530-555-0101", "website": ""}, issues=[], issue_log=[], capabilities={}))
db.commit()
real = llm.llm_available
llm.llm_available = lambda: False  # offline: the kit is built from the Facebook Page alone
out = asyncio.run(bi.build_for_user(u.id))
llm.llm_available = real
db.expire_all()
u = db.query(User).filter(User.id == u.id).first()
ok("the kit is saved on the account, status done", (u.brand or {}).get("build", {}).get("status") == "done", u.brand)
ok("built from Meta's facts when the web search can't run", u.brand.get("phone") == "530-555-0101"
   and u.brand.get("instagram") == "jamiecarterhomes" and u.brand.get("note"), u.brand)
ok("what's missing is listed for the campaign flow", "license" in u.brand.get("missing", []))
st = bi.build_status(u)
ok("build status endpoint shape", st["build"]["status"] == "done" and "license" in st["missing"])

print("An agent who typed their brand before the engine existed")
old = User(email="typed@example.com", hashed_password="x", name="Pat Typed", facebook_id="fb2",
           brand={"agent": "Pat Typed", "brokerage": "Pat's Own Realty", "license": "777"})
db.add(old)
db.commit()
db.add(MetaConnection(user_id=old.id, page_name="Pat Page", page_info={"phone": "530-555-0177"},
                      issues=[], issue_log=[], capabilities={}))
db.commit()
llm.llm_available = lambda: False
asyncio.run(bi.build_for_user(old.id))
llm.llm_available = real
db.expire_all()
old = db.query(User).filter(User.id == old.id).first()
ok("what they typed is kept", old.brand.get("brokerage") == "Pat's Own Realty" and old.brand.get("license") == "777", old.brand)
ok("  ...and the empty fields are filled", old.brand.get("phone") == "530-555-0177")
ok("  ...and the legal line uses their brokerage", "Pat's Own Realty" in " ".join(old.brand.get("legal") or []), old.brand.get("legal"))

print(f"\n{checks} checks, {failures} failed.")
if failures:
    raise SystemExit(1)
print("ALL BRAND INVESTIGATOR TESTS PASSED")
