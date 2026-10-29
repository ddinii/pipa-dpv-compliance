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


def test_evidence_lists_item_names_not_hashed_item_links():
    """처리행위→항목 노드 연결(해시 ID)은 화면에서 읽히지 않으므로 근거로 내지 않는다."""
    results = P0RuleEngine().evaluate_mapping_result(
        facts_to_mapping([items_fact("act-collection-001", ["이름", "이메일 주소"])]), poc="poc1"
    )
    result = next(r for r in results if r.rule_id == "P1-R11")
    predicates = [str(e.predicate) for e in result.instance_results[0].evidence]
    assert predicates and all(p.endswith("hasItemName") for p in predicates)


def test_default_mock_extractor_supplies_v11_facts():
    """기본 데모(mock)에서 P1-R09~P1-R11이 '입력 데이터 미전달' YELLOW로 나오지 않아야 한다."""
    from app.services.compliance import run_policy_check
    from app.extractors.poc1_mock_extractor import MockPoC1Extractor

    results = run_policy_check(
        {"analysis_id": "mock", "controller": {"controller_id": "c"}, "policy_text": "합성"},
        extractor=MockPoC1Extractor(),
    )
    statuses = {r.rule_id: r.status.value for r in results}
    assert statuses["P1-R09"] == "GREEN"
    assert statuses["P1-R10"] == "GREEN"
    assert statuses["P1-R11"] == "GREEN"


def purpose_fact(activity: str) -> dict:
    """처리행위 노드는 confirmed Fact가 있어야 생긴다. absent/unknown만으로는 처리행위가 없다."""
    return {**items_fact(activity, None), "fact_id": f"F1-02:{activity}",
            "ontology_property": "hasPurpose", "value": "합성 목적"}


def instance_statuses(facts: list[dict], rule_id: str = "P1-R11") -> dict[str, str]:
    results = P0RuleEngine().evaluate_mapping_result(facts_to_mapping(facts), poc="poc1")
    result = next(r for r in results if r.rule_id == rule_id)
    return {i.instance_id.rsplit("/", 1)[-1]: i.status.value for i in result.instance_results}


def test_absent_fact_turns_only_its_own_activity_red():
    """한 처리행위의 absent가 다른 처리행위까지 RED로 만들지 않는다 (Fact 계약의 처리행위별 적용)."""
    assert instance_statuses([
        items_fact("act-collection-001", ["이름"]),
        items_fact("act-collection-002", None, "absent"),
        purpose_fact("act-collection-002"),
    ]) == {"act-collection-001": "GREEN", "act-collection-002": "RED"}


def test_unknown_fact_turns_only_its_own_activity_yellow():
    assert instance_statuses([
        items_fact("act-collection-001", ["이름"]),
        items_fact("act-collection-002", None, "unknown"),
        purpose_fact("act-collection-002"),
    ]) == {"act-collection-001": "GREEN", "act-collection-002": "YELLOW"}


def test_document_scope_absent_still_applies_to_the_document_result():
    """처리행위에 속하지 않는 Fact(보호책임자)는 이전처럼 문서 단위 결과에 반영된다."""
    officer = {
        "fact_id": "F1-20:privacy-officer", "subject_id": "privacy-officer", "activity_id": None,
        "ontology_class": "PersonalInformationController", "ontology_property": "hasPrivacyOfficer",
        "value": None, "value_state": "absent",
        "source_type": "policy_text", "evidence": EV, "schema_version": "fact-1.0",
    }
    contact = {**officer, "fact_id": "F1-21:privacy-officer", "ontology_class": "PrivacyOfficer",
               "ontology_property": "hasContact", "value": ["02-0000-0000"], "value_state": "confirmed"}
    assert set(instance_statuses([officer, contact], "P1-R10").values()) == {"RED"}
