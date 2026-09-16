from pathlib import Path

from rdflib import Graph, Namespace, RDF

from app.rules.engine import P0RuleEngine

BASE = Path(__file__).resolve().parent
PIPA = Namespace("https://w3id.org/pipa-compliance/ontology#")


def load(name: str) -> Graph:
    return Graph().parse(BASE / name, format="turtle")


def statuses(results):
    return {result.rule_id: result.status.value for result in results}


def test_frozen_ontology_file_is_not_modified_by_rule_engine():
    ontology = (BASE.parent / "ontology" / "PIPA_Ontology_v1.0.ttl").read_text(encoding="utf-8-sig")
    assert "NotificationObligation" not in ontology
    assert "triggersNotificationObligation" not in ontology


def test_all_18_frozen_rule_ids_are_loaded():
    engine = P0RuleEngine()
    assert set(engine.metadata) == {
        "P1-R01", "P1-R02", "P1-R03", "P1-R04", "P1-R06", "P1-R07",
        "P2-R01", "P2-R02", "P2-R03", "P2-R08",
        "P3-R01", "P3-R02", "P3-R03", "P3-R04", "P3-R05", "P3-R06", "P3-R08", "P3-R11",
    }


def test_sc_p01_expected_freeze_results():
    result = statuses(P0RuleEngine().evaluate_graph(load("SC-P01_FINAL_Protege.ttl"), poc="poc1"))
    assert result == {
        "P1-R01": "GREEN",
        "P1-R02": "AMBER",
        "P1-R03": "GREEN",
        "P1-R04": "GREEN",
        "P1-R06": "GREEN",
        "P1-R07": "GREEN",
    }


def test_sc_p02_expected_freeze_results():
    results = P0RuleEngine().evaluate_graph(load("SC-P02_FINAL_Protege.ttl"), poc="poc2")
    assert statuses(results) == {
        "P2-R01": "GREEN",
        "P2-R02": "GREEN",
        "P2-R03": "GREEN",
        "P2-R08": "GREEN",
    }
    p2_r01 = next(item for item in results if item.rule_id == "P2-R01")
    assert any("does not define" in note for note in p2_r01.implementation_notes)


def test_sc_d01_expected_freeze_results():
    result = statuses(P0RuleEngine().evaluate_graph(load("SC-D01_FINAL_Protege.ttl"), poc="poc3"))
    assert result == {
        "P3-R01": "GREEN",
        "P3-R02": "GREEN",
        "P3-R03": "GREEN",
        "P3-R04": "GREEN",
        "P3-R05": "GREEN",
        "P3-R06": "GREEN",
        "P3-R08": "GREEN",
        "P3-R11": "GREEN",
    }


def test_p2_r03_does_not_substitute_incident_time_for_notice_time():
    graph = Graph()
    incident = Namespace("https://example.org/test#").incident
    notice = Namespace("https://example.org/test#").notice
    graph.add((incident, RDF.type, PIPA.DataBreachIncident))
    graph.add((incident, PIPA.hasNotificationNotice, notice))
    graph.add((notice, RDF.type, PIPA.NotificationNotice))
    graph.add((notice, PIPA.hasIncidentCircumstances, Namespace("https://example.org/test#").circumstance))
    result = P0RuleEngine().evaluate_rule(graph, "P2-R03")
    assert result.status.value in {"AMBER", "RED"}
    assert result.status.value != "GREEN"


def test_rule_engine_does_not_mix_facts_across_activities():
    ex = Namespace("https://example.org/no-mix#")
    graph = Graph()
    a1 = ex.provision1
    a2 = ex.provision2
    graph.add((a1, RDF.type, PIPA.ThirdPartyProvision))
    graph.add((a1, PIPA.hasRecipient, ex.recipient))
    graph.add((a2, RDF.type, PIPA.ThirdPartyProvision))
    graph.add((a2, PIPA.hasPersonalInformation, ex.pi))
    graph.add((a2, PIPA.hasPurpose, ex.purpose))
    result = P0RuleEngine().evaluate_rule(graph, "P1-R03")
    assert result.status.value != "GREEN"
    assert len(result.instance_results) == 2
