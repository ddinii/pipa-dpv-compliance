# 협업 가이드

## 브랜치 전략

```
main        ── 항상 동작하는 상태 유지 (직접 push 금지, PR만 허용)
  └─ dev     ── 통합 브랜치, 기능 브랜치들이 여기로 모임
       ├─ feature/ontology-profile      (1층 온톨로지)
       ├─ feature/rule-engine           (2층 규칙 엔진)
       ├─ feature/compliance-api        (3층 API)
       ├─ feature/frontend-demo         (UI 시나리오)
       └─ feature/evaluation            (PoC 검증/평가)
```

- 브랜치명: `feature/<작업내용>`, `fix/<버그내용>` 형식 권장
- `main`, `dev` 브랜치는 GitHub 설정에서 **Branch protection** 걸어두는 것을 추천
  (Settings → Branches → Require pull request before merging)

## 역할 분담 (문서 제안 기준, 5인 팀)

| 담당 | 폴더/파일 | 내용 |
|---|---|---|
| A | `docs/`, README 배경 부분 | 제안배경, 국내 현황, 문제정의 |
| B | `ontology/pipa_dpv_classes.ttl` | W3C DPV·legal-kr 조사 및 온톨로지 고도화 |
| C | `backend/rules/rule_engine.py`, `backend/models.py` | 규칙 정의, GREEN/RED/AMBER 로직 |
| D | `backend/main.py`, `frontend/app.py` | API 설계, 활용 시나리오 데모 |
| E | `evaluation/`, `tests/` | PoC 검증, 로드맵, 평가 지표 설계 |

작업 시작 전 **최종 정책명 / 전체 아키텍처 / 3계층 정의 / PoC 범위(규칙 개수)**를
먼저 팀 전체가 합의한 뒤 나눠서 작업하세요. (문서에서 강조된 부분 — 안 그러면
서로 다른 설계로 코드가 갈라집니다.)

## 작업 흐름

1. `dev` 브랜치에서 최신 상태로 갱신
   ```bash
   git checkout dev
   git pull origin dev
   ```
2. 본인 feature 브랜치 생성
   ```bash
   git checkout -b feature/rule-engine
   ```
3. 작업 후 커밋 (커밋 메시지 컨벤션 아래 참고)
4. 원격에 push
   ```bash
   git push origin feature/rule-engine
   ```
5. GitHub에서 `feature/rule-engine` → `dev` 로 Pull Request 생성
6. 팀원 1명 이상 리뷰 후 머지
7. 어느 정도 기능이 쌓이면 `dev` → `main` 으로 PR (제출 직전 안정화 시점에)

## 커밋 메시지 컨벤션

`<type>: <설명>` 형식을 권장합니다.

| type | 용도 |
|---|---|
| `feat` | 새 기능 추가 |
| `fix` | 버그 수정 |
| `docs` | 문서 수정 |
| `refactor` | 동작 변경 없는 코드 개선 |
| `test` | 테스트 추가/수정 |
| `chore` | 빌드, 설정 등 기타 |

예: `feat: 국외이전 규칙(R07) AMBER 판정 로직 추가`

## PR 체크리스트

- [ ] `pytest` 통과 확인
- [ ] `legal_basis`(조문 번호)가 placeholder라면 PR 설명에 명시
- [ ] 새 규칙 추가 시 `tests/test_rule_engine.py`에 테스트 케이스 추가
- [ ] README/CONTRIBUTING 업데이트가 필요한 변경이면 함께 반영

## 이슈 관리

- GitHub Issues + Projects(칸반보드) 사용 권장
- 칸반 컬럼: `Backlog` → `In Progress` → `In Review` → `Done`
- 라벨: `ontology`, `rule-engine`, `api`, `frontend`, `evaluation`, `docs`, `bug`

## 규칙/조문 관련 작업 시 주의

`rule_engine.py`와 `pipa_dpv_classes.ttl`의 법조문 번호는 모두 placeholder로
표시되어 있습니다. 조문 검증 작업은 되도록 **1명이 전담**해서 일관성을 유지하고,
확정되면 두 파일 모두 함께 업데이트하세요 (규칙 엔진과 온톨로지가 서로 다른
조문을 참조하지 않도록).
