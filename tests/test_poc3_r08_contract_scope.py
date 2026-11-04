"""P3-R08: required-Fact envelope gaps are judged per activity, not per document."""

import copy
import json
from pathlib import Path

import pytest
from rdflib import RDF, Namespace, URIRef

from app.builders.poc3_fact_builder import build_poc3_facts
from app.mapping.ontology_mapper import OntologyMapper
from app.rules.engine import P0RuleEngine
from app.services.compliance import run_design_check

PIPA = Namespace("https://w3id.org/pipa-compliance/ontology#")
EVALS = Path(__file__).resolve().parents[1] / "evals" / "poc3"
ABSENT = {"state": "absent"}
METHOD = "관련 DB 레코드 영구 삭제"
G, Y, R = "GREEN", "YELLOW", "RED"

ACTIVITY = {
    "activity_id": "A-1",
    "purpose": "회원 인증 및 주문내역 조회",
    "legal_basis": {"type": "Consent", "status": "confirmed"},
    "consent_request": {"planned": True},
    "personal_information_items": [
        {"item_name": "이메일 주소", "is_required": True, "design_rationale": "계정 식별 및 본인 인증"}
    ],
    "retention": {},
    "denies_service_on_optional_refusal": False,
}
FULL = {"end_condition": "회원 탈퇴 완료 시", "destruction_method": METHOD}
# The three A1 designs whose R08 verdict must not depend on the other activities.
A1_DESIGNS = {
    "dest-key-missing": {"end_condition": "회원 탈퇴 완료 시"},
    "dest-empty": {"end_condition": "회원 탈퇴 완료 시", "destruction_method": ""},
    "period-only": {"period": "3년"},
}


def form(*retentions):
    f = {"analysis_id": "Q-SC", "controller": {"controller_id": "QA", "name": "QA"},
         "collection_activities": [], "entrusted_processings": []}
    for i, retention in enumerate(retentions, 1):
        a = copy.deepcopy(ACTIVITY)
        a["activity_id"] = f"A-{i}"
        a["retention"] = retention
        f["collection_activities"].append(a)
    return f


def evaluate(f, mutate=None):
    """P3-R08 result via the real pipeline; ``mutate`` edits the built Facts (to reach unknown)."""
    facts = build_poc3_facts(f)
    if mutate:
        mutate(facts)
    mapped = OntologyMapper(f["analysis_id"], controller_id="QA", controller_name="QA").map(facts)
    return next(r for r in P0RuleEngine().evaluate_mapping_result(mapped, poc="PoC3") if r.rule_id == "P3-R08")


def unknown_f311(activity_id):
    def mutate(facts):
        for fact in facts:
            if fact["fact_id"].startswith("F3-11") and fact["activity_id"] == activity_id:
                fact["value_state"], fact["value"] = "unknown", None
    return mutate


def verdicts(result):
    return {i.instance_id.rsplit("/", 1)[-1]: i.status.value for i in result.instance_results}


def reasons(result):
    return {i.instance_id.rsplit("/", 1)[-1]: i.reason for i in result.instance_results}


# --- three A1 designs x four configurations --------------------------------
@pytest.mark.parametrize("design", A1_DESIGNS)
def test_a1_is_yellow_in_every_configuration(design):
    a1 = A1_DESIGNS[design]
    assert verdicts(evaluate(form(a1))) == {"A-1": Y}
    assert verdicts(evaluate(form(a1, FULL))) == {"A-1": Y, "A-2": G}
    assert verdicts(evaluate(form(a1, FULL), unknown_f311("A-2"))) == {"A-1": Y, "A-2": Y}
    absent_a2 = {"end_condition": "회원 탈퇴 완료 시", "destruction_method": ABSENT}
    assert verdicts(evaluate(form(a1, absent_a2))) == {"A-1": Y, "A-2": R}


@pytest.mark.parametrize("design", A1_DESIGNS)
def test_activity_order_does_not_change_each_verdict(design):
    a1 = A1_DESIGNS[design]
    assert verdicts(evaluate(form(FULL, a1))) == {"A-1": G, "A-2": Y}
    assert verdicts(evaluate(form(a1, FULL))) == {"A-1": Y, "A-2": G}


def test_many_activities_keep_their_own_facts():
    absent = {"end_condition": "탈퇴 시", "destruction_method": ABSENT}
    f = form(A1_DESIGNS["dest-key-missing"], absent, FULL, FULL, {})
    result = evaluate(f, unknown_f311("A-4"))
    assert verdicts(result) == {"A-1": Y, "A-2": R, "A-3": G, "A-4": Y, "A-5": Y}
    assert result.status.value == R   # RED > YELLOW > GREEN


def test_summary_status_is_worst_instance():
    assert evaluate(form(A1_DESIGNS["period-only"], FULL)).status.value == Y
    assert evaluate(form(FULL, FULL)).status.value == G


# --- priority of absent / unknown / missing ---------------------------------
def test_absent_beats_missing_in_same_activity():
    # F3-10 absent, F3-11 not created (method concrete): RED, other activity untouched
    f = form({"end_condition": ABSENT, "destruction_method": METHOD}, FULL)
    assert verdicts(evaluate(f)) == {"A-1": R, "A-2": G}


def test_unknown_beats_missing_and_stays_yellow():
    f = form(FULL, FULL)
    assert verdicts(evaluate(f, unknown_f311("A-1"))) == {"A-1": Y, "A-2": G}


def test_activity_without_any_retention_design_is_yellow_next_to_complete_one():
    assert verdicts(evaluate(form({}, FULL))) == {"A-1": Y, "A-2": G}
    assert verdicts(evaluate(form({}, {}))) == {"A-1": Y, "A-2": Y}


# --- legacy (not linked to an activity) R08 instance keeps document scope ---
def test_legacy_unlinked_end_condition_keeps_document_level_judgement():
    f = form(FULL)
    facts = build_poc3_facts(f)
    mapped = OntologyMapper("Q-SC", controller_id="QA", controller_name="QA").map(facts)
    orphan = URIRef("https://example.org/orphan-end")
    mapped.graph.add((orphan, RDF.type, PIPA.RetentionEndCondition))
    mapped.graph.add((orphan, PIPA.hasEndConditionDescription, __import__("rdflib").Literal("고아 종료조건")))
    result = P0RuleEngine().evaluate_rule(mapped.graph, "P3-R08", facts=mapped.facts)
    by_key = {i.instance_id.rsplit("/", 1)[-1]: i.status.value for i in result.instance_results}
    # Facts of A-1 exist in the document, so the unlinked instance is not rewritten
    # to a missing-envelope YELLOW: it keeps its graph verdict (end without destruction).
    assert by_key["orphan-end"] == R
    assert by_key["A-1"] == G


# --- reasons follow the real Fact state ---------------------------------------
def first_reason(f, activity="A-1", mutate=None):
    return reasons(evaluate(f, mutate))[activity]


def assert_clean(reason):
    assert "존재/부재를 확정할 수 없습니다" not in reason
    assert "F3-" not in reason and "Frozen Fact input contract" not in reason


def test_reason_end_condition_absent_with_concrete_method():
    reason = first_reason(form({"end_condition": ABSENT, "destruction_method": METHOD}))
    assert reason.startswith("파기 방법은 입력되었으나 보유 종료조건이 명시적으로 없어, 종료조건과 파기 방법의 연결을 확인할 수 없습니다.")
    assert_clean(reason)


def test_reason_end_condition_absent_without_method_does_not_claim_method_was_input():
    reason = first_reason(form({"end_condition": ABSENT, "destruction_method": ABSENT}))
    assert "파기 방법은 입력되었으나" not in reason
    assert "보유 종료조건이 명시적으로 없음(absent)" in reason
    assert "파기 방법이 명시적으로 없음(absent)" in reason
    assert_clean(reason)


def test_reason_method_absent_only():
    reason = first_reason(form({"end_condition": "탈퇴 시", "destruction_method": ABSENT}))
    assert "파기 방법이 명시적으로 없음(absent)" in reason and "종료조건이 명시적으로 없" not in reason
    assert_clean(reason)


def test_reason_unknown_method():
    reason = first_reason(form(FULL), mutate=unknown_f311("A-1"))
    assert "파기 방법이 미정(unknown)" in reason and "absent" not in reason
    assert_clean(reason)


def test_reason_unknown_end_condition():
    def mutate(facts):
        for fact in facts:
            if fact["fact_id"].startswith("F3-10"):
                fact["value_state"], fact["value"] = "unknown", None
    reason = first_reason(form(FULL), mutate=mutate)
    assert "보유 종료조건이 미정(unknown)" in reason and "absent" not in reason
    assert_clean(reason)


@pytest.mark.parametrize("design", A1_DESIGNS)
def test_reason_missing_envelope_is_not_absent(design):
    reason = first_reason(form(A1_DESIGNS[design], FULL))
    assert "필수 Fact 누락" in reason and "absent(없음 명시)와 다릅니다" in reason
    assert "명시적으로 없" not in reason
    assert_clean(reason)


def test_reason_activity_without_retention_design():
    reason = first_reason(form({}, FULL))
    assert "보유 종료조건·파기 설계가 입력되지 않아" in reason
    assert_clean(reason)


def test_vague_destruction_reason_is_untouched():
    vague = {"end_condition": "탈퇴 시", "destruction_method": "적절한 방법으로 처리"}
    assert "일반어만으로 구성된" in first_reason(form(vague, FULL))


# --- evaluation inputs stay as before ------------------------------------------
def test_explicit_absent_evaluation_inputs_unchanged():
    expected = {
        "p3_16_explicit_absent.json": {"P3-R04": R, "P3-R08": R},
        "p3_19_explicit_absent.json": {"P3-R03": R, "P3-R05": R, "P3-R08": R, "P3-R11": R},
        "p3_20_explicit_absent.json": {"P3-R05": R, "P3-R06": R, "P3-R08": R, "P3-R11": R},
    }
    for name, want in expected.items():
        got = {r.rule_id: r.status.value for r in run_design_check(json.loads((EVALS / name).read_text(encoding="utf-8")))}
        assert {k: got[k] for k in want} == want, name
