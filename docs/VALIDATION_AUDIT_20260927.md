# PIPA Fact-Ontology Mapping 수정 검증 결과

검증일: 2026-09-27

## 수정 대상

1. Fact Dictionary v1.0에서 F1-12 Type이 `string`인데 기존 테스트가 객체형 값을 사용하던 오류
2. F1-11의 권리 노드와 F1-12의 권리 노드가 서로 다른 URI로 생성되던 오류
3. TST-003 N/A 재현에 필요한 활동 존재/부재 계약 공백

## 반영 내용

- F1-12의 표준 문자열형과 기존 PoC1 Extractor의 객체형을 모두 검증하도록 수정함.
- JSON Schema에도 두 통합 입력 형태를 명시함.
- F1-12의 `subject_id`를 연결 대상 F1-11 권리명으로 사용하도록 계약을 명시함.
- F1-11과 F1-12 모두 `_derived_uri("right", 권리명)`을 사용하도록 매퍼를 통일함.
- 문자열형과 객체형 모두 동일 권리 URI로 연결되는 회귀 테스트를 추가함.
- 신규 Fact 없이 `system_metadata.activity_presence`로 활동 존재/부재를 분리함.
- P1-R03, P1-R06, P2-R02, P2-R03, P3-R11의 N/A 전체 경로 회귀 테스트를 추가함.
- Rule Engine의 테스트 전용 metadata namespace 의존을 제거하고 안정적인 기술
  namespace를 평가 시점에만 사용함.
- property 부재와 activity 자체 부재를 분리함.
- SHACL 원본을 `ontology/PIPA_Process_Centered_SHACL_v1.0.ttl` 하나로 통합함.

## 자동검증 결과

- Python 단위/계약/통합 테스트: 전체 PASS
- PoC3 Fact 생성: 43개 PASS
- PoC3 RDF 생성: 124 triples PASS
- 시스템 메타데이터: 2개 PASS
- PoC3 SHACL: PASS
- F1-12 string 계약: PASS
- F1-11/F1-12 동일 권리 노드 연결: PASS
- 기존 PoC1 Extractor F1-12 객체형 호환: PASS

## N/A 검증 결과

- P1-R03: ThirdPartyProvision 명시적 부재 → N/A
- P1-R06: EntrustedProcessing 명시적 부재 → N/A
- P2-R01: 사고는 있으나 통지문 부재 → RED
- P2-R02: NotificationNotice 명시적 부재 → N/A
- P2-R03: NotificationNotice 명시적 부재 → N/A
- P3-R11: EntrustedProcessing 명시적 부재 → N/A
- ThirdPartyProvision은 존재하지만 recipient property 부재 → RED

위 결과는 Mock Extractor/Form → service → Mapper → Rule Engine 경로로 검증함.
세부 결정 및 팀 승인 상태는
`docs/context/backend/N_A_FACT_DECISION_REQUIRED.md`를 확인함.

## 버전 및 범위 제한

신규 Fact ID와 core ontology term을 추가하지 않았으므로 Frozen Fact/Ontology v1.0을
유지함. 실제 LLM Extractor 품질, 외부 배포 환경, 법적 판단 자체는 이 테스트의 검증
범위가 아님. N/A applicability 정의와 system metadata 방식은 Rule 정의 담당자와 Rule
Engine 담당자의 명시적 승인이 필요함.
