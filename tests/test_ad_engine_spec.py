"""The ad builder against the Digital Ad Engine spec v1.3 §4.

Each assertion here is a bug the previous builder shipped: a daily budget, US-wide
targeting, no creative media, copy read from the wrong keys, Resmara's own site as the
landing page, and everything created PAUSED so an approved campaign never spent.
"""
from types import SimpleNamespace

from app.services.ad_build import build_ad_configs, campaign_name, clamp_budget, with_utm


def boost(**over):
    data = dict(
        id=7, address="1234 Elm Street, Austin, TX 78704", go_live_date="2026-12-01",
        ad_budget_usd=50.0, repeat_round=0, destination_url=None, listing_url=None,
        video_url=None, plan={}, ad_brief={},
    )
    data.update(over)
    return SimpleNamespace(**data)


PLAN = {"ad": {
    "primaryText": "Hill Country views at first light, a pool that runs to the treeline.",
    "headline": "Tour the Elm Street house", "description": "Private showings",
    "ctaButton": "Learn more", "creativeDays": [1, 4, 9],
}}

CARDS = [{"image_hash": "hash_a", "title": "Morning light", "post_id": 11},
         {"image_hash": "hash_b", "title": "The pool", "post_id": 14}]


def base(**over):
    kwargs = dict(page_id="page_1", ig_user_id="ig_1", budget_usd=50.0, cards=CARDS,
                  destination=None, go_live="2026-12-01",
                  geo={"latitude": 30.25, "longitude": -97.76}, campaign_no=1)
    kwargs.update(over)
    return build_ad_configs(boost(), PLAN, **kwargs)


def test_budget_is_lifetime_not_daily():
    built = base()
    campaign = built["campaign"]
    assert campaign["lifetime_budget"] == 5000
    assert "daily_budget" not in campaign
    assert "lifetime_budget" not in built["adset"]


def test_schedule_comes_from_the_go_live_date():
    adset = base()["adset"]
    assert adset["start_time"].startswith("2026-12-01T08:00")
    assert adset["end_time"].startswith("2026-12-15T08:00")


def test_targeting_is_the_listing_radius_only():
    targeting = base()["adset"]["targeting"]
    geo = targeting["geo_locations"]
    assert "countries" not in geo
    loc = geo["custom_locations"][0]
    assert loc["radius"] >= 15 and loc["distance_unit"] == "mile"
    assert loc["latitude"] == 30.25
    assert targeting["age_min"] == 18
    assert "genders" not in targeting and "interests" not in targeting
    assert targeting["publisher_platforms"] == ["facebook", "instagram"]


def test_city_key_wins_over_coordinates():
    built = base(geo={"city_key": "2420379", "radius_miles": 20})
    cities = built["adset"]["targeting"]["geo_locations"]["cities"]
    assert cities[0]["key"] == "2420379" and cities[0]["radius"] == 20


def test_carousel_creative_carries_every_card_and_the_instagram_account():
    built = base()
    assert built["format"] == "carousel"
    link_data = built["adcreative"]["object_story_spec"]["link_data"]
    children = link_data["child_attachments"]
    assert [c["image_hash"] for c in children] == ["hash_a", "hash_b"]
    assert children[0]["name"] == "Morning light"
    assert built["adcreative"]["instagram_actor_id"] == "ig_1"


def test_copy_comes_from_the_plans_camel_case_keys():
    link_data = base()["adcreative"]["object_story_spec"]["link_data"]
    assert link_data["message"].startswith("Hill Country views")
    assert link_data["name"] == "Tour the Elm Street house"
    assert link_data["description"] == "Private showings"
    assert link_data["call_to_action"]["type"] == "LEARN_MORE"


def test_destination_is_the_agent_link_with_utm():
    built = base(destination="https://example.com/elm")
    link = built["adcreative"]["object_story_spec"]["link_data"]["link"]
    assert link.startswith("https://example.com/elm?")
    assert "utm_source=resmara" in link and "utm_medium=paid" in link


def test_video_wins_over_the_carousel_when_meta_processed_it():
    built = base(video={"video_id": "vid_9"}, destination="https://example.com/elm")
    assert built["format"] == "video"
    video_data = built["adcreative"]["object_story_spec"]["video_data"]
    assert video_data["video_id"] == "vid_9"
    assert video_data["call_to_action"]["value"]["link"].startswith("https://")


def test_objects_are_active_and_simply_wait_for_the_start_time():
    built = base()
    assert built["campaign"]["status"] == "ACTIVE"
    assert built["ad"]["status"] == "ACTIVE"
    assert built["adset"]["status"] == "ACTIVE"


def test_no_media_is_never_shipped_silently():
    built = base(cards=[])
    assert built["format"] == "none"
    assert any("NO MEDIA" in note for note in built["notes"])


def test_housing_category_is_always_set():
    assert base()["campaign"]["special_ad_categories"] == ["HOUSING"]


def test_names_carry_the_campaign_number_so_a_rerun_never_collides():
    assert campaign_name(boost(repeat_round=1)) == "1234 elm · Resmara · 2"


def test_budget_floor_and_utm_helpers():
    assert clamp_budget(1) == 5.0
    tagged = with_utm("https://a.com/x?y=1", "1234 Elm Street")
    assert tagged == ("https://a.com/x?y=1&utm_source=resmara&utm_medium=paid"
                      "&utm_campaign=1234+elm")
