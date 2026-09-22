"""PoC1 처리방침 Fact Extraction 프롬프트.

2-pass 구조다.

    Pass 1  처리방침 전체 -> 처리행위 목록 (activity_id 부여)
    Pass 2  처리행위 1개 -> 그 처리행위의 Fact만 추출

1-pass로 문서 전체에서 Fact를 한 번에 뽑으면 제3자 제공이 여러 건일 때 A의 수령자와
B의 목적이 섞인다 (TST-002 / 개발완료 체크리스트 7번). Pass 2를 처리행위 단위로 쪼개면
프롬프트 경계가 곧 activity 경계가 되어 혼합이 구조적으로 불가능해진다.

offset은 LLM에게 시키지 않는다. 근거 문장을 원문 그대로 인용하게 하고 offset은 코드가
찾는다. 찾지 못한 인용은 환각으로 보고 버린다 (NFR-07).
"""

from __future__ import annotations

from app.mapping.mapping_registry import FACT_SPECS

# Fact Dictionary 3장 PoC1. (Fact ID, 설명, 값 타입)
#
# ontology_property는 여기에 적지 않고 정본 레지스트리(app.mapping.mapping_registry)에서
# 끌어온다. 이름을 다시 적어두면 레지스트리가 바뀔 때 프롬프트만 조용히 낡고, 증상은
# "추출은 됐는데 검증에서 전부 reject"라는 형태로 실제 API 실행 때 처음 드러난다.
_POC1_FACT_NOTES: list[tuple[str, str, str]] = [
    ("F1-01", "수집·이용 처리행위의 존재", "없음 (Class assertion)"),
    ("F1-02", "처리 목적", "문자열"),
    ("F1-03", "보유 기간 (숫자 기간)", "문자열"),
    ("F1-04", "보유 종료조건", "문자열"),
    ("F1-05", "제3자 제공 받는 자", "문자열"),
    ("F1-06", "제3자 제공 항목", "문자열 배열"),
    ("F1-07", "제3자 제공 목적", "문자열"),
    ("F1-08", "파기 방법", "문자열"),
    ("F1-09", "위탁 수탁자명", "문자열"),
    ("F1-10", "위탁업무 내용", "문자열 (시스템 필드)"),
    ("F1-11", "정보주체 권리", "문자열 배열"),
    ("F1-12", "권리 행사절차", '객체 {"right": 권리명, "procedure": 절차}'),
]

POC1_FACT_CATALOG: list[tuple[str, str, str | None, str]] = [
    (fact_id, description, FACT_SPECS[fact_id].ontology_property, value_type)
    for fact_id, description, value_type in _POC1_FACT_NOTES
]

# 명시적 부재를 단언할 수 있는 처리행위 유형.
# "제3자에게 제공하지 않습니다"처럼 원문이 없다고 못박은 경우에만 쓴다.
# 단순 미기재는 해당하지 않는다 (미기재는 AMBER, 명시적 부재만 N/A).
ABSENCE_ELIGIBLE_CLASSES: list[str] = [
    "ThirdPartyProvision",
    "EntrustedProcessing",
    "CrossBorderTransfer",
]

# Pass 1이 식별해야 하는 처리행위 유형과 activity_id 접두사
ACTIVITY_KINDS: list[tuple[str, str, str]] = [
    ("CollectionAndUse", "act-collection", "개인정보를 수집하여 이용하는 처리행위"),
    ("ThirdPartyProvision", "act-provision", "개인정보를 제3자에게 제공하는 처리행위"),
    ("EntrustedProcessing", "act-entrust", "개인정보 처리업무를 외부에 위탁하는 처리행위"),
    ("Destruction", "act-destruction", "개인정보를 파기하는 처리행위"),
    ("CrossBorderTransfer", "act-crossborder", "개인정보를 국외로 이전하는 처리행위"),
]


def _activity_kind_table() -> str:
    return "\n".join(
        f"  - {name}: {description} (activity_id 접두사 {prefix}-)"
        for name, prefix, description in ACTIVITY_KINDS
    )


def _absence_class_table() -> str:
    return "\n".join(f"  - {name}" for name in ABSENCE_ELIGIBLE_CLASSES)


def _fact_catalog_table() -> str:
    lines = []
    for fact_id, description, prop, value_type in POC1_FACT_CATALOG:
        prop_text = prop if prop else "null"
        lines.append(
            f"  - {fact_id} | {description} | ontology_property={prop_text} | 값 타입={value_type}"
        )
    return "\n".join(lines)


PASS1_SYSTEM = f"""당신은 한국 개인정보 보호법 준수점검 시스템의 처리행위 식별기입니다.

개인정보 처리방침 원문을 읽고, 문서에 기재된 **처리행위(processing activity)**를 빠짐없이
식별하는 것이 당신의 유일한 임무입니다. 이 단계에서는 Fact를 추출하지 않습니다.

## 식별 대상 처리행위 유형

{_activity_kind_table()}

## 규칙

1. 원문에 실제로 기재된 처리행위만 식별합니다. 일반적인 처리방침에 흔히 있다는 이유로
   원문에 없는 처리행위를 만들어 내지 마십시오.

2. 같은 유형이 여러 건이면 각각을 별도 처리행위로 분리합니다. 예를 들어 수탁자가 4곳이면
   EntrustedProcessing 처리행위는 4개입니다. 수집·이용 목적이 5개 항목으로 나뉘어 있으면
   CollectionAndUse는 5개입니다.

3. activity_id는 유형별 접두사에 001부터 일련번호를 붙입니다.
   예: act-collection-001, act-collection-002, act-entrust-001

4. heading에는 그 처리행위를 원문에서 특정할 수 있는 **짧은 문구를 원문 그대로** 적습니다.
   요약하거나 바꿔 쓰지 마십시오. 원문에 없는 문자열을 적으면 그 처리행위는 버려집니다.

5. 하나의 처리행위가 여러 조에 걸쳐 기재되어 있어도 처리행위는 하나입니다.
   (예: 제1조에 목적, 제2조에 보유기간이 나뉘어 있는 경우)

## 명시적으로 "하지 않는다"고 적힌 처리행위 유형

처리방침이 특정 처리행위를 **하지 않는다고 명시**한 경우, 그 유형을
absent_activity_classes에 담으십시오. 대상은 다음 셋뿐입니다.

{_absence_class_table()}

예: "회사는 이용자의 개인정보를 제3자에게 제공하지 않습니다."
    -> ThirdPartyProvision

**미기재와 명시적 부재는 다릅니다.** 이 구분이 이 작업에서 가장 중요합니다.

  - 원문이 "제공하지 않습니다"라고 **적은** 경우 -> 명시적 부재. 여기에 담습니다.
  - 원문에 제3자 제공 이야기가 **아예 없는** 경우 -> 미기재. 담지 마십시오.

일반적인 처리방침에 그 조항이 보통 있다는 이유로, 또는 문서에서 못 찾았다는 이유로
부재를 단언하면 안 됩니다. 부재를 선언하는 문장을 원문에서 직접 찾은 경우에만 담고,
그 문장을 evidence_text에 **글자 그대로** 인용하십시오.

같은 유형을 activities와 absent_activity_classes에 동시에 담지 마십시오.
"""


PASS2_SYSTEM = f"""당신은 한국 개인정보 보호법 준수점검 시스템의 Fact 추출기입니다.

개인정보 처리방침 원문 전체와, 이번에 처리할 **하나의 처리행위**가 주어집니다.
그 처리행위에 해당하는 Fact만 추출하십시오.

## 추출 대상 Fact

{_fact_catalog_table()}

## 절대 규칙

1. **원문에 없는 값을 추정하지 마십시오.** 처리방침에 적히지 않은 내용을 일반적인 관행이나
   법령 내용으로 채워 넣으면 안 됩니다. 확인되지 않으면 value_state로 표현합니다.

2. **value_state를 정확히 구분하십시오.**
   - confirmed: 원문에 값이 명시되어 있다. value에 그 값을 넣는다.
   - unknown: 관련 서술은 있으나 이 처리행위의 값으로 특정할 수 없다. value는 null.
   - absent: 원문 전체를 확인한 결과 해당 항목 기재가 없다. value는 null.
   `unknown`과 `absent`는 다릅니다. 관련 문장이 존재하지만 어느 처리행위에 걸리는지
   불분명하면 unknown이고, 문서에 아예 없으면 absent입니다.

3. **이번 처리행위의 Fact만 추출하십시오.** 다른 처리행위의 목적·항목·수령자를 가져오면 안 됩니다.
   제3자 제공이 여러 건일 때 A의 수령자와 B의 목적을 한 처리행위에 섞는 것이 가장 흔한 오류입니다.

4. **evidence_text에는 원문 문장을 글자 그대로 인용하십시오.** 한 글자라도 다르면 그 Fact는
   버려집니다. 요약·의역·띄어쓰기 수정·말줄임표 추가를 하지 마십시오.
   배열 값(F1-06, F1-11)은 원소 개수와 같은 개수의 인용을 순서대로 제공하십시오.

5. **수집·이용의 수집 항목은 추출하지 마십시오.** 위 목록에 없습니다. PoC1 Rule이 소비하는
   개인정보 항목 Fact는 제3자 제공 항목(F1-06)뿐입니다. 원문 제1조에 수집 항목이 또렷하게
   적혀 있더라도 Fact로 만들지 마십시오. 목록에 없는 Fact를 만들면 검증 단계에서 전부
   거부됩니다.

6. 해당 처리행위에 해당하지 않는 Fact ID는 아예 출력하지 마십시오.
   예를 들어 EntrustedProcessing 처리행위에서는 F1-09와 F1-10만 나옵니다.

7. **F1-03과 F1-04는 ontology_property가 같습니다.** 둘을 가르는 것은 값의 성격이지
   property 이름이 아닙니다. "3년", "5년간"처럼 기간 자체가 적혀 있으면 F1-03이고,
   "회원 탈퇴 시", "목적 달성 시"처럼 보유를 끝내는 사건이 적혀 있으면 F1-04입니다.
   한 처리행위에 둘 다 적혀 있으면 둘 다 출력합니다.

## 처리행위 유형별로 기대되는 Fact

  - CollectionAndUse    : F1-01, F1-02, F1-03, F1-04
  - ThirdPartyProvision : F1-03, F1-04, F1-05, F1-06, F1-07
  - EntrustedProcessing : F1-09, F1-10
  - Destruction         : F1-08
  - CrossBorderTransfer : F1-03, F1-04

정보주체 권리(F1-11)와 행사절차(F1-12)는 처리행위에 속하지 않으므로 별도로 요청됩니다.
"""


def _rights_fact_table() -> str:
    wanted = {"F1-11", "F1-12"}
    return "\n".join(
        line for line in _fact_catalog_table().splitlines()
        if line.strip().split(" ", 2)[1] in wanted
    )


RIGHTS_SYSTEM = f"""당신은 한국 개인정보 보호법 준수점검 시스템의 Fact 추출기입니다.

개인정보 처리방침 원문에서 **정보주체의 권리와 행사절차**만 추출하십시오.

{_rights_fact_table()}

## 절대 규칙

1. 원문에 열거된 권리만 추출합니다. 개인정보 보호법이 정한 권리라는 이유로 원문에 없는
   권리를 추가하지 마십시오.

2. F1-11의 value는 권리 문구의 배열이고, evidence_text는 권리 개수와 같은 개수를
   순서대로 제공합니다.

3. **F1-12는 권리 하나당 하나씩 출력하십시오.** 원문이 모든 권리에 공통 절차 한 문장만
   기재하더라도, F1-11에 담은 권리 수만큼 F1-12를 냅니다. 각각의 value는
   `{{"right": 그 권리 문구, "procedure": 절차 서술}}` 형태로, 어느 권리에 대한
   절차인지 스스로 밝혀야 합니다.

   판정 엔진이 **모든 권리에** 행사절차가 붙어 있어야 준수로 보기 때문입니다. 절차를
   하나만 내면 나머지 권리는 절차가 없는 것으로 취급되어 판정이 뒤집힙니다.
   권리가 4개면 F1-12도 4개이고, 넷의 evidence_text는 같은 문장이어도 됩니다.

4. evidence_text는 원문 그대로 인용합니다. 한 글자라도 다르면 버려집니다.
"""


def pass1_user_message(document: str) -> str:
    return (
        "다음은 분석 대상 개인정보 처리방침 원문입니다.\n\n"
        "<처리방침>\n"
        f"{document}\n"
        "</처리방침>\n\n"
        "이 문서에 기재된 처리행위를 모두 식별하십시오."
    )


def pass2_user_message(activity_id: str, ontology_class: str, heading: str) -> str:
    return (
        "이번에 처리할 처리행위는 다음과 같습니다.\n\n"
        f"  activity_id    : {activity_id}\n"
        f"  ontology_class : {ontology_class}\n"
        f"  원문 위치 단서 : {heading}\n\n"
        "이 처리행위에 해당하는 Fact만 추출하십시오. "
        "모든 Fact의 activity_id는 위 값과 정확히 같아야 합니다."
    )
