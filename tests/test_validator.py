import json
from pathlib import Path

from app.models.request import ProcessingFact
from app.services.rdf_mapper import processing_fact_to_graph
from app.services.result_builder import build_result
from app.services.validator import validate_graph


EXAMPLES_DIR = Path(__file__).resolve().parents[1] / "examples"


def _validate_example(name: str):
    payload = json.loads(
        (EXAMPLES_DIR / name).read_text(
            encoding="utf-8"
        )
    )

    fact = ProcessingFact.model_validate(payload)

    graph = processing_fact_to_graph(fact)

    validation_run = validate_graph(graph)

    return build_result(
        fact,
        validation_run,
    )


def test_article17_pass():
    result = _validate_example(
        "article17_pass.json"
    )

    assert result.status == "PASS"

    assert result.missing_information == []

    assert result.human_review_required is False


def test_article17_missing_refusal_notice():
    result = _validate_example(
        "article17_missing.json"
    )

    assert result.status == "NEEDS_INFORMATION"

    assert (
        "동의 거부 권리 및 거부에 따른 불이익"
        in result.missing_information
    )

    assert result.human_review_required is False


def test_unimplemented_case_requires_human_review():
    result = _validate_example(
        "article17_review.json"
    )

    assert result.status == "HUMAN_REVIEW_REQUIRED"

    assert result.applied_rules == []

    assert result.human_review_required is True