"""P2-R10: 통지문 피해 신고 접수 담당부서·연락처 검토."""
import pytest
from app.facts.graph import facts_to_mapping
from app.rules.engine import P0RuleEngine

EV = [{"text": "가상 통지문"}]


def fact(number, value, state="confirmed"):
    return {
        "fact_id": f"F2-{number}:breach-notice", "subject_id": "breach-notice",
        "activity_id": "breach-incident", "ontology_class": "NotificationNotice",
        "ontology_property": {"11": "hasDamageReportDepartment", "12": "hasDamageReportContact"}[number],
        "value": value if state == "confirmed" else None, "value_state": state,
        "source_type": "notification_notice", "evidence": EV, "schema_version": "fact-1.0",
    }


def notice():
    return {"fact_id": "F2-03:breach-incident", "subject_id": "breach-incident",
            "activity_id": "breach-incident", "ontology_class": "DataBreachIncident",
            "ontology_property": "hasNotificationNotice", "value": {"notice_id": "breach-notice"},
            "value_state": "confirmed", "source_type": "notification_notice",
            "evidence": EV, "schema_version": "fact-1.0"}


def result(facts, metadata=None):
    mapped = facts_to_mapping(facts, system_metadata=metadata)
    return next(r for r in P0RuleEngine().evaluate_mapping_result(mapped, poc="poc2")
                if r.rule_id == "P2-R10")


@pytest.mark.parametrize("facts,expected", [
    ([notice(), fact("11", "개인정보보호팀"), fact("12", "privacy@example.com")], "GREEN"),
    ([notice(), fact("11", "개인정보보호팀"), fact("12", None, "absent")], "RED"),
    ([notice(), fact("11", None, "unknown"), fact("12", None, "unknown")], "YELLOW"),
    ([notice(), fact("11", "개인정보보호팀")], "YELLOW"),
    ([notice(), fact("11", None, "absent"), fact("12", None, "absent")], "RED"),
])
def test_notice_requirements(facts, expected):
    assert result(facts).status.value == expected


def test_notification_absence_is_not_applicable():
    from app.extractors.poc2_mock_extractor import MockPoc2Extractor
    mocked = MockPoc2Extractor().extract(analysis_id="x", controller_id="x", controller_name=None,
                                           incident={"record": "가상"}, notification=None)
    from app.services.compliance import with_notice_presence
    assert result(mocked, with_notice_presence([], notification_provided=False)).status.value == "N/A"


def test_incident_response_fact_does_not_supply_contact():
    assert result([notice(), fact("11", None, "absent"), fact("12", None, "absent")]).status.value == "RED"


def test_mock_notice_contains_new_facts():
    from app.extractors.poc2_mock_extractor import MockPoc2Extractor
    facts = MockPoc2Extractor().extract(analysis_id="x", controller_id="x", controller_name=None,
                                        incident={"record": "가상"}, notification={"text": "가상"})
    assert {"F2-11", "F2-12"} <= {f["fact_id"][:5] for f in facts}
