"""The README tables come from the results files, and the prose outside them carries no typed numbers."""

import json
import re
from pathlib import Path

from permitcheck.readme import BLOCKS, render

ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"
PARTS = ["## The problem", "```mermaid", "## Results", "## Cost per task", "## Run it in ten minutes",
         "## Limits", "## Glossary", "## Related work", "## How this was built"]
# Tokens that hold digits but are names, not measurements.
ALLOWED = [r"(?m)^\d+\. ", r"v0\.1\.0-rc1", r"Python 3\.11", r"95%", r"LH-APP-\d{4}", r"\bR\d{2}\b", r"badge\.svg"]


def test_readme_tables_match_results(tmp_path):
    copy = tmp_path / "README.md"
    copy.write_text(README.read_text(encoding="utf-8"), encoding="utf-8")
    assert render(copy, ROOT / "results", check=True) == 0


def test_render_rewrites_a_stale_number(tmp_path):
    copy = tmp_path / "README.md"
    copy.write_text(README.read_text(encoding="utf-8").replace("Field F1 | ", "Field F1 | 0.999 "), encoding="utf-8")
    assert render(copy, ROOT / "results", check=True) == 1
    render(copy, ROOT / "results")
    assert copy.read_text(encoding="utf-8") == README.read_text(encoding="utf-8")


def test_headline_numbers_appear_in_the_readme():
    text = README.read_text(encoding="utf-8")
    held = json.loads((ROOT / "results" / "eval_heldout_rule.json").read_text())
    fa = held["false_approve_critical_violations"]
    assert f"{fa['k']} of {fa['n']}" in text
    assert f"{held['field']['f1']:.3f}" in text
    assert str(held["data_seed"]) in text
    assert held["run"]["date"] in text


def test_readme_parts_in_order():
    text = README.read_text(encoding="utf-8")
    pos = [text.index(p) for p in PARTS]
    assert pos == sorted(pos)
    assert text.index("**Status:**") < pos[0]
    assert "actions/workflows/ci.yml/badge.svg" in text
    assert "docs/build/BUILD_PROMPT.md" in text
    assert "not done yet" in text


def test_no_typed_numbers_outside_generated_blocks():
    text = README.read_text(encoding="utf-8")
    for name in BLOCKS:
        text = re.sub(rf"<!-- {name}:start -->.*?<!-- {name}:end -->", "", text, flags=re.S)
    text = re.sub(r"```.*?```", "", text, flags=re.S)
    text = re.sub(r"`[^`]*`", "", text)
    text = re.sub(r"\([^)]*\)", lambda m: "" if "/" in m.group(0) else m.group(0), text)
    for pat in ALLOWED:
        text = re.sub(pat, "", text)
    left = [line for line in text.splitlines() if re.search(r"\d", line)]
    assert left == [], left


def test_no_dashes_or_semicolons_in_readme_prose():
    text = re.sub(r"```.*?```", "", README.read_text(encoding="utf-8"), flags=re.S)
    assert "—" not in text and "–" not in text
    prose = [ln for ln in text.splitlines() if ln and not ln.startswith(("|", "<!--", "[!["))]
    assert not [ln for ln in prose if ";" in ln]
    assert not [ln for ln in prose if " - " in ln]
