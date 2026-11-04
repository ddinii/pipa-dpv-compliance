"""PoC3 builder: explicit absent for retention.end_condition (F3-06 / F3-10 / F3-11)."""

import copy
import json
from pathlib import Path

import pytest

from app.builders.poc3_fact_builder import Poc3FormError, build_poc3_facts
from app.mapping.ontology_mapper import OntologyMapper
from app.rules.engine import P0RuleEngine
from app.services.compliance import run_design_check

EVALS = Path(__file__).resolve().parents[1] / "evals" / "poc3"
ABSENT = {"state": "absent"}
G, Y, R = "GREEN", "YELLOW", "RED"

ACTIVITY = {
    "activity_id": "A-1",
    "purpose": "회원 인증 및 주문내역 조회",
    "legal_basis": {"type": "Consent", "status": "confirmed"},
    "consent_request": {"planned": True},
    "personal_information_items": [
        {"item_name": "이메일 주소", "is_required": True, "design_rationale": "계정 식별 및 본인 인증"}
    ],
    "retention": {"end_condition": "회원 탈퇴 완료 시", "destruction_method": "관련 DB 레코드 영구 삭제"},
    "denies_service_on_optional_refusal": False,
}
FULL = ACTIVITY["retention"]


def form(*retentions):
    f = {"analysis_id": "Q-RA", "controller": {"controller_id": "QA", "name": "QA"},
         "collection_activities": [], "entrusted_processings": []}
    for i, retention in enumerate(retentions, 1):
        a = copy.deepcopy(ACTIVITY)
        a["activity_id"] = f"A-{i}"
        a["retention"] = retention
        f["collection_activities"].append(a)
    return f


def facts_of(f, prefix, activity="A-1"):
    return [x for x in build_poc3_facts(f) if x["fact_id"].startswith(prefix) and x["activity_id"] == activity]


def verdicts(f):
    return {r.rule_id: r.status.value for r in run_design_check(f)}


def per_activity(f, rule):
    r = next(x for x in run_design_check(f) if x.rule_id == rule)
    return {i.instance_id.rsplit("/", 1)[-1]: i.status.value for i in r.instance_results}


def test_both_absent_each_fact_reflects_its_own_field():
    f = form({"end_condition": ABSENT, "destruction_method": ABSENT})
    (f06,), (f10,), (f11,) = facts_of(f, "F3-06"), facts_of(f, "F3-10"), facts_of(f, "F3-11")
    assert f06["value_state"] == "confirmed"          # the retention object exists
    assert f06["value"]["end_condition"] is None      # no marker leaks into the Mapper
    assert (f10["value_state"], f10["value"]) == ("absent", None)
    assert f10["evidence"][0]["field_path"].endswith("retention.end_condition")
    assert (f11["value_state"], f11["value"]) == ("absent", None)
    assert f11["evidence"][0]["field_path"].endswith("retention.destruction_method")
    v = verdicts(f)
    assert v["P3-R04"] == R and v["P3-R08"] == R
    assert all(v[k] == G for k in ("P3-R01", "P3-R02", "P3-R03", "P3-R05"))
    assert v["P3-R06"] == "N/A"   # the test input has no optional item


def test_end_absent_does_not_make_concrete_method_absent():
    f = form({"end_condition": ABSENT, "destruction_method": "DB 레코드 영구 삭제"})
    (f10,) = facts_of(f, "F3-10")
    assert f10["value_state"] == "absent"
    assert facts_of(f, "F3-11") == []                 # nothing to link; method is not absent
    assert facts_of(f, "F3-06")[0]["value"]["destruction_method"] == "DB 레코드 영구 삭제"
    assert facts_of(f, "F3-06")[0]["value_state"] == "confirmed"
    v = verdicts(f)
    assert v["P3-R08"] == R and v["P3-R04"] == R


def test_method_absent_does_not_make_end_condition_absent():
    f = form({"end_condition": "회원 탈퇴 완료 시", "destruction_method": ABSENT})
    (f10,), (f11,) = facts_of(f, "F3-10"), facts_of(f, "F3-11")
    assert f10["value_state"] == "confirmed" and f10["value"] == "회원 탈퇴 완료 시"
    assert f11["value_state"] == "absent"
    v = verdicts(f)
    assert v["P3-R04"] == G and v["P3-R08"] == R


def test_concrete_period_with_absent_end_condition():
    f = form({"period": "3년", "end_condition": ABSENT, "destruction_method": "DB 레코드 영구 삭제"})
    v = verdicts(f)
    assert v["P3-R04"] == G      # a concrete period is enough for R04
    assert v["P3-R08"] == R      # R08 needs F3-10, explicitly absent


def test_empty_strings_keep_existing_behaviour():
    f = form({"end_condition": "", "destruction_method": ""})
    assert facts_of(f, "F3-10") == [] and facts_of(f, "F3-11") == []
    v = verdicts(f)
    assert v["P3-R04"] == R and v["P3-R08"] == Y


def test_empty_end_with_absent_method_is_unchanged():
    f = form({"end_condition": "", "destruction_method": ABSENT})
    assert facts_of(f, "F3-11") == []


@pytest.mark.parametrize("bad", [{"state": "missing"}, {"state": "absent", "x": 1}, {"state": None}])
def test_malformed_end_condition_state_object_is_input_error(bad):
    with pytest.raises(Poc3FormError):
        build_poc3_facts(form({"end_condition": bad, "destruction_method": "x y"}))


def test_absent_is_isolated_between_activities():
    f = form({"end_condition": ABSENT, "destruction_method": ABSENT}, FULL)
    assert per_activity(f, "P3-R04") == {"A-1": R, "A-2": G}
    assert per_activity(f, "P3-R08") == {"A-1": R, "A-2": G}
    assert [x["value_state"] for x in facts_of(f, "F3-10", "A-2")] == ["confirmed"]
    g = form(FULL, {"end_condition": ABSENT, "destruction_method": ABSENT})
    assert per_activity(g, "P3-R08") == {"A-1": G, "A-2": R}


def test_normal_input_facts_are_unchanged():
    f = form(FULL)
    assert facts_of(f, "F3-06")[0]["value"] == FULL
    assert [x["value_state"] for x in facts_of(f, "F3-10")] == ["confirmed"]
    assert [x["value_state"] for x in facts_of(f, "F3-11")] == ["confirmed"]


def test_corrected_p3_16_input():
    f = json.loads((EVALS / "p3_16_explicit_absent.json").read_text(encoding="utf-8"))
    assert verdicts(f) == {
        "P3-R01": G, "P3-R02": G, "P3-R03": G, "P3-R04": R,
        "P3-R05": G, "P3-R06": G, "P3-R08": R, "P3-R11": "N/A",
    }
