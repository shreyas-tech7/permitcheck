import pytest

from permitcheck.extract import RuleExtractor

X = RuleExtractor()


def one(text, field):
    return X.extract(text).get(field)


@pytest.mark.parametrize(
    "line, field, value",
    [
        ("Rear setback: 18 ft", "rear_setback_ft", 18),
        ("Rear yard setback: 18.5 feet", "rear_setback_ft", 18.5),
        ("Setback (rear): 18'", "rear_setback_ft", 18),
        ("Front yard setback: 29'-6\"", "front_setback_ft", 29.5),
        ("Side setback: 7 ft 6 in", "side_setback_ft", 7.5),
        ("Guard height: 38 inches", "guard_height_in", 38),
        ("Railing height: 3 ft 2 in", "guard_height_in", 38),
        ("Baluster spacing: 3 1/2 in", "guard_opening_in", 3.5),
        ("Riser height: 7.25\"", "stair_riser_in", 7.25),
        ("Lot area: 9,900 square feet", "lot_area_sqft", 9900),
        ("Proposed area: 229 sf", "new_area_sqft", 229),
        ("Valuation: $30,400", "valuation_usd", 30400),
        ("Value of work: 1,250 USD", "valuation_usd", 1250),
        ("Number of risers: three", "stair_riser_count", 3),
        ("Risers: 5", "stair_riser_count", 5),
        ("Handrail: Provided", "handrail", True),
        ("Smoke alarm: Not provided", "smoke_alarm", False),
        ("Owner signature: Not signed", "owner_signature", False),
        ("Zoning: R-2", "zoning_district", "R2"),
        ("Zone: District C1", "zoning_district", "C1"),
        ("Ledger: 16d nails", "ledger_fastener", "nails"),
        ("Ledger attachment: through bolts", "ledger_fastener", "bolts"),
        ("Foundation: slab on grade", "foundation_type", "slab"),
        ("Foundation type: crawl space", "foundation_type", "crawlspace"),
        ("Parcel ID: LH-3278-527", "parcel_id", "LH-3278-527"),
        ("APN: 4471-205", "parcel_id", "4471-205"),
        ("Contractor: owner-builder", "contractor", "owner-builder"),
        ("Contractor license: LHC-12345", "contractor", "LHC-12345"),
        ("Project type: Rear deck", "project_type", "deck"),
        ("Work type: Room addition", "project_type", "addition"),
    ],
)
def test_clean_values_parse_with_high_confidence(line, field, value):
    f = one(line, field)
    assert f is not None and f.value == value
    assert f.confidence >= 0.9


def test_table_and_scan_and_prose_formats():
    assert one("| Rear setback | 18 ft |", "rear_setback_ft").value == 18
    assert one("REAR SETBACK .... 18 FT", "rear_setback_ft").value == 18
    fields = X.extract("The rear setback is 18 ft. The guard height is 40 in.")
    assert fields["rear_setback_ft"].value == 18
    assert fields["guard_height_in"].value == 40


def test_setback_given_in_inches_converts():
    """Broken case: reading '216 in' as 216 ft would pass any setback."""
    f = one("Rear setback: 216 in", "rear_setback_ft")
    assert f.value == 18 and f.confidence >= 0.9


def test_unitless_value_is_low_confidence():
    """Broken case: 'Rear setback: 18' could be inches or feet. It must not be trusted."""
    f = one("Rear setback: 18", "rear_setback_ft")
    assert f.value == 18 and f.confidence < 0.8


def test_approximate_value_is_low_confidence():
    f = one("Lot size: roughly 10000 SF", "lot_area_sqft")
    assert f.value == 10000 and f.confidence < 0.8


def test_existing_structure_line_is_ignored():
    """Broken case: 'Existing deck height: 12 in' filled the new deck height, so the guard rule
    thought no guard was needed."""
    fields = X.extract("Existing deck height: 12 in (old deck to be removed)\nDeck height: 32 in")
    assert fields["deck_height_in"].value == 32 and fields["deck_height_in"].confidence >= 0.9
    assert "rear_setback_ft" not in X.extract("Existing rear setback of garage: 3 ft")


def test_conflicting_values_are_low_confidence():
    """Broken case: two different rear setbacks in one file. Picking either one quietly is a guess."""
    f = one("Rear setback: 18 ft\nRevised rear setback: 9 ft", "rear_setback_ft")
    assert f.confidence < 0.8


def test_repeated_same_value_stays_confident():
    f = one("Rear setback: 18 ft\nRear yard setback: 18 ft", "rear_setback_ft")
    assert f.value == 18 and f.confidence >= 0.9


def test_garbled_number_is_not_read():
    """Broken case: 'Lot area: 2O5 sq ft' parsed as 5 sq ft."""
    f = one("Lot area: 9,9O0 sq ft", "lot_area_sqft")
    assert f is None or f.value is None or f.confidence < 0.8
    f = one("GUARD HEIGHT .... 3B IN", "guard_height_in")
    assert f is None or f.value is None or f.confidence < 0.8


@pytest.mark.parametrize("line, field", [
    ("BUILDING HEIGHT: L7 FT 6 IN", "height_ft"),
    ("FINISHED CEILING HEIGHT: 8 FT B IN", "ceiling_height_in"),
    ("Building height: S ft", "height_ft"),
    ("Proposed area: 4O0 sq ft", "new_area_sqft"),
])
def test_garbled_digit_never_reads_as_a_smaller_clean_number(line, field):
    """Found on the second seed: 'L7 FT 6 IN' read as 0.5 ft and '8 FT B IN' as 96 in, both at 0.95.
    A garbled digit that drops out makes a value smaller, which can pass a maximum by mistake."""
    f = one(line, field)
    assert f is None or f.value is None or f.confidence < 0.8


def test_near_miss_label_is_read_with_lower_but_passing_confidence():
    f = one("Side yard setack: 7 ft 6 in", "side_setback_ft")
    assert f.value == 7.5 and 0.8 <= f.confidence < 0.9


def test_unknown_label_is_not_guessed():
    assert one("Gap between pickets: 3 in", "guard_opening_in") is None


def test_builder_inside_owner_builder_is_not_a_label():
    fields = X.extract("Contractor: owner-builder")
    assert fields["contractor"].value == "owner-builder"
    assert fields["contractor"].confidence >= 0.9


def test_missing_field_is_absent():
    assert "rear_setback_ft" not in X.extract("Front setback: 30 ft")


def test_last_prose_sentence_is_read():
    """Broken case: the trailing period on the last sentence hid 'The revised risers is 2.'"""
    f = one("The risers is 0. The revised risers is 2.", "stair_riser_count")
    assert f.confidence < 0.8


def test_revised_line_with_a_typo_label_still_counts_as_a_conflict():
    """Broken case: 'Revised waking surface height' did not match, so the old value looked clean."""
    f = one("Waking surface height: 37 in\nRevised waking surface height: 39\"", "deck_height_in")
    assert f.confidence < 0.8
