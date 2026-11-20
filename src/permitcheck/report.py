"""Writers for the reviewer checklist, the correction letter and the review queue.

The letter may cite only sections that the checker returned, and each one must exist in the code
file and belong to the rule it names. Anything else raises CitationError.
"""

import re

from .disclaimer import DISCLAIMER

CITE_RE = re.compile(r"\[(R\d{2}), (LHRC \d+\.\d+\.\d+)\]")
HEADINGS = (("fail", "Fail"), ("needs_human", "Needs a person"), ("pass", "Pass"))


class CitationError(ValueError):
    pass


def _cite(r) -> str:
    return f"[{r.rule_id}, {r.section}]"


def checklist_md(app_id: str, results: list, code: dict) -> str:
    counts = {s: sum(1 for r in results if r.status == s) for s, _ in HEADINGS}
    out = [f"# Reviewer checklist: {app_id}", "", f"> {DISCLAIMER}", "",
           f"Checked against the {code['code_name']} ({code['short_name']}) version {code['version']}.",
           f"Fail: {counts['fail']}. Needs a person: {counts['needs_human']}. Pass: {counts['pass']}.", ""]
    for status, title in HEADINGS:
        out += [f"## {title}", ""]
        items = sorted((r for r in results if r.status == status), key=lambda r: (not r.critical, r.rule_id))
        if not items:
            out += ["None.", ""]
            continue
        for r in items:
            flag = " (critical)" if r.critical else ""
            out.append(f"- [ ] {_cite(r)} {r.title}{flag}: {r.reason}.")
        out.append("")
    return "\n".join(out)


def _check_citation(r, code: dict) -> None:
    rule = code["by_section"].get(r.section)
    if rule is None:
        raise CitationError(f"{r.section} is not in the code file")
    if rule["id"] != r.rule_id:
        raise CitationError(f"{r.section} belongs to {rule['id']}, not {r.rule_id}")


def letter_md(app_id: str, results: list, code: dict) -> str:
    """Plain-language correction letter. Only fail and needs_human items are cited."""
    fails = sorted((r for r in results if r.status == "fail"), key=lambda r: (not r.critical, r.rule_id))
    unclear = sorted((r for r in results if r.status == "needs_human"), key=lambda r: (not r.critical, r.rule_id))
    for r in fails + unclear:
        _check_citation(r, code)
    out = [f"# Correction letter: {app_id}", "", f"> {DISCLAIMER}", "", "Dear applicant,", "",
           f"We ran a first-pass check of application {app_id} against the {code['code_name']} "
           f"({code['short_name']}) version {code['version']}. A software tool wrote this draft. "
           "A reviewer reads it before it is sent.", ""]
    if not fails and not unclear:
        out += ["We found nothing to correct in this first pass.", ""]
    if fails:
        out += ["## Please correct these items", ""]
        for i, r in enumerate(fails, 1):
            rule = code["by_id"][r.rule_id]
            out.append(f"{i}. {_cite(r)} {r.title}. We read that {r.reason}. The code says: {rule['text']}")
        out.append("")
    if unclear:
        out += ["## Please confirm these items", "",
                "We could not read these clearly enough to decide. Please state each value plainly, with units.",
                ""]
        for i, r in enumerate(unclear, 1):
            rule = code["by_id"][r.rule_id]
            why = r.reason.removeprefix("needs a person: ")
            out.append(f"{i}. {_cite(r)} {r.title}. {why[:1].upper() + why[1:]}. The code says: {rule['text']}")
        out.append("")
    out += ["Thank you,", "", "Larkspur Hollow Building Division (fictional)", ""]
    return "\n".join(out)


def cited_sections(letter: str) -> list[tuple[str, str]]:
    return CITE_RE.findall(letter)


def queue_items(app_id: str, results: list) -> list[dict]:
    """The needs_human items for a reviewer, critical ones first."""
    items = [r for r in results if r.status == "needs_human"]
    items.sort(key=lambda r: (not r.critical, r.rule_id))
    return [{"app_id": app_id, "rule_id": r.rule_id, "section": r.section, "title": r.title,
             "critical": r.critical, "status": r.status, "reason": r.reason, "inputs": r.inputs} for r in items]
