# 추가 규칙: P1-R12 / P2-R10

2026-10-30 구현 / Fact Schema `fact-1.0` / Rule Profile `1.2` / Ontology `1.2`

## P1-R12: 자동수집장치 설치·운영 및 거부 방법

- 법적 근거: 개인정보 보호법 제30조 제1항 제7호.
- 필요한 Fact: `F1-23` (자동수집장치 사용 여부), `F1-24` (설치·운영 설명), `F1-25` (거부 방법).
- 대상: `PersonalInformationController` 문서 범위. 기존 PoC1의 권리 추출 Pass에 포함.
- 결과: 사용+둘 모두 기재 **GREEN**, 사용+명확한 누락 **RED**, 불확실/미추출 **YELLOW**, 명시적 미사용 **N/A**.
- SC-P01: 쿠키 사용(F1-23 confirmed), 나머지 기재 없음 → **RED**.

## P2-R10: 피해 신고 접수 담당부서 및 연락처

- 법적 근거: 개인정보 보호법 제34조 제1항 제5호.
- 필요한 Fact: `F2-11` (담당부서), `F2-12` (연락처).
- 대상: `NotificationNotice` 통지문. PoC2 통지문 추출 Pass에 포함.
- 결과: 모두 확인 **GREEN**, 누락 확인 **RED**, 애매/미추출 **YELLOW**, 통지문 명시적 부재 **N/A**.
- SC-P02: “개인정보보호 담당부서 연락처를 통하여 문의”라는 문장만 있고 구체 연락처가 없어 두 Fact를 unknown으로 둠 → **YELLOW**.

**주의:** 기존 PoC2의 `F2-10` 대응조치는 통지문 연락처를 증명하지 않는다. 두 문서의 Fact를 섞지 말 것. GREEN/RED는 문서 기재 확인 결과이며 최종 위법/적법 판단이 아니다.

## 변경 위치

- `app/extractors/poc1.py`, `app/extractors/poc2.py`: 신규 Fact ID 추출 및 상태 관리
- `app/extractors/prompts.py`, `app/extractors/prompts_poc2.py`: 추출 프롬프트
- `app/mapping/{mapping_registry,fact_schema,ontology_mapper}.py`: 계약 및 RDF 매핑
- `ontology/PIPA_Ontology_v1.0.ttl`: 신규 속성 (파일명은 이전 이름 유지, 내부 버전 1.2)
- `rules/p0_rules.json` / `app/rules/engine.py`: 규칙 정의, 판정
- `frontend/src/utils/complianceLabels.ts`: 화면 규칙 이름
- `evals/poc1`, `evals/poc2`, `tests/`: gold·variants·held-out·회귀 테스트

## 확인 명령

```powershell
py -m pip install -r requirements.txt
py -m pytest -q tests/test_p1_r12_auto_collection.py tests/test_p2_r10_damage_contact.py
py -m pytest -q
```

2026-10-30 개발 컨테이너 검증: `598 passed, 2 failed, 9 errors` (실패/에러는 테스트 실행 환경에 `pyshacl`, `anthropic`이 없는 것과 관련됨). 로컬에서 의존성 설치 후 전체 테스트를 실행해야 함.
