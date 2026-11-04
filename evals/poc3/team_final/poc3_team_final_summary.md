# PoC3 team submission — final re-evaluation (20 scenarios)

## 1. Purpose and scope
Re-run the 20 PoC3 evaluation scenarios requested by the team against the final code and report
the result as it is. Scope: the existing 20 scenarios and the existing rule-level answer sheet
only. No new scenario, no corrected input, no corrected answer.

## 2. Evaluation input (20 files)
| Scenarios | Source | Note |
|---|---|---|
| P3-01 ~ P3-18 | external evaluation package, `PoC3_설계JSON_20건/` (read only) | used unchanged |
| P3-19, P3-20 | `evals/poc3/p3_19_explicit_absent.json`, `p3_20_explicit_absent.json` | explicit-absent versions of the two scenarios (`{"state":"absent"}` instead of the strings "미기재"/"미설계") |

Paths and SHA-256 of all 20 files: `poc3_team_final_manifest.json`.
`<EVAL_ROOT>` in the manifest = the external folder `PIPA_PoC_60시나리오_입력원문_및_정답표`
(not part of this repository; it was only read and was verified unchanged after the run).

The P3-16 explicit-absent copy and the P3-18 R01 corrected answer were **not** used.

## 3. Answer sheet
The original rule-level answer sheet, unchanged: `정답표_360개_rule_level.csv` inside
`평가입력팩.zip` (PoC3 rows = 160). It was cross-checked as identical with
`정답표_360개_rule_level.xlsx` and with column D of the original Excel sheet `룰별_채점`.
No corrections were applied. SHA-256 values are in the manifest.

## 4. Method and code version
- Code: Git HEAD in the manifest (`d2999be`, tracked files clean at run time).
- Run: `evals/poc3/team_final/run_poc3_team_final.py` (temporary-style runner, read-only on
  the package). It calls the real endpoint `POST /api/v1/compliance/design-check` in-process
  (fastapi TestClient, no server, no network, no paid API), i.e. Fact builder -> Ontology
  mapper -> P0 Rule Engine, and reads the answers with the evaluation tool's own
  `extract_api_predictions`, `normalize_status` (YELLOW = AMBER), `calc_metrics`, `calc_far_frr`.
  The gold is read from the answer sheet at run time; nothing is hard-coded.
- Command: see the manifest (`command`).

## 5. Result
| Item | Value |
|---|---|
| Correct rule judgements | **158 / 160** |
| Accuracy | **98.75 %** |
| Macro-F1 (original tool definition) | 96.61 % |
| FAR (gold AMBER/RED judged GREEN) | 0 / 30 = 0 % |
| FRR (gold GREEN judged not GREEN) | 0 / 108 = 0 % |

Confusion (gold -> predicted): GREEN 108/108, AMBER 12/12, N/A 22/22, RED 16/18 (2 predicted AMBER).
Per-rule rows: `poc3_team_final_rule_results.csv` (160 rows: scenario, rule, gold, prediction,
raw API status, match flag, input file).

## 6. The two mismatches
| Scenario / Rule | Gold | Predicted | Cause |
|---|---|---|---|
| P3-16 / P3-R08 | RED | AMBER (YELLOW) | The input gives `end_condition` and `destruction_method` as empty strings `""`. The frozen contract treats an empty value as a *missing* Fact (not an explicit absence), so R08 returns YELLOW. The expected RED would need the explicit marker `{"state":"absent"}`. |
| P3-18 / P3-R01 | RED | AMBER (YELLOW) | The input has `legal_basis.status = "unknown"` (type "미지정"). `unknown` is UNKNOWN in the frozen contract, not absent; the R01 matrix defines YELLOW for an unknown/ambiguous type and RED for a missing basis. |

Both are input/answer-sheet interpretation differences, not Rule Engine defects; they were
**not** corrected for this submission. One cosmetic point: the P3-18 R01 reason text still reads
"법적근거가 지정되지 않았습니다" after the contract sentence, which is slightly misleading for
an unknown (not absent) basis; the verdict itself is unaffected.

## 7. Change from the recorded 139/160 to 158/160
The recorded Excel result (column E) has 139/160 correct. Re-running each commit of the
improvement series with the **same inputs and the same answer sheet** gives:

| Code state | Correct | Changed judgements |
|---|---|---|
| Start of the series (`dccf9ea`) | 139 | 0 vs recorded Excel column E |
| + ConsentRequest `planned=false` / missing field (`2548db2`) | 142 | P3-12 R02, R03, R04 |
| + legal basis tokens and status (`84ff70f`) | 150 | P3-04, P3-05 R01~R04 (8) |
| + concreteness checks (`a89d42a`) | 158 | P3-06 R02, P3-07 R03, P3-08 R04/R08, P3-09 R05, P3-10 R11, P3-11 R11, P3-15 R02 (8) |
| + R08 per activity, explicit end-condition absent, R08 per-activity required Fact (`ae4d558`, `dc9e07a`, `d2999be`) | 158 | none |

- 19 judgements changed from the recorded Excel result, all of them to the gold value; no judgement
  that was correct became wrong.
- These changes are caused by **code / Rule Engine changes** (verified by the commit-by-commit run).
- The last three commits (R08 consistency) changed none of the 160 judgements; they fix
  behaviours that these 20 scenarios do not exercise (e.g. several activities).
- **Input**: the recorded 139 is reproduced only with the explicit-absent P3-19/P3-20 inputs.
  With the package's own P3-19/P3-20 JSON (string sentinels "미기재"/"미설계", which the frozen
  contract keeps as ordinary values) the final code gives 7 further mismatches (P3-19 R03, R05,
  R08, R11; P3-20 R05, R08, R11 -> GREEN instead of RED). It cannot be shown from the
  recorded files how column E of those two scenarios was originally produced.
- **Answer sheet**: unchanged.

## 8. Limits and cautions
- 20 synthetic scenarios designed by the team; the code improvements were made after seeing
  these same scenarios, so 98.75 % is **not** a generalisation estimate for unseen designs.
- The concreteness check is a limited static check with a closed generic-word list; it does not
  detect vague wording mixed with specific words and does not judge legal adequacy.
- GREEN is not a legal compliance certificate and RED is not a confirmed violation; AMBER means
  "needs confirmation". The score measures agreement with the team's expected labels only.
- A separate reference result with a corrected P3-16 input and a corrected P3-18 answer exists in
  `evals/poc3/results_v2/` (series C). It is not part of this submission, is not combined with it,
  and is not an official performance figure.
- The runner uses the in-process FastAPI test client instead of the original tool's `api` mode
  (which needs a running server and a ZIP path fix); the evaluation package's scripts were not
  modified.
