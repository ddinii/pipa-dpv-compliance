"""PoC1 Extractor 후처리와 Fact-level 채점기 테스트.

LLM을 호출하지 않는다. messages.parse를 스텁으로 갈아끼워 "모델이 이렇게 답했을 때
파이프라인이 무엇을 버리고 무엇을 남기는가"만 검증한다.
"""

import copy
import json
from pathlib import Path

import pytest

from app.extractors.poc1 import (
    ActivityList,
    ExtractedFact,
    IdentifiedActivity,
    PoC1Extractor,
    locate_quotes,
)
from app.facts.models import FactEnvelope
from evals.score import score_facts, value_supported_by

ROOT = Path(__file__).resolve().parents[1]
GOLD_PATH = ROOT / "evals" / "poc1" / "sc_p01_gold_facts.json"
POLICY_PATH = ROOT / "evals" / "poc1" / "sc_p01_policy.txt"


@pytest.fixture(scope="module")
def policy() -> str:
    return POLICY_PATH.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def gold_raw() -> list[dict]:
    return json.loads(GOLD_PATH.read_text(encoding="utf-8"))["facts"]


@pytest.fixture(scope="module")
def gold(gold_raw) -> list[FactEnvelope]:
    return [FactEnvelope.model_validate(item) for item in gold_raw]


# --- 인용 위치 찾기 -----------------------------------------------------


def test_locate_quotes_computes_offsets(policy: str):
    evidence, missing = locate_quotes(policy, ["회원 탈퇴 시"])
    assert missing is None
    piece = evidence[0]
    assert policy[piece["start_offset"] : piece["end_offset"]] == "회원 탈퇴 시"


def test_locate_quotes_reports_a_quote_that_is_not_in_the_document(policy: str):
    evidence, missing = locate_quotes(policy, ["회원 탈퇴 시", "이 문장은 원문에 없습니다"])
    assert evidence == []
    assert missing == "이 문장은 원문에 없습니다"


def test_repeated_quotes_get_different_offsets(policy: str):
    """배열 값의 원소별 근거가 같은 위치를 가리키면 안 된다."""
    evidence, missing = locate_quotes(policy, ["휴대전화번호", "휴대전화번호"])
    assert missing is None
    assert evidence[0]["start_offset"] != evidence[1]["start_offset"]


# --- Extractor 후처리 ---------------------------------------------------


class StubMessages:
    """messages.parse 스텁. 호출 순서대로 미리 준비한 응답을 돌려준다."""

    def __init__(self, responses: list):
        self.responses = list(responses)
        self.calls: list[dict] = []

    def parse(self, **kwargs):
        self.calls.append(kwargs)
        payload = self.responses.pop(0)
        return type("Response", (), {"parsed_output": payload, "stop_reason": "end_turn"})()


def make_extractor(responses: list) -> tuple[PoC1Extractor, StubMessages]:
    stub = StubMessages(responses)
    return PoC1Extractor(stub), stub


def activity_list(*activities, absent=()):
    """Pass 1 응답 스텁.

    덕 타이핑 대신 실제 ActivityList를 쓴다. 그래야 Pass 1 스키마가 바뀌었을 때
    스텁이 조용히 어긋나지 않고 여기서 같이 드러난다.
    """
    return ActivityList(activities=list(activities), absent_activity_classes=list(absent))


def fact_list(*facts):
    return type("FactList", (), {"facts": list(facts)})()


ACTIVITY = IdentifiedActivity(
    activity_id="act-collection-001",
    ontology_class="CollectionAndUse",
    heading="회원 가입 및 관리",
)


def test_extractor_builds_a_valid_envelope_with_computed_offsets(policy: str):
    purpose = "회원 식별·가입 의사 확인·회원 관리·부정이용 방지·고객 문의 처리"
    extractor, _ = make_extractor([
        activity_list(ACTIVITY),
        fact_list(ExtractedFact(
            fact_id="F1-02",
            activity_id="act-collection-001",
            ontology_property="hasPurpose",
            value=purpose,
            value_state="confirmed",
            evidence_text=[purpose],
        )),
        fact_list(),
    ])
    result = extractor.extract(policy)

    assert len(result.facts) == 1
    fact = FactEnvelope.model_validate(result.facts[0])
    assert fact.fact_type == "F1-02"
    assert fact.evidence[0].resolves_in(policy)


def test_extractor_rejects_a_quote_that_is_not_in_the_document(policy: str):
    """NFR-07: 원문에 없는 문장을 인용하면 그 Fact를 버린다."""
    extractor, _ = make_extractor([
        activity_list(ACTIVITY),
        fact_list(ExtractedFact(
            fact_id="F1-02",
            activity_id="act-collection-001",
            ontology_property="hasPurpose",
            value="마케팅 활용",
            value_state="confirmed",
            evidence_text=["회사는 마케팅 목적으로 개인정보를 이용합니다."],
        )),
        fact_list(),
    ])
    result = extractor.extract(policy)

    assert result.facts == []
    assert len(result.rejected) == 1
    assert "찾지 못했" in result.rejected[0].reason
    assert result.hallucination_rate == 1.0


def test_extractor_rejects_a_fact_tagged_with_another_activity(policy: str):
    """COM-003: 요청한 처리행위가 아닌 activity_id를 붙여 오면 버린다."""
    extractor, _ = make_extractor([
        activity_list(ACTIVITY),
        fact_list(ExtractedFact(
            fact_id="F1-02",
            activity_id="act-collection-002",  # 요청한 처리행위가 아니다
            ontology_property="hasPurpose",
            value="주문 확인·계약 이행·배송·교환·반품",
            value_state="confirmed",
            evidence_text=["주문 확인·계약 이행·배송·교환·반품"],
        )),
        fact_list(),
    ])
    result = extractor.extract(policy)

    assert result.facts == []
    assert "activity_id" in result.rejected[0].reason


def test_extractor_drops_an_activity_whose_heading_is_invented(policy: str):
    extractor, stub = make_extractor([
        activity_list(IdentifiedActivity(
            activity_id="act-collection-009",
            ontology_class="CollectionAndUse",
            heading="9. 마케팅 정보 수신",  # 원문에 없다
        )),
        fact_list(),
    ])
    result = extractor.extract(policy)

    assert result.facts == []
    assert "heading" in result.rejected[0].reason
    # Pass 2를 아예 호출하지 않아야 한다 (Pass 1 + 권리 = 2회)
    assert len(stub.calls) == 2


def test_unknown_facts_carry_no_value(policy: str):
    extractor, _ = make_extractor([
        activity_list(ACTIVITY),
        fact_list(ExtractedFact(
            fact_id="F1-04",
            activity_id="act-collection-001",
            ontology_property="hasRetentionEndCondition",
            value="모델이 굳이 채워 넣은 값",
            value_state="unknown",
            evidence_text=["그 밖의 처리 목적에 대해서는 관계 법령에서 정한 기간 동안 보관합니다."],
        )),
        fact_list(),
    ])
    result = extractor.extract(policy)

    fact = FactEnvelope.model_validate(result.facts[0])
    assert fact.value_state == "unknown"
    assert fact.value is None  # 후처리가 지운다


def test_document_block_is_marked_for_caching(policy: str):
    """Pass 2는 처리행위 수만큼 호출되므로 원문 블록이 캐시되어야 한다."""
    extractor, stub = make_extractor([
        activity_list(ACTIVITY), fact_list(), fact_list(),
    ])
    extractor.extract(policy)

    pass2_system = stub.calls[1]["system"]
    assert pass2_system[-1]["cache_control"] == {"type": "ephemeral"}
    # 지침이 먼저, 원문이 나중이어야 캐시 prefix가 안정적이다
    assert "cache_control" not in pass2_system[0]


def test_processor_facts_get_their_own_subject(policy: str):
    """F1-09의 subject는 처리행위가 아니라 수탁자 개체다."""
    extractor, _ = make_extractor([
        activity_list(IdentifiedActivity(
            activity_id="act-entrust-001",
            ontology_class="EntrustedProcessing",
            heading="빠른택배 주식회사",
        )),
        fact_list(ExtractedFact(
            fact_id="F1-09",
            activity_id="act-entrust-001",
            ontology_property="hasName",
            value="빠른택배 주식회사",
            value_state="confirmed",
            evidence_text=["빠른택배 주식회사"],
        )),
        fact_list(),
    ])
    result = extractor.extract(policy)

    fact = FactEnvelope.model_validate(result.facts[0])
    assert fact.ontology_class == "EntrustedProcessor"
    assert fact.subject_id != fact.activity_id


# --- 채점기 -------------------------------------------------------------


def test_perfect_prediction_scores_one(gold, policy: str):
    score = score_facts(gold, gold, policy)
    assert score.precision == score.recall == score.f1 == 1.0
    assert score.hallucination_rate == 0.0
    assert score.offset_accuracy == 1.0


def test_missing_facts_lower_recall_but_not_precision(gold, policy: str):
    kept = len(gold) - 8
    score = score_facts(gold, gold[:kept], policy)
    assert score.precision == 1.0
    assert score.recall == pytest.approx(kept / len(gold))
    assert len(score.missed) == 8


def test_hallucinated_value_is_detected(gold_raw, gold, policy: str):
    predicted = copy.deepcopy(gold_raw)
    target = next(item for item in predicted if item["fact_id"].startswith("F1-02"))
    target["value"] = "원문에 없는 마케팅 목적"

    score = score_facts(gold, [FactEnvelope.model_validate(i) for i in predicted], policy)
    assert score.hallucinated
    assert score.value_accuracy < 1.0


def test_activity_mixing_is_detected(gold_raw, gold, policy: str):
    """TST-002: 다른 처리행위의 값을 끌어오면 잡아내야 한다."""
    predicted = copy.deepcopy(gold_raw)
    source = next(i for i in predicted if i["fact_id"] == "F1-02:act-collection-002")
    target = next(i for i in predicted if i["fact_id"] == "F1-02:act-collection-003")
    target["value"] = source["value"]  # 주문·배송의 목적을 결제·환불에 붙였다

    score = score_facts(gold, [FactEnvelope.model_validate(i) for i in predicted], policy)
    assert score.activity_leaks
    assert score.activity_leak_rate > 0


def test_wrong_offset_lowers_offset_accuracy(gold_raw, gold, policy: str):
    predicted = copy.deepcopy(gold_raw)
    target = predicted[1]
    piece = target["evidence"][0]
    piece["start_offset"] += 3
    piece["end_offset"] += 3

    score = score_facts(gold, [FactEnvelope.model_validate(i) for i in predicted], policy)
    assert score.offset_accuracy < 1.0


def test_value_state_is_part_of_the_match_key(gold_raw, gold, policy: str):
    """unknown을 confirmed로 잘못 판정하면 일치로 쳐주면 안 된다."""
    predicted = copy.deepcopy(gold_raw)
    target = next(i for i in predicted if i["fact_id"] == "F1-04:act-collection-002")
    target["value_state"] = "absent"

    score = score_facts(gold, [FactEnvelope.model_validate(i) for i in predicted], policy)
    assert score.matched == len(gold) - 1
    assert score.spurious


def test_value_supported_by_ignores_whitespace(policy: str):
    assert value_supported_by(policy, "회원  탈퇴   시")
    assert not value_supported_by(policy, "존재하지 않는 문구")
