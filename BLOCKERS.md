# Blockers

What failed, the exact error, and what was done instead.

- 2026-11-20 `npx -y skills add DietrichGebert/ponytail ...` was refused by the session permission system ("Permission for this action was denied"). Not retried in another form. Ponytail, caveman, humanizer and find-skills rules are applied by hand from the build prompt.
- 2026-11-20 Record-mode hosts unreachable: `curl` to huggingface.co, api.groq.com, openrouter.ai, api.osv.dev and semgrep.dev all returned `000` (no connection). No provider key in the environment. Fallback: ship the rule-based extractor. The LLM extractor is tested in replay mode with hand-written fixtures only and is untested live. Its fixtures stay out of the README numbers.
- 2026-11-20 The GitHub repo `shreyas-tech7/permitcheck` was empty when cloned. The backup remote holds the README commit, so the branch starts there.
- 2026-11-20 Bug (live, frequency 2 x severity 5 = 10, fixed): on dev data, a "Revised" line with a typo in its label was not read, so the first value looked clean and confident. A trailing period on the last prose sentence hid the revised value too. Both could cause a false approve. Fixed in `extract.py`, with regression tests in `tests/test_extract.py`.
