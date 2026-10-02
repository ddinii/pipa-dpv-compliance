# 결과 화면 용어·근거 가독성 개선

## 변경 목적

룰엔진 응답의 `matched_facts`, `missing_facts`, `uncertain_facts`와 RDF 근거를 일반 사용자 화면에 그대로 노출하지 않도록 표시 계층을 개선함. API 응답과 룰엔진 입력·출력 계약은 변경하지 않음.

## 사용자 화면 변경

| 기존 표시 | 변경 표시 |
| --- | --- |
| 확인된 Fact | 확인된 사항 |
| 누락된 Fact | 누락된 필수사항 |
| 불확실한 Fact | 추가 확인사항 |
| 판정에 사용된 Fact 보기 | 판정에 사용된 검토 항목 보기 |
| 상세 근거 보기 | 판단 근거 보기 |
| `rdf_assertion` | 확인된 관계 |
| `source_text` | 원문 근거 |
| `fact_contract` | 입력자료 확인 |
| `absence` | 확인 필요 |
| `GREEN / AMBER / RED / N/A` | 충족 / 추가 확인 / 미충족 / 해당 없음 |

## RDF·Fact 표시 원칙

- `rdf:ActivityId:hasPurpose` 같은 내부 식별자는 `처리행위 · 처리 목적` 형태로 변환함.
- `fact:F2-08:absent` 같은 Fact 상태는 `통지문 기재 사고시점 — 문서에서 확인되지 않음` 형태로 변환함.
- URI 객체값은 전체 URI 대신 마지막 온톨로지 용어를 한국어 라벨로 표시함.
- RDF 주체 URI, predicate 원문, evidence type 원문은 사용자 화면에 렌더링하지 않음.
- `개발자 정보` 및 `기술 상세 보기` 영역을 프론트에서 제거함.
- `provision`, `processing activity`, `activity` 등 사용자용 설명에 섞인 내부 용어를 한국어로 변환함.
- 원문 인용은 `원문 근거` 블록으로 구분하여 표시함.

## 변경 파일

- `frontend/src/utils/complianceLabels.ts`
- `frontend/src/components/RuleResultCard.tsx`
- `frontend/src/components/EvidenceList.tsx`
- `frontend/src/components/InstanceRuleResultList.tsx`
- `frontend/src/components/ComplianceResults.css`

## 검증 결과

- `npm run lint` 통과함.
- `npm run build` 통과함.
- `python run_tests.py` 45개 통과함.
- 프록시 환경변수를 제외하고 `python -m pytest -q` 실행 시 521개 통과함.

## 비변경 범위

- 온톨로지 TTL, SHACL, Fact Dictionary, Mapper 및 Rule Engine 로직은 변경하지 않음.
- API 응답 필드명과 값은 변경하지 않음.
- 본 변경은 프론트엔드 표시 계층에 한정함.
