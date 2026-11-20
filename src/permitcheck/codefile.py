"""Load and check the fictional city code file (src/permitcheck/data/city_code.json)."""

import hashlib
import json
import re
from pathlib import Path

DEFAULT_PATH = Path(__file__).parent / "data" / "city_code.json"

KINDS = {"choice", "text", "bool", "money", "area", "length_ft", "length_in", "count"}
CHECK_TYPES = {"is_true", "pattern", "min", "max", "in_set", "min_by_district", "ratio_max", "conditional"}
OPS = {">", ">=", "<", "<=", "=="}
SECTION_RE = re.compile(r"^LHRC \d+\.\d+\.\d+$")
PROJECT_TYPES = {"deck", "addition"}


class CodeFileError(ValueError):
    pass


def load_code(path: Path | str | None = None) -> dict:
    """Read the code file, check its schema, and return it with its sha256 added."""
    p = Path(path) if path else DEFAULT_PATH
    raw = p.read_bytes()
    code = json.loads(raw)
    errors = validate(code)
    if errors:
        raise CodeFileError("; ".join(errors))
    code["sha256"] = hashlib.sha256(raw).hexdigest()
    code["by_id"] = {r["id"]: r for r in code["rules"]}
    code["by_section"] = {r["section"]: r for r in code["rules"]}
    return code


def rule_fields(check: dict) -> list[str]:
    """Every field a check reads, condition fields first."""
    t = check["type"]
    if t == "conditional":
        return [check["when"]["field"], *rule_fields(check["then"])]
    if t == "min_by_district":
        return [check["district_field"], check["field"]]
    if t == "ratio_max":
        return [*check["fields"], check["denominator"]]
    return [check["field"]]


def _check_errors(rid: str, check: dict, fields: dict, nested: bool = False) -> list[str]:
    errs = []
    t = check.get("type")
    if t not in CHECK_TYPES:
        return [f"{rid}: unknown check type {t!r}"]
    if t == "conditional":
        if nested:
            errs.append(f"{rid}: nested conditional")
        when = check.get("when", {})
        if when.get("op") not in OPS:
            errs.append(f"{rid}: bad op {when.get('op')!r}")
        if not isinstance(when.get("value"), (int, float)):
            errs.append(f"{rid}: condition value must be a number")
        if when.get("field") not in fields:
            errs.append(f"{rid}: unknown field {when.get('field')!r}")
        errs += _check_errors(rid, check.get("then", {}), fields, nested=True)
        return errs
    for f in rule_fields(check):
        if f not in fields:
            errs.append(f"{rid}: unknown field {f!r}")
    if t in ("min", "max", "ratio_max") and not isinstance(check.get("limit"), (int, float)):
        errs.append(f"{rid}: limit must be a number")
    if t == "in_set" and not check.get("values"):
        errs.append(f"{rid}: in_set needs values")
    if t == "pattern":
        try:
            re.compile(check.get("regex", ""))
        except re.error as e:
            errs.append(f"{rid}: bad regex {e}")
    if t == "min_by_district" and not check.get("limits"):
        errs.append(f"{rid}: min_by_district needs limits")
    return errs


def validate(code: dict) -> list[str]:
    """Return a list of schema errors. An empty list means the file is valid."""
    errs = []
    for key in ("code_name", "short_name", "version", "fields", "rules"):
        if key not in code:
            errs.append(f"missing key {key!r}")
    if errs:
        return errs
    if code.get("fictional") is not True:
        errs.append("the code file must say fictional: true")
    fields = code["fields"]
    for name, spec in fields.items():
        if spec.get("kind") not in KINDS:
            errs.append(f"field {name}: unknown kind {spec.get('kind')!r}")
    seen_ids, seen_sections = set(), set()
    for r in code["rules"]:
        rid = r.get("id", "?")
        for key in ("id", "section", "title", "text", "applies_to", "critical", "check"):
            if key not in r:
                errs.append(f"{rid}: missing {key!r}")
        if errs:
            continue
        if not re.fullmatch(r"R\d{2}", rid):
            errs.append(f"{rid}: id must look like R01")
        if rid in seen_ids:
            errs.append(f"{rid}: duplicate id")
        if r["section"] in seen_sections:
            errs.append(f"{rid}: duplicate section {r['section']}")
        if not SECTION_RE.match(r["section"]):
            errs.append(f"{rid}: section must look like 'LHRC 10.1.1'")
        if not set(r["applies_to"]) <= PROJECT_TYPES or not r["applies_to"]:
            errs.append(f"{rid}: applies_to must name deck and/or addition")
        if not isinstance(r["critical"], bool):
            errs.append(f"{rid}: critical must be true or false")
        seen_ids.add(rid)
        seen_sections.add(r["section"])
        errs += _check_errors(rid, r["check"], fields)
    return errs
