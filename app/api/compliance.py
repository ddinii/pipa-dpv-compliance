from typing import Any, Literal

from fastapi import APIRouter, Body, HTTPException
from pydantic import BaseModel

from app.rules.metadata import load_rule_profile
from app.rules.models import Applicability, RuleStatus
from app.services.compliance import (
    ComplianceInputError,
    run_breach_check,
    run_design_check,
    run_policy_check,
)


router = APIRouter(
    prefix="/api/v1/compliance",
    tags=["compliance"],
)


class EvidenceResponse(BaseModel):
    """Mirrors app.rules.models.Evidence as serialized by RuleResult.to_dict()."""

    evidence_type: str
    subject: str | None = None
    predicate: str | None = None
    value: str | bool | None = None
    source_text: str | None = None
    note: str | None = None


class InstanceRuleResultResponse(BaseModel):
    """Mirrors app.rules.models.InstanceRuleResult as serialized by RuleResult.to_dict()."""

    instance_id: str
    status: RuleStatus
    applicability: Applicability
    matched_facts: list[str] = []
    missing_facts: list[str] = []
    uncertain_facts: list[str] = []
    evidence: list[EvidenceResponse] = []
    reason: str = ""
    recommendation: str = ""


class RuleResultResponse(BaseModel):
    """Mirrors app.rules.models.RuleResult.to_dict() exactly (field-for-field)."""

    rule_id: str
    rule_version: str
    status: RuleStatus
    applicability: Applicability
    matched_facts: list[str]
    missing_facts: list[str]
    uncertain_facts: list[str]
    evidence: list[EvidenceResponse]
    legal_basis: list[str]
    reason: str
    recommendation: str
    evaluated_at: str
    # 기능명세서 8장 필수 필드. RuleResult.to_dict()에는 없으므로 API 계층이
    # 입력 추적 ID로 채운다 (COM-001 · NFR-04 · TST-010).
    source_document_id: str
    instance_results: list[InstanceRuleResultResponse] = []
    implementation_notes: list[str] = []


class ComplianceResponse(BaseModel):
    """기능명세서 9.1 공통 API 응답 봉투.

    세 endpoint가 같은 봉투를 쓴다. 버전 3종과 analysis_id는 COM-011 · NFR-04 ·
    TST-010이 요구하는 추적 정보다.
    """

    analysis_id: str
    poc: Literal["PoC1", "PoC2", "PoC3"]
    ontology_version: str
    rule_version: str
    fact_schema_version: str
    results: list[RuleResultResponse]


def _envelope(
    poc: str, analysis_id: str, results: list[Any]
) -> dict[str, Any]:
    """RuleResult 목록을 9.1 봉투에 담는다.

    source_document_id는 입력 추적 ID이므로 요청의 analysis_id를 그대로 쓴다
    (COM-001: 각 분석 요청마다 source_document_id 또는 scenario_id를 생성한다).
    """
    profile = load_rule_profile()
    return {
        "analysis_id": analysis_id,
        "poc": poc,
        "ontology_version": profile["ontology_version"],
        "rule_version": profile["rule_version"],
        "fact_schema_version": profile["fact_schema_version"],
        "results": [
            {**result.to_dict(), "source_document_id": analysis_id} for result in results
        ],
    }


def _analysis_id(payload: dict[str, Any]) -> str:
    value = payload.get("analysis_id") if isinstance(payload, dict) else None
    return value if isinstance(value, str) and value.strip() else ""


@router.post("/design-check", response_model=ComplianceResponse)
def design_check(
    form: dict[str, Any] = Body(...),
) -> dict[str, Any]:
    try:
        results = run_design_check(form)
    except ComplianceInputError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return _envelope("PoC3", _analysis_id(form), results)


@router.post("/policy-check", response_model=ComplianceResponse)
def policy_check(
    request: dict[str, Any] = Body(...),
) -> dict[str, Any]:
    try:
        results = run_policy_check(request)
    except ComplianceInputError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return _envelope("PoC1", _analysis_id(request), results)


@router.post("/breach-check", response_model=ComplianceResponse)
def breach_check(
    request: dict[str, Any] = Body(...),
) -> dict[str, Any]:
    try:
        results = run_breach_check(request)
    except ComplianceInputError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return _envelope("PoC2", _analysis_id(request), results)
