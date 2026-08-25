from backend.models import PolicyFacts, ExtractedField, FieldStatus, Verdict
from backend.rules.rule_engine import evaluate_policy


def _all_present_facts() -> PolicyFacts:
    field = ExtractedField(status=FieldStatus.PRESENT, evidence="더미 근거", confidence=0.9)
    return PolicyFacts(
        purpose=field, collection_items=field, retention_period=field,
        third_party_provision=field, outsourcing=field, destruction_procedure=field,
        cross_border_transfer=field, consent_withdrawal_method=field,
        data_subject_rights_method=field, privacy_officer_contact=field,
        involves_minor=False, involves_sensitive_data=False,
    )


def test_all_present_yields_amber_on_cross_border():
    """국외이전은 '명시적 부재'가 아니라 '존재'로 잡혀도 별도 로직이 없으면
    기본 로직상 GREEN 처리됨을 확인 (extra_check 는 ABSENT 케이스에서만 개입)"""
    facts = _all_present_facts()
    report = evaluate_policy(facts)
    r07 = next(r for r in report.results if r.rule_id == "R07")
    assert r07.verdict == Verdict.GREEN


def test_missing_field_yields_red():
    facts = _all_present_facts()
    facts.retention_period = ExtractedField(status=FieldStatus.ABSENT, confidence=0.9)
    report = evaluate_policy(facts)
    r03 = next(r for r in report.results if r.rule_id == "R03")
    assert r03.verdict == Verdict.RED
    assert report.overall_verdict == Verdict.RED


def test_low_confidence_yields_amber():
    facts = _all_present_facts()
    facts.purpose = ExtractedField(status=FieldStatus.PRESENT, confidence=0.3)
    report = evaluate_policy(facts)
    r01 = next(r for r in report.results if r.rule_id == "R01")
    assert r01.verdict == Verdict.AMBER


def test_minor_context_adds_r11_amber():
    facts = _all_present_facts()
    facts.involves_minor = True
    report = evaluate_policy(facts)
    r11 = next((r for r in report.results if r.rule_id == "R11"), None)
    assert r11 is not None
    assert r11.verdict == Verdict.AMBER
