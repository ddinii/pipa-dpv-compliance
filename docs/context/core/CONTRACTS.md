# Frozen Contracts

## Fact Envelope

Every frozen Fact uses the common fact-1.0 envelope.

Required fields:

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

## Value State

Allowed values:

- confirmed
- unknown
- absent

These states are semantically different.

Do not convert:
- false to unknown
- false to absent
- unknown to absent
- absent to unknown

Confirmed false is a valid confirmed value.

## Evidence

evidence must be a non-empty array.

Each evidence item must contain at least one of:

- text
- field_path
- offset

## Schema Version

Fact schema_version:

fact-1.0

## Source Types

Allowed source types:

- policy_text
- incident_record
- notification_notice
- structured_form
- derived

Expected PoC sources:

PoC1:
- policy_text
- derived

PoC2 incident Facts:
- incident_record
- derived

PoC2 notice Facts:
- notification_notice
- derived

PoC3:
- structured_form
- derived

## Activity Scope

Except for global PoC1 rights Facts F1-11 and F1-12, frozen Facts must retain activity_id.

Do not silently replace a missing activity_id with subject_id.

## Mapping Contract

Ontology mapping is frozen through FACT_SPECS.

Do not invent ontology classes, ontology properties, or mapping kinds.

Unknown and absent Facts are validated and retained but are not emitted as confirmed RDF assertions.

## Activity Presence Metadata

Conditional activity presence is not a frozen Fact value. It is carried in
`MappingResult.system_metadata` as:

- `field`: `activity_presence`
- `activity_type`: `ThirdPartyProvision`, `EntrustedProcessing`, or `NotificationNotice`
- `state`: `confirmed_true`, `confirmed_false`, or `unknown`
- `source_type`: one of the frozen source types
- `evidence`: non-empty traceable evidence

`value_state=absent` on a frozen Fact means that a property value is absent
from an activity. It must never be used to mean that the activity itself does
not exist. Only evidence-backed `activity_presence=confirmed_false` makes the
five conditional Rules P1-R03, P1-R06, P2-R02, P2-R03, and P3-R11 N/A.

This technical metadata does not add a Fact ID or a core ontology property;
therefore the Fact/Ontology version remains v1.0.

## RuleResult

Canonical deterministic RuleResult contains:

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
- instance_results
- implementation_notes

Rule status:

- GREEN
- AMBER
- RED
- N/A

Applicability:

- TRUE
- FALSE
- UNKNOWN

## Rule Metadata

Rule metadata comes from:

rules/p0_rules.json

Do not duplicate Rule IDs, legal bases, applicability text, required Fact IDs, or ontology terms in a second independent source unless required for API serialization.

## PoC2 Boundary

P2-R01 uses:

- F2-01
- F2-02
- F2-03

It does not use or create triggersNotificationObligation.

P2-R01 does not automatically determine whether an incident is legally subject to notification.

Do not add notification/reporting thresholds to the frozen v1 rule.
