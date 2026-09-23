"""PoC3 타입 Form -> 정본 Builder -> 정본 Mapper -> Rule Engine (D01-001~013, TST-007).

Form -> Fact 변환과 Fact -> RDF 매핑의 정본은 app.builders / app.mapping이다.
여기서는 타입이 붙은 입력 계약(app.forms.poc3)이 그 정본 위에서 올바로 동작하는지,
그리고 설계 변경이 기대한 Rule 전이를 만드는지 본다.
"""

import copy
import json
from pathlib import Path

import pytest
from rdflib import RDF

from app.facts.graph import facts_to_graph, facts_to_mapping
from app.forms.poc3 import DesignForm, build_facts
from app.mapping.fact_schema import fact_type
from app.mapping.ontology_mapper import PIPA
from app.rules.engine import P0RuleEngine

ROOT = Path(__file__).resolve().parents[1]
FORM_PATH = ROOT / "evals" / "poc3" / "sc_d01_form.json"

POC3_RULES = ["P3-R01", "P3-R02", "P3-R03", "P3-R04", "P3-R05", "P3-R06", "P3-R08", "P3-R11"]

# Fact Dictionary 7장 Rule <-> Fact Coverage (PoC3)
RULE_FACT_COVERAGE = {
    "P3-R01": {"F3-01", "F3-02"},
    "P3-R02": {"F3-02", "F3-03", "F3-04"},
    "P3-R03": {"F3-02", "F3-03", "F3-05"},
    "P3-R04": {"F3-02", "F3-03", "F3-06"},
    "P3-R05": {"F3-05", "F3-07", "F3-08"},
    "P3-R06": {"F3-07", "F3-09"},
    "P3-R08": {"F3-10", "F3-11"},
    "P3-R11": {"F3-12", "F3-13"},
}


@pytest.fixture(scope="module")
def engine() -> P0RuleEngine:
    return P0RuleEngine()


@pytest.fixture(scope="module")
def raw_form() -> dict:
    return json.loads(FORM_PATH.read_text(encoding="utf-8"))


def facts_for(form_dict: dict) -> list[dict]:
    return build_facts(DesignForm.model_validate(form_dict))


def evaluate(form_dict: dict, engine: P0RuleEngine) -> dict[str, str]:
    form = DesignForm.model_validate(form_dict)
    mapping = facts_to_mapping(
        build_facts(form),
        analysis_id=form.scenario_id,
        controller_id=form.controller_id,
        controller_name=form.controller_name,
    )
    return {
        item.rule_id: item.status.value
        for item in engine.evaluate_mapping_result(mapping, poc="poc3")
    }


def mutate(raw_form: dict, change) -> dict:
    payload = copy.deepcopy(raw_form)
    change(payload)
    return payload


# --- E2E ----------------------------------------------------------------


def test_sc_d01_form_reproduces_all_green(raw_form: dict, engine: P0RuleEngine):
    """TST-007: 구조화 Form -> Fact -> 8 Rule.

    SC-D01 TTL의 Freeze 기대값(8개 GREEN)을 Form 경로로 재현한다.
    """
    assert evaluate(raw_form, engine) == {rule: "GREEN" for rule in POC3_RULES}


def test_form_is_rejected_when_it_has_unknown_fields(raw_form: dict):
    """COM-002: 모르는 필드를 조용히 무시하지 않는다."""
    payload = mutate(raw_form, lambda d: d.update(invented_field="x"))
    with pytest.raises(ValueError):
        DesignForm.model_validate(payload)


def test_all_poc3_fact_ids_in_the_coverage_table_are_produced(raw_form: dict):
    present = {fact_type(item["fact_id"]) for item in facts_for(raw_form)}
    required = set().union(*RULE_FACT_COVERAGE.values())
    assert required <= present, f"누락: {sorted(required - present)}"


def test_evidence_uses_field_path_not_text_offsets(raw_form: dict):
    """Fact Dictionary 8장: PoC3는 구조화 Form이므로 field_path를 쓴다."""
    for item in facts_for(raw_form):
        for piece in item["evidence"]:
            assert piece.get("field_path"), item["fact_id"]
            assert "text" not in piece


# --- Fact Dictionary 6장: 항목별 design_items 구조 ------------------------


def test_every_item_carries_its_own_required_flag_and_rationale(raw_form: dict):
    """6장 필수 요건: isRequired와 designRationale을 항목별로 묶는다.

    문서 전역 단일값이 되면 P3-R05/R06이 어떤 항목을 평가하는지 잃어버린다.
    """
    form = DesignForm.model_validate(raw_form)
    graph = facts_to_graph(build_facts(form), controller_id=form.controller_id)

    items = list(graph.subjects(RDF.type, PIPA.PersonalInformation))
    expected = sum(len(a.design_items) for a in form.collection_activities)
    assert len(items) == expected

    for item in items:
        assert list(graph.objects(item, PIPA.hasItemName))
        assert list(graph.objects(item, PIPA.isRequired))
        assert list(graph.objects(item, PIPA.designRationale))


def test_item_facts_identify_their_item_by_name(raw_form: dict):
    """F3-07/F3-08의 값은 어느 항목에 대한 것인지 스스로 밝혀야 한다."""
    activity = raw_form["collection_activities"][0]
    names = {item["item_name"] for item in activity["design_items"]}
    for item in facts_for(raw_form):
        if fact_type(item["fact_id"]) in {"F3-07", "F3-08"}:
            if item["activity_id"] == activity["activity_id"]:
                assert item["value"]["item_name"] in names


# --- 상태 전이 (TST-003) -------------------------------------------------


@pytest.mark.parametrize(
    "label, change, rule_id, expected",
    [
        (
            "법적근거 미정",
            lambda d: d["collection_activities"][0].update(legal_basis=None),
            "P3-R01", "AMBER",
        ),
        (
            "동의 처리목적 미정",
            lambda d: d["collection_activities"][0].update(purpose=None),
            "P3-R02", "AMBER",
        ),
        (
            "필수항목 설계사유 미정",
            lambda d: d["collection_activities"][0]["design_items"][0].update(design_rationale=None),
            "P3-R05", "AMBER",
        ),
        (
            "항목 필수여부 미정",
            lambda d: d["collection_activities"][1]["design_items"][0].update(is_required=None),
            "P3-R05", "AMBER",
        ),
        (
            "선택항목 미동의 시 서비스 거부",
            lambda d: d["collection_activities"][1]["consent"].update(
                denies_service_on_optional_refusal=True
            ),
            "P3-R06", "RED",
        ),
        (
            "서비스 거부 여부 미정",
            lambda d: d["collection_activities"][1]["consent"].update(
                denies_service_on_optional_refusal=None
            ),
            "P3-R06", "AMBER",
        ),
        (
            "보유 종료조건 미정",
            lambda d: d["collection_activities"][0]["retention"].update(end_condition=None),
            "P3-R04", "AMBER",
        ),
        (
            "위탁 목록이 비어 있음",
            lambda d: d.update(entrustments=[]),
            "P3-R11", "AMBER",
        ),
    ],
)
def test_form_change_moves_the_expected_rule(
    raw_form: dict, engine: P0RuleEngine, label: str, change, rule_id: str, expected: str
):
    assert evaluate(mutate(raw_form, change), engine)[rule_id] == expected, label


def test_false_denial_is_green_but_unset_denial_is_amber(raw_form: dict, engine: P0RuleEngine):
    """Fact Dictionary 1장: false는 confirmed 값이며 unknown과 다르다.

    선택항목 미동의 시 서비스를 거부하지 '않는다'는 설계는 GREEN이어야 하고,
    아직 정하지 않은 상태는 AMBER여야 한다. Form이 False를 결측으로 취급하면
    둘이 같아져 버린다.
    """
    assert evaluate(raw_form, engine)["P3-R06"] == "GREEN"
    unset = mutate(
        raw_form,
        lambda d: d["collection_activities"][1]["consent"].update(
            denies_service_on_optional_refusal=None
        ),
    )
    assert evaluate(unset, engine)["P3-R06"] == "AMBER"


def test_untouched_activity_types_create_no_instances(raw_form: dict):
    """Form에 없는 처리행위 유형은 그래프에 만들지 않는다.

    Fact Dictionary 3·5장에 "이 유형이 없음"을 담을 Fact ID가 없으므로,
    없다는 사실은 Fact가 없다는 것으로만 나타난다.
    """
    form = DesignForm.model_validate(raw_form)
    graph = facts_to_graph(build_facts(form), controller_id=form.controller_id)
    assert not list(graph.subjects(RDF.type, PIPA.ThirdPartyProvision))
    assert not list(graph.subjects(RDF.type, PIPA.CrossBorderTransfer))
