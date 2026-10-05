# Extractor 평가 세트

LLM Fact Extractor의 정답지와 채점기입니다. Rule Engine이 아니라 **Extractor**를 평가합니다.

> **최종 결과는 [RESULTS.md](RESULTS.md)에 있습니다.** 이 문서는 세트 구성, 규약, 작업 기록입니다.

```text
evals/
├─ dataset.py                  # PoC별 평가 세트 탐색 (POC_DATASETS)
├─ score.py                    # Fact-level 채점기
├─ run_extraction.py           # 실제 추출 + 채점 (API 호출)
├─ compare_runs.py             # 실행 간 비교 (API 호출 없음)
└─ poc1/
   ├─ sc_p01_policy.txt        # 처리방침 원문 (가상)
   ├─ sc_p01_gold_facts.json   # gold Fact set (생성물)
   ├─ build_gold_facts.py      # 생성기
   └─ variants/                # controlled variants 6개
└─ poc2/
   ├─ sc_p02_incident.txt      # 사고 기록 (가상)
   ├─ sc_p02_notice.txt        # 통지문 (가상)
   ├─ sc_p02_gold_facts.json   # gold Fact set (생성물)
   ├─ build_gold_facts.py      # 생성기
   └─ variants/                # controlled variants 5개
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

`expected_rule_status`는 SC-P01의 Freeze 기대값과 동일합니다. **P1-R02가 YELLOW인 이유를
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
| `measureRole`이 `system_metadata`에만 남아 P2-R08이 YELLOW 고정 | 매퍼가 그래프에 싣는다 |
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
Rule Matrix의 YELLOW 분기에 도달하지 못합니다.

## Day 0 결정 필요 — 여기서 임의로 정한 규약

Fact Dictionary v1.0에 명시가 없어 제가 정한 것들입니다. **확정이 아니라 제안입니다.**

| # | 규약 | 대안 |
|---|---|---|
| 1 | `fact_id` = `"F1-02:act-collection-001"` (F-ID를 fact_id에 인코딩) | envelope에 `fact_type` 시스템 필드 추가 |
| 2 | `activity_id` = `act-{collection\|provision\|entrust\|destruction\|crossborder}-{nnn}` | 다른 채번 규칙 |
| 3 | `evidence` = `{text, start_offset, end_offset}` | 2장은 "text+offset"이라고만 적혀 있어 필드명 미정 |
| 4 | `_note` = 비계약 주석 (언더스코어로 계약 필드와 구분) | 제거하거나 정식 필드로 승격 |
| 5 | **결정됨 (2026-09-30, Issue 4)**. "관계 법령에서 정한 기간"처럼 법령도 숫자도 특정하지 않은 기간은 **법령을 연동해 채우지 않고 알 수 없음**으로 둔다 → 그 문장에만 걸리는 3건은 F1-03 `unknown`. 종료조건이 명시된 처리행위는 F1-03 `absent` | 아래 "관계 법령" 절 |
| 6 | **결정됨**. 같은 3건의 F1-04는 `absent` — 그 문장은 기간을 말할 뿐 끝나는 사건을 말하지 않는다 | P1-R02는 그대로 YELLOW |

### "관계 법령에서 정한 기간" — 연동하지 않고 알 수 없음으로 둡니다

처리방침이 법령 이름을 적지 않으면 어느 법령인지 문서만으로는 알 수 없습니다. 업종을 보고
"전자상거래법일 것"이라고 채우는 것은 사실 추출이 아니라 법적 판단이고, 법정 보존기간은
P0 범위 밖의 시행령 수치입니다 (CLAUDE.md §5). 그래서 연동하지 않고 `unknown`으로 두며,
P1-R02 YELLOW가 "근거 법령·기간 미특정, 확인 필요"를 드러냅니다.

| 원문 | F1-03 |
|---|---|
| "관계 법령에서 정한 기간 동안 보관" | `unknown` (법령·값 미특정) |
| "전자상거래 등에서의 소비자보호에 관한 법률에 따라 5년간 보관" | `confirmed` "5년간" |
| "법령에 따른 보유·이용 기간 내에서 처리합니다" (조 첫머리 일반 원칙) | 특정 처리행위의 기재가 아님. 종료조건이 명시된 처리행위를 `unknown`으로 만들지 않음 |
| "일정 기간", "필요한 기간" | `unknown` (길이도 사건도 모름) |
| "서비스 이용기간 동안", "계약 기간 동안" | F1-03이 아니라 **F1-04** (사건으로 끝남). F1-03은 `absent` |

**기준: "기간"이라는 단어가 아니라 끝이 어떻게 정해지는지로 가릅니다.** 시간 길이로 끝이
정해지면("3년간") F1-03, 사건으로 정해지면("회원 탈퇴 시", "서비스 이용기간 동안") F1-04,
길이도 사건도 알 수 없으면 F1-03 `unknown`입니다. 둘 다 "언제 파기하는지"를 알려주지만
Fact Dictionary가 시간 길이와 사건을 다른 Fact로 나눠 두었으므로 그 구분을 따릅니다.

프롬프트의 Fact 설명도 이 기준으로 적었습니다. Fact Dictionary의 이름("보유 기간")은
동결이라 바꾸지 않고, 모델이 읽는 **설명 문구만** 바꿨습니다. "활용 기간"은 쓰지 않습니다.
이용이 끝난 뒤 법령에 따라 보관만 하는 기간도 보유에 들어가기 때문입니다.

| Fact | 프롬프트 설명 (Extractor 내부) |
|---|---|
| F1-03 | 보유 기간의 길이 — 숫자와 단위로 적힌 시간 (예: 3년, 6개월) |
| F1-04 | 보유를 끝내는 사건 (예: 회원 탈퇴 시, 서비스 이용 종료 시) |

Fact Dictionary 본문에도 같은 설명을 덧붙일지는 Fact 담당자 결정 사항입니다(§14-3).

프롬프트 PASS2 7번 규칙에 같은 기준이 있습니다.

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
(`test_p1_r07_partial_right_procedures_are_yellow_not_green`).

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
   귀속시킬 `activity_id`가 없습니다. **해결됨**: 부재는 Fact가 아니라 activity
   presence metadata(`app/mapping/presence_metadata.py`)로 싣습니다. 35개 Fact는
   그대로입니다. 아래 "N/A 경로" 참고.

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
위험한 오류**이기 때문입니다. YELLOW여야 할 Rule이 GREEN이 됩니다.

### Rule-level — 이게 헤드라인입니다

문서 7개 × Rule 6개 = **42개 판정**을 gold와 비교합니다.

| 지표 | 의미 |
|---|---|
| status 일치율 | 42개 중 gold와 같은 판정이 나온 비율 |
| **위험 오판율** | gold가 GREEN이 아닌데 **GREEN으로 예측한** 비율 |

Fact를 몇 개 맞췄는지보다 **"추출 오류가 판정을 뒤집는가"**가 중요합니다. Fact 하나를
놓쳐도 판정이 안 바뀌면 실무 영향이 없고, 반대로 `value_state` 하나를 틀려서 YELLOW가
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

## PoC2 — 사고/통지 분리를 호출 경계로 강제합니다

`app/extractors/poc2.py`는 **사고 기록과 통지문을 서로 다른 호출로** 처리합니다.

```text
사고 pass   사고 기록만 본다  -> F2-01, F2-02, F2-05, F2-06, F2-10
통지 pass   통지문만 본다     -> F2-03, F2-04, F2-07, F2-08, F2-09
```

기능명세서 6장의 핵심 원칙이 "실제 사고 Fact와 통지문에 적힌 Fact를 절대 합치지
않는다"이고 Fact Dictionary 8장도 F2-02↔F2-04, F2-05↔F2-08을 합치지 말라고
못박습니다. 한 호출에 두 문서를 같이 주면 모델이 빈 칸을 상대 문서로 메우려 합니다.
호출을 나누면 **프롬프트 경계가 곧 사고/통지 경계**가 되어 혼합이 구조적으로
불가능해집니다. PoC1에서 처리행위별로 Pass 2를 쪼갠 것과 같은 이유입니다.

그래도 한쪽 pass가 상대편 Fact ID를 내면 후처리가 버립니다. 근거 offset도 그
Fact를 낸 문서에서만 찾으므로, 상대 문서의 문장을 인용하면 그 Fact는 탈락합니다.

| 방어 | 무엇을 막나 |
|---|---|
| 호출 분리 | 모델이 상대 문서를 볼 수 없다 |
| Fact ID 화이트리스트 | 사고 pass의 F2-04, 통지 pass의 F2-02를 버린다 |
| 문서별 인용 대조 | 없는 문장을 인용하면 그 Fact를 버린다 (NFR-07) |
| `measure_role` enum 검사 | 4장의 4종 외 값과 중복 역할을 버린다 |

통지문이 제공되지 않으면 통지문을 **지어내지 않고** F2-03/04/07/08/09를
`absent` + `source_type="derived"`로 남깁니다 (EXTRACTOR_DECISIONS #6).

`tests/test_poc2_llm_extractor.py`가 이 경계들을 고정합니다. 특히
`test_each_pass_only_sees_its_own_document`는 실제 호출 인자를 뒤져서 사고
프롬프트에 통지문 문장이 섞이지 않았는지 확인합니다.

## SC-P02 gold set

`evals/poc2/`. 문서가 둘이라는 점이 PoC1과 다릅니다.

| | |
|---|---|
| 입력 | `sc_p02_incident.txt` (사고 기록) + `sc_p02_notice.txt` (통지문) |
| 정답지 | F2-01~F2-10 **10개** — 사고 4 · 통지문 5 · derived 1 |
| Rule 기대값 | P2-R01/R02/R03/R08 **전부 GREEN** (`tests/SC-P02_FINAL_Protege.ttl` Freeze) |

```powershell
python evals\poc2uild_gold_facts.py
python -m pytest -q tests	est_gold_facts_poc2.py
```

### 근거를 문서별로 찾습니다

빌더의 `inc()`는 사고 기록에서, `note()`는 통지문에서만 근거를 찾습니다. 한 문서에서
찾지 못하면 다른 문서를 뒤지지 않고 실패합니다. 이 분리가 Fact Dictionary 8장의
"F2-02와 F2-04, F2-05와 F2-08을 합치지 않는다"를 **빌더 단계에서** 강제합니다.

`EvalCase.document_for(source_type)`이 채점 단계에서 같은 선택을 합니다.
`incident_record`는 사고 기록, `notification_notice`는 통지문, `derived`는 양쪽입니다.

### F2-05와 F2-08은 값이 같습니다

Freeze 시나리오에서 실제 사고 발생시점과 통지문 기재 시점이 둘 다
`2026-09-05T14:30:00+09:00`입니다. **값이 우연히 같은 경우가 가장 헷갈리므로**
정답지가 그 경우를 일부러 담습니다. 둘은 subject도, source_type도, 근거 문장도
다릅니다 — 하나를 다른 하나에서 파생시키면 그 차이가 사라지고
`test_incident_date_and_notice_stated_time_are_separate_facts`가 깨집니다.

### 평가 하네스에 등록되어 있습니다

```powershell
python evals\run_extraction.py --poc poc2
```

`EvalCase.extract_with()`가 PoC별 Protocol 호출 규약(PoC1은 `policy_text`,
PoC2는 `incident` + `notification`)을 흡수하므로 러너는 PoC를 몰라도 됩니다.

### PoC2 Controlled Variants (TST-003)

| 변형 | 조작 | 결과 |
|---|---|---|
| v1-incident-missing-items | 사고 기록의 실제 영향 항목 삭제 | P2-R01 **RED** + P2-R02 RED |
| v2-notice-omits-items | 통지문의 항목 기재 삭제 | P2-R02 **RED** |
| v3-notice-missing-incident-time | 통지문의 유출 시점 기재 삭제 | P2-R03 **RED** |
| v4-partial-response-measures | 대응조치 4종 중 2종만 남김 | P2-R08 **YELLOW** |
| v5-no-response-measures | 대응조치 기재를 통째로 삭제 | P2-R08 **RED** |

```powershell
python evals\poc2uild_variants.py
python -m pytest -q tests	est_variants_poc2.py
```

**v1은 Rule 두 개를 움직입니다.** F2-02를 7장 Coverage가 P2-R01과 P2-R02에서 함께
소비하기 때문입니다. 그래서 PoC1처럼 "변형 하나가 Rule 하나만 움직인다"로 고정하지
않고, **움직인 Rule이 그 Fact를 소비한다고 7장이 적은 Rule 안에 드는지**를 봅니다.
그 밖의 Rule이 움직이면 변형이 문서를 의도보다 넓게 건드린 것입니다.

v4와 v5를 나눈 이유는 P2-R08에서 **"역할 분류가 모호한 경우"(YELLOW)와 "대응조치를
안 한 경우"(RED)**가 달라야 하기 때문입니다. 둘이 같아지면 판정이 구별력을 잃습니다.

## 남은 일

1. 캐시 효과 실측(`--no-cache`), 수정 후 Opus 5 재비교
2. (다음 범위 후보) 문서 안 "관계 법령에 따라 아래와 같이" 참조를 목록과 연결하고,
   보유 근거 법령을 담을 Fact 신설을 검토 — Fact Dictionary 개정(§14-3)이 필요하다

해결된 것: Day 0 5·6번(Issue 4, 위 표), 근거 인용의 줄바꿈 허용(아래 "근거 인용").

### 근거 인용 — 공백만 다르면 원문 위치로 되찾습니다

원문에서 줄이 바뀐 문장을 모델이 한 줄로 이어 인용하면 정확히 일치하지 않아 Fact가
거부됐습니다 (PoC2 v1: F2-01 거부 -> P2-R08 GREEN이 YELLOW). 이제 정확히 일치하는
곳이 없으면 **공백만 다른** 곳을 찾고, 근거에는 모델 인용이 아니라 **원문 구간**을
담습니다. offset은 항상 원문을 가리키고 공백이 아닌 글자는 모두 일치해야 하므로
NFR-07은 그대로입니다. 모델 인용에 공백이 있는 자리에서만 허용합니다.

## 실행 전에 알아야 할 것 — 호출량과 비용

전체 스윕은 **109회 호출**입니다. 측정치입니다(추정이 아닙니다).

| PoC | 케이스 | 케이스당 호출 | 소계 |
|---|---|---|---|
| PoC1 | 7 | 1(Pass1) + 처리행위 수(Pass2) + 1(권리) = 13~14 | 97 |
| PoC2 | 6 | 2 (사고 + 통지) | 12 |

PoC1이 비싼 이유는 **처리행위가 12개**라 케이스마다 Pass 2가 12번 돌기 때문입니다.
원문은 매번 같으므로 `cache_control`이 걸려 있고, Pass 2 2회차부터 캐시에서 읽습니다.

다만 **Pass 1과 권리 pass는 캐시를 타지 못합니다.** 캐시 prefix는 처음부터 정확히
일치해야 하는데 지침 블록이 pass마다 달라서, 원문 블록이 같아도 prefix가 어긋납니다.
캐시가 실제로 먹는 구간은 같은 `PASS2_SYSTEM`을 쓰는 12번의 Pass 2뿐입니다.

입력 문자 수를 세어 토큰으로 환산하면(한국어 문자당 약 1.4토큰) 캐시 적용 기준
입력 약 40만 토큰, 출력은 호출당 1,500토큰으로 잡아 약 16만 토큰입니다.
**출력 추정은 근거가 약합니다** — `thinking: adaptive`가 얼마나 쓸지 모르기 때문이며,
첫 실행에서 `usage`를 보고 고쳐야 합니다.

이 수치에 단가를 곱하면 Opus 기준 한 자릿수 달러, Sonnet 기준 그 절반 수준입니다.
**단가는 실행 직전에 확인하세요.** 한 PoC만 돌리려면 `--poc`, 한 케이스만 돌리려면
`--case`를 씁니다.

```powershell
python evals\run_extraction.py --poc poc2                    # 12회 호출
python evals\run_extraction.py --case base                   # 14회 호출
```

## 실행 결과는 실행마다 따로 남습니다

실행마다 `<out-dir>/runs/<label>.json`이 생깁니다. label 기본값은
`<poc>-<model>-cache|nocache`이고 `--label`로 바꿀 수 있습니다. **덮어쓰지 않으므로
모델 비교와 캐시 효과 측정이 가능합니다.**

```powershell
python evals\run_extraction.py --model claude-opus-5
python evals\run_extraction.py --model claude-sonnet-5
python evals\run_extraction.py --no-cache
python evals\compare_runs.py evals\poc1\predictions\runs
```

`compare_runs.py`는 추출 품질과 호출량을 표로 세우고 **위험 오판율로 순위를**
매깁니다. F1이 아닙니다 — Fact를 몇 개 맞췄는지보다 "추출 오류가 판정을 뒤집는가"가
실무 영향이기 때문입니다.

## 호출량을 기록합니다

각 응답의 `usage`를 `app/extractors/usage.py`가 누적하고, 추출 결과와 실행
리포트에 함께 실립니다.

| 값 | 왜 보는가 |
|---|---|
| `calls` | 호출 수 |
| `total_input_tokens` | 캐시 쓰기·읽기 포함. 빼먹으면 비용을 과소평가한다 |
| `output_tokens` | `thinking: adaptive` 사용량 실측 |
| `cache_hit_rate` | **0이면 캐시가 전혀 안 먹은 것** |

`cache_hit_rate`가 중요합니다. 프롬프트에 `cache_control`을 걸었다는 사실만으로는
캐시가 먹었는지 알 수 없습니다. 캐시 prefix는 처음부터 정확히 일치해야 하는데
지침 블록이 pass마다 다르면 원문 블록이 같아도 어긋납니다. 이 값이 예상보다 낮으면
프롬프트 구조를 고쳐야 한다는 신호입니다.

스텁으로 돌린 결과는 토큰이 0이므로 `format_usage()`가 "토큰 정보 없음"이라고
분명히 적습니다. 스텁 실행을 실제 측정치처럼 보이게 하지 않기 위해서입니다.

## 자격증명

환경변수에서만 읽습니다. 키를 인자나 소스에 넣지 않습니다.

```powershell
$env:ANTHROPIC_API_KEY = "sk-ant-..."
```

`from_environment()`가 변수 유무를 먼저 보고 요청 전에 실패하므로, 키가 없으면
SDK 내부 오류 대신 안내 문구가 나옵니다. `.env` 파일은 아무것도 자동으로 읽지
않습니다 — 셸에서 export 해야 합니다.

## 첫 실행 결과 (claude-sonnet-5, dev `base` 케이스만)

| | PoC1 base | PoC2 base |
|---|---|---|
| 호출 | 14회 | 2회 |
| Rule 판정 일치 | 6/6 | 4/4 (수정 전 2/4) |
| 위험 오판(GREEN) | 0 | 0 |
| Fact F1 | 0.853 | 1.000 |
| 환각률 | 0.000 | 0.000 (수정 전 0.200) |

첫 실행에서 스텁 테스트가 못 잡은 결함 3건이 나왔고 모두 고쳤습니다.

- `value: Any`가 structured outputs 스키마 변환에서 거부됨 →
  `tests/test_output_schemas.py`가 SDK와 같은 변환을 로컬에서 돌립니다
- F2-03 `notice_id`를 모델이 원문 문서번호로 채워 통지문 노드가 갈라짐 →
  P2-R02/R03이 RED. 이제 Extractor가 `breach-notice`로 고정합니다
- 날짜를 한국어 표기로 냄 → KST ISO 8601로 저장하고(팀 결정), 화면에는
  `yyyy-mm-dd hh:mm (KST)`로 표시합니다

**PoC2 base는 이 수정에 쓰였으므로 더 이상 공정한 점수가 아닙니다.** 일반화는
아래 held-out 세트로만 말합니다.

PoC1에서는 F1-03 absent 7건이 근거 인용이 비어 거부됐습니다. 기재가 없는 항목에서
무엇을 인용할지 프롬프트가 알려주지 않았기 때문이며, 커밋 `9ad60af`에서 고쳤습니다
(거부 6 -> 0).

실행 때 계속 확인할 것:

- **실제 `usage`로 위 추정을 교정** — 특히 출력 토큰. adaptive thinking 사용량을 모른다
- `--no-cache`와 비교해 `usage.cache_read_input_tokens`가 실제로 올라가는지
- 거부된 Fact의 사유 분포 — 인용 불일치가 많으면 프롬프트 4번 규칙을 강화
- 수집 항목(제1조)을 Fact로 만들어 내는지 — 프롬프트 5번 규칙이 듣는지
- PoC2에서 사고 pass가 통지문 Fact를, 통지 pass가 사고 Fact를 내려 하는지
  (후처리가 버리므로 거부 사유에 남는다)

비용을 줄이려면 `--case base`로 한 케이스만 먼저 돌려 프롬프트를 다듬고,
전체 스윕은 그 다음에 하는 편이 낫습니다.

## Held-out 세트 — 프롬프트를 고칠 때 보지 않습니다

dev 세트(기준 문서 + 변형)는 PoC마다 **시나리오가 하나**이고, 프롬프트를 고칠 때
이미 봤습니다. 그 점수는 "이 문서를 잘 읽는가"까지만 말합니다. 처음 보는 문서에서의
성능은 held-out으로 잽니다.

```powershell
python evals\run_extraction.py --poc poc1 --split heldout --model claude-sonnet-5
python evals\run_extraction.py --poc poc2 --split heldout --model claude-sonnet-5
```

| PoC | 케이스 | 무엇이 다른가 | 기대 판정 |
|---|---|---|---|
| PoC1 | `h1-fitness-app` | 목록형. **숫자 보유기간**(dev에 F1-03 confirmed가 없음), 항목이 겹치는 제3자 제공 2건(TST-002 함정) | R02 YELLOW, 나머지 GREEN |
| PoC1 | `h2-online-academy` | **서술형**(조문 안 문장). 제공 목적 누락, 이름 없는 수탁자("외부 전문업체"), 국외 이전 | R02 YELLOW, R03 RED, R06 YELLOW |
| PoC2 | `h1-shop-hacking` | 날짜 표기 `2026. 8. 14. 오전 3시 20분경`, `2026-08-14 10:05`. 통지문이 배송지 주소 누락 | R02 RED |
| PoC2 | `h2-clinic-misdirected` | `오후 2시 15분` 표기. 통지문에 경위 없음, 대응조치 4역할 중 2개 | R03 RED, R08 YELLOW |
| PoC1 | `h3-no-sharing` | 제3자 제공과 위탁을 **하지 않는다고 명시** | R03 **N/A**, R06 **N/A** |
| PoC1 | `h4-partial-negation` | **함정**: "원칙적으로 제공하지 않습니다. 다만 다음의 경우 제공" + 그 제공에 목적 누락. 위탁은 언급 없음 | R03 **RED** (N/A면 위험 오판), R06 YELLOW |
| PoC2 | `h3-academy-no-notice` | 통지문 없음, `오후 1시` 표기, 대응조치 2역할 | R01 RED, R02·R03 **N/A**, R08 YELLOW |

h4는 잘못된 N/A를 잡기 위해 만들었습니다. 부정문으로 시작하지만 실제 제공이 뒤따르므로
부재가 아닙니다. 그 제공에 결함(목적 누락)을 넣어 둔 이유는, 제공이 완전하면 잘못된 N/A가
단순 불일치로만 잡혀 "결함을 가렸다"는 위험이 드러나지 않기 때문입니다.

규칙:

- **held-out 결과를 보고 프롬프트를 고치지 않습니다.** 고치면 그 순간 held-out도
  오염되고, 새 held-out을 만들어야 합니다
- 기대 판정은 Rule 조건을 읽고 손으로 적었습니다. `tests/test_heldout.py`가 정답지로
  엔진을 돌려 그 판정이 재현되는지 확인합니다
- 모든 문서는 가상이며 문서 끝에 그렇게 적혀 있습니다 (CLAUDE.md §7)
- 기재가 없는(absent) Fact의 근거는 **찾아본 구간**(해당 조 제목이나 문장)입니다.
  검증기가 absent Fact에도 근거를 요구하기 때문입니다
- 정답지는 `evals/<poc>/build_heldout.py`가 만듭니다. offset은 손으로 쓰지 않습니다

### 정정 기록 (결과를 본 뒤의 정정)

`h2-online-academy`의 결제 대행 수탁자 F1-09를 처음에 `absent`(P1-R06 RED)로 붙였다가
`unknown`(YELLOW)으로 고쳤습니다. 첫 held-out 실행에서 Sonnet 5와 Opus 5가 **모두**
unknown으로 읽었고, 다음 두 기준에 비추면 정답지가 틀렸습니다.

- dev v4 "수탁자: 추후 선정 예정"(언급했지만 비어 있음) = unknown, dev v5(언급 자체가
  없음) = absent. "외부 전문업체에 맡기고 있습니다"는 v4 쪽입니다
- PASS2 8번 규칙의 같은 구분

결과를 보고 정답을 고친 것이므로 이 한 건은 held-out의 독립성을 약하게 합니다. 모델
출력은 그대로이고 정답지만 바뀌었습니다. 이런 정정이 반복되면 새 held-out을 만듭니다.

### 현재 결과 — 3회 반복 (claude-sonnet-5, 2026-09-30)

같은 설정을 3번 돌렸습니다. 한 번만 돌린 수치는 실행 간 편차를 가립니다(실제로 PoC2 v1에서
실행마다 결과가 달랐던 적이 있습니다). 괄호는 회차별 값입니다.

| | 케이스 | Rule 일치 | GREEN 오판 | N/A 오판 | Fact F1 | 환각률 |
|---|---|---|---|---|---|---|
| PoC1 dev | 7 | 42/42 ×3 | 0 ×3 | 0 ×3 | 0.989 / 0.993 / 0.993 | 0 ×3 |
| PoC1 held-out | 4 | 18/24, 24/24, 24/24 | 0 ×3 | 0 ×3 | 0.965 / 1.000 / 1.000 | 0.024 / 0.012 / 0 |
| PoC2 dev | 7 | 28/28 ×3 | 0 ×3 | 0 ×3 | 1.000 ×3 | 0 ×3 |
| PoC2 held-out | 3 | 12/12 ×3 | 0 ×3 | 0 ×3 | 1.000 ×3 | 0 ×3 |

**PoC1 held-out 1회차의 18/24는 결함이 원인이었고 고쳤습니다.** 권리 pass에서 모델이
`fact_id`를 `"F1-12-1"`, `"F1-12-2"`처럼 번호를 붙여 냈습니다. F1-12로 인식되지 않아
subject class가 틀렸고, 매퍼가 그 문서의 Fact 전체를 거부해 h1의 Rule 6개 결과가 통째로
사라졌습니다. 이제 `fact_id`는 structured outputs 스키마의 **enum**(동결된 ID만)이라 API가
이런 값을 낼 수 없습니다. 수정 후 held-out을 다시 돌려 PoC1 24/24(F1 1.000), PoC2 12/12를
확인했습니다.

h4 함정(부분 부정)은 4회 모두 부재 선언 없이 제공 처리행위를 유지했고, h3의 부재 선언
2건은 4회 모두 나왔습니다. **N/A 오판은 전체 실행에서 0건**입니다.

남은 차이는 판정에 영향이 없는 Fact 단위뿐입니다.

- **v1·v5 정답지 정정 (2026-09-30)**: 기재를 삭제한 Fact(v1 목적, v5 수탁자명)를 정답지가
  빼 버려서, absent를 정확히 낸 모델이 "없는 것을 만듦"으로 잡혔습니다. v3과 같은 규약
  (빼지 않고 absent)으로 고쳤습니다. 판정은 그대로(RED)이고, 저장된 3회 예측을 다시 채점하면
  PoC1 dev F1이 0.989/0.993/0.993 -> **0.993/0.996/0.996**입니다.
- **국외 이전 F1-03 (해결, 2026-09-30 팀 결정)**: SC-P01 "서비스 이용기간 또는 처리 목적
  달성 시까지"를 모델이 F1-03 `unknown`으로 봤습니다. "기간"이라는 **단어가 아니라 끝이
  어떻게 정해지는지**로 가르기로 했습니다. 시간 길이로 끝나면 F1-03, 사건으로 끝나면 F1-04,
  둘 다 모르면 F1-03 unknown입니다. "서비스 이용기간 동안"은 서비스 이용이 끝나는 사건이므로
  F1-04이고, 정답지(F1-03 absent)가 맞았습니다. PASS2 7번 규칙에 반영한 뒤 PoC1 dev
  **F1 1.000, Rule 42/42**, held-out **F1 1.000, 24/24**를 확인했습니다.
- 서술형 문서에서 권리 이름을 원문과 조금 다르게 적는 것 (held-out에서 나온 것이라
  프롬프트에 반영하지 않음).

비용(usage 기준 추정): 3회 반복 전체 약 $5. 1회당 PoC1 dev 약 $1.06, PoC1 held-out
약 $0.36, PoC2 dev 약 $0.17, PoC2 held-out 약 $0.08.

### 서버 경로 확인 (`PIPA_EXTRACTOR=llm`, FastAPI)

평가 러너가 아니라 실제 API로 요청을 보내 봤습니다.

| 요청 | 결과 | 응답 시간 |
|---|---|---|
| PoC1 v6 (제공 안 함 명시) | 정답과 일치, P1-R03 N/A | **88초** |
| PoC2 기준 | 정답과 일치, 날짜 `2026-09-05T14:30:00+09:00` | 12초 |
| PoC2 v6 (통지문 없음) | 정답과 일치, P2-R02·R03 N/A | 7초 |

§9.1 봉투, `source_document_id`, §8 필수 필드가 모두 있었고 서버 로그에 키나 원문이
남지 않았습니다. 화면은 브라우저로 확인하지 않았습니다 (날짜 표시는 `EvidenceList.tsx`의
형식 변환에 의존).

**PoC1이 88초 걸렸습니다.** 호출 약 14회를 순서대로 했기 때문입니다. 이제 처리행위별
Pass 2와 권리 pass를 **동시에** 보냅니다 (`from_environment` 기본 6개). 첫 Pass 2만 혼자
먼저 보내 원문 캐시를 만든 뒤 나머지를 보내므로 캐시 적중률은 그대로입니다. 결과는
응답 도착 순서가 아니라 처리행위 순서로 모으므로 순차 실행과 똑같습니다 (테스트로 고정).

| PoC1 base | 소요 시간 | 캐시 적중률 |
|---|---|---|
| 순차 (서버 경로) | 88초 | 80% |
| 동시 6개 (러너, 시작·채점 포함) | **41초** | **80%** |

직접 `PoC1Extractor(messages)`로 만들면 기본값은 순차(1)입니다. 호출 순서대로 응답을
돌려주는 테스트 스텁이 그대로 동작하게 하기 위해서입니다.

### 모델

A~C 이전의 첫 전체 스윕은 PoC1 dev 위험 오판이 Sonnet 5 3건, Opus 5 1건이었습니다
(원인과 수정은 커밋 `41da388`). 수정 후 Sonnet 5가 위 표처럼 위험 오판 0이므로 Sonnet 5를
기본 모델로 둡니다(`.env.example`). **수정 후 Opus 5는 다시 돌리지 않았으므로 두 모델의
공정한 비교는 아닙니다.**

## N/A 경로 — 명시적 부재는 Fact가 아니라 presence metadata입니다

COM-006은 "처리행위가 없다고 확인됨"을 N/A로 봅니다. Fact Dictionary 35개에는 그것을
담을 Fact가 없으므로 activity presence metadata(`confirmed_false`)로 싣습니다.

| PoC | 무엇이 부재를 말하는가 | metadata |
|---|---|---|
| PoC1 | Pass 1이 "제3자에게 제공하지 않습니다" 같은 **원문 문장**을 `declared_absent`로 보고 | `ThirdPartyProvision` / `EntrustedProcessing` = confirmed_false, 근거는 그 문장 |
| PoC2 | 요청에 **통지문이 없음** (`with_notice_presence`, 서비스와 러너가 같은 함수) | `NotificationNotice` = confirmed_false, 근거는 `field_path: notification` |

잘못된 `confirmed_false`는 Rule을 판정 대상에서 빼서 결함을 가립니다. 그래서 확신이
없으면 내지 않습니다.

- 부재 선언의 인용이 원문에 없으면 버립니다 (NFR-07)
- 같은 유형의 처리행위를 Pass 1이 함께 식별했으면 모순이므로 버립니다. 그 처리행위는
  평소대로 평가됩니다
- "기재가 없음"은 부재 선언이 아닙니다. 원문이 "하지 않는다"고 말할 때만입니다

채점기는 이 위험을 **위험 오판(N/A)**으로 따로 셉니다. gold가 RED/YELLOW인데 N/A로
예측하면 위험 오판이고, 러너는 GREEN 오판과 마찬가지로 종료 코드 1을 냅니다.

실측은 위 "현재 결과 — 3회 반복"에 있습니다. 부재 선언은 dev에서는 v6에서만, held-out에서는
h3에서만 나왔고 h4 함정에서는 한 번도 나오지 않았습니다. 처음 N/A 경로를 붙였을 때 PoC2 v1에서
보인 불일치(F2-01 인용 거부)는 N/A와 무관한 실행 간 편차였고, 근거 인용의 줄바꿈 허용으로
해결했습니다 (위 "근거 인용").

## PoC1 Controlled Variants (TST-003)

SC-P01 하나로는 GREEN과 YELLOW만 나옵니다. `evals/poc1/variants/`의 6개 변형이 나머지를 채웁니다.

```powershell
python evals\poc1\build_variants.py
python -m pytest -q tests\test_variants_poc1.py
```

| 변형 | 조작 | 결과 |
|---|---|---|
| v1-missing-purpose | 처리 목적 문장 삭제 | P1-R01 **RED** |
| v2-vague-destruction | "적절한 방법으로 파기" | P1-R04 **YELLOW** |
| v3-missing-destruction | 파기 방법 기재 삭제 (F1-08 `absent`) | P1-R04 **RED** |
| v4-unknown-processor | "수탁자: 추후 선정 예정" | P1-R06 **YELLOW** |
| v5-missing-processor | 수탁자명 기재 삭제 | P1-R06 **RED** |
| v6-no-third-party-provision | "제3자에게 제공하지 않습니다" 명시 | P1-R03 **N/A** |

문서를 편집하면 글자 위치가 전부 밀리므로, 빌더가 **변형 문서에서 근거를 다시 찾아** offset을
새로 계산합니다. 근거를 찾지 못했는데 변형 정의가 처리하지 않았다면 빌더가 실패합니다.

각 변형은 겨냥한 Rule **하나만** 움직여야 하며, 이것도 테스트로 강제합니다.

### v6는 N/A입니다

v6의 정답지는 제공 Fact를 빼고 `ThirdPartyProvision=confirmed_false` presence
metadata를 싣습니다. 예전 기대값 YELLOW는 N/A를 낼 경로가 없던 때의 값입니다.
PoC2에는 통지문이 없는 `v6-no-notice`가 같은 역할을 합니다 (P2-R02/R03 N/A).

**absent와 unknown의 구분**은 v2와 v3이 보여줍니다. 같은 P1-R04를 v2(파기방법
`unknown`)는 YELLOW로, v3(파기방법 `absent`)는 RED로 움직입니다. Fact를 아예 빼면
"입력 계약 불완전"으로 YELLOW가 되므로, 기재가 없을 때는 Fact를 빼지 말고
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
| `legal_basis: null` | P3-R01 YELLOW |
| `design_rationale: null` (필수항목) | P3-R05 YELLOW |
| `denies_service_on_optional_refusal: true` | P3-R06 **RED** |
| `denies_service_on_optional_refusal: null` | P3-R06 YELLOW |
| `destruction_method: null` | P3-R08 YELLOW |
| `entrustments: []` | P3-R11 YELLOW |

`false`와 `null`이 다른 결과를 낸다는 점이 핵심입니다. Form Builder가 `if not value`로
판정하면 둘이 같아져 Fact Dictionary 1장을 위반합니다.

## A에게

`sc_p01_gold_facts.json`의 `facts`를 `facts_to_graph()`에 넣어 `/console`에서 보면
`expected_rule_status`가 재현됩니다. 이 세트는 매핑 테이블의 정답지입니다.

매퍼가 만든 그래프는 evidence 128건 중 74건이 원문 근거를 싣습니다. SC-P01 TTL은 0건이었으므로,
**PoC1의 근거 경로(COM-008)가 이제 처음으로 실제로 동작합니다.** 다만 offset은 여전히
유실됩니다 — `pipa:hasSourceEvidence`가 문자열 annotation이라 담을 자리가 없습니다
(위 계약 결손 2번).
