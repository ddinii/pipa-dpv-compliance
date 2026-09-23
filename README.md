# PIPA-DPV Compliance Prototype

개인정보보호법(PIPA) 관련 사실을 RDF로 구조화하고, frozen ontology와 결정론적 Machine-Readable Rule을 이용해 컴플라이언스 요건의 **기계판독 가능 여부**를 점검하는 프로토타입입니다.

> GREEN/AMBER/RED는 법률 위반 또는 적법성의 최종 판단이 아닙니다. 입력 문서·사고 사실·설계정보에서 v1.0 Rule이 요구하는 Fact가 확인되는지를 나타냅니다.

## Current Scope

현재 P0 Rule Engine은 **18개 Rule**을 구현합니다.

- PoC1 개인정보 처리방침 준수점검: 6개
- PoC2 침해사고 통지 요건 검토 지원: 4개
- PoC3 Privacy-by-Design 개발지원: 8개

Rule 요약은 [`docs/P0_RULE_MATRIX.md`](docs/P0_RULE_MATRIX.md)에서 빠르게 볼 수 있습니다.

### Status

- `GREEN`: Applicability=TRUE이고 필수 Fact가 명시적으로 확인됨
- `AMBER`: Applicability 또는 필수 Fact가 UNKNOWN/모호하여 자동 확정 불가
- `RED`: Applicability=TRUE이고 필수 Fact의 명시적 부재 또는 금지조건이 확인됨
- `N/A`: Applicability=FALSE가 명시적으로 확인됨. 단순 결측/미추출은 N/A가 아님

동일 Rule 대상 인스턴스가 여러 개면 인스턴스별 결과를 유지하고 대표 상태는 `RED > AMBER > GREEN` 순으로 요약합니다.

## P0 Rule Engine Architecture

```text
RDF Facts
   ↓
PIPA_Ontology_v1.0.ttl
   +
rules/p0_rules.json
   ↓
app.rules.P0RuleEngine
   ↓
RuleResult
(GREEN / AMBER / RED / N/A + evidence + legal basis)
```

핵심 파일:

```text
app/rules/
├─ engine.py       # P0 18개 결정론적 Rule 판정
├─ models.py       # RuleResult / Evidence / Status
├─ metadata.py     # rules/p0_rules.json 로딩
└─ cli.py          # Turtle RDF CLI 실행

rules/
├─ p0_rules.json   # P0 Rule metadata
└─ article17_consent.ttl  # legacy SHACL prototype

ontology/
├─ PIPA_Ontology_v1.0.ttl # frozen P0 ontology
└─ pipa-dpv.ttl           # legacy prototype ontology

tests/
├─ test_p0_rule_engine_v2.py
├─ SC-P01_FINAL_Protege.ttl
├─ SC-P02_FINAL_Protege.ttl
├─ SC-D01_FINAL_Protege.ttl
└─ validate_final_scenarios.py
```

## Important Implementation Notes

### P2-R03

통지문에 기재된 유출등 시점인 `noticeIncidentTime`과 실제 사고의 `incidentDate`는 분리합니다. 실제 사고시각만 존재하는 경우 P2-R03을 GREEN으로 처리하지 않습니다.

### P2-R08

`IncidentResponseMeasure`의 `measureRole`은 다음 4개 역할을 구분합니다.

```text
data_subject_guidance
controller_response
remedy_procedure
post_incident_mitigation
```

P0 v1.0 Freeze에서 GREEN은 4개 역할이 모두 확인되는 경우입니다.

### P2-R01 v1 fact contract

P2-R01의 v1 Required Fact는 `F2-01 DataBreachIncident + F2-02 affectsPersonalInformation + F2-03 hasNotificationNotice`입니다. `triggersNotificationObligation`은 Frozen Fact Dictionary와 Ontology v1.0에 없으므로 Rule 입력에서 사용하지 않습니다.

P2-R01은 통지 대상 여부 자체를 자동판정하지 않습니다. 제공된 사고 사실과 `NotificationNotice` 존재 여부를 검토하며, 신고 threshold와 `ReportingObligation` 자동판정은 v1 범위 밖입니다.

## Setup

PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## Run P0 Rules

PoC1:

```powershell
python -m app.rules.cli tests\SC-P01_FINAL_Protege.ttl --poc poc1
```

PoC2:

```powershell
python -m app.rules.cli tests\SC-P02_FINAL_Protege.ttl --poc poc2
```

PoC3:

```powershell
python -m app.rules.cli tests\SC-D01_FINAL_Protege.ttl --poc poc3
```

전체 18개 Rule:

```powershell
python -m app.rules.cli tests\SC-D01_FINAL_Protege.ttl
```

## Test

P0 Rule Engine만 빠르게 확인:

```powershell
python -m pytest -q tests\test_p0_rule_engine_v2.py
```

전체 테스트:

```powershell
python -m pytest -q
```

Freeze 시나리오 구조 검증:

```powershell
python tests\validate_final_scenarios.py
```

Windows batch 파일:

```powershell
.\tests\run_validation_windows.bat
```

## PoC3 Privacy-by-Design 사전점검

구조화 Form으로 설계정보를 입력하면 P0 PoC3 Rule 8개로 사전점검합니다. LLM을 쓰지 않습니다.

```powershell
uvicorn app.main:app --reload
```

```text
http://127.0.0.1:8000/design
```

예시 설계(SC-D01)가 자동으로 채워지므로 바로 [사전점검 실행]을 누를 수 있습니다.
항목을 추가·삭제하고 "필수/선택/미정"을 바꿔 상태가 어떻게 움직이는지 확인하세요.

빈 값은 `미정`으로 읽혀 해당 Rule이 AMBER가 됩니다. 처리행위 유형의 부재(예: "위탁하지
않는다")를 담을 Fact ID는 Fact Dictionary v1.0에 없으므로, 목록을 비우면 그 처리행위의
Fact가 없을 뿐이며 N/A가 되지는 않습니다.

```text
POST /api/v1/compliance/design-check   # API-003. 설계 Form -> PoC3 RuleResult[]
POST /api/v1/dev/design-facts          # Form -> Fact 변환 결과 (개발용)
GET  /api/v1/dev/design-example        # 예시 설계 Form
GET  /design                           # PbD 체크리스트 화면
```

처리 경로:

```text
DesignForm             입력 계약 (app/forms/poc3.py)
  -> app/builders        Form -> Fact (D01-007)
  -> app/mapping         Fact 검증 + Ontology Mapping (COM-002 / COM-004)
  -> app/rules/engine    P0 PoC3 Rule 8개
  -> ComplianceResponse  기능명세서 9.1
```

Fact Extractor와 평가 세트는 [`evals/README.md`](evals/README.md)를 참고하세요.

## RuleResult 점검 콘솔 (개발용)

Fact Extractor와 Fact→RDF 매퍼가 붙기 전까지, `RuleResult` DTO가 화면에서 성립하는지
확인하는 개발 보조 화면입니다. **API-001/002/003의 구현이 아닙니다.**

```powershell
uvicorn app.main:app --reload
```

```text
http://127.0.0.1:8000/console
```

Freeze 시나리오(SC-P01/P02/D01)를 버튼으로 불러오거나, 매퍼 출력 Turtle을 직접 붙여넣어
18개 Rule 결과를 렌더합니다. RuleResult JSON을 직접 붙여넣어 엔진 없이 DTO만 확인할 수도 있습니다.

콘솔이 자동으로 점검하는 계약 항목:

| 점검 | 근거 |
|---|---|
| 9.1 응답 envelope 6종 존재 여부 | 기능명세서 9.1 |
| 8장 RuleResult 필수 13종 존재 여부 | 기능명세서 8장 |
| evidence의 `source_text` / offset 보유량 | COM-008, P01-004, Fact Dictionary 2장 |
| `instance_results`의 표시용 label 보유 여부 | COM-012 |
| G/A/R 결과에 evidence가 비어 있는지 | TST-004 |

현재 알려진 미해결 계약 결손 3건 (콘솔이 경고로 표시):

1. `RuleResult`에 `source_document_id`가 없습니다. 응답 envelope에만 있어 RuleResult 단건으로는
   입력 문서를 역추적할 수 없습니다 (8장 필수 / NFR-04 / TST-010).
2. `Evidence`에 원문 offset이 없습니다. Fact Dictionary는 evidence를 `text+offset` 또는
   `field_path`로 정의하지만 현재는 `source_text`만 보존합니다.
3. `instance_id`가 raw URI라 표시용 label이 없습니다 (COM-012).

또한 SC-P01에는 `pipa:hasSourceEvidence` 단언이 하나도 없어, Main PoC인 PoC1의 원문 근거 경로가
아직 한 번도 검증되지 않았습니다. SC-P02/SC-D01에는 실제 근거 문자열이 들어 있습니다.

Endpoint:

```text
GET  /console
GET  /api/v1/dev/scenarios
GET  /api/v1/dev/scenarios/{name}
POST /api/v1/dev/evaluate     { turtle, poc?, source_document_id? }
```

## Legacy FastAPI / SHACL Prototype

현재 저장소에는 초기 Article 17 SHACL 프로토타입도 남아 있습니다.

```text
POST /api/v1/validate
```

이 endpoint는 현재 `app/services/validator.py`와 `rules/article17_consent.ttl`을 사용하는 **legacy SHACL flow**입니다. 위의 P0 18-rule `P0RuleEngine`과 동일한 실행 경로가 아닙니다.

Legacy API 실행:

```powershell
uvicorn app.main:app --reload
```

Swagger UI:

```text
http://127.0.0.1:8000/docs
```

## Rule Metadata

`rules/p0_rules.json`에서 다음 metadata를 관리합니다.

- Rule ID / PoC / version
- applicability
- legal basis
- source-spec legal basis
- ontology terms
- implementation notes

일부 조문 번호는 Freeze 문서 작성 후 재확인된 법률 metadata와 차이가 있을 수 있으므로 `source_spec_legal_basis`를 별도로 보존합니다.

## Disclaimer

본 프로젝트의 Rule 결과는 **입력상 기계판독 가능한 요건의 확인 여부**를 나타냅니다. GREEN은 전체 법적 준수 인증이 아니며 RED 역시 법 위반 확정을 의미하지 않습니다. 최종 법적 판단은 별도의 사람 검토가 필요합니다.
