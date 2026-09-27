# Extractor 평가 세트

LLM Fact Extractor의 정답지와 채점기입니다. Rule Engine이 아니라 **Extractor**를 평가합니다.

```text
evals/
├─ dataset.py                  # PoC별 평가 세트 탐색 (POC_DATASETS)
├─ score.py                    # Fact-level 채점기
├─ run_extraction.py           # 실제 추출 + 채점 (API 호출)
└─ poc1/
   ├─ sc_p01_policy.txt        # 처리방침 원문 (가상)
   ├─ sc_p01_gold_facts.json   # gold Fact set (생성물)
   ├─ build_gold_facts.py      # 생성기
   └─ variants/                # controlled variants 6개
```

PoC를 늘릴 때는 `evals/dataset.py`의 `POC_DATASETS`에 `DatasetSpec` 한 줄,
`run_extraction.py`의 `EXTRACTORS`에 Extractor 한 줄을 더합니다. 로더·러너·채점기
본체는 손대지 않습니다. 등록만 해두고 파일이 없으면 즉시 실패하므로
"0건 평가 통과"가 조용히 생기지 않습니다.

## 파이프라인

```text
원문 ──LLM 2-pass──> Fact ──검증──> RDF ──> Rule Engine
                      │                        │
                 Fact-level 채점          Rule-level 비교
```

| 단계 | 모듈 | 명세 |
|---|---|---|
| 추출 | `app/extractors/poc1.py` | P01-002~004 |
| 검증 | `app/mapping/fact_schema.py` + `app/facts/validator.py` | COM-001/002 |
| 매핑 | `app/mapping/ontology_mapper.py` | COM-003/004 |
| 판정 | `app/rules/engine.py` | P0 18 Rule |

**gold Fact를 매퍼에 태우면 SC-P01의 Freeze 기대값이 그대로 재현됩니다**
(`tests/test_facts.py::test_gold_facts_reproduce_sc_p01_statuses`). 따라서
`expected_rule_status`는 주장이 아니라 테스트로 고정된 값입니다.

재생성 / 검증:

```powershell
python evals\poc1\build_gold_facts.py
python -m pytest -q tests\test_gold_facts_poc1.py tests\test_facts.py
```

실제 추출 (Claude API 호출 · 비용 발생). **문서 7개를 전부 돌립니다**:

```powershell
$env:ANTHROPIC_API_KEY = "sk-ant-..."
python evals\run_extraction.py                                      # 기본 --poc poc1
python evals\run_extraction.py --case v6-no-third-party-provision   # 하나만
python evals\run_extraction.py --model claude-sonnet-5 --no-cache   # 비교 실행
```

위험 오판이 하나라도 있으면 exit code 1로 끝나므로 CI에 걸 수 있습니다.

채점만 따로:

```powershell
python evals\score.py evals\poc1\sc_p01_gold_facts.json evals\poc1\predictions\base.json
```

## 이 세트가 무엇인가

`tests/SC-P01_FINAL_Protege.ttl`의 사실관계와 정합하는 **처리방침 원문**과, 그 원문에서
추출되어야 하는 **Fact 38개**입니다. 원문은 NFR-06에 따른 가상 문서이며 실제 기업의
처리방침이 아닙니다.

Extractor가 이 원문을 입력받아 `sc_p01_gold_facts.json`의 `facts`와 같은 결과를 내면 만점입니다.

| 상태 | 개수 |
|---|---|
| confirmed | 28 |
| unknown | 3 |
| absent | 7 |

`expected_rule_status`는 SC-P01의 Freeze 기대값과 동일합니다. **P1-R02가 AMBER인 이유를
gold set이 그대로 담고 있습니다** — 제2조가 회원가입/고객상담의 보유 종료조건만 열거하고
주문·배송 / 결제·환불 / 서비스 개선은 "그 밖의 처리 목적" 한 문장으로 뭉뚱그리기 때문에,
해당 3개 activity의 F1-04가 `unknown`입니다.

## offset은 손으로 쓰지 않습니다

`build_gold_facts.py`는 근거 문자열을 원문에서 찾아 offset을 계산하고, 기대한 출현 횟수와
다르면 실패합니다. `tests/test_gold_facts_poc1.py`는 커밋된 JSON의 모든 offset이
`policy[start:end] == text`를 만족하는지 다시 검증합니다.

정답지의 offset이 정확하다는 보장이 있어야 Extractor의 offset 정확도를 지표로 쓸 수 있습니다.

## 정본 모듈 (통합 후)

Fact 파이프라인은 팀원(O_Jeon) 구현을 정본으로 통합했습니다. 같은 일을 하는 모듈이
두 벌이 되지 않도록 중복 계층은 삭제했습니다.

| 역할 | 정본 | 비고 |
|---|---|---|
| Fact 계약 검증 | `app/mapping/fact_schema.py` | 필수 필드·enum·중복 ID |
| Fact ID 레지스트리 | `app/mapping/mapping_registry.py` | F1/F2/F3 전체 |
| Fact -> RDF 매핑 | `app/mapping/ontology_mapper.py` | PoC1+2+3 |
| Form -> Fact | `app/builders/poc3_fact_builder.py` | PoC3 |
| 타입 Envelope + offset 검증 | `app/facts/models.py`, `validator.py` | 정본 계약 검증 위에 얹힘 |
| 타입 입력 Form | `app/forms/poc3.py` | API/UI 계약. 정본 Builder에 위임 |
| 매핑 헬퍼 | `app/facts/graph.py` | OntologyMapper 얇은 래퍼 |

`app/facts/validator.py`는 정본 계약 검증을 먼저 호출한 뒤 **근거 offset이 원문에서
실제로 그 문자열을 가리키는지**를 추가로 본다. LLM 추출 경로에만 필요한 검사라 정본에는
없다.

### 매핑 결함은 정본 쪽에서 해결되었습니다

Fact -> RDF 경로에서 Rule이 읽을 트리플이 없어 Freeze 기대값에 도달하지 못하던 문제들은
`origin/main`에서 정리되었습니다 (O_Jeon `bedbb69`, YENA `086d1d3` 외).

| 문제 | 해결 |
|---|---|
| `entrustedTaskText` / `noticeIncidentTime`이 그래프에 없어 P1-R06·P3-R11이 항상 RED | 매퍼가 그래프에 싣는다 |
| `measureRole`이 `system_metadata`에만 남아 P2-R08이 AMBER 고정 | 매퍼가 그래프에 싣는다 |
| `triggersNotificationObligation`이 Freeze에 없는데 P2-R01 필수 Fact였음 | [RULE_SPEC_ERRATA_v1.0.md](../docs/RULE_SPEC_ERRATA_v1.0.md)로 Required Fact에서 제거 |
| P3-R11이 수탁자명을 평가하지 않음 | F3-12를 `EntrustedProcessor.hasName`까지 소비 |
| `_finalize_global_destruction_links`가 임의의 Destruction을 붙임 | 함수 제거 |

### unknown / absent는 Fact envelope으로 전달합니다

매퍼는 **confirmed만 RDF로 냅니다.** unknown과 absent의 구분은 Rule Engine이 Fact
envelope을 함께 받아 유지합니다
([RULE_ENGINE_FACT_DICTIONARY_ALIGNMENT](../docs/RULE_ENGINE_FACT_DICTIONARY_ALIGNMENT_20260923.md)).

```python
mapping = facts_to_mapping(facts)          # graph + 정규화된 facts
engine.evaluate_mapping_result(mapping, poc="poc1")
```

그래프만 넘기면(`evaluate_graph(graph)`) 엔진이 unknown과 absent를 구별할 수 없어
Rule Matrix의 AMBER 분기에 도달하지 못합니다.

## Day 0 결정 필요 — 여기서 임의로 정한 규약

Fact Dictionary v1.0에 명시가 없어 제가 정한 것들입니다. **확정이 아니라 제안입니다.**

| # | 규약 | 대안 |
|---|---|---|
| 1 | `fact_id` = `"F1-02:act-collection-001"` (F-ID를 fact_id에 인코딩) | envelope에 `fact_type` 시스템 필드 추가 |
| 2 | `activity_id` = `act-{collection\|provision\|entrust\|destruction\|crossborder}-{nnn}` | 다른 채번 규칙 |
| 3 | `evidence` = `{text, start_offset, end_offset}` | 2장은 "text+offset"이라고만 적혀 있어 필드명 미정 |
| 4 | `_note` = 비계약 주석 (언더스코어로 계약 필드와 구분) | 제거하거나 정식 필드로 승격 |
| 5 | F1-03 `absent` — 처리방침이 숫자 기간 없이 종료조건만 기재 | `unknown`으로 볼 수도 있음. **Extractor 동작이 달라지므로 반드시 합의 필요** |
| 6 | F1-04 미연결 3건 `unknown` — 일반 보유 문장은 있으나 activity 연결 불명 | 이 판단이 P1-R02 AMBER를 만듭니다 |

### 7. 값 담는 위치 — 정본 레지스트리를 따릅니다

`app/mapping/mapping_registry.py`의 `FACT_SPECS`가 Fact ID별 `subject_class`와
`ontology_property`를 고정합니다. gold set은 이 레지스트리에 맞춰 생성됩니다.
중간 개체(`ProcessingPurpose`, `Retention`, `ThirdParty` 등)는 매퍼가 만듭니다.

| Fact | gold set이 싣는 것 |
|---|---|
| F1-02 | `act -hasPurpose-> "문자열"` |
| F1-03 / F1-04 | `act -hasRetention-> "문자열"` (기간/종료조건은 Fact ID로 구분) |
| F1-05 | `act -hasRecipient-> "문자열"` |
| F1-06 | `act -hasPersonalInformation-> ["항목", ...]` |
| F1-09 | `act -hasProcessor-> "수탁자명"` |

### 8. F1-12는 권리별로 하나씩 냅니다

처리방침은 4개 권리에 공통 절차 1문장을 기재하지만, **엔진은 모든 `DataSubjectRight`에
`hasExerciseProcedure`가 있어야 P1-R07을 GREEN으로 줍니다**
(`test_p1_r07_partial_right_procedures_are_amber_not_green`).

그래서 gold set은 F1-12를 권리 수만큼 내고, 값이 `{"right": ..., "procedure": ...}`로
어느 권리에 대한 절차인지 스스로 밝힙니다. 근거는 같은 문장입니다.
Fact Dictionary에는 이 규칙이 없습니다.

## 이 세트를 만들면서 발견한 Fact Dictionary 결손

명세서 §14-3에 따라 Issue로 올릴 것들입니다.

1. **CrossBorderTransfer의 존재를 나타낼 Fact ID가 없습니다.** F1-01은 `CollectionAndUse`
   전용입니다. P1-R02는 CrossBorderTransfer도 평가하므로, gold set은 F1-03/F1-04의
   `ontology_class`를 `CrossBorderTransfer`로 두는 방식으로 우회했습니다
   (F1-03/F1-04의 매핑이 상위 클래스 `PersonalInformationProcessing`이라 위반은 아닙니다).
   `Destruction`과 `EntrustedProcessing`도 같은 상황이며, 각각 F1-08 / F1-09+F1-10으로
   존재가 암시됩니다.

2. **F1-11(array) ↔ F1-12(권리별) 정렬 규칙이 없습니다.** 위 8번 항목.

3. **CollectionAndUse의 수집항목에 Fact ID가 없습니다.** PoC1은 제3자 제공 항목(F1-06)만
   정의합니다. Fact Dictionary 범위 원칙("P0 18개 Rule이 실제로 소비하는 Fact만 정의")상
   맞지만, **원문에는 수집 항목이 또렷하게 적혀 있어서 Extractor가 뽑고 싶어 합니다.**
   프롬프트에서 명시적으로 금지해야 합니다 — 안 그러면 스키마에 없는 Fact를 만들어 내고
   COM-002 validation에서 전부 reject됩니다.

4. **처리행위 유형의 부재를 표현할 Fact ID가 없습니다.** 3·4·5장은 35개 Fact를
   정의하는데, 그중 "이 유형의 처리행위를 하지 않는다"를 담을 자리가 없습니다.
   8장은 미기재를 `value_state=absent`로 유지하라고 하지만, 처리행위 자체가 없으면
   귀속시킬 `activity_id`가 없습니다. 그 결과 **N/A는 Fact 경로로 도달할 수 없고**
   손으로 쓴 RDF(`test:thirdPartyProvisionState "confirmed_false"`)로만 나옵니다.
   v1.0의 한계이므로 개정 사항으로 올립니다.

5. **타입이 `instance`인 Fact(F3-01/F3-03/F3-06)는 Envelope에 담을 자리가 애매합니다.**
   리터럴 값이 아니라 연결 대상 개체를 가리키기 때문입니다. 정본은 값 객체
   (`{"planned": true}`, `{"end_condition": ...}`)로 표현합니다.

6. **F3-06과 F3-10이 같은 Ontology 구조를 가리킵니다.** 각각 P3-R04와 P3-R08에 쓰이지만
   둘 다 `Retention`으로 수렴합니다. 정본 매퍼가 같은 노드로 모아 트리플이 중복되지 않습니다.

## Extractor 설계 — offset을 LLM에게 시키지 않습니다

`app/extractors/poc1.py`는 2-pass입니다.

| Pass | 입력 | 출력 |
|---|---|---|
| 1 | 처리방침 전체 | 처리행위 목록 + `activity_id` |
| 2 | 처리행위 **1개** | 그 처리행위의 Fact만 |

1-pass로 문서 전체에서 Fact를 뽑으면 제3자 제공 A의 수령자와 B의 목적이 섞입니다
(TST-002). Pass 2를 처리행위 단위로 쪼개면 **프롬프트 경계가 곧 activity 경계**가 되어
혼합이 구조적으로 불가능해집니다. 그래도 모델이 다른 `activity_id`를 붙여 오면 후처리가
버립니다.

LLM은 **근거 문장을 원문 그대로 인용**하기만 하고, offset은 `locate_quotes()`가 찾습니다.
결과가 둘입니다.

1. offset이 항상 정확합니다. LLM의 char offset은 신뢰할 수 없습니다.
2. **원문에서 찾지 못한 인용은 그 Fact를 통째로 버립니다.** 환각 탐지가 파이프라인에
   내장됩니다 (NFR-07).

Pass 2는 처리행위 수만큼 호출되는데 원문은 매번 같으므로, 지침을 앞에 두고 원문 블록에
`cache_control`을 겁니다.

## 채점 지표

### Fact-level

| 지표 | 의미 |
|---|---|
| precision / recall / F1 | `(fact_id, activity_id, value_state)` 일치 기준 |
| value 정확도 | 위 키가 맞은 Fact 중 값까지 맞은 비율 |
| offset 정확도 | 근거가 원문에서 실제로 그 문자열을 가리키는 비율 |
| 환각률 | 원문에 없는 값을 실은 Fact 비율 (NFR-07) |
| activity 혼합률 | 다른 처리행위의 값을 가져온 Fact 비율 (TST-002) |

`value_state`를 일치 키에 넣은 이유는 **unknown을 confirmed로 잘못 판정하는 것이 가장
위험한 오류**이기 때문입니다. AMBER여야 할 Rule이 GREEN이 됩니다.

### Rule-level — 이게 헤드라인입니다

문서 7개 × Rule 6개 = **42개 판정**을 gold와 비교합니다.

| 지표 | 의미 |
|---|---|
| status 일치율 | 42개 중 gold와 같은 판정이 나온 비율 |
| **위험 오판율** | gold가 GREEN이 아닌데 **GREEN으로 예측한** 비율 |

Fact를 몇 개 맞췄는지보다 **"추출 오류가 판정을 뒤집는가"**가 중요합니다. Fact 하나를
놓쳐도 판정이 안 바뀌면 실무 영향이 없고, 반대로 `value_state` 하나를 틀려서 AMBER가
GREEN이 되면 준수한 것처럼 보이게 됩니다.

**일치율만 보면 안 되는 이유**: 아무것도 안 하고 전부 GREEN이라고 우기는 추출기도
일치율 **0.69**가 나옵니다 (42건 중 29건). 이 기준선은
`tests/test_eval_sweep.py::test_predicting_green_everywhere_is_caught_as_dangerous`에
고정해 뒀습니다. 위험 오판율(그 경우 0.31)을 같이 봐야 합니다.

## 프롬프트가 정본에서 낡지 않게 막습니다

`tests/test_prompt_contract.py`

프롬프트는 LLM에게 "이 Fact ID에는 이 `ontology_property`를 쓰라"고 지시합니다.
정본 레지스트리가 바뀌면 그 지시만 조용히 낡고, **증상은 실제 API 실행 때 "추출은 됐는데
검증에서 전부 reject"라는 형태로 처음 드러납니다.** 돈을 쓰고 나서야 알게 되는 자리입니다.

실제로 그 상태였습니다. 통합 시점에 세 건이 어긋나 있었습니다.

| Fact | 프롬프트가 지시하던 값 | 정본 |
|---|---|---|
| F1-03 | `hasRetentionPeriod` | `hasRetention` |
| F1-04 | `hasRetentionEndCondition` | `hasRetention` |
| F1-09 | `hasName` | `hasProcessor` |

F1-12는 값 타입과 개수가 함께 틀려 있었습니다. "문자열 하나"로 안내했는데 엔진은 모든
`DataSubjectRight`에 `hasExerciseProcedure`를 요구하므로, 시킨 대로 하나만 내면
나머지 권리가 절차 없는 것으로 취급되어 P1-R07 판정이 뒤집힙니다.

이제 카탈로그가 property 이름을 다시 적지 않고 `FACT_SPECS`에서 끌어옵니다.
그리고 네 가지를 테스트로 고정했습니다.

- 카탈로그 property == **정답지** property (레지스트리를 거치지 않는 대조)
- 프롬프트 산문에 손으로 적은 property 이름도 훑기
- 선언한 값 타입 == 정답지의 실제 값 타입 (F1-12 같은 사고를 잡는 자리)
- 레지스트리에 Fact가 늘면 프롬프트도 늘어야 함

F1-03과 F1-04가 같은 property를 쓰게 되었으므로, 값의 성격으로 둘을 가르는 규칙
(기간이면 F1-03, 종료 사건이면 F1-04)을 PASS2 프롬프트에 명시했습니다.

## 정본 파이프라인에 연결되어 있습니다

`app/extractors/poc1_llm_extractor.py`의 `LlmPoC1Extractor`가 `Poc1Extractor`
Protocol을 구현합니다 (`app/extractors/base.py`). 주입만 하면 실제 API 경로가 됩니다.

```python
from app.extractors.poc1_llm_extractor import LlmPoC1Extractor
from app.services.compliance import run_policy_check

run_policy_check(request, extractor=LlmPoC1Extractor.from_environment())
```

`from_environment()`는 `ANTHROPIC_API_KEY`를 SDK가 직접 읽게 하고 이 코드가 키 값을
보지 않습니다. 키가 없으면 실행 전에 실패합니다.

**기본값은 여전히 `MockPoC1Extractor`입니다.** `app/services/compliance.py`의
모듈 기본값을 바꾸면 `/policy-check` 호출마다 과금되므로, 실제 연결은 키가 준비된
뒤 팀이 결정합니다 (handoff 6장).

### 연결하면서 드러난 Extractor 결함 3건

정본 `validate_facts()`와 `OntologyMapper`를 통과시키자 그동안 안 보이던 것들이
나왔습니다. 제 테스트가 정본이 아니라 `app.facts.models.FactEnvelope`로만 검증하고
있어서 가려져 있었습니다.

| 결함 | 증상 | 근거 |
|---|---|---|
| F1-09의 subject를 수탁자 개체로 둠 | 매퍼가 `ontology_class='EntrustedProcessor'` 거부 | 3장 매핑의 출발 Class는 `EntrustedProcessing` |
| F1-12의 subject Class가 `DataSubject` | 매퍼가 `DataSubjectRight` 기대값과 불일치로 거부 | 3장 F1-12 = `DataSubjectRight.hasExerciseProcedure` |
| 같은 subject의 동형 Fact가 fact_id 충돌 | 권리 4개의 F1-12가 전부 `F1-12:subj-001` → "중복 fact_id" | P1-R07은 권리마다 절차를 요구 |

`tests/test_poc1_llm_extractor.py`가 이제 정본 검증기와 매퍼, Rule Engine까지
한 번에 통과시키므로 같은 유형의 결함이 다시 숨지 않습니다.

## 아직 실행하지 않았습니다

Extractor는 **실제 API로 한 번도 돌리지 않았습니다.** 자격증명이 없고, 모델 호출은 비용이
발생하므로 승인 없이 실행하지 않았습니다. 테스트는 `messages.parse`를 스텁으로 갈아끼워
후처리 로직만 검증합니다 (`tests/test_extractor_and_score.py`).

첫 실행 때 확인할 것:

- `--no-cache`와 비교해 `usage.cache_read_input_tokens`가 실제로 올라가는지
- 거부된 Fact의 사유 분포 — 인용 불일치가 많으면 프롬프트 4번 규칙을 강화
- 수집 항목(제1조)을 Fact로 만들어 내는지 — 프롬프트 5번 규칙이 듣는지

## PoC1 Controlled Variants (TST-003)

SC-P01 하나로는 GREEN과 AMBER만 나옵니다. `evals/poc1/variants/`의 6개 변형이 나머지를 채웁니다.

```powershell
python evals\poc1\build_variants.py
python -m pytest -q tests\test_variants_poc1.py
```

| 변형 | 조작 | 결과 |
|---|---|---|
| v1-missing-purpose | 처리 목적 문장 삭제 | P1-R01 **RED** |
| v2-vague-destruction | "적절한 방법으로 파기" | P1-R04 **AMBER** |
| v3-missing-destruction | 파기 방법 기재 삭제 (F1-08 `absent`) | P1-R04 **RED** |
| v4-unknown-processor | "수탁자: 추후 선정 예정" | P1-R06 **AMBER** |
| v5-missing-processor | 수탁자명 기재 삭제 | P1-R06 **RED** |
| v6-no-third-party-provision | "제3자에게 제공하지 않습니다" 명시 | P1-R03 **AMBER** |

문서를 편집하면 글자 위치가 전부 밀리므로, 빌더가 **변형 문서에서 근거를 다시 찾아** offset을
새로 계산합니다. 근거를 찾지 못했는데 변형 정의가 처리하지 않았다면 빌더가 실패합니다.

각 변형은 겨냥한 Rule **하나만** 움직여야 하며, 이것도 테스트로 강제합니다.

### N/A는 이 변형 세트로 만들 수 없습니다

v6는 "제3자에게 제공하지 않습니다"를 명시하지만 결과는 N/A가 아니라 **AMBER**입니다.
Fact Dictionary에 처리행위 유형의 부재를 담을 Fact ID가 없어서, 제3자 제공 Fact가
그냥 사라질 뿐이기 때문입니다 (위 결손 4번).

대신 **absent와 unknown의 구분**은 v2와 v3이 보여줍니다. 같은 P1-R04를 v2(파기방법
`unknown`)는 AMBER로, v3(파기방법 `absent`)는 RED로 움직입니다. Fact를 아예 빼면
"입력 계약 불완전"으로 AMBER가 되므로, 기재가 없을 때는 Fact를 빼지 말고
`value_state="absent"`로 유지해야 합니다 (8장).

## PoC3 Privacy-by-Design

LLM을 쓰지 않습니다. `evals/poc3/sc_d01_form.json`이 SC-D01 설계와 정합하는 구조화 Form이고,
`app/forms/poc3.py`가 이를 F3-01~F3-13으로 변환합니다.

```powershell
python -m pytest -q tests\test_poc3_form.py
```

Form 45개 Fact → 트리플 145개 → **8개 Rule 전부 GREEN** (SC-D01 Freeze 기대값 재현).
근거는 text+offset이 아니라 `field_path`를 씁니다 (예:
`collection_activities[0].design_items[2].is_required`).

Form 값 하나만 바꾸면 상태가 전이되므로 PoC3의 변형은 별도 문서가 필요 없습니다.

| Form 변경 | 결과 |
|---|---|
| `legal_basis: null` | P3-R01 AMBER |
| `design_rationale: null` (필수항목) | P3-R05 AMBER |
| `denies_service_on_optional_refusal: true` | P3-R06 **RED** |
| `denies_service_on_optional_refusal: null` | P3-R06 AMBER |
| `destruction_method: null` | P3-R08 AMBER |
| `entrustments: []` | P3-R11 AMBER |

`false`와 `null`이 다른 결과를 낸다는 점이 핵심입니다. Form Builder가 `if not value`로
판정하면 둘이 같아져 Fact Dictionary 1장을 위반합니다.

## A에게

`sc_p01_gold_facts.json`의 `facts`를 `facts_to_graph()`에 넣어 `/console`에서 보면
`expected_rule_status`가 재현됩니다. 이 세트는 매핑 테이블의 정답지입니다.

매퍼가 만든 그래프는 evidence 128건 중 74건이 원문 근거를 싣습니다. SC-P01 TTL은 0건이었으므로,
**PoC1의 근거 경로(COM-008)가 이제 처음으로 실제로 동작합니다.** 다만 offset은 여전히
유실됩니다 — `pipa:hasSourceEvidence`가 문자열 annotation이라 담을 자리가 없습니다
(위 계약 결손 2번).
