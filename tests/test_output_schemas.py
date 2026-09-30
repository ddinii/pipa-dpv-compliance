"""LLM 응답 스키마가 structured outputs에 실제로 실릴 수 있는지.

스텁 테스트는 messages.parse를 가짜로 바꾸기 때문에 SDK의 스키마 변환을 거치지
않는다. 그래서 `value: Any`처럼 타입 없는 필드는 스텁에서는 통과하고 첫 실제
호출에서야 ValueError로 드러났다. 여기서 SDK와 같은 경로로 변환을 돌린다.
"""

import json
from pathlib import Path

import pytest
from anthropic.lib._parse._transform import transform_schema
from pydantic import TypeAdapter

from app.extractors.poc1 import ActivityList, ExtractedFact, FactList
from app.extractors.poc2 import ExtractedPoc2Fact, Poc2FactList

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_FORMATS = [ActivityList, FactList, Poc2FactList]


def _untyped_nodes(schema, path="$"):
    """type/anyOf/oneOf/allOf/$ref 중 아무것도 없는 스키마 노드를 찾는다."""
    if isinstance(schema, dict):
        keys = {"type", "anyOf", "oneOf", "allOf", "$ref", "const", "enum"}
        if path != "$" and not (schema.keys() & keys) and not path.endswith("$defs"):
            yield path
        for key, child in schema.items():
            if key in {"properties", "$defs"}:
                for name, sub in child.items():
                    yield from _untyped_nodes(sub, f"{path}.{key}.{name}")
            elif key in {"items", "additionalProperties"} and isinstance(child, dict):
                yield from _untyped_nodes(child, f"{path}.{key}")
            elif key in {"anyOf", "oneOf", "allOf"}:
                for i, sub in enumerate(child):
                    yield from _untyped_nodes(sub, f"{path}.{key}[{i}]")


@pytest.mark.parametrize("output_format", OUTPUT_FORMATS, ids=lambda t: t.__name__)
def test_output_format_survives_the_sdk_schema_transform(output_format):
    """messages.parse가 요청 전에 하는 변환과 같다. 여기서 실패하면 실제 호출도 실패한다."""
    schema = TypeAdapter(output_format).json_schema()
    assert list(_untyped_nodes(schema)) == []
    transform_schema(schema)


@pytest.mark.parametrize(
    ("model", "valid", "numbered"),
    [(ExtractedFact, "F1-12", "F1-12-1"), (ExtractedPoc2Fact, "F2-10", "F2-10-1")],
)
def test_fact_id_is_an_enum_of_the_frozen_ids(model, valid: str, numbered: str):
    """실측: 모델이 권리 pass에서 fact_id를 "F1-12-1", "F1-12-2"로 냈다.

    F1-12로 인식되지 않아 subject class가 틀리고 매퍼가 그 문서의 Fact 전체를
    거부했다 (held-out h1, Rule 6개 결과 소실). 스키마 enum이면 API가 이런 값을
    낼 수 없다.
    """
    from pydantic import ValidationError

    schema = TypeAdapter(model).json_schema()
    enum = schema["properties"]["fact_id"]["enum"]
    assert valid in enum and numbered not in enum
    base = {"ontology_property": None, "value": None, "value_state": "absent",
            "evidence_text": ["x"]}
    if model is ExtractedFact:
        base["activity_id"] = None
    model.model_validate({**base, "fact_id": valid})
    with pytest.raises(ValidationError):
        model.model_validate({**base, "fact_id": numbered})


def _gold_facts(poc: str) -> list[dict]:
    facts = []
    for path in (ROOT / "evals" / poc).rglob("*gold_facts*.json"):
        data = json.loads(path.read_text(encoding="utf-8"))
        facts.extend(data["facts"] if isinstance(data, dict) else data)
    return facts


@pytest.mark.parametrize(
    ("poc", "model"),
    [("poc1", ExtractedFact), ("poc2", ExtractedPoc2Fact)],
)
def test_every_gold_value_shape_round_trips(poc: str, model):
    """정답지에 있는 모든 값 형태를 스키마가 받고, Extractor가 같은 모양으로 돌려준다."""
    facts = _gold_facts(poc)
    assert facts
    for item in facts:
        parsed = model.model_validate(
            {**item, "fact_id": item["fact_id"].split(":")[0], "evidence_text": []}
        )
        assert parsed.model_dump()["value"] == item["value"], item["fact_id"]
