# N/A Presence State 변경 묶음

작성일: 2026-09-27

## 결과

- N/A가 실제 필요한 핵심 Rule을 P1-R03, P1-R06, P2-R02, P2-R03,
  P3-R11의 5개로 확정함.
- property 부재와 activity 자체 부재를 별도 계약으로 구현함.
- 신규 Frozen Fact와 core ontology term은 추가하지 않아 v1.0을 유지함.
- Mock Extractor/Form → Mapper → Rule Engine 실제 서비스 경로로 회귀 검증함.
- SHACL은 `ontology/PIPA_Process_Centered_SHACL_v1.0.ttl`만 원본으로 유지함.

## 변경 파일

### 실행 코드

- `app/extractors/base.py`
- `app/mapping/ontology_mapper.py`
- `app/mapping/presence_metadata.py` (신규)
- `app/rules/engine.py`
- `app/services/compliance.py`

### Ontology/SHACL

- `ontology/PIPA_Ontology_v1.0.ttl`
- `ontology/PIPA_Process_Centered_SHACL_v1.0.ttl`
- `tests/PIPA_Process_Centered_SHACL_v1.0.ttl` (삭제)

### 테스트

- `tests/test_activity_presence_pipeline.py` (신규)
- `tests/test_p0_rule_engine_v2.py`
- `tests/validate_final_scenarios.py`

### 계약/명세

- `docs/FACT_ONTOLOGY_MAPPING_SPEC.md`
- `docs/P0_RULE_MATRIX.md`
- `docs/README_Fact_Ontology_Mapping.md`
- `docs/VALIDATION_AUDIT_20260927.md`
- `docs/context/core/CONTRACTS.md`
- `docs/context/poc1/FACTS.md`
- `docs/context/poc2/FACTS.md`
- `docs/context/poc3/REQUIREMENTS.md`
- `docs/context/backend/EXTRACTOR_DECISIONS.md`
- `docs/context/backend/EXTRACTOR_INTEGRATION.md`
- `docs/context/backend/LLM_EXTRACTOR_HANDOFF.md`
- `docs/context/backend/N_A_FACT_DECISION_REQUIRED.md` (신규)

## 검증 명령

Windows CMD에서 저장소 루트로 이동한 뒤 실행함.

```bat
python -m pip install -r requirements.txt
python -m pytest -q
python run_tests.py
python tests\validate_final_scenarios.py
cd frontend
npm install
npm run lint
npm run build
cd ..
```

검증 당시 결과는 Python 144 tests PASS, 매핑 테스트 PASS, 세 시나리오 SHACL
PASS, frontend lint/build PASS임. `StarletteDeprecationWarning` 1건은 테스트 실패가
아니며 이번 N/A 변경과 무관함.

## Git 반영 예시

```bat
git status
git add app docs ontology tests
git status
git commit -m "fix: implement activity presence metadata for N/A rules"
git push origin main
```

main 직접 push 권한이나 branch protection에 막히면 feature branch에 push한 뒤 PR을
생성해야 함.

## 팀 확인 사항

Rule 정의 담당자는 5개 Rule의 applicability와 P2-R01 RED 유지 여부를 승인해야 함.
Rule Engine 담당자는 `MappingResult.system_metadata.activity_presence` 입력 계약과
안정적 metadata namespace 사용을 승인해야 함. 실제 승인을 받기 전에는
`N_A_FACT_DECISION_REQUIRED.md`의 상태를 승인 완료로 바꾸지 않음.
