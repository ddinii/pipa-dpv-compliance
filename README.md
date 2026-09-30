# PIPA-DPV Compliance Prototype

개인정보 보호법(PIPA) 준수 검토를 **기계가 읽을 수 있는 형태**로 구현한 프로토타입입니다.
입력은 고정된(Frozen) Fact 계약으로 구조화되고, 고정된 온톨로지에 매핑된 뒤,
**결정론적(deterministic) Rule Engine**이 규칙별 `GREEN` / `AMBER` / `RED` / `N/A`
`RuleResult`를 산출합니다.

> **`GREEN`은 법적 준수 인증이 아니며, `RED`는 확정적인 법 위반 판정이 아닙니다.**
> 결과는 규칙이 요구하는 Fact가 입력에서 확인되었는지, 누락되었는지, 불확실한지를
> 나타낼 뿐 최종 법적 판단이 아닙니다. 최종 법적 판단에는 사람의 검토가 필요합니다.
> LLM은 Fact 추출만 수행하며 Rule status 부여나 법적 판단은 하지 않습니다.

## 세 개의 PoC

세 PoC는 **동등한** 응용 시나리오이며 Main/Sub 구분이 없습니다.

| PoC | 시나리오 | 입력 | Fact 생성 방식 |
|---|---|---|---|
| **PoC1** | 개인정보 처리방침 준수점검 | 처리방침 텍스트 | LLM Fact 추출 |
| **PoC2** | 개인정보 침해사고 통지 요건 검토 지원 | 사고 기록 + 통지/대응 정보 | LLM Fact 추출 |
| **PoC3** | Privacy-by-Design 개발지원 | 구조화 form | `build_poc3_facts()` (LLM 미사용) |

```text
PoC1: 처리방침 텍스트          → LLM Fact 추출        → Frozen Facts → OntologyMapper → P0RuleEngine → RuleResult
PoC2: 사고 기록 / 통지문       → LLM Fact 추출        → Frozen Facts → OntologyMapper → P0RuleEngine → RuleResult
PoC3: 구조화 form              → build_poc3_facts()   → Frozen Facts → OntologyMapper → P0RuleEngine → RuleResult
```

- **PoC2**는 사고 기록과 통지문을 **별도 호출로 각각 추출**하며, 서로 다른 사실을 혼합하지 않습니다.
- **PoC3**는 설계상 LLM을 사용하지 않습니다. 구조화 form에서 Fact를 직접 만드는 것이 현재 설계이며 미완성 상태가 아닙니다.
- **PoC2 v1**은 `ReportingObligation`을 자동 판정하지 않습니다. 시행령의 1,000명 / 72시간 등
  신고·통지 threshold 자동 판정은 현재 P0 범위 밖입니다.

## 아키텍처

```text
Input
  → Fact                        (fact-1.0 envelope)
  → Fact Schema Validation      (app/mapping/fact_schema.py)
  → RDF / Ontology Mapping      (app/mapping/ontology_mapper.py — OntologyMapper)
  → P0 Rule Engine              (app/rules/engine.py — P0RuleEngine, 결정론적)
  → RuleResult                  (app/rules/models.py)
  → REST API                    (FastAPI, app/api/compliance.py)
  → UI                          (React, frontend/src)
```

- REST API는 **FastAPI**(`app/main.py`) 단일 애플리케이션입니다. 별도의 두 번째 백엔드는 없습니다.
- **Fact 계약**, 온톨로지 매핑(`app/mapping/mapping_registry.py`의 `FACT_SPECS`), P0 규칙 집합은
  고정(Frozen)되어 있으며, API와 UI는 특정 LLM 구현이 아니라 이 안정된 계약에 의존합니다.
- 모든 Fact의 `value_state`는 **`confirmed` / `unknown` / `absent`** 중 하나이며 서로 의미를
  변환하지 않습니다(예: `unknown` → `absent` 금지). 누락되었거나 추출되지 않은 정보는 자동으로 `N/A`가 아닙니다.
- `GREEN` / `AMBER` / `RED` / `N/A` 판정은 오직 결정론적 `P0RuleEngine`만 수행합니다.
- 활동(`activity_id`) 단위의 process-centered 그룹핑과 Evidence / provenance를 보존합니다.

## Frozen 범위

| PoC | Facts | P0 Rules |
|---|---|---|
| PoC1 | 12 (F1-01 ~ F1-12) | 6 (P1-R01, P1-R02, P1-R03, P1-R04, P1-R06, P1-R07) |
| PoC2 | 10 (F2-01 ~ F2-10) | 4 (P2-R01, P2-R02, P2-R03, P2-R08) |
| PoC3 | 13 (F3-01 ~ F3-13) | 8 (P3-R01, P3-R02, P3-R03, P3-R04, P3-R05, P3-R06, P3-R08, P3-R11) |
| **합계** | **35 Facts** | **18 P0 Rules** |

Fact Dictionary와 Rule 명세 전문은 이 README에 복제하지 않습니다.
[`docs/context/core/CONTRACTS.md`](docs/context/core/CONTRACTS.md)(Fact envelope, RuleResult 계약)와
[`docs/P0_RULE_MATRIX.md`](docs/P0_RULE_MATRIX.md)(규칙별 요약)를 참고하세요.

## Extractor 구성

PoC1/PoC2에는 실제 Claude LLM extractor가 구현되어 있으며, 환경변수 `PIPA_EXTRACTOR`로 선택합니다.

| `PIPA_EXTRACTOR` | PoC1 | PoC2 | 특징 |
|---|---|---|---|
| `mock` (기본) | `MockPoC1Extractor` | `MockPoc2Extractor` | 고정 synthetic scenario, API 호출·비용 없음 |
| `llm` | `LlmPoC1Extractor` | `LlmPoc2Extractor` | 실제 Claude API 호출, **요청당 과금** |

- Mock extractor는 입력 내용을 무시하고 항상 고정된 Fact 시나리오를 반환합니다.
  API·UI 파이프라인을 비용 없이 확인하는 용도입니다.
- 기본 LLM model은 `claude-sonnet-5`이며, `PIPA_EXTRACTOR_MODEL`로 바꿀 수 있습니다.
- LLM은 인용(quote)만 반환하고 offset은 코드가 원문에서 찾습니다. 찾지 못한 인용의 Fact는 버립니다.

## 설치

Python 3.10이 필요합니다.

```bash
python3.10 -m venv .venv
source .venv/bin/activate        # Windows: .\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

프론트엔드 의존성:

```bash
cd frontend
npm install
```

## 환경변수

[`.env.example`](.env.example)을 기준으로 합니다. **저장소는 `.env`를 자동으로 load하지 않으므로**
shell 등 process environment에 직접 설정해야 합니다.

| 변수 | 설명 |
|---|---|
| `PIPA_EXTRACTOR` | `mock`(기본) 또는 `llm`. PoC1/PoC2 extractor 선택 |
| `ANTHROPIC_API_KEY` | `PIPA_EXTRACTOR=llm`일 때만 필요. Anthropic SDK가 직접 읽음 |
| `PIPA_EXTRACTOR_MODEL` | LLM model override. 미설정 시 `claude-sonnet-5` |

`.env.example`에는 `APP_ENV`, `APP_HOST`, `APP_PORT`, `FRONTEND_ORIGIN`도 있으나 현재 `app/main.py`가
시작 시 읽지 않는 placeholder입니다.

LLM 모드 실행 예시 (macOS/Linux):

```bash
export PIPA_EXTRACTOR=llm
export ANTHROPIC_API_KEY=<your-api-key>     # 실제 키는 코드/문서/커밋에 넣지 말 것
uvicorn app.main:app --reload
```

`llm` 모드에서 키가 없어도 서버는 시작되며, 실패는 첫 PoC1/PoC2 요청 시점에 나타납니다.
따라서 PoC3와 다른 endpoint는 계속 동작합니다.

프론트엔드는 `frontend/.env.example`을 `frontend/.env`로 복사해 백엔드 주소를 바꿀 수 있습니다.

```text
VITE_API_BASE_URL=http://127.0.0.1:8000
```

`.env` 파일은 커밋하지 말고, 실제 secret은 런타임 환경변수로만 제공하세요.

## 실행

백엔드 (저장소 루트, 가상환경 활성화 후):

```bash
uvicorn app.main:app --reload
```

- API: `http://127.0.0.1:8000`
- Swagger UI: `http://127.0.0.1:8000/docs`

프론트엔드:

```bash
cd frontend
npm run dev
```

- 개발 서버: `http://localhost:5173` (백엔드 CORS가 이 origin을 허용)
- `VITE_API_BASE_URL`이 없으면 `http://127.0.0.1:8000`을 사용합니다 (`frontend/src/api/client.ts`).
- 세 PoC 화면은 동일한 `RuleResult` 컴포넌트로 결과를 렌더링합니다 (`frontend/src/pages`).

## API

현재 3-PoC compliance pipeline (`app/api/compliance.py`, prefix `/api/v1/compliance`):

| Method | Path | PoC |
|---|---|---|
| `POST` | `/api/v1/compliance/policy-check` | PoC1 |
| `POST` | `/api/v1/compliance/breach-check` | PoC2 |
| `POST` | `/api/v1/compliance/design-check` | PoC3 |
| `GET` | `/health` | 헬스 체크 |

세 compliance endpoint는 같은 응답 envelope를 사용합니다.

```text
{
  "analysis_id": ...,
  "poc": "PoC1" | "PoC2" | "PoC3",
  "ontology_version": ...,
  "rule_version": ...,
  "fact_schema_version": ...,
  "results": [ ...RuleResult... ]
}
```

`results`의 각 항목은 `RuleResult.to_dict()`(`app/rules/models.py`)를 따릅니다.

**Legacy endpoint** (`app/api/validate.py`, prefix `/api/v1`): `POST /api/v1/validate`는
`ProcessingFact` → SHACL 검증의 이전 prototype(`app/services/validator.py`,
`rules/article17_consent.ttl`)입니다. 호환을 위해 남겨 두었지만 현재 3-PoC
Fact / OntologyMapper / P0RuleEngine pipeline과는 **별개**이며 compliance endpoint와 동등하지 않습니다.

## 테스트

백엔드 (표준 명령):

```bash
python -m pytest -q
```

프론트엔드 (`frontend/`에서):

```bash
npm run build   # tsc -b && vite build
npm run lint    # oxlint
```

## Extractor 평가 세트 (`evals/`)

PoC1/PoC2 LLM Fact Extractor의 gold Fact set, controlled variants, 채점기는 `evals/`에 있습니다.
구성과 실행 방법은 [`evals/README.md`](evals/README.md), 결과는 [`evals/RESULTS.md`](evals/RESULTS.md)를 참고하세요.

```bash
python evals/poc1/build_gold_facts.py
python evals/poc1/build_variants.py
python -m pytest -q tests/test_gold_facts_poc1.py tests/test_variants_poc1.py
```

`evals/run_extraction.py`는 **실제 Claude API를 호출하므로 비용이 발생**하며 일반 test suite에 포함되지 않습니다.

## 해석상 주의

- `GREEN`은 법적 준수 인증이 아닙니다.
- `RED`는 확정적인 법 위반 판정이 아닙니다.
- PoC2 v1은 `ReportingObligation`을 자동 판정하지 않습니다.
- 시행령의 신고·통지 threshold(예: 1,000명, 72시간)는 현재 P0 Rule 범위 밖입니다.
- 최종 법적 판단은 사람의 검토가 필요합니다.

## 참고 문서

- [`docs/context/INDEX.md`](docs/context/INDEX.md) — 작업별 context 색인
- [`docs/context/core/PROJECT.md`](docs/context/core/PROJECT.md),
  [`PIPELINE.md`](docs/context/core/PIPELINE.md),
  [`CONTRACTS.md`](docs/context/core/CONTRACTS.md) — 프로젝트 범위, pipeline, Frozen 계약
- [`docs/context/backend/EXISTING_CODE.md`](docs/context/backend/EXISTING_CODE.md) — 재사용 대상 백엔드 모듈
- [`docs/P0_RULE_MATRIX.md`](docs/P0_RULE_MATRIX.md) — 18개 P0 Rule 요약
- [`docs/context/backend/LLM_EXTRACTOR_HANDOFF.md`](docs/context/backend/LLM_EXTRACTOR_HANDOFF.md),
  [`EXTRACTOR_DECISIONS.md`](docs/context/backend/EXTRACTOR_DECISIONS.md) — extractor 연동 과정과 결정 기록(이력 문서)
