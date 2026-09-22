"""Fact -> RDF 변환 헬퍼.

매핑 정본은 app.mapping.OntologyMapper다. 평가·테스트 계층은 analysis_id와
controller_id를 매번 정할 이유가 없어 이 얇은 헬퍼를 쓴다.
"""

from __future__ import annotations

from typing import Any, Iterable

from rdflib import Graph

from app.mapping import OntologyMapper

DEFAULT_CONTROLLER_ID = "ctrl-001"


def facts_to_graph(
    facts: Iterable[Any],
    *,
    analysis_id: str = "analysis",
    controller_id: str = DEFAULT_CONTROLLER_ID,
    controller_name: str | None = None,
) -> Graph:
    """Fact 목록(dict 또는 FactEnvelope)을 RDF 그래프로 바꾼다."""
    payload = [
        item if isinstance(item, dict) else item.model_dump(by_alias=True, exclude_none=False)
        for item in facts
    ]
    # _note 같은 비계약 필드는 매핑 정본이 모른다. 계약 필드만 넘긴다.
    contract = {
        "fact_id", "subject_id", "activity_id", "ontology_class", "ontology_property",
        "value", "value_state", "source_type", "evidence", "schema_version",
    }
    payload = [{k: v for k, v in item.items() if k in contract} for item in payload]
    return OntologyMapper(
        analysis_id, controller_id=controller_id, controller_name=controller_name
    ).map(payload).graph
