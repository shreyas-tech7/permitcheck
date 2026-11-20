# LLM fixtures

Recorded model responses go here, one file per prompt: `<model>/<sha256 of model and prompt>.json`.

This folder is empty on purpose. The build VM could not reach any free provider and had no key, so nothing was recorded. The test fixtures in `tests/test_llm.py` are hand-written and are not model recordings.

To record, see the "Record mode" step in [docs/HUMAN_STEPS.md](../../docs/HUMAN_STEPS.md).
