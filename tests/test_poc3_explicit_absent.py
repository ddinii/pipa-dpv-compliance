"""PoC3 builder: explicit absence marker ``{"state": "absent"}`` (P3-19/P3-20)."""

import copy
import json
from pathlib import Path

import pytest

from app.builders.poc3_fact_builder import Poc3FormError, build_poc3_facts
from app.mapping.ontology_mapper import OntologyMapper
from app.rules.engine import P0RuleEngine

EVALS = Path(__file__).resolve().parents[1] / "evals" / "poc3"
ABSENT = {"state": "absent"}


def load(name):
    return json.loads((EVALS / name).read_text(encoding="utf-8"))


def verdicts(form):
    facts = build_poc3_facts(form)
    mapped = OntologyMapper(form["analysis_id"], controller_id="QA", controller_name="QA").map(facts)
    return {r.rule_id: r.status.value for r in P0RuleEngine().evaluate_mapping_result(mapped, poc="PoC3")}


def test_p3_19_matches_expected_verdicts():
    assert verdicts(load("p3_19_explicit_absent.json")) == {
        "P3-R01": "GREEN", "P3-R02": "GREEN", "P3-R03": "RED", "P3-R04": "GREEN",
        "P3-R05": "RED", "P3-R06": "GREEN", "P3-R08": "RED", "P3-R11": "RED",
    }


def test_p3_20_matches_expected_verdicts():
    assert verdicts(load("p3_20_explicit_absent.json")) == {
        "P3-R01": "GREEN", "P3-R02": "GREEN", "P3-R03": "GREEN", "P3-R04": "GREEN",
        "P3-R05": "RED", "P3-R06": "RED", "P3-R08": "RED", "P3-R11": "RED",
    }


def test_absent_facts_follow_frozen_envelope():
    facts = build_poc3_facts(load("p3_19_explicit_absent.json"))
    absent = [f for f in facts if f["value_state"] == "absent"]
    # unnamed required item: F3-05 (name) and F3-08 (rationale) are absent
    assert {f["fact_id"][:5] for f in absent} == {"F3-05", "F3-08", "F3-11", "F3-12", "F3-13"}
    for f in absent:
        assert f["value"] is None and f["activity_id"] and f["evidence"][0]["field_path"]
    f05 = next(f for f in absent if f["fact_id"].startswith("F3-05"))
    assert f05["evidence"][0]["field_path"].endswith("personal_information_items[0].item_name")
    # named item keeps its information in a separate confirmed aggregate
    confirmed05 = next(f for f in facts if f["fact_id"].startswith("F3-05") and f["value_state"] == "confirmed")
    assert confirmed05["value"] == ["관심분야"]


def test_sentinel_strings_are_not_interpreted_as_absent():
    form = load("p3_20_explicit_absent.json")
    form["collection_activities"][0]["personal_information_items"][0]["design_rationale"] = "필요사유 미설계"
    facts = build_poc3_facts(form)
    assert not [f for f in facts if f["fact_id"].startswith("F3-08") and f["value_state"] == "absent"]
    assert verdicts(form)["P3-R05"] == "GREEN"


@pytest.mark.parametrize("bad", [{"state": "missing"}, {"state": "absent", "x": 1}, {"state": None}])
def test_malformed_state_object_is_input_error(bad):
    form = load("p3_20_explicit_absent.json")
    form["entrusted_processings"][0]["task"] = bad
    with pytest.raises(Poc3FormError):
        build_poc3_facts(form)


@pytest.mark.parametrize("path", ["task", "processor"])
def test_missing_required_field_without_marker_still_errors(path):
    form = load("p3_20_explicit_absent.json")
    form["entrusted_processings"][0][path] = ""
    with pytest.raises(Poc3FormError):
        build_poc3_facts(form)


def test_optional_item_rationale_absent_does_not_make_r05_red():
    form = load("p3_20_explicit_absent.json")
    items = form["collection_activities"][0]["personal_information_items"]
    items[0]["design_rationale"] = "이메일 로그인에 필요"
    items[1]["design_rationale"] = copy.deepcopy(ABSENT)
    assert verdicts(form)["P3-R05"] == "GREEN"


def test_required_item_rationale_absent_is_red():
    form = load("p3_20_explicit_absent.json")
    assert verdicts(form)["P3-R05"] == "RED"


def _unnamed(form, index, **item_changes):
    item = form["collection_activities"][0]["personal_information_items"][index]
    item["item_name"] = copy.deepcopy(ABSENT)
    item.update(item_changes)
    return form


def test_unnamed_optional_item_does_not_leak_into_r05():
    """Item-name gap is owned by R03; R05 judges by is_required/rationale."""
    form = load("p3_20_explicit_absent.json")
    items = form["collection_activities"][0]["personal_information_items"]
    items[0]["design_rationale"] = "이메일 로그인에 필요"
    _unnamed(form, 1)
    v = verdicts(form)
    assert v["P3-R03"] == "RED" and v["P3-R05"] == "GREEN"


def test_unnamed_item_keeps_identity_and_named_items_survive():
    form = _unnamed(load("p3_20_explicit_absent.json"), 1)
    facts = build_poc3_facts(form)
    aid = form["collection_activities"][0]["activity_id"]
    f05 = [f for f in facts if f["fact_id"].startswith("F3-05")]
    absent = next(f for f in f05 if f["value_state"] == "absent")
    assert absent["subject_id"] == f"{aid}-item-2"
    assert absent["evidence"][0]["field_path"].endswith("personal_information_items[1].item_name")
    f07 = next(f for f in facts if f["fact_id"].startswith("F3-07") and f["subject_id"] == f"{aid}-item-2")
    assert f07["value"] == {"item_name": None, "is_required": False}
    mapped = OntologyMapper(form["analysis_id"], controller_id="QA", controller_name="QA").map(facts)
    from rdflib import RDF
    from app.mapping.ontology_mapper import PIPA
    nodes = list(mapped.graph.subjects(RDF.type, PIPA.PersonalInformation))
    named = [n for n in nodes if list(mapped.graph.objects(n, PIPA.hasItemName))]
    assert len(nodes) == 2 and len(named) == 1  # named item untouched, unnamed has no hasItemName


def test_r03_red_r05_red_when_unnamed_required_rationale_absent():
    v = verdicts(load("p3_19_explicit_absent.json"))
    assert v["P3-R03"] == "RED" and v["P3-R05"] == "RED"


def test_r05_judged_by_rationale_when_unnamed_required_item():
    form = load("p3_19_explicit_absent.json")
    form["collection_activities"][0]["personal_information_items"][0]["design_rationale"] = "본인확인에 필요"
    v = verdicts(form)
    assert v["P3-R03"] == "RED" and v["P3-R05"] == "GREEN"


@pytest.mark.parametrize("deny,expected", [(True, "RED"), (False, "GREEN")])
def test_r06_sees_unnamed_optional_item(deny, expected):
    form = _unnamed(load("p3_20_explicit_absent.json"), 1)
    form["collection_activities"][0]["denies_service_on_optional_refusal"] = deny
    assert verdicts(form)["P3-R06"] == expected


def test_r06_required_only_stays_not_applicable():
    form = load("p3_20_explicit_absent.json")
    form["collection_activities"][0]["personal_information_items"][1]["is_required"] = True
    assert verdicts(form)["P3-R06"] == "N/A"


def _verdicts_from_facts(form, mutate):
    facts = build_poc3_facts(form)
    mutate(facts)
    mapped = OntologyMapper(form["analysis_id"], controller_id="QA", controller_name="QA").map(facts)
    return {r.rule_id: r.status.value for r in P0RuleEngine().evaluate_mapping_result(mapped, poc="PoC3")}


def test_f3_05_fully_missing_unknown_and_activity_absent_keep_contract_meaning():
    form = load("p3_20_explicit_absent.json")
    # neutralize the unrelated required-rationale absence so only F3-05 varies
    form["collection_activities"][0]["personal_information_items"][0]["design_rationale"] = "로그인에 필요"
    # envelope missing -> YELLOW for R03 and R05
    v = _verdicts_from_facts(form, lambda fs: fs.__setitem__(slice(None), [f for f in fs if not f["fact_id"].startswith("F3-05")]))
    assert v["P3-R03"] == "YELLOW" and v["P3-R05"] == "YELLOW"

    def to_state(state):
        def m(fs):
            for f in fs:
                if f["fact_id"].startswith("F3-05"):
                    f["value_state"] = state
                    f["value"] = None
        return m
    v = _verdicts_from_facts(form, to_state("unknown"))
    assert v["P3-R03"] == "YELLOW" and v["P3-R05"] == "YELLOW"
    # activity-level absent (not tied to an item) still reaches R05
    v = _verdicts_from_facts(form, to_state("absent"))
    assert v["P3-R03"] == "RED" and v["P3-R05"] == "RED"


def test_no_entrusted_processing_is_not_applicable():
    form = load("p3_20_explicit_absent.json")
    form["entrusted_processings"] = []
    # presence metadata is service-level; exercise the real service path
    from app.services.compliance import run_design_check
    res = {r.rule_id: r.status.value for r in run_design_check(form)}
    assert res["P3-R11"] == "N/A"


def test_entrusted_both_absent_is_red_via_service():
    from app.services.compliance import run_design_check
    form = load("p3_19_explicit_absent.json")
    res = {r.rule_id: r.status.value for r in run_design_check(form)}
    assert res["P3-R11"] == "RED"


def test_unknown_and_missing_envelope_stay_yellow():
    form = load("p3_20_explicit_absent.json")
    form["collection_activities"][0]["denies_service_on_optional_refusal"] = None
    assert verdicts(form)["P3-R06"] == "YELLOW"
    form = load("p3_20_explicit_absent.json")
    form["collection_activities"][0]["retention"]["destruction_method"] = ""
    assert verdicts(form)["P3-R08"] == "YELLOW"


def test_optional_item_absent_rationale_is_preserved_as_fact_but_not_red():
    form = load("p3_20_explicit_absent.json")
    items = form["collection_activities"][0]["personal_information_items"]
    items[0]["design_rationale"] = "이메일 로그인에 필요"
    items[1]["design_rationale"] = copy.deepcopy(ABSENT)
    facts = build_poc3_facts(form)
    kept = [f for f in facts if f["fact_id"].startswith("F3-08") and f["value_state"] == "absent"]
    assert len(kept) == 1 and kept[0]["evidence"][0]["field_path"].endswith("[1].design_rationale")
    assert verdicts(form)["P3-R05"] == "GREEN"


def _r11_instances(form):
    from app.services.compliance import run_design_check
    r = next(r for r in run_design_check(form) if r.rule_id == "P3-R11")
    return r


def test_r11_both_absent_is_judged_on_the_real_instance():
    from app.rules.engine import P0RuleEngine as E  # noqa: F401
    form = load("p3_19_explicit_absent.json")
    facts = build_poc3_facts(form)
    mapped = OntologyMapper(form["analysis_id"], controller_id="QA", controller_name="QA").map(facts)
    eng = P0RuleEngine()
    r = next(r for r in eng.evaluate_mapping_result(mapped, poc="PoC3") if r.rule_id == "P3-R11")
    assert r.status.value == "RED"
    assert "ENT-P3-19-1" in " ".join(r.missing_facts)
    assert "__document__" not in str(r.evidence) and not r.uncertain_facts


def test_r11_instances_are_independent():
    form = load("p3_19_explicit_absent.json")
    form["entrusted_processings"].append(
        {"activity_id": "ENT-OK", "processor": "정상수탁자", "task": "정상업무"}
    )
    facts = build_poc3_facts(form)
    mapped = OntologyMapper(form["analysis_id"], controller_id="QA", controller_name="QA").map(facts)
    r = next(r for r in P0RuleEngine().evaluate_mapping_result(mapped, poc="PoC3") if r.rule_id == "P3-R11")
    assert r.status.value == "RED"
    assert any("ENT-OK" in m for m in r.matched_facts) and not any("ENT-OK" in m for m in r.missing_facts)
    form["entrusted_processings"] = [form["entrusted_processings"][1]]
    assert verdicts(form)["P3-R11"] == "GREEN"
