"""v1.1 P1-R09 국외 이전 기재 / P1-R10 개인정보 보호책임자·연락처 기재.

판정 기준 (항목 단위):
  RED     필수 항목이 문서 전체에서 명확히 누락 (absent)
  YELLOW  일부만 기재됐거나 모호함 (unknown), 또는 추출되지 않아 확인이 더 필요함
  GREEN   필수 기재사항이 모두 확인됨
  N/A     의무 자체가 적용되지 않음 (국외 이전을 하지 않는다고 명시)
"""

import pytest

from app.facts.graph import facts_to_mapping
from app.mapping.presence_metadata import activity_presence_metadata
from app.rules.engine import P0RuleEngine

ACT = "act-crossborder-001"
EV = [{"text": "x", "start_offset": 0, "end_offset": 1}]

TRANSFER = {
    "F1-13": ("CrossBorderTransfer", "hasDestinationCountry", "일본"),
    "F1-14": ("CrossBorderTransfer", "hasPersonalInformation", ["이메일 주소", "예약 내역"]),
    "F1-15": ("CrossBorderTransfer", "hasPurpose", "해외 지점 예약 처리"),
    "F1-16": ("CrossBorderTransfer", "hasTransferRecipient", "Example Travel K.K."),
    "F1-17": ("OverseasRecipient", "hasContact", ["privacy@example.org"]),
    "F1-18": ("CrossBorderTransfer", "hasTransferTimingAndMethod", "예약 확정 시 암호화 전송"),
    "F1-19": ("CrossBorderTransfer", "hasTransferRefusalProcedure", "이메일로 거부, 거부 시 예약 불가"),
}
OFFICER = {
    "F1-20": ("PersonalInformationController", "hasPrivacyOfficer",
              {"name": "홍길동", "department": "정보보호팀"}),
    "F1-21": ("PrivacyOfficer", "hasContact", ["02-0000-0000"]),
}


def fact(fact_id: str, spec: tuple, state: str = "confirmed", *, activity: str | None = ACT) -> dict:
    cls, prop, value = spec
    subject = activity or "privacy-officer"
    return {
        "fact_id": f"{fact_id}:{subject}", "subject_id": subject, "activity_id": activity,
        "ontology_class": cls, "ontology_property": prop,
        "value": value if state == "confirmed" else None, "value_state": state,
        "source_type": "policy_text", "evidence": EV, "schema_version": "fact-1.0",
    }


def transfer_facts(**states: str) -> list[dict]:
    return [fact(fid, spec, states.get(fid.replace("-", "_"), "confirmed"))
            for fid, spec in TRANSFER.items()]


def officer_facts(**states: str) -> list[dict]:
    return [fact(fid, spec, states.get(fid.replace("-", "_"), "confirmed"), activity=None)
            for fid, spec in OFFICER.items()]


def status(facts: list[dict], rule_id: str, system_metadata=None) -> str:
    mapping = facts_to_mapping(facts, system_metadata=system_metadata)
    results = P0RuleEngine().evaluate_mapping_result(mapping, poc="poc1")
    return next(r for r in results if r.rule_id == rule_id).status.value


# --- P1-R09 ---------------------------------------------------------------


def test_p1_r09_green_when_all_seven_items_are_written():
    assert status(transfer_facts(), "P1-R09") == "GREEN"


@pytest.mark.parametrize("fact_id", sorted(TRANSFER))
def test_p1_r09_red_when_any_item_is_absent(fact_id: str):
    assert status(transfer_facts(**{fact_id.replace("-", "_"): "absent"}), "P1-R09") == "RED"


@pytest.mark.parametrize("fact_id", sorted(TRANSFER))
def test_p1_r09_yellow_when_an_item_is_vague(fact_id: str):
    assert status(transfer_facts(**{fact_id.replace("-", "_"): "unknown"}), "P1-R09") == "YELLOW"


def test_p1_r09_absent_outweighs_unknown():
    assert status(transfer_facts(F1_16="absent", F1_18="unknown"), "P1-R09") == "RED"


def test_p1_r09_is_na_when_the_policy_says_it_does_not_transfer_abroad():
    absence = activity_presence_metadata(
        "CrossBorderTransfer", "confirmed_false", source_type="policy_text",
        evidence=[{"text": "국외로 이전하지 않습니다", "start_offset": 0, "end_offset": 12}],
    )
    assert status(officer_facts(), "P1-R09", [absence]) == "N/A"


def test_p1_r09_silence_is_not_na():
    """국외 이전 언급이 없다는 것은 '하지 않는다'는 선언이 아니다 (CLAUDE.md §5)."""
    assert status(officer_facts(), "P1-R09") == "YELLOW"


# --- P1-R10 ---------------------------------------------------------------


def test_p1_r10_green_with_name_department_and_contact():
    assert status(officer_facts(), "P1-R10") == "GREEN"


@pytest.mark.parametrize("identity", [{"name": "홍길동"}, {"department": "정보보호팀"}])
def test_p1_r10_name_or_department_is_enough(identity: dict):
    facts = officer_facts()
    facts[0]["value"] = identity
    assert status(facts, "P1-R10") == "GREEN"


@pytest.mark.parametrize("missing", ["F1_20", "F1_21"])
def test_p1_r10_red_when_identity_or_contact_is_absent(missing: str):
    assert status(officer_facts(**{missing: "absent"}), "P1-R10") == "RED"


def test_p1_r10_yellow_when_only_a_title_is_written():
    """직함만 있으면 F1-20 unknown -> 확인 필요."""
    assert status(officer_facts(F1_20="unknown"), "P1-R10") == "YELLOW"


def test_p1_r10_unextracted_is_yellow_not_red():
    """Fact가 아예 없으면 '기재 없음'이 아니라 '추출 안 됨'이다. UNKNOWN과 ABSENT를 섞지 않는다."""
    assert status(transfer_facts(), "P1-R10") == "YELLOW"
