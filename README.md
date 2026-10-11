<div align="center">

# 온톨로지 기반 개인정보보호 컴플라이언스 AX 체계 구축

### PIPA-DPV Compliance | 개인정보보호 업무의 신뢰 가능한 AI Transformation

**LLM Fact 추출 · PIPA 온톨로지 · 결정론적 Rule Engine · 근거 추적**

[프로젝트 소개](#-프로젝트-소개) · [핵심 기능](#-세-가지-poc) · [실행 가이드](#-처음-실행하기) · [기술 문서](#-기술-문서와-검증)

</div>

---

## 📌 프로젝트 소개

개인정보보호 담당자는 개인정보 처리방침, 침해사고 통지문, 서비스 설계정보를 확인할 때 관련 법적 요건을 반복적으로 검토해야 합니다. 생성형 AI는 문서에서 정보를 추출하는 데 유용하지만, AI가 법적 판단까지 직접 수행하면 결과의 일관성과 근거 추적에 한계가 있습니다.

**PIPA-DPV Compliance**는 이러한 문제를 해결하기 위한 **개인정보보호 컴플라이언스 AX 프로토타입**입니다. 개인정보 보호법(PIPA)의 주요 개념과 관계를 온톨로지로 구조화하고, 입력에서 확인된 사실(Fact)에 사전 정의된 규칙(Rule)을 적용해 **추가 검토가 필요한 항목과 그 근거**를 제시합니다.

이 프로젝트는 「2026 정보보호 정책제안 공모전」에 제출한 **「온톨로지 기반 개인정보보호 컴플라이언스 AX 체계 구축」** 정책제안의 기술적 실현 가능성을 확인하기 위한 PoC입니다. 법률 전문가의 판단을 대체하는 서비스가 아니라, **반복적인 사전 검토를 지원하고 담당자가 중요한 사안에 집중하도록 돕는 도구**를 지향합니다.

### 핵심 설계 원칙

| 원칙 | 구현 방식 |
| --- | --- |
| **AI와 판단 기준의 역할 분리** | LLM은 비정형 문서에서 Fact·Evidence를 추출하고, 검토 상태는 Rule Engine이 산출합니다. |
| **일관성** | 동일한 Fact에 동일한 규칙을 적용하여 일관된 결과를 생성합니다. |
| **근거 추적** | 원문 근거(Evidence), 사용된 Fact, 규칙 및 판단 사유를 연결합니다. |
| **불확실성 보존** | 확인된 사실(`confirmed`), 불확실한 사실(`unknown`), 근거 있는 부재(`absent`)를 구분합니다. |
| **사람의 최종 검토** | 시스템 결과는 검토 지원 정보이며, 최종 법적 판단은 담당자가 수행합니다. |

> ⚖️ **중요:** `GREEN`은 법적 준수 인증이 아니며, `RED`는 확정적인 법 위반 판정이 아닙니다. 본 프로젝트는 개인정보 보호법 전체에 대한 자동 법률 판단 시스템이 아닙니다.

## 🧩 세 가지 PoC

세 가지 PoC는 서로 다른 개인정보보호 업무에 동일한 Fact–Ontology–Rule 구조를 적용한 **독립적인 검증 시나리오**입니다.

| 구분 | 업무 시점 | 입력 | 확인하려는 내용 | Fact 생성 |
| --- | --- | --- | --- | --- |
| **PoC1 · 개인정보 처리방침 점검** | 운영·관리 | 개인정보 처리방침 텍스트 | 처리목적, 보유기간, 제3자 제공, 처리위탁 등 기재사항 | **LLM** |
| **PoC2 · 침해사고 통지 검토** | 사고·대응 | 사고 기록 및 통지문 | 사고 사실과 통지 내용의 일치 여부, 필수 통지사항 | **LLM** |
| **PoC3 · Privacy-by-Design 개발 지원** | 기획·설계 | 구조화된 설계정보 입력 폼 | 법적 근거, 수집항목, 보유·파기, 처리위탁 등 설계 단계 검토사항 | **규칙 기반 Fact Builder** |

**PoC1 — 개인정보 처리방침 점검:** 처리방침에서 확인되는 개인정보 처리행위를 구조화하고, 각 처리행위에서 추가 확인이 필요한 기재사항을 제시합니다.

**PoC2 — 침해사고 통지 검토:** 사고 기록과 통지문을 **서로 다른 출처로 분리해 추출**한 후, 검토가 필요한 항목과 근거를 제시합니다. 현재 PoC는 신고·통지 의무 발생 여부의 모든 법정 임계값을 자동 판단하지 않습니다.

**PoC3 — Privacy-by-Design:** 개발·설계 단계에서 입력한 구조화된 정보를 이용해 개인정보 처리 계획의 보완 필요 사항을 검토합니다. **PoC3에서 LLM을 사용하지 않는 것은 의도된 설계**입니다.

### 구현 범위

| 구분 | Fact | P0 Rule |
| --- | ---: | ---: |
| PoC1 | 12개 | 6개 |
| PoC2 | 10개 | 4개 |
| PoC3 | 13개 | 8개 |
| **합계** | **35개** | **18개** |

PIPA 온톨로지는 **37개 클래스, 23개 객체속성, 17개 데이터속성, 24개 법조문 개체**로 구성했으며, OWL 2·RDF를 사용했습니다. 국제 개인정보보호 어휘체계 DPV를 참고하되 국내 개인정보 보호법의 규율 구조를 반영했습니다.

## 🏗️ 시스템 아키텍처

<!-- TODO: 팀에서 제작할 전체 시스템 흐름도 이미지를 이 위치에 삽입하세요.
예시: ![PIPA-DPV Compliance 전체 아키텍처](docs/images/architecture.png)
실제 이미지 파일을 저장소에 추가한 뒤 경로를 수정하세요.
-->

전체 흐름도를 추가하기 전에도 구조를 확인할 수 있도록 텍스트로 표시했습니다.

```text
[PoC1: 개인정보 처리방침] ──┐
                           ├─> LLM Fact Extractor ──┐
[PoC2: 사고 기록·통지문] ──┘                       │
                                                   ├─> Fact Schema 검증
[PoC3: 구조화된 설계 폼] ──> Deterministic Builder ─┘           │
                                                                ▼
                                                      PIPA Ontology / RDF 매핑
                                                                │
                                                                ▼
                                                        P0 Rule Engine
                                                                │
                                                                ▼
                                                  RuleResult + Evidence + 근거
                                                                │
                                                                ▼
                                                      FastAPI → React UI
```

- **Fact Schema Validation:** 입력 Fact의 형식과 상태를 검증합니다.
- **Ontology Mapping:** Fact를 개인정보 처리행위 중심의 온톨로지 구조와 연결합니다.
- **Rule Engine:** 사전에 정의된 조건으로 규칙별 검토 상태를 산출합니다.
- **Web UI:** 검토 결과와 관련 근거를 화면에 표시합니다.

### 결과 상태 읽는 법

| 상태 | 의미 |
| --- | --- |
| `GREEN` | 해당 규칙에서 요구하는 정보 또는 조건이 확인됨 |
| `YELLOW` | 정보가 불명확하거나 추가 확인이 필요함 |
| `RED` | 해당 규칙에서 요구하는 정보 또는 조건이 충족되지 않음 |
| `N/A` | 규칙 적용 전제가 되는 처리행위가 존재하지 않는 것이 확인됨 |

`unknown`을 자동으로 `absent` 또는 `N/A`로 취급하지 않습니다. 결과는 검토 우선순위를 정하기 위한 참고정보이며 법적 판단을 확정하지 않습니다.

## 🎬 시연 영상

<!-- TODO: 시연 영상이 준비되면 팀에서 보유한 YouTube/영상 삽입 코드를 여기에 추가하세요. -->

## 🚀 처음 실행하기

개발 환경을 처음 구성하는 심사위원도 따라 할 수 있도록 **① 무료 Mock 모드로 화면 확인 → ② 선택적으로 Claude API 연결** 순서로 안내합니다.

> **권장:** 처음에는 API 키가 필요 없는 **Mock 모드**로 실행해 보세요. Mock 모드는 입력 내용을 실제로 분석하지 않고 **미리 정해진 테스트 Fact**를 반환하므로, UI와 전체 처리 흐름 확인에 적합합니다. 실제 문서에서 Fact를 추출하려면 아래의 **Claude API 연결** 단계를 진행해야 합니다.

### 1. 준비물

| 프로그램 | 용도 | 확인 명령 |
| --- | --- | --- |
| **Git** | GitHub 저장소 다운로드 | `git --version` |
| **Python 3.10** | FastAPI 백엔드 실행 | `python3.10 --version`(Mac) / `py -3.10 --version`(Windows) |
| **Node.js + npm** | React 프론트엔드 실행 | `node --version` / `npm --version` |
| **터미널** | 설치 및 서버 실행 | macOS 터미널 / Windows PowerShell |

- Git: <https://git-scm.com/downloads>
- Python 3.10: <https://www.python.org/downloads/>
- Node.js: <https://nodejs.org/>
- Python 설치 시 Windows에서는 **Add Python to PATH** 옵션을 확인하세요.
- 설치 후 터미널을 새로 열어 위 확인 명령이 동작하는지 확인하세요.
- Node.js는 지원되는 LTS 버전을 권장합니다. 구체적인 호환 버전은 저장소의 `frontend/package.json`을 확인하세요.

### 2. 소스코드 다운로드 (Windows / macOS 공통)

터미널에서 다음 명령을 실행합니다.

```bash
git clone https://github.com/ddinii/pipa-dpv-compliance.git
cd pipa-dpv-compliance
```

`git`을 사용할 수 없다면 GitHub 저장소의 **Code → Download ZIP**으로 다운로드해 압축을 풀어도 됩니다. 이후 터미널에서 압축을 푼 프로젝트 폴더로 이동하세요.

**이후 명령의 기본 위치는 `pipa-dpv-compliance` 프로젝트 최상위 폴더입니다.**

### 3. 백엔드 설치

<details>
<summary><strong>🍎 macOS (터미널)</strong></summary>

```bash
# 프로젝트 최상위 폴더에서 실행
python3.10 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

가상환경이 활성화되면 터미널 앞에 `(.venv)`가 표시될 수 있습니다. `python3.10`을 찾을 수 없다면 Python 3.10 설치 및 PATH를 확인하세요.

</details>

<details>
<summary><strong>🪟 Windows (PowerShell)</strong></summary>

```powershell
# 프로젝트 최상위 폴더에서 실행
py -3.10 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

PowerShell에서 스크립트 실행이 차단되는 경우 **현재 PowerShell 프로세스에 한해서만** 다음 명령을 실행한 뒤 가상환경 활성화를 다시 시도하세요.

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

조직에서 PowerShell 정책 변경이 금지되어 있다면 정책을 우회하지 말고 관리자에게 문의하거나, 가상환경의 `python.exe`를 직접 사용하세요.

</details>

### 4. 프론트엔드 설치 (Windows / macOS 공통)

같은 프로젝트 폴더에서 다음을 실행합니다.

```bash
cd frontend
npm install
cd ..
```

설치가 끝나면 프로젝트 최상위 폴더로 돌아옵니다.

### 5. 무료 Mock 모드로 실행하기

**권장: 간편 실행 (명령어 한 번)**

백엔드와 프론트엔드를 한 번에 시작하는 스크립트를 제공합니다. 먼저 **3~4단계의 설치를 완료**한 뒤 프로젝트 최상위 폴더에서 실행하세요. 기본값은 API 키가 필요 없는 **Mock 모드**입니다.

**🍎 macOS (터미널)**

```bash
bash start.sh
```

**🪟 Windows (PowerShell)**

```powershell
.\start.ps1
```

PowerShell이 실행 정책으로 차단한다면 조직 정책을 확인한 뒤, 허용되는 개인 PC에서는 현재 세션에 한해 `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`를 설정할 수 있습니다. 정책 변경이 불가능하면 아래의 **개별 실행 방식**을 이용하세요.

스크립트가 실행 중인 **터미널 하나를 그대로 열어두고** 브라우저에서 <http://localhost:5173>으로 접속하세요. 백엔드 확인: <http://127.0.0.1:8000/health>, API 문서: <http://127.0.0.1:8000/docs>. 종료할 때는 스크립트를 실행한 터미널에서 **Ctrl+C**를 누르세요. 이미 8000 또는 5173 포트를 사용 중인 서버가 있다면 먼저 종료해야 합니다.

> **참고:** 이 스크립트는 설치를 자동 수행하지 않습니다. `.venv`나 `frontend/node_modules`가 없으면 설치 방법을 안내합니다. macOS와 Windows 스크립트는 제공하지만, 실제 Windows 환경 검증은 별도로 진행해야 합니다.

<details>
<summary><strong>개별 실행 방식 (문제 해결 또는 개발용: 터미널 2개)</strong></summary>

**터미널 A — 백엔드**

macOS:

```bash
source .venv/bin/activate
export PIPA_EXTRACTOR=mock
python -m uvicorn app.main:app --reload
```

Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
$env:PIPA_EXTRACTOR = "mock"
python -m uvicorn app.main:app --reload
```

**터미널 B — 프론트엔드 (공통)**

```bash
cd frontend
npm run dev
```

</details>

**정상 실행 확인 순서:** `GET /health` 응답 확인 → 프론트엔드 접속 → PoC1·2·3 화면 확인 → Mock 테스트 실행 → 규칙별 결과와 근거 확인.

### 6. 실제 Claude API 연결하기 (선택 사항)

PoC1과 PoC2에서 **입력한 실제 문서로부터 Fact를 추출**하려면 Anthropic Claude API 키가 필요합니다. PoC3는 구조화된 입력을 사용하므로 Claude API 키가 필요하지 않습니다.

**① API 키 준비**

Anthropic Console(<https://console.anthropic.com/>)에서 본인 계정의 API 키를 발급받으세요. API 사용에는 **비용이 발생할 수 있습니다.** API 키는 절대 GitHub, README, 스크린샷, 공개 로그에 올리지 마세요.

**② 기존 서버 중지**

간편 실행 중이라면 해당 터미널에서 `Ctrl+C`로 백엔드와 프론트엔드를 모두 중지하세요. 개별 실행 중이라면 백엔드 터미널에서 `Ctrl+C`로 백엔드만 중지하면 됩니다.

**③ 환경변수 설정 후 재실행**

간편 실행을 사용하려면 아래의 환경변수 설정 명령만 먼저 실행한 다음, macOS는 `bash start.sh`, Windows는 `.\start.ps1`을 실행하면 됩니다. 아래 코드의 마지막 `python -m uvicorn ...` 명령은 **개별 실행 방식을 사용할 때만** 실행하세요.

**macOS** — 프로젝트 최상위 폴더, 가상환경 활성화 상태:

```bash
export PIPA_EXTRACTOR=llm
read -s "ANTHROPIC_API_KEY?Anthropic API Key: "
export ANTHROPIC_API_KEY
printf '\n'
python -m uvicorn app.main:app --reload
```

**Windows PowerShell** — 프로젝트 최상위 폴더, 가상환경 활성화 상태:

```powershell
$env:PIPA_EXTRACTOR = "llm"
$secureKey = Read-Host "Anthropic API Key" -AsSecureString
$env:ANTHROPIC_API_KEY = [System.Net.NetworkCredential]::new("", $secureKey).Password
Remove-Variable secureKey
python -m uvicorn app.main:app --reload
```

위 예시는 **현재 터미널 세션에만** 키를 설정합니다. 터미널을 닫으면 다시 입력해야 할 수 있습니다. 실제 키를 명령어에 직접 적거나 셸 기록에 남기지 않도록 주의하세요.

**④ 브라우저에서 PoC1 또는 PoC2 실행**

<http://localhost:5173>에서 문서를 입력하고 분석을 실행합니다. Mock과 달리 LLM이 입력 문서를 읽어 Fact를 추출한 뒤, 동일한 검증·온톨로지 매핑·Rule Engine을 거쳐 결과를 제공합니다.

> **중요:** `.env.example` 파일이 있어도 **현재 백엔드는 `.env`를 자동으로 읽지 않습니다.** `.env` 파일에 API 키만 작성하는 것으로는 LLM 모드가 활성화되지 않습니다. 위와 같이 **백엔드를 실행하는 터미널에 환경변수를 설정**해야 합니다.

**모델 설정(선택):** 현재 README에 기재된 기본 모델명은 `claude-sonnet-5`입니다. 해당 모델을 API 계정에서 사용할 수 없는 경우, **본인 계정에서 실제로 사용 가능한 모델 ID**를 확인해 다음 환경변수로 지정하세요.

```bash
# macOS
export PIPA_EXTRACTOR_MODEL="사용 가능한 모델 ID"
```

```powershell
# Windows PowerShell
$env:PIPA_EXTRACTOR_MODEL = "사용 가능한 모델 ID"
```

모델 변경 후 백엔드를 다시 실행합니다. 모델 ID와 API 접근 가능 여부는 Anthropic 계정 및 서비스 정책에 따라 달라질 수 있습니다.

### 7. 프론트엔드 API 주소를 변경해야 하는 경우 (선택 사항)

기본 API 주소는 `http://127.0.0.1:8000`입니다. 백엔드를 다른 주소에서 실행할 때만 `frontend/.env`를 설정하세요.

**macOS**

```bash
cp frontend/.env.example frontend/.env
```

**Windows PowerShell**

```powershell
Copy-Item frontend\.env.example frontend\.env
```

`frontend/.env`의 API 주소를 실제 백엔드 주소로 수정합니다.

```dotenv
VITE_API_BASE_URL=http://127.0.0.1:8000
```

변경 후 프론트엔드 개발 서버를 다시 실행하세요. **프론트엔드 `.env`에는 Anthropic API 키를 넣지 마세요.** `VITE_` 접두사 환경변수는 브라우저 코드에 노출될 수 있습니다.

### 8. 실행 종료 및 재실행

- **종료:** 각 서버 터미널에서 `Ctrl + C`.
- **재실행:** 설치 단계(`pip install`, `npm install`)를 매번 반복할 필요는 없습니다. 프로젝트 최상위 폴더에서 macOS는 `bash start.sh`, Windows는 `.\start.ps1`을 실행하세요. 개별 실행 방식도 계속 사용할 수 있습니다.
- **Mock으로 복귀:** 백엔드 터미널에서 `PIPA_EXTRACTOR=mock`으로 변경한 뒤 재실행하세요.

## 🧪 직접 확인해 볼 내용

1. **PoC1:** 개인정보 처리방침 텍스트를 입력하고 처리행위별 기재사항 및 근거가 어떻게 표시되는지 확인합니다.
2. **PoC2:** 사고 기록과 통지문을 입력하고 서로 다른 출처의 정보가 어떻게 검토되는지 확인합니다.
3. **PoC3:** 서비스 설계정보를 입력하고 누락·불확실 항목에 대한 검토 결과를 확인합니다.
4. **결과 추적:** 각 규칙의 `GREEN / YELLOW / RED / N/A` 상태와 Fact·Evidence·법적 근거·판정 사유를 확인합니다.

**Mock 모드에서는 입력 내용에 따라 결과가 바뀌지 않습니다.** 실제 텍스트에 따른 Fact 추출 결과를 확인하려면 LLM 모드를 사용하세요. 테스트할 때는 실제 개인정보나 민감한 사고 자료 대신 **가상·비식별 예시 데이터**를 사용하세요.

## 🛠️ 기술 구성

| 영역 | 기술 / 구성 | 역할 |
| --- | --- | --- |
| Frontend | React, TypeScript, Vite | PoC 입력 화면 및 결과 시각화 |
| Backend | Python 3.10, FastAPI | API 및 검토 파이프라인 |
| LLM | Anthropic Claude API | PoC1·2 비정형 문서 Fact 추출 |
| Ontology | OWL 2, RDF, Protégé | PIPA 개념·관계 표현 및 매핑 |
| Validation | Fact Schema | 입력 계약 및 상태 검증 |
| Rule Engine | `P0RuleEngine` | 18개 P0 Rule의 결정론적 검토 |
| Testing | pytest, frontend build/lint | 백엔드 및 프론트엔드 검증 |

### 주요 코드 위치

```text
pipa-dpv-compliance/
├── app/
│   ├── main.py                      # FastAPI 진입점
│   ├── api/compliance.py            # 3개 PoC API
│   ├── mapping/
│   │   ├── fact_schema.py           # Fact Schema 검증
│   │   ├── ontology_mapper.py       # OntologyMapper
│   │   └── mapping_registry.py      # Fact 매핑 명세
│   └── rules/
│       ├── engine.py                # P0RuleEngine
│       └── models.py                # RuleResult
├── frontend/                        # React 웹 애플리케이션
├── docs/                            # 설계·규칙·계약 문서
├── evals/                           # Fact Extractor 평가 자료
├── requirements.txt                 # Python 의존성
└── README.md
```

## 🔌 API 안내

백엔드 실행 후 <http://127.0.0.1:8000/docs>에서 각 API의 요청 형식과 응답을 확인할 수 있습니다.

| Method | Endpoint | 기능 |
| --- | --- | --- |
| `GET` | `/health` | 서버 상태 확인 |
| `POST` | `/api/v1/compliance/policy-check` | PoC1 처리방침 검토 |
| `POST` | `/api/v1/compliance/breach-check` | PoC2 침해사고 통지 검토 |
| `POST` | `/api/v1/compliance/design-check` | PoC3 설계정보 검토 |

결과에는 분석 ID, PoC 구분, 온톨로지·규칙·Fact Schema 버전, 규칙별 `RuleResult`가 포함됩니다.

## 🧰 자주 발생하는 문제

<details>
<summary><strong>Python 또는 py 명령을 찾을 수 없어요.</strong></summary>

Python **3.10**이 설치되어 있는지 확인하세요. macOS에서는 `python3.10 --version`, Windows에서는 `py -3.10 --version`으로 확인합니다. 설치 후 터미널을 다시 여세요.

</details>

<details>
<summary><strong>uvicorn 모듈을 찾을 수 없어요.</strong></summary>

프로젝트 최상위 폴더에서 가상환경을 활성화하고 `python -m pip install -r requirements.txt`를 다시 실행하세요. 백엔드 실행에는 `python -m uvicorn app.main:app --reload`를 사용합니다.

</details>

<details>
<summary><strong>npm 명령을 찾을 수 없어요.</strong></summary>

Node.js 설치 및 PATH를 확인하세요. `node --version`, `npm --version`으로 설치 여부를 확인하고 터미널을 다시 여세요.

</details>

<details>
<summary><strong>화면은 열리는데 API 요청이 실패해요.</strong></summary>

백엔드가 실행 중인지 <http://127.0.0.1:8000/health>에서 확인하세요. `frontend/.env`의 `VITE_API_BASE_URL`과 실제 백엔드 주소가 같은지, 프론트엔드가 기본 포트 `5173`에서 실행되는지 확인하세요.

</details>

<details>
<summary><strong>LLM 모드에서 API 키 오류가 발생해요.</strong></summary>

`PIPA_EXTRACTOR=llm`인지, **백엔드를 실행하는 터미널**에 `ANTHROPIC_API_KEY`가 설정되어 있는지 확인하세요. `.env` 파일만 작성해도 자동 적용되지는 않습니다. 모델 ID, API 사용 권한, 과금 상태도 확인하세요. 실제 API 키를 이슈나 로그에 공개하지 마세요.

</details>

<details>
<summary><strong>Mock 모드에서 입력을 바꿔도 결과가 같아요.</strong></summary>

정상적인 동작입니다. Mock Extractor는 입력을 분석하지 않고 고정된 테스트 Fact를 반환합니다. 실제 문서 기반 추출을 확인하려면 LLM 모드를 사용하세요.

</details>

<details>
<summary><strong>8000 또는 5173 포트가 이미 사용 중이에요.</strong></summary>

기존에 실행한 서버가 남아 있는지 확인하고 해당 터미널에서 `Ctrl + C`로 종료하세요. 포트를 변경하려면 프론트엔드 API 주소 및 백엔드 CORS 설정을 함께 확인해야 합니다.

</details>

## 📚 기술 문서와 검증

### 로컬 테스트

**백엔드** — 프로젝트 최상위 폴더에서 가상환경 활성화 후:

```bash
python -m pytest -q
```

**프론트엔드** — `frontend` 폴더에서:

```bash
npm run build
npm run lint
```

> 위 명령은 저장소에서 제공하는 검증 방법입니다. 테스트 통과 개수는 코드 버전에 따라 달라질 수 있으므로 README에 고정된 수치를 적지 않았습니다. 실제 결과는 실행한 커밋 기준으로 확인하세요.

### 추가 문서

- [프로젝트 개요 및 범위](docs/context/core/PROJECT.md)
- [파이프라인 구조](docs/context/core/PIPELINE.md)
- [Fact / RuleResult 계약](docs/context/core/CONTRACTS.md)
- [P0 Rule Matrix](docs/P0_RULE_MATRIX.md)
- [Extractor 평가 자료](evals/README.md)
- [Extractor 평가 결과](evals/RESULTS.md)

### 적용 범위와 한계

- 35개 Fact와 18개 P0 Rule은 **선정된 세 가지 PoC 검토 항목**에 대한 구현 범위입니다. 개인정보 보호법 전체를 포괄하지 않습니다.
- PoC2는 신고·통지 의무의 모든 법정 기준(예: 인원·시간 임계값)을 자동 판정하지 않습니다.
- LLM의 추출 품질은 문서 내용과 모델에 따라 달라질 수 있으며, 원문 근거 확인이 필요합니다.
- 시스템의 상태 분류는 법적 위반 여부의 확정 판정이 아닙니다.
- Mock 모드는 실제 문서 분석 성능을 입증하는 수단이 아닙니다.

---

<div align="center">

**PIPA-DPV Compliance**
개인정보보호 업무의 반복적인 사전 검토를 지원하는, 근거 중심의 컴플라이언스 AX 프로토타입

</div>
