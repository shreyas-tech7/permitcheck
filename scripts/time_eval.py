"""Time the rule-based pipeline on all 300 applications on 2 cores and write results/timing.json.
Run: taskset -c 0,1 .venv/bin/python scripts/time_eval.py"""

import datetime as dt
import json
import os
import platform
import time
from pathlib import Path

from permitcheck.checker import check_application
from permitcheck.codefile import load_code
from permitcheck.extract import RuleExtractor
from permitcheck.report import checklist_md, letter_md, queue_items

ROOT = Path(__file__).resolve().parent.parent


def cpu_model() -> str:
    for line in Path("/proc/cpuinfo").read_text().splitlines():
        if line.startswith("model name"):
            return line.split(":", 1)[1].strip()
    return platform.processor() or "unknown"


def main() -> None:
    code = load_code()
    x = RuleExtractor(code)
    apps = sorted((ROOT / "data" / "applications").glob("*.txt"))
    best = None
    for _ in range(3):
        t0 = time.perf_counter()
        for p in apps:
            res = check_application(x.extract(p.read_text()), code)
            checklist_md(p.stem, res, code), letter_md(p.stem, res, code), queue_items(p.stem, res)
        secs = time.perf_counter() - t0
        best = secs if best is None else min(best, secs)
    out = {
        "date": dt.date.today().isoformat(), "cpu": cpu_model(), "cores_used": len(os.sched_getaffinity(0)),
        "python": platform.python_version(), "n_apps": len(apps), "best_of_3_seconds": round(best, 3),
        "ms_per_app": round(1000 * best / len(apps), 2), "model_calls": 0, "cost_usd": 0.0,
        "note": "Rule-based extractor, checker and all three writers. No network and no model.",
    }
    (ROOT / "results" / "timing.json").write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps(out))


if __name__ == "__main__":
    main()
