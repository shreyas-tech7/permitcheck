import json
from pathlib import Path

import pytest

from permitcheck.extract import Field
from permitcheck.metrics import field_counts, prf, rate, same, wilson

ROOT = Path(__file__).resolve().parent.parent


@pytest.mark.parametrize("k, n, lo, hi", [
    (0, 47, 0.0, 0.075560),   # z^2 / (n + z^2) when k = 0
    (5, 10, 0.236590, 0.763410),
    (10, 10, 0.722467, 1.0),
    (1, 100, 0.001767, 0.054488),
])
def test_wilson_matches_reference_values(k, n, lo, hi):
    """Reference values computed by hand from the Wilson formula with z = 1.96."""
    a, b = wilson(k, n)
    assert a == pytest.approx(lo, abs=1e-5) and b == pytest.approx(hi, abs=1e-5)


def test_wilson_zero_n():
    assert wilson(0, 0) == (None, None)
    assert rate(0, 0)["value"] is None


def test_zero_count_still_has_a_wide_upper_bound():
    assert wilson(0, 20)[1] > 0.15


def test_field_counts_and_prf():
    key = {"fields": {"a": 1, "b": 2, "c": "x", "d": True}, "field_status": {"a": "clean", "b": "clean",
           "c": "missing", "d": "clean"}}
    got = {"a": Field(1, 0.9, ""), "b": Field(3, 0.9, ""), "c": Field("x", 0.9, ""), "d": Field(None, 0.2, "")}
    tp, fp, fn = field_counts(key, got)
    assert (tp, fp, fn) == (1, 2, 2)
    m = prf(tp, fp, fn)
    assert m["precision"] == pytest.approx(1 / 3) and m["recall"] == pytest.approx(1 / 3)


def test_same_does_not_mix_bools_and_numbers():
    assert not same(True, 1) and same(1, 1.0) and not same(False, 0)


@pytest.mark.parametrize("name", ["eval_dev_rule.json", "eval_heldout_rule.json"])
def test_results_files_have_the_readme_fields(name):
    r = json.loads((ROOT / "results" / name).read_text())
    for key in ("field", "violation", "false_approve_apps", "false_approve_critical_violations",
                "needs_human_decisions", "citation_validity"):
        assert key in r
    assert r["synthetic"] is True
    assert r["false_approve_apps"]["method"].startswith("Wilson")
    assert r["n_apps"] == {"eval_dev_rule.json": 200, "eval_heldout_rule.json": 100}[name]
