# LLM Extractor Handoff — PoC1 / PoC2

Concise integration contract for replacing `MockPoC1Extractor` /
`MockPoc2Extractor` with a real LLM-backed extractor. This document does not
duplicate the Fact Dictionary or Rule Specification — see
`docs/context/poc1/FACTS.md`, `docs/context/poc1/RULES.md`,
`docs/context/poc2/FACTS.md`, `docs/context/poc2/RULES.md`, and
`docs/context/core/CONTRACTS.md` for the authoritative content.

## 1. Architecture boundary

```
PoC1:
policy_text
  -> Poc1Extractor.extract(...)
  -> ExtractionResult(Frozen Fact[], system metadata)
  -> run_policy_check() [app/services/compliance.py]
  -> OntologyMapper.map()
  -> P0RuleEngine.evaluate_mapping_result(..., poc="PoC1")
  -> RuleResult[] -> REST response -> frontend RuleResultCard

PoC2:
incident / notification input
  -> Poc2Extractor.extract(...)
  -> ExtractionResult(Frozen Fact[], system metadata)
  -> run_breach_check() [app/services/compliance.py]
  -> OntologyMapper.map()
  -> P0RuleEngine.evaluate_mapping_result(..., poc="PoC2")
  -> RuleResult[] -> REST response -> frontend RuleResultCard
```

The extractor extracts Facts only. It must never:
- assign GREEN / AMBER / RED / N/A;
- determine legal compliance;
- implement P0 Rule logic or replace `P0RuleEngine`.

Rule evaluation remains deterministic and lives exclusively in
`app/rules/engine.py`.

## 2. Exact Protocol contracts

From `app/extractors/base.py` (copied verbatim — do not add/remove
parameters):

```python
class Poc1Extractor(Protocol):
    def extract(
        self,
        *,
        analysis_id: str,
        controller_id: str,
        controller_name: str | None,
        policy_text: str,
    ) -> ExtractorOutput:
        ...


class Poc2Extractor(Protocol):
    def extract(
        self,
        *,
        analysis_id: str,
        controller_id: str,
        controller_name: str | None,
        incident: dict[str, Any],
        notification: dict[str, Any] | None,
    ) -> ExtractorOutput:
        ...
```

Return value: legacy `list[dict]` or `ExtractionResult`. Each item in
`ExtractionResult.facts` is a raw Fact envelope (see §3) that must pass
`app.mapping.fact_schema.validate_facts()` unchanged. New real extractors
should return `ExtractionResult` when they can explicitly establish activity
absence.

Current implementations of each Protocol (integration test doubles, not
reference behavior):
- `Poc1Extractor` → `MockPoC1Extractor` (`app/extractors/poc1_mock_extractor.py`)
- `Poc2Extractor` → `MockPoc2Extractor` (`app/extractors/poc2_mock_extractor.py`)

Both mocks ignore their text/dict input content entirely and return a fixed
scenario; they exist only to prove the extractor → mapper → engine pipeline
works end-to-end before a real extractor exists.

## 3. Frozen Fact output contract

Envelope (from `docs/context/core/CONTRACTS.md`, enforced by
`app/mapping/fact_schema.py:REQUIRED_FIELDS`):

| Field | Notes |
|---|---|
| `fact_id` | e.g. `"F1-01-001"`; must match `^(F[123]-\d{2})(?:[-_:].+)?$` |
| `subject_id` | non-empty string |
| `activity_id` | string or `null`; required for every Fact except `F1-11`/`F1-12` (global rights Facts) — never substitute `subject_id` |
| `ontology_class` | non-empty string, must resolve to the `PIPA_NAMESPACE` (`https://w3id.org/pipa-compliance/ontology#`) or be a bare local name |
| `ontology_property` | string or `null`, same namespace rule |
| `value` | any JSON value; may be `null` |
| `value_state` | one of `confirmed`, `unknown`, `absent` (`fact_schema.VALUE_STATES`) |
| `source_type` | one of `policy_text`, `incident_record`, `notification_notice`, `structured_form`, `derived` (`fact_schema.SOURCE_TYPES`), constrained per-PoC below |
| `evidence` | non-empty array; each item needs at least one of `text`, `field_path`, `offset` |
| `schema_version` | must equal `"fact-1.0"` (`FACT_SCHEMA_VERSION`) exactly |

`source_type` constraint by Fact family (`fact_schema.py:120-128`):
- `F1-*` → `{"policy_text", "derived"}`
- `F2-01, F2-02, F2-05, F2-06` (incident facts, `POC2_INCIDENT_FACTS`) → `{"incident_record", "derived"}`
- `F2-03, F2-04, F2-07, F2-08, F2-09, F2-10` (notice facts, `POC2_NOTICE_FACTS`) → `{"notification_notice", "derived"}`

Value-state semantics — do not collapse these:
- **confirmed** — evidence supports the asserted value (including a
  confirmed `false`/absence-of-fact value; that is still `confirmed`, not
  `absent`).
- **unknown** — the source/input does not establish the value (extractor
  could not determine it from what was given).
- **absent** — explicit absence is established under the current input
  contract (e.g. PoC2 `notification` was not supplied at all, so every
  notice-side Fact is `absent`, not `unknown` — see
  `MockPoc2Extractor.extract`, `app/extractors/poc2_mock_extractor.py:233-258`).

Never convert `false → unknown`, `false → absent`, `unknown → absent`, or
`absent → unknown` (`docs/context/core/CONTRACTS.md`).

Evidence requirement is enforced by `fact_schema._validate_evidence`: a
non-empty list; every item needs `text`, `field_path`, and/or `offset`. Do
not fabricate evidence not traceable to the actual input.

Do not invent fields inside the frozen Fact envelope beyond the table above.

### Activity-presence metadata

`ExtractionResult.system_metadata` may contain only validated
`activity_presence` entries for `ThirdPartyProvision`, `EntrustedProcessing`,
or `NotificationNotice`. Allowed states are `confirmed_true`,
`confirmed_false`, and `unknown`; each entry requires source type and
traceable evidence.

Property absence and activity absence are different. For example, F1-05
`value_state=absent` says that an existing ThirdPartyProvision has no recipient
value and is a RED/AMBER input. `ThirdPartyProvision=confirmed_false` says that
the provision activity itself is explicitly absent and makes P1-R03 N/A.

## 4. PoC1 output scope

The real extractor may emit only the existing frozen PoC1 Fact IDs, per
`docs/context/poc1/FACTS.md` and `docs/context/poc1/RULES.md`:

| Fact ID | Required by Rule |
|---|---|
| F1-01, F1-02 | P1-R01 (처리목적 명시) |
| F1-03, F1-04 | P1-R02 (처리·보유기간 명시) |
| F1-05, F1-06, F1-07 | P1-R03 (제3자 제공 기재) |
| F1-08 | P1-R04 (파기 절차·방법 기재) |
| F1-09, F1-10 | P1-R06 (처리위탁 기재) |
| F1-11, F1-12 | P1-R07 (정보주체 권리행사 방법) — global, `activity_id = null` |

`source_type` normally `policy_text`; `derived` only where the frozen
contract allows it. Do not invent additional F1 Fact IDs. For the exact
`ontology_class`/`ontology_property`/expected value shape per Fact ID,
consult `app/mapping/mapping_registry.py` and
`tests/test_poc1_mock_extractor.py` (not duplicated here).

## 5. PoC2 output scope

The real extractor may emit only the existing frozen PoC2 Fact IDs F2-01
through F2-10, per `docs/context/poc2/FACTS.md` and
`docs/context/poc2/RULES.md`:

| Fact ID | Required by Rule | Side |
|---|---|---|
| F2-01 | P2-R01, P2-R08 | incident |
| F2-02 | P2-R01, P2-R02 | incident |
| F2-03 | P2-R01 | notice |
| F2-04 | P2-R02 | notice |
| F2-05 | — (incidentDate) | incident |
| F2-06 | — (detectionDate) | incident |
| F2-07 | — (notificationDate) | notice |
| F2-08 | P2-R03 | notice |
| F2-09 | P2-R03 | notice |
| F2-10 | P2-R08 | notice (per `fact_schema.POC2_NOTICE_FACTS`) |

Explicit boundaries (`docs/context/poc2/FACTS.md`,
`docs/context/poc2/RULES.md`):
- Incident Facts and `NotificationNotice` Facts are distinct; never collapse
  `incident.affectsPersonalInformation` (F2-02) into
  `notice.mentionsPersonalInformation` (F2-04).
- `incidentDate` (F2-05) and the notice-stated incident time (F2-08) are
  distinct; F2-08 must never be derived from F2-05.
- Do not create `triggersNotificationObligation`.
- Do not create `ReportingObligation`.
- Do not implement notification/reporting thresholds, including Enforcement
  Decree thresholds, in this v1 integration.
- When `notification` is not supplied, represent every notice-side Fact
  (F2-03, F2-04, F2-07, F2-08, F2-09) as `absent` with `source_type:
  "derived"` — never fabricate a `NotificationNotice`. See
  `MockPoc2Extractor.extract` for the reference pattern.
- In addition, the service records evidence-backed
  `NotificationNotice=confirmed_false` activity-presence metadata. P2-R01
  remains RED; P2-R02 and P2-R03 become N/A.

## 6. Replacement points

Both extractors are consumed only through the `Poc1Extractor`/`Poc2Extractor`
Protocol, injected in `app/services/compliance.py`:

- `run_policy_check(request, *, extractor: Poc1Extractor | None = None)`
  (`app/services/compliance.py:65-69`) — falls back to module-level
  `_default_poc1_extractor = MockPoC1Extractor()` (`compliance.py:21`).
- `run_breach_check(request, *, extractor: Poc2Extractor | None = None)`
  (`app/services/compliance.py:119-123`) — falls back to
  `_default_poc2_extractor = MockPoc2Extractor()` (`compliance.py:22`).

`app/api/compliance.py` calls `run_policy_check(request)` and
`run_breach_check(request)` with no `extractor` argument, so it always uses
the module-level default. To wire in the real extractor for the live API,
the only required change is replacing the two default-instantiation lines
(`compliance.py:21-22`) to construct the real class instead of the Mock
class (or an equivalent dependency-injection point, at the team's
discretion) — no other line in `compliance.py` changes.

**No modification required to:** `app/api/compliance.py` request/response
handling, `OntologyMapper`, `P0RuleEngine`, the frontend API types
(`frontend/src/types/api.ts`), or the frontend pages
(`PolicyCheckPage.tsx`, `BreachCheckPage.tsx`), **provided** the real
extractor:
1. implements the Protocol signature exactly (§2), and
2. emits only Fact envelopes that pass `validate_facts()` unchanged (§3–5),
   and any presence metadata passes `validate_system_metadata()`.

## 7. Security / data handling

- Never hardcode provider credentials (API keys, tokens) in source code.
- Credentials must come from environment variables.
- Never commit `.env`; never put real secrets in `.env.example`.
- Do not use real personal information or real breach records in repository
  test fixtures — synthetic/anonymized fixtures only (see
  `examples/poc1_synthetic_policy_fixture.json`,
  `examples/poc2_synthetic_breach_fixture.json` for the existing pattern).
- Do not log raw source text (policy text, incident/notification content)
  unnecessarily.
- Do not log API keys or auth headers.

This handoff does not add or reference any real secret, provider, or model
configuration.

## 8. Acceptance checklist

Before integrating a real extractor:

- [ ] Implements `Poc1Extractor`/`Poc2Extractor` Protocol exactly as in §2
- [ ] Output passes `app.mapping.fact_schema.validate_facts()` unchanged
- [ ] Activity-presence metadata passes `validate_system_metadata()`
- [ ] Emits only the allowed Fact IDs for its PoC (F1-01..F1-12 / F2-01..F2-10)
- [ ] Every Fact has non-empty, traceable `evidence`
- [ ] `unknown` vs `absent` distinction is preserved, never collapsed
- [ ] property absence vs activity absence distinction is preserved
- [ ] `P0RuleEngine` and `OntologyMapper` remain unchanged
- [ ] `RuleResultResponse`/`ComplianceResponse` API contract remains unchanged
- [ ] Full existing test suite (`python -m pytest -q`) still passes
- [ ] New extractor-specific tests added (mirroring
      `tests/test_poc1_mock_extractor.py` / `tests/test_poc2_mock_extractor.py`)
- [ ] No secrets or real PII committed

## 9. Explicit non-goals

This handoff document does NOT define:
- model/provider choice;
- prompt engineering strategy;
- fine-tuning;
- LLM-based legal judgment;
- LLM-based GREEN/AMBER/RED scoring;
- automatic `ReportingObligation` determination;
- frontend redesign.

See also `docs/context/backend/EXTRACTOR_INTEGRATION.md` and
`docs/context/backend/EXTRACTOR_DECISIONS.md` for prior integration-design
decisions referenced directly in the mock extractor source.
