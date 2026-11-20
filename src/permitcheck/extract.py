"""Rule-based extractor: finds each field by its label, parses the value, and scores confidence.

It only reads. It never decides pass or fail. Confidence scores:
0.95 exact label and a clean value, 0.85 near-miss label and a clean value,
0.5 approximate value, 0.4 a length or area with no unit, 0.3 two different values,
0.2 a garbled number (no value is returned).
"""

import difflib
import re
from dataclasses import dataclass

from .codefile import load_code

NAME = "rule-v1"

ALIASES = {
    "project_type": ["project type", "type of work", "work type"],
    "parcel_id": ["parcel id", "parcel number", "apn", "parcel"],
    "owner_signature": ["owner signature", "signed by owner", "owner signed"],
    "contractor": ["contractor license", "contractor", "builder"],
    "valuation_usd": ["valuation", "value of work", "estimated cost", "project valuation"],
    "zoning_district": ["zoning district", "zoning", "zone"],
    "lot_area_sqft": ["lot area", "lot size", "parcel area"],
    "existing_footprint_sqft": ["existing footprint", "existing building footprint", "existing coverage"],
    "new_area_sqft": ["proposed area", "new floor area", "area of new work", "deck area", "addition area"],
    "front_setback_ft": ["front setback", "front yard setback", "setback (front)"],
    "side_setback_ft": ["side setback", "side yard setback", "setback (side)"],
    "rear_setback_ft": ["rear setback", "rear yard setback", "setback (rear)"],
    "height_ft": ["building height", "height of addition", "addition height"],
    "deck_height_in": ["deck height", "deck height above grade", "walking surface height"],
    "guard_height_in": ["guard height", "guardrail height", "railing height"],
    "guard_opening_in": ["guard opening", "baluster spacing", "max opening in guard"],
    "stair_riser_in": ["riser height", "stair riser", "max riser"],
    "stair_tread_in": ["tread depth", "stair tread", "min tread"],
    "stair_riser_count": ["number of risers", "riser count", "risers"],
    "handrail": ["handrail", "handrail provided", "stair handrail"],
    "joist_spacing_in": ["joist spacing", "joists at", "joist spacing (o.c.)"],
    "footing_depth_in": ["footing depth", "depth of footings", "footing depth below grade"],
    "ledger_fastener": ["ledger attachment", "ledger fastener", "ledger"],
    "ceiling_height_in": ["ceiling height", "finished ceiling height", "ceiling"],
    "new_bedrooms": ["new bedrooms", "bedrooms added", "number of new bedrooms"],
    "egress_window": ["egress window", "emergency escape window", "escape window"],
    "smoke_alarm": ["smoke alarm", "smoke detector", "hardwired smoke alarm"],
    "stories": ["stories", "number of stories", "floors"],
    "foundation_type": ["foundation", "foundation type", "foundation system"],
}

EXACT, NEAR = 0.95, 0.85
APPROX, UNITLESS, CONFLICT, GARBLED = 0.5, 0.4, 0.3, 0.2
NOT_NEW = re.compile(r"\b(existing|old|previous|current|neighbor'?s?)\b[^:|]{0,20}$", re.I)
APPROX_RE = re.compile(r"^(about|approx\.?|approximately|around|roughly|~|\+/-|circa)\s*", re.I)
GARBLE_RE = re.compile(r"\d[OolSB]|[OolSB]\d|\d,[OolSB]|[OolSB],\d")
NUM = r"(?<![\w.,])(\d[\d,]*(?:\.\d+)?)"
FT = r"(?:ft|feet|foot|')"
IN = r"(?:in|inches|inch|\")"
WORDS = {"zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8,
         "nine": 9, "ten": 10}


@dataclass
class Field:
    value: object
    confidence: float
    source: str


def _n(s: str) -> float:
    v = float(s.replace(",", ""))
    return int(v) if v.is_integer() else v


def _length(text: str, unit: str):
    """Return (value in the field's unit, quality). Quality: clean, unitless or None."""
    t = text.lower()
    m = re.search(NUM + r"\s*" + FT + r"\s*-?\s*(\d+(?:\.\d+)?)\s*" + IN + r"(?![a-z])", t)
    if m:
        ft, inch = float(m.group(1).replace(",", "")), float(m.group(2))
        return (_n(str(ft + inch / 12)) if unit == "ft" else _n(str(ft * 12 + inch))), "clean"
    m = re.search(NUM + r"\s+(1/4|1/2|3/4)\s*" + IN + r"(?![a-z])", t)
    if m:
        v = float(m.group(1)) + {"1/4": 0.25, "1/2": 0.5, "3/4": 0.75}[m.group(2)]
        return (_n(str(v / 12)) if unit == "ft" else _n(str(v))), "clean"
    m = re.search(NUM + r"\s*" + FT + r"(?![a-z])", t)
    if m:
        v = float(m.group(1).replace(",", ""))
        return (_n(str(v)) if unit == "ft" else _n(str(v * 12))), "clean"
    m = re.search(NUM + r"\s*" + IN + r"(?![a-z])", t)
    if m:
        v = float(m.group(1).replace(",", ""))
        return (_n(str(round(v / 12, 6))) if unit == "ft" else _n(str(v))), "clean"
    m = re.search(NUM + r"(?![\w])", t)
    if m:
        return _n(m.group(1)), "unitless"
    return None, None


def _area(text: str):
    t = text.lower()
    m = re.search(NUM + r"\s*(?:sq\.?\s*ft|sf|square\s+feet|sqft|ft2|ft²)(?![a-z])", t)
    if m:
        return _n(m.group(1)), "clean"
    m = re.search(NUM + r"(?![\w])", t)
    return (_n(m.group(1)), "unitless") if m else (None, None)


def _money(text: str):
    t = text.lower()
    m = re.search(r"\$\s*(\d[\d,]*(?:\.\d+)?)", t) or re.search(NUM + r"\s*(?:usd|dollars)\b", t)
    if m:
        return _n(m.group(1)), "clean"
    m = re.search(NUM + r"(?![\w])", t)
    return (_n(m.group(1)), "unitless") if m else (None, None)


def _count(text: str):
    t = text.lower()
    m = re.search(NUM + r"(?![\w.])", t)
    if m and "." not in m.group(1) and "," not in m.group(1):
        return int(m.group(1)), "clean"
    m = re.match(r"\s*(" + "|".join(WORDS) + r")\b", t)
    return (WORDS[m.group(1)], "clean") if m else (None, None)


def _bool(text: str):
    t = text.strip().lower()
    if re.match(r"(no|n|none|not provided|not signed|false|missing)\b", t):
        return False, "clean"
    if re.match(r"(yes|y|provided|signed|true|included|x)\b", t):
        return True, "clean"
    return None, None


def _choice(field: str, text: str):
    t = text.lower()
    if field == "project_type":
        hits = [v for v in ("deck", "addition") if re.search(r"\b" + v + r"\b", t)]
    elif field == "zoning_district":
        hits = sorted({m.group(1).upper() + m.group(2) for m in re.finditer(r"\b([rc])-?([0-9])\b", t)})
    elif field == "ledger_fastener":
        hits = [v for v, p in (("freestanding", r"free\s*-?standing"), ("lag screws", r"\blag\b"),
                               ("bolts", r"\bbolt"), ("nails", r"\bnail")) if re.search(p, t)]
        if "freestanding" in hits:
            hits = ["freestanding"]
    else:  # foundation_type
        hits = [v for v, p in (("slab", r"\bslab\b"), ("crawlspace", r"\bcrawl\s*space\b"),
                               ("basement", r"\bbasement\b"), ("piers", r"\bpiers?\b")) if re.search(p, t)]
    return (hits[0], "clean") if len(hits) == 1 else (None, None)


def _text(field: str, text: str):
    t = text.strip()
    if field == "contractor" and re.match(r"owner[\s-]*builder\b", t, re.I):
        return "owner-builder", "clean"
    m = re.match(r"[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*", t)
    if not m:
        return None, None
    tok = m.group(0)
    return (tok.upper() if re.search(r"\d", tok) else tok.lower()), "clean"


class RuleExtractor:
    name = NAME

    def __init__(self, code: dict | None = None):
        self.code = code or load_code()
        self.kinds = {k: v["kind"] for k, v in self.code["fields"].items()}
        self.patterns = []
        for field, aliases in ALIASES.items():
            for a in aliases:
                body = r"\s+".join(re.escape(w) for w in a.split())
                self.patterns.append((field, a, re.compile(r"(?<![\w-])" + body + r"(?![\w])", re.I)))
        self.flat = [(f, a) for f, al in ALIASES.items() for a in al]

    def _parse(self, field: str, raw: str):
        kind = self.kinds[field]
        text = raw.strip().strip("|").strip()
        approx = bool(APPROX_RE.match(text))
        text = APPROX_RE.sub("", text)
        if kind in ("length_ft", "length_in", "area", "money", "count") and GARBLE_RE.search(text[:20]):
            return None, "garbled"
        if kind == "length_ft":
            v, q = _length(text, "ft")
        elif kind == "length_in":
            v, q = _length(text, "in")
        elif kind == "area":
            v, q = _area(text)
        elif kind == "money":
            v, q = _money(text)
        elif kind == "count":
            v, q = _count(text)
        elif kind == "bool":
            v, q = _bool(text)
        elif kind == "choice":
            v, q = _choice(field, text)
        else:
            v, q = _text(field, text)
        if v is not None and approx:
            q = "approx"
        return v, q

    @staticmethod
    def _segments(text: str):
        for line in text.splitlines():
            line = line.strip()
            if not line or re.fullmatch(r"\|[\s|:-]*\|", line):
                continue
            if line.startswith("|"):
                cells = [c.strip() for c in line.strip("|").split("|")]
                line = f"{cells[0]}: {' '.join(cells[1:])}" if len(cells) > 1 else cells[0]
            line = re.sub(r"\s\.{2,}\s", ": ", line)
            for s in re.split(r"\.\s+(?=The\s)", line):
                s = re.sub(r"(?<=[\w\"'])\.$", "", s.strip())
                if s:
                    yield s

    def _near_miss(self, seg: str):
        m = re.match(r"^(?:the\s+)?([a-z][a-z ().-]{2,40}?)\s*(?::|\s+is\s+)(.+)$", seg, re.I)
        if not m:
            return None
        label = re.sub(r"^(revised|corrected|updated|amended)\s+", "", m.group(1).lower().strip())
        scores = sorted(((difflib.SequenceMatcher(None, label, a).ratio(), f) for f, a in self.flat),
                        reverse=True)
        best, field = scores[0]
        runner = next((s for s, f in scores if f != field), 0)
        if best >= 0.88 and best - runner >= 0.03:
            return field, m.group(2)
        return None

    def extract(self, text: str) -> dict[str, Field]:
        cands: dict[str, list[tuple[object, float, str]]] = {}
        for seg in self._segments(text):
            hits = []
            for field, _alias, pat in self.patterns:
                for m in pat.finditer(seg):
                    hits.append((m.start(), m.end(), field))
            hits.sort(key=lambda h: (-(h[1] - h[0]), h[0]))
            kept = []
            for h in hits:
                if all(h[1] <= k[0] or h[0] >= k[1] for k in kept):
                    kept.append(h)
            kept.sort()
            found = []
            for i, (s, e, field) in enumerate(kept):
                if NOT_NEW.search(seg[:s]):
                    continue
                end = kept[i + 1][0] if i + 1 < len(kept) else len(seg)
                raw = re.sub(r"^[\s:|=.-]*(?:(?:is|will be|of|at|equals)\s+)?", "", seg[e:end])
                found.append((field, raw, EXACT))
            if not kept:
                near = self._near_miss(seg)
                if near:
                    found.append((near[0], near[1], NEAR))
            for field, raw, base in found:
                v, q = self._parse(field, raw)
                if q is None:
                    continue
                conf = {"clean": base, "approx": APPROX, "unitless": UNITLESS, "garbled": GARBLED}[q]
                cands.setdefault(field, []).append((v, conf, seg))
        out = {}
        for field, items in cands.items():
            values = [v for v, _, _ in items if v is not None]
            if not values:
                out[field] = Field(None, GARBLED, items[0][2])
                continue
            distinct = []
            for v in values:
                if not any(_same(v, d) for d in distinct):
                    distinct.append(v)
            best = max((it for it in items if it[0] is not None), key=lambda it: it[1])
            if len(distinct) > 1:
                out[field] = Field(best[0], CONFLICT, " / ".join(it[2] for it in items))
            elif any(it[0] is None for it in items):
                out[field] = Field(best[0], min(best[1], GARBLED), best[2])
            else:
                out[field] = Field(best[0], min(it[1] for it in items), best[2])
        return out


def _same(a, b) -> bool:
    if isinstance(a, (int, float)) and isinstance(b, (int, float)) and not isinstance(a, bool):
        return abs(a - b) < 1e-6
    return a == b
