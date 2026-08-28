# PIPA-DPV Compliance Prototype

개인정보 처리 사실을 공통 데이터 모델로 변환하고,
RDF 및 SHACL을 이용하여 개인정보 보호법 관련 규칙을 검증하는 프로토타입입니다.

현재 구현 범위는 개인정보 보호법 제17조의 동의 기반 제3자 제공 규칙입니다.

## Architecture

```text
JSON Input
    ↓
ProcessingFact
    ↓
RDF Graph
    ↓
SHACL Rules
    ↓
pySHACL Validation
    ↓
Result Builder
    ↓
FastAPI Response
```

## Current Rule

현재 구현된 대표 규칙:

```text
PIPA-17-CONSENT-001
```

적용 조건:

```text
processingType = ThirdPartyTransfer
legalBasis = Consent
```

검사 항목:

- 제공받는 자
- 제공 목적
- 제공 개인정보 항목
- 보유 및 이용 기간
- 동의 거부 권리 및 불이익 관련 고지

근거 조항:

```text
개인정보 보호법 제17조제1항제1호 및 제2항
```

## Validation Status

### PASS

현재 구현된 형식적 검사 항목을 충족한 상태입니다.

최종적인 법률상 적법성을 의미하지 않습니다.

### FAIL

명확한 위반 규칙을 위해 예약된 상태입니다.

현재 프로토타입에서는 사용하지 않습니다.

### NEEDS_INFORMATION

검증에 필요한 정보가 누락된 상태입니다.

### HUMAN_REVIEW_REQUIRED

현재 구현된 규칙만으로 판단할 수 없는 상태입니다.

## Project Structure

```text
pipa-dpv-compliance/
├── app/
│   ├── api/
│   │   └── validate.py
│   ├── core/
│   │   └── config.py
│   ├── models/
│   │   ├── request.py
│   │   └── response.py
│   ├── services/
│   │   ├── rdf_mapper.py
│   │   ├── rule_loader.py
│   │   ├── validator.py
│   │   └── result_builder.py
│   └── main.py
├── ontology/
│   └── pipa-dpv.ttl
├── rules/
│   └── article17_consent.ttl
├── examples/
│   ├── article17_pass.json
│   ├── article17_missing.json
│   └── article17_review.json
├── tests/
│   ├── test_mapper.py
│   └── test_validator.py
├── docs/
│   └── temporary_spec.md
├── requirements.txt
└── README.md
```

## Setup

가상환경 생성:

```powershell
python -m venv .venv
```

가상환경 활성화:

```powershell
.\.venv\Scripts\Activate.ps1
```

패키지 설치:

```powershell
pip install -r requirements.txt
```

## Run

```powershell
uvicorn app.main:app --reload
```

Swagger UI:

```text
http://127.0.0.1:8000/docs
```

Health Check:

```text
GET /health
```

Validation API:

```text
POST /api/v1/validate
```

## Example Request

```json
{
  "processingType": "ThirdPartyTransfer",
  "personalData": [
    "EmailAddress"
  ],
  "purpose": "Advertising",
  "recipient": "외부 광고업체",
  "recipientRole": "ThirdParty",
  "legalBasis": "Consent",
  "retentionPeriod": "1년",
  "noticeItems": [
    "recipient",
    "purpose",
    "personalData",
    "retentionPeriod",
    "refusalRight"
  ]
}
```

## Example Response

```json
{
  "status": "PASS",
  "appliedRules": [
    {
      "ruleId": "PIPA-17-CONSENT-001",
      "legalBasis": "개인정보 보호법 제17조제1항제1호 및 제2항"
    }
  ],
  "missingInformation": [],
  "humanReviewRequired": false
}
```

## Test

```powershell
python -m pytest -q
```

현재 테스트 시나리오:

- RDF 변환
- Article 17 PASS
- Article 17 NEEDS_INFORMATION
- 미구현 규칙 HUMAN_REVIEW_REQUIRED

## Disclaimer

본 프로젝트의 `PASS` 결과는 현재 구현된 규칙의 형식적 검사 항목을 충족했다는 의미이며,
최종적인 법률상 적법성 판단을 의미하지 않습니다.