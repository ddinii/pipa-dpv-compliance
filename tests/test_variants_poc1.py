"""PoC1 controlled variants 검증 (TST-003).

각 변형이 의도한 status 전이를 실제로 만들어 내는지 확인한다.
기준 문서 하나만으로는 GREEN/AMBER밖에 나오지 않아 RED와 N/A 대표 케이스가 없었다.
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

from app.facts.graph import facts_to_graph
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
    assert len(VARIANT_NAMES) == 6


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
    results = engine.evaluate_graph(facts_to_graph(facts), poc="poc1")
    actual = {result.rule_id: result.status.value for result in results}
    assert actual == gold["expected_rule_status"]


@pytest.mark.parametrize("name", VARIANT_NAMES)
def test_variant_only_moves_its_target_rule(name: str):
    """변형은 겨냥한 Rule 하나만 바꿔야 한다. 나머지가 같이 움직이면 통제된 변형이 아니다."""
    gold, _ = load(name)
    base_status = {
        "P1-R01": "GREEN", "P1-R02": "AMBER", "P1-R03": "GREEN",
        "P1-R04": "GREEN", "P1-R06": "GREEN", "P1-R07": "GREEN",
    }
    target = gold["variant"]["target_rule"]
    for rule_id, status in gold["expected_rule_status"].items():
        if rule_id == target:
            assert status != base_status[rule_id]
        else:
            assert status == base_status[rule_id], f"{name}이 {rule_id}까지 바꿨습니다"


def test_all_four_statuses_are_represented_in_poc1():
    """TST-003: 각 PoC에서 GREEN/AMBER/RED/N/A 대표 케이스 최소 1개씩."""
    seen = {"GREEN", "AMBER"}  # 기준 SC-P01이 제공한다
    for name in VARIANT_NAMES:
        gold, _ = load(name)
        seen.update(gold["expected_rule_status"].values())
    assert {"GREEN", "AMBER", "RED", "N/A"} <= seen


def test_explicit_absence_is_not_the_same_as_a_missing_fact(engine: P0RuleEngine):
    """N/A와 AMBER의 차이. 명시적 부재만 N/A이고 단순 결측은 AMBER다.

    v6의 부재 단언 Fact를 빼면 같은 문서가 N/A가 아니라 AMBER가 되어야 한다.
    """
    gold, document = load("v6-no-third-party-provision")

    with_absence = validate_facts(gold["facts"], document=document)
    assert engine.evaluate_rule(facts_to_graph(with_absence), "P1-R03").status.value == "N/A"

    without_absence = validate_facts(
        [item for item in gold["facts"] if not item["fact_id"].startswith("F1-00")],
        document=document,
    )
    assert engine.evaluate_rule(facts_to_graph(without_absence), "P1-R03").status.value == "AMBER"


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
