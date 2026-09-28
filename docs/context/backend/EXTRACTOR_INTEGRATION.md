# Extractor Integration Contract

## Purpose

PoC1 and PoC2 API development must not depend directly on a specific LLM provider or model.

The compliance pipeline consumes frozen Fact envelopes.

The extractor is an interchangeable Fact-producing boundary.

## Architectural Boundary

PoC1:

policy input
→ PoC1 extractor
→ ExtractionResult(Frozen F1 Fact[], system metadata)
→ existing mapping/evaluation pipeline

PoC2:

incident + notification input
→ PoC2 extractor
→ ExtractionResult(Frozen F2 Fact[], system metadata)
→ existing mapping/evaluation pipeline

The API and Rule Engine must not know whether Facts came from:

- a mock extractor;
- an LLM extractor;
- another future extraction implementation.

## Extractor Responsibility

An extractor may:

- parse source input;
- identify information relevant to frozen Facts;
- create frozen Fact envelopes;
- assign value_state according to the extraction contract;
- attach source evidence and provenance.

An extractor must not:

- evaluate P0 Rules;
- assign RuleStatus;
- decide legal compliance;
- modify ontology mappings;
- invent Fact IDs;
- invent Rule IDs;
- introduce legal thresholds outside frozen scope.

## Output Contract

Extractor output is either a legacy `list[dict]` or
`ExtractionResult(facts, system_metadata)`. New extractors should use
`ExtractionResult` whenever they can confirm the absence of a conditional
activity.

Extractor output must pass the existing:

validate_facts(...)

contract before deterministic evaluation.

Do not create a second competing Fact schema.

Activity absence metadata must pass `validate_system_metadata(...)`. It must
not be encoded by changing a property Fact to `value_state=absent`.

## Provider Independence

Application/service code must depend on an extractor abstraction/protocol, not directly on:

- Anthropic
- OpenAI
- Gemini
- a specific model name
- an SDK-specific response object

Provider-specific implementation belongs behind the extractor boundary.

## Current Development Strategy

Until the real PoC1/PoC2 LLM extractors are ready:

- use deterministic mock/stub extractors only for API integration tests;
- use synthetic inputs and synthetic Fact outputs;
- do not pretend mock extraction demonstrates LLM extraction quality.

The mock exists only to validate:

HTTP/API
→ extractor boundary
→ frozen Facts
→ OntologyMapper
→ P0RuleEngine
→ RuleResult

## Future Replacement

A future real extractor should be replaceable without changing:

- REST endpoint paths;
- Rule Engine;
- ontology mapping;
- frozen Fact contract;
- frontend RuleResult handling.

Only extractor construction/configuration and provider-specific implementation should need replacement.

## Error Boundary

Expected extractor input/output validation failures should become controlled application errors.

Unexpected provider/internal/programming failures must not be silently reclassified as ordinary user input errors.

Do not expose provider credentials, raw stack traces, or sensitive internal details in API responses.

## Security

Never put provider API keys in:

- source files;
- tests;
- fixtures;
- committed JSON;
- committed Markdown.

Credentials must come from environment/configuration outside version control.

Do not use real personal information or real breach records in development fixtures.
