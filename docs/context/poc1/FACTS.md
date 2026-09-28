# PoC1 Frozen Facts

## Scope

PoC1 evaluates a privacy policy.

The extractor receives policy text and produces frozen Fact envelopes.

The extractor extracts Facts only.
It does not determine RuleResult status and does not perform legal compliance judgment.

## Frozen Fact IDs

Exactly 12 PoC1 Fact types exist:

- F1-01
- F1-02
- F1-03
- F1-04
- F1-05
- F1-06
- F1-07
- F1-08
- F1-09
- F1-10
- F1-11
- F1-12

Do not invent additional F1 Fact IDs.

Explicit absence of the entire `ThirdPartyProvision` or
`EntrustedProcessing` activity is carried separately as evidence-backed
`system_metadata.activity_presence=confirmed_false`. It is not F1-05/F1-09
with `value_state=absent`. See `docs/context/backend/N_A_FACT_DECISION_REQUIRED.md`.

## Fact Contract

Every produced Fact must follow the common fact-1.0 envelope documented in:

docs/context/core/CONTRACTS.md

PoC1 extractor output must therefore preserve:

- fact_id
- subject_id
- activity_id
- ontology_class
- ontology_property
- value
- value_state
- source_type
- evidence
- schema_version

## Source Type

PoC1 extracted Facts normally use:

- policy_text

derived may be used only where allowed by the existing frozen Fact contract.

## Activity Scope

F1-11 and F1-12 are global rights-related Facts and are exempt from the normal activity_id requirement.

Other PoC1 Facts must preserve their processing activity scope.

Do not silently substitute subject_id for a missing activity_id.

## Value State

Use only:

- confirmed
- unknown
- absent

The extractor must preserve the distinction between:

- an explicitly confirmed value;
- information that cannot be determined;
- information confirmed to be absent.

Confirmed false is not unknown.

## Evidence

Extracted policy Facts must contain evidence traceable to the supplied policy input.

Do not generate unsupported evidence.

## Mapping

The authoritative Fact-to-ontology mapping is:

app/mapping/mapping_registry.py

Do not duplicate, rename, or reinterpret the mapping in extractor code.

## Frozen Fact Semantics

The authoritative semantic contract for F1-01 through F1-12 remains the existing frozen Fact Dictionary, mapping registry, Rule metadata, and current tests.

When implementation needs the exact ontology class/property or expected value shape for a Fact ID, inspect the existing mapping registry and relevant tests rather than guessing.
