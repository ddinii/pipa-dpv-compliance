from pydantic import BaseModel, ConfigDict, Field


class ProcessingFact(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        extra="forbid",
    )

    processing_type: str = Field(alias="processingType")

    personal_data: list[str] = Field(
        default_factory=list,
        alias="personalData",
    )

    purpose: str | None = None

    recipient: str | None = None

    recipient_role: str | None = Field(
        default=None,
        alias="recipientRole",
    )

    legal_basis: str = Field(alias="legalBasis")

    retention_period: str | None = Field(
        default=None,
        alias="retentionPeriod",
    )

    notice_items: list[str] = Field(
        default_factory=list,
        alias="noticeItems",
    )