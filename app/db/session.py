import os
from sqlalchemy import create_engine, Column, Integer, String, Text, Float, Boolean, DateTime, ForeignKey, func, JSON, LargeBinary, Date, UniqueConstraint
from sqlalchemy.orm import deferred
from sqlalchemy.orm import sessionmaker, declarative_base

from app.db.urls import normalize_database_url

SQLALCHEMY_DATABASE_URL = normalize_database_url(os.getenv("DATABASE_URL", "sqlite:///./resmara.db"))
if "sqlite" in SQLALCHEMY_DATABASE_URL:
    connect_args = {"check_same_thread": False}
else:
    connect_args = {}

engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# --- User/Agent ---
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    name = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    subscription_status = Column(String, default="inactive")
    last_login = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    # The customer's brand profile (agent name, brokerage, colours, voice, website...).
    # Until this column existed the profile lived only in one browser's localStorage, so
    # clearing storage or signing in on another machine lost work the customer had done.
    brand = Column(JSON, default=dict)
    # The Stripe Customer this account pays as. Created on the first checkout and reused after
    # that, so Checkout can show the saved card instead of asking for it again.
    stripe_customer_id = Column(String, nullable=True)
    billing_hold = Column(String, nullable=True)       # Engine 10: "dispute" pauses new charges
    # Campaigns this account has already paid for and not yet built. A pack purchase is what
    # makes this non-zero and building a campaign spends one (api/billing.require_paid). It is
    # a pre-paid balance, not credit we invented: every unit arrived as a Stripe payment.
    campaign_credits = Column(Integer, default=0, nullable=False)
    # Onboarding facts that must survive a cleared browser (owner item 8): when Meta was
    # connected, when a setup session was booked, and whether the first-visit tour was shown.
    # Stored here rather than in localStorage because "every sign-in lands on Accounts until
    # Meta is connected" cannot be enforced by a browser.
    meta_connected_at = Column(DateTime(timezone=True), nullable=True)
    setup_booked_at = Column(DateTime(timezone=True), nullable=True)
    tour_seen_at = Column(DateTime(timezone=True), nullable=True)
    # Email confirmation before the first sign-in (item 8). The token is stored hashed: a dumped
    # database must not be a pile of working confirmation links.
    email_confirmed_at = Column(DateTime(timezone=True), nullable=True)
    # Marked by the team as a test account (e.g. a demo client like 'Coggins'): left out of every
    # Team room count. Accounts on test emails are caught by app.core.testdata anyway.
    is_test = Column(Boolean, default=False)
    confirm_token_hash = Column(String, nullable=True)
    confirm_sent_at = Column(DateTime(timezone=True), nullable=True)
    # Team room access. A team member is a normal account with a list of the console's sections
    # they may read; someone with no list and no flag is a customer and gets nothing. Access is
    # checked on the server for every console endpoint, so the page's hiding is a courtesy and
    # not the fence.
    team_access = Column(JSON, nullable=True)
    team_super_admin = Column(Boolean, default=False)
    team_invited_at = Column(DateTime(timezone=True), nullable=True)
    # --- Engine 9 (Marketing) ---------------------------------------------------
    # Where this sign-up came from: "ad", "email" or "website". Stamped once, when the account
    # is made, and never changed afterwards - the channel rows on Marketing are only honest if
    # the stamp cannot be rewritten by a later visit.
    signup_source = Column(String, nullable=True)
    # The raw evidence for the stamp (utm_*, fbclid, the ad or campaign id, the referrer), kept
    # so a number can be explained later without guessing what the tags were.
    signup_source_detail = Column(JSON, nullable=True)
    # The one-line marketing consent at sign-up, and the on/off switch on the account. It is
    # stored here rather than only in Mailchimp because "someone unsubscribed" has to survive a
    # sync that has not run yet.
    marketing_optin = Column(Boolean, default=True)
    # --- Engine 1 Part A (login) ------------------------------------------------
    # Facebook is the way in (Adam, 22 Nov), so the account is keyed by the Facebook user id.
    # Unique: the same Facebook account logging in twice must land on the same account, never
    # a second one.
    facebook_id = Column(String, unique=True, index=True, nullable=True)
    facebook_name = Column(String, nullable=True)
    # Consent, recorded before the Facebook redirect and stamped on the account it creates:
    # which Terms version, when, and from where. New accounts only.
    terms_accepted_at = Column(DateTime(timezone=True), nullable=True)
    terms_version = Column(String, nullable=True)
    signup_ip = Column(String, nullable=True)
    signup_ua = Column(String, nullable=True)
    # "Close my account" (reversible, keeps campaigns/leads/reports) is deliberately not the
    # same thing as "Delete my data" (permanent). One timestamp cannot mean both.
    closed_at = Column(DateTime(timezone=True), nullable=True)
    # Facebook sometimes hides the email. The account still works; we ask once, for receipts.
    needs_email = Column(Boolean, default=False)

# --- Ad Account (OAuth) ---
class AdAccount(Base):
    __tablename__ = "ad_accounts"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    platform = Column(String, nullable=False)  # meta, tiktok, google-ads
    advertiser_id = Column(String, nullable=False)
    account_name = Column(String, nullable=True)
    currency = Column(String, default="USD")
    budget = Column(Float, default=0.0)
    # Stored encrypted (see app/core/crypto.py). The underscore attribute is what SQLAlchemy
    # maps; the public `access_token` property below transparently decrypts on read and
    # encrypts on write, so every existing caller keeps working unchanged while the
    # database file alone no longer hands over a customer's ad account.
    _access_token = Column("access_token", Text, nullable=True)
    _refresh_token = Column("refresh_token", Text, nullable=True)
    token_expires_at = Column(DateTime(timezone=True), nullable=True)
    # Token/account health, refreshed by app/services/token_health.py. A client-billed
    # account is the customer's own ad account with the customer's own card on it, so both
    # "is our token still good" and "can this account actually spend" have to be answerable.
    token_status = Column(String, nullable=True)        # healthy | expiring | needs_reconnect | simulated
    token_checked_at = Column(DateTime(timezone=True), nullable=True)
    token_note = Column(Text, nullable=True)            # Meta's own wording, never invented
    token_refreshed_at = Column(DateTime(timezone=True), nullable=True)  # last refresh attempt
    # What the last refresh actually achieved. Meta sometimes returns a new token with the
    # SAME expiry, and saying "renewed" there would be a lie the client only discovers when
    # the ads stop.
    token_refresh_note = Column(Text, nullable=True)
    funding_status = Column(String, nullable=True)      # has_funding | no_funding
    funding_note = Column(Text, nullable=True)
    account_status = Column(Integer, nullable=True)     # Meta account_status enum (1 = ACTIVE)
    account_checked_at = Column(DateTime(timezone=True), nullable=True)
    # Publishing targets: the FB Page and the IG business account this boost posts to.
    page_id = Column(String, nullable=True)
    ig_user_id = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # --- token access: plaintext to the app, ciphertext in the database ---
    @property
    def access_token(self):
        from app.core.crypto import decrypt
        return decrypt(self._access_token)

    @access_token.setter
    def access_token(self, value):
        from app.core.crypto import encrypt
        self._access_token = encrypt(value)

    @property
    def refresh_token(self):
        from app.core.crypto import decrypt
        return decrypt(self._refresh_token)

    @refresh_token.setter
    def refresh_token(self, value):
        from app.core.crypto import encrypt
        self._refresh_token = encrypt(value)


# --- Listing website (Engine 5) ---
class ListingSite(Base):
    """One website per home: homes.resmara.com/<slug>. Written by the campaign build, drawn by
    one template in code (app/services/listing_site.py). The slug never changes."""
    __tablename__ = "listing_sites"
    id = Column(Integer, primary_key=True, index=True)
    boost_id = Column(Integer, ForeignKey("boosts.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    slug = Column(String, nullable=False, unique=True, index=True)
    status = Column(String, default="built")          # built | live | pending | sold | ended
    version = Column(Integer, default=1)
    content = Column(JSON, default={})                 # facts, headline, chapters, note, neighborhood, photos
    brand = Column(JSON, default={})                   # brand kit snapshot (section 9)
    checks = Column(JSON, default=[])                  # what the build checked, and any safe defaults used
    # Section 3a: the price. Shown only when the sources agree; hidden the moment a change is suspected.
    price_cents = Column(Integer, nullable=True)       # the price on the page, or None
    price_mode = Column(String, default="auto")        # auto | agent | none
    price_hold = Column(String, nullable=True)         # why the price is off while auto (a change suspected)
    price_seen = Column(JSON, default={})              # last readings by source
    price_email_at = Column(DateTime(timezone=True), nullable=True)
    price_token = Column(String, nullable=True, index=True)
    price_token_at = Column(DateTime(timezone=True), nullable=True)
    share_asset_id = Column(Integer, nullable=True)    # the 1200x630 share image
    checked_at = Column(DateTime(timezone=True), nullable=True)   # the daily load check
    check_note = Column(Text, nullable=True)
    ended_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class ListingVisit(Base):
    """A visitor on a listing website, at most one row per visitor per day."""
    __tablename__ = "listing_visits"
    __table_args__ = (UniqueConstraint("site_id", "visitor", "day", name="uq_listing_visit_day"),)
    id = Column(Integer, primary_key=True, index=True)
    site_id = Column(Integer, ForeignKey("listing_sites.id", ondelete="CASCADE"), nullable=False, index=True)
    visitor = Column(String, nullable=False)
    day = Column(String, nullable=False)               # YYYY-MM-DD (UTC)
    source = Column(String, nullable=True)             # utm_content: which post or the ad
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# --- Meta connection (Engine 1 Part B) ---
class MetaConnection(Base):
    """One Meta connection per agent: their login, the Page they chose, its Instagram and the
    ad account in use. Saved on every Facebook login, even with no Page and no ad account,
    and overwritten (never ``or``-ed) on every reconnect and Check again. Ad accounts stay in
    ``ad_accounts`` for the ad engine and billing; this row points at the one in use.
    See docs/engines/meta-integration-engine.md, section 4.
    """
    __tablename__ = "meta_connections"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    fb_user_id = Column(String, nullable=True)
    fb_user_name = Column(String, nullable=True)
    fb_user_picture = Column(Text, nullable=True)
    _token = Column("token_enc", Text, nullable=True)
    _page_token = Column("page_token_enc", Text, nullable=True)
    token_expires_at = Column(DateTime(timezone=True), nullable=True)
    token_status = Column(String, nullable=True)      # healthy | expiring | needs_reconnect | unknown
    scopes_granted = Column(JSON, default=list)
    scopes_declined = Column(JSON, default=list)
    page_id = Column(String, nullable=True, index=True)
    page_name = Column(String, nullable=True)
    page_picture = Column(Text, nullable=True)
    page_tasks = Column(JSON, default=list)
    page_published = Column(Boolean, nullable=True)
    page_chosen = Column(Boolean, default=False)      # the agent picked it (or it was the only one)
    page_info = Column(JSON, default=dict)            # website, phone, address, category, about: for the Brand engine
    pages_available = Column(JSON, default=list)      # [{id, name, picture, tasks, published, ig_id, ig_username}]
    ig_user_id = Column(String, nullable=True)
    ig_username = Column(String, nullable=True)
    ig_picture = Column(Text, nullable=True)
    ad_account_id = Column(Integer, ForeignKey("ad_accounts.id"), nullable=True)
    ad_account_name = Column(String, nullable=True)
    ad_account_owner = Column(String, nullable=True)  # their own, or the brokerage business that owns it
    issues = Column(JSON, default=list)               # current outcome keys, most important first
    issue_log = Column(JSON, default=list)            # the setup to-do list: [{key, found_at, fixed_at}]
    capabilities = Column(JSON, default=dict)         # {fb_post, ig_post, ad, download_mode, campaigns_allowed}
    last_checked_at = Column(DateTime(timezone=True), nullable=True)
    last_check_source = Column(String, nullable=True) # connect | sign_in | check_again | sweep | daily | pre_publish
    unreachable_since = Column(DateTime(timezone=True), nullable=True)
    breakage_emails = Column(JSON, default=dict)      # {key: [sent_at, ...]} for after-onboarding breakages
    first_connected_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    @property
    def access_token(self):
        from app.core.crypto import decrypt
        return decrypt(self._token)

    @access_token.setter
    def access_token(self, value):
        from app.core.crypto import encrypt
        self._token = encrypt(value)

    @property
    def page_access_token(self):
        from app.core.crypto import decrypt
        return decrypt(self._page_token)

    @page_access_token.setter
    def page_access_token(self, value):
        from app.core.crypto import encrypt
        self._page_token = encrypt(value)

# --- Creative ---
class Creative(Base):
    __tablename__ = "creatives"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    asset_url = Column(Text, nullable=False)
    asset_type = Column(String, nullable=False)
    asset_name = Column(String, nullable=True)
    render_status = Column(String, default="PENDING")  # PENDING, APPROVED
    copy_text = Column(Text, nullable=True)
    cta_text = Column(String, nullable=True)
    landing_page_url = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

# --- Boost (Campaign) ---
class Boost(Base):
    __tablename__ = "boosts"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    ad_account_id = Column(Integer, ForeignKey("ad_accounts.id"), nullable=True)
    address = Column(String, nullable=False)
    tier = Column(String, default="bap_shoot_499")
    main_status = Column(String, default="In Progress")
    go_live_date = Column(String, nullable=True)
    campaign_days = Column(Integer, default=14)
    ad_budget_usd = Column(Float, default=50.0)
    property_facts = Column(Text, nullable=True)
    brand_profile = Column(JSON, default={})
    plan = Column(JSON, default={})
    ad_brief = Column(JSON, default={})
    meta_campaign_id = Column(String, nullable=True)
    stage = Column(String, default="PENDING")  # PENDING, LIVE, COMPLETE
    # Hidden from the campaign list without destroying it: a finished campaign still has a
    # report worth reading, so "hide" is a flag on the row, not a delete.
    hidden = Column(Boolean, default=False)
    # Which campaign this is for the listing: 0 for the first, 1 for the next one started from
    # it, and so on. The build rotates the gallery and asks for new copy when it is above 0.
    repeat_round = Column(Integer, default=0)
    # "Run it until it sells": the agent has asked for a fresh 14-day round (and a $39 renewal)
    # every two weeks until the listing is pending or sold. False on every existing campaign, and
    # the front end used to keep this in the browser by address - which meant nothing on the server
    # could build the next round or stop it. This is the record it needed.
    until_sold = Column(Boolean, default=False)
    until_sold_at = Column(DateTime(timezone=True), nullable=True)
    # Engine 10 §8: the agreement behind an automatic renewal — Terms version, when it was
    # accepted, and from which IP and browser. Kept when the switch is turned off (three years,
    # or one year after it is turned off), which is why the off switch stamps a date instead of
    # nulling these: a recurring charge with no record of the agreement is the one audit an
    # agent would win.
    renewal_consent_at = Column(DateTime(timezone=True), nullable=True)
    renewal_consent_version = Column(String, nullable=True)
    renewal_consent_ip = Column(String, nullable=True)
    renewal_consent_ua = Column(String, nullable=True)
    renewal_consent_off_at = Column(DateTime(timezone=True), nullable=True)
    # A campaign is bought, not credited: $49 at checkout sets these, and the build/launch
    # gates read them. Both null = nobody has paid for this campaign yet.
    paid_at = Column(DateTime(timezone=True), nullable=True)
    paid_amount_cents = Column(Integer, nullable=True)
    # --- Digital Ad Engine v1.3 -------------------------------------------------
    # The listing link the agent pasted, and the optional click destination from launch
    # details. Left blank, the ad and the posts send clicks to the listing.
    listing_url = Column(Text, nullable=True)
    destination_url = Column(Text, nullable=True)
    # The listing's video, when the link had one: it becomes the ad and the day-1 post.
    video_url = Column(Text, nullable=True)
    budget_confirmed_at = Column(DateTime(timezone=True), nullable=True)
    # Round n+1 points at the campaign it continues, so a listing keeps its history.
    parent_boost_id = Column(Integer, nullable=True)
    paused_at = Column(DateTime(timezone=True), nullable=True)
    paused_days = Column(Integer, default=0)
    # active | pending | sold | contingent | unknown — written by the daily watcher.
    listing_status = Column(String, nullable=True)
    # When the agent ticked "I have permission to use these photos" (item 9). Meta and the
    # agent's broker both expect that answer to exist, and a timestamp is the only version of
    # it that can be shown to them later.
    photo_permission_at = Column(DateTime, nullable=True)
    # When the listing video was found (Post Engine §6.6). The footage stays at its public URL;
    # Meta pulls it from there and Resmara never stores the file.
    video_found_at = Column(DateTime, nullable=True)
    listing_checked_at = Column(DateTime(timezone=True), nullable=True)
    # The social-leads scan: when it last ran for this campaign and what it saw, so "no leads
    # yet" and "Meta refused the comments call" stop looking the same on the campaign page.
    leads_checked_at = Column(DateTime(timezone=True), nullable=True)
    leads_scan_note = Column(Text, nullable=True)
    reboost_offer_sent_at = Column(DateTime(timezone=True), nullable=True)
    # Engine 6: pending and sold
    paused_reason = Column(String, nullable=True)       # agent | pending | sold
    listing_sources = Column(JSON, default=list)        # the agent's link + the same home elsewhere
    listing_reads = Column(JSON, default=dict)          # last read per source: status, price, agent, layer, quote
    listing_notes = Column(JSON, default=dict)          # one-time emails and alerts already sent
    # --- Engine 9 (Marketing) ---------------------------------------------------
    # Which channel gets credit for this purchase: "ad", "email" or "website". Decided once, when
    # the payment lands, by the last thing that got them to buy (Engine 9, section 1a) - so a
    # campaign bought after a day-5 email counts once, for Email, and never twice.
    paid_source = Column(String, nullable=True)
    paid_source_detail = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    launched_at = Column(DateTime(timezone=True), nullable=True)

# --- Post ---
class Post(Base):
    __tablename__ = "posts"
    id = Column(Integer, primary_key=True, index=True)
    boost_id = Column(Integer, ForeignKey("boosts.id", ondelete="CASCADE"), nullable=False)
    day = Column(Integer, nullable=False)
    slot = Column(Integer, default=1)
    kind = Column(String, default="static")
    caption = Column(Text, nullable=True)
    hashtags = Column(Text, nullable=True)
    cta = Column(String, nullable=True)
    image_url = Column(Text, nullable=True)
    # The creative the plan wrote, kept on the post: the calendar shows the overlay over the photo,
    # and the item editor edits it. Without these columns the overlay died with the plan JSON.
    title = Column(String, nullable=True)
    kicker = Column(String, nullable=True)
    overlay_text = Column(String, nullable=True)
    photo_room = Column(String, nullable=True)
    photo_file = Column(String, nullable=True)
    post_type = Column(String, default="photo")
    design_asset_id = Column(Integer, nullable=True)
    client_status = Column(String, default="pending")  # pending, approved, change_requested
    publish_at = Column(String, nullable=True)      # set by the engine, acted on by the publisher
    publish_status = Column(String, default="scheduled")  # scheduled | posting | posted | failed | skipped | held | download
    publish_target = Column(String, default="both")  # facebook | instagram | both
    fb_post_id = Column(String, nullable=True)
    ig_media_id = Column(String, nullable=True)
    last_error = Column(Text, nullable=True)
    # The failed-post ladder (post_retry): how many tries this post has had, when the next one
    # is due, and whose fault the failure was - the three kinds drive the message, the red
    # banner and whether anything is retried at all.
    publish_attempts = Column(Integer, default=0)
    next_attempt_at = Column(String, nullable=True)
    failure_kind = Column(String, nullable=True)          # our_fault | connection | meta_rejected
    failure_note = Column(Text, nullable=True)            # the sentence the agent reads
    failed_at = Column(DateTime, nullable=True)           # when it ran out of tries
    failure_notified_at = Column(DateTime, nullable=True)  # the one email a connection sent
    # Every failure, oldest first: [{at, error}]. The console's fail log reads this, so a retry
    # shows what happened last time instead of only the newest sentence in last_error.
    fail_log = Column(JSON, default=list)
    # Engine 4: two captions (the Instagram one never carries a link), Facebook's own 0-2 tags,
    # the post style and how the agent's details are shown, the agent's thumbs, and the flag a
    # post gets when the checks couldn't clear it.
    caption_ig = Column(Text, nullable=True)
    hashtags_fb = Column(Text, nullable=True)
    design_style = Column(String, nullable=True)
    details_treatment = Column(String, nullable=True)
    rating = Column(Integer, nullable=True)          # 1 thumbs up, -1 thumbs down
    needs_look = Column(Boolean, default=False)
    features = Column(JSON, nullable=True)           # what the learner compares between 👍 and 👎
    created_at = Column(DateTime(timezone=True), server_default=func.now())

# --- Social lead (Post Engine §10.4) ---
class Lead(Base):
    """One comment on a campaign post or ad that reads like buying interest.

    This is the record the Social leads panel reads. Before it existed the panel kept its
    leads in the browser: sample comments for the demo campaigns, an empty list for a real
    one, and "Add a lead" vanishing on reload or on another device. The comment id Meta
    gave it is the identity, so a scan that runs every 15 minutes cannot insert the same
    person twice.
    """
    __tablename__ = "leads"
    id = Column(Integer, primary_key=True, index=True)
    boost_id = Column(Integer, ForeignKey("boosts.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    # The post the comment landed on, when it was one of ours. An ad's comment has no post row.
    post_id = Column(Integer, nullable=True)
    platform = Column(String, nullable=False)                 # instagram | facebook | manual
    # What the panel prints next to the name ("Instagram", "Facebook ad", "Phone or text"):
    # a comment from an ad reads as "Facebook ad" because that is what the agent saw.
    channel = Column(String, nullable=True)
    source = Column(String, default="comment")                # comment | ad_comment | manual
    # Meta's own id for the comment. Unique per platform: the dedupe key for every scan.
    platform_comment_id = Column(String, nullable=True)
    author_name = Column(String, nullable=True)
    author_handle = Column(String, nullable=True)
    text = Column(Text, nullable=True)
    permalink = Column(Text, nullable=True)
    # Which post (or "the ad") the comment landed on: what the panel prints under the quote.
    post_label = Column(String, nullable=True)
    comment_at = Column(DateTime(timezone=True), nullable=True)
    # new -> handled (ticked off) or removed (not a lead). Rows are never deleted: a removed
    # comment stays removed instead of being re-flagged by the next scan.
    status = Column(String, default="new", nullable=False)
    # How it was judged: ai (the engine), keyword (rule fallback, no engine configured),
    # manual (the agent typed it in). interest/confidence are kept so a wrong call can be
    # reviewed instead of being an invisible opinion.
    classified_by = Column(String, nullable=True)
    confidence = Column(Float, nullable=True)
    reason = Column(String, nullable=True)
    # The agent's own note on this lead ("called back, showing Saturday"), editable any time.
    note = Column(Text, nullable=True)
    notified_at = Column(DateTime(timezone=True), nullable=True)   # the alert email actually went
    email_error = Column(Text, nullable=True)                      # why it did not
    # Engine 5: a lead from the listing website (form, call tap, text tap)
    email = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    visitor = Column(String, nullable=True)                        # one call/text lead per visitor per day
    wants = Column(String, nullable=True)                          # showing | question | similar
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    __table_args__ = (UniqueConstraint("platform", "platform_comment_id", name="uq_leads_comment"),)

# --- Ad ---
class Ad(Base):
    __tablename__ = "ads"
    id = Column(Integer, primary_key=True, index=True)
    boost_id = Column(Integer, ForeignKey("boosts.id", ondelete="CASCADE"), nullable=False)
    kind = Column(String, nullable=False)  # photo, video
    primary_text = Column(Text, nullable=True)
    headline = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    cta_button = Column(String, default="Learn More")
    creative_asset_ids = Column(JSON, default=[])
    meta_ad_id = Column(String, nullable=True)
    meta_adset_id = Column(String, nullable=True)
    meta_creative_id = Column(String, nullable=True)
    reach = Column(Integer, nullable=True)     # last pulled from the Insights API
    last_error = Column(Text, nullable=True)
    status = Column(String, default="draft")  # draft, submitted, live, paused
    # One ad per campaign: carousel of designed posts, or a single video (Ad Engine §4.2).
    format = Column(String, nullable=True)          # carousel | video
    card_post_ids = Column(JSON, default=[])        # which posts are the carousel cards
    image_hashes = Column(JSON, default=[])         # Meta image_hash per card, in order
    meta_campaign_id = Column(String, nullable=True)
    meta_video_id = Column(String, nullable=True)
    video_url = Column(Text, nullable=True)
    destination_url = Column(Text, nullable=True)
    # Engine 6: every ad in the ad set (the main video or carousel, and each hook version), and what
    # the live ad audit has done: [{kind, hook, meta_ad_id, meta_creative_id, status, started_at, ...}]
    versions = Column(JSON, default=list)
    audit = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

# --- Photo / design asset (the PHOTO INDEX behind the content engine) ---
class Asset(Base):
    __tablename__ = "assets"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    boost_id = Column(Integer, ForeignKey("boosts.id", ondelete="CASCADE"), nullable=True)
    filename = Column(String, nullable=False)      # stored file name under uploads/
    url = Column(Text, nullable=False)             # /uploads/<file>
    original_name = Column(String, nullable=True)  # the name the agent uploaded
    kind = Column(String, default="photo")         # photo | design | reference | headshot
    room = Column(String, nullable=True)
    social_score = Column(String, nullable=True)
    shape = Column(String, nullable=True)          # landscape | portrait | square
    see = Column(Text, nullable=True)              # what is visible
    story = Column(Text, nullable=True)            # the STORY detail the caption is built from
    tags = Column(JSON, default=[])                # POST, ROOM, FEATURE, SCALE, SOCIAL, WHY
    # The image itself. A free-tier container has no persistent disk, so a photo that lives
    # only in uploads/ becomes a 404 at the next deploy; the bytes ride along in the row.
    # Deferred: 56 rows x 4 MB of blobs is more memory than a small hosted instance has, and
    # almost nothing needs the bytes (the index, the plan and the calendar all work from
    # metadata). Code that needs the image itself loads it a row at a time.
    data = deferred(Column(LargeBinary, nullable=True))
    content_type = Column(String, nullable=True)
    tagged_by = Column(String, default="none")     # none | ai | human
    created_at = Column(DateTime(timezone=True), server_default=func.now())

# --- Support Ticket ---
class SupportTicket(Base):
    __tablename__ = "support_tickets"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    subject = Column(String, nullable=False)
    status = Column(String, default="received")  # received, answered, waiting, closed (app/services/support.py)
    messages = Column(JSON, default=[])
    boost_id = Column(Integer, nullable=True)     # Which listing? (optional)
    page = Column(String, nullable=True)          # the page they were on
    snapshot = Column(JSON, default=dict)         # the account at the time, so the team doesn't have to ask
    reply_by = Column(DateTime(timezone=True), nullable=True)  # the 1 business day promise
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now())

# --- Password reset (customer accounts) ---
class PasswordReset(Base):
    __tablename__ = "password_resets"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token_hash = Column(String, nullable=False, index=True)   # only the hash is stored
    expires_at = Column(DateTime(timezone=True), nullable=False)
    used_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class FacebookLoginCode(Base):
    """A one-time ticket handed back from Facebook's redirect.

    Facebook sends the browser to our callback with no Authorization header, so the callback
    cannot hand a JWT back in the URL: a token in a query string is written to referrer logs,
    analytics and browser history. The callback mints one of these, the app swaps it for a
    token immediately, and a second use is refused.
    """

    __tablename__ = "facebook_login_codes"
    id = Column(Integer, primary_key=True)
    code = Column(String, unique=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    purpose = Column(String, default="login")  # login | reactivate
    expires_at = Column(DateTime(timezone=True), nullable=False)
    used_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# --- Orders (one paid campaign = one order) ---
class Order(Base):
    """A purchase of one campaign. Stripe holds the money; this row is what gates a build.

    Keyed on the Stripe Checkout session so a replayed webhook updates one row instead of
    granting a second campaign.
    """
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    boost_id = Column(Integer, ForeignKey("boosts.id", ondelete="CASCADE"), nullable=False)
    amount_cents = Column(Integer, nullable=False, default=4900)
    currency = Column(String, default="usd")
    status = Column(String, default="pending")  # pending | paid | expired | failed
    stripe_session_id = Column(String, nullable=True, index=True)
    stripe_payment_intent = Column(String, nullable=True)
    checkout_url = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    paid_at = Column(DateTime(timezone=True), nullable=True)
    # Engine 10
    tax_cents = Column(Integer, nullable=True)
    receipt_url = Column(Text, nullable=True)
    refunded_cents = Column(Integer, nullable=True)
    refund_reason = Column(Text, nullable=True)
    kind = Column(String, nullable=True)            # campaign | run_again | round

# --- Campaign packs (repeat business) ---
class CreditPurchase(Base):
    """A prepaid pack of campaigns: "4 campaigns for $196", paid once, built later.

    The whole point of the business is a repeat customer, and a repeat customer needs a way to
    buy the second campaign without re-entering a card and without the operator doing anything.
    A pack is a Stripe payment recorded here; the campaigns it buys land on
    ``users.campaign_credits`` and each build spends one.

    Its own table rather than a row in ``orders`` because an order is one campaign tied to one
    boost (``orders.boost_id`` is NOT NULL); a pack exists before any campaign does.
    """
    __tablename__ = "credit_purchases"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    campaigns = Column(Integer, nullable=False, default=4)
    amount_cents = Column(Integer, nullable=False)
    currency = Column(String, default="usd")
    status = Column(String, default="pending")   # pending | paid | expired | failed
    stripe_session_id = Column(String, nullable=True, index=True)
    stripe_payment_intent = Column(String, nullable=True)
    checkout_url = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    paid_at = Column(DateTime(timezone=True), nullable=True)

# --- Finance model (the console's Finance tab) ---
class FinanceSetting(Base):
    """One row of operator-entered assumptions: what a campaign costs us, how often agents buy.

    These are opinions (engine cost per build, hosting run-rate, campaigns per agent per year),
    not measurements, so they live in the database where the operator can change them without a
    deploy. Everything derived from them is arithmetic on this row plus real rows elsewhere.
    """
    __tablename__ = "finance_settings"
    id = Column(Integer, primary_key=True)
    payload = Column(JSON, default=dict)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

# --- Event Log (audit) ---
class Event(Base):
    __tablename__ = "events"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=True)
    boost_id = Column(Integer, nullable=True)
    event_type = Column(String, nullable=False)
    payload = Column(JSON, default={})
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# --- Start-up costs (what it cost to get here, who paid, and what repeats) ---
# Until the business has its own bank account, the project's costs are paid out of
# personal cards. This is the ledger for that: one row per thing bought, who fronted it,
# and — for a subscription — the cadence, so the monthly burn keeps counting instead of
# being retyped every month. Receipts live in their own table and are served only to an
# admin, because a receipt image carries the last four digits of somebody's card.
class Cost(Base):
    __tablename__ = "costs"
    id = Column(Integer, primary_key=True, index=True)
    paid_on = Column(Date, nullable=False)
    paid_by = Column(String(120), nullable=False)
    vendor = Column(String(160), nullable=False)
    description = Column(Text, nullable=True)
    amount_cents = Column(Integer, nullable=False)
    currency = Column(String(8), default="usd")
    kind = Column(String(16), nullable=False, default="one_off")   # one_off | recurring
    cadence = Column(String(16), nullable=True)                    # monthly | yearly
    started_on = Column(Date, nullable=True)                       # recurring: first charge
    ended_on = Column(Date, nullable=True)                         # recurring: cancelled
    notes = Column(Text, nullable=True)
    created_by = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class CostReceipt(Base):
    __tablename__ = "cost_receipts"
    id = Column(Integer, primary_key=True, index=True)
    cost_id = Column(Integer, ForeignKey("costs.id", ondelete="CASCADE"), nullable=False, index=True)
    filename = Column(String(255), nullable=False)
    original_name = Column(String(255), nullable=True)
    content_type = Column(String(80), nullable=True)
    size = Column(Integer, nullable=True)
    data = Column(LargeBinary, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

# --- Build room (who is doing what, and who has it claimed) ---
# Adam works the front end, Dan works the back end, and both touch one repo. The failure mode
# this table exists to prevent is two people editing the same thing at once, or a piece of work
# going quiet because each thought the other had it. So a row carries an owner (claimed_by),
# when it was claimed, what it is about (area), when it is due, and whether it has been tested.
# A claim is a lock: nobody else may edit the row while a fresh claim is on it.
class BuildroomTask(Base):
    __tablename__ = "buildroom_tasks"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(240), nullable=False)
    area = Column(String(24), nullable=False, default="front_end")   # front_end | back_end | both
    status = Column(String(16), nullable=False, default="todo")      # todo | doing | review | done | blocked
    notes = Column(Text, nullable=True)
    # Who *should* do it, decided when the task is written; separate from the claim, which is
    # who is *on it right now*. Assignment is the plan, the claim is the lock.
    assigned_to = Column(String(160), nullable=True)
    claimed_by = Column(String(160), nullable=True)                  # the lock: an email or a name
    claimed_at = Column(DateTime(timezone=True), nullable=True)
    due_on = Column(Date, nullable=True)
    tested_by = Column(String(160), nullable=True)
    tested_at = Column(DateTime(timezone=True), nullable=True)
    test_note = Column(Text, nullable=True)
    created_by = Column(String(160), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


# --- Filings (the paperwork with a clock on it) ---
# A general partnership has almost no state paperwork — which is exactly why the little it
# does have gets forgotten: a Fictitious Business Name statement is due 40 days after
# business starts, the newspaper run starts within 45 days of that filing, Form 1065 and
# California's 565 are due on a fixed date every spring. None of those are in anyone's
# calendar, and a missed one costs the whole fee again. So each row is one obligation:
# what it is, who it goes to, the date it is due, what it costs, and — when it is not
# moving — who or what it is waiting on. A recurring row rolls itself forward when it is
# marked done, so the next window is on the board before this one is closed.
class Filing(Base):
    __tablename__ = "filings"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(240), nullable=False)
    kind = Column(String(24), nullable=False, default="filing")     # filing|publication|tax|renewal|report|other
    jurisdiction = Column(String(120), nullable=True)               # "Shasta County, CA", "IRS", "CA FTB"
    due_on = Column(Date, nullable=True)                            # the hard date
    window_opens_on = Column(Date, nullable=True)                   # earliest it may be filed
    recurrence = Column(String(24), nullable=False, default="one_off")  # one_off|annual|every_5_years
    # Money is nullable on purpose: NULL means "nobody has quoted this yet", which is a
    # different fact from $0 (free) and must not be summed as zero.
    cost_cents = Column(Integer, nullable=True)
    cost_note = Column(String(240), nullable=True)                  # "$84 + $9 per extra registrant"
    status = Column(String(16), nullable=False, default="open")     # open|done|not_needed
    done_on = Column(Date, nullable=True)
    paid_cents = Column(Integer, nullable=True)
    confirmation = Column(String(240), nullable=True)               # receipt or confirmation number
    blocked_on = Column(String(240), nullable=True)                 # who or what it is waiting on
    owner = Column(String(160), nullable=True)
    link = Column(String(400), nullable=True)
    notes = Column(Text, nullable=True)
    rolled_from = Column(Integer, nullable=True)                    # id of the cycle this one followed
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class HelpMiss(Base):
    """A question the Ask Resmara chat could not answer.

    The chat matches a question to `static/help-kb.js` locally, so a miss is the only
    evidence of what customers actually ask that we have no answer for. It is logged
    instead of guessed at: an operator turns a real miss into an approved answer, and
    the next agent who asks gets it (see HelpAnswer).
    """
    __tablename__ = "help_misses"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    question = Column(String(400), nullable=False)
    # The same question typed twice is one gap, not two: the count is what makes the
    # miss list a priority order instead of a log.
    asked_count = Column(Integer, default=1)
    ticket_id = Column(Integer, nullable=True)      # set when the agent sent it to support
    answer_id = Column(Integer, nullable=True)      # set when an operator answered it
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_asked_at = Column(DateTime(timezone=True), server_default=func.now())


class HelpAnswer(Base):
    """An answer the team approved, served to the chat on load.

    Customer-facing text only: the chat fetches these without a token, so nothing
    account-specific may be written into one.
    """
    __tablename__ = "help_answers"
    id = Column(Integer, primary_key=True, index=True)
    question = Column(String(400), nullable=False)
    answer = Column(Text, nullable=False)
    topic = Column(String(120), nullable=True)
    keys = Column(String(400), nullable=True)       # comma separated match words
    source_ticket_id = Column(Integer, nullable=True)
    created_by = Column(String(160), nullable=True)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# --- Marketing settings (Engine 9) ---
class MarketingSetting(Base):
    """The two monthly costs the team types in once, plus which email series are on.

    Ad spend is read from Meta on its own; Mailchimp's plan and the website hosting are not
    measurable from here, so the operator states them once and every "did it pay for itself?"
    answer is arithmetic on this row. Guessed costs would make the verdict meaningless.
    """
    __tablename__ = "marketing_settings"
    id = Column(Integer, primary_key=True)
    payload = Column(JSON, default=dict)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
