"""Frozen Fact ID to ontology mapping registry for P0 rules."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FactSpec:
    subject_class: str
    ontology_property: str | None
    mapping_kind: str


FACT_SPECS: dict[str, FactSpec] = {
    # PoC1
    "F1-01": FactSpec("CollectionAndUse", None, "class_assertion"),
    "F1-02": FactSpec("CollectionAndUse", "hasPurpose", "purpose"),
    "F1-03": FactSpec("PersonalInformationProcessing", "hasRetention", "retention_period"),
    "F1-04": FactSpec("PersonalInformationProcessing", "hasRetention", "retention_end"),
    "F1-05": FactSpec("ThirdPartyProvision", "hasRecipient", "recipient"),
    "F1-06": FactSpec("ThirdPartyProvision", "hasPersonalInformation", "personal_information"),
    "F1-07": FactSpec("ThirdPartyProvision", "hasPurpose", "purpose"),
    "F1-08": FactSpec("Destruction", "hasDestructionMethod", "destruction_method"),
    "F1-09": FactSpec("EntrustedProcessing", "hasProcessor", "processor"),
    "F1-10": FactSpec("EntrustedProcessing", None, "entrusted_task_metadata"),
    "F1-11": FactSpec("DataSubject", "hasRight", "rights"),
    "F1-12": FactSpec("DataSubjectRight", "hasExerciseProcedure", "right_procedure"),
    # PoC2
    "F2-01": FactSpec("DataBreachIncident", None, "class_assertion"),
    "F2-02": FactSpec("DataBreachIncident", "affectsPersonalInformation", "incident_information"),
    "F2-03": FactSpec("DataBreachIncident", "hasNotificationNotice", "notification_notice"),
    "F2-04": FactSpec("NotificationNotice", "mentionsPersonalInformation", "notice_information"),
    "F2-05": FactSpec("DataBreachIncident", "incidentDate", "datetime"),
    "F2-06": FactSpec("DataBreachIncident", "detectionDate", "datetime"),
    "F2-07": FactSpec("DataBreachIncident", "notificationDate", "datetime"),
    "F2-08": FactSpec("NotificationNotice", None, "notice_incident_time_metadata"),
    "F2-09": FactSpec("NotificationNotice", "hasIncidentCircumstances", "string_literal"),
    "F2-10": FactSpec("DataBreachIncident", "hasResponseMeasure", "response_measures"),
    # PoC3
    "F3-01": FactSpec("CollectionAndUse", None, "class_assertion"),
    "F3-02": FactSpec("CollectionAndUse", "hasLegalBasis", "legal_basis"),
    "F3-03": FactSpec("CollectionAndUse", "hasConsentRequest", "consent_request"),
    "F3-04": FactSpec("CollectionAndUse", "hasPurpose", "purpose"),
    "F3-05": FactSpec("CollectionAndUse", "hasPersonalInformation", "personal_information"),
    "F3-06": FactSpec("CollectionAndUse", "hasRetention", "retention_object"),
    "F3-07": FactSpec("PersonalInformation", "isRequired", "item_required"),
    "F3-08": FactSpec("PersonalInformation", "designRationale", "item_rationale"),
    "F3-09": FactSpec("ConsentRequest", "deniesServiceOnOptionalRefusal", "optional_refusal"),
    "F3-10": FactSpec("Retention", "hasRetentionEndCondition", "retention_end"),
    "F3-11": FactSpec("RetentionEndCondition", "triggersDestruction", "destruction_link"),
    "F3-12": FactSpec("EntrustedProcessing", "hasProcessor", "processor"),
    "F3-13": FactSpec("EntrustedProcessing", None, "entrusted_task_metadata"),
}


SYSTEM_METADATA_FACTS = {"F1-10", "F2-08", "F3-13"}

