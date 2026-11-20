"""Seeded generator for synthetic permit applications and their hidden answer keys.

Every application is fictional. The answer key logic here is written on its own, apart from
checker.py, so that a bug in the checker shows up in the eval instead of hiding in both places.
"""

import json
import random
from pathlib import Path

from .codefile import load_code, rule_fields

UNCLEAR = {"missing", "approx", "unitless", "conflict", "garbled"}

# Labels the generator writes. The extractor knows most of them. The ones in UNUSUAL are only
# here, so the eval measures how the extractor copes with wording it was not built for.
LABELS = {
    "project_type": ["Project type", "Type of work", "Work type"],
    "parcel_id": ["Parcel ID", "Parcel number", "APN"],
    "owner_signature": ["Owner signature", "Signed by owner", "Owner signed"],
    "contractor": ["Contractor license", "Contractor", "Builder"],
    "valuation_usd": ["Valuation", "Value of work", "Estimated cost"],
    "zoning_district": ["Zoning district", "Zoning", "Zone"],
    "lot_area_sqft": ["Lot area", "Lot size", "Parcel area"],
    "existing_footprint_sqft": ["Existing footprint", "Existing building footprint", "Existing coverage"],
    "new_area_sqft": ["Proposed area", "New floor area", "Area of new work"],
    "front_setback_ft": ["Front setback", "Front yard setback", "Setback (front)"],
    "side_setback_ft": ["Side setback", "Side yard setback", "Setback (side)"],
    "rear_setback_ft": ["Rear setback", "Rear yard setback", "Setback (rear)"],
    "height_ft": ["Building height", "Height of addition", "Addition height"],
    "deck_height_in": ["Deck height", "Deck height above grade", "Walking surface height"],
    "guard_height_in": ["Guard height", "Guardrail height", "Railing height"],
    "guard_opening_in": ["Guard opening", "Baluster spacing", "Max opening in guard"],
    "stair_riser_in": ["Riser height", "Stair riser", "Max riser"],
    "stair_tread_in": ["Tread depth", "Stair tread", "Min tread"],
    "stair_riser_count": ["Number of risers", "Riser count", "Risers"],
    "handrail": ["Handrail", "Handrail provided", "Stair handrail"],
    "joist_spacing_in": ["Joist spacing", "Joists at", "Joist spacing (o.c.)"],
    "footing_depth_in": ["Footing depth", "Depth of footings", "Footing depth below grade"],
    "ledger_fastener": ["Ledger attachment", "Ledger fastener", "Ledger"],
    "ceiling_height_in": ["Ceiling height", "Finished ceiling height", "Ceiling"],
    "new_bedrooms": ["New bedrooms", "Bedrooms added", "Number of new bedrooms"],
    "egress_window": ["Egress window", "Emergency escape window", "Escape window"],
    "smoke_alarm": ["Smoke alarm", "Smoke detector", "Hardwired smoke alarm"],
    "stories": ["Stories", "Number of stories", "Floors"],
    "foundation_type": ["Foundation", "Foundation type", "Foundation system"],
}
UNUSUAL = {
    "parcel_id": "Assessor lot no.",
    "side_setback_ft": "Distance to side lot line",
    "guard_opening_in": "Gap between pickets",
    "footing_depth_in": "Footings go down",
    "valuation_usd": "Job cost",
}
COMMON = ["project_type", "parcel_id", "owner_signature", "contractor", "valuation_usd", "zoning_district",
          "lot_area_sqft", "existing_footprint_sqft", "new_area_sqft", "front_setback_ft", "side_setback_ft",
          "rear_setback_ft"]
DECK = ["deck_height_in", "guard_height_in", "guard_opening_in", "stair_riser_in", "stair_tread_in",
        "stair_riser_count", "handrail", "joist_spacing_in", "footing_depth_in", "ledger_fastener"]
ADDITION = ["height_ft", "ceiling_height_in", "new_bedrooms", "egress_window", "smoke_alarm", "stories",
            "foundation_type"]
NAMES = ["Jordan Vale", "Priya Nandakumar", "Sam Okafor", "Lee Marchetti", "Alex Brandt", "Rosa Delgado",
         "Kenji Ward", "Morgan Pike", "Dana Ilves", "Chris Abara"]
STREETS = ["Larkspur", "Thistle", "Quarry", "Orchard", "Millrace", "Fernbank", "Copper", "Wren"]
WORDS = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six", 7: "seven", 8: "eight"}
OPS = {">": lambda a, b: a > b, ">=": lambda a, b: a >= b, "<": lambda a, b: a < b,
       "<=": lambda a, b: a <= b, "==": lambda a, b: a == b}


# ---------- answer key logic (independent of checker.py) ----------

def _inner_truth(check: dict, f: dict) -> str:
    t = check["type"]
    if t == "is_true":
        return "pass" if f[check["field"]] is True else "fail"
    if t == "pattern":
        import re
        return "pass" if re.fullmatch(check["regex"], str(f[check["field"]])) else "fail"
    if t == "in_set":
        return "pass" if f[check["field"]] in check["values"] else "fail"
    if t == "min":
        return "pass" if f[check["field"]] >= check["limit"] else "fail"
    if t == "max":
        return "pass" if f[check["field"]] <= check["limit"] else "fail"
    if t == "min_by_district":
        limit = check["limits"].get(f[check["district_field"]])
        if limit is None:
            return "undefined"
        return "pass" if f[check["field"]] >= limit else "fail"
    if t == "ratio_max":
        total = sum(f[x] for x in check["fields"])
        return "pass" if total <= check["limit"] * f[check["denominator"]] else "fail"
    raise ValueError(t)


def truth_status(rule: dict, f: dict) -> str:
    """What the rule says about the true values: pass, fail or undefined (no limit for the district)."""
    check = rule["check"]
    if check["type"] == "conditional":
        w = check["when"]
        if not OPS[w["op"]](f[w["field"]], w["value"]):
            return "pass"
        return _inner_truth(check["then"], f)
    return _inner_truth(check, f)


def expected_status(rule: dict, f: dict, status: dict) -> str:
    """What an ideal reviewer would say from the text: needs_human whenever the text is unclear."""
    check = rule["check"]
    if check["type"] == "conditional":
        w = check["when"]
        if status.get(w["field"], "missing") in UNCLEAR:
            return "needs_human"
        if not OPS[w["op"]](f[w["field"]], w["value"]):
            return "pass"
        need = rule_fields(check["then"])
    else:
        need = rule_fields(check)
    if any(status.get(x, "missing") in UNCLEAR for x in need):
        return "needs_human"
    t = truth_status(rule, f)
    return "needs_human" if t == "undefined" else t


# ---------- value sampling ----------

def _half(rng, lo, hi):
    return rng.randint(int(lo * 2), int(hi * 2)) / 2


def _quarter(rng, lo, hi):
    return rng.randint(int(lo * 4), int(hi * 4)) / 4


def _base_values(rng, ptype):
    district = rng.choice(["R1", "R2", "R3"])
    front = {"R1": 25, "R2": 20, "R3": 15}[district]
    side = {"R1": 8, "R2": 6, "R3": 5}[district]
    rear = {"R1": 20, "R2": 15, "R3": 10}[district]
    lot = rng.randint(100, 240) * 50
    existing = round(lot * rng.uniform(0.15, 0.26) / 10) * 10
    room = int(lot * 0.4) - existing
    new = rng.randint(120, min(480, room)) if ptype == "deck" else rng.randint(200, min(850, room))
    f = {
        "project_type": ptype,
        "parcel_id": f"LH-{rng.randint(1000, 9999)}-{rng.randint(100, 999)}",
        "owner_signature": True,
        "contractor": rng.choice([f"LHC-{rng.randint(10000, 99999)}", "owner-builder"]),
        "valuation_usd": rng.randint(60, 2400) * 50,
        "zoning_district": district,
        "lot_area_sqft": lot,
        "existing_footprint_sqft": existing,
        "new_area_sqft": new,
        "front_setback_ft": front + _half(rng, 1, 15),
        "side_setback_ft": side + _half(rng, 0.5, 8),
        "rear_setback_ft": rear + _half(rng, 1, 15),
    }
    if ptype == "deck":
        count = rng.randint(2, 8)
        f.update({
            "deck_height_in": rng.choice([rng.randint(12, 24), rng.randint(25, 60), rng.randint(25, 60)]),
            "guard_height_in": rng.randint(38, 42),
            "guard_opening_in": _quarter(rng, 3, 3.5),
            "stair_riser_in": _quarter(rng, 6, 7.5),
            "stair_tread_in": _half(rng, 10.5, 12),
            "stair_riser_count": count,
            "handrail": True if count >= 4 else rng.random() < 0.5,
            "joist_spacing_in": rng.choice([12, 16]),
            "footing_depth_in": rng.randint(30, 48),
            "ledger_fastener": rng.choice(["bolts", "lag screws", "freestanding"]),
        })
    else:
        beds = rng.choice([0, 0, 1, 1, 2, 3])
        f.update({
            "height_ft": _half(rng, 12, 28),
            "ceiling_height_in": rng.randint(84, 108),
            "new_bedrooms": beds,
            "egress_window": True if beds else rng.random() < 0.5,
            "smoke_alarm": True,
            "stories": rng.choice([1, 1, 2]),
            "foundation_type": rng.choice(["slab", "crawlspace", "basement"]),
        })
    return f


def _violate(rng, rid, f):
    """Change the true values so the rule fails."""
    lim = {"R1": (25, 8, 20), "R2": (20, 6, 15), "R3": (15, 5, 10)}.get(f["zoning_district"])
    if lim is None and rid in ("R06", "R07", "R08"):
        return
    if rid == "R01":
        f["owner_signature"] = False
    elif rid == "R02":
        f["parcel_id"] = rng.choice([f"LH-{rng.randint(100, 999)}-{rng.randint(10, 99)}",
                                     f"{rng.randint(1000, 9999)}-{rng.randint(100, 999)}"])
    elif rid == "R03":
        f["contractor"] = rng.choice([f"LHC-{rng.randint(100, 999)}", "pending"])
    elif rid == "R04":
        f["valuation_usd"] = 0
    elif rid == "R05":
        f["zoning_district"] = "C1"
    elif rid == "R06":
        f["front_setback_ft"] = lim[0] - _half(rng, 0.5, 6)
    elif rid == "R07":
        f["side_setback_ft"] = lim[1] - _half(rng, 0.5, 3)
    elif rid == "R08":
        f["rear_setback_ft"] = lim[2] - _half(rng, 0.5, 6)
    elif rid == "R09":
        room = int(f["lot_area_sqft"] * 0.4) - f["existing_footprint_sqft"]
        f["new_area_sqft"] = room + rng.randint(1, 400)
    elif rid == "R10":
        f["height_ft"] = _half(rng, 30.5, 36)
    elif rid == "R11":
        f["new_area_sqft"] = rng.randint(501, 700)
    elif rid == "R12":
        f["deck_height_in"] = rng.randint(25, 60)
        f["guard_height_in"] = rng.randint(30, 37)
    elif rid == "R13":
        f["deck_height_in"] = rng.randint(25, 60)
        f["guard_opening_in"] = _quarter(rng, 3.75, 6)
    elif rid == "R14":
        f["stair_riser_in"] = _quarter(rng, 7.75, 9)
    elif rid == "R15":
        f["stair_tread_in"] = _quarter(rng, 9, 10.25)
    elif rid == "R16":
        f["stair_riser_count"] = rng.randint(4, 8)
        f["handrail"] = False
    elif rid == "R17":
        f["joist_spacing_in"] = rng.choice([19.2, 24])
    elif rid == "R18":
        f["footing_depth_in"] = rng.randint(18, 29)
    elif rid == "R19":
        f["ledger_fastener"] = "nails"
    elif rid == "R20":
        f["new_area_sqft"] = rng.randint(901, 1200)
    elif rid == "R21":
        f["ceiling_height_in"] = rng.randint(76, 83)
    elif rid == "R22":
        f["new_bedrooms"] = rng.randint(1, 3)
        f["egress_window"] = False
    elif rid == "R23":
        f["smoke_alarm"] = False
    elif rid == "R24":
        f["stories"] = 3
    elif rid == "R25":
        f["foundation_type"] = "piers"


def _edge(rng, rid, f):
    """Put a value exactly on the limit (or on the condition line). Returns a tag or None."""
    lim = {"R1": (25, 8, 20), "R2": (20, 6, 15), "R3": (15, 5, 10)}.get(f["zoning_district"])
    edges = {
        "R04": ("valuation_usd", 1), "R10": ("height_ft", 30), "R11": ("new_area_sqft", 500),
        "R14": ("stair_riser_in", 7.5), "R15": ("stair_tread_in", 10.5), "R17": ("joist_spacing_in", 16),
        "R18": ("footing_depth_in", 30), "R20": ("new_area_sqft", 900), "R21": ("ceiling_height_in", 84),
        "R24": ("stories", 2),
    }
    if lim:
        edges.update({"R06": ("front_setback_ft", lim[0]), "R07": ("side_setback_ft", lim[1]),
                      "R08": ("rear_setback_ft", lim[2])})
    if rid in edges:
        field, value = edges[rid]
        if rid in ("R11", "R20") and f["existing_footprint_sqft"] + value > f["lot_area_sqft"] * 0.4:
            return None
        f[field] = value
        return f"{rid}:at_limit"
    if rid == "R12":
        f["deck_height_in"], f["guard_height_in"] = rng.choice([(24, rng.randint(20, 36)), (25, 38)])
        return f"{rid}:at_condition_line"
    if rid == "R13":
        f["deck_height_in"], f["guard_opening_in"] = rng.choice([(24, 5.0), (30, 3.5)])
        return f"{rid}:at_condition_line"
    if rid == "R16":
        f["stair_riser_count"], f["handrail"] = rng.choice([(3, False), (4, True)])
        return f"{rid}:at_condition_line"
    if rid == "R22" and f["new_bedrooms"] == 0:
        f["egress_window"] = False
        return f"{rid}:no_bedrooms_no_window"
    if rid == "R09":
        f["lot_area_sqft"] = 10000
        f["existing_footprint_sqft"] = 2000 + rng.randint(0, 10) * 100
        f["new_area_sqft"] = 4000 - f["existing_footprint_sqft"]
        return f"{rid}:at_limit"
    return None


# ---------- text rendering ----------

def _num(v) -> str:
    if isinstance(v, float) and v.is_integer():
        v = int(v)
    return f"{v:,}" if isinstance(v, int) and v >= 10000 else str(v)


def _frac(v: float) -> str:
    whole, part = int(v), v - int(v)
    names = {0.25: "1/4", 0.5: "1/2", 0.75: "3/4"}
    return f"{whole} {names[part]}" if part in names else _num(v)


def _render_value(rng, field, kind, v):
    if kind == "length_ft":
        if rng.random() < 0.08:
            return f"{_num(v * 12)} in"
        if not float(v).is_integer() and rng.random() < 0.5:
            return rng.choice([f"{int(v)} ft 6 in", f"{int(v)}'-6\""])
        return rng.choice([f"{_num(v)} ft", f"{_num(v)} feet", f"{_num(v)}'"])
    if kind == "length_in":
        r = rng.random()
        if float(v).is_integer() and v >= 24 and r < 0.12:
            ft, inch = divmod(int(v), 12)
            return rng.choice([f"{ft} ft {inch} in", f"{ft}'-{inch}\""])
        body = _frac(v) if (not float(v).is_integer() and r < 0.4) else _num(v)
        return rng.choice([f"{body} in", f"{body} inches", f"{body}\""]) if "/" not in body else \
            rng.choice([f"{body} in", f"{body} inches"])
    if kind == "area":
        return rng.choice([f"{v:,} sq ft", f"{v} sf", f"{v:,} square feet", f"{v} SF"])
    if kind == "money":
        return rng.choice([f"${v:,}", f"{v:,} USD", f"$ {v}"])
    if kind == "count":
        return WORDS[v] if v in WORDS and rng.random() < 0.2 else str(v)
    if kind == "bool":
        if field == "owner_signature":
            return rng.choice(["Signed", "Yes"]) if v else rng.choice(["Not signed", "No"])
        return rng.choice(["Yes", "Y", "Provided"]) if v else rng.choice(["No", "N", "Not provided", "None"])
    if field == "zoning_district":
        return rng.choice([v, f"{v[0]}-{v[1:]}", f"District {v}"])
    if field == "ledger_fastener":
        return {"bolts": rng.choice(["bolts", "through bolts"]), "lag screws": "lag screws",
                "nails": rng.choice(["nails", "16d nails"]),
                "freestanding": rng.choice(["freestanding", "none, freestanding deck"])}[v]
    if field == "foundation_type":
        return {"slab": rng.choice(["slab", "slab on grade"]),
                "crawlspace": rng.choice(["crawlspace", "crawl space"]),
                "basement": "basement", "piers": rng.choice(["piers", "concrete piers"])}[v]
    if field == "project_type":
        return {"deck": rng.choice(["Deck", "New deck", "Rear deck"]),
                "addition": rng.choice(["Addition", "Room addition", "Home addition"])}[v]
    return str(v)


def _garble(rng, s: str) -> str:
    swaps = {"0": "O", "1": "l", "5": "S", "8": "B"}
    spots = [i for i, ch in enumerate(s) if ch in swaps]
    if not spots:
        return s
    i = rng.choice(spots)
    return s[:i] + swaps[s[i]] + s[i + 1:]


def _typo(rng, label: str) -> str:
    words = label.split()
    i = max(range(len(words)), key=lambda j: len(words[j]))
    w = words[i]
    if len(w) < 5:
        return label
    k = rng.randint(1, len(w) - 2)
    words[i] = w[:k] + w[k + 1:]
    return " ".join(words)


def _line(fmt, label, value):
    if fmt == "form":
        return f"{label}: {value}"
    if fmt == "table":
        return f"| {label} | {value} |"
    if fmt == "scan":
        return f"{label.upper()} .... {value.upper()}"
    return f"The {label.lower()} is {value}."


def _render(rng, app_id, f, fields_in_doc, code, fmt):
    kinds = {k: v["kind"] for k, v in code["fields"].items()}
    status, label_style, lines, extra = {}, {}, [], []
    for field in fields_in_doc:
        kind = kinds[field]
        st = "clean"
        r = rng.random()
        protected = field == "project_type"
        if not protected:
            if r < 0.035:
                st = "missing"
            elif r < 0.055 and kind in ("length_ft", "length_in", "area", "money"):
                st = "approx"
            elif r < 0.075 and kind in ("length_ft", "length_in", "area"):
                st = "unitless"
            elif r < 0.095 and kind in ("length_ft", "length_in", "area", "count", "money"):
                st = "conflict"
            elif r < 0.11 and fmt == "scan" and kind in ("length_ft", "length_in", "area", "money"):
                st = "garbled"
        status[field] = st
        if st == "missing":
            continue
        s = rng.random()
        if field in UNUSUAL and s < 0.12:
            label, label_style[field] = UNUSUAL[field], "unusual"
        else:
            label = rng.choice(LABELS[field])
            label_style[field] = "standard"
            if s > 0.95:
                typo = _typo(rng, label)
                if typo != label:
                    label, label_style[field] = typo, "typo"
        v = f[field]
        if st == "unitless":
            text = _num(v)
        elif st == "conflict":
            delta = {"area": 60, "money": 500}.get(kind, 2)
            first = v + delta if v - delta < 0 else v + rng.choice([-1, 1]) * delta
            text = _render_value(rng, field, kind, first)
            extra.append(_line(fmt, f"Revised {label.lower()}", _render_value(rng, field, kind, v)))
        else:
            text = _render_value(rng, field, kind, v)
            if st == "approx":
                text = rng.choice(["about ", "approx. ", "~", "roughly "]) + text
            elif st == "garbled":
                g = _garble(rng, text)
                if g == text:
                    status[field] = "clean"
                text = g
        lines.append(_line(fmt, label, text))
    distractors = []
    if f["project_type"] == "deck" and rng.random() < 0.12:
        old = _line(fmt, "Existing deck height", f"{rng.randint(6, 20)} in")
        lines.insert(rng.randint(1, len(lines)), old + " (old deck to be removed)")
        distractors.append("existing_deck_height")
    if rng.random() < 0.1:
        lines.insert(rng.randint(1, len(lines)),
                     _line(fmt, "Existing rear setback of garage", f"{rng.randint(1, 4)} ft"))
        distractors.append("existing_garage_setback")
    lines += extra
    name = rng.choice(NAMES)
    addr = f"{rng.randint(10, 990)} {rng.choice(STREETS)} Lane, Larkspur Hollow"
    scope = {"deck": "Build a new deck at the back of the house.",
             "addition": "Build a new room addition on the side of the house."}[f["project_type"]]
    head = [
        "SYNTHETIC TEST DOCUMENT. Fictional city. Not a real application.",
        "LARKSPUR HOLLOW BUILDING DIVISION: RESIDENTIAL PERMIT APPLICATION",
        f"Application: {app_id}",
        f"Applicant: {name}",
        f"Site address: {addr}",
        f"Scope: {scope}",
        "",
    ]
    if fmt == "table":
        head += ["| Item | Entry |", "| --- | --- |"]
    if fmt == "scan":
        head = [h.upper() for h in head]
    body = "\n".join(head + lines) + "\n"
    if fmt == "prose":
        body = "\n".join(head) + "\n" + " ".join(lines) + "\n"
    return body, status, label_style, distractors


def _one(rng, i, code):
    app_id = f"LH-APP-{i:04d}"
    ptype = "deck" if rng.random() < 0.55 else "addition"
    f = _base_values(rng, ptype)
    applicable = [r for r in code["rules"] if ptype in r["applies_to"]]
    edges = []
    for r in applicable:
        if rng.random() < 0.08:
            tag = _edge(rng, r["id"], f)
            if tag:
                edges.append(tag)
    k = rng.choices([0, 1, 2, 3], weights=[40, 35, 18, 7])[0]
    weights = [2 if r["critical"] else 1 for r in applicable]
    chosen = set()
    while len(chosen) < k:
        chosen.add(rng.choices(applicable, weights=weights)[0]["id"])
    for rid in sorted(chosen):
        _violate(rng, rid, f)
    in_doc = COMMON + (DECK if ptype == "deck" else ADDITION)
    if ptype == "deck" and f["deck_height_in"] <= 24 and rng.random() < 0.5:
        in_doc = [x for x in in_doc if x not in ("guard_height_in", "guard_opening_in")]
    if ptype == "addition" and f["new_bedrooms"] == 0 and rng.random() < 0.5:
        in_doc = [x for x in in_doc if x != "egress_window"]
    fmt = rng.choices(["form", "table", "prose", "scan"], weights=[40, 25, 20, 15])[0]
    text, status, label_style, distractors = _render(rng, app_id, f, in_doc, code, fmt)
    for x in f:
        status.setdefault(x, "missing")
    violations, expected = [], {}
    for r in applicable:
        if truth_status(r, f) == "fail":
            violations.append({"rule_id": r["id"], "critical": r["critical"]})
        expected[r["id"]] = expected_status(r, f, status)
    key = {
        "app_id": app_id, "synthetic": True, "project_type": ptype, "format": fmt,
        "fields": f, "field_status": status, "label_style": label_style,
        "violations": violations, "expected": expected, "edge_cases": edges, "distractors": distractors,
        "code_version": code["version"],
    }
    return app_id, text, key


def generate(seed: int, n: int, out: Path | str, code: dict | None = None) -> list[dict]:
    """Write n applications, their answer keys and a 2:1 dev/held-out split. Returns the keys."""
    code = code or load_code()
    out = Path(out)
    (out / "applications").mkdir(parents=True, exist_ok=True)
    (out / "answer_keys").mkdir(parents=True, exist_ok=True)
    rng = random.Random(seed)
    ids = [f"LH-APP-{i:04d}" for i in range(1, n + 1)]
    order = ids[:]
    random.Random(seed + 1).shuffle(order)
    n_dev = n * 2 // 3
    split = {"seed": seed, "dev": sorted(order[:n_dev]), "heldout": sorted(order[n_dev:])}
    which = {a: "dev" for a in split["dev"]} | {a: "heldout" for a in split["heldout"]}
    keys = []
    for i in range(1, n + 1):
        app_id, text, key = _one(rng, i, code)
        key["split"] = which[app_id]
        (out / "applications" / f"{app_id}.txt").write_text(text, encoding="utf-8")
        (out / "answer_keys" / f"{app_id}.json").write_text(
            json.dumps(key, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        keys.append(key)
    (out / "split.json").write_text(json.dumps(split, indent=1) + "\n", encoding="utf-8")
    (out / "meta.json").write_text(json.dumps({
        "seed": seed, "n": n, "code_version": code["version"], "synthetic": True,
        "note": "Synthetic applications for a fictional city. Generated by permitcheck generate.",
    }, indent=1) + "\n", encoding="utf-8")
    return keys
