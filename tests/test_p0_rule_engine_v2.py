from pathlib import Path

from rdflib import Graph, Literal, Namespace, RDF

from app.mapping.ontology_mapper import OntologyMapper
from app.rules.engine import P0RuleEngine

BASE = Path(__file__).resolve().parent
PIPA = Namespace("https://w3id.org/pipa-compliance/ontology#")
META = Namespace("https://w3id.org/pipa-compliance/metadata#")


def load(name: str) -> Graph:
    return Graph().parse(BASE / name, format="turtle")


def statuses(results):
    return {result.rule_id: result.status.value for result in results}


def frozen_fact(
    fact_id,
    *,
    subject_id,
    activity_id,
    ontology_class,
    ontology_property,
    value,
    value_state="confirmed",
    source_type="structured_form",
):
    return {
        "fact_id": fact_id,
        "subject_id": subject_id,
        "activity_id": activity_id,
        "ontology_class": ontology_class,
        "ontology_property": ontology_property,
        "value": value,
        "value_state": value_state,
        "source_type": source_type,
        "evidence": [{"field_path": f"test.{fact_id}"}],
        "schema_version": "fact-1.0",
    }


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


def test_rule_fact_coverage_matches_frozen_fact_dictionary():
    expected = {
        "P1-R01": ("F1-01", "F1-02"),
        "P1-R02": ("F1-03", "F1-04"),
        "P1-R03": ("F1-05", "F1-06", "F1-07"),
        "P1-R04": ("F1-08",),
        "P1-R06": ("F1-09", "F1-10"),
        "P1-R07": ("F1-11", "F1-12"),
        "P2-R01": ("F2-01", "F2-02", "F2-03"),
        "P2-R02": ("F2-02", "F2-04"),
        "P2-R03": ("F2-08", "F2-09"),
        "P2-R08": ("F2-01", "F2-10"),
        "P3-R01": ("F3-01", "F3-02"),
        "P3-R02": ("F3-02", "F3-03", "F3-04"),
        "P3-R03": ("F3-02", "F3-03", "F3-05"),
        "P3-R04": ("F3-02", "F3-03", "F3-06"),
        "P3-R05": ("F3-05", "F3-07", "F3-08"),
        "P3-R06": ("F3-07", "F3-09"),
        "P3-R08": ("F3-10", "F3-11"),
        "P3-R11": ("F3-12", "F3-13"),
    }
    metadata = P0RuleEngine().metadata
    assert set(metadata) == set(expected)
    assert {rule_id: item.required_fact_ids for rule_id, item in metadata.items()} == expected


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
    assert p2_r01.status.value == "GREEN"
    assert all("triggersNotificationObligation" not in fact for fact in (
        p2_r01.matched_facts + p2_r01.missing_facts + p2_r01.uncertain_facts
    ))


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
    ex = Namespace("https://example.org/test#")
    incident = ex.incident
    notice = ex.notice
    graph.add((incident, RDF.type, PIPA.DataBreachIncident))
    graph.add((incident, PIPA.incidentDate, Literal("2026-09-05T14:30:00+09:00")))
    graph.add((incident, PIPA.hasNotificationNotice, notice))
    graph.add((notice, RDF.type, PIPA.NotificationNotice))
    graph.add((notice, PIPA.hasIncidentCircumstances, ex.circumstance))
    result = P0RuleEngine().evaluate_rule(graph, "P2-R03")
    assert result.status.value in {"AMBER", "RED"}
    assert result.status.value != "GREEN"
    assert any("noticeIncidentTime" in fact for fact in result.missing_facts + result.uncertain_facts)


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


def test_p2_r08_rejects_role_outside_frozen_four_as_amber():
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
    assert result.status.value == "AMBER"
    assert "unexpected_measure_role:internal_tracking" in result.uncertain_facts


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
    request = ex.request
    retention = ex.retention
    end = ex.end

    graph.add((activity, RDF.type, PIPA.CollectionAndUse))
    graph.add((basis, RDF.type, PIPA.Consent))
    graph.add((request, RDF.type, PIPA.ConsentRequest))
    graph.add((retention, RDF.type, PIPA.Retention))
    graph.add((end, RDF.type, PIPA.RetentionEndCondition))
    graph.add((activity, PIPA.hasLegalBasis, basis))
    graph.add((activity, PIPA.hasConsentRequest, request))
    graph.add((activity, PIPA.hasRetention, retention))
    graph.add((retention, PIPA.hasRetentionEndCondition, end))

    result = P0RuleEngine().evaluate_rule(graph, "P3-R04")
    assert result.status.value == "AMBER"


def test_p3_r04_requires_f3_03_consent_request():
    ex = Namespace("https://example.org/p3r04-request#")
    graph = Graph()
    activity = ex.activity
    basis = ex.consent
    retention = ex.retention
    period = ex.period

    graph.add((activity, RDF.type, PIPA.CollectionAndUse))
    graph.add((basis, RDF.type, PIPA.Consent))
    graph.add((retention, RDF.type, PIPA.Retention))
    graph.add((period, RDF.type, PIPA.RetentionPeriod))
    graph.add((activity, PIPA.hasLegalBasis, basis))
    graph.add((activity, PIPA.hasRetention, retention))
    graph.add((retention, PIPA.hasRetentionPeriod, period))
    graph.add((period, PIPA.hasDurationValue, Literal("회원 탈퇴 시까지")))

    result = P0RuleEngine().evaluate_rule(graph, "P3-R04")
    assert result.status.value == "RED"
    assert any("hasConsentRequest" in fact for fact in result.missing_facts)


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


def test_p1_r04_unknown_destruction_method_is_amber():
    ex = Namespace("https://example.org/p1r04-unknown#")
    graph = Graph()
    destruction = ex.destruction
    graph.add((destruction, RDF.type, PIPA.Destruction))
    graph.add((destruction, PIPA.hasDestructionMethod, Literal("UNKNOWN")))

    result = P0RuleEngine().evaluate_rule(graph, "P1-R04")
    assert result.status.value == "AMBER"


def test_p1_r06_unknown_task_or_processor_name_is_amber():
    ex = Namespace("https://example.org/p1r06-unknown#")
    graph = Graph()
    activity = ex.activity
    processor = ex.processor
    graph.add((activity, RDF.type, PIPA.EntrustedProcessing))
    graph.add((activity, PIPA.hasProcessor, processor))
    graph.add((processor, PIPA.hasName, Literal("UNKNOWN")))
    graph.add((activity, PIPA.entrustedTaskText, Literal("UNKNOWN")))

    result = P0RuleEngine().evaluate_rule(graph, "P1-R06")
    assert result.status.value == "AMBER"


def test_p3_r05_unknown_design_rationale_is_amber():
    ex = Namespace("https://example.org/p3r05-unknown#")
    graph = Graph()
    activity = ex.activity
    item = ex.item
    graph.add((activity, RDF.type, PIPA.CollectionAndUse))
    graph.add((activity, PIPA.hasPersonalInformation, item))
    graph.add((item, PIPA.hasItemName, Literal("이메일")))
    graph.add((item, PIPA.isRequired, Literal(True)))
    graph.add((item, PIPA.designRationale, Literal("UNKNOWN")))

    result = P0RuleEngine().evaluate_rule(graph, "P3-R05")
    assert result.status.value == "AMBER"


def test_p3_r05_unknown_required_flag_is_amber():
    ex = Namespace("https://example.org/p3r05-flag-unknown#")
    graph = Graph()
    activity = ex.activity
    item = ex.item
    graph.add((activity, RDF.type, PIPA.CollectionAndUse))
    graph.add((activity, PIPA.hasPersonalInformation, item))
    graph.add((item, PIPA.hasItemName, Literal("이메일")))
    graph.add((item, PIPA.isRequired, Literal("UNKNOWN")))

    result = P0RuleEngine().evaluate_rule(graph, "P3-R05")
    assert result.status.value == "AMBER"


def test_p2_r02_unknown_item_name_does_not_compare_as_green():
    ex = Namespace("https://example.org/p2r02-item-unknown#")
    graph = Graph()
    incident = ex.incident
    notice = ex.notice
    actual = ex.actual
    mentioned = ex.mentioned
    graph.add((incident, RDF.type, PIPA.DataBreachIncident))
    graph.add((incident, PIPA.affectsPersonalInformation, actual))
    graph.add((incident, PIPA.hasNotificationNotice, notice))
    graph.add((notice, RDF.type, PIPA.NotificationNotice))
    graph.add((notice, PIPA.mentionsPersonalInformation, mentioned))
    graph.add((actual, PIPA.hasItemName, Literal("UNKNOWN")))
    graph.add((mentioned, PIPA.hasItemName, Literal("UNKNOWN")))

    result = P0RuleEngine().evaluate_rule(graph, "P2-R02")
    assert result.status.value == "AMBER"


def test_p2_r01_v1_does_not_require_notification_obligation_fact():
    ex = Namespace("https://example.org/p2r01-v1#")
    graph = Graph()
    incident = ex.incident
    item = ex.item
    graph.add((incident, RDF.type, PIPA.DataBreachIncident))
    graph.add((item, RDF.type, PIPA.PersonalInformation))
    graph.add((item, PIPA.hasItemName, Literal("이메일")))
    graph.add((incident, PIPA.affectsPersonalInformation, item))
    graph.add((incident, PIPA.hasNotificationNotice, ex.notice))

    result = P0RuleEngine().evaluate_rule(graph, "P2-R01")
    assert result.status.value == "GREEN"
    assert result.applicability.value == "TRUE"
    assert all("triggersNotificationObligation" not in fact for fact in (
        result.matched_facts + result.missing_facts + result.uncertain_facts
    ))


def test_p2_r01_missing_notice_is_red_without_reporting_obligation_inference():
    ex = Namespace("https://example.org/p2r01-no-notice#")
    graph = Graph()
    incident = ex.incident
    item = ex.item
    graph.add((incident, RDF.type, PIPA.DataBreachIncident))
    graph.add((item, RDF.type, PIPA.PersonalInformation))
    graph.add((item, PIPA.hasItemName, Literal("이메일")))
    graph.add((incident, PIPA.affectsPersonalInformation, item))

    result = P0RuleEngine().evaluate_rule(graph, "P2-R01")
    assert result.status.value == "RED"
    assert any("hasNotificationNotice" in fact for fact in result.missing_facts)
    assert "통지 의무 대상 여부 판정이 아닙니다" in result.instance_results[0].reason


def test_p2_r02_missing_notice_is_amber_without_explicit_false():
    ex = Namespace("https://example.org/p2r02-no-notice#")
    graph = Graph()
    incident = ex.incident
    graph.add((incident, RDF.type, PIPA.DataBreachIncident))
    graph.add((incident, PIPA.affectsPersonalInformation, ex.item))

    result = P0RuleEngine().evaluate_rule(graph, "P2-R02")
    assert result.status.value == "AMBER"
    assert result.applicability.value == "UNKNOWN"


def test_p2_r03_missing_notice_is_amber_without_explicit_false():
    graph = Graph()
    result = P0RuleEngine().evaluate_rule(graph, "P2-R03")
    assert result.status.value == "AMBER"
    assert result.applicability.value == "UNKNOWN"


def test_p2_r03_explicit_no_notice_can_be_not_applicable():
    ex = Namespace("https://example.org/p2r03-explicit-none#")
    graph = Graph()
    controller = ex.controller
    graph.add((controller, RDF.type, PIPA.PersonalInformationController))
    graph.add((controller, META.notificationNoticeState, Literal("confirmed_false")))

    result = P0RuleEngine().evaluate_rule(graph, "P2-R03")
    assert result.status.value == "N/A"
    assert result.applicability.value == "FALSE"


def test_p3_r11_requires_processor_name_from_f3_12():
    ex = Namespace("https://example.org/p3r11-no-name#")
    graph = Graph()
    activity = ex.activity
    processor = ex.processor
    graph.add((activity, RDF.type, PIPA.EntrustedProcessing))
    graph.add((activity, PIPA.hasProcessor, processor))
    graph.add((activity, PIPA.entrustedTaskText, Literal("고객 문의 처리")))

    result = P0RuleEngine().evaluate_rule(graph, "P3-R11")
    assert result.status.value == "RED"
    assert any("hasName" in fact for fact in result.missing_facts)


def test_p1_r06_still_requires_processor_name():
    ex = Namespace("https://example.org/p1r06-no-name#")
    graph = Graph()
    activity = ex.activity
    processor = ex.processor
    graph.add((activity, RDF.type, PIPA.EntrustedProcessing))
    graph.add((activity, PIPA.hasProcessor, processor))
    graph.add((activity, PIPA.entrustedTaskText, Literal("고객 문의 처리")))

    result = P0RuleEngine().evaluate_rule(graph, "P1-R06")
    assert result.status.value == "RED"


def test_p3_r11_unknown_task_is_amber():
    ex = Namespace("https://example.org/p3r11-unknown#")
    graph = Graph()
    activity = ex.activity
    processor = ex.processor
    graph.add((activity, RDF.type, PIPA.EntrustedProcessing))
    graph.add((activity, PIPA.hasProcessor, processor))
    graph.add((processor, PIPA.hasName, Literal("고객센터 수탁자")))
    graph.add((activity, PIPA.entrustedTaskText, Literal("UNKNOWN")))

    result = P0RuleEngine().evaluate_rule(graph, "P3-R11")
    assert result.status.value == "AMBER"


def test_p1_r01_requires_concrete_f1_02_purpose_value():
    ex = Namespace("https://example.org/p1r01-detail#")
    graph = Graph()
    activity = ex.activity
    purpose = ex.purpose
    graph.add((activity, RDF.type, PIPA.CollectionAndUse))
    graph.add((purpose, RDF.type, PIPA.ProcessingPurpose))
    graph.add((activity, PIPA.hasPurpose, purpose))

    result = P0RuleEngine().evaluate_rule(graph, "P1-R01")
    assert result.status.value == "AMBER"
    assert any("hasPurposeDescription" in fact for fact in result.uncertain_facts)


def test_p1_r03_requires_concrete_frozen_values_not_only_links():
    ex = Namespace("https://example.org/p1r03-detail#")
    graph = Graph()
    activity = ex.activity
    graph.add((activity, RDF.type, PIPA.ThirdPartyProvision))
    graph.add((activity, PIPA.hasRecipient, ex.recipient))
    graph.add((activity, PIPA.hasPersonalInformation, ex.item))
    graph.add((activity, PIPA.hasPurpose, ex.purpose))

    result = P0RuleEngine().evaluate_rule(graph, "P1-R03")
    assert result.status.value == "AMBER"
    assert any("hasName" in fact for fact in result.uncertain_facts)
    assert any("hasItemName" in fact for fact in result.uncertain_facts)
    assert any("hasPurposeDescription" in fact for fact in result.uncertain_facts)


def test_p2_r01_requires_concrete_f2_02_item_name():
    ex = Namespace("https://example.org/p2r01-detail#")
    graph = Graph()
    incident = ex.incident
    graph.add((incident, RDF.type, PIPA.DataBreachIncident))
    graph.add((incident, PIPA.affectsPersonalInformation, ex.item))
    graph.add((incident, PIPA.hasNotificationNotice, ex.notice))

    result = P0RuleEngine().evaluate_rule(graph, "P2-R01")
    assert result.status.value == "AMBER"


def test_strict_fact_contract_preserves_unknown_as_amber():
    facts = [
        frozen_fact(
            "F3-01-001",
            subject_id="act-001",
            activity_id="act-001",
            ontology_class="CollectionAndUse",
            ontology_property=None,
            value=None,
        ),
        frozen_fact(
            "F3-02-001",
            subject_id="act-001",
            activity_id="act-001",
            ontology_class="CollectionAndUse",
            ontology_property="hasLegalBasis",
            value=None,
            value_state="unknown",
        ),
    ]
    mapping = OntologyMapper("strict-unknown", controller_id="controller").map(facts)

    result = P0RuleEngine().evaluate_rule(
        mapping.graph,
        "P3-R01",
        facts=mapping.facts,
    )
    assert result.status.value == "AMBER"
    assert "fact:F3-02:unknown" in result.uncertain_facts


def test_strict_fact_contract_missing_required_fact_prevents_green():
    facts = [
        frozen_fact(
            "F3-11-001",
            subject_id="end-001",
            activity_id="act-001",
            ontology_class="RetentionEndCondition",
            ontology_property="triggersDestruction",
            value={
                "end_condition": "회원 탈퇴",
                "destruction_method": "복구 불가능한 방법으로 삭제",
            },
        )
    ]
    mapping = OntologyMapper("strict-coverage", controller_id="controller").map(facts)

    # F3-11 mapping can materialize the retention/end-condition structure, so
    # graph-only evaluation used to become GREEN even though frozen F3-10 was
    # never supplied. Strict mode must keep that input-contract gap visible.
    result = P0RuleEngine().evaluate_rule(
        mapping.graph,
        "P3-R08",
        facts=mapping.facts,
    )
    assert result.status.value == "AMBER"
    assert "fact:F3-10:missing_envelope" in result.uncertain_facts


def test_strict_fact_contract_absent_required_fact_is_red():
    facts = [
        frozen_fact(
            "F3-10-001",
            subject_id="retention-001",
            activity_id="act-001",
            ontology_class="Retention",
            ontology_property="hasRetentionEndCondition",
            value=None,
            value_state="absent",
        ),
        frozen_fact(
            "F3-11-001",
            subject_id="end-001",
            activity_id="act-001",
            ontology_class="RetentionEndCondition",
            ontology_property="triggersDestruction",
            value={
                "end_condition": "회원 탈퇴",
                "destruction_method": "복구 불가능한 방법으로 삭제",
            },
        ),
    ]
    mapping = OntologyMapper("strict-absent", controller_id="controller").map(facts)

    result = P0RuleEngine().evaluate_rule(
        mapping.graph,
        "P3-R08",
        facts=mapping.facts,
    )
    assert result.status.value == "RED"
    assert "fact:F3-10:absent" in result.missing_facts


def test_strict_fact_contract_keeps_confirmed_false_as_value():
    facts = [
        frozen_fact(
            "F3-07-001",
            subject_id="item-001",
            activity_id="act-001",
            ontology_class="PersonalInformation",
            ontology_property="isRequired",
            value={"item_name": "관심사", "is_required": False},
        ),
        frozen_fact(
            "F3-09-001",
            subject_id="request-001",
            activity_id="act-001",
            ontology_class="ConsentRequest",
            ontology_property="deniesServiceOnOptionalRefusal",
            value=False,
        ),
    ]
    mapping = OntologyMapper("strict-false", controller_id="controller").map(facts)

    result = P0RuleEngine().evaluate_rule(
        mapping.graph,
        "P3-R06",
        facts=mapping.facts,
    )
    assert result.status.value == "GREEN"


def test_strict_p1_r02_period_or_end_condition_allows_explicit_absent_alternative():
    facts = [
        frozen_fact(
            "F1-03-001",
            subject_id="act-001",
            activity_id="act-001",
            ontology_class="CollectionAndUse",
            ontology_property="hasRetention",
            value="1년",
            source_type="policy_text",
        ),
        frozen_fact(
            "F1-04-001",
            subject_id="act-001",
            activity_id="act-001",
            ontology_class="CollectionAndUse",
            ontology_property="hasRetention",
            value=None,
            value_state="absent",
            source_type="policy_text",
        ),
    ]
    mapping = OntologyMapper("strict-p1r02-or", controller_id="controller").map(facts)

    result = P0RuleEngine().evaluate_rule(
        mapping.graph,
        "P1-R02",
        facts=mapping.facts,
    )
    assert result.status.value == "GREEN"


def test_strict_p1_r02_unknown_alternative_does_not_override_confirmed_period():
    facts = [
        frozen_fact(
            "F1-03-001",
            subject_id="act-001",
            activity_id="act-001",
            ontology_class="CollectionAndUse",
            ontology_property="hasRetention",
            value="1년",
            source_type="policy_text",
        ),
        frozen_fact(
            "F1-04-001",
            subject_id="act-001",
            activity_id="act-001",
            ontology_class="CollectionAndUse",
            ontology_property="hasRetention",
            value=None,
            value_state="unknown",
            source_type="policy_text",
        ),
    ]
    mapping = OntologyMapper("strict-p1r02-unknown-or", controller_id="controller").map(facts)

    result = P0RuleEngine().evaluate_rule(
        mapping.graph,
        "P1-R02",
        facts=mapping.facts,
    )
    assert result.status.value == "GREEN"


def test_p3_r08_unknown_destruction_method_is_amber():
    ex = Namespace("https://example.org/p3r08-unknown#")
    graph = Graph()
    retention = ex.retention
    end = ex.end
    destruction = ex.destruction
    graph.add((retention, RDF.type, PIPA.Retention))
    graph.add((end, RDF.type, PIPA.RetentionEndCondition))
    graph.add((destruction, RDF.type, PIPA.Destruction))
    graph.add((retention, PIPA.hasRetentionEndCondition, end))
    graph.add((end, PIPA.triggersDestruction, destruction))
    graph.add((destruction, PIPA.hasDestructionMethod, Literal("UNKNOWN")))

    result = P0RuleEngine().evaluate_rule(graph, "P3-R08")
    assert result.status.value == "AMBER"
