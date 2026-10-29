"""프롬프트가 정본 계약에서 낡지 않았는지 본다.

프롬프트는 LLM에게 "이 Fact ID에는 이 ontology_property를 쓰라"고 지시한다. 정본
레지스트리가 바뀌면 그 지시만 조용히 낡고, 증상은 실제 API 실행 때 "추출은 됐는데
검증에서 전부 reject"라는 형태로 처음 드러난다. 돈을 쓰기 전에 잡아야 하는 자리다.

실제로 통합 시점에 F1-03/F1-04/F1-09 세 건이 이 상태였다.
"""

import json
import re
from pathlib import Path

import pytest

from app.extractors.prompts import (
    PASS1_SYSTEM,
    PASS2_SYSTEM,
    POC1_FACT_CATALOG,
    RIGHTS_SYSTEM,
)
from app.mapping.mapping_registry import FACT_SPECS

ROOT = Path(__file__).resolve().parents[1]
GOLD_PATH = ROOT / "evals" / "poc1" / "sc_p01_gold_facts.json"

# Pass 2가 실제로 뽑는 Fact. F1-00(명시적 부재)은 Pass 1이 따로 처리한다.
EXTRACTABLE_FACT_IDS = {f"F1-{n:02d}" for n in range(1, 23)}  # v1.1: F1-13~F1-22

PROMPTS = {
    "PASS1_SYSTEM": PASS1_SYSTEM,
    "PASS2_SYSTEM": PASS2_SYSTEM,
    "RIGHTS_SYSTEM": RIGHTS_SYSTEM,
}

# 선언된 값 타입 -> gold set에서 기대되는 파이썬 타입
DECLARED_VALUE_TYPES = {
    "문자열": str,
    "문자열 배열": list,
    "객체": dict,
    "없음": type(None),
}


def declared_kind(value_type: str) -> type:
    # "문자열 배열"이 "문자열"에 먼저 걸리지 않도록 긴 표기부터 본다
    for prefix in sorted(DECLARED_VALUE_TYPES, key=len, reverse=True):
        if value_type.startswith(prefix):
            return DECLARED_VALUE_TYPES[prefix]
    raise AssertionError(f"해석할 수 없는 값 타입 표기: {value_type!r}")


@pytest.fixture(scope="module")
def gold() -> dict:
    return json.loads(GOLD_PATH.read_text(encoding="utf-8"))


# --- 레지스트리와의 동기화 ------------------------------------------------


@pytest.mark.parametrize("fact_id, _d, prop, _v", POC1_FACT_CATALOG)
def test_catalog_property_matches_the_registry(fact_id: str, _d: str, prop, _v: str):
    """카탈로그는 레지스트리에서 끌어오므로 지금은 항상 참이다.

    다시 손으로 적어 넣는 순간 깨지라고 두는 가드다.
    """
    assert prop == FACT_SPECS[fact_id].ontology_property


def test_catalog_property_matches_the_gold_set(gold: dict):
    """프롬프트가 지시하는 property와 정답지가 쓰는 property가 같아야 한다.

    레지스트리를 거치지 않는 대조다. 정답지는 Extractor 출력을 채점하는 기준이므로,
    둘이 어긋나면 모델이 시킨 대로 뽑아도 전부 오답이 된다.
    """
    declared = {fact_id: prop for fact_id, _, prop, _ in POC1_FACT_CATALOG}
    for item in gold["facts"]:
        fact_id = item["fact_id"].split(":", 1)[0]
        if fact_id not in declared:
            continue
        assert item["ontology_property"] == declared[fact_id], item["fact_id"]


def test_catalog_covers_every_extractable_fact_id():
    """레지스트리에 Fact가 늘면 프롬프트도 같이 늘어야 한다."""
    assert {item[0] for item in POC1_FACT_CATALOG} == EXTRACTABLE_FACT_IDS
    assert EXTRACTABLE_FACT_IDS <= set(FACT_SPECS)


@pytest.mark.parametrize("name", sorted(PROMPTS))
def test_no_prompt_mentions_a_property_the_registry_rejects(name: str):
    """표가 아니라 산문에 직접 적힌 property 이름까지 훑는다.

    카탈로그를 레지스트리에서 끌어오도록 바꿔도, 누군가 설명 문장에 이름을
    손으로 적으면 같은 드리프트가 다시 생긴다.
    """
    known = {spec.ontology_property for spec in FACT_SPECS.values()} - {None}
    mentioned = set(re.findall(r"ontology_property=(\w+)", PROMPTS[name])) - {"null"}
    assert mentioned <= known, f"{name}: 레지스트리에 없는 property {sorted(mentioned - known)}"


# --- 정답지와의 동기화 ----------------------------------------------------


def test_declared_value_types_match_the_gold_set(gold: dict):
    """프롬프트가 알려준 값 타입과 정답지의 실제 값 타입이 같아야 한다.

    F1-12가 대표적이다. 문자열 하나로 안내하면 모델이 절차를 하나만 내는데,
    엔진은 모든 권리에 절차가 붙어야 P1-R07을 GREEN으로 준다. 프롬프트만 보고는
    드러나지 않고 판정이 뒤집힌 뒤에야 알게 된다.
    """
    declared = {fact_id: declared_kind(value_type) for fact_id, _, _, value_type in POC1_FACT_CATALOG}

    seen = set()
    for item in gold["facts"]:
        if item["value_state"] != "confirmed":
            continue
        fact_id = item["fact_id"].split(":", 1)[0]
        seen.add(fact_id)
        assert isinstance(item["value"], declared[fact_id]), (
            f"{item['fact_id']}: 프롬프트는 {declared[fact_id].__name__}라고 안내하는데 "
            f"정답지는 {type(item['value']).__name__}이다"
        )
    assert seen, "정답지에서 confirmed Fact를 하나도 읽지 못했다"


@pytest.mark.parametrize("name", ["PASS2_SYSTEM", "INCIDENT_SYSTEM", "NOTICE_SYSTEM"])
def test_prompt_asks_for_evidence_on_unknown_and_absent(name: str):
    """Extractor는 인용이 빈 Fact를 상태와 무관하게 버린다 (검증기도 근거를 요구한다).

    첫 실제 실행에서 F1-03 absent 7건이 이 이유로 버려졌다. 프롬프트가 absent일 때
    무엇을 인용할지 알려주지 않았기 때문이다.
    """
    from app.extractors import prompts, prompts_poc2

    text = getattr(prompts, name, None) or getattr(prompts_poc2, name)
    assert "unknown과 absent도 evidence_text가 비어 있으면 버려집니다" in text


def test_pass1_asks_for_a_single_line_heading():
    """두 줄을 이어 붙인 heading 때문에 처리행위가 빠진 적이 있다 (실측 v2, v4)."""
    from app.extractors.prompts import PASS1_SYSTEM

    assert "한 줄 안의 문구만 쓰십시오" in PASS1_SYSTEM


@pytest.mark.parametrize(
    "phrase",
    [
        "구체적인 내용이 없는 상투적 문구는 confirmed가 아닙니다",  # 실측 v2 위험 오판
        "처리행위의 제목이나 항목명을 값으로 옮기지 마십시오",      # 실측 v1 위험 오판
    ],
)
def test_pass2_guards_against_the_observed_false_greens(phrase: str):
    from app.extractors.prompts import PASS2_SYSTEM

    assert phrase in PASS2_SYSTEM


@pytest.mark.parametrize(
    "variant, state",
    [
        ("v2-vague-destruction", "unknown"),    # "적절한 방법으로" — 언급했지만 비어 있다
        ("v3-missing-destruction", "absent"),   # "지체 없이 파기" — 방법을 아예 말하지 않는다
    ],
)
def test_vague_value_rule_matches_the_gold_set(variant: str, state: str):
    """프롬프트 8번 규칙의 두 갈래를 정답지도 같은 방식으로 나눈다.

    8번 규칙 첫 버전은 둘을 구분하지 않아 v3가 RED -> YELLOW로 움직였다 (실측).
    """
    import json

    from app.extractors.prompts import PASS2_SYSTEM

    assert "그 항목을 언급했지만 내용이 비어 있을 때만" in PASS2_SYSTEM
    gold = json.loads(
        (ROOT / f"evals/poc1/variants/{variant}/gold_facts.json").read_text(encoding="utf-8")
    )
    destruction = [f for f in gold["facts"] if f["fact_id"].startswith("F1-08")]
    assert [f["value_state"] for f in destruction] == [state]


def test_unspecified_statutory_period_is_unknown_not_resolved():
    """Issue 4 팀 결정: 법령을 연동해 채우지 않고 알 수 없음으로 둔다.

    프롬프트와 정답지가 같은 기준이어야 Fact 단위 채점이 의미를 가진다.
    """
    from app.extractors.prompts import PASS2_SYSTEM

    assert "근거 법령도 숫자도 특정하지 않은 기간" in PASS2_SYSTEM
    assert "어떤 법령일지 추정하거나 법정" in PASS2_SYSTEM
    gold = json.loads(GOLD_PATH.read_text(encoding="utf-8"))
    general = "그 밖의 처리 목적에 대해서는 관계 법령에서 정한 기간 동안 보관합니다."
    covered = {
        item["activity_id"]: item["value_state"]
        for item in gold["facts"]
        if item["fact_id"].startswith("F1-03")
        and item["value_state"] != "absent"
        and item["evidence"][0]["text"] == general
    }
    assert covered and set(covered.values()) == {"unknown"}


def test_event_bounded_span_is_an_end_condition_not_an_unknown_period(gold: dict):
    """팀 결정 (Issue 4 후속): '서비스 이용기간 동안'은 사건으로 끝이 정해진다 -> F1-04.

    '기간'이라는 단어로 가르면 같은 뜻의 "서비스 이용 종료 시까지"와 결과가 갈린다.
    정답지(국외 이전: "서비스 이용기간 또는 처리 목적 달성 시까지")도 F1-03 absent다.
    """
    from app.extractors.prompts import PASS2_SYSTEM

    assert "끝이 어떻게 정해지는지로 가르십시오" in PASS2_SYSTEM
    assert "서비스 이용기간 동안" in PASS2_SYSTEM
    crossborder = {
        f["fact_id"].split(":")[0]: f["value_state"]
        for f in gold["facts"]
        if f["activity_id"] == "act-crossborder-001" and f["fact_id"].startswith(("F1-03", "F1-04"))
    }
    assert crossborder == {"F1-03": "absent", "F1-04": "confirmed"}


def test_every_gold_fact_has_evidence_even_without_a_value(gold: dict):
    """프롬프트가 요구하는 것과 정답지가 같아야 한다."""
    for item in gold["facts"]:
        if item["value_state"] != "confirmed":
            assert item["evidence"], item["fact_id"]


def test_rights_procedure_is_requested_per_right(gold: dict):
    """F1-12는 권리 수만큼 나와야 한다 (엔진이 모든 권리에 절차를 요구한다)."""
    rights = [i for i in gold["facts"] if i["fact_id"].startswith("F1-11")]
    procedures = [i for i in gold["facts"] if i["fact_id"].startswith("F1-12")]
    assert len(procedures) == sum(len(item["value"]) for item in rights)
    for item in procedures:
        assert set(item["value"]) == {"right", "procedure"}
