# Handover

## Done

Every feature in `feature_list.json` except F17. The rule-based extractor makes zero false approves on the held-out set (`results/eval_heldout_rule.json`). The README tables come from the results files. The release check is in `docs/RELEASE_CHECK.md`.

Release commit: 8fb00cfa50f4861f80a58c9e8b4249b8c2dfb374. It is tagged `v0.1.0-rc1`. Later commits tidy the repo for public release.

## Not done

- F17: the live LLM record run. It needs a free Groq key. See `docs/HUMAN_STEPS.md`, step 6.
- The stretch reviewer page. It is listed in `docs/PROPOSALS.md`.

## Open decisions for Shreyas

- Whether the README should show LLM numbers once they exist.
- Whether `docs/build/BUILD_PROMPT.md` stays public.
- Whether to publish the package to PyPI.

## Exact commands

```bash
git clone https://github.com/shreyas-tech7/permitcheck.git && cd permitcheck
git checkout claude/build-permitcheck
./init.sh
.venv/bin/permitcheck eval --split both --check
.venv/bin/permitcheck readme --check
.venv/bin/python scripts/check_features.py
```

## Resume launcher

Read docs/build/BUILD_PROMPT.md and follow it. Resume from PROGRESS.md on branch claude/build-permitcheck. Do not ask questions. Do not stop until every Done-means item is true or blocked with a fallback.
