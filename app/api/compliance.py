"""Compliance API (기능명세서 9장).

API-003 POST /api/v1/compliance/design-check  PoC3 Privacy-by-Design 사전점검

PoC1(policy-check)과 PoC2(breach-check)는 Extractor가 붙은 뒤에 추가한다.
세 endpoint 모두 같은 ComplianceResponse 계약을 쓴다.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse

from app.facts.graph import facts_to_graph
from app.mapping.fact_schema import FactValidationError as FactMappingError
from app.facts.validator import FactValidationError, validate_facts
from app.forms.poc3 import DesignForm, build_facts
from app.models.compliance import ComplianceResponse, RuleResultOut
from app.rules.engine import P0RuleEngine
from app.rules.metadata import load_rule_profile

ROOT_DIR = Path(__file__).resolve().parents[2]
DESIGN_HTML = ROOT_DIR / "app" / "web" / "design.html"
EXAMPLE_FORM = ROOT_DIR / "evals" / "poc3" / "sc_d01_form.json"

router = APIRouter(tags=["compliance"])

_engine: P0RuleEngine | None = None


def get_engine() -> P0RuleEngine:
    global _engine
    if _engine is None:
        _engine = P0RuleEngine()
    return _engine


def _analysis_id() -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
    return f"A-{stamp}-{uuid4().hex[:8]}"


def design_form_to_facts(form: DesignForm) -> list:
    """Form -> Fact -> 검증. 검증 실패는 400으로 올린다 (COM-002)."""
    try:
        return validate_facts(build_facts(form))
    except FactValidationError as exc:
        raise HTTPException(
            status_code=400,
            detail={
                "detail": "Fact 검증에 실패했습니다. 값을 임의로 보완하지 않습니다.",
                "issues": [
                    {"index": issue.index, "fact_id": issue.fact_id, "message": issue.message}
                    for issue in exc.issues
                ],
            },
        ) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post(
    "/api/v1/compliance/design-check",
    response_model=ComplianceResponse,
    summary="API-003 PoC3 Privacy-by-Design 사전점검",
)
def design_check(form: DesignForm) -> ComplianceResponse:
    """구조화 설계 Form을 P0 PoC3 Rule 8개로 점검한다.

    LLM을 쓰지 않는다. Form -> Fact -> Ontology -> Rule 경로가 전부 결정론적이므로
    같은 Form은 항상 같은 결과를 낸다 (NFR-03).
    """
    facts = design_form_to_facts(form)

    try:
        graph = facts_to_graph(facts)
    except FactMappingError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    results = get_engine().evaluate_graph(graph, poc="poc3")
    profile = load_rule_profile()

    return ComplianceResponse(
        analysis_id=_analysis_id(),
        poc="poc3",
        ontology_version=profile["ontology_version"],
        rule_version=profile["rule_version"],
        fact_schema_version=profile["fact_schema_version"],
        source_document_id=form.scenario_id,
        results=[
            RuleResultOut(**result.to_dict(), source_document_id=form.scenario_id)
            for result in results
        ],
    )


@router.post(
    "/api/v1/dev/design-facts",
    summary="Form에서 생성된 Fact를 그대로 돌려준다 (개발용)",
)
def design_facts(form: DesignForm) -> dict:
    """Form -> Fact 변환 결과 확인용. API-003의 일부가 아니다."""
    facts = design_form_to_facts(form)
    return {
        "scenario_id": form.scenario_id,
        "fact_count": len(facts),
        "facts": [fact.model_dump(by_alias=True, exclude_none=False) for fact in facts],
    }


@router.get(
    "/api/v1/dev/design-example",
    summary="예시 설계 Form (개발/데모용)",
)
def design_example() -> dict:
    """UI가 처음 열릴 때 채워 넣을 예시. SC-D01 설계와 정합한다."""
    if not EXAMPLE_FORM.is_file():
        raise HTTPException(status_code=500, detail="예시 Form 파일을 찾을 수 없습니다.")
    return json.loads(EXAMPLE_FORM.read_text(encoding="utf-8"))


@router.get("/design", response_class=HTMLResponse, include_in_schema=False)
def design_page() -> HTMLResponse:
    if not DESIGN_HTML.is_file():
        raise HTTPException(status_code=500, detail="design.html을 찾을 수 없습니다.")
    return HTMLResponse(DESIGN_HTML.read_text(encoding="utf-8"))
