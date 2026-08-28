from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


ValidationStatus = Literal[
    "PASS",
    "FAIL",
    "NEEDS_INFORMATION",
    "HUMAN_REVIEW_REQUIRED",
]


class AppliedRule(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
    )

    rule_id: str = Field(alias="ruleId")
    legal_basis: str = Field(alias="legalBasis")


class ValidationResponse(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
    )

    status: ValidationStatus

    applied_rules: list[AppliedRule] = Field(
        alias="appliedRules",
    )

    missing_information: list[str] = Field(
        alias="missingInformation",
    )

    human_review_required: bool = Field(
        alias="humanReviewRequired",
    )