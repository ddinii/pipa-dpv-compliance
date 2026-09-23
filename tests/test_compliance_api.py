"""API-003 design-check 계약 테스트 (기능명세서 8장·9장).

UI와 API가 같은 ComplianceResponse를 쓰므로, 여기서 깨지면 화면도 같이 깨진다.
"""

import copy
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app

ROOT = Path(__file__).resolve().parents[1]
FORM_PATH = ROOT / "evals" / "poc3" / "sc_d01_form.json"

ENDPOINT = "/api/v1/compliance/design-check"

# 기능명세서 9.1 공통 응답 필드
ENVELOPE_FIELDS = {
    "analysis_id",
    "poc",
    "ontology_version",
    "rule_version",
    "fact_schema_version",
    "results",
}

# 기능명세서 8장 RuleResult 필수 필드
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
    "source_document_id",
    "evaluated_at",
}

POC3_RULES = {"P3-R01", "P3-R02", "P3-R03", "P3-R04", "P3-R05", "P3-R06", "P3-R08", "P3-R11"}


@pytest.fixture(scope="module")
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture(scope="module")
def form() -> dict:
    return json.loads(FORM_PATH.read_text(encoding="utf-8"))


def mutate(form: dict, change) -> dict:
    payload = copy.deepcopy(form)
    change(payload)
    return payload


# --- 계약 ---------------------------------------------------------------


def test_design_check_returns_the_nine_one_envelope(client: TestClient, form: dict):
    payload = client.post(ENDPOINT, json=form).json()
    assert ENVELOPE_FIELDS <= set(payload)
    assert payload["poc"] == "poc3"
    assert payload["ontology_version"] == payload["rule_version"] == "1.0"
    assert payload["analysis_id"].startswith("A-")


def test_every_rule_result_carries_the_chapter_eight_fields(client: TestClient, form: dict):
    """RuleResult에 source_document_id가 실려야 한다 (8장 필수 · NFR-04 · TST-010).

    Rule Engine의 RuleResult에는 아직 이 필드가 없어 API 계층이 채운다.
    """
    payload = client.post(ENDPOINT, json=form).json()
    for result in payload["results"]:
        assert RULE_RESULT_FIELDS <= set(result), result["rule_id"]
        assert result["source_document_id"] == form["scenario_id"]


def test_only_the_eight_poc3_rules_are_loaded(client: TestClient, form: dict):
    """COM-005: PoC에 따라 Rule Set을 분리 로드한다. P1은 로드하지 않는다."""
    payload = client.post(ENDPOINT, json=form).json()
    assert {result["rule_id"] for result in payload["results"]} == POC3_RULES


def test_sc_d01_design_is_all_green(client: TestClient, form: dict):
    payload = client.post(ENDPOINT, json=form).json()
    assert {r["rule_id"]: r["status"] for r in payload["results"]} == {
        rule: "GREEN" for rule in POC3_RULES
    }


def test_gar_results_always_carry_evidence(client: TestClient, form: dict):
    """TST-004: G/A/R 결과에서 evidence가 비어 있으면 실패로 처리한다."""
    incomplete = mutate(form, lambda d: d["collection_activities"][0].update(legal_basis=None))
    payload = client.post(ENDPOINT, json=incomplete).json()
    for result in payload["results"]:
        if result["status"] != "N/A":
            assert result["evidence"], result["rule_id"]


def test_same_form_gives_the_same_statuses(client: TestClient, form: dict):
    """NFR-03 재현성. analysis_id와 evaluated_at만 달라야 한다."""
    first = client.post(ENDPOINT, json=form).json()
    second = client.post(ENDPOINT, json=form).json()
    key = lambda payload: {  # noqa: E731
        r["rule_id"]: (r["status"], r["reason"], r["matched_facts"]) for r in payload["results"]
    }
    assert key(first) == key(second)
    assert first["analysis_id"] != second["analysis_id"]


# --- 입력 검증 ----------------------------------------------------------


def test_unknown_form_field_is_rejected(client: TestClient, form: dict):
    """COM-002: 임의 보완 금지. 모르는 필드는 조용히 무시하지 않고 거부한다."""
    payload = mutate(form, lambda d: d.update(hallucinated="x"))
    assert client.post(ENDPOINT, json=payload).status_code == 422


def test_design_without_any_activity_is_rejected(client: TestClient):
    """정본 Builder는 처리행위가 최소 하나 있어야 한다. 빈 설계는 점검 대상이 아니다."""
    response = client.post(ENDPOINT, json={"scenario_id": "EMPTY"})
    assert response.status_code == 400
    assert "collection_activities" in str(response.json()["detail"])


# --- 상태 전이 ----------------------------------------------------------


@pytest.mark.parametrize(
    "change, rule_id, expected",
    [
        (lambda d: d["collection_activities"][0].update(legal_basis=None), "P3-R01", "AMBER"),
        (
            lambda d: d["collection_activities"][1]["consent"].update(
                denies_service_on_optional_refusal=True
            ),
            "P3-R06", "RED",
        ),
        (lambda d: d.update(entrustments=[]), "P3-R11", "AMBER"),
    ],
)
def test_status_transitions_through_the_api(
    client: TestClient, form: dict, change, rule_id: str, expected: str
):
    payload = client.post(ENDPOINT, json=mutate(form, change)).json()
    statuses = {result["rule_id"]: result["status"] for result in payload["results"]}
    assert statuses[rule_id] == expected


# --- UI 지원 endpoint ---------------------------------------------------


def test_design_page_is_served(client: TestClient):
    response = client.get("/design")
    assert response.status_code == 200
    assert "Privacy-by-Design" in response.text


def test_example_form_round_trips_through_the_api(client: TestClient):
    """UI가 처음 불러오는 예시가 그대로 API를 통과해야 한다."""
    example = client.get("/api/v1/dev/design-example").json()
    assert client.post(ENDPOINT, json=example).status_code == 200


def test_design_facts_endpoint_exposes_generated_facts(client: TestClient, form: dict):
    payload = client.post("/api/v1/dev/design-facts", json=form).json()
    assert payload["fact_count"] == len(payload["facts"])
    from app.mapping.fact_schema import fact_type

    assert {fact_type(fact["fact_id"]) for fact in payload["facts"]} >= {
        "F3-01", "F3-02", "F3-05", "F3-07", "F3-08", "F3-11", "F3-12", "F3-13"
    }
    # PoC3 근거는 field_path다 (Fact Dictionary 8장)
    for fact in payload["facts"]:
        assert fact["evidence"][0]["field_path"]
