"""v1.1 P1-R11 처리하는 개인정보 항목 기재 (시행령 제31조 제1항 제1호).

수집·이용 처리행위마다 항목이 하나 이상 기재되어야 GREEN이다 (P1-R01과 같은 단위).
"""

from app.facts.graph import facts_to_mapping
from app.rules.engine import P0RuleEngine

EV = [{"text": "x", "start_offset": 0, "end_offset": 1}]


def items_fact(activity: str, value, state: str = "confirmed") -> dict:
    return {
        "fact_id": f"F1-22:{activity}", "subject_id": activity, "activity_id": activity,
        "ontology_class": "CollectionAndUse", "ontology_property": "hasPersonalInformation",
        "value": value if state == "confirmed" else None, "value_state": state,
        "source_type": "policy_text", "evidence": EV, "schema_version": "fact-1.0",
    }


def status(facts: list[dict]) -> str:
    results = P0RuleEngine().evaluate_mapping_result(facts_to_mapping(facts), poc="poc1")
    return next(r for r in results if r.rule_id == "P1-R11").status.value


def test_green_when_every_activity_lists_items():
    assert status([
        items_fact("act-collection-001", ["이름", "이메일 주소"]),
        items_fact("act-collection-002", ["결제 내역"]),
    ]) == "GREEN"


def test_red_when_one_activity_has_no_items_written():
    assert status([
        items_fact("act-collection-001", ["이름"]),
        items_fact("act-collection-002", None, "absent"),
    ]) == "RED"


def test_yellow_when_items_are_only_a_blanket_phrase():
    """'상담 처리에 필요한 정보'처럼 항목을 특정하지 않으면 unknown -> 확인 필요."""
    assert status([
        items_fact("act-collection-001", ["이름"]),
        items_fact("act-collection-002", None, "unknown"),
    ]) == "YELLOW"


def test_unextracted_is_yellow_not_red():
    """F1-22 Fact가 아예 없으면 '기재 없음'이 아니라 '추출 안 됨'이다."""
    purpose = {
        "fact_id": "F1-02:act-collection-001", "subject_id": "act-collection-001",
        "activity_id": "act-collection-001", "ontology_class": "CollectionAndUse",
        "ontology_property": "hasPurpose", "value": "회원 관리", "value_state": "confirmed",
        "source_type": "policy_text", "evidence": EV, "schema_version": "fact-1.0",
    }
    assert status([purpose]) == "YELLOW"


def test_collection_items_attach_only_to_their_activity():
    """F1-22는 그 수집·이용 처리행위에만 붙는다. 다른 처리행위로 새지 않는다."""
    from rdflib import RDF

    from app.rules.engine import PIPA

    graph = facts_to_mapping([
        items_fact("act-collection-001", ["이름"]),
        items_fact("act-collection-002", ["결제 내역"]),
    ]).graph
    activities = list(graph.subjects(RDF.type, PIPA.CollectionAndUse))
    assert len(activities) == 2
    for activity in activities:
        names = {
            str(name)
            for item in graph.objects(activity, PIPA.hasPersonalInformation)
            for name in graph.objects(item, PIPA.hasItemName)
        }
        assert len(names) == 1, names
