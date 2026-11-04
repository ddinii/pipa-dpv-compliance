# PoC3 evaluation v2 — change record

The original evaluation package (`PIPA_PoC_60시나리오_입력원문_및_정답표`, Excel, answer
sheets, JSON) is **not modified**. All corrections live in this repository as
separate, clearly named copies.

## Files

| File | What it is | SHA-256 |
|---|---|---|
| `gold_poc3_v1_original_extract.csv` | PoC3 rows of the original answer sheet, verbatim | `47ab93b1f37460ce6a0667cb9127ffcff5a09034364d5b552c25dc6f5d51b3af` |
| `gold_poc3_v2_corrected.csv` | same, with ONE corrected answer (below) | `09ba9975147e32d9ef8b65c795d168d2bf91ba5b29edcb2a563fc9b677b2bedc` |
| `p3_16_explicit_absent.json` | copy of original P3-16 with explicit absent markers | `bbb7d8c90361cc302a43327915a9f73d39a30cbeda255261ea348f6ca1efae4a` |
| `p3_19_explicit_absent.json`, `p3_20_explicit_absent.json` | already existing corrected copies (used in all runs) | see results |

## Changes

1. **Gold correction — P3-18 / P3-R01: RED -> AMBER** (only this entry).
   The input has `legal_basis = {"type": "미지정", "status": "unknown"}`.
   `status: unknown` is UNKNOWN in the frozen Fact contract (CONTRACTS.md: unknown and absent
   must not be converted into each other; the UI labels it "추가 검토 필요"). The P0 matrix
   defines R01 YELLOW as "유형 UNKNOWN/모호" and RED as "근거 미지정". An unknown legal basis is
   therefore YELLOW; the original RED expected an absence that the input does not state.
   The P3-18 input file is unchanged. All other gold entries are unchanged.
2. **Input correction — P3-16**: `retention.end_condition` and `retention.destruction_method`
   changed from `""` to `{"state": "absent"}` (same convention as P3-19/P3-20).
   The original used empty strings, which the frozen contract treats as a missing value, not
   as an explicit absence (missing -> YELLOW). The gold for P3-16 is unchanged (R04 RED, R08 RED).

## Result series (see `results_v2/`)

| Series | Inputs | Gold | Result |
|---|---|---|---|
| A | original inputs (P3-19/20 explicit_absent) | original | 158/160 |
| B | same as A | P3-18 R01 corrected | 159/160 |
| C | P3-16 explicit-absent copy | corrected | 160/160 |

Only A is a pure measure of code improvement against the original package (baseline before
any code change: 139/160 with the same P3-19/20 inputs). B and C include a gold/input
correction and must not be reported as code improvements.
