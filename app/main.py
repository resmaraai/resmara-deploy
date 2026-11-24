from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from app.api import api_router
from app.core.config import settings
import mimetypes
import os
import re

app = FastAPI(title="Resmara API", version="0.2.0",
              # relative so the spec resolves both at /docs (direct) and /resmara/docs (behind the router)
              swagger_ui_parameters={"url": "openapi.json"})

# create_all() makes missing tables but never adds columns to existing ones, so new
# fields (graph ids, publish target, asset tagging) need this idempotent ALTER pass.
from app.db.migrate import migrate, encrypt_stored_tokens


@app.on_event("startup")
def _startup_migrations() -> None:
    """Schema and data migrations belong to the running app, not to importing this module.

    They used to run at import time. Once tokens started being encrypted at rest that became
    actively dangerous: any script or test that imported app.main would migrate - and
    re-encrypt - whatever database the environment happened to point at, with whatever key
    that process happened to have. Importing a module must never write to data.
    """
    added = migrate()
    locked = encrypt_stored_tokens()
    print(f"[resmara] startup migrations: {len(added)} columns added, {locked} token(s) encrypted")


@app.on_event("startup")
def _startup_clock_image() -> None:
    """The clock is a second Render service with its own image, and Render never rebuilds a cron
    job on a commit — so without this the clock runs yesterday's script forever. One GET, and its
    deploy is started when the two builds differ. Never raises (see app/services/clock_image.py)."""
    from app.services.clock_image import keep_in_step
    keep_in_step()

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
# Serve whatever UPLOAD_DIR actually is — uploads are written there by app/api/content.py, and
# Instagram fetches post media back through this mount. Hard-coding "uploads" here meant a
# deployment that set UPLOAD_DIR (a mounted volume, say) wrote files to one directory and served
# them from another, so every published picture 404'd.


def _upload_bytes(safe: str, on_disk: str):
    """The photo's bytes and content type: the file on disk, else the copy stored on its row."""
    if os.path.isfile(on_disk):
        with open(on_disk, "rb") as fh:
            return fh.read(), mimetypes.guess_type(on_disk)[0] or "application/octet-stream"
    from app.db.session import Asset, SessionLocal

    db = SessionLocal()
    try:
        asset = db.query(Asset).filter(Asset.filename == safe).first()
        if asset is not None and asset.data:
            return bytes(asset.data), asset.content_type or "image/jpeg"
    finally:
        db.close()
    return None, None


@app.get("/uploads/{filename}", include_in_schema=False)
def serve_upload(filename: str, w: int = 0):
    """The file from disk, the copy stored with the asset, or a preview of either.

    A hosted instance without a persistent volume starts empty, so an imported photo would
    otherwise be a 404 until someone re-uploaded it. Asset rows carry the bytes for exactly
    this case; this route is registered before the StaticFiles mount so it wins.

    `?w=` asks for a preview whose long edge is that many pixels. A page that draws a whole
    campaign (122 originals, 2-7 MB each) needs it: the console asks for 360 px thumbs and
    the full-size file stays one click away.
    """
    from fastapi import HTTPException
    from fastapi.responses import Response

    safe = os.path.basename(filename)
    on_disk = os.path.join(settings.UPLOAD_DIR, safe)
    raw, ctype = None, None
    if w or not os.path.isfile(on_disk):
        raw, ctype = _upload_bytes(safe, on_disk)
        if raw is None:
            raise HTTPException(status_code=404, detail="Not Found")
    if w:
        from app.services.thumbs import preview

        # A preview is made once and kept next to the uploads: the second look at a campaign,
        # and every reload, costs nothing. The directory lives with UPLOAD_DIR so a host with a
        # volume keeps it and a host without one simply starts empty again.
        cache_dir = os.path.join(settings.UPLOAD_DIR, ".thumbs")
        cached = os.path.join(cache_dir, "%d-%s" % (int(w), safe))
        if os.path.isfile(cached):
            return FileResponse(cached, media_type="image/jpeg",
                                headers={"Cache-Control": "public, max-age=604800, immutable"})
        small = preview(raw, w)
        if small:
            try:
                os.makedirs(cache_dir, exist_ok=True)
                tmp = cached + ".part"
                with open(tmp, "wb") as fh:
                    fh.write(small)
                os.replace(tmp, cached)          # atomically: a half-written preview never serves
            except OSError:
                pass                             # read-only disk: answer from memory this time
            return Response(content=small, media_type="image/jpeg",
                            headers={"Cache-Control": "public, max-age=604800, immutable"})
        # An unreadable original is still the picture the agent uploaded: serve it whole.
    if raw is not None:
        return Response(content=raw, media_type=ctype or "image/jpeg",
                        headers={"Cache-Control": "public, max-age=3600"})
    return FileResponse(on_disk)


app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")

app.include_router(api_router, prefix="/api")
# Engine 5: the listing websites and what visitors do on them (paths are absolute in the module).
from app.api.listing_pages import router as listing_pages_router  # noqa: E402
app.include_router(listing_pages_router)


@app.middleware("http")
async def listing_host(request, call_next):
    """homes.resmara.com/<slug> is the listing website; /photos/<file> its photos. One DNS record
    points the whole host at this app, so every house is just a path (Engine 5, section 9)."""
    host = (request.headers.get("host") or "").split(":")[0].lower()
    if host.startswith("homes."):
        path = request.scope.get("path") or "/"
        if path in ("/", ""):
            from fastapi.responses import RedirectResponse
            return RedirectResponse("https://www.resmara.com", status_code=302)
        first = path.strip("/").split("/")[0]
        if first not in ("photos", "api", "l") and "." not in first:
            request.scope["path"] = "/l/" + path.strip("/")
    return await call_next(request)


def _migrate_failures():
    """Columns the last startup could not add; [] is the healthy answer."""
    try:
        from app.db.migrate import failed_additions
        return failed_additions()
    except Exception:  # noqa: BLE001
        return []


@app.get("/api/version", include_in_schema=False)
def version():
    """Which commit is actually running here.

    Render answers the deploy hook with 202 and builds in the background, and a failed build
    keeps serving the previous container — so "the push went through" is not evidence that the
    code arrived. This makes it a one-line check, with no secret in the answer.
    """
    import os as _os
    from app.services import mail as _mail
    return {
        "commit": (_os.getenv("RENDER_GIT_COMMIT") or _os.getenv("GIT_COMMIT") or "unknown")[:12],
        "branch": _os.getenv("RENDER_GIT_BRANCH") or "",
        "env": settings.ENV,
        # Any column the last startup could not add. Empty is the healthy answer; a name here
        # means a feature reads a column that does not exist yet, and it is visible from a curl
        # instead of only in the dashboard's log.
        "migrations_failed": _migrate_failures(),
        # Whether transactional mail is connected. No key, no address, just yes or no — so
        # "did the provider I just configured take effect?" is a curl, not a guess.
        "mail": _mail.mail_configured(),
        "alerts": bool((_os.getenv("RESMARA_ALERT_WEBHOOK") or "").strip()),
    }


@app.get("/robots.txt", include_in_schema=False)
def robots():
    """A testing site should not be indexed. Remove this once the beta gate comes off."""
    if settings.SIGNUP_EMAILS or settings.SIGNUP_CODE:
        return Response(content="User-agent: *\nDisallow: /\n", media_type="text/plain")
    return Response(content="User-agent: *\nAllow: /\n", media_type="text/plain")

# Serve static frontend at root (after API routes)
if os.path.isdir("static"):
    # The browser keeps the script it fetched last week unless the URL changes. A fix that is on
    # the server but not in the page is a fix the customer cannot see: pressing the same dead
    # button after a deploy is what "still not working" looks like. Every shipped .js/.css is
    # therefore requested with ?v=<newest asset mtime>, and the HTML itself is sent no-cache so
    # the new URLs are actually read.
    _ASSET_REF = re.compile(r'(src|href)="([^":]+?\.(?:js|css))(?:\?[^"]*)?"')

    def _asset_stamp() -> str:
        newest = 0.0
        for root, _dirs, files in os.walk("static"):
            for name in files:
                if name.endswith((".js", ".css")):
                    try:
                        newest = max(newest, os.path.getmtime(os.path.join(root, name)))
                    except OSError:
                        pass
        return str(int(newest))

    def _index_html() -> HTMLResponse:
        with open(os.path.join("static", "index.html"), encoding="utf-8") as fh:
            page = fh.read()
        stamp = _asset_stamp()
        page = _ASSET_REF.sub(lambda m: '%s="%s?v=%s"' % (m.group(1), m.group(2), stamp), page)
        return HTMLResponse(page, headers={"Cache-Control": "no-cache"})

    @app.get("/", include_in_schema=False)
    def index_page():
        return _index_html()

    # The password-reset link is a real page (mail clients mangle fragments). It is the same
    # single-page app; the script reads ?token= and shows the reset form.
    @app.get("/reset", include_in_schema=False)
    def reset_page():
        return _index_html()

    # The confirmation link in the sign-up email lands here, and the script calls the API with
    # ?token= and shows the result (item 8: confirm the address before the first sign-in).
    @app.get("/confirm", include_in_schema=False)
    def confirm_page():
        return _index_html()

    # The legal pages at the clean URLs Meta asks for. They were only reachable as
    # /privacy.html, and "Privacy policy URL: https://www.resmara.com/privacy" is what the app
    # dashboard requires - a 404 there is an app-review rejection, not a broken link.
    _LEGAL = {"privacy": "privacy.html", "terms": "terms.html",
              "data-deletion": "data-deletion.html"}
    for _path, _file in _LEGAL.items():
        def _legal_page(_file=_file):
            return FileResponse(os.path.join("static", _file), media_type="text/html")
        app.add_api_route(f"/{_path}", _legal_page, methods=["GET"], include_in_schema=False)

    app.mount("/", StaticFiles(directory="static", html=True), name="static")
