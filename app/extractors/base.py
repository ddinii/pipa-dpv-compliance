"""Provider-independent PoC1 Fact extractor boundary.

The compliance service depends on this abstraction, not on a specific
extraction implementation. A future real LLM-backed extractor can implement
``Poc1Extractor`` without changing the policy-check endpoint contract,
``OntologyMapper``, ``P0RuleEngine``, the ``RuleResult`` response shape, or
frontend integration. See docs/context/backend/EXTRACTOR_INTEGRATION.md.
"""

from __future__ import annotations

from typing import Any, Protocol


class Poc1Extractor(Protocol):
    """Produces frozen F1-01..F1-12 Fact envelopes from PoC1 policy input.

    Implementations must emit ``fact-1.0`` envelopes that pass
    ``app.mapping.fact_schema.validate_facts()`` unchanged. An extractor must
    not evaluate P0 Rules, assign RuleStatus, or make legal judgments.
    """

    def extract(
        self,
        *,
        analysis_id: str,
        controller_id: str,
        controller_name: str | None,
        policy_text: str,
    ) -> list[dict[str, Any]]:
        ...
