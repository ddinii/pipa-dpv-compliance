"""Provider-independent PoC1/PoC2 Fact extractor boundary.

The compliance service depends on this abstraction, not on a specific
extraction implementation. A future real LLM-backed extractor can implement
``Poc1Extractor``/``Poc2Extractor`` without changing the respective endpoint
contract, ``OntologyMapper``, ``P0RuleEngine``, the ``RuleResult`` response
shape, or frontend integration. See
docs/context/backend/EXTRACTOR_INTEGRATION.md.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, TypeAlias


@dataclass
class ExtractionResult:
    """Extractor output without mixing applicability metadata into Facts."""

    facts: list[dict[str, Any]]
    system_metadata: list[dict[str, Any]] = field(default_factory=list)


ExtractorOutput: TypeAlias = list[dict[str, Any]] | ExtractionResult


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
    ) -> ExtractorOutput:
        ...


class Poc2Extractor(Protocol):
    """Produces frozen F2-01..F2-10 Fact envelopes from PoC2 breach input.

    Implementations must emit ``fact-1.0`` envelopes that pass
    ``app.mapping.fact_schema.validate_facts()`` unchanged. An extractor must
    not evaluate P0 Rules, assign RuleStatus, decide reportability, or invent
    a NotificationNotice when ``notification`` is not provided.
    """

    def extract(
        self,
        *,
        analysis_id: str,
        controller_id: str,
        controller_name: str | None,
        incident: dict[str, Any],
        notification: dict[str, Any] | None,
    ) -> ExtractorOutput:
        ...
