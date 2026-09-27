# Project Context

## Project

PIPA-DPV Compliance Prototype is a PoC for representing selected Personal Information Protection Act (PIPA) compliance requirements in a machine-readable form and evaluating supplied facts with deterministic rules.

The system is not a legal compliance certification system.

- GREEN does not mean that an organization is legally compliant.
- RED does not by itself establish a confirmed legal violation.
- Rule results are decision-support outputs based on the implemented P0 rules and supplied facts.

## Three Equal PoCs

The project contains three equal PoCs. Do not describe them as Main/Sub.

### PoC1 — 개인정보 처리방침 준수점검

Input:
- privacy policy text

Processing:
- extractor produces frozen Fact envelopes
- deterministic rules evaluate the Facts

Frozen scope:
- 12 Fact types: F1-01 through F1-12
- 6 P0 Rules:
  - P1-R01
  - P1-R02
  - P1-R03
  - P1-R04
  - P1-R06
  - P1-R07

### PoC2 — 개인정보 침해사고 통지 요건 검토 지원

Input:
- incident information
- existing notification/response information

Frozen scope:
- 10 Fact types: F2-01 through F2-10
- 4 P0 Rules:
  - P2-R01
  - P2-R02
  - P2-R03
  - P2-R08

Important:
- incident facts and notification facts are distinct.
- incident.affectsPersonalInformation is not notice.mentionsPersonalInformation.
- incidentDate is not notice_incident_time.
- v1 does not automatically determine ReportingObligation.
- notification/reporting thresholds are outside the v1 P0 scope.
- v1 does not automatically generate a notification notice.

### PoC3 — Privacy-by-Design 개발지원

Input:
- structured Privacy-by-Design form

Processing:
- deterministic form builder produces frozen Facts
- no LLM extraction is required

Frozen scope:
- 13 Fact types: F3-01 through F3-13
- 8 P0 Rules:
  - P3-R01
  - P3-R02
  - P3-R03
  - P3-R04
  - P3-R05
  - P3-R06
  - P3-R08
  - P3-R11

## Frozen Counts

- PoC1: 12 Facts / 6 Rules
- PoC2: 10 Facts / 4 Rules
- PoC3: 13 Facts / 8 Rules
- Total: 35 Fact types / 18 P0 Rules

Do not add, remove, rename, or reinterpret frozen Fact IDs or Rule IDs unless explicitly requested.

## Legal Scope

The normative P0 Rule source is the PIPA Act body for the frozen specification.

Do not introduce Enforcement Decree thresholds or other legal thresholds into P0 rules unless explicitly requested as a later scope expansion.

## LLM Boundary

LLMs may extract Facts from unstructured input.

LLMs must not replace deterministic legal rule evaluation.

Target architecture:

Input
→ Fact extraction/building
→ Fact validation
→ ontology mapping
→ deterministic P0 Rule Engine
→ RuleResult
→ REST API
→ UI
