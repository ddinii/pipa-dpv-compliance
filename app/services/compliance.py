"""Application/service layer for the frozen Fact + OntologyMapper + P0RuleEngine pipeline."""

from __future__ import annotations

from typing import Any

from app.builders.poc3_fact_builder import Poc3FormError, build_poc3_facts
from app.extractors.base import ExtractionResult, Poc1Extractor, Poc2Extractor
from app.extractors.selection import default_poc1_extractor, default_poc2_extractor
from app.mapping.fact_schema import FactValidationError
from app.mapping.ontology_mapper import OntologyMapper
from app.mapping.presence_metadata import activity_presence_metadata
from app.rules.engine import P0RuleEngine
from app.rules.models import RuleResult


class ComplianceInputError(ValueError):
    """Raised when compliance API input fails validation before rule evaluation."""


# 기본 Extractor는 PIPA_EXTRACTOR 환경변수가 고른다 (app/extractors/selection.py).
# 기본값은 mock이라 과금 없이 서버가 뜬다. 실제 LLM은 PIPA_EXTRACTOR=llm으로 켠다.
_default_poc1_extractor = default_poc1_extractor()
_default_poc2_extractor = default_poc2_extractor()


def _split_extractor_output(
    output: list[dict[str, Any]] | ExtractionResult,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Accept legacy list extractors and the presence-aware output contract."""

    if isinstance(output, ExtractionResult):
        return output.facts, list(output.system_metadata)
    return output, []


def with_notice_presence(
    presence_metadata: list[dict[str, Any]], *, notification_provided: bool
) -> list[dict[str, Any]]:
    """통지문이 제공되지 않았으면 NotificationNotice 명시적 부재를 붙인다.

    Extractor가 이미 NotificationNotice presence를 냈으면 그것을 따른다.
    평가 러너도 이 함수를 쓴다. 서비스와 러너의 판정 경로가 갈라지면 러너 점수가
    실제 API 동작을 대변하지 못한다.
    """
    has_notice_presence = any(
        item.get("field") == "activity_presence"
        and item.get("activity_type") == "NotificationNotice"
        for item in presence_metadata
    )
    if notification_provided or has_notice_presence:
        return list(presence_metadata)
    return [
        *presence_metadata,
        activity_presence_metadata(
            "NotificationNotice",
            "confirmed_false",
            source_type="derived",
            evidence=[{"field_path": "notification"}],
        ),
    ]


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

    presence_metadata: list[dict[str, Any]] = []
    if "entrusted_processings" in form and form.get("entrusted_processings") == []:
        presence_metadata.append(
            activity_presence_metadata(
                "EntrustedProcessing",
                "confirmed_false",
                source_type="structured_form",
                evidence=[{"field_path": "entrusted_processings"}],
            )
        )

    try:
        mapper = OntologyMapper(
            analysis_id,
            controller_id=controller_id,
            controller_name=controller_name,
        )
        mapping_result = mapper.map(facts, system_metadata=presence_metadata)
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
    extractor_output = active_extractor.extract(
        analysis_id=analysis_id,
        controller_id=controller_id,
        controller_name=controller_name,
        policy_text=policy_text,
    )

    facts, presence_metadata = _split_extractor_output(extractor_output)

    try:
        mapper = OntologyMapper(
            analysis_id,
            controller_id=controller_id,
            controller_name=controller_name,
        )
        mapping_result = mapper.map(facts, system_metadata=presence_metadata)
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
    extractor_output = active_extractor.extract(
        analysis_id=analysis_id,
        controller_id=controller_id,
        controller_name=controller_name,
        incident=incident,
        notification=notification,
    )

    facts, presence_metadata = _split_extractor_output(extractor_output)
    presence_metadata = with_notice_presence(
        presence_metadata, notification_provided=notification is not None
    )

    try:
        mapper = OntologyMapper(
            analysis_id,
            controller_id=controller_id,
            controller_name=controller_name,
        )
        mapping_result = mapper.map(facts, system_metadata=presence_metadata)
    except FactValidationError as exc:
        raise ComplianceInputError(str(exc)) from exc

    engine = P0RuleEngine()
    return engine.evaluate_mapping_result(mapping_result, poc="PoC2")
