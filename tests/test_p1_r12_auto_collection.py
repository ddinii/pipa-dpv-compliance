"""P1-R12: 자동수집장치 사용 조건 + 설치·운영 및 거부 기재."""
import pytest

from app.facts.graph import facts_to_mapping
from app.rules.engine import P0RuleEngine

EV = [{"text": "가상 처리방침"}]


def fact(number, value, state="confirmed"):
    return {
        "fact_id": f"F1-{number}:automatic-collection", "subject_id": "automatic-collection",
        "activity_id": None, "ontology_class": "PersonalInformationController",
        "ontology_property": {
            "23": "hasAutomaticCollectionDevice",
            "24": "hasAutomaticCollectionOperation",
            "25": "hasAutomaticCollectionOptOutMethod",
        }[number],
        "value": value if state == "confirmed" else None, "value_state": state,
        "source_type": "policy_text", "evidence": EV, "schema_version": "fact-1.0",
    }


def result(facts):
    items = P0RuleEngine().evaluate_mapping_result(facts_to_mapping(facts), poc="poc1")
    return next(r for r in items if r.rule_id == "P1-R12")


@pytest.mark.parametrize("facts,expected", [
    ([fact("23", "쿠키"), fact("24", "접속 시 쿠키가 설치됨"), fact("25", "브라우저 설정에서 쿠키 차단")], "GREEN"),
    ([fact("23", "쿠키"), fact("24", None, "absent"), fact("25", None, "absent")], "RED"),
    ([fact("23", "쿠키"), fact("24", "접속 시 쿠키 설치"), fact("25", None, "unknown")], "YELLOW"),
    ([fact("23", "미사용"), fact("24", None, "absent"), fact("25", None, "absent")], "N/A"),
    ([fact("23", None, "absent"), fact("24", None, "absent"), fact("25", None, "absent")], "YELLOW"),
    ([fact("23", None, "unknown"), fact("24", None, "absent"), fact("25", None, "absent")], "YELLOW"),
    ([fact("23", "쿠키"), fact("24", "접속 시 쿠키 설치")], "YELLOW"),
])
def test_judgments(facts, expected):
    assert result(facts).status.value == expected


def test_controller_properties_are_mapped():
    from rdflib import RDF
    from app.mapping.ontology_mapper import PIPA
    mapped = facts_to_mapping([fact("23", "쿠키"), fact("24", "접속 시 설치")])
    controllers = list(mapped.graph.subjects(RDF.type, PIPA.PersonalInformationController))
    assert controllers
    assert any(str(v) == "쿠키" for c in controllers for v in mapped.graph.objects(c, PIPA.hasAutomaticCollectionDevice))


def test_mock_has_new_facts():
    from app.extractors.poc1_mock_extractor import MockPoC1Extractor
    facts = MockPoC1Extractor().extract(analysis_id="test", controller_id="test", controller_name=None, policy_text="합성")
    assert {"F1-23", "F1-24", "F1-25"} <= {f["fact_id"][:5] for f in facts}
