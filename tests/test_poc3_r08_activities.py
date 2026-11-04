"""P3-R08 is evaluated per CollectionAndUse activity (no cross-activity effects)."""

import copy

from app.builders.poc3_fact_builder import build_poc3_facts
from app.mapping.ontology_mapper import OntologyMapper
from app.rules.engine import P0RuleEngine
from app.services.compliance import run_design_check

ACTIVITY = {
    "activity_id": "A-1",
    "purpose": "회원 인증 및 주문내역 조회",
    "legal_basis": {"type": "Consent", "status": "confirmed"},
    "consent_request": {"planned": True},
    "personal_information_items": [
        {"item_name": "이메일 주소", "is_required": True, "design_rationale": "계정 식별 및 본인 인증"}
    ],
    "retention": {"end_condition": "회원 탈퇴 완료 시", "destruction_method": "관련 DB 레코드 영구 삭제"},
    "denies_service_on_optional_refusal": False,
}
EMPTY = {"end_condition": "", "destruction_method": ""}
G, Y, R = "GREEN", "YELLOW", "RED"


def form(*retentions):
    """One activity per retention design (A-1, A-2, ...)."""
    f = {"analysis_id": "Q-R08", "controller": {"controller_id": "QA", "name": "QA"},
         "collection_activities": [], "entrusted_processings": []}
    for i, retention in enumerate(retentions, 1):
        a = copy.deepcopy(ACTIVITY)
        a["activity_id"] = f"A-{i}"
        a["purpose"] = f"목적 {i} 회원 인증"
        a["retention"] = retention
        f["collection_activities"].append(a)
    return f


FULL = ACTIVITY["retention"]


def r08(f):
    return next(r for r in run_design_check(f) if r.rule_id == "P3-R08")


def by_activity(f):
    return {i.instance_id.rsplit("/", 1)[-1]: i.status.value for i in r08(f).instance_results}


def test_single_activity_without_retention_design():
    assert by_activity(form(EMPTY)) == {"A-1": Y}


def test_missing_activity_is_not_hidden_by_complete_one():
    assert by_activity(form(EMPTY, FULL)) == {"A-1": Y, "A-2": G}


def test_all_activities_without_retention_are_listed():
    assert by_activity(form(EMPTY, EMPTY)) == {"A-1": Y, "A-2": Y}


def test_explicit_absent_does_not_contaminate_other_activity():
    absent = {"end_condition": "탈퇴 시", "destruction_method": {"state": "absent"}}
    assert by_activity(form(absent, FULL)) == {"A-1": R, "A-2": G}


def test_unknown_fact_is_scoped_to_its_activity():
    f = form(FULL, FULL)
    facts = build_poc3_facts(f)
    for fact in facts:
        if fact["fact_id"].startswith("F3-11") and fact["activity_id"] == "A-1":
            fact["value_state"], fact["value"] = "unknown", None
    mapped = OntologyMapper("Q", controller_id="QA", controller_name="QA").map(facts)
    res = next(r for r in P0RuleEngine().evaluate_mapping_result(mapped, poc="PoC3") if r.rule_id == "P3-R08")
    assert {i.instance_id.rsplit("/", 1)[-1]: i.status.value for i in res.instance_results} == {"A-1": Y, "A-2": G}


def test_vague_destruction_method_is_scoped_to_its_activity():
    vague = {"end_condition": "탈퇴 시", "destruction_method": "적절한 방법으로 처리"}
    f = form(vague, FULL)
    assert by_activity(f) == {"A-1": Y, "A-2": G}
    reasons = [i.reason for i in r08(f).instance_results if i.status.value == Y]
    assert any("일반어만으로 구성된" in x for x in reasons)


def test_empty_destruction_method_keeps_existing_contract_per_activity():
    no_method = {"end_condition": "탈퇴 시", "destruction_method": ""}
    assert by_activity(form(no_method, FULL)) == {"A-1": R, "A-2": G}


def test_period_only_retention_is_red_for_that_activity():
    assert by_activity(form({"period": "3년"}, FULL)) == {"A-1": R, "A-2": G}


def test_activity_order_does_not_change_verdicts():
    absent = {"end_condition": "탈퇴 시", "destruction_method": {"state": "absent"}}
    a = by_activity(form(EMPTY, FULL, absent))
    f = form(absent, FULL, EMPTY)           # same designs, reversed order -> ids swap
    b = by_activity(f)
    assert sorted(a.values()) == sorted(b.values()) == sorted([Y, G, R])
    assert a == {"A-1": Y, "A-2": G, "A-3": R}
    assert b == {"A-1": R, "A-2": G, "A-3": Y}


def test_summary_status_follows_priority_and_matches_instances():
    result = r08(form(EMPTY, FULL))
    assert result.status.value == Y
    assert sorted(i.status.value for i in result.instance_results) == [G, Y]
    assert r08(form(FULL, FULL)).status.value == G


def test_instance_id_is_activity_uri_with_label_and_no_mixing():
    f = form(
        {"end_condition": "탈퇴 시", "destruction_method": {"state": "absent"}}, FULL
    )
    result = r08(f)
    ids = [i.instance_id for i in result.instance_results]
    assert len(set(ids)) == 2 and all(x.endswith(("/A-1", "/A-2")) for x in ids)
    a2 = next(i for i in result.instance_results if i.instance_id.endswith("/A-2"))
    assert a2.instance_label == "목적 2 회원 인증"
    mentioned = " ".join([*a2.matched_facts, *a2.missing_facts, *a2.uncertain_facts])
    assert "A-1" not in mentioned
