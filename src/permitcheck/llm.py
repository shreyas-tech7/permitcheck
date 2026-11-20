"""LLM extractor with replay and record modes.

The model only extracts. It returns a value, a quote and a confidence for each field. Code then
checks that the quote appears in the application and that the quote parses to the same value.
If not, the confidence is capped at 0.5, so the checker sends the item to a person.

Replay reads saved responses from fixtures/llm/<model>/<prompt sha256>.json. Record calls a free
OpenAI-compatible endpoint with a key from the environment and saves the response. Send only
synthetic text: free tiers can use prompts for training.
"""

import hashlib
import json
import os
import re
import time
import urllib.error
import urllib.request
from pathlib import Path

from .codefile import load_code
from .extract import Field, RuleExtractor

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "fixtures" / "llm"
DEFAULT_MODEL = "llama-3.1-8b-instant"
ENDPOINT = "https://api.groq.com/openai/v1/chat/completions"
GROUNDED_CAP, UNGROUNDED_CAP = 0.95, 0.5

PROMPT = """You extract fields from a synthetic permit application for a fictional city.
Do not judge whether the application passes. Only report what the text says.
Return one JSON object:
{{"fields": {{"<name>": {{"value": ..., "quote": "<exact text you copied>", "confidence": 0.0-1.0}}}}}}.
Use null for a field the text does not state. Copy the quote word for word from the application,
including the label and the unit. Convert lengths to the unit in the field name (_ft feet, _in inches).

Fields:
{fields}

Application:
<<<
{text}
>>>"""


class ReplayMissing(LookupError):
    pass


class RecordBlocked(RuntimeError):
    pass


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip().lower()


class LLMExtractor:
    def __init__(self, code: dict | None = None, mode: str = "replay", model: str = DEFAULT_MODEL,
                 fixtures: Path | str = FIXTURES, endpoint: str = ENDPOINT):
        if mode not in ("replay", "record"):
            raise ValueError(mode)
        if not endpoint.startswith("https://"):
            raise ValueError("the provider endpoint must use https")
        self.code = code or load_code()
        self.mode, self.model, self.endpoint = mode, model, endpoint
        self.fixtures = Path(fixtures)
        self.name = f"llm-{mode}-v1"
        self.rule = RuleExtractor(self.code)

    def prompt(self, text: str) -> str:
        fields = "\n".join(f"- {n} ({s['kind']}" + (f": one of {', '.join(s['values'])}" if "values" in s else "")
                           + ")" for n, s in self.code["fields"].items())
        return PROMPT.format(fields=fields, text=text)

    def fixture_path(self, prompt: str) -> Path:
        sha = hashlib.sha256(f"{self.model}\n{prompt}".encode()).hexdigest()
        return self.fixtures / self.model / f"{sha}.json"

    def _record(self, prompt: str) -> str:
        key = os.environ.get("GROQ_API_KEY")
        if not key:
            raise RecordBlocked("GROQ_API_KEY is not set. Record mode needs a free-tier key.")
        body = json.dumps({"model": self.model, "temperature": 0, "response_format": {"type": "json_object"},
                           "messages": [{"role": "user", "content": prompt}]}).encode()
        wait = 2.0
        for _ in range(5):
            req = urllib.request.Request(self.endpoint, data=body, method="POST", headers={  # noqa: S310 (https only)
                "Authorization": f"Bearer {key}", "Content-Type": "application/json"})
            try:
                with urllib.request.urlopen(req, timeout=30) as resp:  # noqa: S310 (fixed https endpoint)
                    return json.loads(resp.read())["choices"][0]["message"]["content"]
            except urllib.error.HTTPError as e:
                if e.code != 429:
                    raise RecordBlocked(f"provider answered {e.code}") from e
                time.sleep(wait)
                wait *= 2
            except urllib.error.URLError as e:
                raise RecordBlocked(f"cannot reach {self.endpoint}: {e.reason}") from e
        raise RecordBlocked("still rate limited after 5 tries")

    def response(self, text: str) -> str:
        prompt = self.prompt(text)
        path = self.fixture_path(prompt)
        if self.mode == "replay":
            if not path.exists():
                raise ReplayMissing(f"no recorded response at {path}")
            return json.loads(path.read_text())["response"]
        raw = self._record(prompt)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"model": self.model, "recorded": True, "response": raw,
                                    "note": "Recorded from a free provider on synthetic text."}, indent=1) + "\n")
        return raw

    def extract(self, text: str) -> dict[str, Field]:
        return self.parse(self.response(text), text)

    def _grounded(self, field: str, value, quote: str, text: str) -> bool:
        if not quote or _norm(quote) not in _norm(text):
            return False
        got = self.rule.extract(quote).get(field)
        if got is None or got.value is None:
            v, q = self.rule._parse(field, quote)
            got = Field(v, 0, "") if q == "clean" else None
        if got is None:
            return False
        a, b = got.value, value
        if isinstance(a, (int, float)) and not isinstance(a, bool) and isinstance(b, (int, float)):
            return abs(a - b) < 1e-6
        return str(a).lower() == str(b).lower()

    def parse(self, raw: str, text: str) -> dict[str, Field]:
        """Turn the model's JSON into fields. Bad JSON gives no fields, so every rule is needs_human."""
        s = re.sub(r"^```(?:json)?|```$", "", raw.strip(), flags=re.M).strip()
        try:
            data = json.loads(s)
            items = data["fields"]
            if not isinstance(items, dict):
                return {}
        except (ValueError, KeyError, TypeError):
            return {}
        out = {}
        for name, item in items.items():
            if name not in self.code["fields"] or not isinstance(item, dict) or item.get("value") is None:
                continue
            try:
                conf = max(0.0, min(1.0, float(item.get("confidence", 0))))
            except (TypeError, ValueError):
                conf = 0.0
            value = item["value"]
            if isinstance(value, str):
                value = value.strip()
                if name in ("project_type", "ledger_fastener", "foundation_type"):
                    value = value.lower()
                elif name == "contractor" and value.lower().startswith("owner"):
                    value = "owner-builder"
                elif name == "zoning_district":
                    value = value.upper().replace("-", "")
            quote = str(item.get("quote") or "")
            cap = GROUNDED_CAP if self._grounded(name, value, quote, text) else UNGROUNDED_CAP
            out[name] = Field(value, min(conf, cap), quote)
        return out
