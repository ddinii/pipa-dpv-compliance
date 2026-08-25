"""
PIPA-DPV Compliance Engine — 데이터 모델 정의

개인정보 처리방침에서 추출되는 '사실(Fact)'의 구조를 정의합니다.
이 구조는 온톨로지(PIPA-DPV Semantic Profile)의 클래스와 1:1로 매핑되도록 설계되었습니다.

각 필드는 ontology/pipa_dpv_classes.ttl 의 클래스와 대응됩니다:
  - purpose                       <-> dpv:Purpose
  - collection_items              <-> dpv:PersonalData
  - retention_period              <-> dpv:Retention
  - third_party_provision         <-> dpv:ThirdPartyProvision
  - outsourcing                   <-> legal-kr:Outsourcing (처리위탁)
  - destruction_procedure         <-> dpv:Destruction
  - cross_border_transfer         <-> dpv:CrossBorderTransfer
  - consent_withdrawal            <-> dpv:Consent (철회 관련)
  - data_subject_rights           <-> dpv:DataSubjectRight
  - privacy_officer               <-> legal-kr:PrivacyOfficer (개인정보보호책임자)
  - auto_collection_device        <-> legal-kr:AutoCollectionDevice (쿠키 등)
  - sensitive_data_disclosure_method <-> legal-kr:SensitiveDataDisclosureChoice
  - pseudonymized_data_processing <-> legal-kr:PseudonymizedDataProcessing

NOTE: 조문 번호(legal_basis)는 2026-08-26 국가법령정보센터·casenote.kr 대조로
      검증되었습니다 (개인정보 보호법, 법률 제20897호 2025.4.1. 개정 기준).
      법령이 개정되면 backend/rules/rule_engine.py 상단의 검증일과 함께 재확인하세요.
"""

from __future__ import annotations
from typing import Optional, List
from enum import Enum
from pydantic import BaseModel, Field


class FieldStatus(str, Enum):
    """개별 항목의 추출 상태"""
    PRESENT = "present"       # 명시적으로 존재함이 확인됨
    ABSENT = "absent"         # 명시적으로 존재하지 않음이 확인됨
    UNCLEAR = "unclear"       # 텍스트만으로 판단하기 어려움 (LLM 저신뢰)


class ExtractedField(BaseModel):
    """LLM이 추출한 단일 항목 + 근거 스니펫 + 신뢰도"""
    status: FieldStatus
    evidence: Optional[str] = Field(
        default=None, description="판단 근거가 된 원문 스니펫 (해당 시)"
    )
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


class PolicyFacts(BaseModel):
    """
    처리방침 1건에서 추출된 전체 Fact 집합.
    Rule Engine은 이 구조를 입력으로 받아 판정을 수행합니다.
    """
    purpose: ExtractedField
    collection_items: ExtractedField
    retention_period: ExtractedField
    third_party_provision: ExtractedField
    outsourcing: ExtractedField
    destruction_procedure: ExtractedField
    cross_border_transfer: ExtractedField
    consent_withdrawal_method: ExtractedField
    data_subject_rights_method: ExtractedField
    privacy_officer_contact: ExtractedField
    auto_collection_device: ExtractedField
    sensitive_data_disclosure_method: ExtractedField
    pseudonymized_data_processing: ExtractedField

    # 원문 처리방침의 특정 상황을 반영하기 위한 선택적 컨텍스트
    involves_minor: Optional[bool] = Field(
        default=None, description="정보주체에 만 14세 미만 아동 포함 여부 (해당 시 AMBER 가능성 ↑)"
    )
    involves_sensitive_data: Optional[bool] = Field(
        default=None, description="민감정보 처리 여부 (해당 시 R13 평가 대상)"
    )
    involves_pseudonymized_data: Optional[bool] = Field(
        default=None, description="가명정보 처리 여부 (해당 시 R14 평가 대상)"
    )


class Verdict(str, Enum):
    GREEN = "GREEN"   # 명시적 요건 충족
    RED = "RED"       # 명시적 필수요건 누락
    AMBER = "AMBER"   # 법적 해석 또는 사람의 판단 필요


class RuleResult(BaseModel):
    rule_id: str
    rule_name: str
    legal_basis: str
    verdict: Verdict
    rationale: str


class ComplianceReport(BaseModel):
    overall_verdict: Verdict
    results: List[RuleResult]
    green_count: int
    red_count: int
    amber_count: int
