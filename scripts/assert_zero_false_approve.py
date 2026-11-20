"""Exit 0 only if a results file shows zero false approves on seeded critical violations.
Run: .venv/bin/python scripts/assert_zero_false_approve.py results/eval_heldout_rule.json"""

import json
import sys
from pathlib import Path


def main(path: str) -> int:
    p = Path(path)
    if not p.exists():
        print(f"{path}: missing. This extractor has no results (see BLOCKERS.md).")
        return 1
    r = json.loads(p.read_text())
    fa = r["false_approve_critical_violations"]
    print(f"{path}: {r['split']}, {r['extractor']}, false approves {fa['k']} of {fa['n']} critical violations, "
          f"{r['false_approve_apps']['k']} of {r['false_approve_apps']['n']} applications")
    ok = fa["k"] == 0 and fa["n"] > 0 and r["false_approve_apps"]["k"] == 0
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
