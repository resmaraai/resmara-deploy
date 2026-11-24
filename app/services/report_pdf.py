"""A campaign report as a real PDF, with no new dependency.

The owner asked for "Download PDF" on the Day 7 and Day 14 reports. Adding reportlab to the
runtime for one page of text is a dependency the Docker image would carry forever, so this
module writes the PDF directly: one or more pages, Helvetica, wrapped lines, and a small table
of label/value rows. It is deliberately plain — no images, no fonts beyond the standard 14 — but
it is a valid PDF 1.4 that opens in Preview, Chrome and a phone.

Only text we generate goes in here, and parentheses/backslashes are escaped, so a caption with a
bracket cannot break the file.
"""

from datetime import datetime, timezone

PAGE_W, PAGE_H = 595, 842  # A4 points
MARGIN = 54
LINE = 15
BODY = 10.5
FONT = "Helvetica"
BOLD = "Helvetica-Bold"


def _esc(text: str) -> str:
    """PDF strings: backslash escapes, and non-Latin-1 characters become '?' rather than junk."""
    out = []
    for ch in str(text):
        if ch in "()\\":
            out.append("\\" + ch)
        elif ord(ch) < 32:
            out.append(" ")
        elif ord(ch) > 255:
            out.append("?")
        else:
            out.append(ch)
    return "".join(out)


def _wrap(text: str, size: float, width: float) -> list[str]:
    """Greedy wrap using an approximate Helvetica average glyph width (0.5 em)."""
    max_chars = max(8, int(width / (size * 0.5)))
    lines, line = [], ""
    for word in str(text).split():
        candidate = (line + " " + word).strip()
        if len(candidate) <= max_chars:
            line = candidate
            continue
        if line:
            lines.append(line)
        # A single word longer than the line is hard-split, not dropped.
        while len(word) > max_chars:
            lines.append(word[:max_chars])
            word = word[max_chars:]
        line = word
    if line:
        lines.append(line)
    return lines or [""]


class _Page:
    def __init__(self):
        self.ops: list[str] = []
        self.y = PAGE_H - MARGIN

    def text(self, s: str, size: float = BODY, bold: bool = False, indent: int = 0,
             gap: float = 2) -> None:
        self.y -= size + gap
        self.ops.append(
            f"BT /{'F2' if bold else 'F1'} {size:.1f} Tf 1 0 0 1 {MARGIN + indent:.1f} {self.y:.1f} Tm "
            f"({_esc(s)}) Tj ET")

    def rule(self, gap: float = 6) -> None:
        self.y -= gap
        self.ops.append(f"0.85 0.85 0.85 RG 0.6 w {MARGIN} {self.y:.1f} m {PAGE_W - MARGIN} "
                        f"{self.y:.1f} l S")

    def room(self, needed: float = 60) -> bool:
        return self.y - needed > MARGIN


def _render(pages: list[_Page]) -> bytes:
    objects: list[bytes] = []

    def add(body: bytes) -> int:
        objects.append(body)
        return len(objects)

    font1 = add(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>")
    font2 = add(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>")
    pages_obj_placeholder = len(objects) + 1 + 2 * len(pages) + 1  # computed below; placeholder id
    kids = []
    page_ids = []
    for page in pages:
        content = ("\n".join(page.ops)).encode("latin-1", "replace")
        stream_id = add(b"<< /Length " + str(len(content)).encode() + b" >>\nstream\n" + content +
                        b"\nendstream")
        page_id = add(f"<< /Type /Page /Parent {pages_obj_placeholder} 0 R /MediaBox [0 0 {PAGE_W} "
                      f"{PAGE_H}] /Resources << /Font << /F1 {font1} 0 R /F2 {font2} 0 R >> >> "
                      f"/Contents {stream_id} 0 R >>".encode())
        page_ids.append(page_id)
        kids.append(f"{page_id} 0 R")
    pages_id = add(f"<< /Type /Pages /Kids [{' '.join(kids)}] /Count {len(page_ids)} >>".encode())
    catalog_id = add(f"<< /Type /Catalog /Pages {pages_id} 0 R >>".encode())

    # The placeholder assumed pages come last; if not, rewrite each page's Parent now.
    if pages_id != pages_obj_placeholder:
        for i, pid in enumerate(page_ids):
            objects[pid - 1] = objects[pid - 1].replace(
                f"/Parent {pages_obj_placeholder} 0 R".encode(), f"/Parent {pages_id} 0 R".encode())

    out = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for i, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{i} 0 obj\n".encode() + body + b"\nendobj\n"
    xref_at = len(out)
    out += f"xref\n0 {len(objects) + 1}\n".encode()
    out += b"0000000000 65535 f \n"
    for off in offsets[1:]:
        out += f"{off:010d} 00000 n \n".encode()
    out += (f"trailer\n<< /Size {len(objects) + 1} /Root {catalog_id} 0 R >>\nstartxref\n"
            f"{xref_at}\n%%EOF\n").encode()
    return bytes(out)


def _rows_from_payload(report: dict, version: str = "agent") -> list[tuple[str, str, str]]:
    """The numbers the page shows, in the order the page shows them.

    version="seller" is the client-ready report (Engine 6, section 9): reach, views, engagement and
    clicks to the listing, and NO cost, spend or cost per click anywhere."""
    seller = version == "seller"
    organic = report.get("organic") or {}
    paid = report.get("paid") or {}
    summary = organic.get("summary") or {}
    measured = int(summary.get("measured") or 0)
    rows: list[tuple[str, str, str]] = []

    posts = report.get("posts") or {}
    rows.append(("Posts", f"{posts.get('published', 0)} published", "" if seller else
                 f"of {posts.get('total', 0)}; {posts.get('approved', 0)} approved"))
    if measured:
        rows.append(("Reach", f"{int(summary.get('reach') or 0):,}",
                     f"People who saw the posts, across {summary.get('posts') or 0} posts"))
        rows.append(("Engagement", f"{int(summary.get('interactions') or 0):,}",
                     "Likes, comments, shares, saves and clicks on the posts"))
    else:
        reason = organic.get("reason") or "Meta has not shared numbers for this period yet"
        rows.append(("Reach", "-", reason))

    if paid.get("ok"):
        rows.append(("Ad views", f"{int(paid.get('impressions') or 0):,}",
                     f"Seen by {int(paid.get('reach') or 0):,} people" if paid.get("reach") else ""))
        rows.append(("Clicks to the listing", f"{int(paid.get('link_clicks') or 0):,}", ""))
        if not seller:
            spend = paid.get("spend")
            rows.append(("Ad spend", f"${spend}" if spend not in (None, "") else "-",
                         "Billed by Meta on your own card, not by Resmara"))
            rows.append(("Cost per click", f"${paid.get('cpc')}" if paid.get("cpc") not in (None, "") else "-",
                         f"Click rate {paid.get('ctr')}%" if paid.get("ctr") not in (None, "") else ""))
            if paid.get("frequency") not in (None, ""):
                rows.append(("Frequency", str(paid.get("frequency")), "Times each person saw the ad, on average"))
    elif paid.get("reason") and not seller:
        rows.append(("Ad numbers", "-", str(paid.get("reason"))))

    website = report.get("website") or {}
    if website.get("visits") is not None and website:
        srcs = website.get("sources") or {}
        top = ", ".join(f"{k}: {v}" for k, v in sorted(srcs.items(), key=lambda kv: -kv[1])[:4])
        rows.append(("Listing website visits", f"{int(website.get('visits') or 0):,}", "" if seller else top))
    if not seller:
        leads = report.get("leads") or {}
        if leads:
            total = sum(int(v or 0) for v in leads.values())
            rows.append(("Leads", str(total),
                         f"Ad comments {leads.get('ad_comments', 0)} · post comments {leads.get('post_comments', 0)} · "
                         f"website form {leads.get('website_form', 0)} · calls {leads.get('calls', 0)} · "
                         f"texts {leads.get('texts', 0)}"))
    return rows


def campaign_report_pdf(report: dict, *, brand: str = "Resmara", version: str = "agent") -> bytes:
    """Render the Day 7 / Day 14 report payload as a real PDF.

    Takes the same dict ``GET /api/boosts/{id}/reports/{day}`` returns, so the download can never
    disagree with the page. Anything Meta did not measure is printed as "Not measured" with the
    reason - a PDF is the most quotable thing we produce, so it is the last place to invent a zero.
    """
    pages = [_Page()]
    page = pages[0]

    def new_page():
        pages.append(_Page())
        return pages[-1]

    seller = version == "seller"
    day = report.get("report_day") or report.get("day") or 7
    page.text(f"Day {day} marketing report" if seller else f"Day {day} report", size=20, bold=True, gap=6)
    page.text(str(report.get("address") or ""), size=12, gap=5)
    who = report.get("prepared_by") or {}
    if seller and (who.get("agent") or who.get("brokerage")):
        page.text("Prepared by " + ", ".join(x for x in (who.get("agent"), who.get("brokerage")) if x), size=10.5, gap=4)
    period = report.get("period") or {}
    label = period.get("label") if isinstance(period, dict) else str(period or "")
    if label:
        page.text(label, size=9.5, gap=4)
    page.rule()

    rows = _rows_from_payload(report, version) if seller else (report.get("stats") or _rows_from_payload(report))
    for row in rows:
        if isinstance(row, dict):
            lab, val, note = row.get("label"), row.get("value"), row.get("note") or ""
        else:
            lab, val, note = row
        if not page.room(70):
            page = new_page()
        page.text(f"{lab}: {val}", size=11.5, bold=True, gap=2)
        for line in _wrap(str(note), 9.5, PAGE_W - 2 * MARGIN - 8) if note else []:
            page.text(line, size=9.5, indent=8, gap=1)

    sections = (("What worked", "worked"), ("Notes", "notes")) if seller else (
        ("What worked", "worked"), ("What to change", "change"), ("Notes", "notes"), ("Ad audit log", "audit_lines"))
    report = dict(report)
    report["audit_lines"] = [a.get("line") for a in report.get("audit") or [] if a.get("line")]
    for heading, key in sections:
        body = report.get(key)
        if not body:
            continue
        if not page.room(90):
            page = new_page()
        page.rule()
        page.text(heading, size=12, bold=True, gap=4)
        items = body if isinstance(body, (list, tuple)) else [body]
        for item in items:
            for line in _wrap(f"- {item}" if isinstance(body, list) else str(item),
                              BODY, PAGE_W - 2 * MARGIN):
                if not page.room(30):
                    page = new_page()
                page.text(line, gap=1)

    page.rule()
    stamp = datetime.now(timezone.utc).strftime("%d %b %Y, %H:%M UTC")
    footer = (f"Generated {stamp}. Numbers come from Meta; anything Meta hasn't shared shows as a dash." if seller
              else f"{brand} - generated {stamp}. Reach, clicks and leads are what this report ranks on; "
                   f"ad spend is billed by Meta on the agent's card.")
    for line in _wrap(footer, 8.5, PAGE_W - 2 * MARGIN):
        page.text(line, size=8.5, gap=1)
    return _render(pages)
