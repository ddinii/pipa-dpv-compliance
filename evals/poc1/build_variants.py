"""SC-P01 controlled variants 생성 (TST-003).

기준 처리방침을 조금씩 망가뜨려 RED / YELLOW / N/A 대표 케이스를 만든다.
SC-P01 하나만으로는 GREEN과 YELLOW밖에 나오지 않아 TST-003을 충족할 수 없다.

각 변형은 (문서 편집, Fact 편집, 기대 status)로 정의된다. 문서를 편집하면 글자 위치가
전부 밀리므로, 기준 gold Fact의 근거를 **변형 문서에서 다시 찾아** offset을 새로 계산한다.
근거를 찾지 못한 Fact는 반드시 변형 정의가 명시적으로 처리해야 하며, 그러지 않으면 실패한다.
그래서 변형 gold set의 offset은 항상 그 변형 문서와 맞는다.

실행:
    python evals/poc1/build_variants.py
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASE_POLICY = HERE / "sc_p01_policy.txt"
BASE_GOLD = HERE / "sc_p01_gold_facts.json"
OUT_DIR = HERE / "variants"

BASE_STATUS = {
    "P1-R01": "GREEN",
    "P1-R02": "YELLOW",
    "P1-R03": "GREEN",
    "P1-R04": "GREEN",
    "P1-R06": "GREEN",
    "P1-R07": "GREEN",
    "P1-R08": "GREEN",
    "P1-R09": "RED",
    "P1-R10": "RED",
    "P1-R11": "GREEN",
    "P1-R12": "RED",
}


@dataclass
class Variant:
    name: str
    description: str
    target_rule: str
    expected_status: str
    # (원문 그대로, 바꿀 내용). 원문에 정확히 1회만 나와야 한다.
    edits: list[tuple[str, str]] = field(default_factory=list)
    # 삭제할 Fact ID
    drop: set[str] = field(default_factory=set)
    # fact_id -> (새 value_state, 새 근거 인용)
    restate: dict[str, tuple[str, str]] = field(default_factory=dict)
    # fact_id -> (새 confirmed value, 근거 인용 목록). 기준에서 absent였던 항목을 채울 때 쓴다.
    confirm: dict[str, tuple[object, list[str]]] = field(default_factory=dict)
    # 추가할 Fact (envelope 전체). 근거 인용은 변형 문서 기준으로 해석된다.
    add: list[dict] = field(default_factory=list)
    # 정답 activity presence metadata: (activity_type, 부재를 명시한 원문 인용).
    # Fact가 아니다. 처리행위 유형이 "없다고 명시됨"(confirmed_false)을 뜻한다.
    presence: list[tuple[str, str]] = field(default_factory=list)


CONTROLLER_ABSENCE_EVIDENCE = "회사는 이용자의 개인정보를 제3자에게 제공하지 않습니다."
CROSS_BORDER_ABSENCE_EVIDENCE = "회사는 이용자의 개인정보를 국외로 이전하지 않습니다."

# v7·v8에서 채워 넣는 기재 내용. 전부 합성 값이다 (example.com, 0000 번호, 관용 예시 성명).
TRANSFER_RECIPIENT = "Example Cloud Inc."
TRANSFER_RECIPIENT_CONTACT = "privacy@example.com"
TRANSFER_TIMING_METHOD = "서비스 이용 시점에 네트워크를 통해 암호화하여 전송"
TRANSFER_REFUSAL = (
    "개인정보 보호책임자에게 이메일로 국외 이전 거부 의사를 알릴 수 있으며, "
    "거부 시 서비스 이용이 제한될 수 있습니다."
)
OFFICER_NAME = "홍길동"
OFFICER_DEPARTMENT = "개인정보보호팀"
OFFICER_PHONE = "02-0000-0000"
OFFICER_EMAIL = "dpo@example.com"


VARIANTS: list[Variant] = [
    Variant(
        name="v1-missing-purpose",
        description="서비스 개선 처리행위의 처리 목적 문장을 삭제한다.",
        target_rule="P1-R01",
        expected_status="RED",
        edits=[("   처리 목적: 서비스 개선 및 이용 통계 분석\n", "")],
        # Fact Dictionary 8장: 기재가 없으면 Fact를 빼지 않고 absent로 유지한다 (v3와 같은
        # 규약). 근거는 목적이 적혀 있어야 할 항목의 제목이다. 예전에는 Fact를 빼서,
        # absent를 정확히 낸 모델이 채점에서 "없는 것을 만듦"으로 잡혔다.
        restate={"F1-02:act-collection-004": ("absent", "4. 서비스 개선")},
    ),
    Variant(
        name="v2-vague-destruction",
        description="파기 방법을 '적절한 방법으로'라는 모호한 표현으로 바꾼다.",
        target_rule="P1-R04",
        expected_status="YELLOW",
        edits=[(
            "파기 방법: 전자파일은 복구·재생이 어렵도록 삭제하고 종이문서는 분쇄 또는 안전한 방법으로 폐기합니다.",
            "파기 방법: 적절한 방법으로 파기합니다.",
        )],
        restate={
            "F1-08:act-destruction-001": ("unknown", "파기 방법: 적절한 방법으로 파기합니다."),
        },
    ),
    Variant(
        name="v3-missing-destruction",
        description="파기한다는 사실만 남기고 파기 방법 기재를 삭제한다.",
        target_rule="P1-R04",
        expected_status="RED",
        edits=[(
            "\n파기 방법: 전자파일은 복구·재생이 어렵도록 삭제하고 종이문서는 분쇄 또는 안전한 방법으로 폐기합니다.\n",
            "",
        )],
        # Fact Dictionary 8장: 기재가 없으면 Fact를 빼는 것이 아니라 absent로 유지한다.
        # 근거는 그 항목이 있어야 할 조항을 가리킨다.
        restate={
            "F1-08:act-destruction-001": (
                "absent",
                "회사는 개인정보 보유기간이 경과하거나 처리 목적이 달성된 경우에는 지체 없이 해당 개인정보를 파기합니다.",
            ),
        },
    ),
    Variant(
        name="v4-unknown-processor",
        description="수탁자 한 곳을 '추후 선정 예정'으로 바꿔 수탁자명을 특정할 수 없게 만든다.",
        target_rule="P1-R06",
        expected_status="YELLOW",
        edits=[("수탁자: 빠른택배 주식회사", "수탁자: 추후 선정 예정")],
        restate={
            "F1-09:act-entrust-001": ("unknown", "수탁자: 추후 선정 예정"),
        },
    ),
    Variant(
        name="v5-missing-processor",
        description="수탁자 한 곳의 수탁자명 기재를 삭제한다. 위탁업무만 남는다.",
        target_rule="P1-R06",
        expected_status="RED",
        edits=[("수탁자: 빠른택배 주식회사\n위탁업무: 상품 배송", "위탁업무: 상품 배송")],
        # v1과 같은 규약: 빼지 않고 absent. 근거는 수탁자명이 있어야 할 그 위탁 항목이다.
        restate={"F1-09:act-entrust-001": ("absent", "위탁업무: 상품 배송")},
    ),
    Variant(
        name="v6-no-third-party-provision",
        # Fact Dictionary 3장에는 "처리행위 유형이 없다"를 담을 Fact ID가 없다
        # (F1-00 같은 것은 존재하지 않는다). 부재는 Fact가 아니라 activity presence
        # metadata로 싣는다 (app/mapping/presence_metadata.py). 명시적 부재는
        # COM-006에 따라 N/A다. 예전 기대값 YELLOW는 N/A를 낼 경로가 없던 때의 값이다.
        description="제3자 제공을 하지 않는다고 명시한다. 제공 Fact는 사라지고 부재가 명시된다.",
        target_rule="P1-R03",
        expected_status="N/A",
        presence=[("ThirdPartyProvision", CONTROLLER_ABSENCE_EVIDENCE)],
        edits=[(
            "회사는 이용자의 개인정보를 제1조에서 명시한 범위 내에서만 처리하며, 다음의 경우에 한하여 개인정보를 제3자에게 제공합니다.\n"
            "\n"
            "제공받는 자: 이용자가 상품을 구매한 모아마켓 입점 판매자\n"
            "제공 목적: 주문상품 확인·배송·교환·반품\n"
            "제공 항목: 주문자·수령인 이름, 휴대전화번호, 배송지 주소, 주문상품 정보\n"
            "보유 및 이용 기간: 배송 및 거래 관련 업무 종료 시까지\n",
            CONTROLLER_ABSENCE_EVIDENCE + "\n",
        )],
        drop={
            "F1-05:act-provision-001",
            "F1-06:act-provision-001",
            "F1-07:act-provision-001",
            "F1-03:act-provision-001",
            "F1-04:act-provision-001",
        },
    ),
    Variant(
        name="v7-complete-cross-border",
        description="제5조에 이전받는 자·연락처, 이전 시기·방법, 거부 방법·절차·효과를 채운다.",
        target_rule="P1-R09",
        expected_status="GREEN",
        edits=[(
            "이전 항목: 회원 식별정보·주문정보·서비스 이용기록\n",
            "이전 항목: 회원 식별정보·주문정보·서비스 이용기록\n"
            f"이전받는 자: {TRANSFER_RECIPIENT} (연락처: {TRANSFER_RECIPIENT_CONTACT})\n"
            f"이전 시기 및 방법: {TRANSFER_TIMING_METHOD}\n"
            f"거부 방법 및 절차: {TRANSFER_REFUSAL}\n",
        )],
        confirm={
            "F1-16:act-crossborder-001": (TRANSFER_RECIPIENT, [TRANSFER_RECIPIENT]),
            "F1-17:act-crossborder-001": ([TRANSFER_RECIPIENT_CONTACT], [TRANSFER_RECIPIENT_CONTACT]),
            "F1-18:act-crossborder-001": (TRANSFER_TIMING_METHOD, [TRANSFER_TIMING_METHOD]),
            "F1-19:act-crossborder-001": (TRANSFER_REFUSAL, [TRANSFER_REFUSAL]),
        },
    ),
    Variant(
        name="v8-complete-privacy-officer",
        description="제8조에 보호책임자 성명·부서·연락처를 채운다.",
        target_rule="P1-R10",
        expected_status="GREEN",
        edits=[(
            "개인정보 보호책임자를 지정하고 있습니다.\n",
            "개인정보 보호책임자를 지정하고 있습니다.\n"
            "\n"
            f"성명: {OFFICER_NAME}\n"
            f"소속: {OFFICER_DEPARTMENT}\n"
            f"연락처: {OFFICER_PHONE}, {OFFICER_EMAIL}\n",
        )],
        confirm={
            "F1-20:privacy-officer": (
                {"name": OFFICER_NAME, "department": OFFICER_DEPARTMENT},
                [OFFICER_NAME, OFFICER_DEPARTMENT],
            ),
            "F1-21:privacy-officer": (
                [OFFICER_PHONE, OFFICER_EMAIL], [OFFICER_PHONE, OFFICER_EMAIL],
            ),
        },
    ),
    Variant(
        name="v9-no-cross-border-transfer",
        # v6과 같은 규약: 처리행위 유형의 명시적 부재는 presence metadata로 싣고 N/A다.
        description="국외로 이전하지 않는다고 명시한다. 국외 이전 Fact는 사라지고 부재가 명시된다.",
        target_rule="P1-R09",
        expected_status="N/A",
        presence=[("CrossBorderTransfer", CROSS_BORDER_ABSENCE_EVIDENCE)],
        edits=[(
            "회사는 서비스 제공을 위하여 다음과 같이 개인정보를 국외로 이전하고 있습니다.\n"
            "\n"
            "이전받는 국가: 미국(US)\n"
            "이전 목적: 인프라 운영·데이터 저장·장애복구\n"
            "이전 항목: 회원 식별정보·주문정보·서비스 이용기록\n"
            "보유 및 이용 기간: 서비스 이용기간 또는 처리 목적 달성 시까지\n",
            CROSS_BORDER_ABSENCE_EVIDENCE + "\n",
        )],
        drop={f"F1-{n:02d}:act-crossborder-001" for n in (3, 4, *range(13, 20))},
    ),
    Variant(
        name="v10-missing-collection-items",
        description="고객 상담 처리행위의 수집 항목 줄을 삭제한다.",
        target_rule="P1-R11",
        expected_status="RED",
        edits=[("   수집 항목: 고객 상담 기록\n", "")],
        # v1과 같은 규약: 빼지 않고 absent. 근거는 항목이 있어야 할 처리행위의 제목이다.
        restate={"F1-22:act-collection-005": ("absent", "5. 고객 상담")},
    ),
    Variant(
        name="v11-vague-collection-items",
        description="고객 상담의 수집 항목을 항목을 특정하지 않는 포괄 표현으로 바꾼다.",
        target_rule="P1-R11",
        expected_status="YELLOW",
        edits=[("수집 항목: 고객 상담 기록", "수집 항목: 상담 처리에 필요한 정보")],
        restate={"F1-22:act-collection-005": ("unknown", "수집 항목: 상담 처리에 필요한 정보")},
    ),
]


def locate(document: str, quote: str, near: int = 0) -> dict:
    """quote의 위치. 여러 번 나오면 near(기준 문서 offset)에 가장 가까운 것을 고른다.

    같은 문구가 여러 조항에 나오면("주문정보" 등) 첫 등장이 아니라 원래 가리키던 자리를 찾아야 한다.
    """
    starts, start = [], document.find(quote)
    while start != -1:
        starts.append(start)
        start = document.find(quote, start + 1)
    if not starts:
        raise ValueError(f"변형 문서에서 근거를 찾지 못했습니다: {quote!r}")
    start = min(starts, key=lambda s: abs(s - near))
    return {"text": quote, "start_offset": start, "end_offset": start + len(quote)}


def apply_edits(document: str, edits: list[tuple[str, str]]) -> str:
    for old, new in edits:
        count = document.count(old)
        if count != 1:
            raise ValueError(f"편집 대상이 {count}회 나타납니다 (1회여야 함): {old[:40]!r}…")
        document = document.replace(old, new, 1)
    return document


def rebuild_facts(base_facts: list[dict], document: str, variant: Variant) -> list[dict]:
    """기준 Fact를 변형 문서에 맞춰 다시 만든다.

    근거를 변형 문서에서 다시 찾아 offset을 새로 계산한다. 찾지 못했는데 변형 정의가
    drop/restate로 처리하지 않았다면 정의가 불완전한 것이므로 실패시킨다.
    """
    facts: list[dict] = []

    for base in base_facts:
        fact_id = base["fact_id"]
        if fact_id in variant.drop:
            continue

        fact = json.loads(json.dumps(base))  # 깊은 복사

        if fact_id in variant.restate:
            state, quote = variant.restate[fact_id]
            fact["value_state"] = state
            fact["value"] = None
            fact["evidence"] = [locate(document, quote)]
            fact["_note"] = f"변형 {variant.name}: {variant.description}"
            facts.append(fact)
            continue

        if fact_id in variant.confirm:
            value, quotes = variant.confirm[fact_id]
            fact["value_state"] = "confirmed"
            fact["value"] = value
            fact["evidence"] = [locate(document, quote) for quote in quotes]
            fact["_note"] = f"변형 {variant.name}: {variant.description}"
            facts.append(fact)
            continue

        try:
            fact["evidence"] = [
                locate(document, piece["text"], piece["start_offset"]) for piece in base["evidence"]
            ]
        except ValueError as exc:
            raise ValueError(
                f"{variant.name}: {fact_id}의 근거가 변형 문서에 없는데 drop/restate에 "
                f"들어 있지 않습니다. 변형 정의를 보완하세요.\n  {exc}"
            ) from exc

        facts.append(fact)

    for extra in variant.add:
        fact = json.loads(json.dumps(extra))
        quote = fact.pop("_evidence_quote")
        fact["evidence"] = [locate(document, quote)]
        facts.append(fact)

    return facts


def build() -> list[tuple[Variant, Path]]:
    base_policy = BASE_POLICY.read_text(encoding="utf-8")
    base_gold = json.loads(BASE_GOLD.read_text(encoding="utf-8"))

    OUT_DIR.mkdir(exist_ok=True)
    built: list[tuple[Variant, Path]] = []

    for variant in VARIANTS:
        document = apply_edits(base_policy, variant.edits)
        facts = rebuild_facts(base_gold["facts"], document, variant)

        expected = dict(BASE_STATUS)
        expected[variant.target_rule] = variant.expected_status

        directory = OUT_DIR / variant.name
        directory.mkdir(exist_ok=True)
        (directory / "policy.txt").write_text(document, encoding="utf-8")
        payload = {
            "source_document_id": f"SC-P01-{variant.name}",
            "poc": "poc1",
            "policy_text_file": "policy.txt",
            "fact_schema_version": "fact-1.0",
            "variant": {
                "name": variant.name,
                "description": variant.description,
                "target_rule": variant.target_rule,
                "expected_status": variant.expected_status,
            },
            "expected_rule_status": expected,
            "facts": facts,
        }
        if variant.presence:
            payload["system_metadata"] = [
                {
                    "field": "activity_presence",
                    "activity_type": activity_type,
                    "state": "confirmed_false",
                    "source_type": "policy_text",
                    "evidence": [locate(document, quote)],
                }
                for activity_type, quote in variant.presence
            ]
        (directory / "gold_facts.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        built.append((variant, directory))

    return built


def main() -> int:
    built = build()
    print(f"변형 {len(built)}개 생성 -> {OUT_DIR}")
    for variant, directory in built:
        facts = json.loads((directory / "gold_facts.json").read_text(encoding="utf-8"))["facts"]
        print(f"  {variant.name:28s} {variant.target_rule} {variant.expected_status:6s} "
              f"fact {len(facts)}개")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
