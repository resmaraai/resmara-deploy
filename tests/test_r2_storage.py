#!/usr/bin/env python3
"""Photo storage: R2 when it is configured, the database row when it is not — and the row again
the moment an upload fails.

The switch exists because a campaign is ~50 MB of photos: Render's Postgres charges $0.30/GB-month
for those bytes and a 1 GB database is full after about twenty campaigns, while R2 is free to
10 GB. But the cost saving is only worth having if it cannot lose a photo, so what is pinned here:

  * with no R2 environment the mode is "database" and nothing is uploaded anywhere
  * with R2 configured, a file goes up under a predictable key and its public URL comes back
  * a failed upload returns None, which every caller reads as "keep the bytes in the row"
  * an incomplete environment is described by name, so the switch can be finished without a
    deploy
  * the upload endpoint stores the R2 URL and no bytes at all — that is the whole saving
"""
from __future__ import annotations

import io
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

FAILS = 0


def check(label: str, cond: bool, detail: str = "") -> None:
    global FAILS
    if cond:
        print("  ok   %s" % label)
    else:
        FAILS += 1
        print("  FAIL %s %s" % (label, detail))


class FakeS3:
    """Stands in for boto3's client so the test needs no credentials and no network."""

    def __init__(self, explode: bool = False):
        self.puts = []
        self.deletes = []
        self.explode = explode

    def put_object(self, **kwargs):
        if self.explode:
            raise RuntimeError("bucket refused it")
        self.puts.append(kwargs)
        return {"ETag": "fake"}

    def delete_object(self, **kwargs):
        self.deletes.append(kwargs)
        return {}


def main() -> int:
    tmp = tempfile.mkdtemp(prefix="resmara-storage-")
    os.environ["RESMARA_UPLOAD_DIR"] = tmp
    os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(tmp, "storage.db")
    os.environ.setdefault("SECRET_KEY", "test-secret-key-for-storage")
    os.environ["RESMARA_ADMIN_EMAILS"] = "owner@example.com"
    for key in ("R2_ACCOUNT_ID", "R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY", "R2_BUCKET",
                "R2_PUBLIC_BASE_URL"):
        os.environ.pop(key, None)

    from app.services import storage

    # ── without R2, nothing changes ───────────────────────────────────────────
    check("no environment means the database", storage.mode() == "database", storage.mode())
    check("and an upload is a no-op that says so",
          storage.put("photo.jpg", b"bytes", "image/jpeg") is None)
    note = storage.note()
    check("the note names what is missing", "R2_ACCOUNT_ID" in note, note)
    check("status reports the missing names", len(storage.status()["missing"]) == 4,
          str(storage.status()["missing"]))

    # ── configured: uploads go up, with a URL that can be served ──────────────
    os.environ.update({"R2_ACCOUNT_ID": "acct123", "R2_ACCESS_KEY_ID": "key",
                       "R2_SECRET_ACCESS_KEY": "secret", "R2_BUCKET": "resmara-photos",
                       "R2_PUBLIC_BASE_URL": "https://photos.example.com/"})
    check("credentials switch the mode", storage.mode() == "r2", storage.mode())
    fake = FakeS3()
    original_client = storage._client
    storage._client = lambda: fake
    try:
        url = storage.put("photo-1.jpg", b"jpeg-bytes", "image/jpeg")
        check("an upload returns its public URL",
              url == "https://photos.example.com/campaigns/photo-1.jpg", str(url))
        check("under a campaign key", fake.puts and fake.puts[0]["Key"] == "campaigns/photo-1.jpg",
              str(fake.puts[:1]))
        check("with the right bucket", fake.puts[0]["Bucket"] == "resmara-photos")
        check("and the content type the browser needs",
              fake.puts[0]["ContentType"] == "image/jpeg", str(fake.puts[0].get("ContentType")))
        check("cached hard, because a photo never changes",
              "immutable" in str(fake.puts[0].get("CacheControl")), str(fake.puts[0].get("CacheControl")))
        check("delete removes the same key", storage.delete("photo-1.jpg") is True
              and fake.deletes[0]["Key"] == "campaigns/photo-1.jpg", str(fake.deletes[:1]))
    finally:
        storage._client = original_client

    # ── a failing bucket must not lose the photo ──────────────────────────────
    storage._client = lambda: FakeS3(explode=True)
    try:
        check("a failed upload returns None so the caller keeps the bytes",
              storage.put("photo-2.jpg", b"jpeg-bytes", "image/jpeg") is None)
    finally:
        storage._client = original_client

    # ── the upload endpoint stores the URL and no bytes ───────────────────────
    from fastapi.testclient import TestClient
    from app.main import app
    from app.core.security import get_password_hash
    from app.db.session import Base, engine, SessionLocal, Asset, Boost, User
    import app.api.content as content_api

    Base.metadata.create_all(bind=engine)
    client = TestClient(app)
    with SessionLocal() as db:
        db.add(User(email="agent@example.com", name="agent",
                    hashed_password=get_password_hash("storage-pass-123"), is_active=True,
                    subscription_status="active"))
        db.commit()
        uid = db.query(User).filter(User.email == "agent@example.com").first().id
        boost = Boost(user_id=uid, address="4 Storage Way")
        db.add(boost)
        db.commit()
        bid = boost.id
    r = client.post("/api/auth/login",
                    data={"username": "agent@example.com", "password": "storage-pass-123"})
    headers = {"Authorization": "Bearer %s" % r.json().get("access_token", "")}

    fake = FakeS3()
    storage._client = lambda: fake
    try:
        r = client.post("/api/content/upload/photo",
                        headers=headers,
                        data={"boost_id": str(bid), "kind": "photo"},
                        files={"file": ("listing.jpg", io.BytesIO(b"x" * 4096), "image/jpeg")})
        check("the upload succeeds", r.status_code == 201, str(r.status_code) + " " + r.text[:200])
        with SessionLocal() as db:
            asset = (db.query(Asset).filter(Asset.boost_id == bid)
                     .order_by(Asset.id.desc()).first())
            check("it stores the R2 URL", asset is not None
                  and str(asset.url).startswith("https://photos.example.com/campaigns/"),
                  str(asset and asset.url))
            check("and keeps no bytes in the database — the whole saving",
                  asset is not None and asset.data is None,
                  "bytes=%s" % (asset and (len(asset.data) if asset.data else 0)))
        check("the object actually went up", len(fake.puts) == 1, str(len(fake.puts)))
    finally:
        storage._client = original_client
        os.environ.pop("R2_PUBLIC_BASE_URL", None)

    # ── credentials without a public URL must not break serving ───────────────
    check("a missing public URL is called out instead of serving broken images",
          "R2_PUBLIC_BASE_URL" in storage.note(), storage.note())
    check("and nothing is uploaded in that state",
          storage.put("photo-3.jpg", b"bytes", "image/jpeg") is None)

    if FAILS:
        print("FAIL — %d check(s) failed" % FAILS)
        return 1
    print("PASS — photos move to R2 when it is configured, stay in the database when it is not,\n"
          "       and never disappear when the bucket misbehaves")
    return 0


if __name__ == "__main__":
    sys.exit(main())
