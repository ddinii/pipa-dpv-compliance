from __future__ import annotations

import json
import unittest
from pathlib import Path

from pyshacl import validate
from rdflib import Graph, Literal, Namespace, RDF

from app.builders import build_poc3_facts
from app.mapping import FactValidationError, OntologyMapper


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
            fact("F1-12-001", subject_id="right", activity_id=None, ontology_class="DataSubjectRight", ontology_property="hasExerciseProcedure", value={"right": "열람", "procedure": "마이페이지에서 신청"}, source_type="policy_text"),
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
        # entrustedTaskText는 Ontology Property가 아니라 Rule 입력 보조 필드지만
        # (Fact Dictionary 8장), frozen ontology에 AnnotationProperty로 선언되어
        # 있고 Rule Engine이 그래프에서 직접 읽는다. system_metadata에만 담으면
        # P1-R06과 P3-R11이 위탁업무 누락으로 보아 항상 RED가 된다.
        self.assertTrue(any(graph.triples((None, PIPA.entrustedTaskText, None))))

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
        # 위와 같은 이유. 그래프에 실려야 P3-R11이 GREEN에 도달할 수 있다.
        self.assertTrue(any(result.graph.triples((None, PIPA.entrustedTaskText, None))))

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

        # unknown은 "값을 확정할 수 없다"이지 "기재가 없다"가 아니다. 트리플을 아예
        # 만들지 않으면 Rule Engine이 결측(RED)과 구별하지 못해, Rule Matrix의
        # AMBER 분기("언급은 있으나 모호")에 도달할 수 없다. 그래서 UNKNOWN 표식을
        # 실어 보낸다. 엔진의 _nonempty_values가 이 표식을 빈 값으로 취급한다.
        purposes = list(result.graph.triples((None, PIPA.hasPurpose, None)))
        self.assertTrue(purposes)
        self.assertTrue(result.trace[1]["emitted"])
        self.assertTrue(result.trace[1]["unknown_marker"])

        descriptions = {
            str(value)
            for _, _, value in result.graph.triples(
                (None, PIPA.hasPurposeDescription, None)
            )
        }
        self.assertEqual({"UNKNOWN"}, descriptions)

    def test_absent_facts_produce_no_triples(self):
        """absent는 명시적 부재다. unknown과 달리 아무 트리플도 만들지 않는다."""
        facts = [
            fact(
                "F3-04-001",
                subject_id="activity",
                activity_id="activity",
                ontology_class="CollectionAndUse",
                ontology_property="hasPurpose",
                value=None,
                source_type="structured_form",
                state="absent",
            ),
        ]
        result = OntologyMapper("absent", controller_id="controller").map(facts)
        self.assertFalse(any(result.graph.triples((None, PIPA.hasPurpose, None))))
        self.assertFalse(result.trace[0]["emitted"])

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
        # noticeIncidentTime이 그래프에 없으면 P2-R03이 통지문 기재시점을 확인하지
        # 못한다. 실제 incidentDate(F2-05)와는 아래 단언대로 끝까지 분리된다.
        self.assertTrue(any(result.graph.triples((notice, PIPA.noticeIncidentTime, None))))
        self.assertFalse(any(result.graph.triples((None, PIPA.measureRole, None))))

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


class FrozenScenarioTests(unittest.TestCase):
    """Fact -> RDF -> Rule Engine이 Freeze 시나리오 기대값을 재현하는지 본다.

    매핑 단위 테스트만으로는 "그래프는 만들어졌는데 Rule이 읽지 못하는" 결함을
    잡을 수 없다. entrustedTaskText 누락이 정확히 그런 경우였다.
    """

    @classmethod
    def setUpClass(cls):
        from app.rules.engine import P0RuleEngine

        cls.engine = P0RuleEngine()
        cls.form = json.loads(
            (BASE / "examples" / "SC-D01_form.json").read_text(encoding="utf-8")
        )

    def _evaluate(self, form, poc="poc3"):
        facts = build_poc3_facts(form)
        controller = form.get("controller", {})
        result = OntologyMapper(
            form.get("analysis_id", "test"),
            controller_id=controller.get("controller_id", "controller"),
            controller_name=controller.get("name"),
        ).map(facts)
        return {
            item.rule_id: item.status.value
            for item in self.engine.evaluate_graph(result.graph, poc=poc)
        }

    def test_sc_d01_form_reproduces_the_frozen_eight_green(self):
        """SC-D01 Freeze 기대값은 PoC3 8개 Rule 전부 GREEN이다."""
        statuses = self._evaluate(self.form)
        self.assertEqual({"GREEN"}, set(statuses.values()), statuses)

    def test_confirmed_absence_gives_na_but_an_empty_list_gives_amber(self):
        """단순 결측은 N/A가 아니다. 없음이 확인된 경우에만 N/A다."""
        undecided = json.loads(json.dumps(self.form))
        undecided["entrusted_processings"] = []
        self.assertEqual("AMBER", self._evaluate(undecided)["P3-R11"])

        confirmed = json.loads(json.dumps(undecided))
        confirmed["entrusted_processing_state"] = "confirmed_false"
        self.assertEqual("N/A", self._evaluate(confirmed)["P3-R11"])

    def test_unknown_value_is_amber_not_red(self):
        """Rule Matrix: 값이 UNKNOWN/모호하면 AMBER, 미확인이면 RED."""
        from app.rules.engine import P0RuleEngine

        def destruction_fact(state, value):
            return fact(
                "F1-08-001",
                subject_id="destroy",
                activity_id="destroy",
                ontology_class="Destruction",
                ontology_property="hasDestructionMethod",
                value=value,
                source_type="policy_text",
                state=state,
            )

        engine = P0RuleEngine()
        vague = OntologyMapper("vague", controller_id="c").map(
            [destruction_fact("unknown", None)]
        )
        self.assertEqual("AMBER", engine.evaluate_rule(vague.graph, "P1-R04").status.value)

        concrete = OntologyMapper("ok", controller_id="c").map(
            [destruction_fact("confirmed", "복구 불가능하게 삭제")]
        )
        self.assertEqual("GREEN", engine.evaluate_rule(concrete.graph, "P1-R04").status.value)

    def test_entrusted_task_text_reaches_the_graph(self):
        """system_metadata에만 담으면 P1-R06/P3-R11이 항상 RED가 된다."""
        from app.rules.engine import P0RuleEngine

        facts = [
            fact(
                "F1-09-001",
                subject_id="entrust",
                activity_id="entrust",
                ontology_class="EntrustedProcessing",
                ontology_property="hasProcessor",
                value="빠른택배 주식회사",
                source_type="policy_text",
            ),
            fact(
                "F1-10-001",
                subject_id="entrust",
                activity_id="entrust",
                ontology_class="EntrustedProcessing",
                ontology_property=None,
                value="상품 배송",
                source_type="policy_text",
            ),
        ]
        result = OntologyMapper("entrust", controller_id="c").map(facts)
        engine = P0RuleEngine()
        self.assertEqual("GREEN", engine.evaluate_rule(result.graph, "P1-R06").status.value)
        self.assertEqual("GREEN", engine.evaluate_rule(result.graph, "P3-R11").status.value)
        # 추적용 metadata도 함께 남아야 한다
        self.assertEqual("entrusted_task_text", result.system_metadata[0]["field"])
