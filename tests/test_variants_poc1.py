"""PoC1 controlled variants 검증 (TST-003).

각 변형이 의도한 status 전이를 실제로 만들어 내는지 확인한다.
기준 문서 하나만으로는 GREEN/YELLOW밖에 나오지 않아 RED와 N/A 대표 케이스가 없었다.
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

from app.facts.graph import facts_to_graph, facts_to_mapping
from app.facts.validator import validate_facts
from app.rules.engine import P0RuleEngine

ROOT = Path(__file__).resolve().parents[1]
VARIANT_DIR = ROOT / "evals" / "poc1" / "variants"
BUILDER = ROOT / "evals" / "poc1" / "build_variants.py"

VARIANT_NAMES = sorted(path.name for path in VARIANT_DIR.iterdir() if path.is_dir())


@pytest.fixture(scope="module")
def engine() -> P0RuleEngine:
    return P0RuleEngine()


def load(name: str) -> tuple[dict, str]:
    directory = VARIANT_DIR / name
    gold = json.loads((directory / "gold_facts.json").read_text(encoding="utf-8"))
    document = (directory / "policy.txt").read_text(encoding="utf-8")
    return gold, document


def test_variants_exist():
    assert len(VARIANT_NAMES) == 11


@pytest.mark.parametrize("name", VARIANT_NAMES)
def test_variant_evidence_resolves_in_its_own_document(name: str):
    """문서를 편집하면 글자 위치가 밀린다. 변형 gold set의 offset은 변형 문서 기준이어야 한다."""
    gold, document = load(name)
    facts = validate_facts(gold["facts"], document=document)  # offset 불일치면 여기서 실패
    assert facts


@pytest.mark.parametrize("name", VARIANT_NAMES)
def test_variant_reproduces_its_expected_statuses(name: str, engine: P0RuleEngine):
    gold, document = load(name)
    facts = validate_facts(gold["facts"], document=document)
    mapping = facts_to_mapping(facts, system_metadata=gold.get("system_metadata"))
    results = engine.evaluate_mapping_result(mapping, poc="poc1")
    actual = {result.rule_id: result.status.value for result in results}
    assert actual == gold["expected_rule_status"]


@pytest.mark.parametrize("name", VARIANT_NAMES)
def test_variant_only_moves_its_target_rule(name: str):
    """변형은 겨냥한 Rule 하나만 바꿔야 한다. 나머지가 같이 움직이면 통제된 변형이 아니다."""
    gold, _ = load(name)
    base_status = {
        "P1-R01": "GREEN", "P1-R02": "YELLOW", "P1-R03": "GREEN",
        "P1-R04": "GREEN", "P1-R06": "GREEN", "P1-R07": "GREEN", "P1-R08": "GREEN",
        "P1-R09": "RED", "P1-R10": "RED", "P1-R11": "GREEN",
    }
    target = gold["variant"]["target_rule"]
    for rule_id, status in gold["expected_rule_status"].items():
        if rule_id == target:
            assert status != base_status[rule_id]
        else:
            assert status == base_status[rule_id], f"{name}이 {rule_id}까지 바꿨습니다"


def test_all_four_statuses_are_represented_in_poc1():
    """TST-003: GREEN/YELLOW/RED/N/A 대표 케이스가 세트에 모두 있어야 한다.

    N/A는 v6이 낸다. 원문이 "제3자에게 제공하지 않습니다"라고 명시하면 정답지가
    ThirdPartyProvision=confirmed_false presence metadata를 싣는다 (Fact가 아니다).
    """
    seen = {"GREEN", "YELLOW"}  # 기준 SC-P01이 제공한다
    for name in VARIANT_NAMES:
        gold, _ = load(name)
        seen.update(gold["expected_rule_status"].values())
    assert {"GREEN", "YELLOW", "RED", "N/A"} <= seen


def test_na_comes_from_presence_metadata_not_from_a_fact():
    """35개 Fact에 부재 전용 Fact를 더하지 않는다. N/A의 근거는 metadata다."""
    gold, document = load("v6-no-third-party-provision")
    [presence] = gold["system_metadata"]
    assert presence["activity_type"] == "ThirdPartyProvision"
    assert presence["state"] == "confirmed_false"
    piece = presence["evidence"][0]
    assert document[piece["start_offset"]:piece["end_offset"]] == piece["text"]
    assert not any("provision" in (f["activity_id"] or "") for f in gold["facts"])


def test_absent_and_unknown_move_the_same_rule_differently(engine: P0RuleEngine):
    """Fact Dictionary 1장: absent와 unknown은 다르다.

    같은 P1-R04를 v2(unknown)는 YELLOW로, v3(absent)는 RED로 움직인다.
    둘을 합치면 "기재가 모호한 것"과 "기재가 없는 것"을 구별할 수 없게 된다.
    """
    vague, _ = load("v2-vague-destruction")
    missing, _ = load("v3-missing-destruction")
    assert vague["expected_rule_status"]["P1-R04"] == "YELLOW"
    assert missing["expected_rule_status"]["P1-R04"] == "RED"

    # 두 변형의 fact_id가 같으므로 dict로 모으면 하나가 덮인다. 상태만 모은다.
    states = {
        item["value_state"]
        for gold in (vague, missing)
        for item in gold["facts"]
        if item["fact_id"].startswith("F1-08")
    }
    assert states == {"unknown", "absent"}


def test_builder_is_deterministic():
    before = {
        name: (VARIANT_DIR / name / "gold_facts.json").read_text(encoding="utf-8")
        for name in VARIANT_NAMES
    }
    result = subprocess.run(
        [sys.executable, str(BUILDER)], capture_output=True, text=True, cwd=str(ROOT)
    )
    assert result.returncode == 0, result.stderr
    for name, content in before.items():
        assert (VARIANT_DIR / name / "gold_facts.json").read_text(encoding="utf-8") == content
