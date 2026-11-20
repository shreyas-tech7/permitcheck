import dataclasses
import json
from pathlib import Path

import pytest

from permitcheck.checker import check_application
from permitcheck.codefile import load_code
from permitcheck.disclaimer import DISCLAIMER
from permitcheck.extract import Field, RuleExtractor
from permitcheck.report import CitationError, cited_sections, letter_md

CODE = load_code()
ROOT = Path(__file__).resolve().parent.parent


def results():
    f = {"project_type": "deck", "zoning_district": "R2", "stair_riser_in": 8.0, "guard_height_in": 30,
         "deck_height_in": 40, "joist_spacing_in": 24}
    return check_application({k: Field(v, 0.95, "t") for k, v in f.items()}, CODE)


def test_letter_cites_each_fail_and_needs_human_item():
    res = results()
    letter = letter_md("LH-APP-9999", res, CODE)
    assert DISCLAIMER in letter
    cites = cited_sections(letter)
    want = {(r.rule_id, r.section) for r in res if r.status != "pass"}
    assert set(cites) == want


def test_every_cited_section_exists_and_matches_its_rule():
    """Checks the letters for 40 real applications, not only a hand case."""
    x = RuleExtractor(CODE)
    apps = sorted((ROOT / "data" / "applications").glob("*.txt"))[:40]
    n = 0
    for p in apps:
        letter = letter_md(p.stem, check_application(x.extract(p.read_text()), CODE), CODE)
        for rid, section in cited_sections(letter):
            assert section in CODE["by_section"], section
            assert CODE["by_section"][section]["id"] == rid
            n += 1
    assert n > 40


def test_fake_section_id_raises():
    """Broken case: a result carrying a section that is not in the code file."""
    res = results()
    bad = [dataclasses.replace(r, section="LHRC 99.9.9") if r.status == "fail" else r for r in res]
    with pytest.raises(CitationError):
        letter_md("LH-APP-9999", bad, CODE)


def test_section_that_names_the_wrong_rule_raises():
    res = results()
    fail = next(r for r in res if r.status == "fail")
    other = next(r for r in CODE["rules"] if r["id"] != fail.rule_id)
    bad = [dataclasses.replace(fail, section=other["section"])]
    with pytest.raises(CitationError):
        letter_md("LH-APP-9999", bad, CODE)


def test_clean_application_letter_says_nothing_to_fix():
    res = [r for r in results() if r.status == "pass"]
    letter = letter_md("LH-APP-9999", res, CODE)
    assert "nothing to correct" in letter.lower()
    assert cited_sections(letter) == []


def test_letter_text_has_no_rule_text_from_outside_the_code_file():
    letter = letter_md("LH-APP-9999", results(), CODE)
    for rid, _ in cited_sections(letter):
        assert CODE["by_id"][rid]["text"] in letter
    json.dumps(letter)
