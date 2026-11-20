import json
from pathlib import Path

from permitcheck.codefile import load_code
from permitcheck.generator import expected_status, generate, truth_status

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"


def test_same_seed_gives_same_bytes(tmp_path):
    """Broken case: any use of unseeded randomness or set ordering makes two runs differ."""
    generate(7, 20, tmp_path / "a")
    generate(7, 20, tmp_path / "b")
    for sub in ("applications", "answer_keys"):
        a = sorted((tmp_path / "a" / sub).iterdir())
        b = sorted((tmp_path / "b" / sub).iterdir())
        assert [p.name for p in a] == [p.name for p in b]
        assert all(x.read_bytes() == y.read_bytes() for x, y in zip(a, b, strict=True))
    assert (tmp_path / "a" / "split.json").read_bytes() == (tmp_path / "b" / "split.json").read_bytes()


def test_other_seed_gives_other_data(tmp_path):
    generate(7, 5, tmp_path / "a")
    generate(8, 5, tmp_path / "b")
    assert (tmp_path / "a" / "applications" / "LH-APP-0001.txt").read_text() != (
        tmp_path / "b" / "applications" / "LH-APP-0001.txt"
    ).read_text()


def test_committed_data_matches_the_generator(tmp_path):
    """Broken case: someone edits data/ by hand, or changes the generator without regenerating."""
    meta = json.loads((DATA / "meta.json").read_text())
    generate(meta["seed"], meta["n"], tmp_path)
    for sub in ("applications", "answer_keys"):
        for p in sorted((tmp_path / sub).iterdir()):
            assert p.read_bytes() == (DATA / sub / p.name).read_bytes(), p.name
    assert (tmp_path / "split.json").read_bytes() == (DATA / "split.json").read_bytes()


def test_split_is_200_dev_and_100_heldout_with_no_overlap():
    split = json.loads((DATA / "split.json").read_text())
    dev, held = set(split["dev"]), set(split["heldout"])
    assert len(dev) == 200 and len(held) == 100
    assert not dev & held
    assert len(list((DATA / "applications").glob("*.txt"))) == 300


def test_split_matches_each_key():
    split = json.loads((DATA / "split.json").read_text())
    for name, ids in split.items():
        if name in ("dev", "heldout"):
            for app_id in ids:
                key = json.loads((DATA / "answer_keys" / f"{app_id}.json").read_text())
                assert key["split"] == name


def test_keys_have_critical_violations_edge_cases_and_mess():
    keys = [json.loads(p.read_text()) for p in sorted((DATA / "answer_keys").glob("*.json"))]
    held = [k for k in keys if k["split"] == "heldout"]
    crit = sum(1 for k in held for v in k["violations"] if v["critical"])
    assert crit >= 30
    assert sum(1 for k in keys if k["edge_cases"]) >= 50
    statuses = {s for k in keys for s in k["field_status"].values()}
    assert {"clean", "missing", "approx", "unitless", "conflict", "garbled"} <= statuses
    assert {k["format"] for k in keys} == {"form", "table", "prose", "scan"}
    assert all(k["synthetic"] is True for k in keys)


def test_every_application_says_it_is_synthetic():
    for p in sorted((DATA / "applications").glob("*.txt"))[:20]:
        assert "SYNTHETIC" in p.read_text().upper()


def test_truth_status_on_hand_examples():
    code = load_code()
    r12 = code["by_id"]["R12"]
    assert truth_status(r12, {"deck_height_in": 30, "guard_height_in": 36}) == "fail"
    assert truth_status(r12, {"deck_height_in": 24, "guard_height_in": 10}) == "pass"
    assert truth_status(r12, {"deck_height_in": 30, "guard_height_in": 38}) == "pass"
    r09 = code["by_id"]["R09"]
    assert truth_status(r09, {"existing_footprint_sqft": 2000, "new_area_sqft": 2000,
                              "lot_area_sqft": 10000}) == "pass"
    assert truth_status(r09, {"existing_footprint_sqft": 2000, "new_area_sqft": 2001,
                              "lot_area_sqft": 10000}) == "fail"


def test_expected_status_is_needs_human_when_text_is_unclear():
    code = load_code()
    r14 = code["by_id"]["R14"]
    fields = {"stair_riser_in": 8.0}
    assert expected_status(r14, fields, {"stair_riser_in": "clean"}) == "fail"
    assert expected_status(r14, fields, {"stair_riser_in": "approx"}) == "needs_human"
    r12 = code["by_id"]["R12"]
    f = {"deck_height_in": 20, "guard_height_in": 30}
    # Condition is clearly false, so the missing guard does not matter.
    assert expected_status(r12, f, {"deck_height_in": "clean", "guard_height_in": "missing"}) == "pass"
    assert expected_status(r12, f, {"deck_height_in": "missing", "guard_height_in": "clean"}) == "needs_human"
