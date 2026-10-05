# Fact ↔ Ontology 매핑표 v1.0

Frozen Fact 35종과 core ontology term은 변경하지 않음. 조건부 활동 자체의 존재
여부는 아래 별도 system metadata 계약으로 전달함.

## Rule applicability presence metadata

| system metadata | 의미 | 사용 Rule |
|---|---|---|
| `ThirdPartyProvision=confirmed_false` | 제3자 제공 활동 자체가 없다고 확인됨 | P1-R03 → N/A |
| `EntrustedProcessing=confirmed_false` | 처리위탁 활동 자체가 없다고 확인됨 | P1-R06, P3-R11 → N/A |
| `NotificationNotice=confirmed_false` | 입력 사고에 대한 통지문 자체가 없다고 확인됨 | P2-R02, P2-R03 → N/A |

형식은 `field=activity_presence`, `activity_type`, `state`, `source_type`,
`evidence`로 고정함. 이 메타데이터는 mapper가 검증해 보존하고 Rule Engine이 평가
직전에 `https://w3id.org/pipa-compliance/metadata#` 기술 vocabulary로 임시
투영함. core ontology assertion으로 직렬화하지 않음.

활동이 존재하지만 recipient, processor, 통지 내용 등 속성이 빠진 경우에는 해당
Frozen Fact의 `value_state=absent`를 사용함. 이 경우 N/A가 아니라 RED/YELLOW 평가
대상임.

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
| F1-12 | `DataSubjectRight.hasExerciseProcedure → RightsExerciseProcedure` (`value`: string, `subject_id`: F1-11 권리명) |

> **F1-12 v1 확정 계약:** Fact Dictionary v1.0의 Type은 `string`이다.
> `subject_id`에는 연결 대상인 F1-11 권리명을 사용하며, 매퍼는 F1-11과 F1-12에서
> 동일한 `_derived_uri("right", 권리명)`을 생성한다. 기존 PoC1 Extractor가 출력하는
> `{right, procedure}` 객체형은 통합 호환 입력으로 수용한 뒤 동일한 RDF로 정규화한다.

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

## 버전 정책

현재 변경은 신규 Fact ID 또는 core ontology term을 추가하지 않으므로 v1.0을 유지함.
향후 presence 상태를 Frozen Fact나 공개 RDF property로 승격하면 v1.1로 올리고 Fact
Dictionary, ontology, SHACL, mapping spec과 engine을 같은 변경으로 배포함.
