"""Engine 6, section 7: is the home still for sale? Read the status field, never guess.

Replaces the word-matching in listing_watch.classify. Every hour, for each running (or paused
pending) campaign, each source for the home is read, layer by layer, stopping at the first clear
answer (docs/engines/engine-6-brain.md, "Self-healing"):

  1. the known spot: the status field where each site keeps it (`homeStatus`, `listingStatus`,
     `mlsStatus`, `standardStatus`...), in the data behind the page
  2. the standard spot: schema.org data (JSON-LD) published for search engines
  3. the AI reads the page, only when 1 and 2 fail: it must quote the exact words, and the quote
     must be on the page and not in a "nearby / similar homes" list. No clear line -> unknown
  4. another source: the same home on the other sites Engine 3 found

Act on a clear Pending or Sold (one source's status field, or two sources agreeing). A page that
can't be read, sources that disagree, or a photographer's page that was taken down are never a sale.
Pending beats Sold until a clear Sold appears. The listing agent is read the same way, so a home
that comes back with another agent never prompts this one.
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Dict, List, Optional
from urllib.parse import urlsplit

log = logging.getLogger(__name__)

ACTIVE, PENDING, SOLD, OFFLINE, UNKNOWN = "active", "pending", "sold", "offline", "unknown"
LISTING_SITES = ("zillow.com", "redfin.com", "realtor.com", "trulia.com", "homes.com")
PHOTO_HOSTS = ("aryeo", "fotello", "dropbox", "hdphotohub", "spiro", "tourbuzz", "matterport", "vimeo", "youtube")

_ACTIVE = {"for_sale", "forsale", "active", "coming_soon", "new", "new_construction", "price_change",
           "back_on_market", "for sale", "available"}
_PENDING = {"pending", "contingent", "under_contract", "undercontract", "active_under_contract",
            "active_contingent", "pending_sale", "sale_pending", "in_contract", "contract", "under contract",
            "active under contract", "pending - taking backups", "accepting backup offers"}
_SOLD = {"sold", "recently_sold", "closed", "sold_out", "off_market_sold"}
_OFF = {"off_market", "offmarket", "withdrawn", "expired", "cancelled", "canceled", "delisted", "other"}

STATUS_KEYS = ("homeStatus", "listingStatus", "mlsStatus", "standardStatus", "propertyStatus",
               "searchStatus", "listing_status", "statusText", "status")
NEARBY = re.compile(r"(recently sold|nearby|similar homes|comparable|neighborhood sales|sold homes near|"
                    r"homes for you|you may also like|more homes|filter)", re.I)


@dataclass
class Read:
    source: str
    url: str
    status: str = UNKNOWN
    layer: str = ""
    quote: str = ""
    price_cents: Optional[int] = None
    agent: Dict[str, str] = field(default_factory=dict)
    http: int = 0
    at: str = ""

    def clear(self) -> bool:
        return self.status in (ACTIVE, PENDING, SOLD) and self.layer in ("known", "standard", "ai")


def _norm(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip().lower().replace("-", "_").replace(" ", "_")


def map_status(value: Any) -> Optional[str]:
    v = _norm(value)
    if not v:
        return None
    raw = str(value).strip().lower()
    if v in _PENDING or raw in _PENDING or "under_contract" in v or "pending" in v or "contingent" in v:
        return PENDING
    if v in _SOLD or raw in _SOLD:
        return SOLD
    if v in _ACTIVE or raw in _ACTIVE:
        return ACTIVE
    if v in _OFF:
        return OFFLINE
    return None


def host_of(url: str) -> str:
    host = urlsplit(url or "").netloc.lower()
    return host[4:] if host.startswith("www.") else host


def source_name(url: str) -> str:
    host = host_of(url)
    for site in LISTING_SITES:
        if host.endswith(site):
            return site.split(".")[0]
    return host or "link"


def is_photo_page(url: str) -> bool:
    return any(h in host_of(url) for h in PHOTO_HOSTS)


# ------------------------------------------------------------------ layer 1: the known spot
def _json_blobs(html: str) -> List[Any]:
    out = []
    for m in re.finditer(r"<script[^>]*(?:__NEXT_DATA__|application/json|__APOLLO_STATE__)[^>]*>(.*?)</script>",
                         html or "", re.S | re.I):
        try:
            out.append(json.loads(m.group(1)))
        except (ValueError, TypeError):
            continue
    return out


def _walk(node, depth=0):
    if depth > 40:
        return
    if isinstance(node, dict):
        yield node
        for v in node.values():
            yield from _walk(v, depth + 1)
    elif isinstance(node, list):
        for v in node[:400]:
            yield from _walk(v, depth + 1)


def _dig_agent(node: Dict[str, Any]) -> Dict[str, str]:
    agent = {}
    for key in ("listingAgent", "listing_agent", "attributionInfo", "agent", "listAgent", "advertisers"):
        val = node.get(key)
        if isinstance(val, list) and val:
            val = val[0]
        if isinstance(val, dict):
            name = val.get("agentName") or val.get("name") or val.get("fullName") or val.get("displayName")
            lic = val.get("agentLicenseNumber") or val.get("licenseNumber") or val.get("license")
            brk = val.get("brokerName") or val.get("brokerageName") or val.get("officeName")
            if isinstance(brk, dict):
                brk = brk.get("name")
            agent = {k: str(v)[:120] for k, v in (("name", name), ("license", lic), ("brokerage", brk)) if v}
            if agent:
                return agent
    return agent


def _price(value) -> Optional[int]:
    if isinstance(value, dict):
        value = value.get("value") or value.get("amount") or value.get("price")
    try:
        n = float(str(value).replace(",", "").replace("$", ""))
    except (TypeError, ValueError):
        return None
    return int(round(n * 100)) if 10_000 <= n <= 100_000_000 else None


def known_spot(html: str, street: str = "") -> Optional[Read]:
    """The status field in the data behind the page. The listing's own object is the one carrying a
    status AND (when we know it) the street; the first such object wins, so a "similar homes" list
    later in the data never decides."""
    street_key = _street_key(street)
    best = None
    for blob in _json_blobs(html):
        for node in _walk(blob):
            status = None
            for key in STATUS_KEYS:
                if key in node and isinstance(node[key], (str, int)):
                    status = map_status(node[key])
                    if status:
                        quote = f'{key}: {node[key]}'
                        break
            if not status:
                continue
            text = json.dumps(node)[:4000].lower()
            if street_key and street_key not in _street_key(text):
                if best is None:
                    best = (status, quote, node)
                continue
            return Read(source="", url="", status=status, layer="known", quote=quote,
                        price_cents=_price(node.get("price") or node.get("listPrice") or node.get("unformattedPrice")),
                        agent=_dig_agent(node))
    if best and not street_key:
        status, quote, node = best
        return Read(source="", url="", status=status, layer="known", quote=quote,
                    price_cents=_price(node.get("price") or node.get("listPrice")), agent=_dig_agent(node))
    return None


def _street_key(text: str) -> str:
    m = re.search(r"\b(\d{1,6})\s+([a-z0-9]+)", (text or "").lower())
    return f"{m.group(1)} {m.group(2)}" if m else ""


# ------------------------------------------------------------------ layer 2: the standard spot
_AVAIL = {"instock": ACTIVE, "presale": ACTIVE, "limitedavailability": PENDING, "soldout": SOLD,
          "outofstock": SOLD, "discontinued": OFFLINE}


def standard_spot(html: str) -> Optional[Read]:
    for m in re.finditer(r'<script[^>]*application/ld\+json[^>]*>(.*?)</script>', html or "", re.S | re.I):
        try:
            data = json.loads(m.group(1))
        except (ValueError, TypeError):
            continue
        for node in _walk(data):
            offers = node.get("offers")
            if isinstance(offers, list) and offers:
                offers = offers[0]
            if not isinstance(offers, dict):
                continue
            avail = str(offers.get("availability") or "").rsplit("/", 1)[-1].lower()
            status = _AVAIL.get(avail)
            if status:
                return Read(source="", url="", status=status, layer="standard", quote=f"availability: {avail}",
                            price_cents=_price(offers.get("price")))
    return None


# ------------------------------------------------------------------ layer 3: the AI, quoting
AI_SYSTEM = """You read a real estate listing page and say whether THIS home (the one the page is
about) is for sale, pending (under contract, contingent) or sold, the way a person would.
Return ONLY JSON: {"status": "active" | "pending" | "sold" | "unknown", "quote": "the exact words on
the page that show it, copied character for character", "agent": "the listing agent's name or empty",
"price": "the list price as digits or empty"}. Lists of other homes ("Recently sold nearby",
"Similar homes", filters, menus) never count. If no line clearly says it, status is "unknown"."""


def page_text(html: str) -> str:
    text = re.sub(r"<(script|style|noscript)[^>]*>.*?</\1>", " ", html or "", flags=re.S | re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def check_quote(text: str, quote: str) -> bool:
    """The quote has to be on the page, and not inside a list of other homes."""
    q = re.sub(r"\s+", " ", quote or "").strip()
    if len(q) < 4:
        return False
    i = text.lower().find(q.lower())
    if i < 0:
        return False
    # A list of other homes sits under its heading, so the words just before the quote decide.
    return not NEARBY.search(text[max(0, i - 100): i + len(q)])


async def ai_read(html: str, address: str, *, ai: Optional[Callable] = None) -> Optional[Read]:
    text = page_text(html)[:9000]
    if not text:
        return None
    try:
        if ai is not None:
            got = await ai(text, address)
        else:
            from app.core.config import settings
            from app.services import llm
            if not llm.llm_available():
                return None
            got = await llm.chat_json(AI_SYSTEM, f"HOME: {address}\nPAGE TEXT: {text}",
                                      model=settings.OPENAI_MODEL_BRAND, max_completion_tokens=400,
                                      reasoning_effort="low")
    except Exception as exc:  # noqa: BLE001 - unknown, never a guess
        log.info("listing AI read failed: %s", exc)
        return None
    status = map_status((got or {}).get("status"))
    quote = str((got or {}).get("quote") or "")
    if status not in (ACTIVE, PENDING, SOLD) or not check_quote(text, quote):
        return None
    return Read(source="", url="", status=status, layer="ai", quote=quote[:200],
                price_cents=_price((got or {}).get("price")),
                agent={"name": str(got.get("agent"))[:120]} if got.get("agent") else {})


# ------------------------------------------------------------------ one source, all layers
async def fetch(url: str, timeout: int = 20) -> tuple:
    import httpx
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True, headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 "
                              "(KHTML, like Gecko) Version/17.0 Safari/605.1.15 Resmara-listing-check",
                "Accept-Language": "en-US,en;q=0.9"}) as c:
            resp = await c.get(url)
        return resp.status_code, resp.text[:800000]
    except Exception as exc:  # noqa: BLE001 - an unreachable page is a recorded fact
        log.info("listing %s unreachable: %s", url, exc)
        return 0, ""


async def read_source(url: str, address: str, *, fetcher: Optional[Callable] = None,
                      ai: Optional[Callable] = None, use_ai: bool = True) -> Read:
    now = datetime.now(timezone.utc).isoformat()
    code, html = await (fetcher or fetch)(url)
    base = Read(source=source_name(url), url=url, http=code, at=now)
    if code in (404, 410):
        base.status = OFFLINE          # taken down: never a sale on its own
        base.layer = "gone"
        return base
    if code == 0 or code >= 400 or not html:
        base.layer = "unreadable"
        return base
    street = (address or "").split(",")[0]
    for layer in (lambda: known_spot(html, street), lambda: standard_spot(html)):
        got = layer()
        if got and got.status in (ACTIVE, PENDING, SOLD):
            got.source, got.url, got.http, got.at = base.source, url, code, now
            return got
        if got and got.status == OFFLINE:
            base.status, base.layer, base.quote = OFFLINE, got.layer, got.quote
    if use_ai and not is_photo_page(url):
        got = await ai_read(html, address, ai=ai)
        if got:
            got.source, got.url, got.http, got.at = base.source, url, code, now
            return got
    base.layer = base.layer or "no_status"
    return base


def decide(reads: List[Read]) -> tuple:
    """(status or None, why). None means: don't act, keep checking."""
    clear = [r for r in reads if r.clear()]
    if not clear:
        return None, "no source could be read clearly"
    by = {s: [r for r in clear if r.status == s] for s in (ACTIVE, PENDING, SOLD)}
    field_reads = lambda s: [r for r in by[s] if r.layer in ("known", "standard")]
    strong = lambda s: bool(field_reads(s)) or len({r.source for r in by[s]}) >= 2 or (
        len(by[s]) == 1 and len(clear) == 1)
    if by[PENDING] and strong(PENDING):
        return PENDING, f"{by[PENDING][0].source} shows {by[PENDING][0].quote}"
    if by[SOLD] and strong(SOLD):
        if by[PENDING]:
            return PENDING, "one source says pending and another sold: pending until a clear sold"
        return SOLD, f"{by[SOLD][0].source} shows {by[SOLD][0].quote}"
    if by[ACTIVE] and not by[PENDING] and not by[SOLD]:
        return ACTIVE, f"{by[ACTIVE][0].source} shows {by[ACTIVE][0].quote}"
    return None, "the sources disagree"


def same_agent(reads: List[Read], kit: Dict[str, Any]) -> Optional[bool]:
    """Is it still this Resmara agent's listing? True, False, or None when it can't be told."""
    seen = [r.agent for r in reads if r.agent]
    if not seen:
        return None
    name = _norm(kit.get("agent"))
    lic = re.sub(r"\D", "", str(kit.get("license") or ""))
    brk = _norm(kit.get("company") or kit.get("brokerage"))
    for a in seen:
        if lic and re.sub(r"\D", "", a.get("license", "")) == lic:
            return True
        if name and _norm(a.get("name")) == name:
            return True
        if name and _norm(a.get("name")).split("_")[-1:] == name.split("_")[-1:] and brk and _norm(a.get("brokerage")) == brk:
            return True
    return False


def prices(reads: List[Read]) -> Dict[str, Optional[int]]:
    return {r.source: r.price_cents for r in reads if r.layer in ("known", "standard", "ai")}


def sources_for(boost) -> List[str]:
    """The agent's own link first, then the same home on the listing sites (Engine 3)."""
    urls = []
    for u in [getattr(boost, "listing_url", None)] + list(getattr(boost, "listing_sources", None) or []):
        u = (u or "").strip()
        if u.startswith("http") and u not in urls:
            urls.append(u)
    return urls[:6]


SOURCE_URL = re.compile(r"https?://(?:www\.)?(?:zillow|redfin|realtor|trulia|homes)\.com/[^\s\])\"'<>]+", re.I)


def sources_from_research(text: str) -> List[str]:
    """Engine 3 names each source; the listing-site links it found are kept on the campaign."""
    out = []
    for m in SOURCE_URL.finditer(text or ""):
        url = m.group(0).rstrip(".,;")
        if url not in out:
            out.append(url)
    return out[:5]


def reads_to_json(reads: List[Read]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for r in reads:
        key, n = r.source, 2
        while key in out:
            key, n = f"{r.source}-{n}", n + 1
        out[key] = asdict(r)
    return out
