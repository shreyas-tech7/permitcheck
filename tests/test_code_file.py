import copy
import json

import pytest

from permitcheck.codefile import DEFAULT_PATH, CodeFileError, load_code, rule_fields, validate


def raw():
    return json.loads(DEFAULT_PATH.read_text())


def test_code_file_is_valid_and_has_25_rules():
    code = load_code()
    assert len(code["rules"]) == 25
    assert code["fictional"] is True
    assert code["version"] == "2026.1"
    assert len(code["sha256"]) == 64


def test_every_rule_field_is_declared():
    code = load_code()
    for r in code["rules"]:
        for f in rule_fields(r["check"]):
            assert f in code["fields"], (r["id"], f)


@pytest.mark.parametrize(
    "mutate, needle",
    [
        (lambda c: c["rules"][1].update(id="R01"), "duplicate id"),
        (lambda c: c["rules"][1].update(section="LHRC 10.1.1"), "duplicate section"),
        (lambda c: c["rules"][0].update(section="10.1.1"), "section must look like"),
        (lambda c: c["rules"][0]["check"].update(field="no_such_field"), "unknown field"),
        (lambda c: c["rules"][0]["check"].update(type="vibes"), "unknown check type"),
        (lambda c: c["rules"][0].update(applies_to=["pool"]), "applies_to"),
        (lambda c: c.update(fictional=False), "fictional"),
        (lambda c: c["rules"][11]["check"]["when"].update(op="~"), "bad op"),
        (lambda c: c["rules"][3]["check"].update(limit="one"), "limit must be a number"),
        (lambda c: c["rules"][1]["check"].update(regex="(["), "bad regex"),
    ],
)
def test_schema_check_catches_broken_files(mutate, needle):
    """Broken case: each mutation makes the file invalid. validate() must name the problem."""
    c = copy.deepcopy(raw())
    mutate(c)
    errors = validate(c)
    assert any(needle in e for e in errors), errors


def test_load_code_raises_on_invalid_file(tmp_path):
    c = raw()
    c["rules"][0]["section"] = "bad"
    p = tmp_path / "code.json"
    p.write_text(json.dumps(c))
    with pytest.raises(CodeFileError):
        load_code(p)
