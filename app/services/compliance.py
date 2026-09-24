"""Application/service layer for the frozen Fact + OntologyMapper + P0RuleEngine pipeline."""

from __future__ import annotations

from typing import Any

from app.builders.poc3_fact_builder import Poc3FormError, build_poc3_facts
from app.mapping.fact_schema import FactValidationError
from app.mapping.ontology_mapper import OntologyMapper
from app.rules.engine import P0RuleEngine
from app.rules.models import RuleResult


class ComplianceInputError(ValueError):
    """Raised when compliance API input fails validation before rule evaluation."""


def run_design_check(form: dict[str, Any]) -> list[RuleResult]:
    """Evaluate a PoC3 structured design form against the frozen PoC3 P0 rules.

    Canonical pipeline: build_poc3_facts() -> OntologyMapper.map() ->
    P0RuleEngine.evaluate_mapping_result(..., poc="PoC3").
    """
    if not isinstance(form, dict):
        raise ComplianceInputError("PoC3 Form은 JSON 객체여야 함")

    controller = form.get("controller")
    if not isinstance(controller, dict):
        raise ComplianceInputError("필수 Form 필드 누락: controller")
    controller_id = controller.get("controller_id")
    if not controller_id:
        raise ComplianceInputError("필수 Form 필드 누락: controller.controller_id")
    controller_name = controller.get("name")

    analysis_id = form.get("analysis_id")
    if not isinstance(analysis_id, str) or not analysis_id.strip():
        raise ComplianceInputError("필수 Form 필드 누락: analysis_id")

    try:
        facts = build_poc3_facts(form)
    except Poc3FormError as exc:
        raise ComplianceInputError(str(exc)) from exc

    try:
        mapper = OntologyMapper(
            analysis_id,
            controller_id=controller_id,
            controller_name=controller_name,
        )
        mapping_result = mapper.map(facts)
    except FactValidationError as exc:
        raise ComplianceInputError(str(exc)) from exc

    engine = P0RuleEngine()
    return engine.evaluate_mapping_result(mapping_result, poc="PoC3")
