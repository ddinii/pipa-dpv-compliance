"""Fact -> RDF 변환 헬퍼.

매핑 정본은 app.mapping.OntologyMapper다. 평가·테스트 계층은 analysis_id와
controller_id를 매번 정할 이유가 없어 이 얇은 헬퍼를 쓴다.

Rule 판정에는 facts_to_mapping()을 쓰고 결과를 P0RuleEngine.evaluate_mapping_result에
넘긴다. 매퍼는 confirmed만 RDF로 내므로, 그래프만 넘기면 엔진이 unknown과 absent를
구별하지 못한다 (docs/RULE_ENGINE_FACT_DICTIONARY_ALIGNMENT_20260923.md).
facts_to_graph()는 그래프 구조만 보는 곳에 남겨둔다.
"""

from __future__ import annotations

from typing import Any, Iterable

from rdflib import Graph

from app.mapping import OntologyMapper
from app.mapping.ontology_mapper import MappingResult

DEFAULT_CONTROLLER_ID = "ctrl-001"


# Fact Dictionary 2장 공통 Envelope. _note 같은 비계약 필드는 매핑 정본이 모른다.
CONTRACT_FIELDS = {
    "fact_id", "subject_id", "activity_id", "ontology_class", "ontology_property",
    "value", "value_state", "source_type", "evidence", "schema_version",
}


def _contract_payload(facts: Iterable[Any]) -> list[dict]:
    payload = [
        item if isinstance(item, dict) else item.model_dump(by_alias=True, exclude_none=False)
        for item in facts
    ]
    return [{k: v for k, v in item.items() if k in CONTRACT_FIELDS} for item in payload]


def facts_to_mapping(
    facts: Iterable[Any],
    *,
    analysis_id: str = "analysis",
    controller_id: str = DEFAULT_CONTROLLER_ID,
    controller_name: str | None = None,
) -> MappingResult:
    """Fact 목록(dict 또는 FactEnvelope)을 매핑 결과로 바꾼다.

    그래프와 정규화된 Fact를 함께 들고 있어야 Rule Engine이 unknown/absent를
    유지한 채 판정할 수 있다.
    """
    return OntologyMapper(
        analysis_id, controller_id=controller_id, controller_name=controller_name
    ).map(_contract_payload(facts))


def facts_to_graph(
    facts: Iterable[Any],
    *,
    analysis_id: str = "analysis",
    controller_id: str = DEFAULT_CONTROLLER_ID,
    controller_name: str | None = None,
) -> Graph:
    """그래프 구조만 볼 때 쓴다. Rule 판정에는 facts_to_mapping()을 쓸 것."""
    return facts_to_mapping(
        facts,
        analysis_id=analysis_id,
        controller_id=controller_id,
        controller_name=controller_name,
    ).graph
