"""개발용 RuleResult 점검 콘솔.

API-001/002/003(policy-check / breach-check / design-check)의 구현이 아니다.
이 라우터는 Turtle RDF를 직접 P0RuleEngine에 넣어 RuleResult를 눈으로 확인하기
위한 개발 보조 endpoint이며, Fact Extractor / Fact->RDF 매퍼가 붙기 전까지
DTO 계약을 검증하는 용도로만 쓴다.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from rdflib import Graph

from app.rules.engine import P0RuleEngine
from app.rules.metadata import load_rule_profile


ROOT_DIR = Path(__file__).resolve().parents[2]
SCENARIO_DIR = ROOT_DIR / "tests"
CONSOLE_HTML = ROOT_DIR / "app" / "web" / "console.html"

router = APIRouter(tags=["dev-console"])

_engine: P0RuleEngine | None = None


def get_engine() -> P0RuleEngine:
    global _engine
    if _engine is None:
        _engine = P0RuleEngine()
    return _engine


class EvaluateRequest(BaseModel):
    turtle: str = Field(description="Turtle 형식 RDF Fact graph")
    poc: str | None = Field(default=None, description="poc1 | poc2 | poc3, 생략 시 18개 전부")
    source_document_id: str | None = Field(default=None)


def _analysis_id() -> str:
    return "A-" + datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")


@router.get("/api/v1/dev/scenarios")
def list_scenarios() -> dict:
    """저장소에 포함된 Freeze 시나리오 TTL 목록."""
    items = []
    for path in sorted(SCENARIO_DIR.glob("SC-*.ttl")):
        items.append({"name": path.name, "size": path.stat().st_size})
    return {"scenarios": items}


@router.get("/api/v1/dev/scenarios/{name}")
def read_scenario(name: str) -> dict:
    path = SCENARIO_DIR / name
    # 경로 탈출 방지: tests/ 바로 아래의 SC-*.ttl 만 허용
    if path.parent != SCENARIO_DIR or not path.name.startswith("SC-") or path.suffix != ".ttl":
        raise HTTPException(status_code=400, detail="허용되지 않은 시나리오 이름입니다.")
    if not path.is_file():
        raise HTTPException(status_code=404, detail=f"시나리오를 찾을 수 없습니다: {name}")
    return {"name": path.name, "turtle": path.read_text(encoding="utf-8")}


@router.post("/api/v1/dev/evaluate")
def evaluate(request: EvaluateRequest) -> dict:
    """Turtle 입력을 P0 Rule Engine에 넣고 기능명세서 9.1 형태로 반환한다."""
    if request.poc is not None and request.poc.lower() not in {"poc1", "poc2", "poc3"}:
        raise HTTPException(status_code=400, detail="poc는 poc1 | poc2 | poc3 중 하나여야 합니다.")

    graph = Graph()
    try:
        graph.parse(data=request.turtle, format="turtle")
    except Exception as exc:  # rdflib은 파서별로 다른 예외를 던진다
        raise HTTPException(status_code=400, detail=f"Turtle 파싱 실패: {exc}") from exc

    results = get_engine().evaluate_graph(graph, poc=request.poc)
    profile = load_rule_profile()

    return {
        "analysis_id": _analysis_id(),
        "poc": request.poc,
        "source_document_id": request.source_document_id,
        "ontology_version": profile["ontology_version"],
        "rule_version": profile["rule_version"],
        "fact_schema_version": profile["fact_schema_version"],
        "results": [result.to_dict() for result in results],
    }


@router.get("/console", response_class=HTMLResponse)
def console() -> HTMLResponse:
    if not CONSOLE_HTML.is_file():
        raise HTTPException(status_code=500, detail="console.html을 찾을 수 없습니다.")
    return HTMLResponse(CONSOLE_HTML.read_text(encoding="utf-8"))
