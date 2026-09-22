"""PoC3 Privacy-by-Design 입력 Form (D01-001 ~ D01-006).

Form -> Fact 변환 자체는 app.builders.build_poc3_facts가 정본이다. 이 모듈은 그 위에
API/UI용 **타입이 붙은 입력 계약**만 얹는다.

  - 모르는 필드를 조용히 무시하지 않고 거부한다 (COM-002)
  - None / False / 값 있음을 구분한다. false는 confirmed 값이며 미정과 다르다
    (Fact Dictionary 1장)
  - 항목별 is_required / design_rationale을 같은 design_item에 묶는다 (6장)

to_builder_form()이 이 Form을 정본 Builder가 받는 dict 형태로 바꾼다.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.builders import build_poc3_facts

CONFIRMED_FALSE = "confirmed_false"


class FormModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")


class DesignItem(FormModel):
    """개인정보 항목 하나의 설계 (D01-003).

    is_required와 design_rationale이 여기 함께 있어야 P3-R05/R06이 항목을 특정할 수 있다.
    None은 "아직 정하지 않음"(unknown)이며 False와 다르다.
    """

    item_name: str = Field(min_length=1)
    is_required: bool | None = None
    design_rationale: str | None = None


class RetentionDesign(FormModel):
    """보유·파기 설계 (D01-005)."""

    period: str | None = None
    end_condition: str | None = None
    destruction_method: str | None = None


class ConsentDesign(FormModel):
    """동의요청 설계 (D01-004)."""

    denies_service_on_optional_refusal: bool | None = None


class CollectionActivityDesign(FormModel):
    """수집·이용 처리행위 설계 (D01-001 / D01-002)."""

    activity_id: str = Field(min_length=1)
    label: str = ""
    legal_basis: str | None = None  # Ontology LegalBasis 하위 클래스명 (예: Consent)
    purpose: str | None = None
    design_items: list[DesignItem] = Field(default_factory=list)
    retention: RetentionDesign = Field(default_factory=RetentionDesign)
    consent: ConsentDesign | None = None


class EntrustmentDesign(FormModel):
    """처리위탁 설계 (D01-006)."""

    activity_id: str = Field(min_length=1)
    processor_name: str | None = None
    task: str | None = None


class DesignForm(FormModel):
    scenario_id: str = Field(min_length=1)
    controller_id: str = "ctrl-001"
    controller_name: str = ""
    collection_activities: list[CollectionActivityDesign] = Field(default_factory=list)
    entrustments: list[EntrustmentDesign] = Field(default_factory=list)
    # 처리행위 유형별 존재 여부 (D01-006 "위탁 여부가 TRUE일 때 …").
    # None = 아직 정하지 않음(AMBER), False = 없음이 확인됨(N/A), True = 있음.
    # 목록이 비어 있는 것과 "없음이 확인됨"은 다르다. 전자는 AMBER, 후자만 N/A다.
    entrustment: bool | None = None
    third_party_provision: bool | None = None
    cross_border_transfer: bool | None = None

    def to_builder_form(self) -> dict[str, Any]:
        """정본 Fact Builder가 받는 dict 형태로 바꾼다."""
        if self.entrustment is False and self.entrustments:
            raise ValueError(
                "entrustment=False(위탁 없음 확인)인데 entrustments 목록이 비어 있지 않습니다."
            )

        form: dict[str, Any] = {
            "analysis_id": self.scenario_id,
            "controller": {
                "controller_id": self.controller_id,
                "name": self.controller_name or self.controller_id,
            },
            "collection_activities": [
                _collection_to_builder(activity) for activity in self.collection_activities
            ],
            "entrusted_processings": [
                {
                    "activity_id": entry.activity_id,
                    "processor": entry.processor_name,
                    "task": entry.task,
                }
                for entry in self.entrustments
            ],
        }

        # 명시적 부재만 싣는다. True나 None이면 아무것도 싣지 않는다.
        for field, flag in (
            ("entrusted_processing_state", self.entrustment),
            ("third_party_provision_state", self.third_party_provision),
            ("cross_border_transfer_state", self.cross_border_transfer),
        ):
            if flag is False:
                form[field] = CONFIRMED_FALSE

        return form


def _collection_to_builder(activity: CollectionActivityDesign) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "activity_id": activity.activity_id,
        "purpose": activity.purpose,
        "personal_information_items": [
            {
                "item_name": item.item_name,
                "is_required": item.is_required,
                "design_rationale": item.design_rationale,
            }
            for item in activity.design_items
        ],
        "retention": {
            "period": activity.retention.period,
            "end_condition": activity.retention.end_condition,
            "destruction_method": activity.retention.destruction_method,
        },
    }
    if activity.legal_basis:
        payload["legal_basis"] = {"type": activity.legal_basis}
    if activity.consent is not None:
        payload["consent_request"] = {"planned": True}
        payload["denies_service_on_optional_refusal"] = (
            activity.consent.denies_service_on_optional_refusal
        )
    return payload


def build_facts(form: DesignForm) -> list[dict[str, Any]]:
    """타입이 붙은 Form에서 Fact를 만든다 (D01-007).

    변환 자체는 app.builders.build_poc3_facts가 한다. LLM을 쓰지 않으므로 환각이 없고
    값은 Form이 가진 것만 나온다.
    """
    return build_poc3_facts(form.to_builder_form())
