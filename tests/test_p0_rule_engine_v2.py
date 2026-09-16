from pathlib import Path

from rdflib import Graph, Literal, Namespace, RDF

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

def test_p1_r07_partial_right_procedures_are_amber_not_green():
    ex = Namespace("https://example.org/right-partial#")
    graph = Graph()
    subject = ex.subject
    right1 = ex.right1
    right2 = ex.right2
    procedure = ex.procedure

    graph.add((subject, RDF.type, PIPA.DataSubject))
    graph.add((subject, PIPA.hasRight, right1))
    graph.add((subject, PIPA.hasRight, right2))
    graph.add((right1, RDF.type, PIPA.DataSubjectRight))
    graph.add((right2, RDF.type, PIPA.DataSubjectRight))
    graph.add((right1, PIPA.hasExerciseProcedure, procedure))
    graph.add((procedure, RDF.type, PIPA.RightsExerciseProcedure))
    graph.add((procedure, PIPA.hasProcedureDescription, Literal("온라인 신청")))

    result = P0RuleEngine().evaluate_rule(graph, "P1-R07")
    assert result.status.value == "AMBER"


def test_p1_r07_rights_with_no_procedure_are_red():
    ex = Namespace("https://example.org/right-missing#")
    graph = Graph()
    subject = ex.subject
    right = ex.right
    graph.add((subject, RDF.type, PIPA.DataSubject))
    graph.add((subject, PIPA.hasRight, right))
    graph.add((right, RDF.type, PIPA.DataSubjectRight))

    result = P0RuleEngine().evaluate_rule(graph, "P1-R07")
    assert result.status.value == "RED"


def test_p2_r03_missing_one_required_notice_fact_is_red():
    ex = Namespace("https://example.org/p2r03#")
    graph = Graph()
    notice = ex.notice
    graph.add((notice, RDF.type, PIPA.NotificationNotice))
    graph.add((notice, PIPA.noticeIncidentTime, Literal("2026-09-05T14:30:00+09:00")))

    result = P0RuleEngine().evaluate_rule(graph, "P2-R03")
    assert result.status.value == "RED"


def test_p2_r08_all_required_roles_plus_extra_role_is_green():
    ex = Namespace("https://example.org/p2r08#")
    graph = Graph()
    incident = ex.incident
    graph.add((incident, RDF.type, PIPA.DataBreachIncident))

    roles = [
        "data_subject_guidance",
        "controller_response",
        "remedy_procedure",
        "post_incident_mitigation",
        "internal_tracking",
    ]
    for index, role in enumerate(roles):
        measure = ex[f"measure{index}"]
        graph.add((measure, RDF.type, PIPA.IncidentResponseMeasure))
        graph.add((measure, PIPA.measureRole, Literal(role)))
        graph.add((incident, PIPA.hasResponseMeasure, measure))

    result = P0RuleEngine().evaluate_rule(graph, "P2-R08")
    assert result.status.value == "GREEN"


def test_p2_r08_unclassified_response_measure_is_amber():
    ex = Namespace("https://example.org/p2r08-unclassified#")
    graph = Graph()
    incident = ex.incident
    measure = ex.measure
    graph.add((incident, RDF.type, PIPA.DataBreachIncident))
    graph.add((measure, RDF.type, PIPA.IncidentResponseMeasure))
    graph.add((incident, PIPA.hasResponseMeasure, measure))

    result = P0RuleEngine().evaluate_rule(graph, "P2-R08")
    assert result.status.value == "AMBER"


def test_p3_r01_untyped_legal_basis_is_amber():
    ex = Namespace("https://example.org/p3r01#")
    graph = Graph()
    activity = ex.activity
    basis = ex.basis
    graph.add((activity, RDF.type, PIPA.CollectionAndUse))
    graph.add((activity, PIPA.hasLegalBasis, basis))

    result = P0RuleEngine().evaluate_rule(graph, "P3-R01")
    assert result.status.value == "AMBER"


def test_p3_r02_purpose_without_description_is_amber():
    ex = Namespace("https://example.org/p3r02#")
    graph = Graph()
    activity = ex.activity
    basis = ex.consent
    request = ex.request
    purpose = ex.purpose

    graph.add((activity, RDF.type, PIPA.CollectionAndUse))
    graph.add((basis, RDF.type, PIPA.Consent))
    graph.add((request, RDF.type, PIPA.ConsentRequest))
    graph.add((purpose, RDF.type, PIPA.ProcessingPurpose))
    graph.add((activity, PIPA.hasLegalBasis, basis))
    graph.add((activity, PIPA.hasConsentRequest, request))
    graph.add((activity, PIPA.hasPurpose, purpose))

    result = P0RuleEngine().evaluate_rule(graph, "P3-R02")
    assert result.status.value == "AMBER"


def test_p3_r03_personal_information_without_item_name_is_amber():
    ex = Namespace("https://example.org/p3r03#")
    graph = Graph()
    activity = ex.activity
    basis = ex.consent
    request = ex.request
    item = ex.item

    graph.add((activity, RDF.type, PIPA.CollectionAndUse))
    graph.add((basis, RDF.type, PIPA.Consent))
    graph.add((request, RDF.type, PIPA.ConsentRequest))
    graph.add((item, RDF.type, PIPA.PersonalInformation))
    graph.add((activity, PIPA.hasLegalBasis, basis))
    graph.add((activity, PIPA.hasConsentRequest, request))
    graph.add((activity, PIPA.hasPersonalInformation, item))

    result = P0RuleEngine().evaluate_rule(graph, "P3-R03")
    assert result.status.value == "AMBER"


def test_p3_r04_unidentified_end_condition_is_amber():
    ex = Namespace("https://example.org/p3r04#")
    graph = Graph()
    activity = ex.activity
    basis = ex.consent
    retention = ex.retention
    end = ex.end

    graph.add((activity, RDF.type, PIPA.CollectionAndUse))
    graph.add((basis, RDF.type, PIPA.Consent))
    graph.add((retention, RDF.type, PIPA.Retention))
    graph.add((end, RDF.type, PIPA.RetentionEndCondition))
    graph.add((activity, PIPA.hasLegalBasis, basis))
    graph.add((activity, PIPA.hasRetention, retention))
    graph.add((retention, PIPA.hasRetentionEndCondition, end))

    result = P0RuleEngine().evaluate_rule(graph, "P3-R04")
    assert result.status.value == "AMBER"


def test_p3_r06_unknown_refusal_value_does_not_become_green():
    ex = Namespace("https://example.org/p3r06#")
    graph = Graph()
    activity = ex.activity
    item = ex.item
    request = ex.request

    graph.add((activity, RDF.type, PIPA.CollectionAndUse))
    graph.add((item, RDF.type, PIPA.PersonalInformation))
    graph.add((request, RDF.type, PIPA.ConsentRequest))
    graph.add((activity, PIPA.hasPersonalInformation, item))
    graph.add((activity, PIPA.hasConsentRequest, request))
    graph.add((item, PIPA.isRequired, Literal(False)))
    graph.add((request, PIPA.deniesServiceOnOptionalRefusal, Literal("UNKNOWN")))

    result = P0RuleEngine().evaluate_rule(graph, "P3-R06")
    assert result.status.value == "AMBER"


def test_rule_metadata_legal_basis_matches_frozen_spec():
    engine = P0RuleEngine()
    for metadata in engine.metadata.values():
        assert metadata.legal_basis == metadata.source_spec_legal_basis
