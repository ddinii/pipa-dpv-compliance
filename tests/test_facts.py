"""Fact Envelope / Validator / Mapper 테스트.

가장 중요한 것은 test_gold_facts_reproduce_sc_p01_statuses다.
gold Fact -> 검증 -> RDF -> Rule Engine이 SC-P01 Freeze 기대값을 그대로 재현하면
Fact 계약과 매핑 규칙이 서로 맞는다는 뜻이다.
"""

import json
from pathlib import Path

import pytest
from app.facts.graph import facts_to_graph
from app.facts.models import Evidence, FactEnvelope
from app.facts.validator import FactValidationError, group_by_activity, validate_facts
from app.rules.engine import P0RuleEngine

ROOT = Path(__file__).resolve().parents[1]
GOLD_PATH = ROOT / "evals" / "poc1" / "sc_p01_gold_facts.json"
POLICY_PATH = ROOT / "evals" / "poc1" / "sc_p01_policy.txt"


@pytest.fixture(scope="module")
def gold() -> dict:
    return json.loads(GOLD_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def policy() -> str:
    return POLICY_PATH.read_text(encoding="utf-8")


def make_fact(**overrides) -> dict:
    base = {
        "fact_id": "F1-02:act-collection-001",
        "subject_id": "act-collection-001",
        "activity_id": "act-collection-001",
        "ontology_class": "CollectionAndUse",
        "ontology_property": "hasPurpose",
        "value": "회원 식별",
        "value_state": "confirmed",
        "source_type": "policy_text",
        "evidence": [{"text": "회원 식별", "start_offset": 0, "end_offset": 5}],
        "schema_version": "fact-1.0",
    }
    base.update(overrides)
    return base


# --- Envelope -----------------------------------------------------------


def test_evidence_requires_exactly_one_locator():
    with pytest.raises(ValueError, match="정확히 하나"):
        Evidence(text="가", start_offset=0, end_offset=1, field_path="a.b")
    with pytest.raises(ValueError, match="정확히 하나"):
        Evidence()


def test_evidence_offset_length_must_match_text():
    with pytest.raises(ValueError, match="offset 길이"):
        Evidence(text="회원 식별", start_offset=0, end_offset=99)


def test_field_path_evidence_rejects_offsets():
    Evidence(field_path="design_items[0].is_required")  # PoC3 형태
    with pytest.raises(ValueError, match="offset을 함께"):
        Evidence(field_path="a.b", start_offset=0)


def test_unknown_and_absent_facts_must_not_carry_a_value():
    for state in ("unknown", "absent"):
        with pytest.raises(ValueError, match="value가 있습니다"):
            FactEnvelope.model_validate(make_fact(value_state=state, value="뭔가"))


def test_false_is_a_confirmed_value_not_unknown():
    """Fact Dictionary 1장: false는 confirmed 값이며 unknown과 다르다."""
    fact = FactEnvelope.model_validate(make_fact(
        fact_id="F3-09:act-collection-001",
        ontology_property="deniesServiceOnOptionalRefusal",
        value=False,
        value_state="confirmed",
    ))
    assert fact.value is False


def test_confirmed_property_assertion_requires_a_value():
    with pytest.raises(ValueError, match="value가 필요"):
        FactEnvelope.model_validate(make_fact(value=None))


def test_class_assertion_may_omit_value():
    fact = FactEnvelope.model_validate(make_fact(
        fact_id="F1-01:act-collection-001", ontology_property=None, value=None,
    ))
    assert fact.fact_type == "F1-01"


def test_schema_version_is_not_auto_filled():
    """COM-002: 임의 보완 금지. 누락을 기본값으로 메우지 않는다."""
    payload = make_fact()
    del payload["schema_version"]
    with pytest.raises(ValueError):
        FactEnvelope.model_validate(payload)


def test_unknown_fields_are_rejected():
    with pytest.raises(ValueError):
        FactEnvelope.model_validate(make_fact(hallucinated_field="x"))


# --- Validator ----------------------------------------------------------


def test_validator_reports_offset_mismatch_against_the_document():
    document = "전혀 다른 문서 내용입니다."
    with pytest.raises(FactValidationError, match="offset이"):
        validate_facts([make_fact()], document=document)


def test_validator_rejects_duplicate_fact_ids():
    with pytest.raises(FactValidationError, match="중복"):
        validate_facts([make_fact(), make_fact()])


def test_validator_collects_every_issue_instead_of_failing_fast():
    """Envelope 단계 문제는 첫 건에서 멈추지 않고 모아서 보고한다.

    파이프라인 계약 위반(필수 필드/enum/중복 ID)은 정본인
    app.mapping.fact_schema가 먼저 잡고 즉시 실패한다.
    """
    with pytest.raises(FactValidationError) as exc:
        validate_facts([
            make_fact(fact_id="F1-02:a", value_state="unknown"),
            make_fact(fact_id="F1-04:b", value_state="absent"),
        ])
    assert len(exc.value.issues) == 2


def test_contract_violation_is_reported_by_the_canonical_validator():
    with pytest.raises(FactValidationError, match="fact_id"):
        validate_facts([make_fact(fact_id="완전히 다른 형식")])


def test_group_by_activity_keeps_activities_separate(gold: dict, policy: str):
    """TST-002: 서로 다른 activity의 값이 섞이지 않아야 한다."""
    facts = validate_facts(gold["facts"], document=policy)
    groups = group_by_activity(facts)
    assert "act-provision-001" in groups
    for activity_id, members in groups.items():
        assert all(item.activity_id == activity_id for item in members)


# --- 정본 매핑과의 연결 --------------------------------------------------


def test_gold_facts_reproduce_sc_p01_statuses(gold: dict, policy: str):
    """Fact -> 검증 -> RDF -> Rule Engine이 Freeze 기대값을 재현해야 한다.

    매핑 자체는 app.mapping.OntologyMapper(정본)가 한다. 여기서는 gold set이
    그 정본 규약과 맞는지, 그리고 결과가 SC-P01 Freeze 기대값과 같은지 본다.
    """
    facts = validate_facts(gold["facts"], document=policy)
    results = P0RuleEngine().evaluate_graph(facts_to_graph(facts), poc="poc1")
    actual = {result.rule_id: result.status.value for result in results}
    assert actual == gold["expected_rule_status"]


def test_mapping_is_deterministic(gold: dict):
    """NFR-03: 같은 Fact는 같은 그래프를 내야 한다."""
    facts = validate_facts(gold["facts"])
    assert set(facts_to_graph(facts)) == set(facts_to_graph(facts))
