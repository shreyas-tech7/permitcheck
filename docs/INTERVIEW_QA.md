# Interview questions and answers

Each answer points to the code (file and function) and the results (file and number). The numbers come from the run on 2026-11-20 with the rule-based extractor and no model.

## Why does the model extract and code decide?

A model is good at reading messy text and bad at being exactly right every time. A code check is the opposite. So the model extracts, which means it only reports what the text says, and code decides. In `src/permitcheck/checker.py`, `check_rule` takes values and confidences and applies the rule. The LLM prompt in `src/permitcheck/llm.py` tells the model not to judge, and `test_model_cannot_decide` in `tests/test_llm.py` proves that a model's "pass" never reaches a result. The split also makes every decision explainable: the audit log line shows the value, the confidence and the rule.

## Why does a false approve cost more than a false reject?

A false approve lets an unsafe deck or addition get built. Fixing it later means a failed inspection, a teardown or an injury. A false reject costs the applicant a day and a reply to the city. So the eval treats the false-approve rate as the main number. `evaluate` in `src/permitcheck/evaluate.py` counts it two ways: per application with a critical violation and per critical violation. On the held-out set it is 0 of 47 applications and 0 of 63 critical violations (`results/eval_heldout_rule.json`).

## What is the needs-human result for?

It is the safe exit. When a field is missing, read with confidence below 0.8 or the wrong type, the rule cannot be decided. Instead of guessing, the tool sends it to a person. `_get` in `src/permitcheck/checker.py` raises the signal, and `queue_items` in `src/permitcheck/report.py` builds the review queue from it. On the held-out set, 203 of 1,708 rule decisions went to a person, an 11.9% rate. That is the price of zero false approves. The work is to push that rate down without letting a single guess through.

## What can the synthetic data not show?

It cannot show how real applicants write, which labels they use or how often real plans break each rule. It cannot show scans, drawings or handwriting. The generator in `src/permitcheck/generator.py` makes the mess I thought of, so the eval proves the tool handles that mess. A real pilot would need real applications, permission from the city and a reviewer to label them. The README says this under Limits.

## How do you know zero false approves is not luck?

I do not know it for sure, and the README says so. With 63 critical violations and none missed, the 95% Wilson upper bound is 5.7% per critical violation (`results/eval_heldout_rule.json`). So the true rate could still be a few percent. Because zero looked too good, I ran a second seed with 300 new applications: 0 false approves in 134 applications with a critical violation (`results/seed2/eval_all_rule.json`). That shows the result holds across random draws from the same generator. It does not show it holds on new wording.

## How did you keep the held-out set honest?

`data/split.json` fixed 200 dev and 100 held-out applications before any extractor existed. I tuned only on dev. The extractor and checker were frozen at commit 68d49bf, then held-out ran once. `test_split_is_200_dev_and_100_heldout_with_no_overlap` in `tests/test_generator.py` guards the split. `DECISIONS.md` logs the order.

## How do you stop the letter from inventing a citation?

`letter_md` in `src/permitcheck/report.py` calls `_check_citation` for every item before writing. The section must exist in the code file and belong to the rule it names, or it raises `CitationError`. A test in `tests/test_letter.py` feeds it a fake section and expects the error. The eval reads every citation back out with `cited_sections`: 293 of 293 valid on held-out. That is a fixed count, so it has no interval.

## Why a Wilson interval and not plus or minus?

The simple normal interval breaks near zero. It gives zero width when the count is zero, which would claim certainty I do not have. The Wilson score interval stays sensible at zero and at small n. `wilson` in `src/permitcheck/metrics.py` computes it, and `test_wilson_matches_reference_values` checks it against known values.

## How does the confidence score work?

`RuleExtractor` in `src/permitcheck/extract.py` scores each field by how it was read. An exact label scores 0.95. A label with a small typo scores 0.85, which still passes the 0.8 threshold. A rounded value ("about 12 ft") scores 0.5, a value without a unit 0.4, two values that disagree 0.3 and garbled text 0.2. Everything below 0.8 goes to a person. The scores are rules I wrote, not learned. That keeps them easy to audit.

## What stops the LLM extractor from making things up?

The grounding check. `_grounded` in `src/permitcheck/llm.py` requires the model's quote to appear in the application and to parse to the same value the model gave. If either fails, the confidence drops to 0.5 at most, so the rule goes to a person. Tests in `tests/test_llm.py` cover a quote that is not in the text and a quote that disagrees with the value. Bad JSON gives no fields at all, so every rule becomes needs-human.

## Did the LLM extractor run on real models?

No. Record mode needs a free provider key, and the build machine could not reach any provider. Replay mode and the grounding check are built and tested offline. `BLOCKERS.md` logs the block, and `docs/HUMAN_STEPS.md` gives the command to run once a key exists. The README numbers come from the rule-based extractor only.

## What does the audit log record, and why?

One JSON line per decision from `append_audit` in `src/permitcheck/audit.py`. It records the inputs with their confidences, the status and reason, the rule version, the sha256 of the code file, the extractor name and the tool version. A reviewer can replay any decision months later and know exactly which code and which reader made it. The log only appends, which `test_log_appends_and_never_overwrites` checks.

## Where does the tool fail today?

Most misses are labels the rule-based extractor does not know. Those rules go to a person, so they cost review time but not safety. On held-out, violation recall is 88.2% (90 of 102 seeded violations marked fail) and the rest went to needs-human (`results/eval_heldout_rule.json`). The checker never marked a violation as pass. `docs/PROPOSALS.md` suggests letting a reviewer map a new label once.

## How fast and how cheap is it?

`scripts/time_eval.py` timed 300 applications on two cores: 11.98 ms per application for extraction, checking and all three outputs, with zero model calls and zero cost (`results/timing.json`). The LLM extractor would add one model call per application, on a free tier.

## How is this different from what vendors sell?

Vendors such as Archistar, CodeComply.Ai from CivicPlus, Clariti's CivCheck and Blitz AI sell plan review tools to cities. permitcheck is a small open demo. Its value is the public answer key and the eval harness, which show exactly how often it would approve something it should not. It makes no claim to match any vendor.

## What would you build next?

A reviewer page to accept or reject each checklist item, which is the stretch item in the brief. Then label learning from the review queue, a per-rule false-approve table and a second fictional code to prove nothing is tied to one city. The list is in `docs/PROPOSALS.md`.
