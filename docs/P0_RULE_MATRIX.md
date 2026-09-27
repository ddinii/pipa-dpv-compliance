# P0 Rule Matrix (v1.0 Freeze)

이 문서는 `PIPA Rule Specification v1.0 FINAL`을 코드에서 빠르게 확인하기 위한 개발용 요약입니다.
법률 판단 문서가 아니라 Rule Engine 구현/테스트용 매트릭스입니다.

## 공통 상태

- `GREEN`: Applicability=TRUE이고 필수 Fact가 명시적으로 확인됨
- `AMBER`: Applicability 또는 필수 Fact가 UNKNOWN/모호하여 자동 확정 불가
- `RED`: Applicability=TRUE이고 필수 Fact의 명시적 부재 또는 금지조건이 확인됨
- `N/A`: Applicability=FALSE가 명시적으로 확인됨. 단순 결측은 N/A로 처리하지 않음
- 동일 Rule의 여러 인스턴스는 `RED > AMBER > GREEN` 우선순위로 대표 상태를 요약하며 N/A 인스턴스는 적용 대상 집계에서 제외
- 조건부 활동 자체의 명시적 부재는 `system_metadata.activity_presence=confirmed_false`로 전달함. 속성 Fact의 `value_state=absent`와 구분함.

## PoC1

| Rule | Applicability | 핵심 Fact | GREEN | AMBER | RED |
|---|---|---|---|---|---|
| P1-R01 처리목적 명시 | 항상 | `CollectionAndUse.hasPurpose` | 처리행위별 목적 식별 가능 | 목적 문구는 있으나 연결/의미 모호 | 목적 미확인 |
| P1-R02 처리·보유기간 명시 | 항상 | `hasRetention -> Retention`, period 또는 identifiable end condition | 기간 또는 식별 가능한 종료조건 | 종료시점/대상 activity 연결 모호 | 기간·종료조건 미확인 |
| P1-R03 제3자 제공 기재 | `ThirdPartyProvision=TRUE` | recipient + personal information + purpose | 3요소 모두 확인 | 제공 여부/일부 값 모호 | 제공 확인 + 필수요소 누락 |
| P1-R04 파기 절차·방법 | 항상 | `Destruction.hasDestructionMethod` | 구체적 방법 | 파기 언급은 있으나 방법 모호 | 방법 미확인 |
| P1-R06 처리위탁 | `EntrustedProcessing=TRUE` | processor + processor name + entrusted task text | 수탁자/업무 확인 | 일부 모호 | 위탁 확인 + 수탁자/업무 부재 |
| P1-R07 권리행사 방법 | 항상 | rights + exercise procedure | 권리와 행사절차 확인 | 일부 권리/절차만 확인 또는 모호 | 행사 방법·절차 미확인 |

## PoC2

| Rule | Applicability | 핵심 Fact | GREEN | AMBER | RED |
|---|---|---|---|---|---|
| P2-R01 사고 사실·통지문 존재 검토 | `DataBreachIncident=TRUE` | `F2-01` incident + `F2-02` affected PI + `F2-03` notice | 사고·영향항목·notice 존재 확인 | 영향항목 또는 notice 값 UNKNOWN/모호 | 사고·영향항목 확인 + notice 부재 |
| P2-R02 통지 항목 완전성 | `NotificationNotice=TRUE` | incident affected items vs notice mentioned items | 실제 영향 항목 모두 포함 | 포괄표현 등으로 집합 비교 불가 | 실제 영향 항목 누락 |
| P2-R03 통지 시점·경위 | `NotificationNotice=TRUE` | `noticeIncidentTime` + `hasIncidentCircumstances` | 통지문 자체에 둘 다 확인 | 둘 중 하나가 UNKNOWN/모호 | 둘 중 하나 이상 명시적 부재 |
| P2-R08 피해 최소화·대응·구제 | `DataBreachIncident=TRUE` | response measure 4 roles | 4개 역할 모두 확인 | 일부 역할/내용 모호 | 필수 대응정보 부재 |

P2-R01은 통지 대상 여부를 자동판정하지 않고, 제공된 사고 사실과 `NotificationNotice` 존재 여부만 검토합니다. 신고 threshold와 `ReportingObligation`은 v1 범위 밖입니다.

P2-R03의 `noticeIncidentTime`은 system field `notice_incident_time`의 graph 호환 표현이며 실제 `incidentDate`와 분리합니다. 실제 사고시각이 있다는 이유만으로 GREEN 처리하지 않습니다.

P2-R08의 역할은 `data_subject_guidance`, `controller_response`, `remedy_procedure`, `post_incident_mitigation` 4종입니다. 이 4종 밖의 `measureRole` 값은 v1 Rule 입력으로 확정하지 않습니다.

## PoC3

| Rule | Applicability | 핵심 Fact | GREEN | AMBER | RED |
|---|---|---|---|---|---|
| P3-R01 법적근거 | `CollectionAndUse=TRUE` | `hasLegalBasis` | 구체 법적근거 유형 명시 | 유형 UNKNOWN/모호 | 근거 미지정 |
| P3-R02 동의 목적 | `LegalBasis=Consent` | consent request + purpose | 동의 맥락 목적 구체적 | 포괄/연결 모호 | 목적 미지정 |
| P3-R03 동의 항목 | `LegalBasis=Consent` | consent request + PI items | 동의 대상 항목 특정 | 포괄 범주/일부 모호 | 항목 미지정 |
| P3-R04 동의 보유기간 | `LegalBasis=Consent` | retention + period 또는 identifiable end condition | 기간/종료조건 설계 | 조건/연결 모호 | 기간·종료조건 미설계 |
| P3-R05 최소수집 사유 | `CollectionAndUse=TRUE` | item name + `isRequired` + `designRationale` | 필수항목마다 사유 | 일부 사유 모호/누락 | 필수 지정 항목에 사유 부재 |
| P3-R06 선택항목 거부금지 | optional item 존재 | `deniesServiceOnOptionalRefusal` | `false` | UNKNOWN | `true` |
| P3-R08 보유종료→파기 | retention/end condition TRUE | end condition -> destruction -> method | 파기+방법 연결 | 연결/방법 일부 모호 | 종료조건 있으나 파기 연결 부재 |
| P3-R11 처리위탁 설계 | `EntrustedProcessing=TRUE` | processor + task text | 수탁자/업무 확인 | 일부 미정/모호 | 수탁자 또는 업무 부재 |

## 구현 메모

- `app/rules/engine.py`가 18개 P0 Rule의 결정론적 판정을 담당합니다.
- `rules/p0_rules.json`은 Rule ID, PoC, 법적 근거, applicability, ontology term metadata를 관리합니다.
- P2-R01은 v1에서 `F2-01 DataBreachIncident`, `F2-02 affectsPersonalInformation`, `F2-03 hasNotificationNotice`만 Required Fact로 사용합니다. 통지 대상 여부 자체, 신고 threshold, `ReportingObligation`, `triggersNotificationObligation` 자동판정은 범위 밖입니다.
- `noticeIncidentTime`, `measureRole`, `entrustedTaskText`는 Rule 입력용 보조 metadata이며 ontology v1.0에서는 annotation property로만 정의되어 있습니다.
- N/A 적용성 메타데이터를 실제 사용하는 핵심 Rule은 P1-R03, P1-R06, P2-R02, P2-R03, P3-R11입니다.
- P2-R01은 사고 입력이 존재하는 상태에서 통지문이 없으면 RED이며, P2-R02/P2-R03만 N/A입니다.
- Presence State는 Frozen Fact가 아닌 system metadata이므로 Fact/Ontology v1.0을 유지합니다.
