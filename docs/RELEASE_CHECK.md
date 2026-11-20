# Release check

The checks from section 11 of the build prompt, run on 2026-11-20 on branch `claude/build-permitcheck`.

| Check | Command | Result |
| --- | --- | --- |
| Code review | manual review of the branch diff (the ponytail skill could not be installed) | see below |
| Secret scan | `gitleaks git -v .` | no leaks found in the full history |
| Dependencies | `pip-audit --path .venv/lib/python3.13/site-packages` | no known vulnerabilities. The project has no runtime dependencies. |
| Security lint | `ruff check --select S src scripts` | three findings, all fixed or justified, see below |
| Workflows | `actionlint` | clean |
| Links | `scripts/check_links.py` | no broken relative links. External links are listed as "not checked". |
| Writing rules | `tests/test_repo_quality.py` and a manual humanizer pass | see below |
| Outside check | one subagent cloned the repo to `/tmp/outside-check` and checked every Done-means item | six items pass. Item 2 passes for the rule-based extractor and is blocked for the LLM extractor, which the repo says. |

## Security lint findings

- S310 in `src/permitcheck/llm.py`: the record mode opens a URL. The constructor now refuses any endpoint that does not start with `https://`, and `test_record_endpoint_must_be_https` proves it.
- S311 twice in `src/permitcheck/generator.py`: the generator uses `random.Random` with a fixed seed. That is the point, because the synthetic data must be reproducible. Nothing here needs secure randomness.

## Code review

The ponytail and humanizer skills could not be installed in this session (see `BLOCKERS.md`), so the review and the writing pass were manual.

- Read every module against the brief. The model never decides: `check_application` in `src/permitcheck/checker.py` only reads values and confidences.
- Checked that every path that cannot decide returns needs_human, including an unknown district, a zero lot area, a wrong type and an unclear project type.
- Checked that no test, answer key or held-out file changed after the held-out run. `permitcheck eval --split both --check` matches the committed results.
- Fixed during the review: a pattern rule's fail reason did not say why it failed, and the eval printed absolute paths.

## Writing pass

Read `README.md` and every file in `docs/` for passive voice, filler and long sentences. The repo quality test checks for em dashes, dashes used as punctuation, semicolons in prose and the banned words. Every fact, number, name and code block stayed the same.

## Outside check

A subagent that did not write the code cloned commit ce7a5ef to `/tmp/outside-check`, ran `./init.sh` and checked each Done-means item with its own commands. It edited nothing.

- Item 1, rule tests: pass. All 25 rules have pass, fail and edge cases, and a coverage test guards it.
- Item 2, zero false approves: pass for the rule-based extractor (0 of 63 critical violations, 0 of 47 applications on a fresh run). Blocked for the LLM extractor. The checker confirmed that `BLOCKERS.md` and the README say so and that no LLM numbers appear anywhere.
- Item 3, citations: pass. It noted that citation validity is close to true by construction, because `letter_md` raises before it writes a bad citation. The eval still reads every citation back to prove it.
- Item 4, README table: pass. It checked the 0 of 63 upper bound of 5.7% by hand.
- Item 5, disclaimers: pass for every command, every help page and every output file.
- Item 6, offline tests: pass with the proxy variables unset.
- Item 7, quality bar: pass, except the expected placeholder in this file, which this section replaces.
- README numbers: it spot-checked dev, held-out, second-seed and timing numbers against `results/`. All matched.

Fixed after the outside check:

- `scripts/assert_zero_false_approve.py` crashed with no argument. It now defaults to `results/eval_heldout_rule.json`.
- `test_rule_fail` had an assertion that could never fail. It now checks the section and that the reason is a real fail reason.
- `permitcheck check` on a missing file printed a traceback. It now prints a clear error and exits with code 2, with a test.
- The README glossary said the held-out set was scored once at the end, which a reader cannot verify. It now says the tool was frozen first and points to `DECISIONS.md`.

Logged, not changed:

- CI skips pushes that change only docs, as the build prompt asks. A push that changes only `docs/RELEASE_CHECK.md` will not run CI, although a test reads that file. Every code push runs that test.
- The Archistar claim in Related work comes from Archistar's own site, as the brief cites it. The README says "says that".

Also found during the release check, before the outside check: a garbled digit in an upper-case scan line could drop out and leave a smaller clean number. It is fixed and logged in `BLOCKERS.md`.
