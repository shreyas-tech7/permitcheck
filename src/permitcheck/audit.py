"""Append-only audit log. One JSON line per decision."""

import datetime as dt
import hashlib
import json
from pathlib import Path

from . import __version__


def append_audit(path, app_id, app_text, fields, results, code, extractor_name, now=None) -> None:
    """Append one line for each rule result. The log records the inputs, rule version and extractor."""
    now = now or dt.datetime.now(dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    app_sha = hashlib.sha256(app_text.encode("utf-8")).hexdigest()
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as fh:
        for r in results:
            fh.write(json.dumps({
                "time": now, "app_id": app_id, "app_sha256": app_sha, "synthetic": True,
                "rule_id": r.rule_id, "section": r.section, "critical": r.critical,
                "rule_version": code["version"], "code_sha256": code["sha256"],
                "extractor": extractor_name, "tool_version": __version__,
                "inputs": r.inputs, "status": r.status, "reason": r.reason,
            }, sort_keys=True) + "\n")
