# Context Index

This directory provides task-scoped context for Claude.

## Rule

Do not load every context file.

For each task:

1. read CLAUDE.md
2. find the task below
3. read only the listed context files
4. inspect only the source files required for that task

If additional context is genuinely required, explain why before expanding scope.


## Project / Architecture

Task: understand the overall project
Read:
- core/PROJECT.md
- core/PIPELINE.md

Task: understand shared Fact / RuleResult / API contracts
Read:
- core/CONTRACTS.md
- core/PIPELINE.md


## Security

Task: Git, secrets, environment variables, deployment configuration, logging
Read:
- core/SECURITY.md


## PoC1

Task: PoC1 Fact handling or extractor integration
Read:
- poc1/FACTS.md
- poc1/REQUIREMENTS.md
- core/CONTRACTS.md

Task: PoC1 Rule/API integration
Read:
- poc1/RULES.md
- poc1/REQUIREMENTS.md
- core/PIPELINE.md
- core/CONTRACTS.md

Task: PoC1 UI
Read:
- poc1/REQUIREMENTS.md
- frontend/REQUIREMENTS.md
- core/CONTRACTS.md


## PoC2

Task: PoC2 Fact handling or extractor integration
Read:
- poc2/FACTS.md
- poc2/REQUIREMENTS.md
- core/CONTRACTS.md

Task: PoC2 Rule/API integration
Read:
- poc2/RULES.md
- poc2/REQUIREMENTS.md
- core/PIPELINE.md
- core/CONTRACTS.md

Task: PoC2 UI
Read:
- poc2/REQUIREMENTS.md
- frontend/REQUIREMENTS.md
- core/CONTRACTS.md


## PoC3

Task: PoC3 Form-to-Fact integration
Read:
- poc3/FACTS.md
- poc3/REQUIREMENTS.md
- core/CONTRACTS.md

Task: PoC3 Rule/API integration
Read:
- poc3/RULES.md
- poc3/REQUIREMENTS.md
- core/PIPELINE.md
- core/CONTRACTS.md

Task: PoC3 UI
Read:
- poc3/REQUIREMENTS.md
- frontend/REQUIREMENTS.md
- core/CONTRACTS.md


## Backend

Task: existing backend architecture
Read:
- backend/EXISTING_CODE.md
- core/PIPELINE.md

Task: FastAPI compliance endpoint integration
Read:
- backend/EXISTING_CODE.md
- backend/INTEGRATION.md
- core/CONTRACTS.md
- core/PIPELINE.md

Do not read all three PoC documents unless the endpoint task actually
covers all three PoCs.

Task: PoC1/PoC2 real (non-mock) LLM extractor integration
Read:
- backend/LLM_EXTRACTOR_HANDOFF.md
- core/CONTRACTS.md

Read the PoC-specific FACTS.md/RULES.md only if the handoff document's
minimum field/ID summary is insufficient.


## Frontend

Task: frontend foundation or shared result components
Read:
- frontend/REQUIREMENTS.md
- core/CONTRACTS.md

Then read only the REQUIREMENTS.md for the PoC currently being implemented.


## Testing

Task: regression or E2E testing
Read:
- testing/ACCEPTANCE.md
- core/PIPELINE.md

Then read only the PoC-specific RULES.md and REQUIREMENTS.md required
by the test.


## Original Detailed Documents

The existing files under docs/ and the frozen specifications are detailed
reference material.

Open them only when the task-scoped context is insufficient or when
verifying an exact mapping, Rule, ontology term, or erratum.

Do not routinely load all original documents.
