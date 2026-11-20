from permitcheck.checker import check_application
from permitcheck.codefile import load_code
from permitcheck.disclaimer import DISCLAIMER
from permitcheck.extract import Field
from permitcheck.report import checklist_md, queue_items

CODE = load_code()


def results():
    f = {"project_type": "deck", "zoning_district": "R2", "stair_riser_in": 8.0, "joist_spacing_in": 12,
         "footing_depth_in": 20}
    fields = {k: Field(v, 0.95, "t") for k, v in f.items()}
    fields["rear_setback_ft"] = Field(18, 0.4, "t")
    return check_application(fields, CODE)


def test_checklist_lists_every_result_with_section_and_status():
    res = results()
    md = checklist_md("LH-APP-9999", res, CODE)
    assert DISCLAIMER in md
    for r in res:
        assert r.section in md and r.rule_id in md
    assert md.index("## Fail") < md.index("## Needs a person") < md.index("## Pass")
    assert "- [ ]" in md


def test_queue_has_only_needs_human_items_with_critical_first():
    res = results()
    q = queue_items("LH-APP-9999", res)
    assert q and all(i["status"] == "needs_human" for i in q)
    assert {i["rule_id"] for i in q} == {r.rule_id for r in res if r.status == "needs_human"}
    crit = [i["critical"] for i in q]
    assert crit == sorted(crit, reverse=True)
    assert all(i["app_id"] == "LH-APP-9999" and i["section"] for i in q)
