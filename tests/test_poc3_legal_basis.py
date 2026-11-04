"""PoC3 legal basis: allowed tokens, exact matching and legal_basis.status."""

import copy

import pytest
from rdflib import RDF, RDFS, URIRef

from app.builders.poc3_fact_builder import Poc3FormError, build_poc3_facts
from app.mapping.ontology_mapper import OntologyMapper
from app.rules.engine import P0RuleEngine
from app.services.compliance import ComplianceInputError, run_design_check

PIPA = "https://w3id.org/pipa-compliance/ontology#"

BASE = {
    "analysis_id": "Q-LB",
    "controller": {"controller_id": "QA", "name": "QA"},
    "collection_activities": [
        {
            "activity_id": "A-LB-1",
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
RULES = ("P3-R01", "P3-R02", "P3-R03", "P3-R04")


def form(legal_basis=..., **changes):
    f = copy.deepcopy(BASE)
    act = f["collection_activities"][0]
    if legal_basis is not ...:
        act["legal_basis"] = legal_basis
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
    return facts, mapped, [{r.rule_id: r.status.value for r in results}[k] for k in RULES]


def lb(type_, status="confirmed"):
    value = {"type": type_}
    if status is not ...:
        value["status"] = status
    return value


G, Y, R, NA = "GREEN", "YELLOW", "RED", "N/A"


@pytest.mark.parametrize("token", ["Contract", "LegalObligation"])
def test_non_consent_tokens_green_r01_and_na_consent_rules(token):
    assert evaluate(form(lb(token)))[2] == [G, NA, NA, NA]


@pytest.mark.parametrize("token", ["Contract", "LegalObligation"])
def test_non_consent_ignores_consent_request_shape(token):
    assert evaluate(form(lb(token), consent_request={"planned": False}))[2] == [G, NA, NA, NA]
    assert evaluate(form(lb(token), consent_request=...))[2] == [G, NA, NA, NA]


def test_consent_existing_behaviour_kept():
    assert evaluate(form())[2] == [G, G, G, G]
    assert evaluate(form(consent_request={"planned": False}))[2] == [G, R, R, R]
    assert evaluate(form(consent_request=...))[2] == [G, Y, Y, Y]


@pytest.mark.parametrize("token", ["Consent", "Contract", "LegalObligation"])
def test_status_unknown_never_confirms(token):
    facts, _, status = evaluate(form(lb(token, "unknown")))
    f302 = next(x for x in facts if x["fact_id"].startswith("F3-02"))
    assert f302["value_state"] == "unknown"
    assert status == [Y, Y, Y, Y]


def test_consent_unknown_with_planned_false_is_not_red():
    facts, _, status = evaluate(form(lb("Consent", "unknown"), consent_request={"planned": False}))
    assert next(x for x in facts if x["fact_id"].startswith("F3-03"))["value_state"] == "confirmed"
    assert status == [Y, Y, Y, Y]


@pytest.mark.parametrize("status", ["planned", "confirmed", ...])
def test_status_confirmed_like_values(status):
    facts, _, result = evaluate(form(lb("Contract", status)))
    assert next(x for x in facts if x["fact_id"].startswith("F3-02"))["value_state"] == "confirmed"
    assert result == [G, NA, NA, NA]


@pytest.mark.parametrize("bad", ["maybe", "absent", "", None, 1, "Confirmed"])
def test_unsupported_status_is_input_error(bad):
    with pytest.raises(Poc3FormError):
        build_poc3_facts(form(lb("Consent", bad)))
    with pytest.raises(ComplianceInputError):
        run_design_check(form(lb("Consent", bad)))


@pytest.mark.parametrize("text", ["비동의", "동의 안함", "동의", "계약 이행"])
def test_korean_text_is_not_consent(text):
    # exact-token matching only: no substring and no Korean alias
    _, mapped, status = evaluate(form(lb(text), consent_request={"planned": False}))
    assert not list(mapped.graph.subjects(RDF.type, URIRef(PIPA + "Consent")))
    assert status == [Y, Y, Y, Y]


@pytest.mark.parametrize("text", ["CONSENT", " consent ", "consent"])
def test_consent_token_normalization(text):
    assert evaluate(form(lb(text)))[2] == [G, G, G, G]
    assert evaluate(form(lb(text), consent_request={"planned": False}))[2] == [G, R, R, R]


@pytest.mark.parametrize("text", ["contract", " LEGALOBLIGATION "])
def test_non_consent_token_normalization(text):
    assert evaluate(form(lb(text)))[2] == [G, NA, NA, NA]


@pytest.mark.parametrize("text", ["Contrct", "미지정", "LegitimateInterest", "legal obligation", "Contract Law", ""])
def test_unregistered_or_malformed_types_stay_yellow(text):
    if text == "":
        with pytest.raises(Exception):
            evaluate(form(lb(text)))
        return
    assert evaluate(form(lb(text)))[2] == [Y, Y, Y, Y]


def test_string_legal_basis_path_kept():
    assert evaluate(form("Consent"))[2] == [G, G, G, G]
    assert evaluate(form("Contract"))[2] == [G, NA, NA, NA]
    assert evaluate(form("unknown-token"))[2] == [Y, Y, Y, Y]


def test_no_new_ontology_class_and_label_links_to_activity():
    _, mapped, _ = evaluate(form(lb(" contract ")))
    g = mapped.graph
    bases = list(g.objects(None, URIRef(PIPA + "hasLegalBasis")))
    assert len(bases) == 1
    assert set(g.objects(bases[0], RDF.type)) == {URIRef(PIPA + "LegalBasis")}
    assert [str(x) for x in g.objects(bases[0], RDFS.label)] == ["Contract"]
    assert not list(g.subjects(RDF.type, URIRef(PIPA + "Contract")))


def test_p3_18_like_input_unchanged():
    f = form({"type": "미지정", "status": "unknown"}, purpose=" ")
    assert evaluate(f)[2] == [Y, Y, Y, Y]
