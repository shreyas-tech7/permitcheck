"""Run the pipeline over a split and score it against the answer keys."""

import json
import platform
from pathlib import Path

from .checker import check_application
from .codefile import load_code
from .metrics import field_counts, prf, rate
from .report import cited_sections, letter_md

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"


def load_split(split: str, data: Path = DATA) -> list[str]:
    s = json.loads((data / "split.json").read_text())
    return s["dev"] + s["heldout"] if split == "all" else s[split]


def evaluate(split: str, extractor, data: Path = DATA, code: dict | None = None) -> dict:
    code = code or load_code()
    meta = json.loads((data / "meta.json").read_text())
    tp = fp = fn = 0
    v_tp = v_fp = v_fn = 0
    fa_apps = crit_apps = fa_viol = crit_viol = 0
    any_pass_on_viol = n_viol = 0
    nh = decisions = agree = 0
    cites = valid = 0
    apps_with_nh = 0
    false_approves = []
    ids = load_split(split, data)
    for app_id in ids:
        key = json.loads((data / "answer_keys" / f"{app_id}.json").read_text())
        text = (data / "applications" / f"{app_id}.txt").read_text()
        fields = extractor.extract(text)
        a, b, c = field_counts(key, fields)
        tp, fp, fn = tp + a, fp + b, fn + c
        res = {r.rule_id: r for r in check_application(fields, code)}
        viol = {v["rule_id"]: v["critical"] for v in key["violations"]}
        app_nh = False
        app_fa = False
        for rid, want in key["expected"].items():
            got = res[rid].status if rid in res else "needs_human"
            decisions += 1
            agree += got == want
            if got == "needs_human":
                nh += 1
                app_nh = True
            if rid in viol:
                n_viol += 1
                any_pass_on_viol += got == "pass"
                if got == "fail":
                    v_tp += 1
                else:
                    v_fn += 1
                if viol[rid]:
                    crit_viol += 1
                    if got == "pass":
                        fa_viol += 1
                        app_fa = True
                        false_approves.append({"app_id": app_id, "rule_id": rid})
            elif got == "fail":
                v_fp += 1
        apps_with_nh += app_nh
        if any(viol.values()):
            crit_apps += 1
            fa_apps += app_fa
        letter = letter_md(app_id, list(res.values()), code)
        for rid, section in cited_sections(letter):
            cites += 1
            valid += section in code["by_section"] and code["by_section"][section]["id"] == rid
    return {
        "synthetic": True,
        "split": split,
        "n_apps": len(ids),
        "extractor": extractor.name,
        "model": getattr(extractor, "model", "none (rule-based, no model)"),
        "data_seed": meta["seed"],
        "code_version": code["version"],
        "code_sha256": code["sha256"],
        "field": prf(tp, fp, fn),
        "violation": {
            "tp": v_tp, "fp": v_fp, "fn": v_fn,
            "precision": rate(v_tp, v_tp + v_fp),
            "recall": rate(v_tp, v_tp + v_fn),
        },
        "false_approve_apps": rate(fa_apps, crit_apps),
        "false_approve_critical_violations": rate(fa_viol, crit_viol),
        "pass_on_any_violation": rate(any_pass_on_viol, n_viol),
        "false_approves": false_approves,
        "needs_human_decisions": rate(nh, decisions),
        "apps_with_any_needs_human": rate(apps_with_nh, len(ids)),
        "agreement_with_expected": rate(agree, decisions),
        "citation_validity": {"valid": valid, "cited": cites, "value": valid / cites if cites else None,
                              "note": "A fixed count over every letter. No sampling error."},
    }


def run_info() -> dict:
    return {"python": platform.python_version(), "machine": platform.machine()}
