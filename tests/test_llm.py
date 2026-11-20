"""LLM extractor tests. The fixtures here are hand-written for tests. They are not model recordings."""

import json

import pytest

from permitcheck.checker import check_application
from permitcheck.codefile import load_code
from permitcheck.llm import LLMExtractor, RecordBlocked, ReplayMissing

CODE = load_code()
TEXT = """SYNTHETIC TEST DOCUMENT.
Project type: Deck
Zoning: R2
Deck height: 32 in
Guard height: 36 in
Riser height: 7 in
Contractor license: LHC-12345
"""


def response(**fields):
    return json.dumps({"fields": fields})


def item(value, quote, conf=0.9):
    return {"value": value, "quote": quote, "confidence": conf}


def save(tmp_path, x, raw):
    p = x.fixture_path(x.prompt(TEXT))
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"model": x.model, "recorded": False, "response": raw,
                             "note": "hand-written test fixture, not a model recording"}))


def test_replay_reads_a_fixture_and_grounded_values_keep_their_confidence(tmp_path):
    x = LLMExtractor(CODE, mode="replay", fixtures=tmp_path)
    save(tmp_path, x, response(project_type=item("deck", "Project type: Deck"),
                               deck_height_in=item(32, "Deck height: 32 in"),
                               guard_height_in=item(36, "Guard height: 36 in"),
                               contractor=item("LHC-12345", "Contractor license: LHC-12345")))
    f = x.extract(TEXT)
    assert f["deck_height_in"].value == 32 and f["deck_height_in"].confidence == 0.9
    assert f["contractor"].value == "LHC-12345"
    res = {r.rule_id: r for r in check_application(f, CODE)}
    assert res["R12"].status == "fail"
    assert res["R03"].status == "pass"


def test_quote_that_is_not_in_the_text_caps_confidence(tmp_path):
    """Broken case: the model invents 'Guard height: 40 in'. Without grounding the guard rule passes."""
    x = LLMExtractor(CODE, fixtures=tmp_path)
    f = x.parse(response(project_type=item("deck", "Project type: Deck", 0.99),
                         deck_height_in=item(32, "Deck height: 32 in", 0.99),
                         guard_height_in=item(40, "Guard height: 40 in", 0.99)), TEXT)
    assert f["guard_height_in"].confidence <= 0.5
    res = {r.rule_id: r for r in check_application(f, CODE)}
    assert res["R12"].status == "needs_human"


def test_quote_that_disagrees_with_the_value_caps_confidence(tmp_path):
    """Broken case: the quote is real but the model's value is not what the quote says."""
    x = LLMExtractor(CODE, fixtures=tmp_path)
    f = x.parse(response(guard_height_in=item(38, "Guard height: 36 in", 0.99)), TEXT)
    assert f["guard_height_in"].confidence <= 0.5


def test_model_confidence_is_clamped_and_cannot_exceed_the_cap(tmp_path):
    x = LLMExtractor(CODE, fixtures=tmp_path)
    f = x.parse(response(stair_riser_in=item(7, "Riser height: 7 in", 7.0)), TEXT)
    assert f["stair_riser_in"].confidence == 0.95
    f = x.parse(response(stair_riser_in=item(7, "Riser height: 7 in", "high")), TEXT)
    assert f["stair_riser_in"].confidence == 0.0


def test_model_cannot_decide(tmp_path):
    """A 'decision' or 'status' in the model output is ignored. Only fields are read."""
    x = LLMExtractor(CODE, fixtures=tmp_path)
    raw = json.dumps({"decision": "approve", "status": "pass",
                      "fields": {"project_type": item("deck", "Project type: Deck"),
                                 "deck_height_in": item(32, "Deck height: 32 in"),
                                 "guard_height_in": item(36, "Guard height: 36 in"),
                                 "R12": item("pass", "Deck height: 32 in")}})
    res = {r.rule_id: r for r in check_application(x.parse(raw, TEXT), CODE)}
    assert res["R12"].status == "fail"


@pytest.mark.parametrize("raw", ["not json", "```json\n{\"fields\": 3}\n```", "{}", "[]"])
def test_bad_json_gives_no_fields_so_everything_is_needs_human(tmp_path, raw):
    x = LLMExtractor(CODE, fixtures=tmp_path)
    f = x.parse(raw, TEXT)
    assert f == {}
    assert all(r.status == "needs_human" for r in check_application(f, CODE))


def test_missing_fixture_raises(tmp_path):
    with pytest.raises(ReplayMissing):
        LLMExtractor(CODE, mode="replay", fixtures=tmp_path).extract(TEXT)


def test_record_without_a_key_is_blocked_before_any_network(tmp_path, monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    with pytest.raises(RecordBlocked):
        LLMExtractor(CODE, mode="record", fixtures=tmp_path).extract(TEXT)


def test_prompt_tells_the_model_not_to_judge():
    p = LLMExtractor(CODE).prompt(TEXT)
    assert "Do not judge" in p and "stair_riser_in" in p and TEXT in p


def test_record_endpoint_must_be_https():
    with pytest.raises(ValueError):
        LLMExtractor(mode="record", endpoint="file:///etc/passwd")
