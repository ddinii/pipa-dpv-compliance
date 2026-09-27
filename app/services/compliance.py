"""Application/service layer for the frozen Fact + OntologyMapper + P0RuleEngine pipeline."""

from __future__ import annotations

from typing import Any

from app.builders.poc3_fact_builder import Poc3FormError, build_poc3_facts
from app.extractors.base import Poc1Extractor, Poc2Extractor
from app.extractors.poc1_mock_extractor import MockPoC1Extractor
from app.extractors.poc2_mock_extractor import MockPoc2Extractor
from app.mapping.fact_schema import FactValidationError
from app.mapping.ontology_mapper import OntologyMapper
from app.rules.engine import P0RuleEngine
from app.rules.models import RuleResult


class ComplianceInputError(ValueError):
    """Raised when compliance API input fails validation before rule evaluation."""


_default_poc1_extractor = MockPoC1Extractor()
_default_poc2_extractor = MockPoc2Extractor()


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


def run_policy_check(
    request: dict[str, Any],
    *,
    extractor: Poc1Extractor | None = None,
) -> list[RuleResult]:
    """Evaluate PoC1 policy text against the frozen PoC1 P0 rules.

    Canonical pipeline: extractor.extract() -> OntologyMapper.map() ->
    P0RuleEngine.evaluate_mapping_result(..., poc="PoC1"). ``extractor``
    defaults to the deterministic ``MockPoC1Extractor`` integration test
    double; a future real LLM extractor can be injected here without any
    other change to this function, the endpoint, or the response contract.
    """
    if not isinstance(request, dict):
        raise ComplianceInputError("PoC1 요청은 JSON 객체여야 함")

    analysis_id = request.get("analysis_id")
    if not isinstance(analysis_id, str) or not analysis_id.strip():
        raise ComplianceInputError("필수 요청 필드 누락: analysis_id")

    controller = request.get("controller")
    if not isinstance(controller, dict):
        raise ComplianceInputError("필수 요청 필드 누락: controller")
    controller_id = controller.get("controller_id")
    if not controller_id:
        raise ComplianceInputError("필수 요청 필드 누락: controller.controller_id")
    controller_name = controller.get("name")

    policy_text = request.get("policy_text")
    if not isinstance(policy_text, str) or not policy_text.strip():
        raise ComplianceInputError("필수 요청 필드 누락: policy_text")

    active_extractor = extractor if extractor is not None else _default_poc1_extractor
    facts = active_extractor.extract(
        analysis_id=analysis_id,
        controller_id=controller_id,
        controller_name=controller_name,
        policy_text=policy_text,
    )

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
    return engine.evaluate_mapping_result(mapping_result, poc="PoC1")


def run_breach_check(
    request: dict[str, Any],
    *,
    extractor: Poc2Extractor | None = None,
) -> list[RuleResult]:
    """Evaluate a PoC2 breach-notification request against the frozen PoC2 P0 rules.

    Canonical pipeline: extractor.extract() -> OntologyMapper.map() ->
    P0RuleEngine.evaluate_mapping_result(..., poc="PoC2"). ``extractor``
    defaults to the deterministic ``MockPoc2Extractor`` integration test
    double; a future real LLM extractor can be injected here without any
    other change to this function, the endpoint, or the response contract.

    For v1, one request represents exactly one incident and zero or one
    notification (docs/context/backend/EXTRACTOR_DECISIONS.md #4).
    """
    if not isinstance(request, dict):
        raise ComplianceInputError("PoC2 요청은 JSON 객체여야 함")

    analysis_id = request.get("analysis_id")
    if not isinstance(analysis_id, str) or not analysis_id.strip():
        raise ComplianceInputError("필수 요청 필드 누락: analysis_id")

    controller = request.get("controller")
    if not isinstance(controller, dict):
        raise ComplianceInputError("필수 요청 필드 누락: controller")
    controller_id = controller.get("controller_id")
    if not controller_id:
        raise ComplianceInputError("필수 요청 필드 누락: controller.controller_id")
    controller_name = controller.get("name")

    incident = request.get("incident")
    if not isinstance(incident, dict):
        raise ComplianceInputError("필수 요청 필드 누락: incident")

    notification = request.get("notification")
    if notification is not None and not isinstance(notification, dict):
        raise ComplianceInputError("notification은 JSON 객체 또는 생략되어야 함")

    active_extractor = extractor if extractor is not None else _default_poc2_extractor
    facts = active_extractor.extract(
        analysis_id=analysis_id,
        controller_id=controller_id,
        controller_name=controller_name,
        incident=incident,
        notification=notification,
    )

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
    return engine.evaluate_mapping_result(mapping_result, poc="PoC2")
