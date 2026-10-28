"""v1.1 — linked accident/notice time consistency; no legal-deadline decision."""
from rdflib import Graph, Literal, Namespace, RDF
from app.rules.engine import META, PIPA, P0RuleEngine

EX = Namespace("https://example.org/time-match#")


def make_graph(actual="2026-09-05T14:30:00+09:00", stated="2026-09-05T14:30:00+09:00"):
    graph = Graph()
    graph.add((EX.incident, RDF.type, PIPA.DataBreachIncident))
    graph.add((EX.incident, PIPA.hasNotificationNotice, EX.notice))
    graph.add((EX.notice, RDF.type, PIPA.NotificationNotice))
    if actual is not None:
        graph.add((EX.incident, PIPA.incidentDate, Literal(actual)))
    if stated is not None:
        graph.add((EX.notice, PIPA.noticeIncidentTime, Literal(stated)))
    return graph


def evaluate(graph):
    return P0RuleEngine().evaluate_rule(graph, "P2-R09")


def test_same_instant_is_green():
    result = evaluate(make_graph())
    assert result.status.value == "GREEN"
    assert result.evidence
    assert all("incidentDate" in str(item) or "noticeIncidentTime" in str(item) or "hasNotificationNotice" in str(item) for item in result.evidence if item.evidence_type == "rdf_assertion")


def test_different_time_is_yellow_with_both_facts_in_evidence():
    result = evaluate(make_graph(stated="2026-09-05T15:30:00+09:00"))
    assert result.status.value == "YELLOW"
    assert "incident_time_mismatch" in result.uncertain_facts
    assert any(e.predicate == "incidentDate" for e in result.evidence)
    assert any(e.predicate == "noticeIncidentTime" for e in result.evidence)


def test_date_only_notice_on_the_same_day_is_yellow_but_not_called_a_mismatch():
    """통지문이 날짜만 적으면 Extractor가 00:00으로 채운다.

    날짜가 같은데 "시점이 다르다"고 하면 사실과 다르다. 판정은 명세대로 YELLOW
    (값이 불명확)이고, 사유와 확인 항목만 정확해야 한다.
    """
    result = evaluate(make_graph(stated="2026-09-05T00:00:00+09:00"))
    assert result.status.value == "YELLOW"
    assert "incident_time_precision" in result.uncertain_facts
    assert "incident_time_mismatch" not in result.uncertain_facts
    assert "다릅니다" not in result.instance_results[0].reason


def test_date_only_record_on_the_same_day_is_also_precision_not_mismatch():
    result = evaluate(make_graph(actual="2026-09-05T00:00:00+09:00"))
    assert "incident_time_precision" in result.uncertain_facts


def test_date_only_on_a_different_day_is_still_a_mismatch():
    result = evaluate(make_graph(stated="2026-09-04T00:00:00+09:00"))
    assert result.status.value == "YELLOW"
    assert "incident_time_mismatch" in result.uncertain_facts


def test_both_date_only_on_the_same_day_is_green():
    result = evaluate(make_graph(actual="2026-09-05T00:00:00+09:00",
                                 stated="2026-09-05T00:00:00+09:00"))
    assert result.status.value == "GREEN"


def test_same_day_check_uses_the_date_only_sides_timezone():
    """UTC로는 전날(9/4 23:30Z)이지만 KST로는 9/5 08:30 -> 같은 날짜."""
    result = evaluate(make_graph(actual="2026-09-04T23:30:00Z",
                                 stated="2026-09-05T00:00:00+09:00"))
    assert "incident_time_precision" in result.uncertain_facts


def test_timezone_equivalent_instant_is_green():
    result = evaluate(make_graph(stated="2026-09-05T05:30:00Z"))
    assert result.status.value == "GREEN"


def test_missing_notice_time_is_yellow_not_red():
    result = evaluate(make_graph(stated=None))
    assert result.status.value == "YELLOW"
    assert result.applicability.value == "TRUE"


def test_missing_actual_time_is_yellow_not_red():
    assert evaluate(make_graph(actual=None)).status.value == "YELLOW"


def test_missing_timezone_is_yellow():
    assert evaluate(make_graph(stated="2026-09-05T14:30:00")).status.value == "YELLOW"


def test_explicitly_absent_notice_is_na():
    graph = Graph()
    graph.add((EX.incident, RDF.type, PIPA.DataBreachIncident))
    graph.add((META.document, META.notificationNoticeState, Literal("confirmed_false")))
    result = evaluate(graph)
    assert result.status.value == "N/A"


def test_absent_notice_without_presence_metadata_is_yellow():
    graph = Graph()
    graph.add((EX.incident, RDF.type, PIPA.DataBreachIncident))
    assert evaluate(graph).status.value == "YELLOW"


def test_notice_from_other_incident_is_not_mixed():
    graph = make_graph()
    graph.add((EX.other_incident, RDF.type, PIPA.DataBreachIncident))
    graph.add((EX.other_incident, PIPA.incidentDate, Literal("2026-09-05T08:00:00+09:00")))
    # The second incident has no linked notice; never reuse EX.notice from first incident.
    result = evaluate(graph)
    assert result.status.value == "YELLOW"
    assert any(r.instance_id == str(EX.other_incident) and r.status.value == "YELLOW" for r in result.instance_results)
