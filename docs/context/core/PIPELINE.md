# Runtime Pipeline

## Canonical Integration Pipeline

New compliance API work must use the frozen Fact + OntologyMapper + P0RuleEngine path.

PoC input
→ PoC-specific Fact producer
→ Fact envelope validation
→ OntologyMapper
→ MappingResult
→ P0RuleEngine
→ RuleResult[]
→ REST API response
→ frontend

## PoC1

Policy text
→ PoC1 extractor
→ F1 Facts
→ validate_facts()
→ OntologyMapper.map()
→ P0RuleEngine.evaluate_mapping_result(..., poc="PoC1")
→ 6 RuleResults

The real LLM extractor may be integrated later.

API/UI code must depend on a stable Fact-producing interface rather than a specific LLM provider.

## PoC2

Incident + existing notification/response input
→ PoC2 extractor
→ F2 Facts
→ validate_facts()
→ OntologyMapper.map()
→ P0RuleEngine.evaluate_mapping_result(..., poc="PoC2")
→ 4 RuleResults

The real LLM extractor may be integrated later.

Do not collapse incident facts and notification facts.

## PoC3

Structured PbD form
→ build_poc3_facts()
→ F3 Facts
→ validate_facts()
→ OntologyMapper.map()
→ P0RuleEngine.evaluate_mapping_result(..., poc="PoC3")
→ 8 RuleResults

PoC3 does not require an LLM extractor.

## MappingResult

OntologyMapper.map() returns:

- graph
- facts
- system_metadata
- trace

The normalized Facts must be preserved because RDF contains confirmed assertions only.

Unknown and absent Facts must survive outside the RDF graph so the Rule Engine can distinguish their states.

## Rule Evaluation

Use:

P0RuleEngine.evaluate_mapping_result(mapping_result, poc=...)

when a MappingResult is available.

Do not discard mapping_result.facts and evaluate only the RDF graph in the canonical integration path.

## Legacy Path

The repository also contains an older prototype path based on:

ProcessingFact
→ processing_fact_to_graph()
→ SHACL validate_graph()
→ build_result()

This path currently supports the older validation prototype.

Do not use this legacy path as the architecture for the new three-PoC compliance endpoints.

Do not delete or refactor the legacy path unless explicitly requested.
