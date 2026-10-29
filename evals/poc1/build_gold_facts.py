"""SC-P01 처리방침 원문에서 PoC1 gold Fact set을 생성한다.

evidence의 offset을 손으로 적지 않는다. 근거 문자열을 원문에서 찾아 offset을 계산하고,
기대한 출현 횟수와 다르면 즉시 실패한다. 따라서 생성된 gold set의 offset은 항상 원문과 일치한다.

실행:
    python evals/poc1/build_gold_facts.py

Fact ID / 필드 정의는 PIPA Fact Dictionary v1.0 3장(PoC1)과 2장(공통 Envelope)을 따른다.
여기서 새로 정한 규약은 evals/README.md의 "Day 0 결정 필요" 절에 정리되어 있다.
"""

from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
POLICY_PATH = HERE / "sc_p01_policy.txt"
OUTPUT_PATH = HERE / "sc_p01_gold_facts.json"

SCHEMA_VERSION = "fact-1.0"
SOURCE_TYPE = "policy_text"
SOURCE_DOCUMENT_ID = "SC-P01"

POLICY = POLICY_PATH.read_text(encoding="utf-8")


def ev(text: str, nth: int = 1, *, expect: int = 1) -> dict:
    """근거 문자열의 원문 offset을 계산한다.

    expect와 실제 출현 횟수가 다르면 예외를 던진다. 원문을 수정했을 때
    근거가 조용히 엉뚱한 위치를 가리키는 일을 막는다.
    """
    count = POLICY.count(text)
    if count != expect:
        raise ValueError(f"근거 문자열 {text!r} 출현 {count}회, 기대 {expect}회")
    start = -1
    for _ in range(nth):
        start = POLICY.index(text, start + 1)
    return {"text": text, "start_offset": start, "end_offset": start + len(text)}


def fact(
    fact_id: str,
    subject_id: str,
    ontology_class: str,
    evidence: list[dict],
    *,
    activity_id: str | None = None,
    ontology_property: str | None = None,
    value=None,
    value_state: str = "confirmed",
    note: str | None = None,
) -> dict:
    item = {
        "fact_id": fact_id,
        "subject_id": subject_id,
        "activity_id": activity_id,
        "ontology_class": ontology_class,
        "ontology_property": ontology_property,
        "value": value,
        "value_state": value_state,
        "source_type": SOURCE_TYPE,
        "evidence": evidence,
        "schema_version": SCHEMA_VERSION,
    }
    if note:
        item["_note"] = note
    return item


# ---------------------------------------------------------------------------
# 처리행위 정의: (activity_id, 문단 제목, 처리 목적)
# ---------------------------------------------------------------------------

COLLECTION_ACTIVITIES = [
    ("act-collection-001", "회원 가입 및 관리", "회원 식별·가입 의사 확인·회원 관리·부정이용 방지·고객 문의 처리"),
    ("act-collection-002", "주문 및 배송", "주문 확인·계약 이행·배송·교환·반품"),
    ("act-collection-003", "결제 및 환불", "결제·결제내역 확인·환불"),
    ("act-collection-004", "서비스 개선", "서비스 개선 및 이용 통계 분석"),
    ("act-collection-005", "고객 상담", "문의·민원·분쟁 처리 및 결과 안내"),
]

# 제목 문자열이 원문에 몇 번 나오는지 (제2조나 제4조에서 재등장하는 경우가 있다)
HEADING_OCCURRENCES = {
    "회원 가입 및 관리": 2,   # 제1조 1항, 제2조 1항
    "주문 및 배송": 1,
    "결제 및 환불": 2,        # 제1조 3항, 제4조 "상품대금 결제 및 환불 처리"
    "서비스 개선": 2,         # 제1조 4항 제목, 같은 항 처리 목적 문장
    "고객 상담": 3,           # 제1조 5항, 제1조 5항 수집 항목, 제2조 2항
}

# 보유 종료조건이 처리행위에 연결된 경우만 기재한다.
# 제2조에 명시되지 않은 처리행위는 "관계 법령에서 정한 기간"에만 걸린다.
# 기간 unknown / 종료조건 absent -> P1-R02 YELLOW (Issue 4 팀 결정)
RETENTION_END_CONDITIONS = {
    "act-collection-001": "회원 탈퇴 시",
    "act-collection-005": "상담 및 분쟁 처리 종료 시",
    "act-provision-001": "배송 및 거래 관련 업무 종료 시",
    "act-crossborder-001": "서비스 이용기간 또는 처리 목적 달성 시",
}

RETENTION_UNKNOWN = ["act-collection-002", "act-collection-003", "act-collection-004"]

ENTRUSTMENTS = [
    ("act-entrust-001", "proc-001", "빠른택배 주식회사", "상품 배송"),
    ("act-entrust-002", "proc-002", "모아페이먼츠 주식회사", "상품대금 결제 및 환불 처리"),
    ("act-entrust-003", "proc-003", "메시지온 주식회사", "주문·배송 관련 문자메시지 및 알림 발송"),
    ("act-entrust-004", "proc-004", "클라우드원 주식회사", "서비스 인프라 운영 및 데이터 보관"),
]

PROVISION_ITEMS = [
    ("주문자·수령인 이름", 2, 2),
    ("휴대전화번호", 3, 3),
    ("배송지 주소", 2, 2),
    ("주문상품 정보", 1, 1),
]

RIGHTS = [
    "개인정보 열람 요구",
    "오류 등이 있을 경우 정정·삭제 요구",
    "처리정지 요구",
    "개인정보 처리에 대한 동의 철회",
]

RIGHTS_PROCEDURE = "마이페이지 > 개인정보 관리 또는 개인정보보호 담당부서 이메일"

# 제2조 마지막 문장. 보유 정보가 존재하지만 특정 처리행위와 연결되지 않는 근거다.
GENERAL_RETENTION_SENTENCE = "그 밖의 처리 목적에 대해서는 관계 법령에서 정한 기간 동안 보관합니다."


def build() -> list[dict]:
    facts: list[dict] = []

    # --- F1-01 수집·이용 activity 존재 / F1-02 처리목적 -------------------
    for activity_id, heading, purpose in COLLECTION_ACTIVITIES:
        occurrences = HEADING_OCCURRENCES[heading]
        facts.append(fact(
            f"F1-01:{activity_id}",
            subject_id=activity_id,
            activity_id=activity_id,
            ontology_class="CollectionAndUse",
            ontology_property=None,  # Class assertion이므로 null (Fact Dictionary 2장)
            value=None,
            evidence=[ev(heading, nth=1, expect=occurrences)],
        ))
        facts.append(fact(
            f"F1-02:{activity_id}",
            subject_id=activity_id,
            activity_id=activity_id,
            ontology_class="CollectionAndUse",
            ontology_property="hasPurpose",
            value=purpose,
            evidence=[ev(purpose)],
        ))

    # --- F1-03 보유기간 ---------------------------------------------------
    # 팀 결정 (2026-09-30, Issue 4): "관계 법령에서 정한 기간"처럼 법령도 숫자도
    # 특정하지 않은 기간은 법령을 연동해 채우지 않고 unknown(알 수 없음)으로 둔다.
    # 기간을 말했지만 값이 비어 있기 때문이다 (PASS2 8번 규칙의 "언급했지만 비어 있음").
    # 제2조가 종료조건을 명시한 처리행위는 기간을 말하지 않았으므로 absent다.
    for activity_id in [a for a, _, _ in COLLECTION_ACTIVITIES] + ["act-provision-001", "act-crossborder-001"]:
        unspecified = activity_id in RETENTION_UNKNOWN
        facts.append(fact(
            f"F1-03:{activity_id}",
            subject_id=activity_id,
            activity_id=activity_id,
            ontology_class="PersonalInformationProcessing",
            ontology_property="hasRetention",
            value=None,
            value_state="unknown" if unspecified else "absent",
            evidence=[ev(GENERAL_RETENTION_SENTENCE)],
            note=(
                "'관계 법령에서 정한 기간' — 기간을 말하지만 근거 법령과 값을 특정하지 않음"
                if unspecified
                else "이 처리행위는 종료조건으로만 기재되고 숫자 기간이 없음"
            ),
        ))

    # --- F1-04 보유 종료조건 ---------------------------------------------
    for activity_id, condition in RETENTION_END_CONDITIONS.items():
        ontology_class = {
            "act-provision-001": "ThirdPartyProvision",
            "act-crossborder-001": "CrossBorderTransfer",
        }.get(activity_id, "CollectionAndUse")
        facts.append(fact(
            f"F1-04:{activity_id}",
            subject_id=activity_id,
            activity_id=activity_id,
            ontology_class=ontology_class,
            ontology_property="hasRetention",
            value=condition,
            evidence=[ev(condition)],
        ))

    # 제2조에 열거되지 않은 처리행위. "그 밖의 처리 목적" 문장은 기간을 말할 뿐 끝나는
    # 사건을 말하지 않으므로 종료조건은 absent다 (Issue 4 팀 결정). 보유 정보는 있으나
    # 값을 알 수 없으므로 P1-R02는 여전히 YELLOW다.
    for activity_id in RETENTION_UNKNOWN:
        facts.append(fact(
            f"F1-04:{activity_id}",
            subject_id=activity_id,
            activity_id=activity_id,
            ontology_class="CollectionAndUse",
            ontology_property="hasRetention",
            value=None,
            value_state="absent",
            evidence=[ev(GENERAL_RETENTION_SENTENCE)],
            note="'그 밖의 처리 목적' 문장에 종료 사건이 없음. 기간은 F1-03 unknown",
        ))

    # --- F1-05 / F1-06 / F1-07 제3자 제공 ---------------------------------
    facts.append(fact(
        "F1-05:act-provision-001",
        subject_id="act-provision-001",
        activity_id="act-provision-001",
        ontology_class="ThirdPartyProvision",
        ontology_property="hasRecipient",
        value="이용자가 상품을 구매한 모아마켓 입점 판매자",
        evidence=[ev("이용자가 상품을 구매한 모아마켓 입점 판매자")],
    ))
    facts.append(fact(
        "F1-06:act-provision-001",
        subject_id="act-provision-001",
        activity_id="act-provision-001",
        ontology_class="ThirdPartyProvision",
        ontology_property="hasPersonalInformation",
        value=[item for item, _, _ in PROVISION_ITEMS],
        # Fact Dictionary 8장: 배열 값은 원소 단위 Evidence 연결을 권장한다
        evidence=[ev(item, nth=nth, expect=expect) for item, nth, expect in PROVISION_ITEMS],
    ))
    facts.append(fact(
        "F1-07:act-provision-001",
        subject_id="act-provision-001",
        activity_id="act-provision-001",
        ontology_class="ThirdPartyProvision",
        ontology_property="hasPurpose",
        value="주문상품 확인·배송·교환·반품",
        evidence=[ev("주문상품 확인·배송·교환·반품")],
    ))

    # --- F1-08 파기 방법 --------------------------------------------------
    destruction_method = (
        "전자파일은 복구·재생이 어렵도록 삭제하고 종이문서는 분쇄 또는 안전한 방법으로 폐기합니다."
    )
    facts.append(fact(
        "F1-08:act-destruction-001",
        subject_id="act-destruction-001",
        activity_id="act-destruction-001",
        ontology_class="Destruction",
        ontology_property="hasDestructionMethod",
        value=destruction_method,
        evidence=[ev(destruction_method)],
    ))

    # --- F1-09 위탁 수탁자 / F1-10 위탁업무 내용 --------------------------
    for activity_id, processor_id, processor_name, task in ENTRUSTMENTS:
        facts.append(fact(
            f"F1-09:{activity_id}",
            subject_id=activity_id,
            activity_id=activity_id,
            ontology_class="EntrustedProcessing",
            ontology_property="hasProcessor",
            value=processor_name,
            evidence=[ev(processor_name)],
        ))
        facts.append(fact(
            f"F1-10:{activity_id}",
            subject_id=activity_id,
            activity_id=activity_id,
            ontology_class="EntrustedProcessing",
            # entrusted_task_text는 Ontology Property가 아니라 Rule 입력 보조 필드다
            # (Fact Dictionary 8장). 따라서 ontology_property는 null로 둔다.
            ontology_property=None,
            value=task,
            evidence=[ev(task)],
            note="system field entrusted_task_text. ontology_property로 승격하지 않는다",
        ))

    # --- F1-11 정보주체 권리 / F1-12 권리 행사절차 ------------------------
    facts.append(fact(
        "F1-11:subj-001",
        subject_id="subj-001",
        activity_id=None,  # 처리행위에 귀속되지 않는다
        ontology_class="DataSubject",
        ontology_property="hasRight",
        value=RIGHTS,
        evidence=[ev(right) for right in RIGHTS],
    ))
    # 처리방침은 4개 권리에 공통 절차 1문장을 기재하지만, Rule Engine은 모든
    # DataSubjectRight에 절차가 연결되어야 P1-R07을 GREEN으로 준다. 그래서 권리별로
    # Fact를 하나씩 낸다. 값이 어느 권리에 대한 절차인지 스스로 밝히므로 매퍼가
    # F1-11이 만든 권리 개체와 같은 노드에 연결한다. 근거는 같은 문장이다.
    for right_name in RIGHTS:
        facts.append(fact(
            f"F1-12:{right_name}",
            subject_id="subj-001",
            activity_id=None,
            ontology_class="DataSubjectRight",
            ontology_property="hasExerciseProcedure",
            value={"right": right_name, "procedure": RIGHTS_PROCEDURE},
            evidence=[ev(RIGHTS_PROCEDURE)],
        ))

    facts += cross_border_facts() + privacy_officer_facts() + collection_item_facts()
    return facts


# --- v1.1 F1-22 처리하는 개인정보 항목 (시행령 제31조 제1항 제1호) -----------
# 제1조는 목적마다 "수집 항목:" 줄을 둔다 -> 다섯 처리행위 모두 confirmed -> P1-R11 GREEN.
# 쉼표로 나열한 줄은 쉼표로만 나눈다("주문자·수령인 이름"은 한 항목, F1-06과 같은 규칙).
# 가운뎃점으로만 나열한 줄은 가운뎃점으로 나눈다(F1-14와 같은 규칙). "(선택)" 표시는 값에서 뺀다.


def split_items(line: str) -> list[str]:
    parts = line.split(", ") if ", " in line else line.split("·")
    return [part.replace("(선택)", "").strip() for part in parts]


def collection_item_facts() -> list[dict]:
    facts = []
    for activity_id, _, _ in COLLECTION_ACTIVITIES:
        heading = "수집 항목: "
        # 처리행위 순서대로 n번째 "수집 항목:" 줄
        index = [a for a, _, _ in COLLECTION_ACTIVITIES].index(activity_id)
        start = -1
        for _ in range(index + 1):
            start = POLICY.index(heading, start + 1)
        line = POLICY[start:POLICY.index("\n", start)]
        items = split_items(line[len(heading):])
        facts.append(fact(
            f"F1-22:{activity_id}",
            subject_id=activity_id,
            activity_id=activity_id,
            ontology_class="CollectionAndUse",
            ontology_property="hasPersonalInformation",
            value=items,
            evidence=[ev_after(item, line) for item in items],
        ))
    return facts


def ev_after(text: str, anchor: str) -> dict:
    """anchor 뒤에서 처음 나오는 text. 같은 문자열이 앞 조항에도 있을 때 쓴다."""
    base = POLICY.index(anchor)
    start = POLICY.index(text, base)
    return {"text": text, "start_offset": start, "end_offset": start + len(text)}


# --- v1.1 F1-13~F1-19 국외 이전 기재 (제28조의8 제2항) -----------------------
# 제5조는 국가·목적·항목·기간만 적는다. 이전받는 자, 시기·방법, 거부 방법은 문서 어디에도
# 없다 -> absent -> P1-R09 RED. 제4조의 "클라우드원 주식회사"는 수탁자로 적혔을 뿐 국외
# 이전받는 자로 적히지 않았으므로 이전받는 자로 채우지 않는다 (추정 금지).

CROSS_BORDER_SECTION = "제5조 (개인정보의 국외 이전)"
CROSS_BORDER_ITEMS = ["회원 식별정보", "주문정보", "서비스 이용기록"]


def cross_border_facts() -> list[dict]:
    act = "act-crossborder-001"
    common = dict(subject_id=act, activity_id=act)
    absent = dict(value=None, value_state="absent", evidence=[ev(CROSS_BORDER_SECTION)])
    return [
        fact("F1-13:act-crossborder-001", ontology_class="CrossBorderTransfer",
             ontology_property="hasDestinationCountry", value="미국(US)",
             evidence=[ev("미국(US)")], **common),
        fact("F1-14:act-crossborder-001", ontology_class="CrossBorderTransfer",
             ontology_property="hasPersonalInformation", value=CROSS_BORDER_ITEMS,
             evidence=[ev_after(item, CROSS_BORDER_SECTION) for item in CROSS_BORDER_ITEMS], **common),
        fact("F1-15:act-crossborder-001", ontology_class="CrossBorderTransfer",
             ontology_property="hasPurpose", value="인프라 운영·데이터 저장·장애복구",
             evidence=[ev("인프라 운영·데이터 저장·장애복구")], **common),
        fact("F1-16:act-crossborder-001", ontology_class="CrossBorderTransfer",
             ontology_property="hasTransferRecipient", **absent, **common,
             note="이전받는 자 기재 없음. 수탁자(제4조)를 이전받는 자로 추정하지 않는다"),
        fact("F1-17:act-crossborder-001", ontology_class="OverseasRecipient",
             ontology_property="hasContact", **absent, **common),
        fact("F1-18:act-crossborder-001", ontology_class="CrossBorderTransfer",
             ontology_property="hasTransferTimingAndMethod", **absent, **common),
        fact("F1-19:act-crossborder-001", ontology_class="CrossBorderTransfer",
             ontology_property="hasTransferRefusalProcedure", **absent, **common),
    ]


# --- v1.1 F1-20~F1-21 개인정보 보호책임자 기재 (제30조 제1항 제6호) -----------
# 제8조는 "보호책임자를 지정하고 있습니다"까지만 적고 성명·부서·연락처가 없다 -> absent -> RED.
# 자리표시자("추후 지정" 등)가 아니라 기재 자체가 없으므로 unknown이 아니다.

OFFICER_SECTION = "제8조 (개인정보 보호책임자)"


def privacy_officer_facts() -> list[dict]:
    common = dict(subject_id="privacy-officer", activity_id=None, value=None,
                  value_state="absent", evidence=[ev(OFFICER_SECTION)])
    return [
        fact("F1-20:privacy-officer", ontology_class="PersonalInformationController",
             ontology_property="hasPrivacyOfficer", **common),
        fact("F1-21:privacy-officer", ontology_class="PrivacyOfficer",
             ontology_property="hasContact", **common),
    ]


def main() -> int:
    facts = build()
    payload = {
        "source_document_id": SOURCE_DOCUMENT_ID,
        "poc": "poc1",
        "policy_text_file": POLICY_PATH.name,
        "fact_schema_version": SCHEMA_VERSION,
        "expected_rule_status": {
            "P1-R01": "GREEN",
            "P1-R02": "YELLOW",
            "P1-R03": "GREEN",
            "P1-R04": "GREEN",
            "P1-R06": "GREEN",
            "P1-R07": "GREEN",
            "P1-R08": "GREEN",
            "P1-R09": "RED",   # 이전받는 자·시기·방법·거부 방법 기재 없음
            "P1-R10": "RED",   # 보호책임자 성명·부서·연락처 기재 없음
            "P1-R11": "GREEN",  # 다섯 목적 모두 수집 항목 기재
        },
        "facts": facts,
    }
    OUTPUT_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"{OUTPUT_PATH.name}: fact {len(facts)}개")
    for state in ("confirmed", "unknown", "absent"):
        print(f"  {state:9s} {sum(1 for f in facts if f['value_state'] == state)}개")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
