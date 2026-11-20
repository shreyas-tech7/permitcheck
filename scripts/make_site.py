"""Write docs/index.html, a static results page that opens from disk with no server.
Every number comes from the results files. Run: .venv/bin/python scripts/make_site.py"""

import html
import json
from pathlib import Path

from permitcheck.disclaimer import DISCLAIMER
from permitcheck.metrics import wilson

ROOT = Path(__file__).resolve().parent.parent
RUNS = [("Dev", "eval_dev_rule.json"), ("Held-out", "eval_heldout_rule.json"),
        ("Second seed", "seed2/eval_all_rule.json")]
EXAMPLES = ["LH-APP-0018", "LH-APP-0064"]


def pct(x) -> str:
    return "n/a" if x is None else f"{100 * x:.1f}%"


def cell(k: int, n: int) -> str:
    lo, hi = wilson(k, n)
    return "n/a" if n == 0 else f"{pct(k / n)} <small>({k} of {n}, CI {pct(lo)} to {pct(hi)})</small>"


def main() -> None:
    runs = [(name, json.loads((ROOT / "results" / f).read_text())) for name, f in RUNS]
    rows = [
        ("Field F1", lambda d: f"{d['field']['f1']:.3f}"),
        ("Violation precision", lambda d: cell(d["violation"]["precision"]["k"], d["violation"]["precision"]["n"])),
        ("Violation recall", lambda d: cell(d["violation"]["recall"]["k"], d["violation"]["recall"]["n"])),
        ("False approves per critical violation", lambda d: cell(d["false_approve_critical_violations"]["k"],
                                                                 d["false_approve_critical_violations"]["n"])),
        ("False-approve rate (applications)",
         lambda d: cell(d["false_approve_apps"]["k"], d["false_approve_apps"]["n"])),
        ("Needs-human rate", lambda d: cell(d["needs_human_decisions"]["k"], d["needs_human_decisions"]["n"])),
        ("Citation validity (fixed count)", lambda d: f"{pct(d['citation_validity']['value'])} <small>("
                                                       f"{d['citation_validity']['valid']} of "
                                                       f"{d['citation_validity']['cited']})</small>"),
    ]
    head = "".join(f"<th>{n}<br><small>{d['n_apps']} apps, seed {d['data_seed']}</small></th>" for n, d in runs)
    body = "".join(f"<tr><th scope=row>{label}</th>" + "".join(f"<td>{fn(d)}</td>" for _, d in runs) + "</tr>"
                   for label, fn in rows)
    held = runs[1][1]
    ex = []
    for app in EXAMPLES:
        q = json.loads((ROOT / "examples" / app / "queue.json").read_text())
        letter = (ROOT / "examples" / app / "letter.md").read_text()
        ex.append(f"<h3>{app}</h3><p><a href=\"../examples/{app}/checklist.md\">Checklist</a> · "
                  f"<a href=\"../examples/{app}/letter.md\">Letter</a> · "
                  f"<a href=\"../data/applications/{app}.txt\">Application text</a> · "
                  f"{len(q['items'])} items in the review queue</p><pre>{html.escape(letter)}</pre>")
    page = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>permitcheck results</title>
<style>
:root {{ --bg: #f7f8f5; --fg: #1c241f; --muted: #5a665e; --line: #d6dbd4; --accent: #9a6a12; }}
@media (prefers-color-scheme: dark) {{ :root {{ --bg: #18201c; --fg: #e9eee8; --muted: #a3b0a6;
  --line: #34403a; --accent: #e8b048; }} }}
body {{ background: var(--bg); color: var(--fg); font: 16px/1.5 system-ui, sans-serif; margin: 0 auto;
  max-width: 980px; padding: 24px 16px; }}
.warn {{ border: 2px solid var(--accent); padding: 8px 12px; font-weight: 600; }}
table {{ border-collapse: collapse; width: 100%; display: block; overflow-x: auto; }}
th, td {{ border-bottom: 1px solid var(--line); padding: 6px 8px; text-align: left; vertical-align: top; }}
small, .muted {{ color: var(--muted); }}
pre {{ white-space: pre-wrap; border: 1px solid var(--line); padding: 12px; font-size: 13px; }}
a {{ color: var(--accent); }}
</style>
</head>
<body>
<p class="warn">{html.escape(DISCLAIMER)}</p>
<h1>permitcheck</h1>
<p>The model reads. Code decides. permitcheck checks a synthetic permit application against a fictional city code,
cites each section, and sends anything unclear to a person.</p>
<p>A <b>false approve</b> is an application with at least one seeded critical violation that the tool marks as pass
on that rule.</p>
<h2>Results</h2>
<table><thead><tr><th>Metric</th>{head}</tr></thead><tbody>{body}</tbody></table>
<p class="muted">Extractor {held['extractor']}. Model: {held['model']}. Code LHRC {held['code_version']}.
Run date {held['run']['date']}. CI is a 95% Wilson score interval. A zero count from a small sample still has a wide
upper bound.</p>
<h2>Worked examples</h2>
{''.join(ex)}
<p class="muted">Written by scripts/make_site.py from the results and examples folders.
See the <a href="../README.md">README</a>.</p>
</body>
</html>
"""
    (ROOT / "docs" / "index.html").write_text(page, encoding="utf-8")


if __name__ == "__main__":
    main()
