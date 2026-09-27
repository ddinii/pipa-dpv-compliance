# PIPA Fact-Ontology Mapping 수정 검증 결과

검증일: 2026-09-27

## 수정 대상

1. Fact Dictionary v1.0에서 F1-12 Type이 `string`인데 기존 테스트가 객체형 값을 사용하던 오류
2. F1-11의 권리 노드와 F1-12의 권리 노드가 서로 다른 URI로 생성되던 오류
3. TST-003 N/A 재현에 필요한 계약이 Frozen Fact 35종에 존재하지 않는 공백

## 반영 내용

- F1-12의 표준 문자열형과 기존 PoC1 Extractor의 객체형을 모두 검증하도록 수정함.
- JSON Schema에도 두 통합 입력 형태를 명시함.
- F1-12의 `subject_id`를 연결 대상 F1-11 권리명으로 사용하도록 계약을 명시함.
- F1-11과 F1-12 모두 `_derived_uri("right", 권리명)`을 사용하도록 매퍼를 통일함.
- 문자열형과 객체형 모두 동일 권리 URI로 연결되는 회귀 테스트를 추가함.
- N/A는 §14-3 공동 결정 전 임의 Fact ID를 추가하지 않고 미결정 사항으로 분리함.

## 자동검증 결과

- 단위/계약 테스트: 15개 PASS
- PoC3 Fact 생성: 43개 PASS
- PoC3 RDF 생성: 124 triples PASS
- 시스템 메타데이터: 2개 PASS
- PoC3 SHACL: PASS
- F1-12 string 계약: PASS
- F1-11/F1-12 동일 권리 노드 연결: PASS
- 기존 PoC1 Extractor F1-12 객체형 호환: PASS

## 범위 제한

이번 수정으로 F1-12 Fact-RDF 매핑 결함은 해소했음. 다만 N/A는 Rule applicability
계약 또는 신규 Fact ID가 결정되지 않아 구현하지 않았음. 따라서 GREEN/AMBER/RED/N/A
네 상태 전체와 18개 Rule Engine/API/UI E2E는 아직 완료로 표시할 수 없음.

세부 결정사항은 `N_A_FACT_DECISION_REQUIRED.md`를 확인함.
