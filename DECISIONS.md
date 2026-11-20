# Decisions

One line per choice: what was weighed and why.

- 2026-11-20 Name: `permitcheck`. PyPI `permitcheck` 404 and npm `permitcheck` 404 on 2026-11-20. `plancheck` is taken on npm (200). Kept the repo name.
- 2026-11-20 Base branch: origin was empty, so `claude/build-permitcheck` starts from the backup remote's `main` (one README commit). Other option was an orphan branch. Shared history keeps the PR simple.
- 2026-11-20 City: Larkspur Hollow, fictional. Code: Larkspur Hollow Residential Code (LHRC) version 2026.1, 25 rules written from scratch. Numbers chosen to differ from any real model code where possible.
- 2026-11-20 Critical rules: 13 of 25 (three setbacks, coverage, addition height, guard height and openings, risers, joists, footings, ledger, escape window, smoke alarm). Paperwork and size-path rules are non-critical.
- 2026-11-20 A conditional rule whose condition is false passes with the reason "not required". Options were pass or a fourth status. A fourth status would complicate every metric.
- 2026-11-20 Confidence threshold 0.8. Anything below goes to needs_human. A clean value with a near-miss label scores 0.85, so typos in labels still pass through.
- 2026-11-20 The answer key logic lives in the generator, written separately from the checker, so the eval can catch a checker bug.
- 2026-11-20 Field F1 counts every extracted value at any confidence. It measures reading. The decision metrics measure deciding.
- 2026-11-20 Stdlib only. The social preview uses a stdlib PNG encoder, not Pillow.
- 2026-11-20 Skills: ponytail, caveman, humanizer and find-skills could not be installed (the permission system refused `npx skills add`). Their rules are applied by hand.
- 2026-11-20 Origin had no main. Pushed the README commit (6892e0a) as origin main so a pull request has a base. GitHub made claude/build-permitcheck the default branch because it was pushed first. HUMAN_STEPS says to set main as the default.
- 2026-11-20 Regenerated data once before any extractor existed (a lint fix changed the order of two random draws). The committed commit holds only the final data. No tuning had happened.
- 2026-11-20 Tuning used dev only. The extractor and checker were frozen at commit 68d49bf (the eval command and the dev results, before the held-out run). Then held-out ran once: 0 false approves on 63 critical violations in 47 applications.
- 2026-11-20 Zero false approves and precision 1.000 look too good, so a second data seed (20261121, 300 new applications) ran too: also 0 false approves on 134 applications with critical violations. Both runs are reported. Both seeds come from the same generator, so this shows stability across random draws, not across new wording.
- 2026-11-20 False approve is reported two ways: per application (the brief's definition) and per critical violation. A rule that is not checked counts as needs_human, never as pass.
- 2026-11-20 The garbled-digit fix came from the second seed, not from the held-out set. Dev and held-out results stayed identical after the fix, so the held-out numbers are still from the frozen run. The second-seed results were rerun and committed.
