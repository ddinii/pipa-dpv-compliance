"""PoC1 gold Fact set 정합성 검증.

gold set은 Extractor 평가의 정답지이므로, 정답지 자체가 틀리면 평가 전체가 무의미하다.
여기서는 Rule 판정이 아니라 gold set이 Fact Dictionary v1.0 계약을 지키는지만 본다.
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
EVAL_DIR = ROOT / "evals" / "poc1"
GOLD_PATH = EVAL_DIR / "sc_p01_gold_facts.json"
POLICY_PATH = EVAL_DIR / "sc_p01_policy.txt"
BUILDER_PATH = EVAL_DIR / "build_gold_facts.py"

# Fact Dictionary 2장 공통 Envelope 필수 필드
ENVELOPE_FIELDS = {
    "fact_id",
    "subject_id",
    "activity_id",
    "ontology_class",
    "ontology_property",
    "value",
    "value_state",
    "source_type",
    "evidence",
    "schema_version",
}

VALUE_STATES = {"confirmed", "unknown", "absent"}

SOURCE_TYPES = {
    "policy_text",
    "incident_record",
    "notification_notice",
    "structured_form",
    "derived",
}

# Fact Dictionary 7장 Rule <-> Fact Coverage (PoC1)
RULE_FACT_COVERAGE = {
    "P1-R01": {"F1-01", "F1-02"},
    "P1-R02": {"F1-03", "F1-04"},
    "P1-R03": {"F1-05", "F1-06", "F1-07"},
    "P1-R04": {"F1-08"},
    "P1-R06": {"F1-09", "F1-10"},
    "P1-R07": {"F1-11", "F1-12"},
}


@pytest.fixture(scope="module")
def gold() -> dict:
    return json.loads(GOLD_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def policy() -> str:
    return POLICY_PATH.read_text(encoding="utf-8")


def fact_type(item: dict) -> str:
    """fact_id 'F1-02:act-collection-001' -> 'F1-02'."""
    return item["fact_id"].split(":", 1)[0]


def test_every_fact_carries_envelope_fields(gold: dict):
    for item in gold["facts"]:
        assert ENVELOPE_FIELDS <= set(item), item["fact_id"]


def test_fact_ids_are_unique(gold: dict):
    ids = [item["fact_id"] for item in gold["facts"]]
    assert len(ids) == len(set(ids))


def test_enum_fields_are_valid(gold: dict):
    for item in gold["facts"]:
        assert item["value_state"] in VALUE_STATES, item["fact_id"]
        assert item["source_type"] in SOURCE_TYPES, item["fact_id"]
        assert item["schema_version"] == "fact-1.0", item["fact_id"]


def test_every_evidence_offset_resolves_in_the_policy_text(gold: dict, policy: str):
    """offset이 원문에서 실제로 그 문자열을 가리켜야 한다.

    LLM이 반환하는 offset은 자주 틀린다. 정답지에서 이 불변식을 강제해 두면
    Extractor 평가 시 offset 정확도를 신뢰할 수 있는 기준으로 쓸 수 있다.
    """
    for item in gold["facts"]:
        assert item["evidence"], f"{item['fact_id']}: evidence가 비어 있다"
        for piece in item["evidence"]:
            start, end = piece["start_offset"], piece["end_offset"]
            assert policy[start:end] == piece["text"], (
                f"{item['fact_id']}: offset {start}:{end}이 "
                f"{piece['text']!r}가 아니라 {policy[start:end]!r}를 가리킨다"
            )


def test_confirmed_facts_have_a_value_and_unknown_facts_do_not(gold: dict):
    """Fact Dictionary 1장: false는 confirmed 값이며 unknown과 다르다.

    F1-01은 Class assertion이므로 예외다. 확인된 것은 인스턴스의 존재 자체이고
    실어 나를 값이 없어서 value가 null이다.
    """
    for item in gold["facts"]:
        if fact_type(item) == "F1-01":
            assert item["value"] is None, item["fact_id"]
            assert item["value_state"] == "confirmed", item["fact_id"]
            continue
        if item["value_state"] == "confirmed":
            assert item["value"] is not None, item["fact_id"]
        else:
            assert item["value"] is None, item["fact_id"]


def test_class_assertions_have_no_ontology_property(gold: dict):
    """2장: Property assertion이 아니면 ontology_property는 null이다."""
    for item in gold["facts"]:
        if fact_type(item) == "F1-01":
            assert item["ontology_property"] is None, item["fact_id"]


def test_all_poc1_fact_ids_in_the_coverage_table_are_present(gold: dict):
    present = {fact_type(item) for item in gold["facts"]}
    required = set().union(*RULE_FACT_COVERAGE.values())
    assert required <= present, f"누락된 Fact ID: {sorted(required - present)}"


@pytest.mark.parametrize("rule_id", sorted(RULE_FACT_COVERAGE))
def test_each_poc1_rule_has_its_required_facts(gold: dict, rule_id: str):
    present = {fact_type(item) for item in gold["facts"]}
    assert RULE_FACT_COVERAGE[rule_id] <= present


def test_activity_scoped_facts_carry_an_activity_id(gold: dict):
    """3장·8장: 처리행위에 귀속되는 Fact는 activity_id로 묶여야 한다.

    F1-11/F1-12(정보주체 권리)만 처리행위에 속하지 않으므로 null을 허용한다.
    """
    for item in gold["facts"]:
        if fact_type(item) in {"F1-11", "F1-12"}:
            assert item["activity_id"] is None, item["fact_id"]
        else:
            assert item["activity_id"], item["fact_id"]


def test_facts_of_one_activity_never_mix_ontology_classes(gold: dict):
    """TST-002: 서로 다른 activity의 값이 잘못 결합되지 않아야 한다."""
    by_activity: dict[str, set[str]] = {}
    for item in gold["facts"]:
        activity_id = item["activity_id"]
        if activity_id is None:
            continue
        by_activity.setdefault(activity_id, set()).add(item["ontology_class"])

    for activity_id, classes in by_activity.items():
        if activity_id.startswith("act-entrust-"):
            # F1-09/F1-10 모두 처리행위를 subject로 둔다. 수탁자 개체는 매퍼가 만든다.
            assert classes == {"EntrustedProcessing"}, activity_id
        else:
            # 보유 관련 Fact는 상위 클래스 이름을 쓰므로 함께 허용한다
            assert classes <= {
                "CollectionAndUse",
                "ThirdPartyProvision",
                "CrossBorderTransfer",
                "Destruction",
                "PersonalInformationProcessing",
            }, (activity_id, classes)


def test_p1_r02_stays_amber_because_three_activities_lack_retention(gold: dict):
    """SC-P01의 P1-R02는 AMBER다. gold set이 그 원인을 그대로 담고 있어야 한다.

    세 처리행위는 "그 밖의 처리 목적에 대해서는 관계 법령에서 정한 기간 동안
    보관합니다"에만 걸린다. 팀 결정(Issue 4): 법령도 숫자도 특정하지 않은 기간은
    법령을 연동해 채우지 않고 알 수 없음으로 둔다 -> F1-03 unknown. 끝나는 사건은
    말하지 않으므로 F1-04 absent.
    """
    lacking = {"act-collection-002", "act-collection-003", "act-collection-004"}

    def states(fact_id: str) -> dict[str, str]:
        return {
            item["activity_id"]: item["value_state"]
            for item in gold["facts"] if fact_type(item) == fact_id
        }

    assert {a for a, s in states("F1-03").items() if s == "unknown"} == lacking
    assert {a for a, s in states("F1-04").items() if s == "absent"} == lacking
    assert "unknown" not in states("F1-04").values()
    assert gold["expected_rule_status"]["P1-R02"] == "AMBER"


def test_builder_is_deterministic(gold: dict):
    """NFR-03: 같은 입력은 같은 산출물을 내야 한다."""
    before = GOLD_PATH.read_text(encoding="utf-8")
    result = subprocess.run(
        [sys.executable, str(BUILDER_PATH)],
        capture_output=True,
        text=True,
        cwd=str(ROOT),
    )
    assert result.returncode == 0, result.stderr
    assert GOLD_PATH.read_text(encoding="utf-8") == before
