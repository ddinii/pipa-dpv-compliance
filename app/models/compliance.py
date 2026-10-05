"""Compliance API 응답 DTO.

기능명세서 8장 RuleResult와 9.1 공통 응답의 타입 정의다.
"필드명은 구현 과정에서 임의 변경하지 말고 변경 시 Rule/Fact 담당자와 합의한다"(8장)이므로
여기가 그 계약의 단일 지점이다.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

RuleStatusOut = Literal["GREEN", "YELLOW", "RED", "N/A"]
ApplicabilityOut = Literal["TRUE", "FALSE", "UNKNOWN"]


class EvidenceOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    evidence_type: str = Field(description="source_text | rdf_assertion | absence")
    subject: str | None = None
    predicate: str | None = None
    value: Any | None = None
    source_text: str | None = None
    note: str | None = None


class InstanceResultOut(BaseModel):
    """COM-012: 같은 유형 activity가 여러 개면 인스턴스별 결과를 유지한다."""

    model_config = ConfigDict(extra="forbid")

    instance_id: str
    status: RuleStatusOut
    applicability: ApplicabilityOut
    matched_facts: list[str] = Field(default_factory=list)
    missing_facts: list[str] = Field(default_factory=list)
    uncertain_facts: list[str] = Field(default_factory=list)
    evidence: list[EvidenceOut] = Field(default_factory=list)
    reason: str = ""
    recommendation: str = ""


class RuleResultOut(BaseModel):
    """기능명세서 8장 RuleResult."""

    model_config = ConfigDict(extra="forbid")

    rule_id: str
    rule_version: str
    status: RuleStatusOut
    applicability: ApplicabilityOut
    matched_facts: list[str]
    missing_facts: list[str]
    uncertain_facts: list[str]
    evidence: list[EvidenceOut]
    legal_basis: list[str]
    reason: str
    recommendation: str
    evaluated_at: str
    instance_results: list[InstanceResultOut] = Field(default_factory=list)
    implementation_notes: list[str] = Field(default_factory=list)

    # 8장은 RuleResult마다 source_document_id를 요구한다. Rule Engine의 RuleResult에는
    # 아직 이 필드가 없어 API 계층에서 채운다. 엔진 DTO에 추가할지는 Day 0 안건이다.
    source_document_id: str | None = None


class ComplianceResponse(BaseModel):
    """기능명세서 9.1 공통 API 응답."""

    model_config = ConfigDict(extra="forbid")

    analysis_id: str
    poc: str
    ontology_version: str
    rule_version: str
    fact_schema_version: str
    source_document_id: str | None = None
    results: list[RuleResultOut]


class FactIssueOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    index: int
    fact_id: str | None = None
    message: str


class FactValidationErrorOut(BaseModel):
    """COM-002 검증 실패. 임의 보완 없이 무엇이 잘못됐는지 그대로 돌려준다."""

    model_config = ConfigDict(extra="forbid")

    detail: str
    issues: list[FactIssueOut]
