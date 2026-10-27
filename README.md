<div align="center">

# 온톨로지 기반 개인정보보호 컴플라이언스 AX 체계 구축

### PIPA-DPV Compliance

**LLM Fact·Evidence 추출 · PIPA 온톨로지 · Rule Profile · Rule Engine · 근거 추적**

[프로젝트 개요](#-프로젝트-개요) · [PoC 구현](#-poc-구현) · [실행 방법](#-실행-방법) · [기술 문서 및 검증](#-기술-문서-및-검증)

</div>

---

## 📌 프로젝트 개요

- **프로젝트명**: PIPA-DPV Compliance
- **프로젝트 형태**: 「2026 정보보호 정책제안 공모전」 정책제안 「온톨로지 기반 개인정보보호 컴플라이언스 AX 체계 구축」의 기술 실현 가능성 검증 PoC
- **추진 배경**: 개인정보처리방침·침해사고 통지문·서비스 설계정보의 반복적 법적 요건 검토 부담, 생성형 AI 단독 법적 판단의 일관성·근거 추적 한계
- **프로젝트 목표**: 개인정보 보호법(PIPA)의 주요 개념·관계를 온톨로지로 구조화하고, 사전 정의된 Rule을 통해 추가 검토 항목 및 근거 제시
- **활용 범위**: 개인정보처리방침 점검, 개인정보 침해사고 통지 검토, Privacy-by-Design 개발지원
- **판단 주체**: 시스템은 사전 검토 지원, 최종 법적 판단은 개인정보보호 담당자·전문가 수행

### 핵심 설계 원칙

| 원칙 | 구현 내용 |
| --- | --- |
| **AI와 판단 기준의 역할 분리** | LLM은 문서에서 Fact·Evidence 추출, Rule Engine은 검토 상태 산출 |
| **일관성** | 동일한 Fact에 동일한 규칙 적용 |
| **근거 추적** | 원문 근거, Fact, Rule, 법적 근거 및 판정사유 연결 |
| **불확실성 보존** | `confirmed`(확인됨), `unknown`(불명확), `absent`(없음) 구분 |
| **사람의 최종 검토** | 검토 우선순위 선별 지원, 법 위반 여부 확정 판정 제외 |

> **유의사항**: `GREEN`은 법적 준수 인증이 아니며, `RED`는 확정적 법 위반 판정이 아님. 개인정보 보호법 전체의 자동 법률 판단 시스템이 아닌 선정 항목 중심 PoC.

## ⚡ 주요 기능

- **Fact·Evidence 추출**: 비정형 문서의 개인정보 처리현황 및 원문 근거 구조화
- **Fact Schema 검증**: Fact 형식·값·확인상태·출처·근거 검증
- **PIPA 온톨로지 매핑**: 개인정보 처리행위와 관련 주체·항목·목적·법적 근거 연결
- **Rule Profile**: 적용대상, 필수 Fact, 온톨로지 항목, 법적 근거 및 버전 정의
- **Rule Engine**: 사전 정의된 검토조건에 따른 상태 분류 및 검토 우선순위 선별
- **근거 추적**: Fact·원문 근거·법적 근거·판정사유 확인
- **웹 화면**: PoC별 자료 입력, 규칙별 검토 결과 및 근거 표시

## 🧩 PoC 구현

세 가지 업무단계에 공통 Fact–PIPA 온톨로지–Rule 체계를 적용한 독립 검증 시나리오.

| 구분 | 업무단계 | 입력자료 | 검토 내용 | Fact 생성 |
| --- | --- | --- | --- | --- |
| **PoC 1 · 개인정보처리방침 점검** | 운영·관리 | 개인정보처리방침 텍스트 | 처리행위별 처리목적, 보유기간, 제3자 제공, 처리위탁 등 기재사항 | LLM |
| **PoC 2 · 개인정보 침해사고 통지 검토** | 사고·대응 | 사고기록 및 통지문 | 사고내용·통지내용의 일치 여부, 필수 통지사항 | LLM |
| **PoC 3 · Privacy-by-Design 개발지원** | 기획·설계 | 구조화된 개발·설계정보 입력 폼 | 법적 근거, 수집항목, 보유·파기, 처리위탁 등 설계요건 | 구조화 입력 기반 Fact Builder |

- **PoC 1**: 처리행위 단위 Fact 구조화, 추가 확인이 필요한 기재사항·근거 확인. **P1-R08**은 F1-11을 이용해 선정된 권리 5항목(열람·정정·삭제·처리정지·동의 철회)의 기재 누락만 YELLOW로 안내 (전체 법적 완전성 판정 아님)
- **PoC 2**: 사고기록과 통지문의 **출처별 분리 추출**, 일치 여부·누락 항목 검토. 신고·통지 의무의 모든 법정 임계값 자동 판정 제외
- **PoC 3**: 입력한 설계정보로 Fact 직접 생성, **LLM 미사용은 의도된 설계**

### 구현 범위

| 구분 | Fact | Rule |
| --- | ---: | ---: |
| PoC 1 | 12개 | 7개 |
| PoC 2 | 10개 | 5개 |
| PoC 3 | 13개 | 8개 |
| **합계** | **35개** | **20개** |

- **PIPA 온톨로지**: 클래스 37개, 객체속성 23개, 데이터속성 17개, 법조문 개체 24개
- **구현 방식**: DPV 참고 및 국내 개인정보 보호법 규율 구조 반영, OWL 2·RDF 활용

## 🏗️ 시스템 아키텍처

<!-- 전체 시스템 흐름도 이미지 추가 위치: docs/images/architecture.png -->

```text
PoC 1 · 개인정보처리방침 ──┐
                          ├── LLM Fact·Evidence 추출 ──┐
PoC 2 · 사고기록·통지문 ───┘                             │
                                                        ├── Fact Schema 검증
PoC 3 · 개발·설계정보 ──── 구조화 입력 → Fact 생성 ───────┘          │
                                                                   ▼
                                                        PIPA 온톨로지 / RDF 매핑
                                                                   │
                                                                   ▼
                                                               Rule Engine
                                                                   │
                                                                   ▼
                                                    RuleResult · Evidence · 근거
                                                                   │
                                                                   ▼
                                                             FastAPI → React
```

- **Fact Schema Validation**: 입력 Fact의 형식·상태 검증
- **Ontology Mapping**: Fact와 개인정보 처리행위 중심 온톨로지 구조 연결
- **Rule Engine**: 규칙별 적용조건 평가 및 검토 상태 산출
- **Web UI**: 검토 결과·근거 시각화

### Rule 판정상태

| 상태 | 의미 |
| --- | --- |
| `GREEN` | 해당 Rule에서 요구하는 정보 또는 조건 확인 |
| `YELLOW` | 정보 불명확 또는 추가 확인 필요 |
| `RED` | 필요한 정보 또는 조건 미충족 |
| `N/A` | 해당 Rule의 전제가 되는 처리행위 부재 확인 |

- **Fact 확인상태**: `confirmed`(확인됨), `unknown`(불명확), `absent`(없음)
- **상태 구분**: 필요한 정보의 누락과 처리행위 자체의 부재를 별도 관리
- **N/A 적용 조건**: 처리행위 자체의 부재에 대한 근거 확인, `unknown`이나 Fact 누락을 자동으로 `N/A` 처리하지 않음
- **결과 해석**: 검토 우선순위 설정용 참고정보, 법적 준수·위반의 확정 판정 아님

## 🎬 시연 영상

PoC 1·2·3의 실제 작동 화면입니다. **이 페이지에서 바로 재생**할 수 있습니다.

<!-- PIPA-DEMO-START -->

### PoC 1 · 개인정보처리방침 점검

https://github.com/user-attachments/assets/eeb1a1b9-730d-4e80-b93f-15fc885d6644

### PoC 2 · 개인정보 침해사고 통지 검토

https://github.com/user-attachments/assets/1df1c1f8-e30b-44d4-8f55-625fe2300ad3

### PoC 3 · Privacy-by-Design 시연 ①

https://github.com/user-attachments/assets/2ef241dc-5699-47c2-9224-e23bd9da27a0

### PoC 3 · Privacy-by-Design 시연 ②

https://github.com/user-attachments/assets/630900b5-ec79-406f-b918-3c5f7b5a3578

<!-- PIPA-DEMO-END -->

## 🛠️ 기술 스택

| 영역 | 기술·구성 | 역할 |
| --- | --- | --- |
| Frontend | React, TypeScript, Vite | PoC 입력 및 결과 시각화 |
| Backend | Python 3.10, FastAPI | API 및 검토 파이프라인 |
| LLM | Anthropic Claude API | PoC 1·2 비정형 문서 Fact·Evidence 추출 |
| Ontology | OWL 2, RDF, Protégé | PIPA 개념·관계 표현 및 매핑 |
| Validation | Fact Schema | 입력 형식 및 확인상태 검증 |
| Rule | Rule Profile, Rule Engine | 검토조건 정의 및 20개 Rule 평가 |
| Testing | pytest, frontend build/lint | 백엔드 및 프론트엔드 검증 |

### 주요 코드 위치

```text
pipa-dpv-compliance/
├── app/
│   ├── main.py                      # FastAPI 진입점
│   ├── api/compliance.py            # 세 가지 PoC API
│   ├── mapping/
│   │   ├── fact_schema.py           # Fact Schema 검증
│   │   ├── ontology_mapper.py       # 온톨로지 매핑
│   │   └── mapping_registry.py      # Fact 매핑 명세
│   └── rules/
│       ├── engine.py                # Rule Engine
│       └── models.py                # RuleResult
├── frontend/                        # React 웹 애플리케이션
├── docs/                            # 설계·규칙·계약 문서
├── evals/                           # Fact 추출 평가 자료
├── requirements.txt                 # Python 의존성
└── README.md
```

## 🚀 실행 방법

**권장 순서**: 무료 Mock 모드로 화면·처리 흐름 확인 → 필요 시 Claude API 연결을 통한 실제 문서 Fact 추출.

### 1. 실행 환경

| 프로그램 | 용도 | 버전 확인 |
| --- | --- | --- |
| Git | 저장소 다운로드 | `git --version` |
| Python 3.10 | FastAPI 백엔드 | macOS `python3.10 --version` / Windows `py -3.10 --version` |
| Node.js 및 npm | React 프론트엔드 | `node --version` / `npm --version` |
| 터미널 | 설치·서버 실행 | macOS 터미널 / Windows PowerShell |

- **설치 링크**: [Git](https://git-scm.com/downloads) · [Python 3.10](https://www.python.org/downloads/) · [Node.js](https://nodejs.org/)
- **Windows Python 설치**: `Add Python to PATH` 확인
- **Node.js**: 지원 LTS 버전 권장, 호환 여부는 `frontend/package.json` 참고
- **설치 후 확인**: 터미널 재실행 및 각 버전 명령어 확인

### 2. 저장소 다운로드

```bash
git clone https://github.com/ddinii/pipa-dpv-compliance.git
cd pipa-dpv-compliance
```

- **Git 사용 불가 시**: GitHub `Code → Download ZIP` 다운로드·압축 해제 후 프로젝트 폴더 이동
- **이후 실행 위치**: 별도 표기 없을 경우 `pipa-dpv-compliance` 최상위 폴더

### 3. 백엔드 설치

**macOS**

```bash
python3.10 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

**Windows PowerShell**

```powershell
py -3.10 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

- **가상환경 활성화 확인**: 터미널에 `(.venv)` 표시 가능
- **Python 실행 오류**: 버전 3.10 설치 및 PATH 확인
- **PowerShell 활성화 차단**: 조직 정책 확인 후, 허용된 환경에서만 현재 세션에 한해 다음 명령 사용

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

- **조직의 정책 변경 금지 시**: 우회 금지, 관리자 문의 또는 가상환경의 `python.exe` 직접 사용

### 4. 프론트엔드 설치

```bash
cd frontend
npm install
cd ..
```

### 5. 무료 Mock 모드 실행

- **사전 조건**: 백엔드·프론트엔드 설치 완료
- **기본 모드**: API 키 불필요, 입력 문서 분석 대신 **고정 테스트 Fact 반환**
- **간편 실행**: 백엔드·프론트엔드 동시 시작, 별도 설치 자동화 없음

**macOS**

```bash
bash start.sh
```

**Windows PowerShell**

```powershell
.\start.ps1
```

- **웹 화면**: <http://localhost:5173>
- **백엔드 상태**: <http://127.0.0.1:8000/health>
- **API 문서**: <http://127.0.0.1:8000/docs>
- **실행 중**: 스크립트 실행 터미널 유지, 종료는 `Ctrl + C`
- **주의사항**: `.venv` 또는 `frontend/node_modules` 부재 시 설치 필요. macOS·Windows 스크립트 제공, Windows 실제 환경 검증은 별도 진행 필요
- **포트 충돌**: 기존 8000·5173 포트 사용 서버 종료
- **Windows 스크립트 차단**: 조직 정책 확인, 허용된 경우에만 위 세션 범위 실행 정책 설정 또는 아래 개별 실행 사용

**개별 실행 방식 — 터미널 2개**

터미널 A · 백엔드 (macOS):

```bash
source .venv/bin/activate
export PIPA_EXTRACTOR=mock
python -m uvicorn app.main:app --reload
```

터미널 A · 백엔드 (Windows PowerShell):

```powershell
.\.venv\Scripts\Activate.ps1
$env:PIPA_EXTRACTOR = "mock"
python -m uvicorn app.main:app --reload
```

터미널 B · 프론트엔드 (공통):

```bash
cd frontend
npm run dev
```

- **정상 실행 확인**: `/health` 응답 → 웹 화면 접속 → PoC 1·2·3 화면 → Mock 테스트 → Rule별 결과·근거 확인

### 6. Claude API 연결 (선택)

- **대상**: PoC 1·2의 실제 입력문서 기반 Fact 추출. PoC 3에는 API 키 불필요
- **API 키 발급**: [Anthropic Console](https://console.anthropic.com/) (과금 발생 가능)
- **보안**: API 키의 GitHub·README·스크린샷·공개 로그 노출 금지
- **절차**: 기존 서버 `Ctrl + C` 종료 → 백엔드 터미널 환경변수 설정 → 서버 재실행 → PoC 1 또는 2 분석

**macOS** (가상환경 활성화, 프로젝트 최상위 폴더)

```bash
export PIPA_EXTRACTOR=llm
read -s "ANTHROPIC_API_KEY?Anthropic API Key: "
export ANTHROPIC_API_KEY
printf '\n'
bash start.sh
```

**Windows PowerShell** (가상환경 활성화, 프로젝트 최상위 폴더)

```powershell
$env:PIPA_EXTRACTOR = "llm"
$secureKey = Read-Host "Anthropic API Key" -AsSecureString
$env:ANTHROPIC_API_KEY = [System.Net.NetworkCredential]::new("", $secureKey).Password
Remove-Variable secureKey
.\start.ps1
```

- **개별 실행 방식 사용 시**: 각 코드 블록의 마지막 `bash start.sh` 또는 `.\start.ps1` 대신 백엔드 `python -m uvicorn app.main:app --reload` 실행, 프론트엔드는 별도 터미널에서 `npm run dev`
- **환경변수 유효범위**: 현재 터미널 세션, 재시작 시 재설정 가능성
- **`.env` 제한**: 백엔드는 `.env` 자동 로드 미지원. 환경변수는 **백엔드 실행 터미널**에 직접 설정 필요
- **LLM 모드 결과**: 입력 문서에서 Fact 추출 → Fact Schema 검증 → 온톨로지 매핑 → Rule Engine 검토

**모델 설정 (선택)**

- **기존 README의 기본 모델 표기**: `claude-sonnet-5`
- **계정별 모델 이용 가능 여부**: Anthropic 계정·서비스 정책에 따른 차이. 이용 불가 시 실제 접근 가능한 모델 ID로 지정 후 백엔드 재실행

macOS:

```bash
export PIPA_EXTRACTOR_MODEL="사용 가능한 모델 ID"
```

Windows PowerShell:

```powershell
$env:PIPA_EXTRACTOR_MODEL = "사용 가능한 모델 ID"
```

### 7. 프론트엔드 API 주소 변경 (선택)

- **기본 백엔드 주소**: `http://127.0.0.1:8000`
- **변경 대상**: 백엔드를 다른 주소에서 실행하는 경우의 `frontend/.env`

macOS:

```bash
cp frontend/.env.example frontend/.env
```

Windows PowerShell:

```powershell
Copy-Item frontend\.env.example frontend\.env
```

`frontend/.env` 설정:

```dotenv
VITE_API_BASE_URL=http://127.0.0.1:8000
```

- **반영 조건**: 실제 백엔드 주소로 수정 후 프론트엔드 개발 서버 재시작
- **보안**: 프론트엔드 `.env`에 Anthropic API 키 저장 금지. `VITE_` 환경변수는 브라우저 코드에 노출 가능

### 8. 종료·재실행

- **종료**: 실행 중인 서버 터미널에서 `Ctrl + C`
- **재실행**: 설치 재반복 불필요, macOS `bash start.sh` / Windows `.\start.ps1` 또는 개별 실행 방식 사용
- **Mock 복귀**: 백엔드 실행 터미널의 `PIPA_EXTRACTOR=mock` 설정 후 재실행

## 🧪 직접 확인할 내용

- **PoC 1**: 개인정보처리방침 입력 → 처리행위별 기재사항·원문 근거 확인
- **PoC 2**: 사고기록·통지문 입력 → 출처별 정보·일치 여부·필수 통지사항 확인
- **PoC 3**: 개발·설계정보 입력 → 누락·불확실 항목 및 보완 필요사항 확인
- **결과 추적**: `GREEN / YELLOW / RED / N/A`, Fact·Evidence·법적 근거·판정사유 확인
- **Mock 한계**: 입력을 변경해도 고정 테스트 Fact 반환, 실제 문서 추출 확인은 LLM 모드 사용
- **테스트 데이터**: 실제 개인정보·민감 사고기록 대신 가상·비식별 자료 사용

## 🔌 API 안내

- **API 문서**: 백엔드 실행 후 <http://127.0.0.1:8000/docs>에서 요청·응답 형식 확인

| Method | Endpoint | 기능 |
| --- | --- | --- |
| `GET` | `/health` | 서버 상태 확인 |
| `POST` | `/api/v1/compliance/policy-check` | 개인정보처리방침 점검 |
| `POST` | `/api/v1/compliance/breach-check` | 개인정보 침해사고 통지 검토 |
| `POST` | `/api/v1/compliance/design-check` | Privacy-by-Design 개발지원 |

- **응답 구성**: 분석 ID, PoC 구분, 온톨로지·Rule·Fact Schema 버전, 규칙별 `RuleResult`

## 🧰 자주 발생하는 문제

| 증상 | 확인·조치 |
| --- | --- |
| `python` 또는 `py` 명령 오류 | Python 3.10 설치·PATH 확인, 터미널 재시작 및 버전 명령 확인 |
| `uvicorn` 모듈 오류 | 가상환경 활성화 → `python -m pip install -r requirements.txt` → `python -m uvicorn app.main:app --reload` |
| `npm` 명령 오류 | Node.js 설치·PATH 확인, `node --version`·`npm --version` 확인 |
| 화면은 열리나 API 요청 실패 | `/health` 응답, `VITE_API_BASE_URL`, 백엔드 주소 및 프론트엔드 포트 5173 확인 |
| LLM 모드 API 키 오류 | `PIPA_EXTRACTOR=llm`, 백엔드 터미널의 `ANTHROPIC_API_KEY`, 모델 ID·접근 권한·과금 상태 확인. `.env`만으로 자동 설정 불가 |
| Mock 입력 변경 후 동일 결과 | 정상 동작. 고정 테스트 Fact 반환, 실제 문서 기반 검토는 LLM 모드 사용 |
| 8000 또는 5173 포트 사용 중 | 기존 서버 `Ctrl + C` 종료. 포트 변경 시 프론트엔드 API 주소·백엔드 CORS 설정 확인 |

## 📚 기술 문서 및 검증

### 로컬 테스트

백엔드 (프로젝트 최상위 폴더, 가상환경 활성화):

```bash
python -m pytest -q
```

프론트엔드 (`frontend` 폴더):

```bash
npm run build
npm run lint
```

- **테스트 결과**: 코드 버전에 따라 통과 개수 변동 가능, 실행 커밋 기준 확인

### 추가 문서

- **프로젝트 개요 및 범위**: [PROJECT.md](docs/context/core/PROJECT.md)
- **파이프라인 구조**: [PIPELINE.md](docs/context/core/PIPELINE.md)
- **Fact·RuleResult 계약**: [CONTRACTS.md](docs/context/core/CONTRACTS.md)
- **Rule 매트릭스**: [규칙별 검토 항목·조건 문서](docs/%50%30_RULE_MATRIX.md)
- **Fact Extractor 평가 자료**: [evals/README.md](evals/README.md)
- **Fact Extractor 평가 결과**: [evals/RESULTS.md](evals/RESULTS.md)

### 적용 범위 및 한계

- **적용 범위**: 선정한 세 가지 PoC의 35개 Fact·20개 Rule. 개인정보 보호법 전체의 자동 검토 제외
- **PoC 2**: 신고·통지 의무의 모든 법정 기준(인원·시간 임계값 등) 자동 판정 제외
- **LLM 추출**: 문서 내용·모델에 따른 품질 차이, 원문 근거 확인 필요
- **결과 상태**: 법적 위반 여부 확정 판정이나 법적 준수 인증이 아닌 참고정보
- **Mock 모드**: UI·파이프라인 확인용, 실제 문서 분석 성능 검증 수단 아님

---

<div align="center">

**PIPA-DPV Compliance**

개인정보보호 업무의 반복적인 사전 검토를 지원하는 근거 중심 컴플라이언스 AX 프로토타입

</div>
