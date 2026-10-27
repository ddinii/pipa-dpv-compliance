"""두 Freeze 명세와의 정합성을 코드로 고정한다.

  - PIPA Compliance PoC 요구사항·기능 명세서 v1.0
  - PIPA Fact Dictionary v1.0 (Freeze)

명세는 문서라서 코드가 조용히 멀어지기 쉽다. 여기서 깨지면 둘 중 하나다.
명세를 어겼거나, 명세가 개정되었거나 (§14-6: 개정 시 버전을 함께 갱신한다).
"""

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.api.compliance import ComplianceResponse, RuleResultResponse
from app.main import app
from app.mapping import fact_schema
from app.mapping.mapping_registry import FACT_SPECS
from app.rules.engine import P0RuleEngine
from app.rules.metadata import load_rule_profile

ROOT = Path(__file__).resolve().parents[1]

# --- Fact Dictionary 3·4·5장 ---------------------------------------------
FACT_IDS = (
    [f"F1-{n:02d}" for n in range(1, 13)]      # 3장 처리방침
    + [f"F2-{n:02d}" for n in range(1, 11)]    # 4장 사고/통지
    + [f"F3-{n:02d}" for n in range(1, 14)]    # 5장 Privacy-by-Design
)

# --- Fact Dictionary 7장 Rule <-> Fact Coverage ---------------------------
COVERAGE = {
    "P1-R01": {"F1-01", "F1-02"},
    "P1-R02": {"F1-03", "F1-04"},
    "P1-R03": {"F1-05", "F1-06", "F1-07"},
    "P1-R04": {"F1-08"},
    "P1-R06": {"F1-09", "F1-10"},
    "P1-R07": {"F1-11", "F1-12"},
    "P2-R01": {"F2-01", "F2-02", "F2-03"},
    "P2-R02": {"F2-02", "F2-04"},
    "P2-R03": {"F2-08", "F2-09"},
    "P2-R08": {"F2-01", "F2-10"},
    "P2-R09": {"F2-05", "F2-08"},
    "P3-R01": {"F3-01", "F3-02"},
    "P3-R02": {"F3-02", "F3-03", "F3-04"},
    "P3-R03": {"F3-02", "F3-03", "F3-05"},
    "P3-R04": {"F3-02", "F3-03", "F3-06"},
    "P3-R05": {"F3-05", "F3-07", "F3-08"},
    "P3-R06": {"F3-07", "F3-09"},
    "P3-R08": {"F3-10", "F3-11"},
    "P3-R11": {"F3-12", "F3-13"},
}

# --- 기능명세서 8장 RuleResult 필수 필드 ----------------------------------
RULE_RESULT_FIELDS = {
    "rule_id", "rule_version", "status", "applicability",
    "matched_facts", "missing_facts", "uncertain_facts",
    "evidence", "legal_basis", "reason", "recommendation",
    "source_document_id", "evaluated_at",
}

# --- 기능명세서 9.1 공통 API 응답 -----------------------------------------
ENVELOPE_FIELDS = {
    "analysis_id", "poc", "ontology_version", "rule_version",
    "fact_schema_version", "results",
}

# --- 기능명세서 9장 최소 Compliance API ------------------------------------
ENDPOINTS = {
    "API-001": ("/api/v1/compliance/policy-check", "examples/poc1_synthetic_policy_fixture.json", "PoC1", 6),
    "API-002": ("/api/v1/compliance/breach-check", "examples/poc2_synthetic_breach_fixture.json", "PoC2", 5),
    "API-003": ("/api/v1/compliance/design-check", "examples/SC-D01_form.json", "PoC3", 8),
}


@pytest.fixture(scope="module")
def client() -> TestClient:
    return TestClient(app)


def payload(name: str) -> dict:
    return json.loads((ROOT / name).read_text(encoding="utf-8"))


# --- Fact Dictionary -----------------------------------------------------


def test_registry_holds_exactly_the_thirty_five_frozen_facts():
    """3·4·5장이 정의하는 Fact는 12+10+13 = 35개다. 늘리지도 줄이지도 않는다."""
    assert sorted(FACT_SPECS) == sorted(FACT_IDS)


def test_envelope_required_fields_match_chapter_two():
    assert set(fact_schema.REQUIRED_FIELDS) == {
        "fact_id", "subject_id", "activity_id", "ontology_class", "ontology_property",
        "value", "value_state", "source_type", "evidence", "schema_version",
    }
    assert set(fact_schema.VALUE_STATES) == {"confirmed", "unknown", "absent"}
    assert set(fact_schema.SOURCE_TYPES) == {
        "policy_text", "incident_record", "notification_notice", "structured_form", "derived",
    }
    assert fact_schema.FACT_SCHEMA_VERSION == "fact-1.0"


@pytest.mark.parametrize("rule_id", sorted(COVERAGE))
def test_rule_fact_coverage_matches_chapter_seven(rule_id: str):
    profile = load_rule_profile()
    rule = next(item for item in profile["rules"] if item["rule_id"] == rule_id)
    assert set(rule.get("required_fact_ids", [])) == COVERAGE[rule_id]


@pytest.mark.parametrize("fact_id", ["F1-10", "F2-08", "F3-13"])
def test_system_metadata_is_never_an_ontology_property(fact_id: str):
    """8장·9장: notice_incident_time / measure_role / entrusted_task_text는
    Rule 입력 보조 필드이며 Ontology Property가 아니다."""
    assert FACT_SPECS[fact_id].ontology_property is None


# --- 기능명세서 ----------------------------------------------------------


def test_rule_set_loader_splits_six_five_eight():
    """COM-005: PoC에 따라 P01 6개 / P02 5개 / D01 8개를 로드한다."""
    engine = P0RuleEngine()
    counts = {
        poc: len([r for r, m in engine.metadata.items() if m.poc.lower() == poc])
        for poc in ("poc1", "poc2", "poc3")
    }
    assert counts == {"poc1": 6, "poc2": 5, "poc3": 8}


def test_response_model_matches_the_nine_one_envelope():
    assert ENVELOPE_FIELDS <= set(ComplianceResponse.model_fields)


def test_rule_result_model_carries_the_chapter_eight_fields():
    assert RULE_RESULT_FIELDS <= set(RuleResultResponse.model_fields)


@pytest.mark.parametrize("api_id", sorted(ENDPOINTS))
def test_minimum_compliance_api_returns_the_frozen_contract(client: TestClient, api_id: str):
    """9장 API-001/002/003이 9.1 봉투와 8장 RuleResult를 돌려준다."""
    path, fixture, poc, rule_count = ENDPOINTS[api_id]
    body = client.post(path, json=payload(fixture)).json()

    assert ENVELOPE_FIELDS <= set(body), api_id
    assert body["poc"] == poc
    assert len(body["results"]) == rule_count

    profile = load_rule_profile()
    assert body["ontology_version"] == profile["ontology_version"]
    assert body["rule_version"] == profile["rule_version"]
    assert body["fact_schema_version"] == profile["fact_schema_version"]

    for result in body["results"]:
        assert RULE_RESULT_FIELDS <= set(result), (api_id, result["rule_id"])
        # NFR-04 · TST-010: 입력 추적 ID가 결과마다 남는다
        assert result["source_document_id"] == body["analysis_id"]
        # COM-007: 상태는 네 가지 중 하나
        assert result["status"] in {"GREEN", "YELLOW", "RED", "N/A"}
        # COM-009: 법적 근거가 비어 있지 않다
        assert result["legal_basis"], result["rule_id"]
        # COM-008 · TST-004: G/A/R 판정에는 근거가 있어야 한다
        if result["status"] != "N/A":
            assert result["evidence"], result["rule_id"]


@pytest.mark.parametrize("api_id", sorted(ENDPOINTS))
def test_same_input_gives_the_same_result(client: TestClient, api_id: str):
    """NFR-03 · TST-008: 동일 입력은 동일 status/reason을 낸다."""
    path, fixture, _, _ = ENDPOINTS[api_id]
    key = lambda body: {  # noqa: E731
        r["rule_id"]: (r["status"], r["reason"], r["matched_facts"]) for r in body["results"]
    }
    first = client.post(path, json=payload(fixture)).json()
    second = client.post(path, json=payload(fixture)).json()
    assert key(first) == key(second)


# --- 미충족 사항 (TST-003) ------------------------------------------------


def test_na_is_reachable_but_our_fixtures_do_not_exercise_it(client: TestClient):
    """N/A는 이제 Fact 경로로 나온다. 다만 이 fixture 3종은 그 경로를 타지 않는다.

    O_Jeon이 activity presence metadata로 구현했다
    (app/mapping/presence_metadata.py · docs/N_A_PRESENCE_CHANGESET_20260927.md).
    Fact가 아니라 system_metadata로 실어 보내므로 Fact Dictionary 3·4·5장의
    35개와 1장의 "Ontology v1.0에 없는 개념을 P0 Fact로 만들지 않는다"를
    둘 다 지킨다. tests/test_activity_presence_pipeline.py가 P1-R03/R06,
    P2-R02/R03, P3-R11의 N/A를 전체 경로로 재현한다.

    여기 fixture 3종은 presence metadata를 싣지 않아 N/A가 나오지 않는다.
    TST-003을 이 세 endpoint로 만족시키려면 fixture를 늘려야 한다.
    """
    seen = set()
    for path, fixture, _, _ in ENDPOINTS.values():
        body = client.post(path, json=payload(fixture)).json()
        seen.update(result["status"] for result in body["results"])

    assert {"GREEN", "YELLOW", "RED"} <= seen
    assert "N/A" not in seen


def test_the_engine_reaches_na_through_presence_metadata():
    """N/A 경로가 살아 있는지 직접 확인한다 (COM-006 · COM-007 · TST-003).

    위 테스트가 "우리 fixture는 N/A를 안 낸다"만 말하므로, 시스템 전체에
    N/A 경로가 있다는 사실을 여기서 따로 고정한다.
    """
    from app.mapping.presence_metadata import (
        ACTIVITY_PRESENCE_STATES,
        activity_presence_metadata,
    )

    assert "confirmed_false" in ACTIVITY_PRESENCE_STATES
    item = activity_presence_metadata(
        "ThirdPartyProvision",
        "confirmed_false",
        source_type="policy_text",
        evidence=[
            {"text": "제3자에게 제공하지 않습니다", "start_offset": 0, "end_offset": 18}
        ],
    )
    assert item["field"] == "activity_presence"
    assert item["state"] == "confirmed_false"
