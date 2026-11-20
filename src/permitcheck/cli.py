"""The permitcheck command: generate, check, eval and readme. Every command prints the disclaimer first."""

import argparse
import datetime as dt
import json
import sys
import time
from pathlib import Path

from .audit import append_audit
from .checker import check_application
from .codefile import load_code
from .disclaimer import DISCLAIMER
from .evaluate import DATA, ROOT, evaluate
from .extract import RuleExtractor
from .generator import generate
from .report import checklist_md, letter_md, queue_items

RUN_KEYS = ("run",)


def make_extractor(name: str, code: dict):
    if name == "rule":
        return RuleExtractor(code)
    from .llm import LLMExtractor
    if name == "llm-replay":
        return LLMExtractor(code, mode="replay")
    if name == "llm-record":
        return LLMExtractor(code, mode="record")
    raise SystemExit(f"unknown extractor {name!r}")


def cmd_generate(a) -> int:
    keys = generate(a.seed, a.n, a.out)
    crit = sum(1 for k in keys for v in k["violations"] if v["critical"])
    print(f"wrote {len(keys)} synthetic applications to {a.out} (seed {a.seed}, {crit} critical violations)")
    return 0


def cmd_check(a) -> int:
    code = load_code()
    x = make_extractor(a.extractor, code)
    path = Path(a.application)
    text = path.read_text(encoding="utf-8")
    app_id = a.app_id or path.stem
    fields = x.extract(text)
    results = check_application(fields, code)
    out = Path(a.out) / app_id
    out.mkdir(parents=True, exist_ok=True)
    (out / "checklist.md").write_text(checklist_md(app_id, results, code), encoding="utf-8")
    (out / "letter.md").write_text(letter_md(app_id, results, code), encoding="utf-8")
    queue = {"disclaimer": DISCLAIMER, "items": queue_items(app_id, results)}
    (out / "queue.json").write_text(json.dumps(queue, indent=1) + "\n", encoding="utf-8")
    append_audit(a.audit or out / "audit.jsonl", app_id, text, fields, results, code, x.name, now=a.now)
    n = {s: sum(r.status == s for r in results) for s in ("fail", "needs_human", "pass")}
    print(f"{app_id}: {n['fail']} fail, {n['needs_human']} needs a person, {n['pass']} pass "
          f"({x.name}, {code['short_name']} {code['version']})")
    for r in results:
        if r.status != "pass":
            print(f"  {r.status:<11} [{r.rule_id}, {r.section}] {r.title}: {r.reason}")
    print(f"wrote {out}/checklist.md, letter.md, queue.json and the audit log")
    return 0


def _show(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(Path.cwd().resolve()))
    except ValueError:
        return str(path)


def _strip_run(d: dict) -> dict:
    return {k: v for k, v in d.items() if k not in RUN_KEYS}


def cmd_eval(a) -> int:
    code = load_code()
    x = make_extractor(a.extractor, code)
    splits = ["dev", "heldout"] if a.split == "both" else [a.split]
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    bad = 0
    for split in splits:
        t0 = time.perf_counter()
        res = evaluate(split, x, Path(a.data), code)
        secs = time.perf_counter() - t0
        res["run"] = {"date": dt.date.today().isoformat(), "seconds": round(secs, 3),
                      "ms_per_app": round(1000 * secs / res["n_apps"], 2)}
        path = out / f"eval_{split}_{a.extractor.split('-')[0]}.json"
        fa = res["false_approve_apps"]
        print(f"{split}: {res['n_apps']} apps, field F1 {res['field']['f1']:.3f}, "
              f"violation precision {res['violation']['precision']['value']:.3f}, "
              f"recall {res['violation']['recall']['value']:.3f}, "
              f"false approve {fa['k']}/{fa['n']} apps, needs a person "
              f"{res['needs_human_decisions']['value']:.3f} of decisions, "
              f"citations valid {res['citation_validity']['valid']}/{res['citation_validity']['cited']}")
        if a.check:
            if not path.exists():
                print(f"MISSING {_show(path)}")
                bad += 1
                continue
            old = json.loads(path.read_text())
            if _strip_run(old) != _strip_run(json.loads(json.dumps(res))):
                print(f"DRIFT {_show(path)}: a fresh run does not match the committed results")
                bad += 1
            else:
                print(f"ok {_show(path)} matches a fresh run")
        else:
            path.write_text(json.dumps(res, indent=1, sort_keys=True) + "\n", encoding="utf-8")
            print(f"wrote {_show(path)}")
    return 1 if bad else 0


def cmd_readme(a) -> int:
    from .readme import render
    return render(Path(a.readme), Path(a.results), check=a.check)


def main(argv=None) -> int:
    print(DISCLAIMER)
    p = argparse.ArgumentParser(prog="permitcheck", description=DISCLAIMER)
    sub = p.add_subparsers(dest="cmd", required=True)
    g = sub.add_parser("generate", help="write synthetic applications and answer keys")
    g.add_argument("--seed", type=int, default=20261120)
    g.add_argument("--n", type=int, default=300)
    g.add_argument("--out", default=str(DATA))
    g.set_defaults(fn=cmd_generate)
    c = sub.add_parser("check", help="check one application and write checklist, letter, queue, audit log")
    c.add_argument("application")
    c.add_argument("--out", default="out")
    c.add_argument("--extractor", default="rule", choices=["rule", "llm-replay", "llm-record"])
    c.add_argument("--audit", default=None, help="audit log path (default: <out>/<app>/audit.jsonl)")
    c.add_argument("--app-id", default=None)
    c.add_argument("--now", default=None, help="fixed timestamp for the audit log (for reproducible examples)")
    c.set_defaults(fn=cmd_check)
    e = sub.add_parser("eval", help="score the pipeline on dev and held-out applications")
    e.add_argument("--split", default="both", choices=["dev", "heldout", "all", "both"])
    e.add_argument("--extractor", default="rule", choices=["rule", "llm-replay", "llm-record"])
    e.add_argument("--data", default=str(DATA))
    e.add_argument("--out", default=str(ROOT / "results"))
    e.add_argument("--check", action="store_true", help="fail if a fresh run differs from the results files")
    e.set_defaults(fn=cmd_eval)
    r = sub.add_parser("readme", help="write the README tables from the results files")
    r.add_argument("--readme", default=str(ROOT / "README.md"))
    r.add_argument("--results", default=str(ROOT / "results"))
    r.add_argument("--check", action="store_true")
    r.set_defaults(fn=cmd_readme)
    a = p.parse_args(argv)
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
