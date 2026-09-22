"""Build frozen P0 PoC3 Facts directly from a structured PbD form."""

from __future__ import annotations

from typing import Any


class Poc3FormError(ValueError):
    """Raised when a required PoC3 form field is missing or malformed."""


def _evidence(field_path: str) -> list[dict[str, str]]:
    return [{"field_path": field_path}]


def _fact(
    fact_id: str,
    *,
    subject_id: str,
    activity_id: str | None,
    ontology_class: str,
    ontology_property: str | None,
    value: Any,
    field_path: str,
    value_state: str = "confirmed",
) -> dict[str, Any]:
    return {
        "fact_id": fact_id,
        "subject_id": subject_id,
        "activity_id": activity_id,
        "ontology_class": ontology_class,
        "ontology_property": ontology_property,
        "value": value,
        "value_state": value_state,
        "source_type": "structured_form",
        "evidence": _evidence(field_path),
        "schema_version": "fact-1.0",
    }


def _required(obj: dict[str, Any], key: str, path: str) -> Any:
    if key not in obj or obj[key] in (None, ""):
        raise Poc3FormError(f"필수 Form 필드 누락: {path}.{key}")
    return obj[key]


def _optional(obj: dict[str, Any], key: str) -> tuple[Any, str]:
    """설계단계에서 아직 정하지 않은 값을 unknown Fact로 표현한다.

    PoC3는 설계 사전점검이므로 "아직 안 정함"이 정상 상태다. 이를 오류로 막으면
    Rule Matrix의 AMBER 분기에 도달할 수 없고, 점검 도구로서 쓸모가 없어진다.
    반대로 값이 없다고 해서 결측(RED)으로 단정해서도 안 된다.
    """
    value = obj.get(key)
    if value in (None, ""):
        return None, "unknown"
    return value, "confirmed"


def build_poc3_facts(form: dict[str, Any]) -> list[dict[str, Any]]:
    """Convert a PoC3 form payload into F3-01..F3-13 Fact envelopes.

    처리행위 유형의 명시적 부재(third_party_provision_state 등)도 Fact로 만든다.
    Fact Dictionary에는 대응 ID가 없어 F3-00을 규약으로 추가했다. 이 Fact가 없으면
    Rule Engine은 단순 결측으로 보아 AMBER로 남기므로 N/A 판정이 불가능하다.
    "confirmed_false"일 때만 만들고, 값이 없거나 다른 값이면 만들지 않는다
    (미정과 부재는 다르다).
    """

    if not isinstance(form, dict):
        raise Poc3FormError("PoC3 Form은 JSON 객체여야 함")
    activities = form.get("collection_activities")
    if not isinstance(activities, list) or not activities:
        raise Poc3FormError("collection_activities는 하나 이상의 배열이어야 함")

    facts: list[dict[str, Any]] = []
    sequence: dict[str, int] = {}

    def next_id(fact_type: str) -> str:
        sequence[fact_type] = sequence.get(fact_type, 0) + 1
        return f"{fact_type}-{sequence[fact_type]:03d}"

    for activity_index, activity in enumerate(activities):
        if not isinstance(activity, dict):
            raise Poc3FormError(
                f"collection_activities[{activity_index}]는 객체여야 함"
            )
        base = f"collection_activities[{activity_index}]"
        activity_id = str(_required(activity, "activity_id", base))
        purpose, purpose_state = _optional(activity, "purpose")
        legal_basis, legal_basis_state = _optional(activity, "legal_basis")
        consent_request = activity.get("consent_request", {"planned": True})
        items = _required(activity, "personal_information_items", base)
        retention, retention_state = _optional(activity, "retention")
        if retention_state == "confirmed" and not any(
            retention.get(key) for key in ("period", "duration", "end_condition", "condition")
        ):
            # 보유 설계 칸은 있으나 안이 비어 있는 경우. 결측이 아니라 미정이다.
            retention_state = "unknown"

        if not isinstance(items, list) or not items:
            raise Poc3FormError(f"{base}.personal_information_items는 비어 있을 수 없음")
        if retention_state == "confirmed" and not isinstance(retention, dict):
            raise Poc3FormError(f"{base}.retention은 객체여야 함")
        for item_index, item in enumerate(items):
            if not isinstance(item, dict):
                raise Poc3FormError(
                    f"{base}.personal_information_items[{item_index}]는 객체여야 함"
                )

        facts.extend(
            [
                _fact(
                    next_id("F3-01"),
                    subject_id=activity_id,
                    activity_id=activity_id,
                    ontology_class="CollectionAndUse",
                    ontology_property=None,
                    value=None,
                    field_path=f"{base}.activity_id",
                ),
                _fact(
                    next_id("F3-02"),
                    subject_id=activity_id,
                    activity_id=activity_id,
                    ontology_class="CollectionAndUse",
                    ontology_property="hasLegalBasis",
                    value=legal_basis,
                    field_path=f"{base}.legal_basis",
                    value_state=legal_basis_state,
                ),
                _fact(
                    next_id("F3-03"),
                    subject_id=activity_id,
                    activity_id=activity_id,
                    ontology_class="CollectionAndUse",
                    ontology_property="hasConsentRequest",
                    value=consent_request,
                    field_path=f"{base}.consent_request",
                ),
                _fact(
                    next_id("F3-04"),
                    subject_id=activity_id,
                    activity_id=activity_id,
                    ontology_class="CollectionAndUse",
                    ontology_property="hasPurpose",
                    value=purpose,
                    field_path=f"{base}.purpose",
                    value_state=purpose_state,
                ),
                _fact(
                    next_id("F3-05"),
                    subject_id=activity_id,
                    activity_id=activity_id,
                    ontology_class="CollectionAndUse",
                    ontology_property="hasPersonalInformation",
                    value=[_required(item, "item_name", f"{base}.personal_information_items") for item in items],
                    field_path=f"{base}.personal_information_items",
                ),
                _fact(
                    next_id("F3-06"),
                    subject_id=activity_id,
                    activity_id=activity_id,
                    ontology_class="CollectionAndUse",
                    ontology_property="hasRetention",
                    value=retention,
                    field_path=f"{base}.retention",
                    value_state=retention_state,
                ),
            ]
        )

        for item_index, item in enumerate(items):
            item_path = f"{base}.personal_information_items[{item_index}]"
            item_name = str(_required(item, "item_name", item_path))
            # 항목별 필수 여부와 설계사유도 설계단계에서는 미정일 수 있다.
            # 값이 False인 것과 정하지 않은 것을 구분해야 한다 (Fact Dictionary 1장).
            required, required_state = _optional(item, "is_required")
            rationale, rationale_state = _optional(item, "design_rationale")
            if required_state == "confirmed" and not isinstance(required, bool):
                raise Poc3FormError(f"{item_path}.is_required는 boolean이어야 함")
            facts.extend(
                [
                    _fact(
                        next_id("F3-07"),
                        subject_id=f"{activity_id}-item-{item_index + 1}",
                        activity_id=activity_id,
                        ontology_class="PersonalInformation",
                        ontology_property="isRequired",
                        value={"item_name": item_name, "is_required": required},
                        field_path=f"{item_path}.is_required",
                        value_state=required_state,
                    ),
                    _fact(
                        next_id("F3-08"),
                        subject_id=f"{activity_id}-item-{item_index + 1}",
                        activity_id=activity_id,
                        ontology_class="PersonalInformation",
                        ontology_property="designRationale",
                        value={
                            "item_name": item_name,
                            "design_rationale": rationale,
                        },
                        field_path=f"{item_path}.design_rationale",
                        value_state=rationale_state,
                    ),
                ]
            )

        if "denies_service_on_optional_refusal" in activity:
            refusal = activity["denies_service_on_optional_refusal"]
            value_state = "unknown" if refusal is None else "confirmed"
            facts.append(
                _fact(
                    next_id("F3-09"),
                    subject_id=f"{activity_id}-consent-request",
                    activity_id=activity_id,
                    ontology_class="ConsentRequest",
                    ontology_property="deniesServiceOnOptionalRefusal",
                    value=refusal,
                    value_state=value_state,
                    field_path=f"{base}.denies_service_on_optional_refusal",
                )
            )

        end_condition = retention.get("end_condition")
        destruction_method = retention.get("destruction_method")
        if end_condition:
            facts.append(
                _fact(
                    next_id("F3-10"),
                    subject_id=f"{activity_id}-retention",
                    activity_id=activity_id,
                    ontology_class="Retention",
                    ontology_property="hasRetentionEndCondition",
                    value=end_condition,
                    field_path=f"{base}.retention.end_condition",
                )
            )
        if end_condition and destruction_method:
            facts.append(
                _fact(
                    next_id("F3-11"),
                    subject_id=f"{activity_id}-retention-end",
                    activity_id=activity_id,
                    ontology_class="RetentionEndCondition",
                    ontology_property="triggersDestruction",
                    value={
                        "end_condition": end_condition,
                        "destruction_method": destruction_method,
                    },
                    field_path=f"{base}.retention",
                )
            )

    entrusted = form.get("entrusted_processings", [])
    if not isinstance(entrusted, list):
        raise Poc3FormError("entrusted_processings는 배열이어야 함")
    for index, entry in enumerate(entrusted):
        if not isinstance(entry, dict):
            raise Poc3FormError(f"entrusted_processings[{index}]는 객체여야 함")
        base = f"entrusted_processings[{index}]"
        activity_id = str(_required(entry, "activity_id", base))
        processor = _required(entry, "processor", base)
        task = _required(entry, "task", base)
        facts.extend(
            [
                _fact(
                    next_id("F3-12"),
                    subject_id=activity_id,
                    activity_id=activity_id,
                    ontology_class="EntrustedProcessing",
                    ontology_property="hasProcessor",
                    value=processor,
                    field_path=f"{base}.processor",
                ),
                _fact(
                    next_id("F3-13"),
                    subject_id=activity_id,
                    activity_id=activity_id,
                    ontology_class="EntrustedProcessing",
                    ontology_property=None,
                    value=task,
                    field_path=f"{base}.task",
                ),
            ]
        )

    facts.extend(_absence_facts(form))
    return facts


# 처리행위 유형의 부재를 선언하는 Form 필드 -> Ontology Class
ABSENCE_FIELDS = {
    "third_party_provision_state": "ThirdPartyProvision",
    "cross_border_transfer_state": "CrossBorderTransfer",
    "entrusted_processing_state": "EntrustedProcessing",
}


def _absence_facts(form: dict[str, Any]) -> list[dict[str, Any]]:
    controller = form.get("controller") or {}
    controller_id = controller.get("controller_id") or "controller"
    facts: list[dict[str, Any]] = []

    for index, (field, ontology_class) in enumerate(sorted(ABSENCE_FIELDS.items()), start=1):
        if form.get(field) != "confirmed_false":
            continue
        facts.append(
            _fact(
                f"F3-00-{index:03d}",
                subject_id=controller_id,
                activity_id=None,
                ontology_class=ontology_class,
                ontology_property=None,
                value={"activity_class_absent": ontology_class},
                field_path=field,
            )
        )
    return facts
