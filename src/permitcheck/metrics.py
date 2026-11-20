"""Eval metrics. Every rate comes with its count, and rates with sampling error get a Wilson interval."""

import math


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float] | tuple[None, None]:
    """95% Wilson score interval for k successes out of n. Returns (None, None) when n is 0."""
    if n == 0:
        return None, None
    p = k / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return max(0.0, centre - half), min(1.0, centre + half)


def rate(k: int, n: int) -> dict:
    lo, hi = wilson(k, n)
    ci = [None if x is None else round(x, 6) for x in (lo, hi)]
    return {"k": k, "n": n, "value": round(k / n, 6) if n else None, "ci95": ci, "method": "Wilson score, 95%"}


def same(a, b) -> bool:
    if isinstance(a, bool) or isinstance(b, bool):
        return a is b
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return abs(a - b) < 1e-6
    return a == b


def field_counts(key: dict, extracted: dict) -> tuple[int, int, int]:
    """(true positives, false positives, false negatives) for one application.
    A field counts as extracted at any confidence. A field the text leaves out has no true value to find."""
    tp = fp = fn = 0
    present = {f for f, s in key["field_status"].items() if s != "missing"}
    for f in set(present) | set(k for k, v in extracted.items() if v.value is not None):
        got = extracted.get(f)
        has = got is not None and got.value is not None
        if f in present and has and same(got.value, key["fields"][f]):
            tp += 1
        else:
            if has:
                fp += 1
            if f in present:
                fn += 1
    return tp, fp, fn


def prf(tp: int, fp: int, fn: int) -> dict:
    p = tp / (tp + fp) if tp + fp else None
    r = tp / (tp + fn) if tp + fn else None
    f1 = 2 * p * r / (p + r) if p and r else None
    return {"tp": tp, "fp": fp, "fn": fn, "precision": p, "recall": r, "f1": f1}
