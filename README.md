<div align="center">

# 온톨로지 기반 개인정보보호 컴플라이언스 AX 체계 구축

**PIPA-DPV Compliance**

PIPA 온톨로지 · Fact Schema · Rule Profile · Rule Engine · 근거 추적

</div>

---

## 📌 프로젝트 개요

- **프로젝트명**: PIPA-DPV Compliance
- **프로젝트 형태**: 「2026 정보보호 정책제안 공모전」 정책제안 연계 PoC
- **프로젝트 목표**: 개인정보보호 컴플라이언스 업무의 반복적인 사전 검토 지원
- **핵심 구조**: Fact 추출·구조화 → PIPA 온톨로지 매핑 → Rule Engine 검토 → 결과·근거 제공
- **활용 범위**: 개인정보처리방침 점검, 개인정보 침해사고 통지 검토, Privacy-by-Design 개발지원
- **판단 원칙**: 추가 검토 필요 항목 선별 및 근거 제시, 최종 법적 판단은 담당자 수행

## ⚡ 주요 기능

- **Fact·Evidence 추출**: LLM을 활용한 비정형 문서의 개인정보 처리현황 및 원문 근거 구조화
- **Fact Schema 검증**: Fact 값·확인상태·출처·근거의 공통 형식 검증
- **PIPA 온톨로지**: 개인정보처리자·처리행위·처리목적·개인정보 항목·법적 근거 간 관계 표현
- **Rule Profile**: 검토요건별 적용대상·필수 Fact·온톨로지 항목·법적 근거·버전 정의
- **Rule Engine**: 사전 정의된 조건에 따른 검토 상태 분류
- **근거 추적**: 검토 결과와 Fact·원문 근거·법적 근거·판정사유 연결
- **웹 화면**: 입력자료 제출 및 규칙별 검토 결과 확인

## 🧩 PoC 구현

| 구분 | 업무단계 | 입력자료 | 주요 검토내용 |
| --- | --- | --- | --- |
| **PoC 1 · 개인정보처리방침 점검** | 운영·관리 | 개인정보처리방침 | 처리행위별 목적, 보유기간, 제3자 제공, 처리위탁 등 기재사항 |
| **PoC 2 · 개인정보 침해사고 통지 검토** | 사고·대응 | 사고기록·통지문 | 사고내용과 통지내용의 일치 여부, 필수 통지사항 |
| **PoC 3 · Privacy-by-Design 개발지원** | 기획·설계 | 개발·설계정보 | 법적 근거, 수집항목, 보유·파기, 처리위탁 등 설계요건 |

- **PoC 1·2**: LLM 기반 Fact·Evidence 추출
- **PoC 3**: 구조화된 입력정보를 Fact로 변환, LLM 미사용
- **공통 검토**: Fact Schema·PIPA 온톨로지·Rule Engine 활용

### 구현 범위

| 구분 | Fact | Rule |
| --- | ---: | ---: |
| PoC 1 | 12개 | 6개 |
| PoC 2 | 10개 | 4개 |
| PoC 3 | 13개 | 8개 |
| **합계** | **35개** | **18개** |

- **PIPA 온톨로지 구성**: 클래스 37개, 객체속성 23개, 데이터속성 17개, 법조문 개체 24개
- **온톨로지 구현**: DPV 참고, 국내 개인정보 보호법의 규율 구조 반영, OWL 2·RDF 활용

## 🏗️ 시스템 아키텍처

```text
PoC 1 · 개인정보처리방침 ──┐
                          ├── LLM Fact·Evidence 추출 ──┐
PoC 2 · 사고기록·통지문 ───┘                             │
                                                        ├── Fact Schema 검증
PoC 3 · 개발·설계정보 ─────── 구조화 입력 → Fact 생성 ────┘          │
                                                                   ▼
                                                         PIPA 온톨로지 매핑
                                                                   │
                                                                   ▼
                                                               Rule Engine
                                                                   │
                                                                   ▼
                                                      검토 결과 · 근거 · 판정사유
                                                                   │
                                                                   ▼
                                                            FastAPI · React
```

### Rule 판정상태

| 상태 | 의미 |
| --- | --- |
| `GREEN` | 해당 Rule에서 요구하는 정보 또는 조건 확인 |
| `YELLOW` | 정보 불명확 또는 추가 확인 필요 |
| `RED` | 필요한 정보 또는 조건 미충족 |
| `N/A` | 해당 Rule의 전제가 되는 처리행위 부재 확인 |

- **확인상태**: `confirmed`(확인됨), `unknown`(불명확), `absent`(없음)
- **N/A 적용**: 처리행위 자체의 부재가 확인된 경우로 한정
- **결과 성격**: 검토 우선순위 설정을 위한 참고정보, 법 위반 여부의 확정 판정 아님

## 🎬 시연 영상


## 🛠️ 기술 스택

| 분류 | 기술 | 용도 |
| --- | --- | --- |
| Frontend | React, TypeScript, Vite | 입력 화면 및 결과 시각화 |
| Backend | Python 3.10, FastAPI | API 및 검토 파이프라인 |
| LLM | Anthropic Claude API | PoC 1·2 Fact·Evidence 추출 |
| Ontology | OWL 2, RDF, Protégé | 개인정보보호 지식 구조화 |
| Rule | Fact Schema, Rule Profile, Rule Engine | 입력 검증 및 규칙 기반 검토 |
| Testing | pytest, npm build/lint | 코드 검증 |

## 🚀 실행 방법

### 실행 환경

- **필수 프로그램**: Git, Python 3.10, Node.js 및 npm
- **기본 실행 모드**: API 키가 필요 없는 Mock 모드
- **Mock 모드 특징**: 입력문서 분석 대신 사전 정의된 테스트 Fact 사용

### 1. 저장소 다운로드

```bash
git clone https://github.com/ddinii/pipa-dpv-compliance.git
cd pipa-dpv-compliance
```

### 2. 의존성 설치

**macOS**

```bash
python3.10 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cd frontend
npm install
cd ..
```

**Windows PowerShell**

```powershell
py -3.10 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
cd frontend
npm install
cd ..
```

### 3. Mock 모드 실행

- **macOS**: `bash start.sh`
- **Windows PowerShell**: `.\start.ps1`
- **웹 화면**: <http://localhost:5173>
- **백엔드 확인**: <http://127.0.0.1:8000/health>
- **API 문서**: <http://127.0.0.1:8000/docs>
- **실행 종료**: 실행 중인 터미널에서 `Ctrl + C`

### 4. Claude API 연결 (선택)

- **적용 대상**: PoC 1·2의 실제 입력문서 기반 Fact 추출
- **준비사항**: Anthropic API 키, API 사용 비용 발생 가능
- **필수 환경변수**: `PIPA_EXTRACTOR=llm`, `ANTHROPIC_API_KEY`
- **설정 위치**: 백엔드 실행 터미널, 서버 재실행 필요
- **유의사항**: 백엔드 `.env` 자동 로드 미지원, 공개 저장소·로그에 API 키 노출 금지

**macOS**

```bash
export PIPA_EXTRACTOR=llm
read -s "ANTHROPIC_API_KEY?Anthropic API Key: "
export ANTHROPIC_API_KEY
printf '\n'
bash start.sh
```

**Windows PowerShell**

```powershell
$env:PIPA_EXTRACTOR = "llm"
$secureKey = Read-Host "Anthropic API Key" -AsSecureString
$env:ANTHROPIC_API_KEY = [System.Net.NetworkCredential]::new("", $secureKey).Password
Remove-Variable secureKey
.\start.ps1
```

## 🔌 API

| Method | Endpoint | 기능 |
| --- | --- | --- |
| `GET` | `/health` | 서버 상태 확인 |
| `POST` | `/api/v1/compliance/policy-check` | 개인정보처리방침 점검 |
| `POST` | `/api/v1/compliance/breach-check` | 개인정보 침해사고 통지 검토 |
| `POST` | `/api/v1/compliance/design-check` | Privacy-by-Design 개발지원 |

## 📁 프로젝트 구조

```text
pipa-dpv-compliance/
├── app/
│   ├── main.py                  # FastAPI 진입점
│   ├── api/compliance.py        # PoC API
│   ├── mapping/                 # Fact Schema 및 온톨로지 매핑
│   └── rules/                   # Rule Engine 및 결과 모델
├── frontend/                    # React 웹 화면
├── docs/                        # 설계·규칙·계약 문서
├── evals/                       # Fact 추출 평가 자료
├── requirements.txt             # Python 의존성
└── README.md
```

## 📚 기술 문서 및 검증

- **프로젝트 개요**: [PROJECT.md](docs/context/core/PROJECT.md)
- **파이프라인 구조**: [PIPELINE.md](docs/context/core/PIPELINE.md)
- **Fact·RuleResult 계약**: [CONTRACTS.md](docs/context/core/CONTRACTS.md)
- **Fact 추출 평가**: [evals/README.md](evals/README.md)
- **평가 결과**: [evals/RESULTS.md](evals/RESULTS.md)
- **백엔드 테스트**: `python -m pytest -q`
- **프론트엔드 검증**: `cd frontend` → `npm run build` / `npm run lint`

## ⚖️ 적용 범위 및 한계

- **적용 범위**: 세 가지 PoC의 선정된 검토항목, 개인정보 보호법 전체의 자동 검토 아님
- **PoC 2**: 신고·통지 의무 발생 여부의 모든 법정 기준에 대한 자동 판정 미지원
- **LLM 추출**: 문서·모델에 따른 추출 품질 차이 및 원문 근거 확인 필요
- **Mock 모드**: 처리 흐름 확인용, 실제 문서 분석 성능 검증과 구분
- **개인정보보호**: 테스트 시 가상·비식별 예시 데이터 사용

---

<div align="center">

**PIPA-DPV Compliance**

개인정보보호 컴플라이언스 업무의 사전 검토를 위한 근거 중심 AX 프로토타입

</div>
