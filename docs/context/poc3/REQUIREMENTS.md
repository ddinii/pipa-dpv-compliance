# PoC3 Requirements

## Purpose

PoC3 provides Privacy-by-Design development support.

It receives a structured design form and evaluates the design against the frozen PoC3 P0 rules.

PoC3 does not use an LLM extractor.

## Input

The request is based on the existing structured PoC3 form format demonstrated by:

examples/SC-D01_form.json

Top-level fields include:

- analysis_id
- controller
- collection_activities
- entrusted_processings
- third_party_provision_state
- cross_border_transfer_state

controller contains:

- controller_id
- name

Each collection activity may contain:

- activity_id
- purpose
- legal_basis
- consent_request
- personal_information_items
- retention
- denies_service_on_optional_refusal

Each personal information item contains:

- item_name
- is_required
- design_rationale

retention may contain:

- end_condition
- destruction_method

Each entrusted processing contains:

- activity_id
- processor
- task

Do not redesign the existing PoC3 form contract unless necessary for HTTP request validation.

## Fact Production

Reuse:

app.builders.poc3_fact_builder.build_poc3_facts

Do not duplicate Fact construction in the API layer.

The builder produces frozen PoC3 Facts F3-01 through F3-13.

## Ontology Mapping

Construct OntologyMapper using request metadata:

- analysis_id
- controller.controller_id
- controller.name

Then call:

mapping_result = mapper.map(facts)

Do not manually construct RDF in the API layer.

## Rule Evaluation

Use:

P0RuleEngine.evaluate_mapping_result(
    mapping_result,
    poc="PoC3",
)

Exactly 8 frozen PoC3 P0 Rules must be evaluated:

- P3-R01
- P3-R02
- P3-R03
- P3-R04
- P3-R05
- P3-R06
- P3-R08
- P3-R11

Do not add or remove PoC3 rules.

## Response

The API must expose deterministic RuleResult information without changing Rule Engine semantics.

Each result must preserve at least:

- rule_id
- rule_version
- status
- applicability
- matched_facts
- missing_facts
- uncertain_facts
- evidence
- legal_basis
- reason
- recommendation
- evaluated_at

Existing instance_results and implementation_notes may also be returned.

Do not translate GREEN/YELLOW/RED/N/A into PASS/FAIL.

## Legal Meaning

The API/UI must not represent GREEN as legal compliance certification.

RED must not be represented as a confirmed legal violation.

Results are decision-support outputs based on the implemented frozen P0 rules and supplied design facts.

## Current Example

examples/SC-D01_form.json is the existing PoC3 structured-form example and should be usable as an integration/acceptance fixture.

It contains:

- three CollectionAndUse activities
- two EntrustedProcessing activities
- confirmed-false third-party provision scenario state
- confirmed-false cross-border transfer scenario state

The existing builder intentionally does not create new frozen Facts for the two confirmed-false scenario-state fields.

An explicitly present empty `entrusted_processings` array is converted by the
service into evidence-backed
`system_metadata.activity_presence(EntrustedProcessing=confirmed_false)`.
This makes P3-R11 N/A without inventing F3-14 or a core ontology property.

## consent_request → F3-03 value_state (input semantics)

No Fact ID, Rule ID or ontology term is added; only the `value_state` of the
existing F3-03 is derived from the input:

| Input | F3-03 |
|---|---|
| `consent_request.planned = true` | confirmed (unchanged) |
| `consent_request.planned = false` and consent legal basis | `absent` (explicit "not designed") → P3-R02/R03/R04 RED |
| `consent_request` field missing or null | `unknown` (no `planned=true` default is invented) → P3-R02/R03/R04 YELLOW |
| `planned = false` and non-consent legal basis | confirmed (unchanged); consent Rules keep their applicability handling |

The Ontology Mapper does not recreate the ConsentRequest node from F3-09 for an
activity whose F3-03 is absent. Consequence: for such an activity P3-R06 sees no
ConsentRequest and reports YELLOW for its optional items.

## legal_basis → F3-02 (allowed tokens and status)

Token definitions live in one module, `app/mapping/legal_basis_tokens.py`, used
by the Fact builder, the Ontology Mapper and the Rule Engine. No ontology class,
Fact ID or Rule condition is added.

Allowed concrete legal basis tokens: `Consent`, `Contract`, `LegalObligation`.
Matching is exact after trimming and case folding. There is no substring
matching and no Korean alias ("비동의", "동의 안함" and even "동의" are not
Consent). `LegitimateInterest`, typos and any other value are not concrete
types (P3-R01 YELLOW, P3-R02/R03/R04 YELLOW).

`Consent` keeps its ontology class. `Contract` and `LegalObligation` stay plain
`LegalBasis` nodes, identified by their canonical `rdfs:label`; the Engine
accepts such a label as a concrete type only on the legal-basis node linked to
the activity. Confirmed non-consent bases make P3-R02/R03/R04 N/A.

`legal_basis.status` sets the F3-02 `value_state`:

| status | F3-02 |
|---|---|
| `confirmed`, `planned`, key missing | confirmed |
| `unknown` | unknown (value not used) → P3-R01..R04 YELLOW |
| anything else | input validation error (422) |

`legal_basis={"state":"absent"}` is not supported yet. F3-03 is made `absent`
for `planned=false` only for a confirmed Consent basis; with an unknown basis
F3-03 stays confirmed so the rules are YELLOW, not RED.
