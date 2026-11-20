# permitcheck Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans inline, one feature at a time. The build prompt bans subagent-driven development for the whole build. Steps use checkbox syntax.

**Goal:** A `permitcheck` command that reads a synthetic permit application, extracts fields with confidence scores, checks them against a fictional city code in plain code, and writes a checklist, a correction letter, a review queue and an audit log.

**Architecture:** One small Python package. The extractor (rule-based, or an LLM in replay or record mode) only returns field values and confidences. The checker is plain code that reads the rule file and returns pass, fail or needs_human with the section. Writers and the eval harness only read checker results.

**Tech Stack:** Python 3.11+, standard library only, pytest and ruff for dev.

**Spec:** `docs/build/BUILD_PROMPT.md`, Part 2.

## Global Constraints

- Python 3.11 or newer, the standard library and pytest. No other runtime dependency.
- The model never decides pass or fail. It only extracts.
- When unsure, the tool says needs-human. It never guesses a pass.
- 300 applications: 200 dev and 100 held out, split before tuning. Report both.
- False approve: an application with at least one seeded critical violation that the tool marks as pass on that rule.
- Every output says: synthetic data, no legal advice, not for production.
- The city is fictional. No text from a real code.
- Tests run offline.

## Review Focus

1. A value given in another unit (a setback in inches, a guard in feet) must convert, never be read as the default unit. Test: `test_extract.py::test_setback_given_in_inches_converts`.
2. A number with no unit must not count as a confident value. Test: `test_extract.py::test_unitless_value_is_low_confidence`.
3. A line about an existing or removed structure must not fill the new field. Test: `test_extract.py::test_existing_structure_line_is_ignored`.
4. Two different values for one field must not pick one quietly. Test: `test_extract.py::test_conflicting_values_are_low_confidence`.
5. A garbled number from a scan (for example `2O5`) must not parse as a smaller number. Test: `test_extract.py::test_garbled_number_is_not_read`.

---

### Task 1: Initializer and code file (F01, F02)

**Files:** `init.sh`, `pyproject.toml`, `src/permitcheck/codefile.py`, `src/permitcheck/data/city_code.json`, `tests/conftest.py`, `tests/test_network_guard.py`, `tests/test_code_file.py`

**Interfaces:** Produces `load_code(path=None) -> dict` (adds `sha256`, `by_id`, `by_section`), `validate(code) -> list[str]`, `rule_fields(check) -> list[str]`.

- [ ] Write the schema tests with one mutation per error type. Run them. Write `validate`. Run `./init.sh`. Commit.

### Task 2: Generator and split (F03, F04)

**Files:** `src/permitcheck/generator.py`, `tests/test_generator.py`, `data/`

**Interfaces:** Produces `generate(seed: int, n: int, out: Path) -> list[dict]` (answer keys), `expected_status(rule, fields, statuses, project_type) -> str`, and the files `data/applications/LH-APP-0001.txt`, `data/answer_keys/LH-APP-0001.json`, `data/split.json`.

- [ ] Tests: same seed gives the same bytes. 300 files. Split is 200 and 100 with no overlap. Every key lists true values, the text status of each field, and violations with a critical flag. At least 30 held-out critical violations.
- [ ] The answer key logic is written in the generator, separate from the checker, so a checker bug shows up in the eval.

### Task 3: Rule-based extractor (F05)

**Files:** `src/permitcheck/extract.py`, `tests/test_extract.py`

**Interfaces:** Produces `Field(value, confidence, source)` and `RuleExtractor().extract(text) -> dict[str, Field]`. Confidence: 0.95 clean exact label, 0.85 near-miss label, 0.5 approximate, 0.4 no unit, 0.3 conflict, 0.2 garbled.

### Task 4: Checker, one rule group per feature (F06 to F09)

**Files:** `src/permitcheck/checker.py`, `tests/test_rules.py`

**Interfaces:** Produces `CONFIDENCE_THRESHOLD = 0.8`, `Result(rule_id, section, status, reason, inputs)` and `check_application(fields, code) -> list[Result]`.

- [ ] A table in the test names pass, fail and edge inputs for each rule. A coverage test fails if any rule lacks one of the three.

### Task 5: Needs-human path (F10)

- [ ] Tests: missing field, field at 0.79, missing project type, missing district, missing condition field. Each gives needs_human with a reason.

### Task 6: Outputs (F11, F12)

**Files:** `src/permitcheck/report.py`, `tests/test_outputs.py`, `tests/test_letter.py`

**Interfaces:** Produces `checklist_md(app_id, results, code) -> str`, `letter_md(app_id, results, code) -> str` (raises `CitationError` on a section that is not in the code file or not in the results), `queue_items(app_id, results) -> list[dict]`, `cited_sections(letter) -> list[tuple[str, str]]`.

### Task 7: Audit log (F13)

**Files:** `src/permitcheck/audit.py`, `tests/test_audit.py`

**Interfaces:** Produces `append_audit(path, app_id, app_text, fields, results, code, extractor_name, now=None)`. One JSON line per decision with the rule version, code sha256 and extractor.

### Task 8: Eval and metrics (F14, F15)

**Files:** `src/permitcheck/metrics.py`, `src/permitcheck/evaluate.py`, `src/permitcheck/cli.py`, `tests/test_metrics.py`, `results/`

**Interfaces:** Produces `wilson(k, n, z=1.96) -> tuple[float, float]` and `evaluate(split, extractor) -> dict` written to `results/eval_<split>_<extractor>.json`.

- [ ] Tune only on dev. Run held-out once at the end of tuning. If a false approve shows up on held-out, fix the code and report both runs.

### Task 9: LLM extractor (F16, F17)

**Files:** `src/permitcheck/llm.py`, `tests/test_llm.py`, `fixtures/llm/`

- [ ] Replay reads fixtures keyed by prompt hash. Record calls a free OpenAI-compatible endpoint with a key from the environment. A grounding check caps confidence when the model's quote is not in the text or does not parse to its value.
- [ ] Probe the hosts. If record mode is blocked, log it and keep fixtures out of the README numbers.

### Task 10: README, study kit, release check, hand-off (F18 to F22)

- [ ] `permitcheck readme` writes the tables. A test compares them with the results files.
- [ ] CI, social preview, static results page, DEMO.md, WALKTHROUGH, INTERVIEW_QA, HUMAN_STEPS, COWORK_PROMPT, RELEASE_CHECK.

## Assumptions

- The city is Larkspur Hollow, and its code is the Larkspur Hollow Residential Code (LHRC), version 2026.1.
- A conditional rule whose condition is false passes as "not required".
- A rule that does not apply to the project type is not checked and is not counted.
- Field F1 counts a field as extracted at any confidence, so it measures reading, not deciding.
