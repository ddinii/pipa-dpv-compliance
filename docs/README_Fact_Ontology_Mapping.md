# PIPA Fact → Ontology Mapping v1.0

이 패키지는 기존의 수작업 시나리오 TTL과 Rule Engine 사이에 빠져 있던 다음 계층을 구현한다.

```text
입력/Form → Fact 생성 → Fact Envelope 검증 → RDF 매핑 → SHACL → Rule Engine
```

`SC-P01_FINAL_Protege.ttl` 같은 기존 파일은 매핑 결과의 골든 데이터로 유지한다. 이 패키지는 런타임 입력으로부터 같은 처리행위 중심 구조의 RDF를 자동 생성한다.

## 구현 범위

- 공통 Fact Envelope `fact-1.0` 검증
- F1-01~F1-12 매핑
- F2-01~F2-10 매핑
- F3-01~F3-13 매핑
- PoC3 구조화 Form → Fact Builder(D01-007)
- 동일 `activity_id` Fact의 동일 처리행위 귀속
- 처리행위별 개인정보 Individual 분리
- `confirmed/unknown/absent` 구분
- PoC2 사고 사실/통지문 Fact 분리
- 시스템 메타데이터와 RDF Ontology assertion 분리
- 기존 SHACL 구조 검증

## 디렉터리

```text
app/
├─ builders/
│  └─ poc3_fact_builder.py
└─ mapping/
   ├─ fact_schema.py
   ├─ mapping_registry.py
   └─ ontology_mapper.py
schemas/
└─ fact-envelope.schema.json
examples/
└─ SC-D01_form.json
ontology/
├─ PIPA_Ontology_v1.0.ttl
└─ PIPA_Process_Centered_SHACL_v1.0.ttl
tests/
└─ test_fact_ontology_mapping.py
run_mapping_demo.py
run_tests.py
run_tests_windows.bat
```

## Windows에서 확인

압축을 풀고 `run_tests_windows.bat`을 더블클릭한다. 필요한 Python 모듈 설치, 자동 테스트, PoC3 매핑 예제 실행이 순서대로 진행된다.

정상 결과:

```text
FINAL: FACT-TO-ONTOLOGY MAPPING TESTS PASSED
SUCCESS: Fact-to-Ontology mapping is valid.
```

직접 실행하려면:

```powershell
py -m pip install -r requirements.txt
py run_tests.py
```

## 생성 결과

예제 실행 후 `generated/`에 다음 파일이 생성된다.

- `SC-D01_facts.json`: 구조화 Form에서 생성한 Fact Envelope
- `SC-D01_mapped.ttl`: Fact에서 자동 생성한 RDF
- `SC-D01_system_metadata.json`: Rule Engine용 비온톨로지 메타데이터

현재 SC-D01 예제는 다음을 생성한다.

- Fact 43개
- RDF triple 122개
- 위탁업무 시스템 메타데이터 2개

## 백엔드 연결 예시

```python
from app.builders import build_poc3_facts
from app.mapping import OntologyMapper

facts = build_poc3_facts(form_payload)

mapping = OntologyMapper(
    analysis_id=form_payload["analysis_id"],
    controller_id=form_payload["controller"]["controller_id"],
    controller_name=form_payload["controller"]["name"],
).map(facts)

# Rule Engine에 세 입력을 함께 전달한다.
rdf_graph = mapping.graph
normalized_facts = mapping.facts
system_metadata = mapping.system_metadata
```

Rule Engine 호출부는 팀 저장소의 실제 메서드명에 맞게 연결한다. 중요한 계약은 `graph + facts + system_metadata` 세 묶음을 유지하는 것이다.

## 매핑 원칙

### 처리행위 중심

동일 `activity_id`의 목적·항목·법적근거·보유정보는 하나의 ProcessingActivity에 연결된다. 서로 다른 `activity_id`는 같은 이메일 항목이라도 서로 다른 PersonalInformation Individual을 사용한다.

### ObjectProperty 값

다음처럼 문자열을 바로 연결하지 않는다.

```turtle
inst:activity pipa:hasPurpose "회원 관리" .
```

대신 목적 Individual을 생성한다.

```turtle
inst:activity pipa:hasPurpose inst:purpose-001 .
inst:purpose-001 a pipa:ProcessingPurpose ;
    pipa:hasPurposeDescription "회원 관리" .
```

### 값 상태

- `confirmed`: RDF assertion 생성
- `unknown`: RDF를 생성하지 않고 Fact 상태 유지 → Rule의 AMBER 판단에 사용
- `absent`: RDF를 생성하지 않고 명시적 부재 Fact 유지 → Rule의 RED/AMBER 판단에 사용

OWL/RDF의 Open World Assumption 때문에 triple이 없다는 사실만으로 `absent`로 판단하면 안 된다.

### 시스템 메타데이터

다음 값은 `ontology_property`로 사용하지 않는다.

- `notice_incident_time`
- `measure_role`
- `entrusted_task_text`

이 값들은 `MappingResult.system_metadata`와 `generated/SC-D01_system_metadata.json`에 보관한다. 따라서 실제 사고시점 `incidentDate`와 통지문 기재시점 `notice_incident_time`이 합쳐지지 않는다.

### 네임스페이스

온톨로지 Class/Property는 다음 네임스페이스만 허용한다.

```text
https://w3id.org/pipa-compliance/ontology#
```

기존 legacy 값인 `https://example.org/pipa-dpv#`가 들어오면 검증 오류를 발생시킨다.

## 기존 코드에서 교체할 부분

기존 `processing_fact_to_graph()` 대신 `OntologyMapper.map()`을 호출한다.

기존처럼 수작업 TTL을 Rule Engine의 유일한 입력으로 사용하지 않는다.

```text
Extractor/Form
  ↓
Fact Envelope list
  ↓
OntologyMapper.map(facts)
  ├─ graph
  ├─ normalized facts
  └─ system metadata
  ↓
P0RuleEngine
```

## 테스트 내용

자동 테스트는 다음을 확인한다.

1. F1-01~F1-12가 모두 RDF 또는 시스템 메타데이터로 변환됨
2. 실제 사고 개인정보와 통지문 기재 개인정보 Individual이 분리됨
3. `notice_incident_time`과 `measure_role`이 RDF Property로 생성되지 않음
4. 같은 개인정보명도 다른 처리행위이면 다른 Individual로 생성됨
5. `unknown/absent`가 확정 RDF assertion으로 생성되지 않음
6. legacy namespace가 거부됨
7. PoC3 Form 결과가 기존 SHACL을 통과함

## 현재 남은 통합 작업

이 패키지는 A 담당 범위인 Fact 생성·검증·온톨로지 매핑까지 구현한다. 팀 저장소에서 마지막으로 필요한 작업은 다음 두 가지다.

1. API의 PoC1/PoC2 Extractor 출력과 이 매퍼의 Fact Envelope 연결
2. `P0RuleEngine` 호출부가 `graph`, `facts`, `system_metadata`를 받도록 연결

Rule Engine 조건과 API endpoint 자체는 B 담당 코드에서 연결해야 한다.

