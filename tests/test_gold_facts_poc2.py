"""SC-P02 gold Fact set 정합성 검증.

정답지가 틀리면 평가 전체가 무의미하다. PoC2는 문서가 둘이라 정답지가 틀릴 수 있는
방식이 하나 더 있다 — **근거가 엉뚱한 문서를 가리키는 것**. 사고 Fact의 근거는
사고 기록에서, 통지문 Fact의 근거는 통지문에서만 해결되어야 한다
(Fact Dictionary 8장 · 기능명세서 6장).
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

from app.facts.graph import facts_to_mapping
from app.mapping.fact_schema import (
    POC2_INCIDENT_FACTS,
    POC2_NOTICE_FACTS,
    fact_type,
    validate_facts,
)
from app.rules.engine import P0RuleEngine
from evals.dataset import load_cases

ROOT = Path(__file__).resolve().parents[1]
EVAL_DIR = ROOT / "evals" / "poc2"
GOLD_PATH = EVAL_DIR / "sc_p02_gold_facts.json"
BUILDER_PATH = EVAL_DIR / "build_gold_facts.py"

ENVELOPE_FIELDS = {
    "fact_id", "subject_id", "activity_id", "ontology_class", "ontology_property",
    "value", "value_state", "source_type", "evidence", "schema_version",
}

# Fact Dictionary 7장 Rule <-> Fact Coverage (PoC2)
RULE_FACT_COVERAGE = {
    "P2-R01": {"F2-01", "F2-02", "F2-03"},
    "P2-R02": {"F2-02", "F2-04"},
    "P2-R03": {"F2-08", "F2-09"},
    "P2-R08": {"F2-01", "F2-10"},
    "P2-R09": {"F2-05", "F2-08"},
    "P2-R10": {"F2-11", "F2-12"},
}

NOTICE_SUBJECT = "breach-notice"
INCIDENT_SUBJECT = "breach-incident"


@pytest.fixture(scope="module")
def gold() -> dict:
    return json.loads(GOLD_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def case():
    return load_cases("poc2")[0]


def contract_facts(gold: dict) -> list[dict]:
    """_note 같은 비계약 필드를 떼고 정본에 넘길 형태로 만든다."""
    return [{k: v for k, v in item.items() if not k.startswith("_")} for item in gold["facts"]]


# --- Envelope ------------------------------------------------------------


def test_every_fact_carries_envelope_fields(gold: dict):
    for item in gold["facts"]:
        assert ENVELOPE_FIELDS <= set(item), item["fact_id"]


def test_fact_ids_are_unique(gold: dict):
    ids = [item["fact_id"] for item in gold["facts"]]
    assert len(ids) == len(set(ids))


def test_gold_passes_the_canonical_validator(gold: dict):
    facts = contract_facts(gold)
    assert len(validate_facts(facts)) == len(facts)


def test_all_ten_poc2_fact_ids_are_present(gold: dict):
    present = {fact_type(item["fact_id"]) for item in gold["facts"]}
    assert present == {f"F2-{n:02d}" for n in range(1, 13)}


@pytest.mark.parametrize("rule_id", sorted(RULE_FACT_COVERAGE))
def test_each_poc2_rule_has_its_required_facts(gold: dict, rule_id: str):
    present = {fact_type(item["fact_id"]) for item in gold["facts"]}
    assert RULE_FACT_COVERAGE[rule_id] <= present


# --- 사고 / 통지문 분리 ---------------------------------------------------


def test_every_evidence_resolves_in_its_own_document(gold: dict, case):
    """근거가 그 Fact의 source_type에 맞는 문서에서 해결되어야 한다.

    사고 Fact의 근거를 통지문에서 찾으면 offset이 엉뚱한 곳을 가리킨다.
    빌더가 문서를 나눠 찾으므로 여기서 그 결과를 다시 확인한다.
    """
    for item in gold["facts"]:
        document = case.document_for(item["source_type"])
        assert item["evidence"], item["fact_id"]
        for piece in item["evidence"]:
            start, end = piece["start_offset"], piece["end_offset"]
            assert document[start:end] == piece["text"], (
                f"{item['fact_id']}: {piece['text']!r}가 "
                f"{item['source_type']} 문서에서 해결되지 않는다"
            )


def test_source_type_matches_the_fact_family(gold: dict):
    """Fact Dictionary 8장: incident_record와 notification_notice를 반드시 구분한다."""
    for item in gold["facts"]:
        base = fact_type(item["fact_id"])
        if base in POC2_INCIDENT_FACTS:
            assert item["source_type"] == "incident_record", item["fact_id"]
        elif base in POC2_NOTICE_FACTS:
            assert item["source_type"] in {"notification_notice", "derived"}, item["fact_id"]


def test_notice_facts_are_subject_to_the_notice(gold: dict):
    """F2-04/F2-08/F2-09는 통지문이 subject다 (4장)."""
    subjects = {fact_type(i["fact_id"]): i["subject_id"] for i in gold["facts"]}
    for base in ("F2-04", "F2-08", "F2-09"):
        assert subjects[base] == NOTICE_SUBJECT, base
    for base in ("F2-01", "F2-02", "F2-05", "F2-06", "F2-10"):
        assert subjects[base] == INCIDENT_SUBJECT, base


def test_actual_items_and_notice_items_are_separate_facts(gold: dict):
    """F2-02와 F2-04를 합치지 않는다. 값이 같아도 별개 Fact다."""
    by_type = {fact_type(i["fact_id"]): i for i in gold["facts"]}
    assert by_type["F2-02"]["fact_id"] != by_type["F2-04"]["fact_id"]
    assert by_type["F2-02"]["subject_id"] != by_type["F2-04"]["subject_id"]
    assert by_type["F2-02"]["source_type"] != by_type["F2-04"]["source_type"]


def test_incident_date_and_notice_stated_time_are_separate_facts(gold: dict):
    """F2-05와 F2-08은 SC-P02에서 값이 같지만 절대 같은 Fact가 아니다.

    4장 주석: F2-08은 incidentDate를 대신 쓰지 않는다. 값이 우연히 같은 경우가
    가장 헷갈리므로 정답지가 그 경우를 담는다.
    """
    by_type = {fact_type(i["fact_id"]): i for i in gold["facts"]}
    incident, notice = by_type["F2-05"], by_type["F2-08"]
    assert incident["value"] == notice["value"]
    assert incident["subject_id"] != notice["subject_id"]
    assert incident["source_type"] != notice["source_type"]
    assert incident["evidence"][0]["text"] != notice["evidence"][0]["text"]


def test_f2_08_is_not_an_ontology_property(gold: dict):
    """4장: F2-08은 Ontology v1.0에 별도 DataProperty를 추가하지 않는다."""
    by_type = {fact_type(i["fact_id"]): i for i in gold["facts"]}
    assert by_type["F2-08"]["ontology_property"] is None


def test_response_measures_cover_the_four_frozen_roles(gold: dict):
    """4장 F2-10 주석의 enum 4종. P2-R08은 넷이 모두 확인될 때 GREEN이다."""
    by_type = {fact_type(i["fact_id"]): i for i in gold["facts"]}
    roles = {item["measure_role"] for item in by_type["F2-10"]["value"]}
    assert roles == {
        "data_subject_guidance",
        "controller_response",
        "remedy_procedure",
        "post_incident_mitigation",
    }


# --- Freeze 재현 ----------------------------------------------------------


def test_gold_facts_reproduce_the_frozen_sc_p02_statuses(gold: dict):
    """정답지 -> 정본 매퍼 -> Rule Engine이 SC-P02 Freeze 기대값을 재현한다."""
    mapping = facts_to_mapping(
        contract_facts(gold), analysis_id="SC-P02", controller_id="ctrl-001"
    )
    statuses = {
        item.rule_id: item.status.value
        for item in P0RuleEngine().evaluate_mapping_result(mapping, poc="poc2")
    }
    assert statuses == gold["expected_rule_status"]


def test_builder_is_deterministic():
    """NFR-03: 같은 입력은 같은 산출물을 내야 한다."""
    before = GOLD_PATH.read_text(encoding="utf-8")
    result = subprocess.run(
        [sys.executable, str(BUILDER_PATH)],
        capture_output=True, text=True, cwd=str(ROOT),
    )
    assert result.returncode == 0, result.stderr
    assert GOLD_PATH.read_text(encoding="utf-8") == before


# --- 데이터셋 등록 --------------------------------------------------------


def test_poc2_case_exposes_both_documents(case):
    assert set(case.documents) == {"incident", "notice"}
    assert case.poc == "poc2"


def test_document_for_picks_the_right_side(case):
    assert "사고 인지시점" in case.document_for("incident_record")
    assert "사고 인지시점" not in case.document_for("notification_notice")
    assert "개인정보 유출 통지문" in case.document_for("notification_notice")
