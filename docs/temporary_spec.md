# Temporary Specification

## 1. 구현 목적

PIPA-DPV Compliance Prototype은 개인정보 처리 사실을 공통 데이터 모델로 변환한 뒤,
RDF와 SHACL을 이용하여 개인정보 보호법 관련 형식 요건을 검증하는 프로토타입이다.

현재 단계에서는 개인정보 보호법 제17조의 동의 기반 제3자 제공 규칙 하나를 대상으로 한다.

## 2. 처리 흐름

JSON Input

→ ProcessingFact

→ RDF Graph

→ SHACL Rule Loading

→ pySHACL Validation

→ Validation Result

→ FastAPI Response

## 3. 공통 데이터 모델

입력 출처와 관계없이 내부에서는 `ProcessingFact` 모델을 사용한다.

현재 입력:

- 사용자가 직접 입력한 JSON

향후 입력:

- LLM이 문서에서 추출한 JSON
- 개인정보 처리방침 분석 결과
- 기획서 또는 정책 문서 분석 결과

검증 엔진은 입력 출처와 무관하게 동일한 `ProcessingFact`를 사용한다.

## 4. 입력 항목

현재 주요 입력 항목은 다음과 같다.

- `processingType`
- `personalData`
- `purpose`
- `recipient`
- `recipientRole`
- `legalBasis`
- `retentionPeriod`
- `noticeItems`

## 5. 상태값

### PASS

현재 구현된 규칙의 형식적 검사 항목을 충족한 상태다.

최종적인 법률상 적법성을 의미하지 않는다.

### FAIL

명확한 위반을 판별하는 규칙을 위해 예약된 상태다.

현재 제17조 프로토타입에서는 사용하지 않는다.

### NEEDS_INFORMATION

검증에 필요한 정보가 누락된 상태다.

### HUMAN_REVIEW_REQUIRED

현재 구현된 규칙만으로 판단할 수 없거나 법률적 해석이 필요한 상태다.

## 6. 적용 규칙

### PIPA-17-CONSENT-001

적용 조건:

- `processingType = ThirdPartyTransfer`
- `legalBasis = Consent`

검사 항목:

1. 제공받는 자
2. 제공받는 자의 개인정보 이용 목적
3. 제공하는 개인정보의 항목
4. 제공받는 자의 개인정보 보유 및 이용 기간
5. 동의 거부 권리 및 거부에 따른 불이익 관련 고지

근거 조항:

- 개인정보 보호법 제17조제1항제1호 및 제2항

## 7. 현재 구현된 모듈

- FastAPI API
- ProcessingFact 공통 모델
- RDF 변환
- PIPA-DPV 최소 온톨로지
- SHACL 규칙 로더
- pySHACL 검증
- 검증 결과 가공
- PASS / NEEDS_INFORMATION / HUMAN_REVIEW_REQUIRED 응답
- pytest 테스트

## 8. 현재 구현하지 않는 항목

- LLM 기반 문서 추출
- 제15조 등 추가 법령 규칙
- 처리위탁 규칙
- 규칙 버전 관리
- 법령 시행일 관리
- 사용자 로그인
- 검증 이력 저장
- PDF 보고서
- 관리자 화면
- 실제 서비스 프론트엔드