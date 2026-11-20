"""A missing or low-confidence field always gives needs_human. Never pass."""

import pytest

from permitcheck.checker import CONFIDENCE_THRESHOLD, check_application, check_rule
from permitcheck.codefile import load_code
from permitcheck.extract import Field

CODE = load_code()


def F(v, c=0.95):
    return Field(v, c, "test")


def test_threshold_is_point_eight():
    assert CONFIDENCE_THRESHOLD == 0.8


def test_missing_field_is_needs_human():
    r = check_rule(CODE["by_id"]["R14"], {"project_type": F("deck")})
    assert r.status == "needs_human"
    assert "stair_riser_in" in r.reason or "riser" in r.reason.lower()


@pytest.mark.parametrize("rid, field, good", [
    ("R14", "stair_riser_in", 7.0), ("R18", "footing_depth_in", 40), ("R23", "smoke_alarm", True),
    ("R19", "ledger_fastener", "bolts"), ("R02", "parcel_id", "LH-1234-567"),
])
def test_low_confidence_passing_value_is_needs_human(rid, field, good):
    """Broken case: a value that would pass, read at 0.79, slipped through as pass."""
    r = check_rule(CODE["by_id"][rid], {"project_type": F("deck"), field: F(good, 0.79)})
    assert r.status == "needs_human"
    r = check_rule(CODE["by_id"][rid], {"project_type": F("deck"), field: F(good, 0.8)})
    assert r.status == "pass"


def test_low_confidence_failing_value_is_also_needs_human():
    r = check_rule(CODE["by_id"]["R14"], {field: F(9.0, 0.5) for field in ["stair_riser_in"]})
    assert r.status == "needs_human"


def test_value_none_is_needs_human():
    r = check_rule(CODE["by_id"]["R14"], {"stair_riser_in": F(None, 0.95)})
    assert r.status == "needs_human"


def test_unclear_condition_is_needs_human_even_if_the_inner_value_passes():
    rule = CODE["by_id"]["R12"]
    r = check_rule(rule, {"deck_height_in": F(30, 0.4), "guard_height_in": F(40)})
    assert r.status == "needs_human"
    r = check_rule(rule, {"guard_height_in": F(40)})
    assert r.status == "needs_human"


def test_false_condition_passes_even_with_a_missing_inner_field():
    r = check_rule(CODE["by_id"]["R12"], {"deck_height_in": F(20)})
    assert r.status == "pass" and "not required" in r.reason


def test_unclear_district_is_needs_human_for_setbacks():
    r = check_rule(CODE["by_id"]["R06"], {"zoning_district": F("R2", 0.3), "front_setback_ft": F(40)})
    assert r.status == "needs_human"


def test_one_missing_part_of_the_coverage_ratio_is_needs_human():
    r = check_rule(CODE["by_id"]["R09"], {"lot_area_sqft": F(10000), "new_area_sqft": F(100)})
    assert r.status == "needs_human"


def test_zero_lot_area_is_needs_human_not_a_crash():
    r = check_rule(CODE["by_id"]["R09"], {"lot_area_sqft": F(0), "new_area_sqft": F(100),
                                         "existing_footprint_sqft": F(100)})
    assert r.status == "needs_human"


def test_unclear_project_type_makes_every_rule_needs_human():
    res = check_application({"project_type": F("deck", 0.3), "stair_riser_in": F(7)}, CODE)
    assert len(res) == 25 and all(r.status == "needs_human" for r in res)
    res = check_application({}, CODE)
    assert len(res) == 25 and all(r.status == "needs_human" for r in res)


def test_wrong_type_value_is_needs_human():
    r = check_rule(CODE["by_id"]["R14"], {"stair_riser_in": F("seven")})
    assert r.status == "needs_human"
