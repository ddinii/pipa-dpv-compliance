"""Regression tests for production-path N/A applicability metadata."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from rdflib import Namespace

from app.extractors.base import ExtractionResult
from app.extractors.poc1_mock_extractor import MockPoC1Extractor
from app.mapping.fact_schema import FactValidationError
from app.mapping.ontology_mapper import OntologyMapper
from app.mapping.presence_metadata import activity_presence_metadata
from app.rules.engine import P0RuleEngine
from app.services.compliance import run_breach_check, run_design_check, run_policy_check


BASE = Path(__file__).resolve().parents[1]
EXAMPLES = BASE / "examples"
META = Namespace("https://w3id.org/pipa-compliance/metadata#")


def _policy_request() -> dict:
    return json.loads(
        (EXAMPLES / "poc1_synthetic_policy_fixture.json").read_text(encoding="utf-8")
    )


def _breach_request() -> dict:
    return json.loads(
        (EXAMPLES / "poc2_synthetic_breach_fixture.json").read_text(encoding="utf-8")
    )


def _result(results, rule_id: str):
    return next(item for item in results if item.rule_id == rule_id)


class _PoC1WithoutActivityExtractor:
    def __init__(self, activity_type: str) -> None:
        self.activity_type = activity_type

    def extract(self, **kwargs) -> ExtractionResult:
        facts = MockPoC1Extractor().extract(**kwargs)
        excluded = {
            "ThirdPartyProvision": {"F1-05", "F1-06", "F1-07"},
            "EntrustedProcessing": {"F1-09", "F1-10"},
        }[self.activity_type]
        filtered = [fact for fact in facts if fact["fact_id"][:5] not in excluded]
        metadata = activity_presence_metadata(
            self.activity_type,
            "confirmed_false",
            source_type="policy_text",
            evidence=[{"text": f"{self.activity_type} 활동이 없다고 명시됨"}],
        )
        return ExtractionResult(facts=filtered, system_metadata=[metadata])


def test_p1_r03_no_third_party_provision_reaches_na_through_full_pipeline():
    results = run_policy_check(
        _policy_request(),
        extractor=_PoC1WithoutActivityExtractor("ThirdPartyProvision"),
    )
    result = _result(results, "P1-R03")
    assert result.status.value == "N/A"
    assert result.applicability.value == "FALSE"


def test_p1_r06_no_entrusted_processing_reaches_na_through_full_pipeline():
    results = run_policy_check(
        _policy_request(),
        extractor=_PoC1WithoutActivityExtractor("EntrustedProcessing"),
    )
    result = _result(results, "P1-R06")
    assert result.status.value == "N/A"
    assert result.applicability.value == "FALSE"


def test_property_absence_is_not_activity_absence():
    facts = MockPoC1Extractor().extract(
        analysis_id="property-absence",
        controller_id="controller",
        controller_name="Controller",
        policy_text="synthetic",
    )
    for fact in facts:
        if fact["fact_id"].startswith("F1-05"):
            fact["value"] = None
            fact["value_state"] = "absent"

    mapping = OntologyMapper(
        "property-absence", controller_id="controller"
    ).map(facts)
    result = _result(
        P0RuleEngine().evaluate_mapping_result(mapping, poc="PoC1"), "P1-R03"
    )
    assert result.status.value == "RED"
    assert result.applicability.value == "TRUE"


def test_poc2_missing_notice_is_red_for_r01_and_na_for_notice_content_rules():
    request = _breach_request()
    request.pop("notification", None)
    results = run_breach_check(request)

    assert _result(results, "P2-R01").status.value == "RED"
    assert _result(results, "P2-R02").status.value == "N/A"
    assert _result(results, "P2-R03").status.value == "N/A"


def test_p3_r11_empty_entrusted_processing_reaches_na_through_full_pipeline():
    form = json.loads((EXAMPLES / "SC-D01_form.json").read_text(encoding="utf-8"))
    form["entrusted_processings"] = []
    result = _result(run_design_check(form), "P3-R11")
    assert result.status.value == "N/A"
    assert result.applicability.value == "FALSE"


def test_presence_metadata_requires_traceable_evidence():
    with pytest.raises(FactValidationError, match="evidence"):
        activity_presence_metadata(
            "EntrustedProcessing",
            "confirmed_false",
            source_type="structured_form",
            evidence=[],
        )


def test_duplicate_presence_state_for_same_activity_type_is_rejected():
    item = activity_presence_metadata(
        "NotificationNotice",
        "confirmed_false",
        source_type="derived",
        evidence=[{"field_path": "notification"}],
    )
    with pytest.raises(FactValidationError, match="중복"):
        OntologyMapper("duplicate-presence").map(
            [], system_metadata=[item, item]
        )


def test_presence_metadata_is_not_persisted_as_core_rdf_assertion():
    item = activity_presence_metadata(
        "ThirdPartyProvision",
        "confirmed_false",
        source_type="policy_text",
        evidence=[{"text": "제3자 제공을 하지 않음"}],
    )
    mapping = OntologyMapper("metadata-only").map([], system_metadata=[item])

    assert list(mapping.graph.triples((None, META.thirdPartyProvisionState, None))) == []
    assert mapping.system_metadata == [item]
