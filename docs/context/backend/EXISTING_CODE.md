# Existing Backend Code

## Framework

The backend uses FastAPI.

Extend the existing FastAPI application.

Do not create a second backend application.

## Existing Legacy API

The repository currently has a legacy validation endpoint:

POST /api/v1/validate

It uses the older ProcessingFact / SHACL validation prototype.

Preserve it unless explicitly asked to remove it.

The new compliance endpoints must use the frozen Fact + OntologyMapper + P0RuleEngine pipeline instead.

## Existing Reusable Modules

### Fact validation

app/mapping/fact_schema.py

Important API:

validate_facts(raw_facts)

Responsibilities:
- validate frozen Fact envelope
- derive fact_type from fact_id
- validate value_state
- validate source_type
- validate evidence
- enforce activity scope
- enforce fact-1.0

### Fact-to-ontology registry

app/mapping/mapping_registry.py

Important object:

FACT_SPECS

Contains the frozen F1/F2/F3 Fact-to-ontology mapping contract.

Do not duplicate or replace it.

### Ontology mapper

app/mapping/ontology_mapper.py

Important classes:

OntologyMapper
MappingResult

Typical usage:

mapper = OntologyMapper(
    analysis_id=...,
    controller_id=...,
    controller_name=...,
)

mapping_result = mapper.map(facts)

MappingResult provides:
- graph
- facts
- system_metadata
- trace

### PoC3 Fact builder

app/builders/poc3_fact_builder.py

Important API:

build_poc3_facts(form)

Exception:

Poc3FormError

It converts the structured PoC3 form into F3-01 through F3-13 Fact envelopes.

Reuse it. Do not rebuild PoC3 Fact construction inside an API route.

### Deterministic P0 Rule Engine

app/rules/engine.py

Important class:

P0RuleEngine

Preferred integration API:

evaluate_mapping_result(mapping_result, poc=...)

Supported frozen rules:

PoC1:
P1-R01, P1-R02, P1-R03, P1-R04, P1-R06, P1-R07

PoC2:
P2-R01, P2-R02, P2-R03, P2-R08

PoC3:
P3-R01, P3-R02, P3-R03, P3-R04, P3-R05, P3-R06, P3-R08, P3-R11

### Rule metadata

app/rules/metadata.py

Metadata source:

rules/p0_rules.json

Use the existing loader instead of hardcoding duplicate metadata.

### Rule result model

app/rules/models.py

Important types:

- RuleStatus
- Applicability
- Evidence
- InstanceRuleResult
- RuleResult

RuleResult.to_dict() provides serialization-friendly output.

## Existing Legacy Modules

These belong to the earlier prototype path:

- app/models/request.py
- app/models/response.py
- app/services/rdf_mapper.py
- app/services/validator.py
- app/services/result_builder.py
- app/services/rule_loader.py

Do not confuse these with the canonical frozen Fact/P0 Rule integration path.

Do not delete them during new API integration.

## Integration Principle

API routes should be thin.

Prefer:

route
→ application/service function
→ existing builder/extractor
→ OntologyMapper
→ P0RuleEngine
→ response serialization

Do not place ontology mapping or Rule logic directly inside FastAPI route functions.
