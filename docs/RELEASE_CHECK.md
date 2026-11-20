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
| Outside check | one subagent cloned the repo to `/tmp/outside-check` and checked every Done-means item | OUTSIDE_CHECK_PENDING |

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

OUTSIDE_CHECK_PENDING
