"""개발용 RuleResult 점검 콘솔 회귀 테스트.

이 콘솔은 API-001/002/003의 구현이 아니라 DTO 계약 검증 도구다.
따라서 여기서 지키는 것은 "Rule 판정이 맞는가"가 아니라
"명세서 9.1 envelope과 8장 RuleResult 필드가 화면까지 전달되는가"다.
"""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app


SCENARIO_DIR = Path(__file__).resolve().parent

# 요구사항·기능 명세서 8장 RuleResult 필수 필드
RULE_RESULT_FIELDS = {
    "rule_id",
    "rule_version",
    "status",
    "applicability",
    "matched_facts",
    "missing_facts",
    "uncertain_facts",
    "evidence",
    "legal_basis",
    "reason",
    "recommendation",
    "evaluated_at",
}

# 9.1 공통 API 응답 필드
ENVELOPE_FIELDS = {
    "analysis_id",
    "poc",
    "ontology_version",
    "rule_version",
    "fact_schema_version",
    "results",
}


@pytest.fixture(scope="module")
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture(scope="module")
def sc_p01() -> str:
    return (SCENARIO_DIR / "SC-P01_FINAL_Protege.ttl").read_text(encoding="utf-8")


def test_console_page_is_served(client: TestClient):
    response = client.get("/console")
    assert response.status_code == 200
    assert "RuleResult" in response.text


def test_scenario_listing_exposes_freeze_scenarios(client: TestClient):
    names = {item["name"] for item in client.get("/api/v1/dev/scenarios").json()["scenarios"]}
    assert {
        "SC-P01_FINAL_Protege.ttl",
        "SC-P02_FINAL_Protege.ttl",
        "SC-D01_FINAL_Protege.ttl",
    } <= names


@pytest.mark.parametrize(
    "name",
    [
        "test_mapper.py",  # SC- 접두사가 아님
        "SC-NOPE.ttl",  # 존재하지 않음
        "../app/main.py",  # 경로 탈출
    ],
)
def test_scenario_read_rejects_unexpected_names(client: TestClient, name: str):
    assert client.get(f"/api/v1/dev/scenarios/{name}").status_code in {400, 404}


def test_evaluate_returns_freeze_statuses_for_sc_p01(client: TestClient, sc_p01: str):
    payload = client.post(
        "/api/v1/dev/evaluate",
        json={"turtle": sc_p01, "poc": "poc1", "source_document_id": "DOC-1"},
    ).json()

    statuses = {item["rule_id"]: item["status"] for item in payload["results"]}
    assert statuses == {
        "P1-R01": "GREEN",
        "P1-R02": "AMBER",
        "P1-R03": "GREEN",
        "P1-R04": "GREEN",
        "P1-R06": "GREEN",
        "P1-R07": "GREEN",
    }


def test_evaluate_response_carries_version_envelope(client: TestClient, sc_p01: str):
    """NFR-04 / TST-010: 모든 분석 결과에 version과 추적 ID가 남아야 한다."""
    payload = client.post(
        "/api/v1/dev/evaluate",
        json={"turtle": sc_p01, "poc": "poc1", "source_document_id": "DOC-1"},
    ).json()

    assert ENVELOPE_FIELDS <= set(payload)
    assert payload["source_document_id"] == "DOC-1"
    assert payload["ontology_version"] == payload["rule_version"] == "1.0"


def test_every_rule_result_carries_contract_fields(client: TestClient, sc_p01: str):
    payload = client.post("/api/v1/dev/evaluate", json={"turtle": sc_p01, "poc": "poc1"}).json()
    for result in payload["results"]:
        assert RULE_RESULT_FIELDS <= set(result), result["rule_id"]


def test_source_document_id_is_still_missing_from_rule_result(client: TestClient, sc_p01: str):
    """8장은 RuleResult마다 source_document_id를 요구하지만 현재 DTO에는 없다.

    콘솔이 이 결손을 화면에 경고로 띄우는 것이 현재 동작이다.
    RuleResult에 필드를 추가하기로 결정하면 이 테스트를 뒤집어야 한다.
    """
    payload = client.post("/api/v1/dev/evaluate", json={"turtle": sc_p01, "poc": "poc1"}).json()
    assert all("source_document_id" not in result for result in payload["results"])


def test_gar_results_always_carry_evidence(client: TestClient, sc_p01: str):
    """TST-004: G/A/R 결과에서 evidence가 비어 있으면 실패로 처리한다."""
    payload = client.post("/api/v1/dev/evaluate", json={"turtle": sc_p01, "poc": "poc1"}).json()
    for result in payload["results"]:
        if result["status"] != "N/A":
            assert result["evidence"], result["rule_id"]


def test_sc_p01_carries_no_source_text_evidence(client: TestClient, sc_p01: str):
    """SC-P01에는 pipa:hasSourceEvidence 단언이 하나도 없다.

    PoC1이 Main PoC인데 원문 근거 경로(COM-008 / P01-004)가 전혀 검증되지 않는
    상태라는 뜻이다. 시나리오에 원문 근거를 채우면 이 테스트를 뒤집어야 한다.
    """
    payload = client.post("/api/v1/dev/evaluate", json={"turtle": sc_p01, "poc": "poc1"}).json()
    evidence = [item for result in payload["results"] for item in result["evidence"]]
    assert evidence, "evidence 자체가 비어 있으면 안 된다"
    assert all(item["source_text"] is None for item in evidence)


def test_evaluate_rejects_bad_input(client: TestClient):
    assert client.post("/api/v1/dev/evaluate", json={"turtle": "x", "poc": "poc9"}).status_code == 400
    assert client.post("/api/v1/dev/evaluate", json={"turtle": "!!! not turtle"}).status_code == 400
