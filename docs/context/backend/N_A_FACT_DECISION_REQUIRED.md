# N/A 적용성 상태 결정 기록

결정일: 2026-09-27  
구현 상태: 제안안 구현 완료, 팀 승인 필요  
대상 버전: Frozen Fact/Ontology v1.0

## 결정

조건부 처리행위의 존재 여부는 신규 Frozen Fact가 아니라
`MappingResult.system_metadata.activity_presence`로 전달함.

```json
{
  "field": "activity_presence",
  "activity_type": "ThirdPartyProvision",
  "state": "confirmed_false",
  "source_type": "policy_text",
  "evidence": [{"text": "제3자에게 제공하지 않습니다."}]
}
```

허용 `activity_type`은 다음 3종임.

- `ThirdPartyProvision`
- `EntrustedProcessing`
- `NotificationNotice`

허용 상태는 `confirmed_true`, `confirmed_false`, `unknown`임. 현재 N/A 판정에는
근거가 있는 `confirmed_false`만 사용함. 메타데이터에는 비어 있지 않은 evidence와
허용된 `source_type`이 필수임.

## N/A가 필요한 핵심 Rule 5개

| Rule | 적용 대상 자체가 없음 | 결과 |
|---|---|---|
| P1-R03 | `ThirdPartyProvision=confirmed_false` | N/A |
| P1-R06 | `EntrustedProcessing=confirmed_false` | N/A |
| P2-R02 | `NotificationNotice=confirmed_false` | N/A |
| P2-R03 | `NotificationNotice=confirmed_false` | N/A |
| P3-R11 | `EntrustedProcessing=confirmed_false` | N/A |

P2-R01은 사고가 입력된 상황에서 통지문 부재를 검토하는 Rule이므로 통지문이 없으면
RED임. P2-R08은 사고 대응조치를 검토하므로 사고 입력이 필수임. PoC3의
CollectionAndUse 및 Retention은 현재 Form 계약에서 필수이므로 별도 N/A presence
상태를 추가하지 않음.

## 모델링 원칙

- **property 부재**: 활동은 존재하지만 필수 속성이 없음. 해당 Rule은 RED 또는
  AMBER가 될 수 있음. 예: ThirdPartyProvision은 있으나 recipient가 없음.
- **activity 부재**: 조건부 활동 자체가 없다고 입력 또는 원문에서 명시적으로
  확인됨. 해당 조건부 Rule은 N/A임.
- RDF triple이 없다는 사실만으로 activity 부재를 추론하지 않음.
- Frozen Fact의 `value_state=absent`를 activity 부재로 재해석하지 않음.
- `unknown`과 `confirmed_false`를 서로 변환하지 않음.

## 선택 이유와 버전

Presence State는 법률 도메인 사실이 아니라 Rule 적용성 판정을 위한 입력 상태임.
따라서 core ontology property로 영구 저장하지 않고 system metadata로 유지함.
Rule Engine은 평가 직전에만 `https://w3id.org/pipa-compliance/metadata#`의 기술
predicate로 임시 투영함. 테스트 전용 `https://example.org/pipa-test/metadata#`에
의존하지 않음.

신규 Fact ID와 core ontology term을 추가하지 않았으므로 Fact Dictionary와
Ontology 버전은 v1.0을 유지함. 향후 Presence를 법률 도메인 Fact 또는 공개 RDF
vocabulary로 승격하면 Fact/Ontology v1.1로 올리고 Dictionary, ontology, SHACL,
mapping spec, engine을 함께 변경해야 함.

## 승인 요청

다음 항목에 대한 Rule 정의 담당자와 Rule Engine 담당자의 승인이 필요함.

- 위 5개 Rule의 N/A applicability 정의
- Presence State를 system metadata로 유지하는 결정
- P2-R01의 통지문 부재 결과를 RED로 유지하는 결정
- 신규 Fact가 필요해질 경우 v1.1로 개정하는 버전 정책

승인 전까지 이 문서의 상태는 `제안안 구현 완료, 팀 승인 필요`로 표시함. 승인자를
추정하거나 승인 완료로 기록하지 않음.
