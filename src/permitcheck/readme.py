"""Write the README results and cost tables from the results files. Nobody types these numbers."""

import json
from pathlib import Path

from .metrics import wilson

BLOCKS = ("results", "cost")


def _pct(x) -> str:
    return "n/a" if x is None else f"{100 * x:.1f}%"


def _cell(k: int, n: int) -> str:
    lo, hi = wilson(k, n)
    if n == 0:
        return "n/a (n = 0)"
    return f"{_pct(k / n)} ({k} of {n}), CI {_pct(lo)} to {_pct(hi)}"


def results_block(results: Path) -> str:
    runs = [("Dev", results / "eval_dev_rule.json"), ("Held-out", results / "eval_heldout_rule.json"),
            ("Second seed", results / "seed2" / "eval_all_rule.json")]
    data = [(name, json.loads(p.read_text())) for name, p in runs]
    head = "| Metric | " + " | ".join(f"{n} ({d['n_apps']} apps, seed {d['data_seed']})" for n, d in data) + " |"
    rows = [head, "| --- |" + " --- |" * len(data)]

    def row(label, fn):
        rows.append(f"| {label} | " + " | ".join(fn(d) for _, d in data) + " |")

    row("Field F1", lambda d: f"{d['field']['f1']:.3f}")
    row("Field precision", lambda d: _cell(d["field"]["tp"], d["field"]["tp"] + d["field"]["fp"]))
    row("Field recall", lambda d: _cell(d["field"]["tp"], d["field"]["tp"] + d["field"]["fn"]))
    row("Violation precision", lambda d: _cell(d["violation"]["precision"]["k"], d["violation"]["precision"]["n"]))
    row("Violation recall", lambda d: _cell(d["violation"]["recall"]["k"], d["violation"]["recall"]["n"]))
    row("**False-approve rate** (applications with a critical violation)",
        lambda d: _cell(d["false_approve_apps"]["k"], d["false_approve_apps"]["n"]))
    row("False approves per critical violation",
        lambda d: _cell(d["false_approve_critical_violations"]["k"], d["false_approve_critical_violations"]["n"]))
    row("Needs-human rate (rule decisions)",
        lambda d: _cell(d["needs_human_decisions"]["k"], d["needs_human_decisions"]["n"]))
    row("Citation validity (fixed count, no interval)",
        lambda d: f"{_pct(d['citation_validity']['value'])} ({d['citation_validity']['valid']} of "
                  f"{d['citation_validity']['cited']})")
    held = data[1][1]
    fa = held["false_approve_critical_violations"]
    _, upper = wilson(0, fa["n"]) if fa["k"] == 0 else wilson(fa["k"], fa["n"])
    note = (f"\nExtractor: `{held['extractor']}`. Model: {held['model']}. Code: LHRC {held['code_version']}. "
            f"Run date: {held['run']['date']}. CI means a 95% Wilson score interval.\n\n"
            f"The held-out set holds {fa['n']} seeded critical violations in {held['false_approve_apps']['n']} "
            f"applications. The tool marked {fa['k']} of them as pass. A zero count from a sample this small "
            f"still leaves a 95% upper bound of {_pct(upper)} per critical violation, so this run cannot rule "
            "out a rare false approve.\n")
    return "\n".join(rows) + "\n" + note


def cost_block(results: Path) -> str:
    t = json.loads((results / "timing.json").read_text())
    return (f"\n$0.00 per application. The rule-based extractor makes {t['model_calls']} model calls. "
            f"One application takes {t['ms_per_app']} ms to extract, check and write all three outputs "
            f"({t['n_apps']} applications, best of 3, {t['cores_used']} cores of an {t['cpu']}, "
            f"Python {t['python']}, {t['date']}, from `results/timing.json`).\n")


def _replace(text: str, name: str, body: str) -> str:
    start, end = f"<!-- {name}:start -->", f"<!-- {name}:end -->"
    a, b = text.index(start) + len(start), text.index(end)
    return text[:a] + "\n" + body + text[b:]


def render(readme: Path, results: Path, check: bool = False) -> int:
    text = readme.read_text(encoding="utf-8")
    new = _replace(_replace(text, "results", results_block(results)), "cost", cost_block(results))
    if check:
        if new != text:
            print("README tables differ from the results files. Run: permitcheck readme")
            return 1
        print("README tables match the results files")
        return 0
    readme.write_text(new, encoding="utf-8")
    print(f"wrote tables in {readme}")
    return 0
