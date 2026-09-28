"""LlmPoC1Extractor가 정본 Extractor 계약을 지키는지 본다.

수용 기준은 docs/context/backend/LLM_EXTRACTOR_HANDOFF.md 8장이다. 여기서는
LLM을 호출하지 않고 messages.parse를 스텁으로 갈아끼워 계약만 검증한다.

가장 중요한 것은 test_gold_shaped_extraction_reproduces_sc_p01이다. 모델이
gold set과 같은 것을 뽑았을 때 SC-P01 Freeze 기대값이 그대로 나오면, 추출기의
후처리와 정본 파이프라인이 서로 맞는다는 뜻이다.
"""

import inspect
import json
from collections import Counter, defaultdict
from pathlib import Path

import pytest

from app.extractors.base import Poc1Extractor
from app.extractors.poc1 import ActivityList, ExtractedFact, IdentifiedActivity
from app.extractors.poc1_llm_extractor import ENV_API_KEY, LlmPoC1Extractor
from app.mapping.fact_schema import fact_type, validate_facts
from app.services.compliance import run_policy_check

ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = ROOT / "evals" / "poc1" / "sc_p01_policy.txt"
GOLD_PATH = ROOT / "evals" / "poc1" / "sc_p01_gold_facts.json"

# Fact Dictionary 3장. Extractor가 낼 수 있는 유일한 목록이다.
ALLOWED_FACT_IDS = {f"F1-{n:02d}" for n in range(1, 13)}
GLOBAL_SCOPE = {"F1-11", "F1-12"}

# activity_id 접두사 -> 처리행위 유형 (Pass 1이 돌려줘야 하는 값)
CLASS_BY_PREFIX = {
    "act-collection": "CollectionAndUse",
    "act-provision": "ThirdPartyProvision",
    "act-destruction": "Destruction",
    "act-entrust": "EntrustedProcessing",
    "act-crossborder": "CrossBorderTransfer",
}


@pytest.fixture(scope="module")
def policy() -> str:
    return POLICY_PATH.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def gold() -> dict:
    return json.loads(GOLD_PATH.read_text(encoding="utf-8"))


class StubMessages:
    """messages.parse 스텁. 호출 순서대로 준비한 응답을 돌려준다."""

    def __init__(self, responses: list):
        self.responses = list(responses)
        self.calls: list[dict] = []

    def parse(self, **kwargs):
        self.calls.append(kwargs)
        payload = self.responses.pop(0)
        return type("Response", (), {"parsed_output": payload, "stop_reason": "end_turn"})()


def fact_list(facts):
    return type("FactList", (), {"facts": facts})()


def gold_shaped_responses(gold: dict) -> list:
    """gold set을 그대로 뱉는 모델을 흉내 낸다.

    Pass 1 -> 처리행위별 Pass 2 -> 권리 Pass 순서로 응답을 쌓는다.
    heading은 그 처리행위의 첫 근거 문장을 쓴다(원문에 실재해야 하므로).
    """
    by_activity = defaultdict(list)
    rights = []
    for item in gold["facts"]:
        if item["activity_id"] is None:
            rights.append(item)
        else:
            by_activity[item["activity_id"]].append(item)

    def to_extracted(item: dict) -> ExtractedFact:
        return ExtractedFact(
            fact_id=fact_type(item["fact_id"]),
            activity_id=item["activity_id"],
            ontology_property=item["ontology_property"],
            value=item["value"],
            value_state=item["value_state"],
            evidence_text=[piece["text"] for piece in item["evidence"]],
        )

    activities = [
        IdentifiedActivity(
            activity_id=activity_id,
            ontology_class=CLASS_BY_PREFIX[activity_id.rsplit("-", 1)[0]],
            heading=items[0]["evidence"][0]["text"],
        )
        for activity_id, items in by_activity.items()
    ]

    responses = [ActivityList(activities=activities)]
    responses += [
        fact_list([to_extracted(i) for i in by_activity[a.activity_id]]) for a in activities
    ]
    responses.append(fact_list([to_extracted(i) for i in rights]))
    return responses


def extract_gold_shaped(gold: dict, policy: str) -> list[dict]:
    extractor = LlmPoC1Extractor(StubMessages(gold_shaped_responses(gold)))
    return extractor.extract(
        analysis_id="SC-P01",
        controller_id="ctrl-001",
        controller_name="모아커머스",
        policy_text=policy,
    )


# --- handoff 2장: Protocol 계약 -----------------------------------------


def test_parameters_match_the_protocol_exactly():
    """파라미터를 더하거나 빼면 주입 지점이 조용히 깨진다.

    반환 타입은 비교하지 않는다. Protocol이 ExtractorOutput
    (list[dict] | ExtractionResult) 유니온으로 넓어졌고, 좁은 쪽인
    list[dict]를 돌려주는 것은 계약을 만족한다. 파라미터는 정확히 같아야 한다.
    """
    assert (
        inspect.signature(LlmPoC1Extractor.extract).parameters
        == inspect.signature(Poc1Extractor.extract).parameters
    )


def test_return_type_is_accepted_by_the_service_boundary():
    """서비스가 legacy list 반환을 받아주는지 확인한다.

    app/services/compliance.py의 _split_extractor_output이 list와
    ExtractionResult를 모두 받는다. 그 계약이 사라지면 여기서 드러난다.
    """
    from app.services.compliance import _split_extractor_output

    facts, presence = _split_extractor_output([{"fact_id": "F1-01:x"}])
    assert facts == [{"fact_id": "F1-01:x"}]
    assert presence == []


def test_returns_a_list_of_plain_dicts(gold: dict, policy: str):
    facts = extract_gold_shaped(gold, policy)
    assert isinstance(facts, list) and facts
    assert all(isinstance(item, dict) for item in facts)


# --- handoff 3~4장: Fact 출력 계약 ---------------------------------------


def test_output_passes_the_canonical_validator_unchanged(gold: dict, policy: str):
    facts = extract_gold_shaped(gold, policy)
    assert len(validate_facts(facts)) == len(facts)


def test_emits_only_the_frozen_poc1_fact_ids(gold: dict, policy: str):
    facts = extract_gold_shaped(gold, policy)
    assert {fact_type(item["fact_id"]) for item in facts} <= ALLOWED_FACT_IDS


def test_every_fact_carries_traceable_evidence(gold: dict, policy: str):
    """근거는 비어 있을 수 없고, 원문에서 그 문자열을 가리켜야 한다 (NFR-07)."""
    for item in extract_gold_shaped(gold, policy):
        assert item["evidence"], item["fact_id"]
        for piece in item["evidence"]:
            start, end = piece["start_offset"], piece["end_offset"]
            assert policy[start:end] == piece["text"], item["fact_id"]


def test_source_type_is_policy_text(gold: dict, policy: str):
    """Fact Dictionary 8장 · handoff 3장: F1-*는 policy_text 계열이다."""
    for item in extract_gold_shaped(gold, policy):
        assert item["source_type"] == "policy_text", item["fact_id"]


def test_only_rights_facts_may_omit_activity_id(gold: dict, policy: str):
    for item in extract_gold_shaped(gold, policy):
        if fact_type(item["fact_id"]) in GLOBAL_SCOPE:
            assert item["activity_id"] is None, item["fact_id"]
        else:
            assert item["activity_id"], item["fact_id"]


def test_unknown_is_preserved_and_never_collapsed(gold: dict, policy: str):
    """handoff 3장: unknown -> absent, unknown -> confirmed 변환 금지."""
    facts = extract_gold_shaped(gold, policy)

    # fact_id의 접미사 규약은 정답지와 다를 수 있다(채점도 fact_type으로 맞춘다).
    # 여기서 보는 것은 상태가 유지되는가이지 ID가 같은가가 아니다.
    def states(items):
        return Counter(
            (fact_type(i["fact_id"]), i["activity_id"], i["value_state"]) for i in items
        )

    assert states(facts) == states(gold["facts"])
    assert any(i["value_state"] == "unknown" for i in facts)
    for item in facts:
        if item["value_state"] != "confirmed":
            assert item["value"] is None, item["fact_id"]


# --- handoff 6장: 주입 지점 ----------------------------------------------


def test_gold_shaped_extraction_reproduces_sc_p01(gold: dict, policy: str):
    """TST-005 E2E: 원문 -> Fact -> Ontology -> 6 Rule.

    run_policy_check에 이 추출기를 주입하면 SC-P01 Freeze 기대값이 나온다.
    """
    extractor = LlmPoC1Extractor(StubMessages(gold_shaped_responses(gold)))
    results = run_policy_check(
        {
            "analysis_id": "SC-P01",
            "controller": {"controller_id": "ctrl-001", "name": "모아커머스"},
            "policy_text": policy,
        },
        extractor=extractor,
    )
    statuses = {item.rule_id: item.status.value for item in results}
    assert statuses == gold["expected_rule_status"]


# --- handoff 7장: 자격증명과 원문 취급 -------------------------------------


def test_from_environment_refuses_to_run_without_a_key(monkeypatch):
    monkeypatch.delenv(ENV_API_KEY, raising=False)
    with pytest.raises(RuntimeError, match=ENV_API_KEY):
        LlmPoC1Extractor.from_environment()


def test_diagnostics_are_opt_in(gold: dict, policy: str):
    """거부 사유를 보려면 훅을 직접 달아야 한다. 기본값은 아무것도 내보내지 않는다."""
    seen = []
    extractor = LlmPoC1Extractor(
        StubMessages(gold_shaped_responses(gold)), on_result=seen.append
    )
    extractor.extract(
        analysis_id="SC-P01",
        controller_id="ctrl-001",
        controller_name=None,
        policy_text=policy,
    )
    assert len(seen) == 1
    assert seen[0].rejected == []


def test_extractor_never_assigns_a_rule_status(gold: dict, policy: str):
    """handoff 1장: Extractor는 Fact만 낸다. G/A/R/N-A를 만들지 않는다."""
    facts = extract_gold_shaped(gold, policy)
    forbidden = {"GREEN", "AMBER", "RED", "N/A"}
    for item in facts:
        assert not (set(item) & {"status", "rule_id", "applicability"}), item["fact_id"]
        assert str(item["value"]) not in forbidden, item["fact_id"]
