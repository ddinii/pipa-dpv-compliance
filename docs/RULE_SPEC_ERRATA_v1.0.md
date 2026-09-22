# PIPA Rule Specification v1.0 정오표

이 문서는 Frozen `PIPA Fact Dictionary v1.0`과 Ontology v1.0에 맞춰 Rule Specification의 PoC2 정의를 정정한다.

## 1. P2-R01 Required Fact 정정

기존 정의:

- `affectsPersonalInformation`
- `triggersNotificationObligation`
- `hasNotificationNotice`

v1 확정 정의:

- `F2-01 DataBreachIncident`
- `F2-02 DataBreachIncident.affectsPersonalInformation`
- `F2-03 DataBreachIncident.hasNotificationNotice`

`triggersNotificationObligation`은 Frozen Fact Dictionary 및 Ontology v1.0에 존재하지 않으므로 Required Fact에서 제거한다. `ReportingObligation` 자동판정과 신고 threshold 판정도 v1 범위 밖이다.

P2-R01은 통지 대상 여부 자체를 자동판정하지 않는다. 입력으로 제공된 사고 인스턴스, 실제 영향 개인정보 항목, `NotificationNotice` 존재 여부를 검토한다. 따라서 P2-R01의 상태는 v1 입력 계약 충족 및 통지문 존재 검토 결과이며, 법적 통지의무 대상 여부를 확정하는 결과로 해석하지 않는다.

## 2. P2-R03 사고시점과 통지문 기재시점 분리

- `F2-05 DataBreachIncident.incidentDate`: 실제 사고 발생시점
- `F2-08 notice_incident_time`: 통지문에 기재된 유출등 시점

두 값은 절대 합치지 않는다. Rule Engine의 graph-only 호환 표현인 `pipa:noticeIncidentTime`은 `notice_incident_time`을 투영한 보조 Annotation이며, `incidentDate`를 대신 사용하지 않는다.

## 3. P2-R08 measure_role v1 enum

`F2-10`의 `measure_role`은 다음 4종으로 고정한다.

- `data_subject_guidance`
- `controller_response`
- `remedy_procedure`
- `post_incident_mitigation`

Rule Engine은 4종이 모두 확인될 때 GREEN으로 평가한다. v1에 없는 역할 값이 입력되면 GREEN으로 확정하지 않는다.

## 4. Rule ↔ Fact Coverage - P0 18개

| Rule | Required Fact IDs |
|---|---|
| P1-R01 | F1-01, F1-02 |
| P1-R02 | F1-03, F1-04 |
| P1-R03 | F1-05, F1-06, F1-07 |
| P1-R04 | F1-08 |
| P1-R06 | F1-09, F1-10 |
| P1-R07 | F1-11, F1-12 |
| P2-R01 | F2-01, F2-02, F2-03 |
| P2-R02 | F2-02, F2-04 |
| P2-R03 | F2-08, F2-09 |
| P2-R08 | F2-01, F2-10 |
| P3-R01 | F3-01, F3-02 |
| P3-R02 | F3-02, F3-03, F3-04 |
| P3-R03 | F3-02, F3-03, F3-05 |
| P3-R04 | F3-02, F3-03, F3-06 |
| P3-R05 | F3-05, F3-07, F3-08 |
| P3-R06 | F3-07, F3-09 |
| P3-R08 | F3-10, F3-11 |
| P3-R11 | F3-12, F3-13 |

이 Coverage를 `rules/p0_rules.json`의 `required_fact_ids`로 고정하고 테스트에서 18개 Rule 전체를 자동검증한다.
