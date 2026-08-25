# PIPA-DPV Compliance PoC

> W3C DPV 기반 한국 개인정보보호법 기계판독 규칙체계 및 국가 Privacy Compliance API — 공모전 PoC

개인정보 처리방침을 자동으로 점검하는 프로토타입입니다. LLM으로 처리방침에서
필수 기재사항을 추출하고, 온톨로지(PIPA-DPV)에 매핑한 뒤, 규칙 엔진으로
**GREEN(적합) / RED(누락) / AMBER(사람 검토 필요)** 3단계 판정을 내립니다.

```
처리방침(자연어)
    │
    ▼
[LLM 추출]  ──── 읽는 역할
    │
    ▼
[PIPA-DPV 온톨로지]  ──── 법률 개념과 연결
    │
    ▼
[Rule Engine]  ──── 명시적 규칙으로 검사
    │
    ▼
GREEN / RED / AMBER + 근거조문
```

## 프로젝트 구조

```
backend/
  models.py            데이터 모델 (Fact 구조)
  extraction/           LLM 정보추출 (Mock / Claude)
  rules/rule_engine.py   10개 규칙 + 판정 로직
  main.py                FastAPI 서버
ontology/
  pipa_dpv_classes.ttl   Protégé 호환 온톨로지 (1계층)
frontend/
  app.py                 Streamlit 데모 UI
data/
  sample_policies/        테스트용 샘플 처리방침
  gold_standard/           평가용 정답 라벨(전문가 작성 필요)
evaluation/
  evaluate.py              Model A vs Model B 비교 스크립트
tests/                     pytest 단위 테스트
```

## 빠른 시작

### 1. 환경 설정

```bash
git clone <repo-url>
cd pipa-dpv-compliance
python -m venv .venv
source .venv/bin/activate   # Windows는 .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

`.env` 파일에 `ANTHROPIC_API_KEY`를 넣으면 실제 Claude로 추출하고,
비워두면 자동으로 `MockExtractor`(키워드 기반, API 키 불필요)가 동작합니다.
**팀원들은 API 키 없이도 바로 개발/테스트를 시작할 수 있습니다.**

### 2. 백엔드 실행

```bash
uvicorn backend.main:app --reload --port 8000
```

- API 문서: http://localhost:8000/docs (Swagger UI 자동 생성)
- 헬스체크: http://localhost:8000/health

### 3. 프론트엔드 실행 (별도 터미널)

```bash
streamlit run frontend/app.py
```

http://localhost:8501 에서 샘플 처리방침을 불러오거나 직접 붙여넣고 점검할 수 있습니다.

### 4. 테스트 실행

```bash
pytest
```

### 5. 평가(Model A vs Model B) 실행

```bash
python -m evaluation.evaluate
```

`data/gold_standard/gold_labels_template.csv` 에 전문가 라벨을 채운 뒤 실행하면,
Rule Engine 판정이 사람 판단과 얼마나 일치하는지 확인할 수 있습니다.

## 온톨로지 편집 (Protégé)

1. [Protégé](https://protege.stanford.edu/) 설치
2. `ontology/pipa_dpv_classes.ttl` 파일 열기
3. Class/Property/Individual 추가 후 저장 → git commit

## 현재 PoC 범위

- ✅ 개인정보 처리방침 필수 기재사항 10개 규칙
- ✅ GREEN/RED/AMBER 3단계 판정 + 근거조문 추적
- ✅ LLM + 온톨로지 + Rule Engine 아키텍처 검증용 최소 구현
- ❌ 전체 개인정보 보호법 커버리지 (범위 밖)
- ❌ 유출신고 판단, PIA 사전점검 등 확장 유즈케이스 (구조는 동일, 로드맵으로만 제시)

## ⚠️ 중요 — 팀원 필수 확인 사항

- `rule_engine.py`, `pipa_dpv_classes.ttl` 안의 `legal_basis`(조문 번호)는
  **placeholder**입니다. 반드시 최신 개인정보 보호법 조문과 대조 후 수정하세요.
- 본 도구의 GREEN 판정은 "법적 적법성 확정"이 아닙니다. 모든 응답에
  disclaimer가 포함되도록 설계되어 있습니다 — 임의로 제거하지 마세요.
- 실제 기업 처리방침 원본은 저작권/개인정보 이슈가 있을 수 있으니
  git에 커밋하지 말고(`.gitignore`에 `data/raw_policies/` 이미 등록됨)
  팀 공유 드라이브 등 별도 채널을 사용하세요.

## 협업 방법

[CONTRIBUTING.md](./CONTRIBUTING.md) 를 참고하세요 — 브랜치 전략, 역할 분담,
커밋 컨벤션이 정리되어 있습니다.
