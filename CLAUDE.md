# PIPA Compliance Development Guide

## 1. Project Goal

This repository implements a machine-readable PIPA compliance prototype.

The three PoCs are equal application scenarios:

- PoC1: 개인정보 처리방침 준수점검
- PoC2: 개인정보 침해사고 통지 요건 검토 지원
- PoC3: Privacy-by-Design 개발지원

Do not describe any PoC as Main or Sub.

Current P0 implementation scope:

- PoC1: 6 Rules
- PoC2: 4 Rules
- PoC3: 8 Rules
- Total: 18 Rules

Frozen Facts:

- PoC1: 12
- PoC2: 10
- PoC3: 13
- Total: 35 Facts


## 2. Core Pipeline

The target integration pipeline is:

Input
→ Fact
→ Fact Schema Validation
→ RDF / Ontology Mapping
→ SHACL Validation
→ Applicability
→ P0 Rule Engine
→ RuleResult
→ REST API
→ UI

The REST API is implemented using FastAPI.


## 3. Existing Implementation

Existing ontology, Fact-RDF mapping, SHACL validation, Rule Engine,
and related tests must be reused.

Do not rewrite or replace existing modules unless the task explicitly
requires it and the change is justified by the current implementation contract.

PoC3 already has a structured Fact builder.

PoC1 and PoC2 LLM Fact Extractors may be developed separately.
API and UI work must therefore depend on stable Fact contracts,
not on a specific LLM implementation.


## 4. Source of Truth

Before modifying code, read:

1. this CLAUDE.md
2. docs/context/INDEX.md
3. only the context files assigned to the current task
4. relevant source code files

Do NOT read all PDFs, all docs, or all context files by default.

For implementation truth, prefer the current repository artifacts and
the latest alignment/errata documents over obsolete drafts.

Never invent:

- Fact IDs
- ontology Classes
- ontology Properties
- Rule IDs
- Rule conditions
- legal thresholds
- API fields

If specifications conflict, stop and report the conflict before changing
the frozen contract.


## 5. Critical Domain Rules

- LLMs extract Facts; they do not make final legal judgments.
- Rule evaluation must remain deterministic.
- Missing or unextracted information is not automatically N/A.
- UNKNOWN and ABSENT must remain distinguishable.
- Preserve activity_id and process-centered grouping.
- Preserve Evidence and provenance required by the current contracts.
- Do not implement Enforcement Decree thresholds in P0 Rules.
- Do not automatically determine ReportingObligation unless explicitly
  added to a future approved scope.
- GREEN is not legal compliance certification.
- RED is not confirmation of a legal violation.


## 6. API Development Rule

Extend the existing FastAPI application.

Do not create a second independent backend.

Existing low-level validation endpoints may remain available.

Compliance endpoints should orchestrate existing services rather than
duplicate ontology, mapping, validation, or Rule Engine logic.


## 7. Security Rules

Never:

- commit API keys, tokens, passwords, credentials, or private keys
- hardcode secrets in source code
- commit .env files
- put real secrets in .env.example
- print secrets in application logs
- commit real personal information or real breach data as test fixtures
- disable security checks merely to make a commit succeed

Use environment variables for secrets.

Use synthetic or anonymized test data only.

Before every commit:

1. inspect git status
2. inspect staged filenames
3. inspect git diff --cached
4. verify no secret, credential, or real personal data is staged
5. run the relevant tests
6. run the configured secret scan when available


## 8. Change Discipline

Keep changes task-scoped.

Do not perform unrelated refactoring.

Do not rename frozen Facts, Rules, ontology terms, or API contracts
without explicit approval.

Do not silently change existing passing behavior.

When a task is complete, report:

- files changed
- behavior changed
- tests executed
- test results
- remaining integration dependency
