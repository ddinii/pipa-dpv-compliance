import copy
import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app


BASE = Path(__file__).resolve().parent
EXAMPLES = BASE.parent / "examples"

client = TestClient(app)

POC3_RULE_IDS = {
    "P3-R01", "P3-R02", "P3-R03", "P3-R04",
    "P3-R05", "P3-R06", "P3-R08", "P3-R11",
}


def load_sc_d01_form() -> dict:
    return json.loads((EXAMPLES / "SC-D01_form.json").read_text(encoding="utf-8"))


def test_design_check_traverses_sc_d01_example():
    response = client.post("/api/v1/compliance/design-check", json=load_sc_d01_form())

    assert response.status_code == 200
    body = response.json()
    assert body["poc"] == "PoC3"
    assert len(body["rule_results"]) == 8


def test_design_check_returns_exactly_the_8_frozen_poc3_rule_ids():
    response = client.post("/api/v1/compliance/design-check", json=load_sc_d01_form())

    body = response.json()
    rule_ids = {result["rule_id"] for result in body["rule_results"]}
    assert rule_ids == POC3_RULE_IDS


def test_design_check_preserves_rule_result_status_and_applicability_semantics():
    response = client.post("/api/v1/compliance/design-check", json=load_sc_d01_form())

    body = response.json()
    for result in body["rule_results"]:
        assert result["status"] in {"GREEN", "AMBER", "RED", "N/A"}
        assert result["applicability"] in {"TRUE", "FALSE", "UNKNOWN"}
        assert "matched_facts" in result
        assert "missing_facts" in result
        assert "uncertain_facts" in result
        assert "evidence" in result
        assert "legal_basis" in result
        assert "reason" in result
        assert "recommendation" in result
        assert "evaluated_at" in result

    # SC-D01 is the frozen all-GREEN acceptance fixture for PoC3.
    statuses = {result["rule_id"]: result["status"] for result in body["rule_results"]}
    assert statuses == {rule_id: "GREEN" for rule_id in POC3_RULE_IDS}


def test_design_check_missing_collection_activities_returns_422():
    form = load_sc_d01_form()
    del form["collection_activities"]

    response = client.post("/api/v1/compliance/design-check", json=form)

    assert response.status_code == 422


def test_design_check_missing_required_activity_field_returns_422():
    form = load_sc_d01_form()
    del form["collection_activities"][0]["legal_basis"]

    response = client.post("/api/v1/compliance/design-check", json=form)

    assert response.status_code == 422


def test_design_check_missing_controller_returns_422():
    form = load_sc_d01_form()
    del form["controller"]

    response = client.post("/api/v1/compliance/design-check", json=form)

    assert response.status_code == 422


def test_design_check_non_object_body_returns_422():
    response = client.post("/api/v1/compliance/design-check", json=["not", "an", "object"])

    assert response.status_code == 422


def test_design_check_does_not_mutate_input_form():
    form = load_sc_d01_form()
    original = copy.deepcopy(form)

    client.post("/api/v1/compliance/design-check", json=form)

    assert form == original


def test_legacy_endpoints_still_work():
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
