from fastapi import APIRouter

from app.models.request import ProcessingFact
from app.models.response import ValidationResponse
from app.services.rdf_mapper import processing_fact_to_graph
from app.services.result_builder import build_result
from app.services.validator import validate_graph


router = APIRouter(
    prefix="/api/v1",
    tags=["validation"],
)


@router.post(
    "/validate",
    response_model=ValidationResponse,
)
def validate_processing_fact(
    fact: ProcessingFact,
) -> ValidationResponse:

    data_graph = processing_fact_to_graph(fact)

    validation_run = validate_graph(data_graph)

    return build_result(
        fact,
        validation_run,
    )