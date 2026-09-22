"""평가 세트 탐색 · Rule-level 채점 · 부재 단언 추출 테스트.

LLM을 호출하지 않는다. Pass 1 응답을 스텁으로 주고 후처리만 검증한다.
"""

import json
from pathlib import Path

import pytest

from app.extractors.poc1 import (
    ABSENCE_FACT_ID,
    CONTROLLER_ID,
    AbsentActivityClass,
    ActivityList,
    IdentifiedActivity,
    PoC1Extractor,
)
from app.facts.graph import facts_to_graph
from app.mapping.fact_schema import ABSENT_ACTIVITY_KEY
from app.facts.models import FactEnvelope
from app.facts.validator import validate_facts
from app.rules.engine import P0RuleEngine
from evals.dataset import load_poc1_cases
from evals.run_extraction import _accumulate
from evals.score import RuleScore, Score, score_facts

V6 = "v6-no-third-party-provision"
ABSENCE_QUOTE = "회사는 이용자의 개인정보를 제3자에게 제공하지 않습니다."


# --- 데이터셋 -----------------------------------------------------------


def test_sweep_covers_the_base_document_and_every_variant():
    cases = load_poc1_cases()
    assert len(cases) == 7
    assert cases[0].name == "base"
    assert {case.name for case in cases[1:]} == {
        "v1-missing-purpose", "v2-vague-destruction", "v3-missing-destruction",
        "v4-unknown-processor", "v5-missing-processor", V6,
    }


def test_every_case_carries_a_document_and_expected_statuses():
    for case in load_poc1_cases():
        assert case.document.strip()
        assert set(case.expected_rule_status) == {
            "P1-R01", "P1-R02", "P1-R03", "P1-R04", "P1-R06", "P1-R07"
        }


def test_gold_facts_of_every_case_validate_against_their_own_document():
    for case in load_poc1_cases():
        assert validate_facts(case.gold_facts, document=case.document)


# --- Rule-level 채점 ----------------------------------------------------


def test_perfect_prediction_scores_full_agreement():
    score = RuleScore()
    for case in load_poc1_cases():
        score.add(case.name, case.expected_rule_status, case.expected_rule_status)
    assert score.total == 42
    assert score.agreement == 1.0
    assert score.false_greens == []


def test_predicting_green_everywhere_is_caught_as_dangerous():
    """무용한 추출기의 기준선.

    전부 GREEN이라고 우겨도 일치율은 0.69가 나온다. 그래서 일치율만 보면 안 되고
    위험 오판율(gold가 GREEN이 아닌데 GREEN으로 예측)을 같이 봐야 한다.
    """
    score = RuleScore()
    for case in load_poc1_cases():
        score.add(
            case.name,
            case.expected_rule_status,
            {rule: "GREEN" for rule in case.expected_rule_status},
        )
    assert 0.6 < score.agreement < 0.75
    assert len(score.false_greens) == 13
    assert score.false_green_rate > 0.3


def test_missing_prediction_is_a_mismatch_not_a_pass():
    score = RuleScore()
    score.add("c", {"P1-R01": "GREEN"}, {})
    assert score.agree == 0
    assert score.mismatches == [("c", "P1-R01", "GREEN", "(없음)")]


def test_amber_predicted_as_red_is_a_mismatch_but_not_a_false_green():
    score = RuleScore()
    score.add("c", {"P1-R02": "AMBER"}, {"P1-R02": "RED"})
    assert score.mismatches and not score.false_greens


def test_fact_scores_accumulate_across_cases():
    total = Score()
    for case in load_poc1_cases():
        gold = [FactEnvelope.model_validate(item) for item in case.gold_facts]
        _accumulate(total, score_facts(gold, gold, case.document))
    assert total.gold_total == sum(len(case.gold_facts) for case in load_poc1_cases())
    assert total.f1 == 1.0
    assert total.offset_accuracy == 1.0
    assert total.hallucination_rate == 0.0


# --- 부재 단언 추출 -----------------------------------------------------


class StubMessages:
    def __init__(self, responses):
        self.responses = list(responses)

    def parse(self, **kwargs):
        payload = self.responses.pop(0)
        return type("Response", (), {"parsed_output": payload, "stop_reason": "end_turn"})()


def empty_facts():
    return type("FactList", (), {"facts": []})()


def extract_with(pass1: ActivityList, document: str):
    # Pass 1 + 처리행위 수만큼의 Pass 2 + 권리 1회
    responses = [pass1] + [empty_facts()] * (len(pass1.activities) + 1)
    return PoC1Extractor(StubMessages(responses)).extract(document)


@pytest.fixture(scope="module")
def v6_case():
    return next(case for case in load_poc1_cases() if case.name == V6)


def test_absence_fact_is_built_from_pass_one(v6_case):
    result = extract_with(
        ActivityList(
            activities=[],
            absent_activity_classes=[
                AbsentActivityClass(
                    ontology_class="ThirdPartyProvision", evidence_text=ABSENCE_QUOTE
                )
            ],
        ),
        v6_case.document,
    )
    assert len(result.facts) == 1
    fact = FactEnvelope.model_validate(result.facts[0])
    assert fact.fact_type == ABSENCE_FACT_ID
    assert fact.subject_id == CONTROLLER_ID
    assert fact.value == {ABSENT_ACTIVITY_KEY: "ThirdPartyProvision"}
    assert fact.value_state == "confirmed"
    assert fact.evidence[0].resolves_in(v6_case.document)


@pytest.mark.parametrize(
    "label, absence, expected_reason",
    [
        (
            "원문에 없는 인용",
            AbsentActivityClass(
                ontology_class="ThirdPartyProvision", evidence_text="원문에 없는 선언 문장"
            ),
            "찾지 못했",
        ),
        (
            "부재를 단언할 수 없는 유형",
            AbsentActivityClass(
                ontology_class="CollectionAndUse", evidence_text=ABSENCE_QUOTE
            ),
            "단언할 수 없는 유형",
        ),
    ],
)
def test_absence_guards_reject_bad_assertions(v6_case, label, absence, expected_reason):
    """부재 단언은 잘못 만들면 비용이 크다. 없는 것을 없다고 확정해 버린다."""
    result = extract_with(
        ActivityList(activities=[], absent_activity_classes=[absence]), v6_case.document
    )
    assert result.facts == [], label
    assert any(expected_reason in item.reason for item in result.rejected), label


def test_claiming_a_class_is_both_present_and_absent_is_rejected(v6_case):
    result = extract_with(
        ActivityList(
            activities=[
                IdentifiedActivity(
                    activity_id="act-provision-001",
                    ontology_class="ThirdPartyProvision",
                    heading="제공받는 자",
                )
            ],
            absent_activity_classes=[
                AbsentActivityClass(
                    ontology_class="ThirdPartyProvision", evidence_text=ABSENCE_QUOTE
                )
            ],
        ),
        v6_case.document,
    )
    assert not any(item["fact_id"].startswith(ABSENCE_FACT_ID) for item in result.facts)
    assert any("동시에" in item.reason or "부재로도" in item.reason for item in result.rejected)


def test_extracted_absence_fact_actually_produces_na(v6_case):
    """이 Fact가 있어야 P1-R03이 N/A가 된다. 없으면 AMBER로 남는다."""
    result = extract_with(
        ActivityList(
            activities=[],
            absent_activity_classes=[
                AbsentActivityClass(
                    ontology_class="ThirdPartyProvision", evidence_text=ABSENCE_QUOTE
                )
            ],
        ),
        v6_case.document,
    )
    others = [
        item for item in v6_case.gold_facts
        if not item["fact_id"].startswith(ABSENCE_FACT_ID)
    ]
    facts = validate_facts(others + result.facts, document=v6_case.document)
    statuses = {
        item.rule_id: item.status.value
        for item in P0RuleEngine().evaluate_graph(facts_to_graph(facts), poc="poc1")
    }
    assert statuses == v6_case.expected_rule_status


def test_prompt_documents_every_absence_eligible_class():
    from app.extractors.prompts import ABSENCE_ELIGIBLE_CLASSES, PASS1_SYSTEM

    for name in ABSENCE_ELIGIBLE_CLASSES:
        assert name in PASS1_SYSTEM
    assert "absent_activity_classes" in PASS1_SYSTEM
    # 미기재와 명시적 부재를 구분하라는 지침이 빠지면 N/A를 남발하게 된다
    assert "미기재" in PASS1_SYSTEM
