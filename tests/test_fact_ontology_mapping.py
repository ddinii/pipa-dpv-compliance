from __future__ import annotations

import json
import unittest
from pathlib import Path

from pyshacl import validate
from rdflib import Graph, Literal, Namespace, RDF, OWL

from app.builders import build_poc3_facts
from app.mapping import FactValidationError, OntologyMapper
from app.mapping.mapping_registry import FACT_SPECS


BASE = Path(__file__).resolve().parents[1]
PIPA = Namespace("https://w3id.org/pipa-compliance/ontology#")


def fact(
    fact_id: str,
    *,
    subject_id: str,
    activity_id: str | None,
    ontology_class: str,
    ontology_property: str | None,
    value,
    source_type: str,
    state: str = "confirmed",
):
    return {
        "fact_id": fact_id,
        "subject_id": subject_id,
        "activity_id": activity_id,
        "ontology_class": ontology_class,
        "ontology_property": ontology_property,
        "value": value,
        "value_state": state,
        "source_type": source_type,
        "evidence": [{"field_path": f"test.{fact_id}"}],
        "schema_version": "fact-1.0",
    }


class FactOntologyMappingTests(unittest.TestCase):
    def test_poc1_all_frozen_fact_types(self):
        facts = [
            fact("F1-01-001", subject_id="collect", activity_id="collect", ontology_class="CollectionAndUse", ontology_property=None, value=None, source_type="policy_text"),
            fact("F1-02-001", subject_id="collect", activity_id="collect", ontology_class="CollectionAndUse", ontology_property="hasPurpose", value="회원 가입 및 관리", source_type="policy_text"),
            fact("F1-03-001", subject_id="collect", activity_id="collect", ontology_class="CollectionAndUse", ontology_property="hasRetention", value="회원 탈퇴 시까지", source_type="policy_text"),
            fact("F1-04-001", subject_id="collect", activity_id="collect", ontology_class="CollectionAndUse", ontology_property="hasRetention", value="회원 탈퇴", source_type="policy_text"),
            fact("F1-05-001", subject_id="provision", activity_id="provision", ontology_class="ThirdPartyProvision", ontology_property="hasRecipient", value="입점 판매자", source_type="policy_text"),
            fact("F1-06-001", subject_id="provision", activity_id="provision", ontology_class="ThirdPartyProvision", ontology_property="hasPersonalInformation", value=["수령인 이름", "배송지 주소"], source_type="policy_text"),
            fact("F1-07-001", subject_id="provision", activity_id="provision", ontology_class="ThirdPartyProvision", ontology_property="hasPurpose", value="상품 배송", source_type="policy_text"),
            fact("F1-08-001", subject_id="destroy", activity_id="destroy", ontology_class="Destruction", ontology_property="hasDestructionMethod", value="복구가 어렵도록 삭제", source_type="policy_text"),
            fact("F1-09-001", subject_id="entrust", activity_id="entrust", ontology_class="EntrustedProcessing", ontology_property="hasProcessor", value="K-Cloud", source_type="policy_text"),
            fact("F1-10-001", subject_id="entrust", activity_id="entrust", ontology_class="EntrustedProcessing", ontology_property=None, value="서비스 인프라 운영", source_type="policy_text"),
            fact("F1-11-001", subject_id="user", activity_id=None, ontology_class="DataSubject", ontology_property="hasRight", value=["열람", "정정·삭제"], source_type="policy_text"),
            fact("F1-12-001", subject_id="열람", activity_id=None, ontology_class="DataSubjectRight", ontology_property="hasExerciseProcedure", value="마이페이지에서 신청", source_type="policy_text"),
        ]
        result = OntologyMapper("poc1", controller_id="MoaCommerce").map(facts)
        graph = result.graph
        self.assertTrue(any(graph.triples((None, PIPA.hasPurpose, None))))
        self.assertTrue(any(graph.triples((None, PIPA.hasRetentionPeriod, None))))
        self.assertTrue(any(graph.triples((None, PIPA.hasRecipient, None))))
        self.assertTrue(any(graph.triples((None, PIPA.hasProcessor, None))))
        self.assertTrue(any(graph.triples((None, PIPA.hasDestructionMethod, None))))
        self.assertTrue(any(graph.triples((None, PIPA.hasRight, None))))
        self.assertTrue(any(graph.triples((None, PIPA.hasExerciseProcedure, None))))
        self.assertEqual("entrusted_task_text", result.system_metadata[0]["field"])
        self.assertTrue(any(graph.triples((None, PIPA.entrustedTaskText, None))))

    def test_f1_12_string_links_procedure_to_f1_11_right_node(self):
        facts = [
            fact(
                "F1-11-001",
                subject_id="user",
                activity_id=None,
                ontology_class="DataSubject",
                ontology_property="hasRight",
                value=["열람"],
                source_type="policy_text",
            ),
            fact(
                "F1-12-001",
                subject_id="열람",
                activity_id=None,
                ontology_class="DataSubjectRight",
                ontology_property="hasExerciseProcedure",
                value="마이페이지에서 신청",
                source_type="policy_text",
            ),
        ]
        graph = OntologyMapper("p1-r07", controller_id="MoaCommerce").map(facts).graph
        data_subject = next(graph.subjects(RDF.type, PIPA.DataSubject))
        right = next(graph.objects(data_subject, PIPA.hasRight))
        procedures = list(graph.objects(right, PIPA.hasExerciseProcedure))

        self.assertEqual(1, len(set(graph.subjects(RDF.type, PIPA.DataSubjectRight))))
        self.assertEqual(1, len(procedures))
        self.assertIn(
            Literal("마이페이지에서 신청"),
            set(graph.objects(procedures[0], PIPA.hasProcedureDescription)),
        )

    def test_f1_12_legacy_object_is_normalized_to_same_right_node(self):
        facts = [
            fact(
                "F1-11-001",
                subject_id="user",
                activity_id=None,
                ontology_class="DataSubject",
                ontology_property="hasRight",
                value=["열람"],
                source_type="policy_text",
            ),
            fact(
            "F1-12-001",
                subject_id="right",
                activity_id=None,
                ontology_class="DataSubjectRight",
                ontology_property="hasExerciseProcedure",
                value={"right": "열람", "procedure": "마이페이지에서 신청"},
                source_type="policy_text",
            ),
        ]
        graph = OntologyMapper("p1-r07-compat", controller_id="MoaCommerce").map(facts).graph
        data_subject = next(graph.subjects(RDF.type, PIPA.DataSubject))
        right = next(graph.objects(data_subject, PIPA.hasRight))
        self.assertEqual(1, len(set(graph.subjects(RDF.type, PIPA.DataSubjectRight))))
        self.assertTrue(any(graph.objects(right, PIPA.hasExerciseProcedure)))

    def test_poc3_form_to_fact_to_rdf_and_shacl(self):
        form = json.loads((BASE / "examples/SC-D01_form.json").read_text(encoding="utf-8"))
        facts = build_poc3_facts(form)
        result = OntologyMapper(
            "SC-D01",
            controller_id="CampusMate",
            controller_name="CampusMate",
        ).map(facts)

        collections = set(result.graph.subjects(RDF.type, PIPA.CollectionAndUse))
        entrusted = set(result.graph.subjects(RDF.type, PIPA.EntrustedProcessing))
        personal_information = set(result.graph.subjects(RDF.type, PIPA.PersonalInformation))
        self.assertEqual(3, len(collections))
        self.assertEqual(2, len(entrusted))
        self.assertEqual(6, len(personal_information))
        self.assertTrue(
            all(list(result.graph.objects(item, PIPA.designRationale)) for item in personal_information)
        )
        self.assertTrue(
            all(list(result.graph.objects(item, PIPA.isRequired)) for item in personal_information)
        )
        self.assertEqual(
            2,
            len([item for item in result.system_metadata if item["field"] == "entrusted_task_text"]),
        )
        self.assertEqual(
            2,
            len(list(result.graph.triples((None, PIPA.entrustedTaskText, None)))),
        )

        ontology = Graph().parse(BASE / "ontology/PIPA_Ontology_v1.0.ttl", format="turtle")
        shapes = Graph().parse(
            BASE / "ontology/PIPA_Process_Centered_SHACL_v1.0.ttl", format="turtle"
        )
        conforms, _, report = validate(
            data_graph=result.graph,
            ont_graph=ontology,
            shacl_graph=shapes,
            inference="rdfs",
            abort_on_first=False,
        )
        self.assertTrue(conforms, str(report))

    def test_same_item_name_is_separated_by_activity(self):
        facts = [
            fact(
                "F3-01-001",
                subject_id="activity-a",
                activity_id="activity-a",
                ontology_class="CollectionAndUse",
                ontology_property=None,
                value=None,
                source_type="structured_form",
            ),
            fact(
                "F3-05-001",
                subject_id="activity-a",
                activity_id="activity-a",
                ontology_class="CollectionAndUse",
                ontology_property="hasPersonalInformation",
                value=["이메일"],
                source_type="structured_form",
            ),
            fact(
                "F3-01-002",
                subject_id="activity-b",
                activity_id="activity-b",
                ontology_class="CollectionAndUse",
                ontology_property=None,
                value=None,
                source_type="structured_form",
            ),
            fact(
                "F3-05-002",
                subject_id="activity-b",
                activity_id="activity-b",
                ontology_class="CollectionAndUse",
                ontology_property="hasPersonalInformation",
                value=["이메일"],
                source_type="structured_form",
            ),
        ]
        graph = OntologyMapper("separation", controller_id="controller").map(facts).graph
        items = set(graph.subjects(PIPA.hasItemName, Literal("이메일")))
        self.assertEqual(2, len(items))
        scopes = {next(graph.objects(item, PIPA.inProcessingActivity)) for item in items}
        self.assertEqual(2, len(scopes))

    def test_unknown_and_absent_are_not_asserted(self):
        facts = [
            fact(
                "F3-01-001",
                subject_id="activity",
                activity_id="activity",
                ontology_class="CollectionAndUse",
                ontology_property=None,
                value=None,
                source_type="structured_form",
            ),
            fact(
                "F3-04-001",
                subject_id="activity",
                activity_id="activity",
                ontology_class="CollectionAndUse",
                ontology_property="hasPurpose",
                value=None,
                source_type="structured_form",
                state="unknown",
            ),
        ]
        result = OntologyMapper("state", controller_id="controller").map(facts)
        self.assertFalse(any(result.graph.triples((None, PIPA.hasPurpose, None))))
        self.assertFalse(result.trace[1]["emitted"])

    def test_poc2_actual_and_notice_information_and_time_are_separate(self):
        facts = [
            fact(
                "F2-01-001",
                subject_id="incident-b24",
                activity_id="incident-b24",
                ontology_class="DataBreachIncident",
                ontology_property=None,
                value=None,
                source_type="incident_record",
            ),
            fact(
                "F2-02-001",
                subject_id="incident-b24",
                activity_id="incident-b24",
                ontology_class="DataBreachIncident",
                ontology_property="affectsPersonalInformation",
                value=["이메일 주소"],
                source_type="incident_record",
            ),
            fact(
                "F2-03-001",
                subject_id="incident-b24",
                activity_id="incident-b24",
                ontology_class="DataBreachIncident",
                ontology_property="hasNotificationNotice",
                value={"notice_id": "notice-b24"},
                source_type="notification_notice",
            ),
            fact(
                "F2-04-001",
                subject_id="notice-b24",
                activity_id="incident-b24",
                ontology_class="NotificationNotice",
                ontology_property="mentionsPersonalInformation",
                value=["이메일 주소"],
                source_type="notification_notice",
            ),
            fact(
                "F2-05-001",
                subject_id="incident-b24",
                activity_id="incident-b24",
                ontology_class="DataBreachIncident",
                ontology_property="incidentDate",
                value="2026-09-05T09:00:00+09:00",
                source_type="incident_record",
            ),
            fact(
                "F2-06-001",
                subject_id="incident-b24",
                activity_id="incident-b24",
                ontology_class="DataBreachIncident",
                ontology_property="detectionDate",
                value="2026-09-05T09:10:00+09:00",
                source_type="incident_record",
            ),
            fact(
                "F2-07-001",
                subject_id="incident-b24",
                activity_id="incident-b24",
                ontology_class="DataBreachIncident",
                ontology_property="notificationDate",
                value="2026-09-05T12:00:00+09:00",
                source_type="notification_notice",
            ),
            fact(
                "F2-08-001",
                subject_id="notice-b24",
                activity_id="incident-b24",
                ontology_class="NotificationNotice",
                ontology_property=None,
                value="2026-09-05",
                source_type="notification_notice",
            ),
            fact(
                "F2-09-001",
                subject_id="notice-b24",
                activity_id="incident-b24",
                ontology_class="NotificationNotice",
                ontology_property="hasIncidentCircumstances",
                value="뉴스레터 수신자 이메일 주소가 일반 참조로 노출됨",
                source_type="notification_notice",
            ),
            fact(
                "F2-10-001",
                subject_id="incident-b24",
                activity_id="incident-b24",
                ontology_class="DataBreachIncident",
                ontology_property="hasResponseMeasure",
                value=[
                    {"role": "data_subject_guidance", "text": "피해 예방 안내"},
                    {"role": "controller_response", "text": "접근 차단"},
                    {"role": "remedy_procedure", "text": "문의 및 구제 절차"},
                    {"role": "post_incident_mitigation", "text": "재발 방지 조치"}
                ],
                source_type="notification_notice",
            ),
        ]
        result = OntologyMapper("poc2").map(facts)
        incident = next(result.graph.subjects(RDF.type, PIPA.DataBreachIncident))
        notice = next(result.graph.subjects(RDF.type, PIPA.NotificationNotice))
        actual = set(result.graph.objects(incident, PIPA.affectsPersonalInformation))
        mentioned = set(result.graph.objects(notice, PIPA.mentionsPersonalInformation))
        self.assertTrue(actual.isdisjoint(mentioned))
        self.assertTrue(any(result.graph.triples((incident, PIPA.incidentDate, None))))
        self.assertTrue(any(result.graph.triples((incident, PIPA.detectionDate, None))))
        self.assertTrue(any(result.graph.triples((incident, PIPA.notificationDate, None))))
        self.assertTrue(any(result.graph.triples((notice, PIPA.hasIncidentCircumstances, None))))
        self.assertEqual("notice_incident_time", result.system_metadata[0]["field"])
        roles = {
            item["value"]
            for item in result.system_metadata
            if item["field"] == "measure_role"
        }
        self.assertEqual(
            {
                "data_subject_guidance",
                "controller_response",
                "remedy_procedure",
                "post_incident_mitigation",
            },
            roles,
        )
        self.assertTrue(any(result.graph.triples((notice, PIPA.noticeIncidentTime, None))))
        graph_roles = {
            str(role)
            for measure in result.graph.objects(incident, PIPA.hasResponseMeasure)
            for role in result.graph.objects(measure, PIPA.measureRole)
        }
        self.assertEqual(roles, graph_roles)

    def test_p2_r01_v1_contract_uses_f2_01_f2_02_f2_03_only(self):
        facts = [
            fact(
                "F2-01-001",
                subject_id="incident",
                activity_id="incident",
                ontology_class="DataBreachIncident",
                ontology_property=None,
                value=None,
                source_type="incident_record",
            ),
            fact(
                "F2-02-001",
                subject_id="incident",
                activity_id="incident",
                ontology_class="DataBreachIncident",
                ontology_property="affectsPersonalInformation",
                value=["이메일"],
                source_type="incident_record",
            ),
            fact(
                "F2-03-001",
                subject_id="incident",
                activity_id="incident",
                ontology_class="DataBreachIncident",
                ontology_property="hasNotificationNotice",
                value={"notice_id": "notice"},
                source_type="notification_notice",
            ),
        ]
        graph = OntologyMapper("p2-r01-v1").map(facts).graph
        incident = next(graph.subjects(RDF.type, PIPA.DataBreachIncident))
        self.assertTrue(any(graph.objects(incident, PIPA.affectsPersonalInformation)))
        self.assertTrue(any(graph.objects(incident, PIPA.hasNotificationNotice)))
        self.assertFalse(
            any(graph.triples((incident, PIPA.triggersNotificationObligation, None)))
        )

    def test_all_fact_specs_reference_frozen_ontology_and_mapper_handlers(self):
        ontology = Graph().parse(BASE / "ontology/PIPA_Ontology_v1.0.ttl", format="turtle")
        classes = set(ontology.subjects(RDF.type, OWL.Class))
        properties = set(ontology.subjects(RDF.type, OWL.ObjectProperty))
        properties.update(ontology.subjects(RDF.type, OWL.DatatypeProperty))
        properties.update(ontology.subjects(RDF.type, OWL.AnnotationProperty))
        self.assertEqual(50, len(FACT_SPECS))  # 동결 35 + v1.1 10 + 신규 5
        mapper = OntologyMapper("contract", controller_id="controller")
        for fact_type, spec in FACT_SPECS.items():
            self.assertIn(PIPA[spec.subject_class], classes, fact_type)
            if spec.ontology_property:
                self.assertIn(PIPA[spec.ontology_property], properties, fact_type)
            self.assertTrue(
                callable(getattr(mapper, f"_map_{spec.mapping_kind}", None)), fact_type
            )

    def test_activity_scoped_fact_requires_activity_id(self):
        bad = fact(
            "F3-01-001",
            subject_id="activity",
            activity_id=None,
            ontology_class="CollectionAndUse",
            ontology_property=None,
            value=None,
            source_type="structured_form",
        )
        with self.assertRaises(FactValidationError):
            OntologyMapper("missing-activity", controller_id="controller").map([bad])

    def test_empty_evidence_is_rejected(self):
        bad = fact(
            "F3-01-001",
            subject_id="activity",
            activity_id="activity",
            ontology_class="CollectionAndUse",
            ontology_property=None,
            value=None,
            source_type="structured_form",
        )
        bad["evidence"] = []
        with self.assertRaises(FactValidationError):
            OntologyMapper("missing-evidence", controller_id="controller").map([bad])

    def test_response_measure_role_enum_and_duplicates_are_rejected(self):
        invalid = fact(
            "F2-10-001",
            subject_id="incident",
            activity_id="incident",
            ontology_class="DataBreachIncident",
            ontology_property="hasResponseMeasure",
            value=[{"role": "invalid_role", "text": "조치"}],
            source_type="notification_notice",
        )
        with self.assertRaises(FactValidationError):
            OntologyMapper("invalid-role").map([invalid])

        duplicate = dict(invalid)
        duplicate["value"] = [
            {"role": "controller_response", "text": "조치 1"},
            {"role": "controller_response", "text": "조치 2"},
        ]
        with self.assertRaises(FactValidationError):
            OntologyMapper("duplicate-role").map([duplicate])

    def test_poc2_incident_and_notice_source_types_are_enforced(self):
        wrong_actual = fact(
            "F2-02-001",
            subject_id="incident",
            activity_id="incident",
            ontology_class="DataBreachIncident",
            ontology_property="affectsPersonalInformation",
            value=["이메일"],
            source_type="notification_notice",
        )
        wrong_notice = fact(
            "F2-04-001",
            subject_id="notice",
            activity_id="incident",
            ontology_class="NotificationNotice",
            ontology_property="mentionsPersonalInformation",
            value=["이메일"],
            source_type="incident_record",
        )
        for bad in (wrong_actual, wrong_notice):
            with self.assertRaises(FactValidationError):
                OntologyMapper("wrong-source").map([bad])

    def test_destruction_is_not_inferred_across_activities(self):
        facts = [
            fact(
                "F3-10-001",
                subject_id="activity-a-retention",
                activity_id="activity-a",
                ontology_class="Retention",
                ontology_property="hasRetentionEndCondition",
                value="회원 탈퇴",
                source_type="structured_form",
            ),
            fact(
                "F1-08-001",
                subject_id="activity-b-destruction",
                activity_id="activity-b-destruction",
                ontology_class="Destruction",
                ontology_property="hasDestructionMethod",
                value="안전 삭제",
                source_type="policy_text",
            ),
        ]
        graph = OntologyMapper("no-cross-link", controller_id="controller").map(facts).graph
        self.assertFalse(any(graph.triples((None, PIPA.triggersDestruction, None))))

    def test_legacy_namespace_is_rejected(self):
        bad = fact(
            "F3-01-001",
            subject_id="activity",
            activity_id="activity",
            ontology_class="https://example.org/pipa-dpv#CollectionAndUse",
            ontology_property=None,
            value=None,
            source_type="structured_form",
        )
        with self.assertRaises(FactValidationError):
            OntologyMapper("bad", controller_id="controller").map([bad])


if __name__ == "__main__":
    unittest.main()
