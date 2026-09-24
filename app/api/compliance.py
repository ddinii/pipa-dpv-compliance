from typing import Any, Literal

from fastapi import APIRouter, Body, HTTPException
from pydantic import BaseModel

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
    instance_results: list[InstanceRuleResultResponse] = []
    implementation_notes: list[str] = []


class ComplianceResponse(BaseModel):
    """Common successful response envelope for all three compliance endpoints."""

    poc: Literal["PoC1", "PoC2", "PoC3"]
    rule_results: list[RuleResultResponse]


@router.post("/design-check", response_model=ComplianceResponse)
def design_check(
    form: dict[str, Any] = Body(...),
) -> dict[str, Any]:
    try:
        results = run_design_check(form)
    except ComplianceInputError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return {
        "poc": "PoC3",
        "rule_results": [result.to_dict() for result in results],
    }


@router.post("/policy-check", response_model=ComplianceResponse)
def policy_check(
    request: dict[str, Any] = Body(...),
) -> dict[str, Any]:
    try:
        results = run_policy_check(request)
    except ComplianceInputError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return {
        "poc": "PoC1",
        "rule_results": [result.to_dict() for result in results],
    }


@router.post("/breach-check", response_model=ComplianceResponse)
def breach_check(
    request: dict[str, Any] = Body(...),
) -> dict[str, Any]:
    try:
        results = run_breach_check(request)
    except ComplianceInputError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return {
        "poc": "PoC2",
        "rule_results": [result.to_dict() for result in results],
    }
