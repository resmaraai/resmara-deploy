"""Idempotent column migrations for the Resmara SQLite database.

`Base.metadata.create_all` creates missing *tables* but never adds missing *columns*
to tables that already exist, so new fields on ad_accounts/posts/ads need an explicit
ALTER. This runs on every startup and is a no-op once the columns are present.
"""
import logging

from sqlalchemy import inspect, text
from app.db.session import engine

log = logging.getLogger("resmara.migrate")

# table -> [(column, DDL type/definition)]
ADDITIONS = {
    # A brand profile the customer entered has to outlive the browser it was typed in.
    "users": [
        ("brand", "JSON"),
        ("stripe_customer_id", "VARCHAR"),
        # Prepaid campaigns from a pack. An existing account keeps working with 0; the ALTER is
        # what stops every build on an established database failing on a missing column.
        ("campaign_credits", "INTEGER DEFAULT 0"),
        # Onboarding answers the product is required to remember (owner item 8): Meta connected,
        # setup session booked, tour shown. On an established database these arrive by ALTER.
        ("meta_connected_at", "TIMESTAMP"),
        ("setup_booked_at", "TIMESTAMP"),
        ("tour_seen_at", "TIMESTAMP"),
        # Email confirmation before first sign-in (item 8); added to existing databases by ALTER.
        ("email_confirmed_at", "TIMESTAMP"),
        # Team-marked test account (21 Nov 2026): kept out of Growth, Marketing and Finance counts.
        ("is_test", "BOOLEAN DEFAULT FALSE"),
        ("confirm_token_hash", "VARCHAR"),
        ("confirm_sent_at", "TIMESTAMP"),
        # The Team room's access list and the fail log the console reads. Both are read on
        # every console call, so an established database needs the ALTER before the page works.
        ("team_access", "JSON"),
        ("team_super_admin", "BOOLEAN DEFAULT 0"),
        ("team_invited_at", "TIMESTAMP"),
        # Engine 9 (Marketing): where the sign-up came from, and marketing consent. Marketing's
        # channel rows read these on every load, so an established database needs the ALTER.
        ("signup_source", "VARCHAR"),
        ("signup_source_detail", "JSON"),
        ("marketing_optin", "BOOLEAN DEFAULT 1"),
        # Engine 1 Part A: Facebook is the way in. On an established database these arrive by
        # ALTER; the unique index is created separately because ADD COLUMN cannot carry it.
        ("facebook_id", "VARCHAR"),
        ("facebook_name", "VARCHAR"),
        ("terms_accepted_at", "TIMESTAMP"),
        ("terms_version", "VARCHAR"),
        ("signup_ip", "VARCHAR"),
        ("signup_ua", "VARCHAR"),
        # Close (reversible) and delete (permanent) cannot share one flag.
        ("closed_at", "TIMESTAMP"),
        ("needs_email", "BOOLEAN DEFAULT FALSE"),
    ],
    "ad_accounts": [
        ("refresh_token", "TEXT"),
        ("token_expires_at", "DATETIME"),
        ("page_id", "VARCHAR"),
        ("ig_user_id", "VARCHAR"),
        ("token_status", "VARCHAR"),
        ("token_checked_at", "DATETIME"),
        ("token_note", "TEXT"),
        ("funding_status", "VARCHAR"),
        ("funding_note", "TEXT"),
        ("account_status", "INTEGER"),
        ("account_checked_at", "DATETIME"),
        ("token_refreshed_at", "DATETIME"),
        ("token_refresh_note", "TEXT"),
    ],
    "posts": [
        ("publish_target", "VARCHAR DEFAULT 'both'"),
        ("last_error", "TEXT"),
        # The plan's creative (title, kicker, text overlay, which space the photo shows) used to be
        # dropped when the post was written, so the calendar had nothing to show over the image.
        ("title", "VARCHAR"),
        ("kicker", "VARCHAR"),
        ("overlay_text", "VARCHAR"),
        ("photo_room", "VARCHAR"),
        ("photo_file", "VARCHAR"),
        ("post_type", "VARCHAR DEFAULT 'photo'"),
        # The failed-post ladder: an established database has none of these, and the publisher
        # now reads them on every sweep, so each needs its own ALTER.
        ("publish_attempts", "INTEGER DEFAULT 0"),
        ("next_attempt_at", "VARCHAR"),
        ("failure_kind", "VARCHAR"),
        ("failure_note", "TEXT"),
        ("failed_at", "DATETIME"),
        ("failure_notified_at", "DATETIME"),
        ("fail_log", "JSON"),
        # Engine 4: two captions, Facebook tags, post style, the thumbs, Needs a look.
        ("caption_ig", "TEXT"),
        ("hashtags_fb", "TEXT"),
        ("design_style", "VARCHAR"),
        ("details_treatment", "VARCHAR"),
        ("rating", "INTEGER"),
        ("needs_look", "BOOLEAN DEFAULT 0"),
        ("features", "JSON"),
    ],
    "ads": [
        ("meta_adset_id", "VARCHAR"),
        ("meta_creative_id", "VARCHAR"),
        ("reach", "INTEGER"),
        ("last_error", "TEXT"),
        # One ad per campaign, carousel or video (Ad Engine §4.2, §8). The format and the
        # card list are what the campaign page renders and what the performance loop learns
        # from, so they are columns and not transient JSON.
        ("format", "VARCHAR"),
        ("card_post_ids", "JSON"),
        ("image_hashes", "JSON"),
        ("meta_campaign_id", "VARCHAR"),
        ("meta_video_id", "VARCHAR"),
        ("video_url", "TEXT"),
        ("destination_url", "TEXT"),
    ],
    # Listing photos live in the row, not only on disk: a free-tier instance has no volume,
    # so every deploy and every idle restart wipes uploads/ and leaves image_url pointing at
    # a 404. Bytes are stored next to the asset so the photo survives a restart.
    "assets": [
        ("data", "BYTEA"),
        ("content_type", "VARCHAR"),
    ],
    # A campaign is bought, not credited: these columns on an existing install are what let
    # the build gate ask "was this campaign paid for?" without a second query.
    "boosts": [
        ("paid_at", "TIMESTAMP"),
        ("paid_amount_cents", "INTEGER"),
        # Hiding a campaign from the list is reversible and keeps its history; only the flag
        # changes. A duplicate "boosts" key here would have silently dropped this entry, so
        # every boost column belongs in this one block.
        ("hidden", "BOOLEAN DEFAULT FALSE"),
        # Which campaign this is for the listing (0 = the first). The build rotates the gallery
        # and asks for new copy when a repeat campaign runs on the same house.
        ("repeat_round", "INTEGER DEFAULT 0"),
        # "Run it until it sells" is a fact about the campaign, not a browser preference: the
        # scheduler reads it to build and charge the next round, and the listing check clears it.
        ("until_sold", "BOOLEAN DEFAULT FALSE"),
        ("until_sold_at", "TIMESTAMP"),
        # --- Digital Ad Engine v1.3 (§8): the launch details, the pause state, the listing
        # watcher and the $39 re-run all live on the boost. Every one of these is NULL/absent
        # on an established database, so each needs its own ALTER here.
        ("destination_url", "TEXT"),
        ("listing_url", "TEXT"),
        ("video_url", "TEXT"),
        ("budget_confirmed_at", "TIMESTAMP"),
        ("parent_boost_id", "INTEGER"),
        ("paused_at", "TIMESTAMP"),
        ("paused_days", "INTEGER DEFAULT 0"),
        ("listing_status", "VARCHAR"),
        ("photo_permission_at", "TIMESTAMP"),
        ("video_found_at", "TIMESTAMP"),
        ("listing_checked_at", "TIMESTAMP"),
        # The social-leads scan's own heartbeat (Post Engine §10.4): when it ran and what it
        # saw. Without these, "no leads yet" and "Meta refused the call" look identical.
        ("leads_checked_at", "TIMESTAMP"),
        ("leads_scan_note", "TEXT"),
        ("reboost_offer_sent_at", "TIMESTAMP"),
        # Engine 9 (Marketing): the channel credited with each purchase, decided once at payment.
        ("paid_source", "VARCHAR"),
        ("paid_source_detail", "JSON"),
    ],
    # The agent's note on a lead (added 21 Nov 2026).
    "leads": [
        ("note", "TEXT"),
        ("email", "VARCHAR"),
        ("phone", "VARCHAR"),
        ("visitor", "VARCHAR"),
        ("wants", "VARCHAR"),
    ],
    "orders": [
        ("user_id", "INTEGER"),
        ("boost_id", "INTEGER"),
        ("amount_cents", "INTEGER"),
        ("currency", "VARCHAR"),
        ("status", "VARCHAR"),
        ("stripe_session_id", "VARCHAR"),
        ("stripe_payment_intent", "VARCHAR"),
        ("checkout_url", "TEXT"),
        ("created_at", "TIMESTAMP"),
        ("paid_at", "TIMESTAMP"),
    ],
    # The build room shipped its assigned_to column after the board was already live, and
    # create_all never adds a column to an existing table — without this ALTER the board on an
    # established database fails on a missing column the first time a task is read.
    "buildroom_tasks": [
        ("assigned_to", "VARCHAR(160)"),
    ],
}

# SQLite has no BYTEA.
_DIALECT_TYPES = {("assets", "data"): {"postgresql": "BYTEA", "sqlite": "BLOB"}}


def encrypt_stored_tokens() -> int:
    """One-time upgrade: encrypt any token still stored in plaintext. No-op afterwards.

    Deliberately uses the raw connection and not the AdAccount model: the model's
    `access_token` property would decrypt on read, which for a legacy plaintext value is a
    no-op but for anything already encrypted would double-handle it. Working in SQL keeps
    this a dumb, idempotent data fix.
    """
    from app.core.crypto import encrypt, is_encrypted
    changed = 0
    insp = inspect(engine)
    if "ad_accounts" not in set(insp.get_table_names()):
        return 0
    with engine.begin() as conn:
        rows = conn.execute(text("SELECT id, access_token, refresh_token FROM ad_accounts")).fetchall()
        for row_id, token, refresh in rows:
            sets, params = [], {}
            if token and not is_encrypted(token):
                sets.append("access_token = :token")
                params["token"] = encrypt(token)
            if refresh and not is_encrypted(refresh):
                sets.append("refresh_token = :refresh")
                params["refresh"] = encrypt(refresh)
            if sets:
                params["rowid"] = row_id
                conn.execute(text(f"UPDATE ad_accounts SET {', '.join(sets)} WHERE id = :rowid"), params)
                changed += 1
    return changed


def migrate() -> list[str]:
    """Add any missing columns. Returns the list of column names actually added."""
    added, failed = [], []
    insp = inspect(engine)
    dialect = engine.dialect.name
    existing_tables = set(insp.get_table_names())
    for table, cols in ADDITIONS.items():
        if table not in existing_tables:
            continue
        have = {c["name"] for c in insp.get_columns(table)}
        for name, ddl in cols:
            if name in have:
                continue
            per_dialect = _DIALECT_TYPES.get((table, name))
            if per_dialect:
                ddl = per_dialect.get(dialect, ddl)
            ddl = _ddl_for(ddl, dialect)
            # One statement per transaction, and a failure is logged and skipped: a single bad
            # ADD COLUMN once took the whole site down with "type datetime does not exist",
            # because the exception propagated out of startup. A missing column is a bug to fix;
            # refusing to boot is an outage.
            try:
                with engine.begin() as conn:
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {ddl}"))
                added.append(f"{table}.{name}")
            except Exception as exc:  # noqa: BLE001
                failed.append(f"{table}.{name}: {type(exc).__name__}: {str(exc)[:160]}")
    if failed:
        log.error("migrate: %d column(s) could not be added: %s", len(failed), "; ".join(failed))
    migrate._failed = failed
    # Columns are not the whole schema: the unique facebook_id is the promise that one Facebook
    # account is one Resmara account, and ADD COLUMN cannot carry a constraint.
    try:
        ensure_unique_indexes()
    except Exception as exc:  # noqa: BLE001 - an index problem must not stop the boot
        log.error("migrate: unique indexes: %s: %s", type(exc).__name__, str(exc)[:160])
    return added


def _ddl_for(ddl: str, dialect: str) -> str:
    """Translate the SQLite-flavoured DDL to what this database actually understands."""
    if dialect == "postgresql":
        # Postgres has no DATETIME; SQLite has no TIMESTAMPTZ, so this only ever narrows one way.
        # It also has no truthy integer where a boolean is expected: "BOOLEAN DEFAULT 0" is a
        # syntax error there, so the SQLite spelling is translated rather than duplicated in
        # ADDITIONS (which every other table reads as SQLite).
        return (ddl.replace("DATETIME", "TIMESTAMP")
                   .replace("BOOLEAN DEFAULT 0", "BOOLEAN DEFAULT FALSE")
                   .replace("BOOLEAN DEFAULT 1", "BOOLEAN DEFAULT TRUE"))
    return ddl


def ensure_unique_indexes() -> list[str]:
    """Indexes ADD COLUMN cannot carry (a unique facebook_id, a unique Page).

    Postgres and SQLite both accept a unique index on an existing column, and both ignore a
    duplicate, so this is safe on every boot. The Facebook one is the promise behind "the same
    Facebook account always lands on the same Resmara account": without it, a race between two
    sign-ins could create two accounts for one person.
    """
    wanted = [("users", "ix_users_facebook_id_unique", "facebook_id"),
              # One Page, one Resmara account (Engine 1 Part B, section 3).
              ("meta_connections", "ix_meta_connections_page_unique", "page_id")]
    done = []
    for table, index, column in wanted:
        try:
            with engine.begin() as conn:
                conn.execute(text(f"CREATE UNIQUE INDEX IF NOT EXISTS {index} ON {table} ({column})"))
            done.append(index)
        except Exception as exc:  # noqa: BLE001 - a duplicate row must not stop the boot
            log.error("migrate: unique index %s skipped: %s: %s", index, type(exc).__name__, str(exc)[:160])
    return done


def failed_additions() -> list[str]:
    """The ALTERs that could not be applied on the last migrate() - shown by /api/version."""
    return list(getattr(migrate, "_failed", []))


if __name__ == "__main__":
    print("added:", migrate() or "nothing (schema already current)")
    print("tokens encrypted:", encrypt_stored_tokens())
