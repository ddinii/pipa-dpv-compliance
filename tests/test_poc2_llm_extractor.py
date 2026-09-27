"""LlmPoc2Extractor가 정본 Extractor 계약을 지키는지 본다.

수용 기준은 docs/context/backend/LLM_EXTRACTOR_HANDOFF.md 8장이고, 분리 원칙은
기능명세서 6장·P02-003과 Fact Dictionary 8장이다. LLM은 호출하지 않는다.

PoC2의 핵심은 "실제 사고 Fact와 통지문에 적힌 Fact를 절대 합치지 않는다"이므로,
여기서 가장 많이 보는 것도 그 경계다.
"""

import inspect

import pytest

from app.extractors.base import Poc2Extractor
from app.extractors.poc2 import (
    INCIDENT_ID,
    NOTICE_ID,
    ExtractedPoc2Fact,
    Poc2InputError,
)
from app.extractors.poc2_llm_extractor import ENV_API_KEY, LlmPoc2Extractor
from app.mapping.fact_schema import fact_type, validate_facts
from app.services.compliance import run_breach_check

INCIDENT_TEXT = (
    "2026년 8월 1일 오전 9시경 외부 침입으로 회원 데이터베이스가 유출되었습니다.\n"
    "유출된 항목은 이름, 이메일 주소, 전화번호입니다.\n"
    "회사는 2026년 8월 1일 오후 3시에 이상 접근을 인지하였습니다.\n"
    "정보주체에게 비밀번호 변경을 안내하였고, 침해 경로를 차단하였습니다.\n"
    "피해 신고 창구를 개설하였으며, 접근통제를 강화하였습니다."
)

NOTICE_TEXT = (
    "회원님께 개인정보 유출 사실을 알려드립니다.\n"
    "유출 시점은 2026년 8월 2일로 확인되었습니다.\n"
    "유출된 항목은 이름, 이메일 주소입니다.\n"
    "외부 침입에 의해 회원 데이터베이스가 유출되었습니다.\n"
    "본 통지는 2026년 8월 3일에 발송되었습니다."
)

ALLOWED_FACT_IDS = {f"F2-{n:02d}" for n in range(1, 11)}
INCIDENT_SIDE = {"F2-01", "F2-02", "F2-05", "F2-06"}
NOTICE_SIDE = {"F2-03", "F2-04", "F2-07", "F2-08", "F2-09"}


class StubMessages:
    def __init__(self, responses: list):
        self.responses = list(responses)
        self.calls: list[dict] = []

    def parse(self, **kwargs):
        self.calls.append(kwargs)
        payload = self.responses.pop(0)
        return type("Response", (), {"parsed_output": payload, "stop_reason": "end_turn"})()


def fact_list(*facts):
    return type("Poc2FactList", (), {"facts": list(facts)})()


def EF(fact_id, prop, value, quotes, state="confirmed"):
    return ExtractedPoc2Fact(
        fact_id=fact_id,
        ontology_property=prop,
        value=value,
        value_state=state,
        evidence_text=quotes,
    )


MEASURES = [
    {"measure_role": "data_subject_guidance", "text": "비밀번호 변경 안내"},
    {"measure_role": "controller_response", "text": "침해 경로 차단"},
    {"measure_role": "remedy_procedure", "text": "피해 신고 창구 개설"},
    {"measure_role": "post_incident_mitigation", "text": "접근통제 강화"},
]


def incident_response():
    return fact_list(
        EF("F2-01", None, None, ["외부 침입으로 회원 데이터베이스가 유출되었습니다"]),
        EF("F2-02", "affectsPersonalInformation",
           ["이름", "이메일 주소", "전화번호"],
           ["이름", "이메일 주소", "전화번호"]),
        EF("F2-05", "incidentDate", "2026-08-01T09:00:00+09:00",
           ["2026년 8월 1일 오전 9시경"]),
        EF("F2-06", "detectionDate", "2026-08-01T15:00:00+09:00",
           ["2026년 8월 1일 오후 3시에 이상 접근을 인지하였습니다"]),
        EF("F2-10", "hasResponseMeasure", MEASURES,
           ["비밀번호 변경을 안내하였고", "침해 경로를 차단하였습니다",
            "피해 신고 창구를 개설하였으며", "접근통제를 강화하였습니다"]),
    )


def notice_response():
    return fact_list(
        EF("F2-03", "hasNotificationNotice", "breach-notice",
           ["개인정보 유출 사실을 알려드립니다"]),
        EF("F2-04", "mentionsPersonalInformation", ["이름", "이메일 주소"],
           ["이름", "이메일 주소"]),
        EF("F2-07", "notificationDate", "2026-08-03T00:00:00+09:00",
           ["2026년 8월 3일에 발송되었습니다"]),
        EF("F2-08", None, "2026-08-02T00:00:00+09:00",
           ["유출 시점은 2026년 8월 2일로 확인되었습니다"]),
        EF("F2-09", "hasIncidentCircumstances",
           "외부 침입에 의해 회원 데이터베이스가 유출되었습니다",
           ["외부 침입에 의해 회원 데이터베이스가 유출되었습니다"]),
    )


def extract(responses, *, notification=True):
    extractor = LlmPoc2Extractor(StubMessages(responses))
    return extractor.extract(
        analysis_id="SC-P02",
        controller_id="ctrl-001",
        controller_name="모아커머스",
        incident={"description": INCIDENT_TEXT},
        notification={"notice_text": NOTICE_TEXT} if notification else None,
    )


def both_passes() -> list[dict]:
    return extract([incident_response(), notice_response()])


# --- handoff 2장: Protocol 계약 -----------------------------------------


def test_signature_matches_the_protocol_exactly():
    assert (
        inspect.signature(LlmPoc2Extractor.extract)
        == inspect.signature(Poc2Extractor.extract)
    )


# --- handoff 3·5장: Fact 출력 계약 ---------------------------------------


def test_output_passes_the_canonical_validator_unchanged():
    facts = both_passes()
    assert len(validate_facts(facts)) == len(facts)


def test_emits_only_the_frozen_poc2_fact_ids():
    assert {fact_type(item["fact_id"]) for item in both_passes()} <= ALLOWED_FACT_IDS


def test_source_type_separates_incident_from_notice():
    """Fact Dictionary 8장: incident_record와 notification_notice를 반드시 구분한다."""
    by_type = {fact_type(i["fact_id"]): i["source_type"] for i in both_passes()}
    for fact_id in INCIDENT_SIDE:
        assert by_type[fact_id] == "incident_record", fact_id
    for fact_id in NOTICE_SIDE:
        assert by_type[fact_id] == "notification_notice", fact_id
    # F2-10만 POC2_NOTICE_FACTS에 속해 사고 쪽에서 낼 때 derived를 쓴다
    assert by_type["F2-10"] == "derived"


def test_notice_facts_are_subject_to_the_notice_not_the_incident():
    """F2-04/F2-08/F2-09는 통지문이 subject다. 사고 인스턴스에 붙이면 안 된다."""
    subjects = {fact_type(i["fact_id"]): i["subject_id"] for i in both_passes()}
    for fact_id in ("F2-04", "F2-08", "F2-09"):
        assert subjects[fact_id] == NOTICE_ID, fact_id
    for fact_id in ("F2-01", "F2-02", "F2-05", "F2-06", "F2-10"):
        assert subjects[fact_id] == INCIDENT_ID, fact_id


def test_evidence_resolves_in_its_own_document():
    """근거는 그 Fact를 낸 문서에서만 해결되어야 한다 (NFR-07)."""
    facts = both_passes()
    for item in facts:
        document = NOTICE_TEXT if fact_type(item["fact_id"]) in NOTICE_SIDE else INCIDENT_TEXT
        assert item["evidence"], item["fact_id"]
        for piece in item["evidence"]:
            start, end = piece["start_offset"], piece["end_offset"]
            assert document[start:end] == piece["text"], item["fact_id"]


# --- 기능명세서 6장 · P02-003: 사고/통지 분리 -----------------------------


def test_each_pass_only_sees_its_own_document():
    """호출을 나누는 것이 혼합을 막는 구조다. 사고 pass에 통지문이 들어가면 안 된다."""
    stub = StubMessages([incident_response(), notice_response()])
    LlmPoc2Extractor(stub).extract(
        analysis_id="SC-P02",
        controller_id="ctrl-001",
        controller_name=None,
        incident={"description": INCIDENT_TEXT},
        notification={"notice_text": NOTICE_TEXT},
    )
    assert len(stub.calls) == 2
    incident_call, notice_call = stub.calls
    incident_blob = str(incident_call["system"]) + str(incident_call["messages"])
    notice_blob = str(notice_call["system"]) + str(notice_call["messages"])
    assert "유출 시점은 2026년 8월 2일" not in incident_blob
    assert "2026년 8월 1일 오전 9시경" not in notice_blob


def test_a_pass_may_not_emit_the_other_sides_facts():
    """사고 pass가 F2-04를 내면 버린다. 통지문을 보지도 않고 만든 값이다."""
    stray = fact_list(EF("F2-04", "mentionsPersonalInformation", ["이름"], ["이름"]))
    facts = extract([stray, notice_response()])
    assert not any(
        i["source_type"] == "incident_record" and fact_type(i["fact_id"]) == "F2-04"
        for i in facts
    )


def test_incident_date_and_notice_stated_time_stay_separate():
    """F2-05와 F2-08을 합치지 않는다 (Fact Dictionary 4장 주석 · EXTRACTOR_DECISIONS #2)."""
    values = {fact_type(i["fact_id"]): i["value"] for i in both_passes()}
    assert values["F2-05"] != values["F2-08"]


def test_actual_items_and_notice_items_stay_separate():
    """F2-02와 F2-04를 합치지 않는다. 통지문이 빠뜨린 항목은 빠뜨린 채로 남는다."""
    values = {fact_type(i["fact_id"]): i["value"] for i in both_passes()}
    assert values["F2-02"] == ["이름", "이메일 주소", "전화번호"]
    assert values["F2-04"] == ["이름", "이메일 주소"]


# --- handoff 5장 · EXTRACTOR_DECISIONS #6: 통지문 부재 ---------------------


def test_missing_notification_never_fabricates_a_notice():
    facts = extract([incident_response()], notification=False)
    by_type = {fact_type(i["fact_id"]): i for i in facts}
    for fact_id in NOTICE_SIDE:
        assert by_type[fact_id]["value_state"] == "absent", fact_id
        assert by_type[fact_id]["value"] is None, fact_id
        assert by_type[fact_id]["source_type"] == "derived", fact_id
    assert len(validate_facts(facts)) == len(facts)


def test_absence_is_not_confused_with_unknown():
    """handoff 3장: absent -> unknown 변환 금지. 입력 자체가 없으면 absent다."""
    facts = extract([incident_response()], notification=False)
    states = {fact_type(i["fact_id"]): i["value_state"] for i in facts}
    assert "unknown" not in {states[f] for f in NOTICE_SIDE}


# --- F2-10 measure_role enum (Fact Dictionary 4장) ------------------------


@pytest.mark.parametrize(
    "label, measures, reason",
    [
        ("v1에 없는 역할", [{"measure_role": "legal_review", "text": "법무 검토"}], "measure_role"),
        (
            "중복 역할",
            [
                {"measure_role": "controller_response", "text": "차단"},
                {"measure_role": "controller_response", "text": "재차단"},
            ],
            "중복",
        ),
        ("text 누락", [{"measure_role": "controller_response"}], "필요"),
    ],
)
def test_bad_response_measures_are_rejected(label, measures, reason):
    bad = fact_list(EF("F2-10", "hasResponseMeasure", measures, ["침해 경로를 차단하였습니다"]))
    extractor = LlmPoc2Extractor(StubMessages([bad]))
    extractor.extract(
        analysis_id="SC-P02", controller_id="c", controller_name=None,
        incident={"description": INCIDENT_TEXT}, notification=None,
    )
    # 거부되었으므로 F2-10 Fact가 없다
    facts = extract([bad], notification=False)
    assert not any(fact_type(i["fact_id"]) == "F2-10" for i in facts), label


# --- 입력 계약 -----------------------------------------------------------


def test_incident_without_readable_text_fails_loudly():
    """본문을 못 찾으면 지어내지 않고 실패한다 (COM-002 임의 보완 금지)."""
    extractor = LlmPoc2Extractor(StubMessages([]))
    with pytest.raises(Poc2InputError, match="incident"):
        extractor.extract(
            analysis_id="SC-P02", controller_id="c", controller_name=None,
            incident={"incident_id": "x"}, notification=None,
        )


# --- handoff 6장: 주입 지점 ----------------------------------------------


def test_injected_extractor_runs_the_four_poc2_rules():
    """TST-006 E2E: 사고/통지 분리 -> 4 Rule."""
    extractor = LlmPoc2Extractor(StubMessages([incident_response(), notice_response()]))
    results = run_breach_check(
        {
            "analysis_id": "SC-P02",
            "controller": {"controller_id": "ctrl-001", "name": "모아커머스"},
            "incident": {"description": INCIDENT_TEXT},
            "notification": {"notice_text": NOTICE_TEXT},
        },
        extractor=extractor,
    )
    statuses = {item.rule_id: item.status.value for item in results}
    assert set(statuses) == {"P2-R01", "P2-R02", "P2-R03", "P2-R08"}
    # 통지문이 전화번호를 빠뜨렸으므로 P2-R02는 GREEN일 수 없다
    assert statuses["P2-R02"] != "GREEN"
    # 나머지는 통지문이 모두 갖춰져 있으므로 확인된다
    assert statuses["P2-R01"] == "GREEN"
    assert statuses["P2-R03"] == "GREEN"
    assert statuses["P2-R08"] == "GREEN"


# --- handoff 7장 ---------------------------------------------------------


def test_from_environment_refuses_to_run_without_a_key(monkeypatch):
    monkeypatch.delenv(ENV_API_KEY, raising=False)
    with pytest.raises(RuntimeError, match=ENV_API_KEY):
        LlmPoc2Extractor.from_environment()


def test_diagnostics_are_opt_in():
    seen = []
    extractor = LlmPoc2Extractor(
        StubMessages([incident_response(), notice_response()]), on_result=seen.append
    )
    extractor.extract(
        analysis_id="SC-P02", controller_id="c", controller_name=None,
        incident={"description": INCIDENT_TEXT},
        notification={"notice_text": NOTICE_TEXT},
    )
    assert len(seen) == 1
    assert seen[0].rejected == []
