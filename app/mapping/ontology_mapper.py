"""Deterministic Fact JSON to PIPA RDF mapper.

The mapper follows the process-centered model. Values of object properties are
minted as RDF individuals instead of being attached as string literals.
Unknown/absent Facts remain in the normalized Fact list and are not asserted as
confirmed RDF triples.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any
from urllib.parse import quote

from rdflib import Graph, Literal, Namespace, RDF, RDFS, URIRef, XSD

from .fact_schema import FactValidationError, local_name, validate_facts
from .mapping_registry import FACT_SPECS
from .presence_metadata import validate_system_metadata


PIPA = Namespace("https://w3id.org/pipa-compliance/ontology#")

RESPONSE_MEASURE_ROLES = {
    "data_subject_guidance",
    "controller_response",
    "remedy_procedure",
    "post_incident_mitigation",
}

PROCESSING_CLASSES = {
    "ProcessingActivity",
    "PersonalInformationProcessing",
    "CollectionAndUse",
    "ThirdPartyProvision",
    "Retention",
    "Destruction",
    "EntrustedProcessing",
    "CrossBorderTransfer",
}


@dataclass
class MappingResult:
    graph: Graph
    facts: list[dict[str, Any]]
    system_metadata: list[dict[str, Any]]
    trace: list[dict[str, Any]]

    def serialize(self, destination: str | None = None) -> str | None:
        return self.graph.serialize(destination=destination, format="turtle")


class OntologyMapper:
    def __init__(
        self,
        analysis_id: str,
        *,
        controller_id: str | None = None,
        controller_name: str | None = None,
        instance_base: str = "https://example.org/pipa-instance/",
    ) -> None:
        if not analysis_id.strip():
            raise ValueError("analysis_id는 비어 있을 수 없음")
        encoded_analysis = quote(analysis_id.strip(), safe="-._~")
        self.instance = Namespace(f"{instance_base.rstrip('/')}/{encoded_analysis}/")
        self.controller_id = controller_id
        self.controller_name = controller_name or controller_id
        self.graph = Graph()
        self.graph.bind("pipa", PIPA)
        self.graph.bind("inst", self.instance)
        self.system_metadata: list[dict[str, Any]] = []
        self.trace: list[dict[str, Any]] = []
        self._end_conditions: list[URIRef] = []
        self._destructions: list[URIRef] = []

    def map(
        self,
        raw_facts: list[dict[str, Any]],
        *,
        system_metadata: list[dict[str, Any]] | None = None,
    ) -> MappingResult:
        facts = validate_facts(raw_facts)
        self.system_metadata.extend(validate_system_metadata(system_metadata))
        for fact in facts:
            self._assert_mapping_contract(fact)
            trace_item = {
                "fact_id": fact["fact_id"],
                "fact_type": fact["fact_type"],
                "value_state": fact["value_state"],
                "source_type": fact["source_type"],
                "evidence": fact["evidence"],
                "emitted": False,
            }
            self.trace.append(trace_item)
            if fact["value_state"] != "confirmed":
                continue
            self._map_confirmed(fact)
            trace_item["emitted"] = True

        return MappingResult(
            graph=self.graph,
            facts=facts,
            system_metadata=self.system_metadata,
            trace=self.trace,
        )

    def _assert_mapping_contract(self, fact: dict[str, Any]) -> None:
        spec = FACT_SPECS.get(fact["fact_type"])
        if spec is None:
            raise FactValidationError(f"매핑 정의가 없는 Fact: {fact['fact_type']}")

        actual_property = local_name(fact["ontology_property"])
        if actual_property != spec.ontology_property:
            raise FactValidationError(
                f"{fact['fact_id']}: ontology_property={actual_property!r}, "
                f"Freeze 기대값={spec.ontology_property!r}"
            )

        actual_class = local_name(fact["ontology_class"])
        expected = spec.subject_class
        generic_activity_match = (
            expected in {"ProcessingActivity", "PersonalInformationProcessing"}
            and actual_class in PROCESSING_CLASSES
        )
        if actual_class != expected and not generic_activity_match:
            raise FactValidationError(
                f"{fact['fact_id']}: ontology_class={actual_class!r}, "
                f"Freeze 기대값={expected!r}"
            )

    def _map_confirmed(self, fact: dict[str, Any]) -> None:
        kind = FACT_SPECS[fact["fact_type"]].mapping_kind
        handler = getattr(self, f"_map_{kind}")
        handler(fact)

    def _uri(self, identifier: str) -> URIRef:
        return URIRef(str(self.instance) + quote(str(identifier), safe="-._~"))

    def _derived_uri(self, kind: str, seed: str) -> URIRef:
        digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:12]
        return self._uri(f"{kind}-{digest}")

    def _activity_id(self, fact: dict[str, Any]) -> str:
        identifier = fact.get("activity_id") or fact["subject_id"]
        if not identifier:
            raise FactValidationError(f"{fact['fact_id']}: activity_id가 필요함")
        return identifier

    def _ensure_controller(self) -> URIRef:
        if not self.controller_id:
            raise FactValidationError(
                "ProcessingActivity 매핑에는 controller_id가 필요함"
            )
        node = self._uri(self.controller_id)
        self.graph.add((node, RDF.type, PIPA.PersonalInformationController))
        if self.controller_name:
            self.graph.add((node, PIPA.hasName, Literal(self.controller_name)))
        return node

    def _ensure_activity(self, identifier: str, class_name: str) -> URIRef:
        if class_name not in PROCESSING_CLASSES:
            raise FactValidationError(f"처리행위 Class가 아님: {class_name}")
        node = self._uri(identifier)
        self.graph.add((node, RDF.type, PIPA[class_name]))
        controller = self._ensure_controller()
        self.graph.add((node, PIPA.performedByController, controller))
        self.graph.add((controller, PIPA.hasProcessingActivity, node))
        return node

    def _subject_activity(self, fact: dict[str, Any]) -> URIRef:
        return self._ensure_activity(
            self._activity_id(fact), local_name(fact["ontology_class"]) or "ProcessingActivity"
        )

    def _add_label(self, node: URIRef, value: Any) -> None:
        self.graph.add((node, RDFS.label, Literal(str(value), lang="ko")))

    @staticmethod
    def _as_items(value: Any) -> list[Any]:
        return value if isinstance(value, list) else [value]

    @staticmethod
    def _object_name(value: Any, *keys: str) -> str:
        if isinstance(value, dict):
            for key in keys:
                if value.get(key) not in (None, ""):
                    return str(value[key])
        if value not in (None, "") and not isinstance(value, dict):
            return str(value)
        raise FactValidationError(f"값에서 이름을 찾을 수 없음: {value!r}")

    def _ensure_retention(self, activity: URIRef) -> URIRef:
        node = self._derived_uri("retention", str(activity))
        self._ensure_activity(node.rsplit("/", 1)[-1], "Retention")
        self.graph.add((activity, PIPA.hasRetention, node))
        return node

    def _ensure_end_condition(self, activity: URIRef, description: str) -> URIRef:
        retention = self._ensure_retention(activity)
        node = self._derived_uri("retention-end", f"{activity}|{description}")
        self.graph.add((node, RDF.type, PIPA.RetentionEndCondition))
        self.graph.add((node, PIPA.hasEndConditionDescription, Literal(description)))
        self.graph.add((retention, PIPA.hasRetentionEndCondition, node))
        if node not in self._end_conditions:
            self._end_conditions.append(node)
        return node

    def _ensure_personal_information(
        self, owner: URIRef, item: Any, relation: URIRef, *, activity: URIRef | None
    ) -> URIRef:
        name = self._object_name(item, "item_name", "name", "value")
        node = self._derived_uri("pi", f"{owner}|{name}")
        self.graph.add((node, RDF.type, PIPA.PersonalInformation))
        self.graph.add((node, PIPA.hasItemName, Literal(name)))
        self.graph.add((owner, relation, node))
        if activity is not None:
            self.graph.add((node, PIPA.inProcessingActivity, activity))
        return node

    def _item_node(self, fact: dict[str, Any]) -> tuple[URIRef, dict[str, Any]]:
        value = fact["value"]
        if not isinstance(value, dict):
            raise FactValidationError(
                f"{fact['fact_id']}: 항목별 Fact value는 객체여야 함"
            )
        item_name = self._object_name(value, "item_name", "name")
        activity = self._ensure_activity(self._activity_id(fact), "CollectionAndUse")
        item = self._ensure_personal_information(
            activity, item_name, PIPA.hasPersonalInformation, activity=activity
        )
        return item, value

    # Generic/class mappings -------------------------------------------------

    def _map_class_assertion(self, fact: dict[str, Any]) -> None:
        class_name = local_name(fact["ontology_class"])
        identifier = self._activity_id(fact) if class_name in PROCESSING_CLASSES else fact["subject_id"]
        if class_name in PROCESSING_CLASSES:
            self._ensure_activity(identifier, class_name)
        else:
            self.graph.add((self._uri(identifier), RDF.type, PIPA[class_name]))

    def _map_purpose(self, fact: dict[str, Any]) -> None:
        activity = self._subject_activity(fact)
        description = self._object_name(fact["value"], "description", "purpose")
        purpose = self._derived_uri("purpose", f"{activity}|{description}")
        self.graph.add((purpose, RDF.type, PIPA.ProcessingPurpose))
        self.graph.add((purpose, PIPA.hasPurposeDescription, Literal(description)))
        self.graph.add((activity, PIPA.hasPurpose, purpose))

    def _map_personal_information(self, fact: dict[str, Any]) -> None:
        activity = self._subject_activity(fact)
        for item in self._as_items(fact["value"]):
            self._ensure_personal_information(
                activity, item, PIPA.hasPersonalInformation, activity=activity
            )

    def _map_retention_period(self, fact: dict[str, Any]) -> None:
        activity = self._subject_activity(fact)
        duration = self._object_name(fact["value"], "duration", "period")
        retention = self._ensure_retention(activity)
        period = self._derived_uri("retention-period", f"{activity}|{duration}")
        self.graph.add((period, RDF.type, PIPA.RetentionPeriod))
        self.graph.add((period, PIPA.hasDurationValue, Literal(duration)))
        self.graph.add((retention, PIPA.hasRetentionPeriod, period))

    def _map_retention_end(self, fact: dict[str, Any]) -> None:
        if local_name(fact["ontology_class"]) == "Retention":
            activity = self._ensure_activity(self._activity_id(fact), "CollectionAndUse")
        else:
            activity = self._subject_activity(fact)
        description = self._object_name(fact["value"], "end_condition", "condition")
        self._ensure_end_condition(activity, description)

    def _map_retention_object(self, fact: dict[str, Any]) -> None:
        activity = self._subject_activity(fact)
        value = fact["value"]
        if not isinstance(value, dict):
            raise FactValidationError(f"{fact['fact_id']}: retention value는 객체여야 함")
        period_value = value.get("period") or value.get("duration")
        end_value = value.get("end_condition") or value.get("condition")
        if period_value:
            retention = self._ensure_retention(activity)
            period = self._derived_uri("retention-period", f"{activity}|{period_value}")
            self.graph.add((period, RDF.type, PIPA.RetentionPeriod))
            self.graph.add((period, PIPA.hasDurationValue, Literal(str(period_value))))
            self.graph.add((retention, PIPA.hasRetentionPeriod, period))
        if end_value:
            self._ensure_end_condition(activity, str(end_value))

    def _map_recipient(self, fact: dict[str, Any]) -> None:
        activity = self._subject_activity(fact)
        name = self._object_name(fact["value"], "name", "recipient")
        recipient = self._derived_uri("third-party", name)
        self.graph.add((recipient, RDF.type, PIPA.ThirdParty))
        self.graph.add((recipient, PIPA.hasName, Literal(name)))
        self.graph.add((activity, PIPA.hasRecipient, recipient))

    def _map_processor(self, fact: dict[str, Any]) -> None:
        activity = self._subject_activity(fact)
        name = self._object_name(fact["value"], "name", "processor")
        processor = self._derived_uri("processor", name)
        self.graph.add((processor, RDF.type, PIPA.EntrustedProcessor))
        self.graph.add((processor, PIPA.hasName, Literal(name)))
        self.graph.add((activity, PIPA.hasProcessor, processor))

    def _map_destruction_method(self, fact: dict[str, Any]) -> None:
        destruction = self._subject_activity(fact)
        method = self._object_name(fact["value"], "method", "description")
        self.graph.add((destruction, PIPA.hasDestructionMethod, Literal(method)))
        if destruction not in self._destructions:
            self._destructions.append(destruction)

    def _map_rights(self, fact: dict[str, Any]) -> None:
        subject = self._uri(fact["subject_id"])
        self.graph.add((subject, RDF.type, PIPA.DataSubject))
        for right_value in self._as_items(fact["value"]):
            name = self._object_name(right_value, "name", "right")
            right = self._derived_uri("right", name)
            self.graph.add((right, RDF.type, PIPA.DataSubjectRight))
            self._add_label(right, name)
            self.graph.add((subject, PIPA.hasRight, right))

    def _map_right_procedure(self, fact: dict[str, Any]) -> None:
        # Canonical F1-12 is a string whose subject_id is the F1-11 right name.
        # The existing PoC1 extractor emits {right, procedure}; normalize both
        # forms here.  In either case F1-11 and F1-12 mint the same right URI.
        value = fact["value"]
        if isinstance(value, dict):
            right_name = self._object_name(value, "right", "right_name")
            description = self._object_name(value, "procedure", "description")
        else:
            right_name = fact["subject_id"]
            description = str(value).strip()
        right = self._derived_uri("right", right_name)
        self.graph.add((right, RDF.type, PIPA.DataSubjectRight))
        self._add_label(right, right_name)
        procedure = self._derived_uri("rights-procedure", f"{right}|{description}")
        self.graph.add((procedure, RDF.type, PIPA.RightsExerciseProcedure))
        self.graph.add((procedure, PIPA.hasProcedureDescription, Literal(description)))
        self.graph.add((right, PIPA.hasExerciseProcedure, procedure))

    # v1.1 국외 이전 기재 (제28조의8 제2항) -----------------------------------

    def _map_destination_country(self, fact: dict[str, Any]) -> None:
        activity = self._subject_activity(fact)
        for item in self._as_items(fact["value"]):
            name = self._object_name(item, "name", "country")
            country = self._derived_uri("country", name)
            self.graph.add((country, RDF.type, PIPA.DestinationCountry))
            self._add_label(country, name)
            self.graph.add((activity, PIPA.hasDestinationCountry, country))

    def _transfer_recipient_node(self, activity_id: str) -> URIRef:
        """국외 이전 처리행위마다 이전받는 자 노드 하나. F1-16(이름)과 F1-17(연락처)이 만난다."""
        activity = self._ensure_activity(activity_id, "CrossBorderTransfer")
        recipient = self._derived_uri("overseas-recipient", str(activity))
        self.graph.add((recipient, RDF.type, PIPA.OverseasRecipient))
        self.graph.add((activity, PIPA.hasTransferRecipient, recipient))
        return recipient

    def _map_transfer_recipient(self, fact: dict[str, Any]) -> None:
        recipient = self._transfer_recipient_node(self._activity_id(fact))
        name = self._object_name(fact["value"], "name", "recipient")
        self.graph.add((recipient, PIPA.hasName, Literal(name)))

    def _map_recipient_contact(self, fact: dict[str, Any]) -> None:
        recipient = self._transfer_recipient_node(self._activity_id(fact))
        for contact in self._as_items(fact["value"]):
            self.graph.add((recipient, PIPA.hasContact, Literal(self._object_name(contact, "contact"))))

    def _map_activity_literal(self, fact: dict[str, Any]) -> None:
        """처리행위에 직접 붙는 문장 값 (F1-18 이전 시기·방법, F1-19 거부 방법·절차·효과)."""
        activity = self._subject_activity(fact)
        text = self._object_name(fact["value"], "description", "text")
        self.graph.add((activity, PIPA[fact["ontology_property"]], Literal(text)))

    # v1.1 개인정보 보호책임자 기재 (제30조 제1항 제6호) ------------------------

    def _privacy_officer_node(self) -> URIRef:
        controller = self._ensure_controller()
        officer = self._derived_uri("privacy-officer", str(controller))
        self.graph.add((officer, RDF.type, PIPA.PrivacyOfficer))
        self.graph.add((controller, PIPA.hasPrivacyOfficer, officer))
        return officer

    def _map_privacy_officer(self, fact: dict[str, Any]) -> None:
        """value = {name, department}. 성명(자연인)은 hasPersonName, 부서는 hasDepartmentName.

        성명은 화면 출력 시 마스킹 대상이라 회사 명칭(hasName)과 다른 속성을 쓴다.
        """
        officer = self._privacy_officer_node()
        value = fact["value"]
        if value.get("name") not in (None, ""):
            self.graph.add((officer, PIPA.hasPersonName, Literal(str(value["name"]))))
        if value.get("department") not in (None, ""):
            self.graph.add((officer, PIPA.hasDepartmentName, Literal(str(value["department"]))))

    def _map_officer_contact(self, fact: dict[str, Any]) -> None:
        officer = self._privacy_officer_node()
        for contact in self._as_items(fact["value"]):
            self.graph.add((officer, PIPA.hasContact, Literal(self._object_name(contact, "contact"))))

    # v1.2 문서 단위 자동수집장치 점검
    def _map_controller_literal(self, fact: dict[str, Any]) -> None:
        controller = self._ensure_controller()
        predicate = PIPA[local_name(fact["ontology_property"])]
        self.graph.add((controller, predicate, Literal(str(fact["value"]))))

    def _map_notice_literal(self, fact: dict[str, Any]) -> None:
        notice = self._notice(fact)
        predicate = PIPA[local_name(fact["ontology_property"])]
        self.graph.add((notice, predicate, Literal(str(fact["value"]))))

    # PoC2 mappings ----------------------------------------------------------

    def _incident(self, fact: dict[str, Any]) -> URIRef:
        identifier = fact.get("activity_id") or fact["subject_id"]
        node = self._uri(identifier)
        self.graph.add((node, RDF.type, PIPA.DataBreachIncident))
        return node

    def _notice(self, fact: dict[str, Any]) -> URIRef:
        node = self._uri(fact["subject_id"])
        self.graph.add((node, RDF.type, PIPA.NotificationNotice))
        return node

    def _map_incident_information(self, fact: dict[str, Any]) -> None:
        incident = self._incident(fact)
        for item in self._as_items(fact["value"]):
            self._ensure_personal_information(
                incident, item, PIPA.affectsPersonalInformation, activity=None
            )

    def _map_notification_notice(self, fact: dict[str, Any]) -> None:
        incident = self._incident(fact)
        value = fact["value"]
        if isinstance(value, dict):
            notice_id = value.get("notice_id") or value.get("id")
        elif isinstance(value, str):
            notice_id = value
        else:
            notice_id = None
        notice_id = notice_id or f"{fact.get('activity_id') or fact['subject_id']}-notice"
        notice = self._uri(str(notice_id))
        self.graph.add((notice, RDF.type, PIPA.NotificationNotice))
        self.graph.add((incident, PIPA.hasNotificationNotice, notice))

    def _map_notice_information(self, fact: dict[str, Any]) -> None:
        notice = self._notice(fact)
        for item in self._as_items(fact["value"]):
            self._ensure_personal_information(
                notice, item, PIPA.mentionsPersonalInformation, activity=None
            )

    def _map_datetime(self, fact: dict[str, Any]) -> None:
        subject = self._incident(fact)
        predicate = PIPA[local_name(fact["ontology_property"])]
        self.graph.add((subject, predicate, Literal(str(fact["value"]), datatype=XSD.dateTime)))

    def _map_string_literal(self, fact: dict[str, Any]) -> None:
        subject_class = local_name(fact["ontology_class"])
        if subject_class == "NotificationNotice":
            subject = self._notice(fact)
        else:
            subject = self._uri(fact["subject_id"])
            self.graph.add((subject, RDF.type, PIPA[subject_class]))
        predicate = PIPA[local_name(fact["ontology_property"])]
        self.graph.add((subject, predicate, Literal(str(fact["value"]))))

    def _map_response_measures(self, fact: dict[str, Any]) -> None:
        incident = self._incident(fact)
        seen_roles: set[str] = set()
        for index, raw in enumerate(self._as_items(fact["value"])):
            if not isinstance(raw, dict):
                raise FactValidationError(
                    f"{fact['fact_id']}: response measure는 객체여야 함"
                )
            role = raw.get("measure_role") or raw.get("role")
            text = raw.get("text") or raw.get("description")
            if not role or not text:
                raise FactValidationError(
                    f"{fact['fact_id']}: response measure에 role과 text가 필요함"
                )
            if role not in RESPONSE_MEASURE_ROLES:
                raise FactValidationError(
                    f"{fact['fact_id']}: 지원하지 않는 measure_role={role!r}"
                )
            if role in seen_roles:
                raise FactValidationError(
                    f"{fact['fact_id']}: 중복 measure_role={role!r}"
                )
            seen_roles.add(role)
            measure_id = raw.get("measure_id") or f"{fact['fact_id']}-measure-{index + 1}"
            measure = self._uri(str(measure_id))
            self.graph.add((measure, RDF.type, PIPA.IncidentResponseMeasure))
            self.graph.add((incident, PIPA.hasResponseMeasure, measure))
            # P2-R08 reads the frozen measureRole annotation from each
            # IncidentResponseMeasure.  Keep the same value in system_metadata
            # as well so non-RDF consumers retain the original Fact payload.
            self.graph.add((measure, PIPA.measureRole, Literal(str(role))))
            self.system_metadata.append(
                {
                    "fact_id": fact["fact_id"],
                    "field": "measure_role",
                    "subject_id": str(measure_id),
                    "value": role,
                    "content": text,
                    "source_type": fact["source_type"],
                    "evidence": fact["evidence"],
                }
            )

    # PoC3 mappings ----------------------------------------------------------

    def _map_legal_basis(self, fact: dict[str, Any]) -> None:
        activity = self._subject_activity(fact)
        value = fact["value"]
        basis_type = self._object_name(value, "type", "basis", "name")
        is_consent = basis_type.lower() == "consent" or "동의" in basis_type
        class_name = "Consent" if is_consent else "LegalBasis"
        basis = self._derived_uri("legal-basis", f"{activity}|{basis_type}")
        self.graph.add((basis, RDF.type, PIPA[class_name]))
        self._add_label(basis, basis_type)
        self.graph.add((activity, PIPA.hasLegalBasis, basis))

    def _ensure_consent_request(self, activity: URIRef) -> URIRef:
        request = self._derived_uri("consent-request", str(activity))
        self.graph.add((request, RDF.type, PIPA.ConsentRequest))
        self.graph.add((activity, PIPA.hasConsentRequest, request))
        return request

    def _map_consent_request(self, fact: dict[str, Any]) -> None:
        activity = self._subject_activity(fact)
        self._ensure_consent_request(activity)

    def _map_item_required(self, fact: dict[str, Any]) -> None:
        item, value = self._item_node(fact)
        required = value.get("is_required")
        if not isinstance(required, bool):
            raise FactValidationError(f"{fact['fact_id']}: is_required는 boolean이어야 함")
        self.graph.add((item, PIPA.isRequired, Literal(required, datatype=XSD.boolean)))

    def _map_item_rationale(self, fact: dict[str, Any]) -> None:
        item, value = self._item_node(fact)
        rationale = value.get("design_rationale") or value.get("rationale")
        if not rationale:
            raise FactValidationError(f"{fact['fact_id']}: design_rationale이 필요함")
        self.graph.add((item, PIPA.designRationale, Literal(str(rationale))))

    def _map_optional_refusal(self, fact: dict[str, Any]) -> None:
        activity = self._ensure_activity(self._activity_id(fact), "CollectionAndUse")
        request = self._ensure_consent_request(activity)
        if not isinstance(fact["value"], bool):
            raise FactValidationError(
                f"{fact['fact_id']}: deniesServiceOnOptionalRefusal 값은 boolean이어야 함"
            )
        self.graph.add(
            (
                request,
                PIPA.deniesServiceOnOptionalRefusal,
                Literal(fact["value"], datatype=XSD.boolean),
            )
        )

    def _map_destruction_link(self, fact: dict[str, Any]) -> None:
        value = fact["value"]
        if not isinstance(value, dict):
            raise FactValidationError(f"{fact['fact_id']}: destruction value는 객체여야 함")
        activity = self._ensure_activity(self._activity_id(fact), "CollectionAndUse")
        condition_text = self._object_name(value, "end_condition", "condition")
        method = self._object_name(value, "destruction_method", "method")
        end = self._ensure_end_condition(activity, condition_text)
        destruction_id = value.get("destruction_id") or f"{self._activity_id(fact)}-destruction"
        destruction = self._ensure_activity(str(destruction_id), "Destruction")
        self.graph.add((destruction, PIPA.hasDestructionMethod, Literal(method)))
        self.graph.add((end, PIPA.triggersDestruction, destruction))
        if destruction not in self._destructions:
            self._destructions.append(destruction)

    # System metadata --------------------------------------------------------

    def _metadata(self, fact: dict[str, Any], field: str) -> None:
        self.system_metadata.append(
            {
                "fact_id": fact["fact_id"],
                "field": field,
                "subject_id": fact["subject_id"],
                "activity_id": fact.get("activity_id"),
                "value": fact["value"],
                "source_type": fact["source_type"],
                "evidence": fact["evidence"],
            }
        )

    def _map_entrusted_task_metadata(self, fact: dict[str, Any]) -> None:
        activity = self._ensure_activity(self._activity_id(fact), "EntrustedProcessing")
        self.graph.add((activity, PIPA.entrustedTaskText, Literal(str(fact["value"]))))
        self._metadata(fact, "entrusted_task_text")

    def _map_notice_incident_time_metadata(self, fact: dict[str, Any]) -> None:
        notice = self._notice(fact)
        self.graph.add((notice, PIPA.noticeIncidentTime, Literal(str(fact["value"]))))
        self._metadata(fact, "notice_incident_time")
