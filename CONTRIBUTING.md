# Contributing

Thanks for looking. This is a small demo, so the rules are short.

## Setup

```bash
./init.sh
source .venv/bin/activate
```

`init.sh` makes the virtual environment, installs the package, runs ruff and runs every test offline. Run it before and after every change.

## Rules

- Use synthetic data only. Never add a real application, a real address or personal data.
- Write rules from scratch. Never paste text from a real building code.
- The model never decides pass or fail. New code that decides goes in `src/permitcheck/checker.py`.
- When the tool is unsure, it says needs_human. Never add a path that guesses a pass.
- Never change an answer key, the held-out split or a test to make code pass. Fix the code. If a test is wrong, show the evidence and log the change in `DECISIONS.md`.
- Never type a number into the README. Run `permitcheck eval`, then `permitcheck readme`.
- Run `gitleaks git --pre-commit --redact --staged --verbose` before you commit. The pre-commit config runs it too.

## Adding a rule

1. Add the rule to `src/permitcheck/data/city_code.json` with an ID, a section, plain text, a check type and its parameters.
2. Add pass, fail and edge cases to `tests/test_rules.py`. The coverage test fails until you do.
3. Teach the generator to seed violations of the rule in `src/permitcheck/generator.py`.
4. Regenerate the data only if you must, and log why in `DECISIONS.md`.
