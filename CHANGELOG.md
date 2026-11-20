# Changelog

All notable changes to this project are listed here.

## v0.1.0-rc1 (release candidate, not yet tagged)

Release commit: this commit (the commit right after it records its full SHA here)

### Added

- A fictional city code, the Larkspur Hollow Residential Code (LHRC 2026.1), with a schema check and a sha256 in every audit line.
- A seeded generator that writes synthetic applications in four formats with hidden answer keys, and a fixed dev and held-out split.
- A rule-based extractor with a confidence score for every field.
- A plain-code checker that returns pass, fail or needs_human with a section citation. A missing or low-confidence field is always needs_human.
- A reviewer checklist, a correction letter with checked citations, a review queue and an append-only audit log.
- `permitcheck eval` with field F1, violation precision and recall, the false-approve rate with Wilson intervals, the needs-human rate and citation validity.
- An LLM extractor with replay and record modes and a grounding check. It is untested live.
- A README whose tables a script writes from the results files, and a test that fails when they drift.
