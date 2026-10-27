"""SC-P02 기준 세트에서 controlled variants를 만든다.

기준 세트 하나로는 GREEN만 나온다. TST-003은 PoC마다 대표 케이스를 요구하므로
YELLOW와 RED 경로를 만들 변형이 필요하다.

각 변형은 Fact 하나만 건드리고, 움직이는 Rule은 **Fact Dictionary 7장 Coverage가
그 Fact를 소비한다고 적은 Rule**뿐이어야 한다. F2-02처럼 두 Rule이 공유하는 Fact는
둘 다 움직이는 것이 정상이고, 그 외의 Rule이 움직이면 변형이 의도보다 넓게 퍼진
것이다. 이 불변식은 tests/test_variants_poc2.py가 강제한다.

PoC1 빌더와 다른 점은 문서가 둘이라는 것이다. 사고 기록과 통지문을 각각 편집하고,
근거도 각자의 문서에서 다시 찾는다.

실행:
    python evals/poc2/build_variants.py
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# 통지문이 없을 때 Extractor가 내는 Fact 모양. 정답지가 이것과 어긋나면 안 되므로
# 다시 적지 않고 가져온다.
from app.extractors.poc2 import NOTICE_ABSENCE_SHAPE, INCIDENT_ID  # noqa: E402
BASE_INCIDENT = HERE / "sc_p02_incident.txt"
BASE_NOTICE = HERE / "sc_p02_notice.txt"
BASE_GOLD = HERE / "sc_p02_gold_facts.json"
OUT_DIR = HERE / "variants"

INCIDENT_NAME = "incident.txt"
NOTICE_NAME = "notice.txt"

# Fact의 source_type -> 근거를 찾을 문서. evals/dataset.py와 같은 규약이다.
DOCUMENT_OF_SOURCE = {
    "incident_record": "incident",
    "notification_notice": "notice",
}


@dataclass(frozen=True)
class Variant:
    name: str
    description: str
    target_rule: str
    expected_status: str
    incident_edits: tuple[tuple[str, str], ...] = ()
    notice_edits: tuple[tuple[str, str], ...] = ()
    # fact_id -> (value_state, 근거 인용). 값은 버리고 상태만 남긴다.
    restate: dict[str, tuple[str, str]] = field(default_factory=dict)
    # fact_id -> (새 값, 근거 인용 목록). 값 자체를 줄일 때 쓴다.
    revalue: dict[str, tuple[Any, list[str]]] = field(default_factory=dict)
    # 겨냥한 Rule 외에 함께 움직이는 Rule (7장 Coverage가 Fact를 공유하는 경우)
    also_moves: dict[str, str] = field(default_factory=dict)
    # 통지문 자체가 없다. 통지문 Fact는 absent(derived)가 되고, 통지문 부재가
    # activity presence metadata(NotificationNotice=confirmed_false)로 명시된다.
    no_notice: bool = False

    @property
    def changed_facts(self) -> set[str]:
        """이 변형이 건드린 Fact 유형. 7장 Coverage 대조에 쓴다."""
        changed = {
            fact_id.split(":", 1)[0]
            for fact_id in (*self.restate, *self.revalue)
        }
        if self.no_notice:
            changed |= set(NOTICE_ABSENCE_SHAPE)
        return changed


VARIANTS: list[Variant] = [
    Variant(
        name="v1-incident-missing-items",
        description="사고 기록에서 실제 영향 항목 기재를 삭제한다. F2-02가 absent가 된다.",
        target_rule="P2-R01",
        expected_status="RED",
        # F2-02는 7장에서 P2-R01과 P2-R02가 함께 소비한다. 둘 다 움직이는 것이 정상이다.
        also_moves={"P2-R02": "RED"},
        incident_edits=(
            (
                "이번 사고로 실제 노출된 개인정보 항목은 이메일 주소입니다.\n"
                "성명, 연락처, 결제정보 등 다른 항목은 발송 대상에 포함되지 않아 노출되지 않았습니다.\n",
                "",
            ),
        ),
        restate={"F2-02:breach-incident": ("absent", "2. 실제 영향을 받은 개인정보")},
    ),
    Variant(
        name="v2-notice-omits-items",
        description="통지문에서 유출 항목 기재를 삭제한다. F2-04가 absent가 된다.",
        target_rule="P2-R02",
        expected_status="RED",
        notice_edits=(("유출된 개인정보 항목은 이메일 주소입니다.\n", ""),),
        restate={"F2-04:breach-notice": ("absent", "2. 유출된 개인정보 항목")},
    ),
    Variant(
        name="v3-notice-missing-incident-time",
        description="통지문에서 유출등 시점 기재를 삭제한다. F2-08이 absent가 된다.",
        target_rule="P2-R03",
        expected_status="RED",
        also_moves={"P2-R09": "YELLOW"},
        notice_edits=(("유출이 발생한 시점은 2026년 9월 5일 14시 30분입니다.\n", ""),),
        restate={"F2-08:breach-notice": ("absent", "1. 유출등이 발생한 시점")},
    ),
    Variant(
        name="v4-partial-response-measures",
        description="사고 기록에서 대응조치 2건을 삭제한다. 필수 4종 중 2종만 남는다.",
        target_rule="P2-R08",
        expected_status="YELLOW",
        incident_edits=(
            ("개인정보보호 담당부서 연락처를 통한 문의 및 피해구제 절차를 안내하였습니다.\n", ""),
            ("재발을 막기 위해 대량 메일 발송 절차 점검과 수신자 필드 검증 통제를 적용하였습니다.\n", ""),
        ),
        revalue={
            "F2-10:breach-incident": (
                [
                    {"measure_role": "data_subject_guidance",
                     "text": "의심스러운 이메일과 링크에 주의하도록 안내"},
                    {"measure_role": "controller_response",
                     "text": "발송 경로를 확인하고 추가 노출을 차단"},
                ],
                [
                    "의심스러운 이메일과 링크에 주의하도록 안내하였습니다",
                    "발송 경로를 확인하고 추가 노출을 차단하였습니다",
                ],
            )
        },
    ),
    Variant(
        name="v5-no-response-measures",
        description="사고 기록에서 대응조치 기재를 통째로 삭제한다. F2-10이 absent가 된다.",
        target_rule="P2-R08",
        expected_status="RED",
        incident_edits=(
            (
                "정보주체에게는 의심스러운 이메일과 링크에 주의하도록 안내하였습니다.\n"
                "담당 부서는 발송 경로를 확인하고 추가 노출을 차단하였습니다.\n"
                "개인정보보호 담당부서 연락처를 통한 문의 및 피해구제 절차를 안내하였습니다.\n"
                "재발을 막기 위해 대량 메일 발송 절차 점검과 수신자 필드 검증 통제를 적용하였습니다.\n",
                "",
            ),
        ),
        restate={"F2-10:breach-incident": ("absent", "3. 사고 후 조치")},
    ),
    Variant(
        name="v6-no-notice",
        description="통지문을 제공하지 않는다. 통지문 부재가 명시되어 통지문 Rule은 N/A가 된다.",
        target_rule="P2-R02",
        expected_status="N/A",
        # 통지문이 없으면 P2-R03도 판정 대상이 없다(N/A). P2-R01은 "사고는 있으나
        # 통지문이 없음"을 RED로 드러낸다. 통지 의무 판정이 아니다 (engine 문구 참고).
        also_moves={"P2-R01": "RED", "P2-R03": "N/A", "P2-R09": "N/A"},
        no_notice=True,
    ),
]

# 서비스(with_notice_presence)가 통지문 없는 요청에 붙이는 것과 같은 metadata
NO_NOTICE_PRESENCE = {
    "field": "activity_presence",
    "activity_type": "NotificationNotice",
    "state": "confirmed_false",
    "source_type": "derived",
    "evidence": [{"field_path": "notification"}],
}


def notice_absence_facts() -> list[dict]:
    """통지문이 없을 때의 통지문 Fact. PoC2Extractor가 내는 것과 같은 모양이다."""
    return [
        {
            "fact_id": f"{fact_id}:{subject_id}",
            "subject_id": subject_id,
            "activity_id": INCIDENT_ID,
            "ontology_class": ontology_class,
            "ontology_property": prop,
            "value": None,
            "value_state": "absent",
            "source_type": "derived",
            "evidence": [{"field_path": "notification"}],
            "schema_version": "fact-1.0",
        }
        for fact_id, (subject_id, ontology_class, prop) in NOTICE_ABSENCE_SHAPE.items()
    ]


def apply_edits(document: str, edits: tuple[tuple[str, str], ...]) -> str:
    for old, new in edits:
        count = document.count(old)
        if count != 1:
            raise ValueError(f"편집 대상이 {count}회 나타납니다 (1회여야 함): {old[:40]!r}…")
        document = document.replace(old, new, 1)
    return document


def locate(document: str, quote: str) -> dict:
    start = document.find(quote)
    if start == -1:
        raise ValueError(f"변형 문서에서 근거를 찾지 못했습니다: {quote!r}")
    return {"text": quote, "start_offset": start, "end_offset": start + len(quote)}


def rebuild_facts(
    base_facts: list[dict], documents: dict[str, str], variant: Variant
) -> list[dict]:
    """기준 Fact를 변형 문서에 맞춰 다시 만든다.

    근거를 그 Fact의 source_type에 해당하는 문서에서 다시 찾는다. 찾지 못했는데
    변형 정의가 restate/revalue로 처리하지 않았다면 정의가 불완전한 것이므로 실패시킨다.
    """
    facts: list[dict] = []

    for base in base_facts:
        fact_id = base["fact_id"]
        fact = json.loads(json.dumps(base))  # 깊은 복사
        document = documents[DOCUMENT_OF_SOURCE.get(base["source_type"], "incident")]

        if fact_id in variant.restate:
            state, quote = variant.restate[fact_id]
            fact["value_state"] = state
            fact["value"] = None
            fact["evidence"] = [locate(document, quote)]
            fact["_note"] = f"변형 {variant.name}: {variant.description}"
            facts.append(fact)
            continue

        if fact_id in variant.revalue:
            value, quotes = variant.revalue[fact_id]
            fact["value"] = value
            fact["evidence"] = [locate(document, quote) for quote in quotes]
            fact["_note"] = f"변형 {variant.name}: {variant.description}"
            facts.append(fact)
            continue

        try:
            fact["evidence"] = [
                locate(document, piece["text"]) for piece in base["evidence"]
            ]
        except ValueError as exc:
            raise ValueError(
                f"{variant.name}: {fact_id}의 근거가 변형 문서에 없는데 "
                f"restate/revalue에 들어 있지 않습니다. 변형 정의를 보완하세요.\n  {exc}"
            ) from exc

        facts.append(fact)

    return facts


def build() -> list[tuple[Variant, Path]]:
    base_incident = BASE_INCIDENT.read_text(encoding="utf-8")
    base_notice = BASE_NOTICE.read_text(encoding="utf-8")
    base_gold = json.loads(BASE_GOLD.read_text(encoding="utf-8"))
    base_status = base_gold["expected_rule_status"]

    OUT_DIR.mkdir(exist_ok=True)
    built: list[tuple[Variant, Path]] = []

    for variant in VARIANTS:
        documents = {
            "incident": apply_edits(base_incident, variant.incident_edits),
            "notice": apply_edits(base_notice, variant.notice_edits),
        }
        if variant.no_notice:
            incident_facts = [
                f for f in base_gold["facts"]
                if f["fact_id"].split(":", 1)[0] not in NOTICE_ABSENCE_SHAPE
            ]
            facts = rebuild_facts(incident_facts, documents, variant) + notice_absence_facts()
        else:
            facts = rebuild_facts(base_gold["facts"], documents, variant)

        expected = dict(base_status)
        expected[variant.target_rule] = variant.expected_status
        expected.update(variant.also_moves)

        directory = OUT_DIR / variant.name
        directory.mkdir(exist_ok=True)
        (directory / INCIDENT_NAME).write_text(documents["incident"], encoding="utf-8")
        payload = {
            "source_document_id": f"SC-P02-{variant.name}",
            "poc": "poc2",
            "incident_text_file": INCIDENT_NAME,
            "notice_text_file": None if variant.no_notice else NOTICE_NAME,
            "fact_schema_version": "fact-1.0",
            "variant": {
                "name": variant.name,
                "description": variant.description,
                "target_rule": variant.target_rule,
                "expected_status": variant.expected_status,
                "also_moves": variant.also_moves,
                "changed_facts": sorted(variant.changed_facts),
            },
            "expected_rule_status": expected,
            "facts": facts,
        }
        if variant.no_notice:
            payload["system_metadata"] = [NO_NOTICE_PRESENCE]
        else:
            (directory / NOTICE_NAME).write_text(documents["notice"], encoding="utf-8")
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
        print(f"  {variant.name:32s} {variant.target_rule} {variant.expected_status:6s} "
              f"fact {len(facts)}개")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
