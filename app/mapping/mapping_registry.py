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
    # v1.1 (2026-10-29) 국외 이전 기재 — 개인정보 보호법 제28조의8 제2항.
    # 보유·이용 기간(제4호 후단)은 새 번호를 두지 않고 기존 F1-03/F1-04를 쓴다.
    "F1-13": FactSpec("CrossBorderTransfer", "hasDestinationCountry", "destination_country"),  # 제2호 국가
    "F1-14": FactSpec("CrossBorderTransfer", "hasPersonalInformation", "personal_information"),  # 제1호
    "F1-15": FactSpec("CrossBorderTransfer", "hasPurpose", "purpose"),  # 제4호 이용목적
    "F1-16": FactSpec("CrossBorderTransfer", "hasTransferRecipient", "transfer_recipient"),  # 제3호
    "F1-17": FactSpec("OverseasRecipient", "hasContact", "recipient_contact"),  # 제3호 연락처
    "F1-18": FactSpec("CrossBorderTransfer", "hasTransferTimingAndMethod", "activity_literal"),  # 제2호
    "F1-19": FactSpec("CrossBorderTransfer", "hasTransferRefusalProcedure", "activity_literal"),  # 제5호
    # v1.1 개인정보 보호책임자 기재 — 제30조 제1항 제6호. 처리행위에 속하지 않는다 (F1-11처럼 문서 단위).
    "F1-20": FactSpec("PersonalInformationController", "hasPrivacyOfficer", "privacy_officer"),  # 성명 또는 부서
    "F1-21": FactSpec("PrivacyOfficer", "hasContact", "officer_contact"),  # 연락처
    # v1.1 처리하는 개인정보 항목 기재 (시행령 제31조 제1항 제1호). 온톨로지 기존 용어를 쓴다
    "F1-22": FactSpec("CollectionAndUse", "hasPersonalInformation", "personal_information"),
    # v1.2 자동수집장치 기재: 문서 범위 조건부 점검.
    "F1-23": FactSpec("PersonalInformationController", "hasAutomaticCollectionDevice", "controller_literal"),
    "F1-24": FactSpec("PersonalInformationController", "hasAutomaticCollectionOperation", "controller_literal"),
    "F1-25": FactSpec("PersonalInformationController", "hasAutomaticCollectionOptOutMethod", "controller_literal"),
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
    "F2-11": FactSpec("NotificationNotice", "hasDamageReportDepartment", "notice_literal"),
    "F2-12": FactSpec("NotificationNotice", "hasDamageReportContact", "notice_literal"),
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


# 처리행위에 속하지 않는 문서 단위 Fact. activity_id가 없어도 된다.
DOCUMENT_SCOPE_FACTS = {"F1-11", "F1-12", "F1-20", "F1-21", "F1-23", "F1-24", "F1-25"}
