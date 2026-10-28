"""P1-R08: F1-11의 선정 5개 권리 누락 점검. P1-R07과 별개다."""

from rdflib import Graph, Literal, Namespace, RDF, RDFS
import pytest

from app.facts.graph import facts_to_mapping
from app.rules.engine import P0RuleEngine, PIPA

EX = Namespace("https://example.org/p1r08#")


def graph_with_rights(*names):
    graph = Graph()
    graph.add((EX.subject, RDF.type, PIPA.DataSubject))
    for i, name in enumerate(names):
        uri = EX[f"right_{i}"]
        graph.add((EX.subject, PIPA.hasRight, uri))
        graph.add((uri, RDF.type, PIPA.DataSubjectRight))
        if name is not None:
            graph.add((uri, RDFS.label, Literal(name)))
    return graph


def test_full_rights_are_green():
    result = P0RuleEngine().evaluate_rule(
        graph_with_rights("개인정보 열람 요구", "정정·삭제", "처리정지", "동의 철회"),
        "P1-R08",
    )
    assert result.status.value == "GREEN"
    assert result.applicability.value == "TRUE"
    assert result.evidence


@pytest.mark.parametrize("missing", ["열람", "정정", "삭제", "처리정지", "동의 철회"])
def test_each_missing_right_is_yellow_not_red(missing):
    names = ["열람", "정정", "삭제", "처리정지", "동의 철회"]
    names.remove(missing)
    result = P0RuleEngine().evaluate_rule(graph_with_rights(*names), "P1-R08")
    assert result.status.value == "YELLOW"
    assert f"right:{missing}" in result.uncertain_facts
    assert missing in result.instance_results[0].reason


def test_correction_does_not_cover_deletion():
    result = P0RuleEngine().evaluate_rule(graph_with_rights("열람", "정정", "처리정지", "동의 철회"), "P1-R08")
    assert "right:삭제" in result.uncertain_facts


def test_withdrawal_with_korean_particle_is_recognized():
    result = P0RuleEngine().evaluate_rule(graph_with_rights("열람", "정정·삭제", "처리정지", "동의를 철회"), "P1-R08")
    assert result.status.value == "GREEN"


def test_right_without_label_does_not_turn_green():
    result = P0RuleEngine().evaluate_rule(graph_with_rights("열람", "정정·삭제", "처리정지", None), "P1-R08")
    assert result.status.value == "YELLOW"


def test_empty_graph_is_yellow_not_red():
    result = P0RuleEngine().evaluate_rule(Graph(), "P1-R08")
    assert result.status.value == "YELLOW"


def test_explicit_absent_fact_is_yellow_not_red():
    fact = {
        "fact_id": "F1-11:subj-001",
        "subject_id": "subj-001", "activity_id": None,
        "ontology_class": "DataSubject", "ontology_property": "hasRight",
        "value": None, "value_state": "absent", "source_type": "policy_text",
        "evidence": [{"text": "권리", "start_offset": 0, "end_offset": 2}], "schema_version": "fact-1.0",
    }
    result = P0RuleEngine().evaluate_mapping_result(facts_to_mapping([fact]), poc="poc1")
    status = {item.rule_id: item.status.value for item in result}
    assert status["P1-R08"] == "YELLOW"


def test_unknown_fact_is_yellow():
    fact = {
        "fact_id": "F1-11:subj-001", "subject_id": "subj-001", "activity_id": None,
        "ontology_class": "DataSubject", "ontology_property": "hasRight",
        "value": None, "value_state": "unknown", "source_type": "policy_text",
        "evidence": [{"text": "권리", "start_offset": 0, "end_offset": 2}], "schema_version": "fact-1.0",
    }
    result = P0RuleEngine().evaluate_mapping_result(facts_to_mapping([fact]), poc="poc1")
    assert next(item for item in result if item.rule_id == "P1-R08").status.value == "YELLOW"


def test_absent_envelope_yellow():
    result = P0RuleEngine().evaluate_rule(graph_with_rights("열람", "정정·삭제", "처리정지", "동의 철회"), "P1-R08", facts=[])
    assert result.status.value == "YELLOW"


def test_legacy_ontology_iri_aliases_are_supported():
    graph = Graph()
    graph.add((EX.subject, RDF.type, PIPA.DataSubject))
    for name in ["RightAccess", "RightCorrectionDeletion", "RightSuspension", "RightWithdraw"]:
        graph.add((EX.subject, PIPA.hasRight, EX[name]))
    result = P0RuleEngine().evaluate_rule(graph, "P1-R08")
    assert result.status.value == "GREEN"


def test_negative_right_statement_is_not_counted():
    names = ["열람 불가", "정정·삭제", "처리정지", "동의 철회"]
    result = P0RuleEngine().evaluate_rule(graph_with_rights(*names), "P1-R08")
    assert result.status.value == "YELLOW"


@pytest.mark.parametrize("phrase", ["개인정보 처리의 정지 요구", "처리 중단 요구", "처리 중지 요구"])
def test_suspension_paraphrases_are_recognized(phrase):
    """'처리의 정지'는 법령·처리방침에 흔한 표현이다. 놓치면 거짓 YELLOW가 난다."""
    result = P0RuleEngine().evaluate_rule(
        graph_with_rights("열람", "정정·삭제", phrase, "동의 철회"), "P1-R08"
    )
    assert result.status.value == "GREEN"


def test_parenthetical_caveat_does_not_erase_the_right():
    """괄호 속 단서의 '불가' 한 단어가 권리 전체를 부정으로 만들면 안 된다."""
    names = [
        "열람", "정정",
        "개인정보의 삭제 요구(다른 법령에서 수집 대상으로 명시된 경우 삭제 불가)",
        "처리정지", "동의 철회",
    ]
    result = P0RuleEngine().evaluate_rule(graph_with_rights(*names), "P1-R08")
    assert result.status.value == "GREEN"


def test_right_mentioned_only_inside_a_caveat_is_not_counted():
    """괄호 안에서만 언급된 권리는 기재된 권리로 세지 않는다."""
    names = ["열람", "정정 요구 (삭제 불가)", "처리정지", "동의 철회"]
    result = P0RuleEngine().evaluate_rule(graph_with_rights(*names), "P1-R08")
    assert result.status.value == "YELLOW"
    assert "right:삭제" in result.uncertain_facts


def test_refusal_is_not_withdrawal():
    names = ["열람", "정정·삭제", "처리정지", "동의 거부"]
    result = P0RuleEngine().evaluate_rule(graph_with_rights(*names), "P1-R08")
    assert "right:동의 철회" in result.uncertain_facts
