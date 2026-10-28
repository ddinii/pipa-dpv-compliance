"""평가 세트 탐색 · Rule-level 채점 · 부재 단언 추출 테스트.

LLM을 호출하지 않는다. Pass 1 응답을 스텁으로 주고 후처리만 검증한다.
"""

import json
from pathlib import Path

import pytest

from app.extractors.poc1 import (
    ActivityList,
    IdentifiedActivity,
    PoC1Extractor,
)
from app.facts.graph import facts_to_graph, facts_to_mapping
from app.facts.models import FactEnvelope
from app.facts.validator import validate_facts
from app.rules.engine import P0RuleEngine
from evals.dataset import POC_DATASETS, load_cases, load_poc1_cases
from evals.run_extraction import _accumulate
from evals.score import RuleScore, Score, score_facts

V6 = "v6-no-third-party-provision"


# --- 데이터셋 -----------------------------------------------------------


def test_sweep_covers_the_base_document_and_every_variant():
    cases = load_poc1_cases()
    assert len(cases) == 10
    assert cases[0].name == "base"
    assert {case.name for case in cases[1:]} == {
        "v1-missing-purpose", "v2-vague-destruction", "v3-missing-destruction",
        "v4-unknown-processor", "v5-missing-processor", V6,
        "v7-complete-cross-border", "v8-complete-privacy-officer", "v9-no-cross-border-transfer",
    }


def test_every_case_carries_a_document_and_expected_statuses():
    for case in load_poc1_cases():
        assert case.document.strip()
        assert set(case.expected_rule_status) == {
            "P1-R01", "P1-R02", "P1-R03", "P1-R04", "P1-R06", "P1-R07", "P1-R08",
            "P1-R09", "P1-R10",
        }


def test_gold_facts_of_every_case_validate_against_their_own_document():
    for case in load_poc1_cases():
        assert validate_facts(case.gold_facts, document=case.document)


# --- Rule-level 채점 ----------------------------------------------------


def test_perfect_prediction_scores_full_agreement():
    score = RuleScore()
    for case in load_poc1_cases():
        score.add(case.name, case.expected_rule_status, case.expected_rule_status)
    assert score.total == 90  # 10건 x 9 Rule
    assert score.agreement == 1.0
    assert score.false_greens == []


def test_predicting_green_everywhere_is_caught_as_dangerous():
    """무용한 추출기의 기준선.

    전부 GREEN이라고 우겨도 일치율은 약 0.62가 나온다 (v1.1 P1-R09/R10 추가 전에는 0.73). 그래서 일치율만 보면 안 되고
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
    assert len(score.false_greens) == 34
    assert score.false_green_rate > 0.25


def test_missing_prediction_is_a_mismatch_not_a_pass():
    score = RuleScore()
    score.add("c", {"P1-R01": "GREEN"}, {})
    assert score.agree == 0
    assert score.mismatches == [("c", "P1-R01", "GREEN", "(없음)")]


def test_yellow_predicted_as_red_is_a_mismatch_but_not_a_false_green():
    score = RuleScore()
    score.add("c", {"P1-R02": "YELLOW"}, {"P1-R02": "RED"})
    assert score.mismatches and not score.false_greens


@pytest.mark.parametrize("expected", ["RED", "YELLOW"])
def test_na_that_hides_a_finding_is_counted_as_dangerous(expected: str):
    """잘못된 부재 선언은 Rule을 판정 대상에서 빼 버린다. GREEN만큼 위험하다."""
    score = RuleScore()
    score.add("c", {"P1-R03": expected}, {"P1-R03": "N/A"})
    assert score.false_nas == [("c", "P1-R03", expected)]
    assert score.false_na_rate == 1.0
    assert not score.false_greens


def test_na_in_place_of_green_is_a_mismatch_but_not_dangerous():
    """GREEN을 N/A로 내면 틀렸지만 가려진 결함은 없다."""
    score = RuleScore()
    score.add("c", {"P1-R03": "GREEN"}, {"P1-R03": "N/A"})
    assert score.mismatches and not score.false_nas


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


# --- PoC 등록 ------------------------------------------------------------


def test_every_registered_poc_dataset_actually_loads():
    """POC_DATASETS에 등록만 해두고 파일이 없으면 즉시 드러나야 한다.

    조용히 빈 세트를 돌려주면 "0건 평가 통과"가 되어 채점이 무의미해진다.
    """
    for poc in POC_DATASETS:
        cases = load_cases(poc)
        assert cases, poc
        assert all(case.poc == poc for case in cases)


def test_unregistered_poc_fails_loudly():
    with pytest.raises(ValueError, match="POC_DATASETS"):
        load_cases("poc9")


def test_runner_refuses_a_poc_without_an_extractor():
    """평가 세트는 있는데 Extractor가 없는 PoC를 실수로 돌리지 않도록."""
    from evals.run_extraction import EXTRACTORS

    assert set(EXTRACTORS) <= set(POC_DATASETS)
    for poc in EXTRACTORS:
        assert load_cases(poc)
