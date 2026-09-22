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

from app.facts.graph import facts_to_graph
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
    graph = facts_to_graph(
        build_facts(form),
        analysis_id=form.scenario_id,
        controller_id=form.controller_id,
        controller_name=form.controller_name,
    )
    return {item.rule_id: item.status.value for item in engine.evaluate_graph(graph, poc="poc3")}


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
            "위탁 목록만 비어 있음 (여부 미정)",
            lambda d: d.update(entrustments=[], entrustment=None),
            "P3-R11", "AMBER",
        ),
        (
            "위탁 없음이 확인됨",
            lambda d: d.update(entrustments=[], entrustment=False),
            "P3-R11", "N/A",
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


def test_absence_flag_contradicting_the_list_is_rejected(raw_form: dict):
    """위탁이 없다고 해놓고 수탁자를 입력한 Form은 모순이므로 거부한다."""
    contradiction = mutate(raw_form, lambda d: d.update(entrustment=False))
    with pytest.raises(ValueError, match="비어 있지 않습니다"):
        build_facts(DesignForm.model_validate(contradiction))


def test_explicit_absence_does_not_create_the_activity(raw_form: dict):
    form = DesignForm.model_validate(raw_form)
    graph = facts_to_graph(build_facts(form), controller_id=form.controller_id)
    assert not list(graph.subjects(RDF.type, PIPA.ThirdPartyProvision))
    assert not list(graph.subjects(RDF.type, PIPA.CrossBorderTransfer))


# --- 발견 사항 -----------------------------------------------------------


def test_p3_r11_does_not_evaluate_the_processor_name(engine: P0RuleEngine):
    """P3-R11이 수탁자 '이름'을 보지 않는다. 같은 상황에서 P1-R06은 RED다.

    Fact Dictionary 7장은 P3-R11 = F3-12 + F3-13이고, F3-12는
    `EntrustedProcessing.hasProcessor -> EntrustedProcessor.hasName` (string)이다.
    즉 P3-R11은 수탁자명을 소비해야 하는데, 엔진은 hasProcessor 링크의 존재만 본다.

    설계단계에서 '수탁자 미정'은 매우 흔한 상태이고 PoC3의 존재 이유이기도 하므로
    AMBER로 잡히는 것이 맞아 보인다. 다만 기능명세서 14장 2번이 "P0 Rule의 조건/status
    의미를 코드 편의상 바꾸지 않는다"고 정하므로 엔진을 고치지 않고 현재 동작을 기록한다.
    Rule 담당자가 판단하면 이 테스트를 뒤집어야 한다.
    """
    from rdflib import Graph, Literal, Namespace

    ex = Namespace("https://example.org/t#")

    def build(processor_name: str | None) -> Graph:
        graph = Graph()
        graph.add((ex.act, RDF.type, PIPA.EntrustedProcessing))
        graph.add((ex.act, PIPA.hasProcessor, ex.proc))
        graph.add((ex.proc, RDF.type, PIPA.EntrustedProcessor))
        graph.add((ex.act, PIPA.entrustedTaskText, Literal("상품 배송")))
        if processor_name is not None:
            graph.add((ex.proc, PIPA.hasName, Literal(processor_name)))
        return graph

    named = build("빠른택배 주식회사")
    assert engine.evaluate_rule(named, "P1-R06").status.value == "GREEN"
    assert engine.evaluate_rule(named, "P3-R11").status.value == "GREEN"

    nameless = build(None)
    assert engine.evaluate_rule(nameless, "P1-R06").status.value == "RED"
    assert engine.evaluate_rule(nameless, "P3-R11").status.value == "GREEN"  # 불일치
