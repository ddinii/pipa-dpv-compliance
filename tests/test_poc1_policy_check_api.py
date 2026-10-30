import copy
import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app


BASE = Path(__file__).resolve().parent
EXAMPLES = BASE.parent / "examples"

client = TestClient(app)

POC1_RULE_IDS = {
    "P1-R01", "P1-R02", "P1-R03", "P1-R04", "P1-R06", "P1-R07", "P1-R08",
    "P1-R09", "P1-R10", "P1-R11", "P1-R12",
}


def load_synthetic_policy_fixture() -> dict:
    return json.loads(
        (EXAMPLES / "poc1_synthetic_policy_fixture.json").read_text(encoding="utf-8")
    )


def test_policy_check_returns_200_for_synthetic_valid_fixture():
    response = client.post(
        "/api/v1/compliance/policy-check", json=load_synthetic_policy_fixture()
    )

    assert response.status_code == 200


def test_policy_check_response_poc_is_poc1():
    response = client.post(
        "/api/v1/compliance/policy-check", json=load_synthetic_policy_fixture()
    )

    assert response.json()["poc"] == "PoC1"


def test_policy_check_returns_exactly_the_11_poc1_rule_ids():
    response = client.post(
        "/api/v1/compliance/policy-check", json=load_synthetic_policy_fixture()
    )

    body = response.json()
    rule_ids = {result["rule_id"] for result in body["results"]}
    assert rule_ids == POC1_RULE_IDS
    assert len(body["results"]) == 11


def test_policy_check_preserves_rule_result_status_and_applicability_semantics():
    response = client.post(
        "/api/v1/compliance/policy-check", json=load_synthetic_policy_fixture()
    )

    body = response.json()
    for result in body["results"]:
        assert result["status"] in {"GREEN", "YELLOW", "RED", "N/A"}
        assert result["applicability"] in {"TRUE", "FALSE", "UNKNOWN"}
        assert "matched_facts" in result
        assert "missing_facts" in result
        assert "uncertain_facts" in result
        assert "evidence" in result
        assert "legal_basis" in result
        assert "reason" in result
        assert "recommendation" in result
        assert "evaluated_at" in result


def test_policy_check_missing_analysis_id_returns_422():
    request = load_synthetic_policy_fixture()
    del request["analysis_id"]

    response = client.post("/api/v1/compliance/policy-check", json=request)

    assert response.status_code == 422


def test_policy_check_missing_controller_returns_422():
    request = load_synthetic_policy_fixture()
    del request["controller"]

    response = client.post("/api/v1/compliance/policy-check", json=request)

    assert response.status_code == 422


def test_policy_check_missing_policy_text_returns_422():
    request = load_synthetic_policy_fixture()
    del request["policy_text"]

    response = client.post("/api/v1/compliance/policy-check", json=request)

    assert response.status_code == 422


def test_policy_check_non_object_body_returns_422():
    response = client.post(
        "/api/v1/compliance/policy-check", json=["not", "an", "object"]
    )

    assert response.status_code == 422


def test_policy_check_does_not_mutate_input_request():
    request = load_synthetic_policy_fixture()
    original = copy.deepcopy(request)

    client.post("/api/v1/compliance/policy-check", json=request)

    assert request == original


def test_design_check_still_works_alongside_policy_check():
    form = json.loads((EXAMPLES / "SC-D01_form.json").read_text(encoding="utf-8"))

    response = client.post("/api/v1/compliance/design-check", json=form)

    assert response.status_code == 200
    assert response.json()["poc"] == "PoC3"


def test_legacy_endpoints_remain_unaffected():
    health = client.get("/health")
    assert health.status_code == 200
    assert health.json() == {"status": "ok"}

    validate_response = client.post(
        "/api/v1/validate",
        json={
            "collection": {
                "purpose": "membership",
                "items": ["email"],
                "legalBasis": "consent",
            },
        },
    )
    assert validate_response.status_code in (200, 422)


def test_instance_results_carry_the_purpose_as_display_label():
    """같은 유형 처리행위를 화면에서 구분하도록 처리 목적 문장을 instance_label로 보낸다."""
    response = client.post(
        "/api/v1/compliance/policy-check", json=load_synthetic_policy_fixture()
    )
    results = {r["rule_id"]: r for r in response.json()["results"]}
    collection = results["P1-R01"]["instance_results"][0]
    assert collection["instance_label"] == "회원 가입 및 서비스 제공(합성 테스트 데이터)"
    officer = results["P1-R10"]["instance_results"][0]
    assert officer["instance_label"] is None
