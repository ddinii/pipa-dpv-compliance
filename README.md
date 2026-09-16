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

### P2-R01 ontology compatibility

v1.0 Rule Specification은 `NotificationObligation / triggersNotificationObligation`을 참조하지만 frozen `PIPA_Ontology_v1.0.ttl`에는 해당 term이 없습니다.

따라서 현재 엔진은 ontology를 임의 변경하지 않고 `DataBreachIncident + affectsPersonalInformation`을 compatibility signal로 사용하며, 결과의 `implementation_notes`에 이 차이를 남깁니다.

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
