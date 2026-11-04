# PoC3 evaluation v2 results

Generated from the working tree on top of commit `a89d42aa1e6f9b4b09ca27763757132646273ad5` (uncommitted changes:
`M app/builders/poc3_fact_builder.py, M app/rules/engine.py, ?? evals/poc3/gold_poc3_v1_original_extract.csv, ?? evals/poc3/gold_poc3_v2_corrected.csv, ?? evals/poc3/p3_16_explicit_absent.json, ?? tests/test_poc3_r08_activities.py, ?? tests/test_poc3_retention_absent.py`; `git diff HEAD` SHA-256
`caff7ed2d4d0812ee7c1bbeca8311cac5d16f2a8b31dc58371b4d78ab76e4490`). Each JSON file lists code identity, every input file with
SHA-256, the gold file with SHA-256, all 160 rule results and the mismatches.

| File | Meaning | Accuracy |
|---|---|---|
| `A_original_inputs_original_gold.json` | original inputs and original gold | 158/160 |
| `B_gold_corrected.json` | P3-18 R01 gold corrected only | 159/160 |
| `C_input_and_gold_corrected.json` | + P3-16 explicit-absent input | 160/160 |

Cautions
- A -> B changes the **answer key**, A/B -> C changes an **input**. Neither is a code improvement.
- P3-19/P3-20 always use the repository `explicit_absent` JSON; the original package JSON
  reproduces fewer matches.
- The other 17 inputs are read from the original package folder (read only); their SHA-256
  values are in each result file.
- Between A and C only one verdict differs (P3-16 R08 AMBER -> RED); no other rule changed.
- The labels follow the original sheet (AMBER = YELLOW). The results do not certify legal
  compliance; GREEN is not a compliance certificate and RED is not a confirmed violation.

Scope note
- Team submission result: series **A** (original inputs and original answer sheet; only
  P3-19/P3-20 use the repository explicit_absent JSON).
- Series **B/C** are separate reference results that include a corrected answer / input. They
  are not added to, and do not replace, the series A result, and must not be used as the
  official result without the team's approval.
