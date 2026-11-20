# Demo

A real terminal session, written by `scripts/make_demo.sh` on 2026-11-20. Paths under a temp folder show as /tmp/demo.

## Check one application

```console
$ .venv/bin/permitcheck check data/applications/LH-APP-0064.txt --out /tmp/demo/out --now 2026-11-20T00:00:00Z
SYNTHETIC DATA ONLY. Larkspur Hollow and its code are fictional. This tool gives no legal advice. Not for production use.
LH-APP-0064: 2 fail, 1 needs a person, 13 pass (rule-v1, LHRC 2026.1)
  needs_human [R09, LHRC 11.3.1] Lot coverage: needs a person: the existing footprint (existing_footprint_sqft) is missing
  fail        [R10, LHRC 11.4.1] Height of an addition: height is 34.5 ft, and this section requires at most 30 ft
  fail        [R23, LHRC 13.3.2] Smoke alarm: smoke alarm: no
wrote /tmp/demo/out/LH-APP-0064/checklist.md, letter.md, queue.json and the audit log
```

## The correction letter it wrote

```markdown
# Correction letter: LH-APP-0064

> SYNTHETIC DATA ONLY. Larkspur Hollow and its code are fictional. This tool gives no legal advice. Not for production use.

Dear applicant,

We ran a first-pass check of application LH-APP-0064 against the Larkspur Hollow Residential Code (LHRC) version 2026.1. A software tool wrote this draft. A reviewer reads it before it is sent.

## Please correct these items

1. [R10, LHRC 11.4.1] Height of an addition. We read that height is 34.5 ft, and this section requires at most 30 ft. The code says: An addition is no taller than 30 ft, measured from grade to the highest point of the roof.
2. [R23, LHRC 13.3.2] Smoke alarm. We read that smoke alarm: no. The code says: An addition has at least one smoke alarm wired to the house system.

## Please confirm these items

We could not read these clearly enough to decide. Please state each value plainly, with units.

1. [R09, LHRC 11.3.1] Lot coverage. The existing footprint (existing_footprint_sqft) is missing. The code says: The existing footprint plus the new area covers no more than 40 percent of the lot.

Thank you,

Larkspur Hollow Building Division (fictional)
```

## Rerun the eval and compare it with the committed results

```console
$ .venv/bin/permitcheck eval --split both --check
SYNTHETIC DATA ONLY. Larkspur Hollow and its code are fictional. This tool gives no legal advice. Not for production use.
dev: 200 apps, field F1 0.973, violation precision 1.000, recall 0.903, false approve 0/77 apps, needs a person 0.132 of decisions, citations valid 619/619
ok results/eval_dev_rule.json matches a fresh run
heldout: 100 apps, field F1 0.971, violation precision 1.000, recall 0.882, false approve 0/47 apps, needs a person 0.119 of decisions, citations valid 293/293
ok results/eval_heldout_rule.json matches a fresh run
```

## Confirm the README tables

```console
$ .venv/bin/permitcheck readme --check
SYNTHETIC DATA ONLY. Larkspur Hollow and its code are fictional. This tool gives no legal advice. Not for production use.
README tables match the results files
```

