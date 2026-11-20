# Walkthrough

A tour of every file. Short sentences, one idea each.

## The idea in one paragraph

An application is a text file. The extractor reads it. It returns a value and a confidence for each field. The checker is plain Python. It decides pass, fail or needs-human for each rule. The model never decides. Unclear means needs-human. The writers turn the results into three outputs. The audit log keeps a line for every decision. The eval scores all of it against hidden answer keys.

## The package: `src/permitcheck/`

### `__init__.py`

It holds the version string. The audit log copies it into every line.

### `disclaimer.py`

It holds one sentence. The sentence says the data is synthetic, the tool gives no legal advice and the code is not for production. Every command prints it first. Every output file carries it.

### `data/city_code.json`

This is the fictional city code. The city is Larkspur Hollow. The code has a version, a list of fields and a list of rules. Each rule has an ID, a section number, a title, plain text, a check type and its parameters. Each rule also says whether it is critical and which project types it applies to. A deck and an addition share some rules and not others.

### `codefile.py`

`load_code` reads the code file. It checks the file with `validate`. It adds a sha256 of the file, so every decision can name the exact code it used. It also builds two lookups: rules by ID and rules by section. `validate` returns a list of problems. An empty list means the file is good.

### `generator.py`

`generate` writes the synthetic applications. It uses a fixed seed, so the same seed gives the same files. Each application gets values for every field. Some get a violation on purpose. Some get an edge case, a value right at the limit. Then the generator writes the text in one of four formats: a form, a table, prose or a scan with dotted leaders. It adds mess on purpose: missing fields, rounded values, values without units, two values that disagree, garbled text, typos in labels and labels the extractor does not know. It also adds lines about existing structures, to tempt the extractor into reading the wrong number.

For each application it writes a hidden answer key. The key holds the true values, the seeded violations and the status the tool should return for each rule. `truth_status` and `expected_status` work out that status. They are written apart from the checker, so a checker bug shows up as a mismatch.

### `extract.py`

`RuleExtractor` is the baseline extractor. It splits the text into segments, one per label and value. It matches each label to a field. An exact label scores 0.95. A close label with a typo scores 0.85. A rounded value scores 0.5, a value without a unit 0.4, two values that disagree 0.3 and garbled text 0.2. It skips lines about existing or old structures. `Field` is the small record it returns: value, confidence and source text.

### `llm.py`

`LLMExtractor` is the model version. It builds one prompt per application. In replay mode it reads a saved response from `fixtures/llm/`. In record mode it calls a free provider with a key from the environment, then saves the response. `_grounded` checks that the quote the model gave appears in the application and parses to the same value. If not, the confidence drops to 0.5 at most. That sends the rule to a person. This extractor has not run live yet.

### `checker.py`

This is where decisions happen. `check_rule` runs one rule. `_get` fetches a field. It raises a "needs a person" signal when the field is missing, below the 0.8 threshold or the wrong type. `_simple` handles each check type: yes or no, a pattern, a set of allowed values, a minimum, a maximum, a minimum by district and a coverage ratio. A conditional rule checks its condition first. If the condition is false, the rule passes as "not required". `check_application` runs every rule for the project type. If the project type itself is unclear, every rule is needs-human.

### `report.py`

`checklist_md` writes the reviewer checklist with fails first, then needs-human, then passes. Critical items come first in each group. `letter_md` writes the correction letter in plain words. Before it writes, it checks every citation with `_check_citation`. A section that is not in the code, or that belongs to another rule, raises `CitationError`. `cited_sections` reads the citations back out of a letter. `queue_items` lists the needs-human items for the review queue.

### `audit.py`

`append_audit` adds one JSON line per decision to the audit log. Each line has the time, the application's sha256, the rule, the section, the inputs and their confidences, the status, the reason, the rule version, the code sha256, the extractor name and the tool version.

### `metrics.py`

`wilson` gives a 95% Wilson score interval. `rate` packs a count, a total, a value and an interval. `field_counts` and `prf` give field precision, recall and F1.

### `evaluate.py`

`evaluate` runs the whole pipeline over a split and compares it with the answer keys. It counts field matches, violations caught, false approves, needs-human decisions and valid citations. `load_split` reads the dev or held-out list from `data/split.json`.

### `readme.py`

`render` writes the README tables from the results files. With `check` set, it only compares and fails on a difference. Nobody types the numbers.

### `cli.py`

`main` is the `permitcheck` command. It prints the disclaimer, then runs one of four steps: `generate`, `check`, `eval` or `readme`.

## Data and outputs

- `data/applications/`: the synthetic application texts.
- `data/answer_keys/`: one hidden answer key per application.
- `data/split.json`: the dev and held-out lists, fixed before any tuning.
- `data/meta.json`: the seed and the code version.
- `results/`: the eval results for dev, held-out and a second seed, plus timing.
- `examples/`: every output for two applications, with their terminal transcripts.
- `fixtures/llm/`: saved model responses for replay mode. It is empty because no live run happened.

## Tests: `tests/`

- `conftest.py`: blocks any network call to a host that is not local.
- `test_network_guard.py`: proves the guard works.
- `test_code_file.py`: the code file loads and validates, every rule field is declared, and the schema check catches broken files.
- `test_generator.py`: the same seed gives the same bytes, the committed data matches the generator, and the split has no overlap.
- `test_extract.py`: each format, label style and mess type reads as expected.
- `test_rules.py`: pass, fail and edge cases for every rule. A coverage test fails if a rule has none.
- `test_needs_human.py`: a missing or low-confidence field never gives a pass.
- `test_outputs.py`: the checklist and the queue.
- `test_letter.py`: every citation is real, and a fake section raises an error.
- `test_audit.py`: one line per decision with the version, inputs and extractor, and the log only appends.
- `test_metrics.py`: Wilson intervals and F1 against known values.
- `test_llm.py`: replay mode, bad JSON and the grounding check.
- `test_disclaimers.py`: the README, every command and every output carry the disclaimer.
- `test_readme_sync.py`: the README tables match the results, and the prose holds no typed numbers.
- `test_repo_quality.py`: the repo files, the writing rules, the links and the release files.

## Scripts: `scripts/`

- `assert_zero_false_approve.py`: fails if a results file shows any false approve.
- `build_examples.sh`: rebuilds `examples/`.
- `check_features.py`: runs the steps for each feature in `feature_list.json` and compares with its flag.
- `check_links.py`: checks every relative link and anchor in the Markdown and HTML files.
- `make_demo.sh`: writes `docs/DEMO.md` from a real terminal session.
- `make_site.py`: writes `docs/index.html` from the results.
- `make_social_preview.py`: draws `docs/social-preview.png` with the standard library.
- `time_eval.py`: times the pipeline and writes `results/timing.json`.

## Project files

- `init.sh`: makes the virtual environment, installs, lints and runs every test.
- `feature_list.json`: the features, each with a check command and a pass flag.
- `PROGRESS.md`, `HANDOVER.md`: where the build stands and how to resume it.
- `DECISIONS.md`: each choice and its reason.
- `BLOCKERS.md`: what could not be done and what was done instead.
- `.github/workflows/ci.yml`: the fast CI job. `record.yml` runs the live model by hand only.
