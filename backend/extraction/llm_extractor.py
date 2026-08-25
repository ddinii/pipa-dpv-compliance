"""
Information Extraction Layer

처리방침 원문(자연어) -> PolicyFacts(구조화된 사실) 로 변환하는 계층.

두 가지 구현을 제공합니다:
  1. MockExtractor   : API 키 없이 키워드 매칭으로 동작 (팀원 개발/테스트용, 정확도 낮음)
  2. ClaudeExtractor  : Anthropic API를 사용해 실제 LLM 추출 수행 (ANTHROPIC_API_KEY 필요)

평가(evaluation/evaluate.py)에서 "Model A: LLM 단독" vs "Model B: LLM+온톨로지+Rule Engine"
비교를 할 때, 이 모듈의 결과가 Model B의 첫 단계 입력이 됩니다.
Model A는 이 모듈 없이 LLM에게 직접 "위반사항 판정"까지 맡긴 결과와 비교합니다.
"""

from __future__ import annotations
import json
import os
import re
from abc import ABC, abstractmethod

from backend.models import PolicyFacts, ExtractedField, FieldStatus


FIELD_NAMES = [
    "purpose", "collection_items", "retention_period",
    "third_party_provision", "outsourcing", "destruction_procedure",
    "cross_border_transfer", "consent_withdrawal_method",
    "data_subject_rights_method", "privacy_officer_contact",
]

EXTRACTION_SYSTEM_PROMPT = """당신은 한국 개인정보 처리방침을 분석하는 정보추출 시스템입니다.
입력된 처리방침 텍스트에서 아래 10개 항목의 존재 여부를 판단하고, 반드시 JSON만 출력하세요.
설명이나 마크다운 코드블록 없이 순수 JSON만 반환합니다.

각 항목은 다음 형식을 가집니다:
{
  "status": "present" | "absent" | "unclear",
  "evidence": "판단 근거가 된 원문 스니펫 (최대 40자, 없으면 null)",
  "confidence": 0.0~1.0
}

10개 항목: purpose, collection_items, retention_period, third_party_provision,
outsourcing, destruction_procedure, cross_border_transfer,
consent_withdrawal_method, data_subject_rights_method, privacy_officer_contact

또한 involves_minor(만 14세 미만 아동 관련 언급 여부, true/false/null),
involves_sensitive_data(민감정보 언급 여부, true/false/null) 도 함께 판단하세요.

최종 출력은 다음 최상위 키를 가진 단일 JSON 객체입니다:
purpose, collection_items, retention_period, third_party_provision, outsourcing,
destruction_procedure, cross_border_transfer, consent_withdrawal_method,
data_subject_rights_method, privacy_officer_contact, involves_minor, involves_sensitive_data
"""


class BaseExtractor(ABC):
    @abstractmethod
    def extract(self, policy_text: str) -> PolicyFacts:
        ...


class MockExtractor(BaseExtractor):
    """
    API 키 없이 동작하는 간단한 키워드 기반 추출기.
    실제 정확도는 낮지만, 팀원들이 API 키 없이도 rule engine / API / frontend를
    바로 개발·테스트할 수 있게 하기 위한 용도입니다.

    ⚠️ 평가(evaluation)에는 사용하지 마세요 — Model A/B 비교는 반드시 실제 LLM으로.
    """

    KEYWORD_MAP = {
        "purpose": ["처리 목적", "이용 목적", "수집 목적"],
        "collection_items": ["수집하는 개인정보", "수집항목", "수집 항목"],
        "retention_period": ["보유기간", "보유 기간", "보관기간", "보관 기간"],
        "third_party_provision": ["제3자 제공", "제3자에게 제공"],
        "outsourcing": ["처리위탁", "처리 위탁", "위탁업체", "수탁자"],
        "destruction_procedure": ["파기절차", "파기 절차", "파기방법", "파기 방법"],
        "cross_border_transfer": ["국외이전", "국외 이전", "해외 이전"],
        "consent_withdrawal_method": ["동의철회", "동의 철회"],
        "data_subject_rights_method": ["열람청구", "정정·삭제", "권리행사"],
        "privacy_officer_contact": ["개인정보보호책임자", "개인정보 보호책임자"],
    }

    def extract(self, policy_text: str) -> PolicyFacts:
        fields = {}
        for field_name in FIELD_NAMES:
            keywords = self.KEYWORD_MAP[field_name]
            found_kw = next((kw for kw in keywords if kw in policy_text), None)
            if found_kw:
                idx = policy_text.find(found_kw)
                snippet = policy_text[max(0, idx - 5): idx + 30].strip()
                fields[field_name] = ExtractedField(
                    status=FieldStatus.PRESENT, evidence=snippet, confidence=0.8
                )
            else:
                # 키워드 부재는 '진짜 부재'인지 '다른 표현으로 쓰였는지' 확신하기 어려우므로
                # LLM 대비 보수적인(약간 낮은) 신뢰도를 부여합니다.
                fields[field_name] = ExtractedField(
                    status=FieldStatus.ABSENT, evidence=None, confidence=0.7
                )

        involves_minor = bool(re.search(r"(14세|만 14|아동)", policy_text))
        involves_sensitive = bool(re.search(r"(민감정보|건강정보|생체정보)", policy_text))

        return PolicyFacts(
            **fields,
            involves_minor=involves_minor,
            involves_sensitive_data=involves_sensitive,
        )


class ClaudeExtractor(BaseExtractor):
    """
    Anthropic API(Claude)를 사용한 실제 정보추출.
    환경변수 ANTHROPIC_API_KEY 필요. 모델명은 필요시 조정하세요.
    """

    def __init__(self, model: str = "claude-sonnet-4-6"):
        self.model = model
        self.api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY 환경변수가 설정되지 않았습니다. "
                ".env 파일을 확인하거나 MockExtractor를 사용하세요."
            )

    def extract(self, policy_text: str) -> PolicyFacts:
        import httpx

        response = httpx.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": self.model,
                "max_tokens": 1500,
                "system": EXTRACTION_SYSTEM_PROMPT,
                "messages": [{"role": "user", "content": policy_text}],
            },
            timeout=60,
        )
        response.raise_for_status()
        data = response.json()
        raw_text = "".join(
            block["text"] for block in data["content"] if block.get("type") == "text"
        )
        # 코드블록 마크다운이 섞여 오는 경우 방어적으로 제거
        cleaned = re.sub(r"^```json|```$", "", raw_text.strip(), flags=re.MULTILINE).strip()
        parsed = json.loads(cleaned)

        fields = {
            name: ExtractedField(**parsed[name]) for name in FIELD_NAMES
        }
        return PolicyFacts(
            **fields,
            involves_minor=parsed.get("involves_minor"),
            involves_sensitive_data=parsed.get("involves_sensitive_data"),
        )


def get_extractor() -> BaseExtractor:
    """환경변수에 API 키가 있으면 Claude, 없으면 Mock을 자동 선택"""
    if os.environ.get("ANTHROPIC_API_KEY"):
        return ClaudeExtractor()
    return MockExtractor()
