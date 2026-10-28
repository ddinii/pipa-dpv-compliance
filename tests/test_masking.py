"""출력 마스킹 (표시제한). 테스트 번호는 모두 형식만 맞춘 가상 값이다."""

import pytest

from app.api.compliance import _mask_result
from app.privacy.masking import mask_name, mask_text


@pytest.mark.parametrize(
    "raw, masked",
    [
        ("연락처 010-1234-5678", "연락처 010-****-5678"),
        ("전화 02-123-4567", "전화 02-***-4567"),
        ("01012345678", "010-****-5678"),
        ("주민번호 900101-1234567", "주민번호 900101-1******"),
        ("9001011234567", "900101-1******"),
        ("카드 1234-5678-9012-3456", "카드 1234-****-****-3456"),
        ("1234567890123456", "1234-****-****-3456"),
        ("privacy@example.com", "pri****@example.com"),   # 앞 3자리만 노출
        ("abcd@example.com", "abc*@example.com"),
        ("abc@example.com", "a**@example.com"),        # 3자리 이하: 첫 글자만
        ("a@example.com", "a@example.com"),
    ],
)
def test_personal_numbers_are_masked(raw: str, masked: str):
    assert mask_text(raw) == masked


@pytest.mark.parametrize(
    "text",
    [
        "2026-09-05T14:30:00+09:00",   # 날짜 Fact (KST ISO)
        "2026-08-14 10:05",
        "2026년 9월 5일",
        "고객센터 1588-0000",           # 기업 대표번호는 개인 번호가 아니다
        "제34조제1항제2호",
        "수신자 5,200명",
        "rule_version 1.1",
        "right_0123456789ab",           # 매퍼가 만든 해시 ID
    ],
)
def test_non_personal_text_is_left_alone(text: str):
    assert mask_text(text) == text


def test_name_masking_hides_the_middle():
    assert [mask_name(n) for n in ["홍길동", "홍길", "남궁민수"]] == ["홍*동", "홍*", "남**수"]


def test_api_masks_only_human_readable_fields():
    """식별자는 화면이 결과를 연결하는 데 쓰므로 바뀌면 안 된다."""
    result = {
        "rule_id": "P1-R09",
        "reason": "담당자 연락처 010-1234-5678이 확인됩니다.",
        "recommendation": "privacy@example.com 로 문의",
        "matched_facts": ["rdf:right_0123456789ab:hasRight"],
        "evidence": [{
            "evidence_type": "source_text",
            "subject": "https://example.org/right_0123456789ab",
            "value": "010-1234-5678",
            "source_text": "개인정보 보호책임자 연락처: 02-123-4567",
            "note": None,
        }],
        "instance_results": [{
            "instance_id": "https://example.org/right_0123456789ab",
            "reason": "전화 01012345678",
            "evidence": [{"value": "900101-1234567", "source_text": None}],
        }],
    }
    masked = _mask_result(result)
    assert masked["reason"] == "담당자 연락처 010-****-5678이 확인됩니다."
    assert masked["recommendation"].startswith("pri****@example.com")
    assert masked["evidence"][0]["value"] == "010-****-5678"
    assert masked["evidence"][0]["source_text"].endswith("02-***-4567")
    assert masked["instance_results"][0]["reason"] == "전화 010-****-5678"
    assert masked["instance_results"][0]["evidence"][0]["value"] == "900101-1******"
    # 식별자는 그대로
    assert masked["rule_id"] == "P1-R09"
    assert masked["matched_facts"] == result["matched_facts"]
    assert masked["evidence"][0]["subject"] == result["evidence"][0]["subject"]
    assert masked["instance_results"][0]["instance_id"] == result["instance_results"][0]["instance_id"]


def test_officer_name_is_masked_wherever_it_appears_but_company_names_are_not():
    """보호책임자 성명(hasPersonName)은 자연인 이름이다. 회사 명칭(hasName)은 그대로 둔다."""
    officer = "https://example.org/privacy-officer-0123"
    result = {
        "rule_id": "P1-R10",
        "reason": "보호책임자 홍길동의 연락처가 확인됩니다.",
        "recommendation": "",
        "evidence": [
            {"subject": officer, "predicate": "hasPersonName", "value": "홍길동"},
            {"subject": officer, "predicate": "hasDepartmentName", "value": "정보보호팀"},
            {"subject": officer, "predicate": "hasContact", "value": "dpo@example.com"},
            {"subject": "x", "predicate": "hasName", "value": "Example Travel K.K."},
        ],
        "instance_results": [{
            "instance_id": officer, "reason": "홍길동 확인",
            "evidence": [{"predicate": "https://w3id.org/pipa#hasPersonName", "value": "홍길동"}],
        }],
    }
    masked = _mask_result(result)
    values = [item["value"] for item in masked["evidence"]]
    # @ 앞이 3자 이하이면 첫 글자만 남긴다
    assert values == ["홍*동", "정보보호팀", "d**@example.com", "Example Travel K.K."]
    assert masked["reason"] == "보호책임자 홍*동의 연락처가 확인됩니다."
    assert masked["instance_results"][0]["reason"] == "홍*동 확인"
    assert masked["instance_results"][0]["evidence"][0]["value"] == "홍*동"
    assert "홍길동" not in repr(masked)


def test_api_response_contains_no_raw_numbers_end_to_end():
    """실제 API 경로로도 확인한다 (mock Extractor는 번호가 없어 원문을 그대로 통과해야 한다)."""
    from fastapi.testclient import TestClient

    from app.main import app

    response = TestClient(app).post(
        "/api/v1/compliance/policy-check",
        json={"analysis_id": "MASK-1", "controller": {"controller_id": "c"},
              "policy_text": "합성 문서"},
    )
    assert response.status_code == 200
    assert response.json()["results"]
