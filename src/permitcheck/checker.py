"""Plain-code rule checks. Every result is pass, fail or needs_human, with the section it cites.

The extractor only supplies values and confidences. This module decides. A missing value, a value
below CONFIDENCE_THRESHOLD, or a value of the wrong type is needs_human. It never guesses a pass.
"""

import re
from dataclasses import dataclass, field

CONFIDENCE_THRESHOLD = 0.8
OPS = {">": lambda a, b: a > b, ">=": lambda a, b: a >= b, "<": lambda a, b: a < b,
       "<=": lambda a, b: a <= b, "==": lambda a, b: a == b}
OP_WORDS = {">": "more than", ">=": "at least", "<": "less than", "<=": "at most", "==": "exactly"}
UNITS = {"length_ft": " ft", "length_in": " in", "area": " sq ft", "money": " dollars"}
STATUSES = ("pass", "fail", "needs_human")


@dataclass
class Result:
    rule_id: str
    section: str
    title: str
    critical: bool
    status: str
    reason: str
    inputs: dict = field(default_factory=dict)


class _Unclear(Exception):
    pass


def _label(name: str) -> str:
    return re.sub(r"_(ft|in|sqft|usd)$", "", name).replace("_", " ")


def _get(fields: dict, name: str, inputs: dict, numeric: bool = False):
    f = fields.get(name)
    if f is None or f.value is None:
        inputs[name] = None
        raise _Unclear(f"the {_label(name)} ({name}) is missing")
    inputs[name] = {"value": f.value, "confidence": f.confidence}
    if f.confidence < CONFIDENCE_THRESHOLD:
        raise _Unclear(f"the {_label(name)} ({name}) was read with low confidence ({f.confidence:.2f})")
    if numeric and (isinstance(f.value, bool) or not isinstance(f.value, (int, float))):
        raise _Unclear(f"the {_label(name)} ({name}) is not a number")
    return f.value


def _fmt(v, name, code):
    kind = code["fields"][name]["kind"] if code else ""
    if isinstance(v, float) and v.is_integer():
        v = int(v)
    return f"{v}{UNITS.get(kind, '')}"


def _simple(check: dict, fields: dict, inputs: dict, code: dict | None):
    """Return (status, reason) for a check that is not conditional."""
    t = check["type"]
    name = check.get("field")
    if t == "is_true":
        v = _get(fields, name, inputs)
        if not isinstance(v, bool):
            raise _Unclear(f"the {_label(name)} answer is not a yes or no")
        return ("pass", f"{_label(name)}: yes") if v else ("fail", f"{_label(name)}: no")
    if t == "pattern":
        v = _get(fields, name, inputs)
        ok = re.fullmatch(check["regex"], str(v)) is not None
        return ("pass" if ok else "fail"), f"{_label(name)} is {v}"
    if t == "in_set":
        v = _get(fields, name, inputs)
        allowed = ", ".join(check["values"])
        if v in check["values"]:
            return "pass", f"{_label(name)} is {v}"
        return "fail", f"{_label(name)} is {v}, and this section allows {allowed}"
    if t in ("min", "max"):
        v = _get(fields, name, inputs, numeric=True)
        lim = check["limit"]
        ok = v >= lim if t == "min" else v <= lim
        need = "at least" if t == "min" else "at most"
        return ("pass" if ok else "fail"), (f"{_label(name)} is {_fmt(v, name, code)}, and this section "
                                            f"requires {need} {_fmt(lim, name, code)}")
    if t == "min_by_district":
        d = _get(fields, check["district_field"], inputs)
        v = _get(fields, name, inputs, numeric=True)
        lim = check["limits"].get(d)
        if lim is None:
            raise _Unclear(f"this section sets no limit for district {d}")
        ok = v >= lim
        return ("pass" if ok else "fail"), (f"{_label(name)} is {_fmt(v, name, code)}, and district {d} "
                                            f"requires at least {_fmt(lim, name, code)}")
    if t == "ratio_max":
        parts = [_get(fields, f, inputs, numeric=True) for f in check["fields"]]
        lot = _get(fields, check["denominator"], inputs, numeric=True)
        if lot <= 0:
            raise _Unclear("the lot area is zero or less")
        ratio = sum(parts) / lot
        ok = sum(parts) <= check["limit"] * lot
        return ("pass" if ok else "fail"), (f"coverage is {ratio:.1%} ({sum(parts):g} of {lot:g} sq ft), and "
                                            f"this section allows at most {check['limit']:.0%}")
    raise ValueError(f"unknown check type {t}")


def check_rule(rule: dict, fields: dict, code: dict | None = None) -> Result:
    """Run one rule on extracted fields."""
    inputs: dict = {}
    check = rule["check"]
    try:
        if check["type"] == "conditional":
            w = check["when"]
            cv = _get(fields, w["field"], inputs, numeric=True)
            if not OPS[w["op"]](cv, w["value"]):
                status = "pass"
                reason = (f"not required: {_label(w['field'])} is {_fmt(cv, w['field'], code)}, which is not "
                          f"{OP_WORDS[w['op']]} {_fmt(w['value'], w['field'], code)}")
            else:
                status, reason = _simple(check["then"], fields, inputs, code)
        else:
            status, reason = _simple(check, fields, inputs, code)
    except _Unclear as e:
        status, reason = "needs_human", f"needs a person: {e}"
    return Result(rule["id"], rule["section"], rule["title"], rule["critical"], status, reason, inputs)


def check_application(fields: dict, code: dict) -> list[Result]:
    """Run every rule that applies to the project type. If the type is unclear, every rule is needs_human."""
    pt = fields.get("project_type")
    if pt is None or pt.value not in ("deck", "addition") or pt.confidence < CONFIDENCE_THRESHOLD:
        why = "needs a person: the project type is missing or unclear, so the tool cannot tell which rules apply"
        inputs = {"project_type": None if pt is None else {"value": pt.value, "confidence": pt.confidence}}
        return [Result(r["id"], r["section"], r["title"], r["critical"], "needs_human", why, dict(inputs))
                for r in code["rules"]]
    return [check_rule(r, fields, code) for r in code["rules"] if pt.value in r["applies_to"]]
