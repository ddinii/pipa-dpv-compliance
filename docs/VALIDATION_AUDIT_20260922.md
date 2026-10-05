# PIPA Fact-Ontology Mapping 검증 감사 결과

검증일: 2026-09-22

## 결론

Fact-Ontology Mapping 계층은 Frozen Fact 35종(F1 12종, F2 10종, F3 13종)에 대한 등록, 온톨로지 용어 존재, 매퍼 핸들러 존재, 처리행위 분리, PoC2 사고/통지 분리, PoC3 Form 변환 및 SHACL 구조 검증을 통과한다.

그러나 프로젝트 전체의 P0 18개 Rule E2E 완료를 의미하지 않는다. 현재 패키지에는 Rule Engine, p0_rules.json, API 및 UI가 포함되어 있지 않으므로 RuleResult의 GREEN/YELLOW/RED/N/A, Evidence, legal_basis, version 및 결정론성은 이 패키지만으로 검증할 수 없다.

P2-R01은 팀 결정에 따라 v1 범위를 유지한다. F2-01/F2-02/F2-03 및 `hasNotificationNotice`를 사용하며 `triggersNotificationObligation`, F2-11, ReportingObligation 자동판정은 사용하지 않는다.

## 해결한 결함

1. `entrusted_task_text`, `notice_incident_time`, `measure_role`을 system metadata에 보존하면서 골든 TTL 및 graph-only Rule Engine 호환용 Annotation triple도 생성한다.
2. `measure_role`을 frozen enum 4종으로 제한하고 중복 역할을 거부한다.
3. activity/incident 범위 Fact의 `activity_id` 누락을 거부한다.
4. 빈 Evidence 배열을 거부한다.
5. 서로 다른 activity의 RetentionEndCondition과 Destruction을 전역 자동 연결하지 않는다.
6. legacy namespace를 거부한다.
7. Frozen Fact 35종의 Class/Property와 mapper handler 존재를 자동검증한다.

## 자동검증 결과

- 단위/계약 테스트: 13개 PASS
- SC-D01 Fact: 43개
- SC-D01 RDF triple: 124개
- SC-D01 system metadata: 2개
- SHACL: PASS

## 요구사항 Acceptance Criteria 대조

| 기준 | 이 패키지 상태 | 비고 |
|---|---|---|
| TST-001 Schema | PASS(매퍼 경계) | enum/type/activity_id/evidence 및 mapping contract 검사 |
| TST-002 Process Scope | PASS | 동일 항목 activity 분리 및 cross-activity 파기 연결 방지 |
| TST-003 4 Status | 미검증 | Rule Engine 필요 |
| TST-004 RuleResult Evidence | 미검증 | Rule Engine/RuleResult 필요 |
| TST-005 PoC1 E2E | 미완료 | LLM Extractor, 6 Rule, API/UI 필요 |
| TST-006 PoC2 E2E | 부분 PASS | P2-R01 v1 계약 확정. 실제 4 Rule 실행 필요 |
| TST-007 PoC3 E2E | 부분 PASS | Form→Fact→RDF→SHACL PASS, 8 Rule/UI 미검증 |
| TST-008 Determinism | 미검증 | Rule Engine 필요 |
| TST-009 No Threshold | 문서상 PASS, 코드 미검증 | Rule Engine 코드 필요 |
| TST-010 Version | Fact version만 PASS | Rule/ontology/source_document version 결과 검증 필요 |

## P2-R01 v1 결정사항

Rule Specification의 `triggersNotificationObligation` 문구와 Fact Dictionary 사이에 충돌이 있었으나, 팀 결정으로 v1 범위를 유지한다. Rule Engine에서 해당 요구를 제거하고 P2-R01은 F2-01/F2-02/F2-03 및 `hasNotificationNotice`를 평가한다. 매퍼는 F2-02에서 통지의무를 파생하지 않고 비공식 F2-11도 추가하지 않는다. Rule Specification에는 이 결정을 정오표 또는 개정본으로 반영해야 한다.

## 최종 완료 판정 조건

다음이 모두 충족되어야 프로젝트 전체를 완료로 판정할 수 있다.

- P2-R01 결정사항의 Rule Specification 및 Rule Engine 반영 확인
- PoC1 6개 Rule 실제 실행 PASS
- PoC2 4개 Rule 실제 실행 PASS
- PoC3 8개 Rule 실제 실행 PASS
- GREEN/YELLOW/RED/N/A 대표 케이스 재현
- 모든 G/A/R 결과 Evidence 존재
- 모든 결과 legal_basis 및 ontology/rule/fact version 존재
- 동일 입력 재실행 결과 결정론성 확인
- API/UI까지 세 시나리오 E2E 확인
