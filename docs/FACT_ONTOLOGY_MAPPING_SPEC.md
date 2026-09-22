# Fact ↔ Ontology 매핑표 v1.0

## PoC1

| Fact | RDF/저장 위치 |
|---|---|
| F1-01 | `CollectionAndUse` Class assertion |
| F1-02 | `hasPurpose → ProcessingPurpose.hasPurposeDescription` |
| F1-03 | `hasRetention → Retention.hasRetentionPeriod → RetentionPeriod.hasDurationValue` |
| F1-04 | `hasRetention → Retention.hasRetentionEndCondition` |
| F1-05 | `ThirdPartyProvision.hasRecipient → ThirdParty.hasName` |
| F1-06 | `ThirdPartyProvision.hasPersonalInformation → PersonalInformation` |
| F1-07 | `ThirdPartyProvision.hasPurpose → ProcessingPurpose` |
| F1-08 | `Destruction.hasDestructionMethod` |
| F1-09 | `EntrustedProcessing.hasProcessor → EntrustedProcessor.hasName` |
| F1-10 | `system_metadata.entrusted_task_text` + `pipa:entrustedTaskText` Annotation triple |
| F1-11 | `DataSubject.hasRight → DataSubjectRight` |
| F1-12 | `DataSubjectRight.hasExerciseProcedure → RightsExerciseProcedure` |

## PoC2

| Fact | RDF/저장 위치 |
|---|---|
| F2-01 | `DataBreachIncident` Class assertion |
| F2-02 | `DataBreachIncident.affectsPersonalInformation` |
| F2-03 | `DataBreachIncident.hasNotificationNotice` |
| F2-04 | `NotificationNotice.mentionsPersonalInformation` |
| F2-05 | `DataBreachIncident.incidentDate` |
| F2-06 | `DataBreachIncident.detectionDate` |
| F2-07 | `DataBreachIncident.notificationDate` |
| F2-08 | `system_metadata.notice_incident_time` + `pipa:noticeIncidentTime` Annotation triple |
| F2-09 | `NotificationNotice.hasIncidentCircumstances` |
| F2-10 | `hasResponseMeasure → IncidentResponseMeasure → measureRole` + `system_metadata.measure_role` |

> **P2-R01 v1 확정 계약:** F2-01/F2-02/F2-03만 사용한다.
> `triggersNotificationObligation`은 Fact Dictionary v1.0과 frozen ontology에 없는 항목이고
> ReportingObligation 자동판정도 v1.0 범위 밖이므로 F2-11로 신설하거나 F2-02에서
> 파생하지 않는다. Rule Engine은 `DataBreachIncident`, `affectsPersonalInformation`,
> `hasNotificationNotice`를 평가한다.

## PoC3

| Fact | RDF/저장 위치 |
|---|---|
| F3-01 | `CollectionAndUse` Class assertion |
| F3-02 | `CollectionAndUse.hasLegalBasis → LegalBasis/Consent` |
| F3-03 | `CollectionAndUse.hasConsentRequest → ConsentRequest` |
| F3-04 | `CollectionAndUse.hasPurpose → ProcessingPurpose` |
| F3-05 | `CollectionAndUse.hasPersonalInformation → PersonalInformation` |
| F3-06 | `CollectionAndUse.hasRetention → Retention` |
| F3-07 | 개인정보 항목 Individual의 `isRequired` |
| F3-08 | 개인정보 항목 Individual의 `designRationale` |
| F3-09 | `ConsentRequest.deniesServiceOnOptionalRefusal` |
| F3-10 | `Retention.hasRetentionEndCondition` |
| F3-11 | `RetentionEndCondition.triggersDestruction → Destruction.hasDestructionMethod` |
| F3-12 | `EntrustedProcessing.hasProcessor → EntrustedProcessor.hasName` |
| F3-13 | `system_metadata.entrusted_task_text` + `pipa:entrustedTaskText` Annotation triple |
