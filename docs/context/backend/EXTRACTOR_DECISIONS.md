# Extractor Integration Decisions

Status: Frozen for the current PoC1/PoC2 integration phase.

## 1. Frozen contract remains unchanged

Do not add or rename:
- Frozen Facts
- ontology classes/properties
- Rule IDs
- Rule conditions

The current scope remains:
- PoC1: F1-01..F1-12 / 6 P0 Rules
- PoC2: F2-01..F2-10 / 4 P0 Rules
- PoC3: F3-01..F3-13 / 8 P0 Rules

Do not introduce a new Fact or ontology mapping solely to represent
confirmed absence of an optional processing category.

Do not invent a new Fact or core ontology term. Explicit absence of one of the
approved conditional activities is represented as validated system metadata,
not as a Fact.

## 2. PoC2 non-rule Facts

F2-05, F2-06, and F2-07 remain valid Frozen Facts even though the
current four PoC2 P0 Rules do not directly consume them.

Extract them when supported by the input.

Do not invent their values when the input does not provide them.

In particular:
- F2-05 = actual incidentDate
- F2-08 = incident time as stated in the notification

F2-08 must never be derived from F2-05.

## 3. API envelope

PoC1 and PoC2 use the same top-level identity envelope pattern as PoC3:

- analysis_id
- controller.controller_id
- controller.name

PoC1 additionally receives policy_text.

PoC2 receives:
- incident
- optional notification

## 4. PoC2 request cardinality

For v1, one breach-check request represents:

- exactly one incident
- zero or one notification

Do not implement batch/multi-incident request handling in this phase.

## 5. Extractor boundary

The service/API must depend on a provider-independent extractor
interface.

Current development uses deterministic synthetic-data mock extractors.

Mock extractors:
- are integration test doubles
- are not LLM simulators
- are not extraction-quality evidence
- must not infer legal conclusions
- must not invent unsupported Facts
- must not evaluate Rules

A future real LLM extractor must be swappable without changing:
- REST endpoint contracts
- OntologyMapper
- P0RuleEngine
- RuleResult response contract
- frontend integration

## 6. PoC2 notification absence

A missing notification must never cause the extractor to fabricate a
NotificationNotice.

F2-03 property absence remains in the Frozen Fact state contract. The absence
of the entire notification input is separately represented as
`NotificationNotice=confirmed_false` activity-presence metadata. P2-R01 stays
RED, while P2-R02 and P2-R03 become N/A. This distinction is verified through
the service pipeline.

## 7. Error boundary

Do not introduce provider-specific LLM/network/timeout error taxonomy
during the mock integration phase.

Expected malformed request/extraction input may become a client-facing
4xx through the compliance service boundary.

Unexpected internal/programming errors must not be silently converted
into client input errors.

Provider-specific operational errors are deferred until the real LLM
extractor is integrated.
