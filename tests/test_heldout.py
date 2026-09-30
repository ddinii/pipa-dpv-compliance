"""held-out 평가 세트 검증.

held-out은 프롬프트를 고칠 때 보지 않는 문서다. 여기서는 정답지 자체가 올바른지만
확인한다. Extractor 결과는 여기서 보지 않는다 (그것은 과금되는 실행의 몫이다).

기대 Rule 상태는 Rule 조건을 읽고 손으로 적었다. 엔진이 정답지로 그 상태를
재현하지 못하면 정답지가 틀렸거나 기대값이 틀린 것이다.
"""

import subprocess
import sys
from pathlib import Path

import pytest

from app.facts.graph import facts_to_mapping
from app.mapping.fact_schema import fact_type, validate_facts
from app.extractors.poc2 import DATETIME_FACT_IDS
from app.rules.engine import P0RuleEngine
from evals.dataset import load_cases
from evals.score import datetime_supported_by, value_supported_by

ROOT = Path(__file__).resolve().parents[1]
HELDOUT = {
    "poc1": ["h1-fitness-app", "h2-online-academy", "h3-no-sharing", "h4-partial-negation"],
    "poc2": ["h1-shop-hacking", "h2-clinic-misdirected", "h3-academy-no-notice"],
}
CASES = [(poc, name) for poc, names in HELDOUT.items() for name in names]


@pytest.fixture(scope="module")
def engine() -> P0RuleEngine:
    return P0RuleEngine()


def heldout(poc: str) -> dict:
    return {case.name: case for case in load_cases(poc, split="heldout")}


def contract_facts(case) -> list[dict]:
    return [{k: v for k, v in f.items() if not k.startswith("_")} for f in case.gold_facts]


# --- 분리 ----------------------------------------------------------------


@pytest.mark.parametrize("poc", HELDOUT)
def test_heldout_split_loads_exactly_the_heldout_cases(poc: str):
    assert sorted(heldout(poc)) == HELDOUT[poc]


@pytest.mark.parametrize("poc", HELDOUT)
def test_default_split_is_unchanged(poc: str):
    """기본값(dev)에 held-out이 섞이면 프롬프트를 고칠 때 held-out을 보게 된다."""
    dev = {case.name for case in load_cases(poc)}
    assert "base" in dev
    assert not dev & set(HELDOUT[poc])


@pytest.mark.parametrize("poc", HELDOUT)
def test_all_split_is_dev_then_heldout(poc: str):
    names = [case.name for case in load_cases(poc, split="all")]
    dev = [case.name for case in load_cases(poc)]
    assert names == dev + HELDOUT[poc]


def test_unknown_split_fails():
    with pytest.raises(ValueError, match="split"):
        load_cases("poc1", split="test")


@pytest.mark.parametrize("poc, name", CASES)
def test_heldout_is_a_different_document_from_dev(poc: str, name: str):
    """held-out이 dev 문서를 고친 것이면 일반화를 잴 수 없다."""
    case = heldout(poc)[name]
    base = load_cases(poc)[0]
    for key, text in case.documents.items():
        # 제목이나 면책 문구 같은 상투적인 줄은 겹쳐도 된다. 본문 대부분이 겹치면 안 된다.
        lines = {line.strip() for line in text.splitlines() if line.strip()}
        base_lines = {line.strip() for line in base.documents[key].splitlines() if line.strip()}
        assert len(lines & base_lines) <= 0.2 * len(lines), f"{name}/{key}: dev 문서와 너무 겹친다"
        assert "PoC 평가용 가상" in text, f"{name}/{key}: 합성 문서 표시가 없다"


# --- 정답지 --------------------------------------------------------------


@pytest.mark.parametrize("poc, name", CASES)
def test_gold_passes_the_canonical_validator(poc: str, name: str):
    facts = contract_facts(heldout(poc)[name])
    assert len(validate_facts(facts)) == len(facts)


@pytest.mark.parametrize("poc, name", CASES)
def test_evidence_resolves_in_its_own_document(poc: str, name: str):
    case = heldout(poc)[name]
    for item in [*case.gold_facts, *case.gold_system_metadata]:
        document = case.document_for(item["source_type"])
        for piece in item["evidence"]:
            if "field_path" in piece:
                continue  # 통지문이 없을 때의 근거는 입력 필드다
            start, end = piece["start_offset"], piece["end_offset"]
            assert document[start:end] == piece["text"], f"{name}/{item['fact_id']}"


@pytest.mark.parametrize("poc, name", CASES)
def test_gold_values_are_supported_by_the_document(poc: str, name: str):
    """정답지 자체가 채점기의 환각 판정에 걸리면 안 된다.

    특히 날짜는 원문 표기가 제각각이다("2026. 8. 14. 오전 3시 20분경", "오후 2시 15분").
    """
    case = heldout(poc)[name]
    for item in case.gold_facts:
        if item["value"] is None:
            continue
        document = case.document_for(item["source_type"])
        if fact_type(item["fact_id"]) in DATETIME_FACT_IDS:
            assert datetime_supported_by(document, item["value"]), item["fact_id"]
        else:
            assert value_supported_by(document, item["value"]), item["fact_id"]


@pytest.mark.parametrize("poc, name", CASES)
def test_gold_reproduces_the_hand_written_statuses(
    engine: P0RuleEngine, poc: str, name: str
):
    case = heldout(poc)[name]
    mapping = facts_to_mapping(
        contract_facts(case), analysis_id=name, controller_id="ctrl-001",
        system_metadata=case.gold_system_metadata,
    )
    statuses = {r.rule_id: r.status.value for r in engine.evaluate_mapping_result(mapping, poc=poc)}
    assert statuses == case.expected_rule_status


@pytest.mark.parametrize("poc", HELDOUT)
def test_heldout_covers_all_four_statuses(poc: str):
    seen = {s for case in heldout(poc).values() for s in case.expected_rule_status.values()}
    assert {"GREEN", "AMBER", "RED", "N/A"} <= seen


def test_partial_negation_is_not_an_absence():
    """잘못된 N/A를 잡는 함정. "원칙적으로 제공하지 않으나 다음의 경우 제공"은 부재가 아니다.

    정답지는 제공 처리행위를 갖고 부재 선언은 없다. 그 제공은 목적이 빠져 RED다.
    모델이 부재를 선언하면 P1-R03이 N/A가 되고, gold가 RED이므로 채점기가
    위험 오판(N/A)으로 센다. 제공이 완전했다면 단순 불일치에 그쳐 위험이 보이지 않는다.
    """
    case = heldout("poc1")["h4-partial-negation"]
    assert case.gold_system_metadata == []
    assert any(f["activity_id"] == "act-provision-001" for f in case.gold_facts)
    assert case.expected_rule_status["P1-R03"] == "RED"
    assert "원칙적으로 이용자의 개인정보를 제3자에게 제공하지 않습니다" in case.documents["policy"]
    # 위탁은 언급이 없다. 부재 선언도 아니고 처리행위도 아니다 -> AMBER
    assert not any("entrust" in (f["activity_id"] or "") for f in case.gold_facts)
    assert case.expected_rule_status["P1-R06"] == "AMBER"


def test_explicit_absences_are_metadata_with_verbatim_quotes():
    case = heldout("poc1")["h3-no-sharing"]
    types = {item["activity_type"] for item in case.gold_system_metadata}
    assert types == {"ThirdPartyProvision", "EntrustedProcessing"}
    assert {case.expected_rule_status[r] for r in ("P1-R03", "P1-R06")} == {"N/A"}


def test_poc1_heldout_exercises_numeric_retention_periods():
    """dev 세트에는 F1-03 confirmed가 하나도 없다. held-out이 그 경로를 채운다."""
    confirmed = [
        f for case in heldout("poc1").values() for f in case.gold_facts
        if fact_type(f["fact_id"]) == "F1-03" and f["value_state"] == "confirmed"
    ]
    assert len(confirmed) >= 2


def test_overlapping_provisions_keep_their_own_items():
    """TST-002 함정. 두 제공이 이름·휴대전화번호를 공유하고 '걸음 수'는 2번에만 있다."""
    case = heldout("poc1")["h1-fitness-app"]
    items = {
        f["activity_id"]: f["value"] for f in case.gold_facts
        if fact_type(f["fact_id"]) == "F1-06"
    }
    assert items["act-provision-001"] == ["이름", "휴대전화번호"]
    assert items["act-provision-002"] == ["이름", "휴대전화번호", "걸음 수"]


# --- 재현성 --------------------------------------------------------------


@pytest.mark.parametrize("poc", HELDOUT)
def test_builder_is_deterministic(poc: str):
    paths = [ROOT / "evals" / poc / "heldout" / name / "gold_facts.json" for name in HELDOUT[poc]]
    before = [p.read_text(encoding="utf-8") for p in paths]
    result = subprocess.run(
        [sys.executable, str(ROOT / "evals" / poc / "build_heldout.py")],
        capture_output=True, text=True, encoding="utf-8", cwd=str(ROOT),
        env={**__import__("os").environ, "PYTHONIOENCODING": "utf-8"},
    )
    assert result.returncode == 0, result.stderr
    assert [p.read_text(encoding="utf-8") for p in paths] == before
