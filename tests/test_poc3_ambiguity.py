"""PoC3 field-specific concreteness checks (generic-only phrases, undetermined processor).

This is a limited static check of how specific a stated phrase is. It does not
verify legal adequacy, and Facts stay confirmed (only Rule results change).
"""

import copy

import pytest
from rdflib import Graph, Literal, Namespace, RDF

from app.builders.poc3_fact_builder import build_poc3_facts
from app.mapping.ontology_mapper import OntologyMapper
from app.rules.engine import P0RuleEngine
from app.services.compliance import run_design_check

PIPA = Namespace("https://w3id.org/pipa-compliance/ontology#")

BASE = {
    "analysis_id": "Q-AMB",
    "controller": {"controller_id": "QA", "name": "QA"},
    "collection_activities": [
        {
            "activity_id": "A-1",
            "purpose": "회원 인증 및 주문내역 조회",
            "legal_basis": {"type": "Consent", "status": "confirmed"},
            "consent_request": {"planned": True},
            "personal_information_items": [
                {"item_name": "이메일 주소", "is_required": True, "design_rationale": "계정 식별 및 본인 인증"},
                {"item_name": "관심분야", "is_required": False, "design_rationale": "선택적 개인화 추천"},
            ],
            "retention": {"end_condition": "회원 탈퇴 완료 시", "destruction_method": "관련 DB 레코드 영구 삭제"},
            "denies_service_on_optional_refusal": False,
        }
    ],
    "entrusted_processings": [
        {"activity_id": "ENT-1", "processor": "가온클라우드 주식회사", "task": "클라우드 DB 운영 및 백업"}
    ],
}
G, Y = "GREEN", "YELLOW"


def act(f, i=0):
    return f["collection_activities"][i]


def build(mut=None):
    f = copy.deepcopy(BASE)
    if mut:
        mut(f)
    return f


def result(f, rule):
    return next(r for r in run_design_check(f) if r.rule_id == rule)


def status(mut, rule):
    return result(build(mut), rule).status.value


def instances(mut, rule):
    return sorted(i.status.value for i in result(build(mut), rule).instance_results)


def set_purpose(t): return lambda f: act(f).__setitem__("purpose", t)
def set_name(i, t): return lambda f: act(f)["personal_information_items"][i].__setitem__("item_name", t)
def set_rat(i, t): return lambda f: act(f)["personal_information_items"][i].__setitem__("design_rationale", t)
def set_ret(k, t): return lambda f: act(f)["retention"].__setitem__(k, t)
def set_ent(k, t): return lambda f: f["entrusted_processings"][0].__setitem__(k, t)


# --- baseline ---------------------------------------------------------------
def test_baseline_all_green():
    assert {r.rule_id: r.status.value for r in run_design_check(build())} == {
        "P3-R01": G, "P3-R02": G, "P3-R03": G, "P3-R04": G, "P3-R05": G,
        "P3-R06": G, "P3-R08": G, "P3-R11": G,
    }


# --- the 8 evaluation cases -------------------------------------------------
@pytest.mark.parametrize(
    "mut,rule",
    [
        (set_purpose("서비스 운영 등 필요한 목적"), "P3-R02"),      # P3-06
        (set_name(0, "기타 개인정보"), "P3-R03"),                   # P3-07
        (set_ret("end_condition", "필요 시"), "P3-R04"),            # P3-08
        (set_ret("destruction_method", "적절한 방법으로 처리"), "P3-R08"),  # P3-08
        (set_rat(0, "필요한 운영 목적으로 수집"), "P3-R05"),        # P3-09
        (set_ent("processor", "수탁업체 협의 중"), "P3-R11"),       # P3-10
        (set_ent("task", "관련 업무"), "P3-R11"),                   # P3-11
        (set_purpose("다양한 서비스 목적"), "P3-R02"),              # P3-15
    ],
)
def test_target_cases_are_yellow(mut, rule):
    assert status(mut, rule) == Y


def test_facts_stay_confirmed_when_phrase_is_vague():
    f = build(set_purpose("다양한 서비스 목적"))
    assert {x["value_state"] for x in build_poc3_facts(f)} == {"confirmed"}


# --- over-detection guards: specific text containing generic words ---------
@pytest.mark.parametrize(
    "mut,rule",
    [
        (set_purpose("회원 인증 및 주문내역 조회"), "P3-R02"),
        (set_purpose("서비스 운영 등을 위한 주문 이력 조회"), "P3-R02"),
        (set_purpose("관련 법령에 따른 본인확인"), "P3-R02"),
        (set_name(0, "기타 결제수단 정보"), "P3-R03"),
        (set_ret("end_condition", "처리 목적 달성 시"), "P3-R04"),
        (set_ret("destruction_method", "해당 정보 삭제"), "P3-R08"),
        (set_ret("destruction_method", "DB 레코드 영구 삭제"), "P3-R08"),
        (set_ent("task", "기타 관련 업무 및 클라우드 DB 백업"), "P3-R11"),
        (set_ent("task", "클라우드 DB 운영 및 백업"), "P3-R11"),
        (set_ent("processor", "미정산업 주식회사"), "P3-R11"),
        (set_ent("processor", "TBDsoft 주식회사"), "P3-R11"),
    ],
)
def test_specific_text_is_not_over_detected(mut, rule):
    assert status(mut, rule) == G


# --- boundary cases decided with the user -----------------------------------
def test_generic_required_rationale_is_yellow():
    assert status(set_rat(0, "서비스 제공을 위해 필요"), "P3-R05") == Y


def test_target_destruction_phrases():
    assert status(set_ret("destruction_method", "적절한 방법으로 파기"), "P3-R08") == Y


def test_concrete_period_keeps_r04_green_with_vague_end_condition():
    def mut(f):
        set_ret("end_condition", "필요 시")(f)
        set_ret("period", "3년")(f)
    assert status(mut, "P3-R04") == G


def test_vague_end_condition_does_not_touch_r08():
    assert status(set_ret("end_condition", "필요 시"), "P3-R08") == G


def test_optional_item_rationale_does_not_affect_r05():
    assert status(set_rat(1, "기타 목적으로 이용"), "P3-R05") == G


def test_vague_item_name_does_not_affect_r05():
    assert status(set_name(0, "기타 개인정보"), "P3-R05") == G


# --- multiple items / activities -------------------------------------------
def test_only_one_of_several_items_vague():
    assert status(set_name(1, "각종 정보"), "P3-R03") == Y


def test_only_one_of_several_activities_vague():
    def mut(f):
        a2 = copy.deepcopy(act(f))
        a2["activity_id"] = "A-2"
        a2["purpose"] = "다양한 서비스 목적"
        f["collection_activities"].append(a2)
    assert instances(mut, "P3-R02") == [G, Y]
    assert status(mut, "P3-R02") == Y
    assert instances(mut, "P3-R03") == [G, G]


# --- processor states -------------------------------------------------------
@pytest.mark.parametrize("text", ["미정", "미확정", "TBD", "협의 중", "선정 중", "검토 중",
                                  "추후 결정", "추후 확정", "추후 지정", "결정 예정", "협의 예정",
                                  "A사 (계약 협의 중)", "가온클라우드 주식회사 (선정 중)"])
def test_processor_undetermined_markers(text):
    assert status(set_ent("processor", text), "P3-R11") == Y


@pytest.mark.parametrize("text", ["수탁업체", "외부 업체", "협력사"])
def test_processor_unspecific_nouns(text):
    assert status(set_ent("processor", text), "P3-R11") == Y


# --- reasons distinguish the cause ------------------------------------------
def reasons(mut, rule):
    # The cause is in the per-instance reason; the response schema is unchanged.
    return " ".join(i.reason for i in result(build(mut), rule).instance_results)


def test_reasons_distinguish_causes():
    assert "수탁자 미확정" in reasons(set_ent("processor", "수탁업체 협의 중"), "P3-R11")
    assert "수탁자 특정 불가" in reasons(set_ent("processor", "외부 업체"), "P3-R11")
    r = reasons(set_ent("task", "관련 업무"), "P3-R11")
    assert "(위탁업무 모호)" in r
    assert "(수탁자 미확정)" not in r and "(수탁자 특정 불가)" not in r
    assert "일반어만으로 구성된" in reasons(set_purpose("다양한 서비스 목적"), "P3-R02")
    assert "일반어만으로 구성된" in reasons(set_ret("end_condition", "필요 시"), "P3-R04")
    assert "일반어만으로 구성된" in reasons(set_ret("destruction_method", "적절한 방법으로 처리"), "P3-R08")
    assert "일반어만으로 구성된" in reasons(set_rat(0, "필요한 운영 목적으로 수집"), "P3-R05")


# --- documented limitations (NOT desired behaviour) --------------------------
@pytest.mark.parametrize(
    "mut,rule",
    [
        (set_name(0, "기타 개인정보 ABC"), "P3-R03"),
        (set_ent("task", "관련 업무 123"), "P3-R11"),
        (set_purpose("다양한 서비스 목적 X"), "P3-R02"),
    ],
)
def test_known_limitation_meaningless_extra_token_counts_as_specific(mut, rule):
    # Any token outside the closed generic list is treated as specific content.
    # Unresolved: whether stray ASCII letters / digits should be ignored.
    assert status(mut, rule) == G


def test_sentinel_strings_stay_confirmed_values():
    assert status(set_ent("task", "위탁업무 미지정"), "P3-R11") == G
    assert status(set_rat(0, "필요사유 미설계"), "P3-R05") == G


# --- shared helpers / PoC1 untouched -----------------------------------------
def test_nonempty_values_is_unchanged_for_generic_text():
    g = Graph()
    node = PIPA.x
    g.add((node, PIPA.entrustedTaskText, Literal("관련 업무")))
    assert P0RuleEngine()._nonempty_values(g, node, PIPA.entrustedTaskText) == [Literal("관련 업무")]


def test_poc1_retention_check_not_affected():
    g = Graph()
    activity, retention, end = PIPA.act, PIPA.ret, PIPA.end
    g.add((activity, RDF.type, PIPA.CollectionAndUse))
    g.add((activity, PIPA.hasRetention, retention))
    g.add((retention, RDF.type, PIPA.Retention))
    g.add((retention, PIPA.hasRetentionEndCondition, end))
    g.add((end, RDF.type, PIPA.RetentionEndCondition))
    g.add((end, PIPA.hasEndConditionDescription, Literal("필요 시")))
    assert P0RuleEngine().evaluate_rule(g, "P1-R02").status.value == G


# --- pure classifier ----------------------------------------------------------
def test_classifier_unit():
    from app.rules.ambiguity import classify

    assert classify("기타 개인정보", "item_name") == "generic_only"
    assert classify("이메일 주소", "item_name") is None
    assert classify("수탁업체 협의 중", "processor") == "processor_undetermined"
    assert classify("외부 업체", "processor") == "processor_unspecific"
    assert classify("가온클라우드 주식회사", "processor") is None
    assert classify("", "purpose") is None
    assert classify("  필요 시. ", "end_condition") == "generic_only"
