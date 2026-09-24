# Backend Integration

## Goal

Expose the existing frozen compliance pipeline through REST endpoints implemented with the existing FastAPI application.

Do not create a second FastAPI app.

## Target Endpoints

Planned compliance endpoints:

POST /api/v1/compliance/policy-check
POST /api/v1/compliance/breach-check
POST /api/v1/compliance/design-check

Recommended metadata endpoint:

GET /api/v1/rules

Implementation order may begin with design-check because PoC3 already has a deterministic structured-form Fact builder.

This implementation order does not imply that PoC3 has higher project priority than PoC1 or PoC2.

## PoC3 Integration

Target endpoint:

POST /api/v1/compliance/design-check

Canonical call chain:

HTTP request
→ application/service layer
→ build_poc3_facts()
→ OntologyMapper.map()
→ P0RuleEngine.evaluate_mapping_result(..., poc="PoC3")
→ RuleResult serialization
→ HTTP response

## Layering

FastAPI route responsibilities:

- receive and validate HTTP input
- call application/service layer
- translate expected application/input errors to suitable HTTP errors
- return response

Route functions must not contain:

- Rule evaluation logic
- Fact-to-RDF mapping logic
- duplicated frozen Fact construction
- duplicated legal-rule metadata

Application/service responsibilities:

- orchestrate existing modules
- preserve frozen contracts
- return deterministic results

## Reuse

Reuse existing:

- build_poc3_facts
- OntologyMapper
- P0RuleEngine
- RuleResult.to_dict()
- rules/p0_rules.json metadata

Do not duplicate these implementations.

## Legacy Compatibility

Preserve:

GET /health
POST /api/v1/validate

The new compliance router may coexist with the existing validation router.

Do not remove or rewrite the legacy endpoint merely to implement the new compliance API.

## Error Handling

Malformed PoC3 form input must produce a client error rather than an internal server error.

Expected domain/input errors such as Poc3FormError and FactValidationError should be handled at an appropriate boundary.

Do not expose Python stack traces, secrets, environment variables, or internal filesystem paths in HTTP responses.

## Security

Never:

- hardcode API keys or credentials
- log secrets
- include real personal information in fixtures
- commit .env
- weaken existing Fact validation to make API input pass

Use synthetic/anonymized development fixtures.

## Testing

Add focused API/integration tests for the new endpoint.

At minimum verify:

1. the existing SC-D01 example can traverse the endpoint;
2. the response contains exactly the 8 frozen PoC3 Rule IDs;
3. RuleResult status/applicability values are preserved;
4. malformed required form input returns a client error;
5. existing legacy endpoints are not broken;
6. the complete existing test suite still passes.

Do not rewrite existing tests merely to make a regression disappear.
