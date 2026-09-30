"""SC-P02 controlled variants 검증.

기준 세트 하나로는 GREEN만 나온다. 변형이 AMBER와 RED 경로를 채운다 (TST-003).

변형이 의도보다 넓게 퍼지면 "판정이 바뀐 원인이 이 변형"이라고 말할 수 없다.
그래서 움직인 Rule이 **Fact Dictionary 7장 Coverage가 그 Fact를 소비한다고 적은
Rule** 안에 드는지를 매 변형마다 확인한다.
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

from app.facts.graph import facts_to_mapping
from app.mapping.fact_schema import fact_type, validate_facts
from app.rules.engine import P0RuleEngine
from evals.dataset import load_cases

ROOT = Path(__file__).resolve().parents[1]
VARIANT_DIR = ROOT / "evals" / "poc2" / "variants"
BUILDER_PATH = ROOT / "evals" / "poc2" / "build_variants.py"

# Fact Dictionary 7장 Rule <-> Fact Coverage (PoC2)
COVERAGE = {
    "P2-R01": {"F2-01", "F2-02", "F2-03"},
    "P2-R02": {"F2-02", "F2-04"},
    "P2-R03": {"F2-08", "F2-09"},
    "P2-R08": {"F2-01", "F2-10"},
}

VARIANT_NAMES = [
    "v1-incident-missing-items",
    "v2-notice-omits-items",
    "v3-notice-missing-incident-time",
    "v4-partial-response-measures",
    "v5-no-response-measures",
    "v6-no-notice",
]


@pytest.fixture(scope="module")
def engine() -> P0RuleEngine:
    return P0RuleEngine()


@pytest.fixture(scope="module")
def cases() -> dict:
    return {case.name: case for case in load_cases("poc2")}


def contract_facts(case) -> list[dict]:
    return [{k: v for k, v in f.items() if not k.startswith("_")} for f in case.gold_facts]


def statuses(case, engine: P0RuleEngine) -> dict[str, str]:
    mapping = facts_to_mapping(
        contract_facts(case), analysis_id=case.name, controller_id="ctrl-001",
        system_metadata=case.gold_system_metadata,
    )
    return {
        item.rule_id: item.status.value
        for item in engine.evaluate_mapping_result(mapping, poc="poc2")
    }


# --- 세트 구성 -----------------------------------------------------------


def test_sweep_covers_the_base_set_and_every_variant(cases: dict):
    assert set(cases) == {"base", *VARIANT_NAMES}


@pytest.mark.parametrize("name", VARIANT_NAMES)
def test_variant_gold_passes_the_canonical_validator(cases: dict, name: str):
    facts = contract_facts(cases[name])
    assert len(validate_facts(facts)) == len(facts)


@pytest.mark.parametrize("name", VARIANT_NAMES)
def test_variant_evidence_resolves_in_its_own_document(cases: dict, name: str):
    """문서를 편집하면 글자 위치가 밀린다. 근거가 새 문서를 가리켜야 한다."""
    case = cases[name]
    for item in case.gold_facts:
        document = case.document_for(item["source_type"])
        for piece in item["evidence"]:
            if "field_path" in piece:
                continue  # 통지문이 없을 때의 근거는 입력 필드다 (v6)
            start, end = piece["start_offset"], piece["end_offset"]
            assert document[start:end] == piece["text"], (
                f"{name}/{item['fact_id']}: 근거가 변형 문서에서 해결되지 않는다"
            )


# --- 판정 ----------------------------------------------------------------


@pytest.mark.parametrize("name", VARIANT_NAMES)
def test_variant_reproduces_its_expected_statuses(cases: dict, engine: P0RuleEngine, name: str):
    case = cases[name]
    assert statuses(case, engine) == case.expected_rule_status


@pytest.mark.parametrize("name", VARIANT_NAMES)
def test_variant_only_moves_rules_that_consume_the_changed_fact(
    cases: dict, engine: P0RuleEngine, name: str
):
    """움직인 Rule은 7장 Coverage가 그 Fact를 소비한다고 적은 Rule뿐이어야 한다.

    F2-02처럼 두 Rule이 공유하는 Fact는 둘 다 움직이는 것이 정상이다. 그 밖의
    Rule이 움직이면 변형이 문서를 의도보다 넓게 건드린 것이다.
    """
    case = cases[name]
    base = cases["base"]
    changed = set(case.payload["variant"]["changed_facts"])
    allowed = {rule for rule, facts in COVERAGE.items() if facts & changed}

    before = statuses(base, engine)
    after = statuses(case, engine)
    moved = {rule for rule in after if after[rule] != before[rule]}

    assert moved, f"{name}: 아무 Rule도 움직이지 않았다"
    assert moved <= allowed, (
        f"{name}: {sorted(moved - allowed)}가 함께 움직였다. "
        f"건드린 Fact={sorted(changed)}이므로 허용되는 Rule은 {sorted(allowed)}뿐이다"
    )


def test_all_four_statuses_are_represented_in_poc2(cases: dict):
    """TST-003: GREEN/AMBER/RED/N/A 대표 케이스가 세트에 모두 있어야 한다.

    N/A는 v6이 낸다. 통지문이 없으면 서비스가 NotificationNotice=confirmed_false를
    붙이고(with_notice_presence), 정답지도 같은 metadata를 싣는다.
    """
    seen = set()
    for case in cases.values():
        seen.update(case.expected_rule_status.values())
    assert {"GREEN", "AMBER", "RED", "N/A"} <= seen


def test_no_notice_case_has_no_notice_document(cases: dict):
    """통지문 없는 케이스는 문서 자체가 없다. 러너는 notification=None으로 부른다."""
    case = cases["v6-no-notice"]
    assert set(case.documents) == {"incident"}
    assert case.documents["incident"] == cases["base"].documents["incident"]


def test_no_notice_gold_matches_what_the_service_and_extractor_produce(cases: dict):
    """정답 metadata와 통지문 Fact가 서비스·Extractor 출력과 같아야 한다.

    다르면 러너가 올바르게 동작해도 채점에서 틀린 것으로 나온다.
    """
    from app.extractors.poc2 import NOTICE_ABSENCE_SHAPE
    from app.services.compliance import with_notice_presence

    case = cases["v6-no-notice"]
    assert case.gold_system_metadata == with_notice_presence([], notification_provided=False)
    notice_side = [f for f in case.gold_facts if fact_type(f["fact_id"]) in NOTICE_ABSENCE_SHAPE]
    assert len(notice_side) == len(NOTICE_ABSENCE_SHAPE)
    for item in notice_side:
        assert item["value_state"] == "absent" and item["source_type"] == "derived"


def test_partial_and_missing_measures_are_distinguished(cases: dict):
    """P2-R08: 일부만 있는 것(AMBER)과 아예 없는 것(RED)은 달라야 한다.

    둘이 같아지면 "역할 분류가 모호한 경우"와 "대응조치를 안 한 경우"를
    구별하지 못한다.
    """
    partial = cases["v4-partial-response-measures"]
    missing = cases["v5-no-response-measures"]
    assert partial.expected_rule_status["P2-R08"] == "AMBER"
    assert missing.expected_rule_status["P2-R08"] == "RED"

    by_type = {fact_type(f["fact_id"]): f for f in partial.gold_facts}
    assert len(by_type["F2-10"]["value"]) == 2
    missing_by_type = {fact_type(f["fact_id"]): f for f in missing.gold_facts}
    assert missing_by_type["F2-10"]["value_state"] == "absent"


# --- 사고/통지 분리가 변형에서도 유지되는지 -------------------------------


@pytest.mark.parametrize("name", VARIANT_NAMES)
def test_incident_and_notice_facts_stay_separate(cases: dict, name: str):
    """변형을 넣어도 F2-05와 F2-08은 별개 Fact로 남아야 한다."""
    by_type = {fact_type(f["fact_id"]): f for f in cases[name].gold_facts}
    incident, notice = by_type["F2-05"], by_type["F2-08"]
    assert incident["subject_id"] != notice["subject_id"]
    assert incident["source_type"] != notice["source_type"]


def test_editing_the_notice_leaves_the_incident_record_untouched(cases: dict):
    """통지문만 건드린 변형은 사고 기록을 바꾸지 않아야 한다."""
    base = cases["base"].documents["incident"]
    for name in ("v2-notice-omits-items", "v3-notice-missing-incident-time"):
        assert cases[name].documents["incident"] == base, name


def test_editing_the_incident_leaves_the_notice_untouched(cases: dict):
    base = cases["base"].documents["notice"]
    for name in ("v1-incident-missing-items", "v4-partial-response-measures",
                 "v5-no-response-measures"):
        assert cases[name].documents["notice"] == base, name


# --- 재현성 --------------------------------------------------------------


def test_builder_is_deterministic():
    """NFR-03: 같은 입력은 같은 산출물을 내야 한다."""
    before = {
        name: (VARIANT_DIR / name / "gold_facts.json").read_text(encoding="utf-8")
        for name in VARIANT_NAMES
    }
    result = subprocess.run(
        [sys.executable, str(BUILDER_PATH)],
        capture_output=True, text=True, cwd=str(ROOT),
    )
    assert result.returncode == 0, result.stderr
    for name, content in before.items():
        assert (VARIANT_DIR / name / "gold_facts.json").read_text(encoding="utf-8") == content


def test_variant_metadata_is_recorded(cases: dict):
    for name in VARIANT_NAMES:
        variant = cases[name].payload["variant"]
        assert variant["name"] == name
        assert variant["target_rule"] in COVERAGE
        assert variant["expected_status"] in {"AMBER", "RED", "N/A"}
        assert variant["changed_facts"]
