from typing import Any

from fastapi import APIRouter, Body, HTTPException

from app.services.compliance import ComplianceInputError, run_design_check


router = APIRouter(
    prefix="/api/v1/compliance",
    tags=["compliance"],
)


@router.post("/design-check")
def design_check(
    form: dict[str, Any] = Body(...),
) -> dict[str, Any]:
    try:
        results = run_design_check(form)
    except ComplianceInputError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return {
        "poc": "PoC3",
        "rule_results": [result.to_dict() for result in results],
    }
