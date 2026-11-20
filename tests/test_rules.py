"""Pass, fail and edge tests for every rule in the code file.

Each case gives the fields a clean extractor would return (confidence 0.95). The coverage test at
the bottom fails if any rule in the code file lacks a pass, a fail or an edge case.
"""

import pytest

from permitcheck.checker import check_application, check_rule
from permitcheck.codefile import load_code
from permitcheck.extract import Field

CODE = load_code()

D = {"project_type": "deck", "zoning_district": "R2"}
A = {"project_type": "addition", "zoning_district": "R2"}
COV = {"lot_area_sqft": 10000, "existing_footprint_sqft": 2000}

# rule: (base, pass fields, fail fields, edge fields, edge expected)
CASES = {
    "R01": (D, {"owner_signature": True}, {"owner_signature": False}, None, None),
    "R02": (D, {"parcel_id": "LH-1234-567"}, {"parcel_id": "LH-123-45"}, {"parcel_id": "LH-1234-5678"}, "fail"),
    "R03": (D, {"contractor": "LHC-12345"}, {"contractor": "pending"}, {"contractor": "owner-builder"}, "pass"),
    "R04": (D, {"valuation_usd": 25000}, {"valuation_usd": 0}, {"valuation_usd": 1}, "pass"),
    "R05": (D, {"zoning_district": "R3"}, {"zoning_district": "C1"}, {"zoning_district": "R1"}, "pass"),
    "R06": (D, {"front_setback_ft": 30}, {"front_setback_ft": 19.5}, {"front_setback_ft": 20}, "pass"),
    "R07": (D, {"side_setback_ft": 9}, {"side_setback_ft": 5.5}, {"side_setback_ft": 6}, "pass"),
    "R08": (D, {"rear_setback_ft": 25}, {"rear_setback_ft": 14.5}, {"rear_setback_ft": 15}, "pass"),
    "R09": (D, {**COV, "new_area_sqft": 300}, {**COV, "new_area_sqft": 2001},
            {**COV, "new_area_sqft": 2000}, "pass"),
    "R10": (A, {"height_ft": 22}, {"height_ft": 30.5}, {"height_ft": 30}, "pass"),
    "R11": (D, {"new_area_sqft": 300}, {"new_area_sqft": 501}, {"new_area_sqft": 500}, "pass"),
    "R12": (D, {"deck_height_in": 30, "guard_height_in": 40}, {"deck_height_in": 30, "guard_height_in": 37},
            {"deck_height_in": 24, "guard_height_in": 20}, "pass"),
    "R13": (D, {"deck_height_in": 30, "guard_opening_in": 3}, {"deck_height_in": 30, "guard_opening_in": 3.75},
            {"deck_height_in": 25, "guard_opening_in": 3.5}, "pass"),
    "R14": (D, {"stair_riser_in": 7}, {"stair_riser_in": 7.75}, {"stair_riser_in": 7.5}, "pass"),
    "R15": (D, {"stair_tread_in": 11}, {"stair_tread_in": 10.25}, {"stair_tread_in": 10.5}, "pass"),
    "R16": (D, {"stair_riser_count": 6, "handrail": True}, {"stair_riser_count": 4, "handrail": False},
            {"stair_riser_count": 3, "handrail": False}, "pass"),
    "R17": (D, {"joist_spacing_in": 12}, {"joist_spacing_in": 19.2}, {"joist_spacing_in": 16}, "pass"),
    "R18": (D, {"footing_depth_in": 36}, {"footing_depth_in": 29}, {"footing_depth_in": 30}, "pass"),
    "R19": (D, {"ledger_fastener": "bolts"}, {"ledger_fastener": "nails"},
            {"ledger_fastener": "freestanding"}, "pass"),
    "R20": (A, {"new_area_sqft": 600}, {"new_area_sqft": 901}, {"new_area_sqft": 900}, "pass"),
    "R21": (A, {"ceiling_height_in": 96}, {"ceiling_height_in": 83}, {"ceiling_height_in": 84}, "pass"),
    "R22": (A, {"new_bedrooms": 2, "egress_window": True}, {"new_bedrooms": 1, "egress_window": False},
            {"new_bedrooms": 0, "egress_window": False}, "pass"),
    "R23": (A, {"smoke_alarm": True}, {"smoke_alarm": False}, None, None),
    "R24": (A, {"stories": 1}, {"stories": 3}, {"stories": 2}, "pass"),
    "R25": (A, {"foundation_type": "crawlspace"}, {"foundation_type": "piers"},
            {"foundation_type": "basement"}, "pass"),
}
# Two rules are plain yes or no, so their edge is "a missing answer", which must never pass.
EDGE_MISSING = {"R01", "R23"}


def fields(base, extra, conf=0.95):
    return {k: Field(v, conf, "test") for k, v in {**base, **extra}.items()}


def run(rid, base, extra):
    return check_rule(CODE["by_id"][rid], fields(base, extra))


@pytest.mark.parametrize("rid", sorted(CASES))
def test_rule_pass(rid):
    base, ok, _, _, _ = CASES[rid]
    r = run(rid, base, ok)
    assert r.status == "pass", r.reason
    assert r.section == CODE["by_id"][rid]["section"]


@pytest.mark.parametrize("rid", sorted(CASES))
def test_rule_fail(rid):
    base, _, bad, _, _ = CASES[rid]
    r = run(rid, base, bad)
    assert r.status == "fail", r.reason
    assert r.section == CODE["by_id"][rid]["section"]
    assert r.reason and not r.reason.startswith("needs a person")


@pytest.mark.parametrize("rid", sorted(CASES))
def test_rule_edge(rid):
    base, _, _, edge, want = CASES[rid]
    if rid in EDGE_MISSING:
        r = run(rid, base, {})
        assert r.status == "needs_human", r.reason
    else:
        r = run(rid, base, edge)
        assert r.status == want, r.reason


def test_every_rule_in_the_code_file_has_pass_fail_and_edge_cases():
    """Broken case: a rule added to the code file without tests."""
    for r in CODE["rules"]:
        assert r["id"] in CASES, r["id"]
        base, ok, bad, edge, _ = CASES[r["id"]]
        assert ok and bad and (edge or r["id"] in EDGE_MISSING)


def test_setbacks_use_the_district_limit():
    assert run("R06", {**D, "zoning_district": "R1"}, {"front_setback_ft": 24.5}).status == "fail"
    assert run("R06", {**D, "zoning_district": "R3"}, {"front_setback_ft": 15}).status == "pass"


def test_setback_with_no_limit_for_the_district_is_needs_human():
    assert run("R06", {**D, "zoning_district": "C1"}, {"front_setback_ft": 40}).status == "needs_human"


def test_check_application_runs_only_the_rules_for_the_project_type():
    res = check_application(fields(D, {}), CODE)
    ids = {r.rule_id for r in res}
    assert "R12" in ids and "R23" not in ids
    res = check_application(fields(A, {}), CODE)
    ids = {r.rule_id for r in res}
    assert "R23" in ids and "R12" not in ids
