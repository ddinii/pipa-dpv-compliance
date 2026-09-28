# PIPA-DPV 프론트엔드 MVP 적용·검증 가이드

## 반영 범위

- 메인 컬러를 `#5682B8`로 통일함.
- 기본 화면은 밝은 블루·화이트 배경으로 구성함.
- 운영체제 테마를 최초값으로 사용하고 상단 버튼으로 라이트·다크 모드를 전환할 수 있게 함.
- 사용자가 선택한 테마를 브라우저에 저장함.
- PoC1·PoC2·PoC3 탭과 모바일 레이아웃을 정리함.
- 세 PoC 모두 예제 불러오기와 입력 초기화 기능을 제공함.
- 결과 상단에 GREEN·AMBER·RED·N/A 집계를 표시함.
- 규칙별 확인 Fact·누락 Fact·불확실 Fact·근거를 접어서 확인할 수 있게 함.
- 법적 적법성이나 법 위반을 확정하는 결과가 아니라는 안내를 표시함.
- PoC3의 제3자 제공·국외이전 상태 입력은 고급 시나리오 메타데이터로 분리함.

## 실행 방법

저장소 루트에서 백엔드를 실행함.

```bat
python -m uvicorn app.main:app --reload --port 8000
```

새 CMD를 열고 프론트엔드를 실행함.

```bat
cd /d C:\Users\jh052\Downloads\온톨로지\pipa-repo\frontend
npm install
npm run dev
```

브라우저에서 `http://localhost:5173`을 열어 확인함.

## 제출 전 자동검사

```bat
cd /d C:\Users\jh052\Downloads\온톨로지\pipa-repo\frontend
npm run lint
npm run build

cd /d C:\Users\jh052\Downloads\온톨로지\pipa-repo
python run_tests.py
```

## 화면별 수동검사

### PoC1

1. `MoaMarket 예제 불러오기`를 누름.
2. 분석 ID, 개인정보처리자명, 처리방침 원문이 채워지는지 확인함.
3. `처리방침 검토하기`를 누름.
4. 결과 수가 6개인지 확인함.
5. 각 결과에서 Fact 상세와 근거를 펼쳐볼 수 있는지 확인함.

### PoC2

1. `침해사고·통지문 예제 불러오기`를 누름.
2. 사고 사실과 통지문이 서로 다른 입력칸에 채워지는지 확인함.
3. `통지 요건 검토하기`를 누름.
4. 결과 수가 4개인지 확인함.
5. 실제 사고 Fact와 통지문 Fact가 섞이지 않는지 확인함.

### PoC3

1. `CampusMate 예제 불러오기`를 누름.
2. 수집·이용 활동 3개와 수탁 처리 2개가 생성되는지 확인함.
3. `설계 검토하기`를 누름.
4. 결과 수가 8개인지 확인함.
5. `고급 시나리오 메타데이터`를 펼치면 제3자 제공·국외이전의 명시적 부재가 표시되는지 확인함.

## 통합 시 주의사항

- 이 패치는 `frontend/`와 본 가이드만 변경함. Rule Engine, Mapper, Ontology, SHACL 파일을 변경하지 않음.
- 실제 결과 상태는 백엔드가 반환한 `rule_results`를 그대로 표시함.
- N/A가 보이려면 Extractor/Form → Mapper → Rule Engine의 실제 경로에서 presence state 계약이 적용되어야 함.
- 실제 LLM Extractor가 연결되기 전에는 팀이 구현한 mock 또는 현재 API 동작에 따라 결과가 달라질 수 있음.
