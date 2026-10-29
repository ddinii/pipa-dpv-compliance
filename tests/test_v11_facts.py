"""v1.1 Fact (F1-13~F1-21)와 온톨로지 v1.1 용어.

국외 이전 기재(제28조의8 제2항)와 개인정보 보호책임자 기재(제30조 제1항 제6호).
"""

import json
import re
from pathlib import Path

import pytest

from app.facts.graph import facts_to_mapping
from app.mapping.fact_schema import FactValidationError, validate_facts
from app.mapping.mapping_registry import DOCUMENT_SCOPE_FACTS, FACT_SPECS

ROOT = Path(__file__).resolve().parents[1]
ONTOLOGY = (ROOT / "ontology" / "PIPA_Ontology_v1.0.ttl").read_text(encoding="utf-8")
V11 = [f"F1-{n}" for n in range(13, 23)]


def defined(term: str) -> bool:
    return re.search(rf"^pipa:{re.escape(term)} a ", ONTOLOGY, re.MULTILINE) is not None


def fact(fact_id, cls, prop, value, *, activity="act-crossborder-001", state="confirmed"):
    subject = activity or "privacy-officer"
    return {
        "fact_id": f"{fact_id}:{subject}", "subject_id": subject, "activity_id": activity,
        "ontology_class": cls, "ontology_property": prop, "value": value if state == "confirmed" else None,
        "value_state": state, "source_type": "policy_text",
        "evidence": [{"text": "x", "start_offset": 0, "end_offset": 1}], "schema_version": "fact-1.0",
    }


def test_v11_facts_are_registered_after_the_frozen_35():
    assert set(V11) <= set(FACT_SPECS)
    assert len(FACT_SPECS) == 45


@pytest.mark.parametrize("fact_id", V11)
def test_every_v11_fact_uses_terms_that_exist_in_the_ontology(fact_id: str):
    """CLAUDE.md: 온톨로지 용어를 지어내지 않는다. v1.1에서 추가한 용어도 파일에 있어야 한다."""
    spec = FACT_SPECS[fact_id]
    assert defined(spec.subject_class), spec.subject_class
    assert defined(spec.ontology_property), spec.ontology_property


def test_ontology_and_profile_report_version_1_1():
    assert 'owl:versionInfo "1.1"' in ONTOLOGY
    profile = json.loads((ROOT / "rules" / "p0_rules.json").read_text(encoding="utf-8"))
    assert profile["ontology_version"] == "1.1"


def test_officer_facts_are_document_scope():
    """보호책임자는 처리행위에 속하지 않는다. F1-11처럼 activity_id 없이 받는다."""
    assert {"F1-20", "F1-21"} <= DOCUMENT_SCOPE_FACTS
    validate_facts([
        fact("F1-20", "PersonalInformationController", "hasPrivacyOfficer", {"department": "개인정보보호팀"}, activity=None),
        fact("F1-21", "PrivacyOfficer", "hasContact", ["privacy@example.com"], activity=None),
    ])


def test_officer_identity_needs_name_or_department():
    with pytest.raises(FactValidationError, match="name 또는 department"):
        validate_facts([fact("F1-20", "PersonalInformationController", "hasPrivacyOfficer",
                             {"title": "팀장"}, activity=None)])


def test_recipient_name_and_contact_meet_on_one_node():
    """F1-16(이름)과 F1-17(연락처)이 같은 이전받는 자 노드에 붙어야 Rule이 둘을 함께 본다."""
    from app.rules.engine import PIPA

    graph = facts_to_mapping([
        fact("F1-16", "CrossBorderTransfer", "hasTransferRecipient", "클라우드원 Inc."),
        fact("F1-17", "OverseasRecipient", "hasContact", ["privacy@example.com"]),
    ]).graph
    recipients = set(graph.objects(None, PIPA.hasTransferRecipient))
    assert len(recipients) == 1
    recipient = recipients.pop()
    assert graph.value(recipient, PIPA.hasName) is not None
    assert graph.value(recipient, PIPA.hasContact) is not None


def test_extractor_value_union_keeps_officer_and_right_objects_apart():
    """F1-20 객체와 F1-12 객체가 union에서 서로의 모델로 잘못 읽히면 매퍼가 값을 잃는다."""
    from app.extractors.poc1 import ExtractedFact, OfficerIdentity, RightProcedure

    def parse(fact_id, value):
        return ExtractedFact.model_validate({
            "fact_id": fact_id, "activity_id": None, "ontology_property": None,
            "value": value, "value_state": "confirmed", "evidence_text": ["x"],
        }).value

    assert isinstance(parse("F1-20", {"name": "홍길동", "department": None}), OfficerIdentity)
    assert isinstance(parse("F1-12", {"right": "열람", "procedure": "이메일"}), RightProcedure)


@pytest.mark.parametrize(("fact_id", "activity", "expected"), [
    ("F1-20", None, ("privacy-officer", "PersonalInformationController")),
    ("F1-21", None, ("privacy-officer", "PrivacyOfficer")),
    ("F1-11", None, ("subj-001", "DataSubject")),
    ("F1-17", "act-crossborder-001", ("act-crossborder-001", "OverseasRecipient")),
    ("F1-16", "act-crossborder-001", ("act-crossborder-001", "CrossBorderTransfer")),
])
def test_extractor_subjects_match_the_registry(fact_id, activity, expected):
    from app.extractors.poc1 import ExtractedFact, IdentifiedActivity, PoC1Extractor

    raw = ExtractedFact(fact_id=fact_id, activity_id=activity, ontology_property=None,
                        value=None, value_state="absent", evidence_text=["x"])
    act = activity and IdentifiedActivity(activity_id=activity, ontology_class="CrossBorderTransfer",
                                          heading="x")
    assert PoC1Extractor._subject_for(raw, act) == expected
    assert FACT_SPECS[fact_id].subject_class == expected[1]


def test_extractor_accepts_a_declared_cross_border_absence():
    from app.extractors.poc1 import ActivityList, ExtractionResult, PoC1Extractor

    quote = "회사는 이용자의 개인정보를 국외로 이전하지 않습니다."
    pass1 = ActivityList.model_validate({
        "activities": [],
        "declared_absent": [{"activity_type": "CrossBorderTransfer", "quote": quote}],
    })
    metadata = PoC1Extractor._declared_absences(ExtractionResult(), pass1, f"제5조\n{quote}\n")
    assert [(m["activity_type"], m["state"]) for m in metadata] == [
        ("CrossBorderTransfer", "confirmed_false")
    ]


def test_unregistered_fact_ids_still_cannot_enter_the_pipeline():
    with pytest.raises(FactValidationError, match="매핑 정의가 없는 Fact"):
        facts_to_mapping([fact("F1-99", "CrossBorderTransfer", "hasDestinationCountry", "미국")])
