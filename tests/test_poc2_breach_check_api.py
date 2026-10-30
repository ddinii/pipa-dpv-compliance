import copy
import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app


BASE = Path(__file__).resolve().parent
EXAMPLES = BASE.parent / "examples"

client = TestClient(app)

POC2_RULE_IDS = {"P2-R01", "P2-R02", "P2-R03", "P2-R08", "P2-R09", "P2-R10"}


def load_synthetic_breach_fixture() -> dict:
    return json.loads(
        (EXAMPLES / "poc2_synthetic_breach_fixture.json").read_text(encoding="utf-8")
    )


def test_breach_check_returns_200_for_synthetic_valid_fixture():
    response = client.post(
        "/api/v1/compliance/breach-check", json=load_synthetic_breach_fixture()
    )

    assert response.status_code == 200


def test_breach_check_response_poc_is_poc2():
    response = client.post(
        "/api/v1/compliance/breach-check", json=load_synthetic_breach_fixture()
    )

    assert response.json()["poc"] == "PoC2"


def test_breach_check_returns_all_6_poc2_rule_ids():
    response = client.post(
        "/api/v1/compliance/breach-check", json=load_synthetic_breach_fixture()
    )

    body = response.json()
    rule_ids = {result["rule_id"] for result in body["results"]}
    assert rule_ids == POC2_RULE_IDS
    assert len(body["results"]) == 6


def test_breach_check_preserves_rule_result_status_and_applicability_semantics():
    response = client.post(
        "/api/v1/compliance/breach-check", json=load_synthetic_breach_fixture()
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


def test_breach_check_missing_analysis_id_returns_422():
    request = load_synthetic_breach_fixture()
    del request["analysis_id"]

    response = client.post("/api/v1/compliance/breach-check", json=request)

    assert response.status_code == 422


def test_breach_check_missing_controller_returns_422():
    request = load_synthetic_breach_fixture()
    del request["controller"]

    response = client.post("/api/v1/compliance/breach-check", json=request)

    assert response.status_code == 422


def test_breach_check_missing_incident_returns_422():
    request = load_synthetic_breach_fixture()
    del request["incident"]

    response = client.post("/api/v1/compliance/breach-check", json=request)

    assert response.status_code == 422


def test_breach_check_non_object_body_returns_422():
    response = client.post(
        "/api/v1/compliance/breach-check", json=["not", "an", "object"]
    )

    assert response.status_code == 422


def test_breach_check_notification_omitted_returns_200_not_500():
    request = load_synthetic_breach_fixture()
    del request["notification"]

    response = client.post("/api/v1/compliance/breach-check", json=request)

    assert response.status_code == 200
    body = response.json()
    assert body["poc"] == "PoC2"
    rule_ids = {result["rule_id"] for result in body["results"]}
    assert rule_ids == POC2_RULE_IDS


def test_breach_check_notification_null_is_treated_as_omitted():
    request = load_synthetic_breach_fixture()
    request["notification"] = None

    response = client.post("/api/v1/compliance/breach-check", json=request)

    assert response.status_code == 200


def test_breach_check_does_not_mutate_input_request():
    request = load_synthetic_breach_fixture()
    original = copy.deepcopy(request)

    client.post("/api/v1/compliance/breach-check", json=request)

    assert request == original


def test_policy_check_and_design_check_still_work_alongside_breach_check():
    policy_request = json.loads(
        (EXAMPLES / "poc1_synthetic_policy_fixture.json").read_text(encoding="utf-8")
    )
    policy_response = client.post(
        "/api/v1/compliance/policy-check", json=policy_request
    )
    assert policy_response.status_code == 200
    assert policy_response.json()["poc"] == "PoC1"

    form = json.loads((EXAMPLES / "SC-D01_form.json").read_text(encoding="utf-8"))
    design_response = client.post("/api/v1/compliance/design-check", json=form)
    assert design_response.status_code == 200
    assert design_response.json()["poc"] == "PoC3"


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
