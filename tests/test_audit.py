import json

from permitcheck.audit import append_audit
from permitcheck.checker import check_application
from permitcheck.codefile import load_code
from permitcheck.extract import RuleExtractor

CODE = load_code()
TEXT = "Project type: Deck\nZoning: R2\nRiser height: 8 in\nRear setback: 18\n"


def test_one_line_per_decision_with_version_inputs_and_extractor(tmp_path):
    x = RuleExtractor(CODE)
    fields = x.extract(TEXT)
    res = check_application(fields, CODE)
    log = tmp_path / "audit.jsonl"
    append_audit(log, "LH-APP-9999", TEXT, fields, res, CODE, x.name, now="2026-11-20T00:00:00Z")
    lines = [json.loads(s) for s in log.read_text().splitlines()]
    assert len(lines) == len(res)
    for line, r in zip(lines, res, strict=True):
        assert line["rule_id"] == r.rule_id and line["status"] == r.status and line["section"] == r.section
        assert line["rule_version"] == "2026.1"
        assert line["code_sha256"] == CODE["sha256"]
        assert line["extractor"] == "rule-v1"
        assert line["time"] == "2026-11-20T00:00:00Z"
        assert len(line["app_sha256"]) == 64
        assert line["synthetic"] is True
    riser = next(s for s in lines if s["rule_id"] == "R14")
    assert riser["inputs"]["stair_riser_in"] == {"value": 8, "confidence": 0.95}
    rear = next(s for s in lines if s["rule_id"] == "R08")
    assert rear["status"] == "needs_human"


def test_log_appends_and_never_overwrites(tmp_path):
    x = RuleExtractor(CODE)
    fields = x.extract(TEXT)
    res = check_application(fields, CODE)
    log = tmp_path / "audit.jsonl"
    append_audit(log, "A", TEXT, fields, res, CODE, x.name, now="t1")
    append_audit(log, "B", TEXT, fields, res, CODE, x.name, now="t2")
    lines = [json.loads(s) for s in log.read_text().splitlines()]
    assert len(lines) == 2 * len(res)
    assert lines[0]["app_id"] == "A" and lines[-1]["app_id"] == "B"
