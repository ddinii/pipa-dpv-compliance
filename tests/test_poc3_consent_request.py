"""PoC3 F3-03: consent_request.planned=false / missing field (P3-12 class)."""

import copy

import pytest
from rdflib import RDF, URIRef

from app.builders.poc3_fact_builder import build_poc3_facts
from app.mapping.ontology_mapper import OntologyMapper
from app.rules.engine import P0RuleEngine

PIPA = "https://w3id.org/pipa-compliance/ontology#"

BASE = {
    "analysis_id": "Q-CR",
    "controller": {"controller_id": "QA", "name": "QA"},
    "collection_activities": [
        {
            "activity_id": "A-CR-1",
            "purpose": "회원 인증 및 주문내역 조회",
            "legal_basis": {"type": "Consent", "status": "confirmed"},
            "consent_request": {"planned": True},
            "personal_information_items": [
                {"item_name": "이메일 주소", "is_required": True, "design_rationale": "계정 식별 및 본인 인증"}
            ],
            "retention": {"end_condition": "회원 탈퇴 완료 시", "destruction_method": "관련 DB 레코드 영구 삭제"},
            "denies_service_on_optional_refusal": False,
        }
    ],
    "entrusted_processings": [],
}
CONSENT_RULES = ("P3-R02", "P3-R03", "P3-R04")


def form(**changes):
    f = copy.deepcopy(BASE)
    act = f["collection_activities"][0]
    for key, value in changes.items():
        if value is ...:
            act.pop(key, None)
        else:
            act[key] = value
    return f


def evaluate(f):
    facts = build_poc3_facts(f)
    mapped = OntologyMapper(f["analysis_id"], controller_id="QA", controller_name="QA").map(facts)
    results = P0RuleEngine().evaluate_mapping_result(mapped, poc="PoC3")
    return facts, mapped, {r.rule_id: r.status.value for r in results}


def f303(facts):
    return [x for x in facts if x["fact_id"].startswith("F3-03")]


def request_nodes(mapped):
    return list(mapped.graph.subjects(RDF.type, URIRef(PIPA + "ConsentRequest")))


def test_planned_false_is_absent_and_consent_rules_red():
    facts, mapped, status = evaluate(form(consent_request={"planned": False}))
    (fact,) = f303(facts)
    assert fact["value_state"] == "absent" and fact["value"] is None
    assert fact["evidence"][0]["field_path"].endswith("consent_request")
    assert {r: status[r] for r in CONSENT_RULES} == {r: "RED" for r in CONSENT_RULES}


def test_absent_f303_is_not_recreated_by_optional_refusal():
    # denies_service_on_optional_refusal=False (F3-09) is present in BASE.
    facts, mapped, _ = evaluate(form(consent_request={"planned": False}))
    assert any(x["fact_id"].startswith("F3-09") for x in facts)
    assert request_nodes(mapped) == []


def test_planned_true_keeps_existing_green():
    facts, mapped, status = evaluate(form())
    assert f303(facts)[0]["value_state"] == "confirmed"
    assert len(request_nodes(mapped)) == 1
    assert {r: status[r] for r in CONSENT_RULES} == {r: "GREEN" for r in CONSENT_RULES}


@pytest.mark.parametrize("missing", [..., None])
def test_missing_consent_request_is_unknown_not_planned_true(missing):
    facts, mapped, status = evaluate(form(consent_request=missing))
    (fact,) = f303(facts)
    assert fact["value_state"] == "unknown" and fact["value"] is None
    assert {r: status[r] for r in CONSENT_RULES} == {r: "YELLOW" for r in CONSENT_RULES}


def test_non_consent_basis_planned_false_is_unchanged():
    base_status = evaluate(form(legal_basis={"type": "Contract", "status": "confirmed"}))[2]
    facts, _, status = evaluate(
        form(legal_basis={"type": "Contract", "status": "confirmed"}, consent_request={"planned": False})
    )
    assert f303(facts)[0]["value_state"] == "confirmed"
    assert {r: status[r] for r in CONSENT_RULES} == {r: base_status[r] for r in CONSENT_RULES}
    assert "RED" not in {status[r] for r in CONSENT_RULES}
