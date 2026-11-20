# Project context: permitcheck

## What it is

`permitcheck` reads a synthetic permit application for a deck or an addition, checks it against a fictional city code (the Larkspur Hollow Residential Code, LHRC), and writes a reviewer checklist, a correction letter with section citations, a review queue and an audit log. The model reads. Code decides. Synthetic data only. No legal advice. Not for production.

## Status

See `PROGRESS.md` and `feature_list.json`.

## Stack

Python 3.11+, standard library only. pytest and ruff for dev.

## Commands

- `./init.sh`: create `.venv`, install, lint, run all tests offline.
- `.venv/bin/permitcheck generate --seed 20261120 --n 300 --out data`
- `.venv/bin/permitcheck check data/applications/LH-APP-0001.txt --out out`
- `.venv/bin/permitcheck eval --split heldout --extractor rule`
- `.venv/bin/permitcheck readme` (writes the README tables) and `readme --check`
- `.venv/bin/python scripts/check_features.py` runs every feature's steps.
- `$HOME/go/bin/gitleaks git --pre-commit --redact --staged --verbose` before each commit.

## Layout

- `src/permitcheck/data/city_code.json`: the fictional code, 25 rules, versioned.
- `src/permitcheck/codefile.py`: load and schema check.
- `src/permitcheck/generator.py`: seeded synthetic applications and answer keys.
- `src/permitcheck/extract.py`: rule-based extractor with confidence scores.
- `src/permitcheck/llm.py`: LLM extractor, replay and record modes.
- `src/permitcheck/checker.py`: plain-code rule checks: pass, fail, needs_human.
- `src/permitcheck/report.py`: checklist, letter, queue.
- `src/permitcheck/audit.py`: JSON Lines audit log.
- `src/permitcheck/metrics.py`, `evaluate.py`: eval metrics and Wilson interval.
- `src/permitcheck/cli.py`: the `permitcheck` command.
- `data/`: 300 applications, answer keys, `split.json` (200 dev, 100 held out).
- `results/`: eval outputs. The README tables come from here.
- `examples/`: example outputs for one deck and one addition.
- `docs/`: plan, walkthrough, interview Q&A, human steps, demo page.

## Rules

- The model never decides pass or fail. When unsure, say needs_human.
- Never change answer keys, held-out data or tests to make code pass.
- Never type numbers into the README.
- Every output carries the disclaimer.
- Copy no text from a real building code.

## Skills that fit

superpowers: executing-plans, test-driven-development, systematic-debugging, verification-before-completion, requesting-code-review.

## Do not read

`.venv/`, `data/applications/` and `data/answer_keys/` in bulk (300 files each, use the generator instead), `logs/`.
