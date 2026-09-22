"""Fact Envelope DTO.

PIPA Fact Dictionary v1.0 2장 공통 Fact Envelope의 구현이다.

COM-002가 요구하는 원칙은 "검증하되 임의로 보완하지 않는다"이다. 따라서 이 모델은
누락값을 기본값으로 메우지 않고 거부한다. schema_version에도 기본값을 주지 않는다.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


from app.mapping.fact_schema import (  # noqa: E402  (정본에서 계약 상수를 가져온다)
    FACT_SCHEMA_VERSION,
    SOURCE_TYPES,
    VALUE_STATES,
)

ValueState = Literal["confirmed", "unknown", "absent"]

SourceType = Literal[
    "policy_text",
    "incident_record",
    "notification_notice",
    "structured_form",
    "derived",
]

# 타입 힌트는 정적이라 정본 상수와 어긋날 수 있다. import 시점에 한 번 맞춰 본다.
assert set(VALUE_STATES) == set(ValueState.__args__), "value_state enum이 정본과 다릅니다"
assert set(SOURCE_TYPES) == set(SourceType.__args__), "source_type enum이 정본과 다릅니다"


class Evidence(BaseModel):
    """근거 locator.

    LLM 입력(PoC1/PoC2)은 원문 text와 offset을, 구조화 Form(PoC3)은 field_path를 쓴다
    (Fact Dictionary 8장). 둘을 섞지 않는다.
    """

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    text: str | None = None
    start_offset: int | None = None
    end_offset: int | None = None
    field_path: str | None = None

    @model_validator(mode="after")
    def check_locator(self) -> "Evidence":
        has_text = self.text is not None
        has_path = self.field_path is not None

        if has_text == has_path:
            raise ValueError("evidence는 text 또는 field_path 중 정확히 하나를 가져야 합니다.")

        if has_text:
            if self.start_offset is None or self.end_offset is None:
                raise ValueError("text 근거에는 start_offset과 end_offset이 필요합니다.")
            if self.start_offset < 0:
                raise ValueError("start_offset은 0 이상이어야 합니다.")
            if self.end_offset - self.start_offset != len(self.text):
                raise ValueError(
                    f"offset 길이({self.end_offset - self.start_offset})가 "
                    f"text 길이({len(self.text)})와 다릅니다."
                )
        elif self.start_offset is not None or self.end_offset is not None:
            raise ValueError("field_path 근거에는 offset을 함께 쓰지 않습니다.")

        return self

    def resolves_in(self, document: str) -> bool:
        """offset이 원문에서 실제로 text를 가리키는지 확인한다."""
        if self.text is None:
            return True
        return document[self.start_offset : self.end_offset] == self.text


class FactEnvelope(BaseModel):
    """Fact Dictionary 2장 공통 Envelope."""

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    fact_id: str = Field(min_length=1)
    subject_id: str = Field(min_length=1)
    activity_id: str | None
    ontology_class: str = Field(min_length=1)
    ontology_property: str | None
    value: Any | None
    value_state: ValueState
    source_type: SourceType
    evidence: list[Evidence] = Field(min_length=1)
    schema_version: str

    # 계약 필드가 아닌 작성자 주석. 언더스코어로 구분한다.
    note: str | None = Field(default=None, alias="_note")

    @model_validator(mode="after")
    def check_value_state(self) -> "FactEnvelope":
        if self.schema_version != FACT_SCHEMA_VERSION:
            raise ValueError(
                f"schema_version은 {FACT_SCHEMA_VERSION}이어야 합니다: {self.schema_version}"
            )

        # Fact Dictionary 1장: false는 confirmed 값이며 unknown과 다르다.
        # 따라서 value가 False인 것과 값이 없는 것을 구분해야 한다.
        if self.value_state in {"unknown", "absent"} and self.value is not None:
            raise ValueError(
                f"value_state={self.value_state}인데 value가 있습니다: {self.value!r}"
            )

        # Class assertion(ontology_property=null)은 실어 나를 값이 없어 value가 null이다.
        # Property assertion이면서 confirmed면 반드시 값이 있어야 한다.
        if (
            self.value_state == "confirmed"
            and self.ontology_property is not None
            and self.value is None
        ):
            raise ValueError("confirmed property assertion에는 value가 필요합니다.")

        return self

    @property
    def fact_type(self) -> str:
        """'F1-02:act-collection-001' -> 'F1-02'.

        Fact Dictionary 2장 Envelope에는 Fact 유형을 담을 필드가 없어 fact_id에
        인코딩한다. 이 규약은 evals/README.md의 Day 0 안건 1번이다.
        """
        return self.fact_id.split(":", 1)[0]
