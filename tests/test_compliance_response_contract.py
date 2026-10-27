"""Proves the response-only Pydantic models added to app/api/compliance.py
freeze the OpenAPI schema without changing any runtime response JSON.
"""

import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app


BASE = Path(__file__).resolve().parent
EXAMPLES = BASE.parent / "examples"

client = TestClient(app)


def load_fixture(name: str) -> dict:
    return json.loads((EXAMPLES / name).read_text(encoding="utf-8"))


def test_policy_check_response_json_unchanged_shape_and_values():
    response = client.post(
        "/api/v1/compliance/policy-check",
        json=load_fixture("poc1_synthetic_policy_fixture.json"),
    )

    assert response.status_code == 200
    body = response.json()
    assert set(body.keys()) == {"analysis_id", "poc", "ontology_version", "rule_version",
         "fact_schema_version", "results"}
    assert body["poc"] == "PoC1"
    for result in body["results"]:
        assert set(result.keys()) == {
            "rule_id", "rule_version", "status", "applicability",
            "matched_facts", "missing_facts", "uncertain_facts",
            "evidence", "legal_basis", "reason", "recommendation",
            "evaluated_at", "source_document_id",
            "instance_results", "implementation_notes",
        }
        for evidence_item in result["evidence"]:
            assert set(evidence_item.keys()) == {
                "evidence_type", "subject", "predicate", "value",
                "source_text", "note",
            }
        for instance in result["instance_results"]:
            assert set(instance.keys()) == {
                "instance_id", "status", "applicability", "matched_facts",
                "missing_facts", "uncertain_facts", "evidence", "reason",
                "recommendation",
            }


def test_breach_check_response_json_unchanged_shape_and_values():
    response = client.post(
        "/api/v1/compliance/breach-check",
        json=load_fixture("poc2_synthetic_breach_fixture.json"),
    )

    assert response.status_code == 200
    body = response.json()
    assert set(body.keys()) == {"analysis_id", "poc", "ontology_version", "rule_version",
         "fact_schema_version", "results"}
    assert body["poc"] == "PoC2"
    assert len(body["results"]) == 5


def test_design_check_response_json_unchanged_shape_and_values():
    response = client.post(
        "/api/v1/compliance/design-check",
        json=load_fixture("SC-D01_form.json"),
    )

    assert response.status_code == 200
    body = response.json()
    assert set(body.keys()) == {"analysis_id", "poc", "ontology_version", "rule_version",
         "fact_schema_version", "results"}
    assert body["poc"] == "PoC3"
    assert len(body["results"]) == 8


def test_openapi_exposes_explicit_response_schema_for_all_three_endpoints():
    schema = app.openapi()
    paths = schema["paths"]

    for path in (
        "/api/v1/compliance/policy-check",
        "/api/v1/compliance/breach-check",
        "/api/v1/compliance/design-check",
    ):
        response_schema = paths[path]["post"]["responses"]["200"]["content"][
            "application/json"
        ]["schema"]
        # response_model=ComplianceResponse -> a named schema reference,
        # not the previous untyped dict[str, Any] response.
        assert "$ref" in response_schema
        assert response_schema["$ref"].endswith("ComplianceResponse")


def test_openapi_rule_result_schema_includes_nested_instance_and_evidence_fields():
    schema = app.openapi()
    components = schema["components"]["schemas"]

    assert "RuleResultResponse" in components
    rule_result_props = components["RuleResultResponse"]["properties"]
    assert set(rule_result_props.keys()) == {
        "rule_id", "rule_version", "status", "applicability",
        "matched_facts", "missing_facts", "uncertain_facts", "evidence",
        "legal_basis", "reason", "recommendation", "evaluated_at",
        "source_document_id",
        "instance_results", "implementation_notes",
    }

    assert "EvidenceResponse" in components
    evidence_props = components["EvidenceResponse"]["properties"]
    assert set(evidence_props.keys()) == {
        "evidence_type", "subject", "predicate", "value", "source_text", "note",
    }

    assert "InstanceRuleResultResponse" in components
    instance_props = components["InstanceRuleResultResponse"]["properties"]
    assert set(instance_props.keys()) == {
        "instance_id", "status", "applicability", "matched_facts",
        "missing_facts", "uncertain_facts", "evidence", "reason",
        "recommendation",
    }


def test_422_from_compliance_input_error_still_returns_plain_string_detail():
    request = load_fixture("poc1_synthetic_policy_fixture.json")
    del request["policy_text"]

    response = client.post("/api/v1/compliance/policy-check", json=request)

    assert response.status_code == 422
    assert isinstance(response.json()["detail"], str)


def test_422_from_malformed_body_still_returns_fastapi_error_list():
    response = client.post(
        "/api/v1/compliance/policy-check", json=["not", "an", "object"]
    )

    assert response.status_code == 422
    assert isinstance(response.json()["detail"], list)
