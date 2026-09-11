# PIPA PoC Freeze v1.0 직접 검증 방법

## 파일 3개

1. `SC-P01_FINAL_Protege.ttl`: 모아마켓 개인정보 처리방침
2. `SC-P02_FINAL_Protege.ttl`: 사고 사실과 이미 작성된 통지문을 분리한 통지 요건 검토
3. `SC-D01_FINAL_Protege.ttl`: CampusMate Privacy-by-Design 구조화 설계

각 파일에는 PIPA 온톨로지 본체와 해당 시나리오 Individual이 함께 들어 있으므로 Protégé에서 바로 열 수 있다.

## Protégé에서 직접 확인

각 시나리오 파일에 대해 다음 과정을 반복한다.

1. Protégé에서 `File > Open`으로 TTL 파일을 연다.
2. `Entities > Classes`에서 클래스 계층이 표시되는지 확인한다.
3. `Individuals by class` 탭을 연다.
4. 시나리오의 Controller, ProcessingActivity, 개인정보, 목적, 수신자/수탁자 등이 Individual로 나타나는지 확인한다.
5. `Reasoner > HermiT > Start reasoner`를 실행한다.
6. 클래스 계층 표시를 `Asserted`에서 `Inferred`로 바꾼다.
7. 오류가 없고, `owl:Nothing` 아래에 프로젝트 Class가 나타나지 않으면 OWL 일관성 검사를 통과한 것이다.
8. 이 파일들은 테스트용이므로 원본 `PIPA_Ontology_v1.0.ttl` 위에 저장하지 않는다.

### SC-P01에서 볼 것

- `MoaCommerce` 아래 처리행위들이 분리되어야 한다.
- `SellerProvision`에만 입점 판매자·제공 항목·제공 목적이 연결되어야 한다.
- `CrossBorderCloud`에 미국이 연결되어야 하며 판매자 제공과 합쳐지면 안 된다.
- 위탁업체 네 곳이 각각 별도 `EntrustedProcessing` Individual이어야 한다.

### SC-P02에서 볼 것

- `Incident_B24`는 `DataBreachIncident`여야 한다.
- `Notice_B24`는 별도 `NotificationNotice`여야 한다.
- `Actual_EmailAddress`와 `Notice_EmailAddress`는 서로 다른 Individual이어야 한다.
- 실제 사고시점은 `incidentDate`, 통지문 기재시점은 `noticeIncidentTime`으로 분리되어야 한다.
- 대응정보는 `measureRole`에 따라 4개 Individual로 나뉘어야 한다.
- 신고 threshold, ReportingObligation, 통지문 자동생성, 정정 provenance가 없어야 한다.

### SC-D01에서 볼 것

- 계정·위치추천·관심분야추천이 서로 다른 `CollectionAndUse` Individual이어야 한다.
- 개인정보 항목별 `isRequired`와 `designRationale`이 보여야 한다.
- K-Cloud와 MessageLink가 각각 별도 위탁 활동이어야 한다.
- 보유 종료조건이 `triggersDestruction`으로 파기 활동과 연결되어야 한다.

## 자동 검사

가장 쉬운 방법은 `run_validation.bat`을 더블클릭하는 것이다. 필요한 `rdflib`, `pyshacl`을 설치한 뒤 검증을 실행한다.

PowerShell에서 직접 실행하려면 이 폴더로 이동하여 다음 명령을 사용한다.

```powershell
py -m pip install --user rdflib pyshacl
py .\validate_final_scenarios.py
```

모든 검사를 통과하면 마지막에 다음 문구가 나온다.

```text
FINAL: ALL AVAILABLE TESTS PASSED
```

이 검사는 세 TTL의 구문, SHACL 구조, 처리행위 분리, PoC2 사고/통지 분리 및 P0 Rule 입력 완전성을 확인한다. 실제 서비스 프로그램의 자연어 추출 정확도를 검증하려면 나중에 프로그램이 생성한 TTL을 이 세 기준 파일과 비교해야 한다.

## GitHub 배치

```text
ontology/
└─ PIPA_Ontology_v1.0.ttl

tests/
├─ fixtures/
│  ├─ SC-P01_FINAL_Protege.ttl
│  ├─ SC-P02_FINAL_Protege.ttl
│  └─ SC-D01_FINAL_Protege.ttl
├─ PIPA_Process_Centered_SHACL_v1.0.ttl
├─ validate_final_scenarios.py
└─ run_validation.bat
```

