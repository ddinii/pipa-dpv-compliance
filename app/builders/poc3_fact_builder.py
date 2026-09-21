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


def build_poc3_facts(form: dict[str, Any]) -> list[dict[str, Any]]:
    """Convert a PoC3 form payload into F3-01..F3-13 Fact envelopes.

    The builder intentionally does not create Facts for third-party provision
    or cross-border transfer FALSE states because those fields are not part of
    the frozen P0 Fact Dictionary. They may remain request-level scenario state.
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
        purpose = _required(activity, "purpose", base)
        legal_basis = _required(activity, "legal_basis", base)
        consent_request = activity.get("consent_request", {"planned": True})
        items = _required(activity, "personal_information_items", base)
        retention = _required(activity, "retention", base)

        if not isinstance(items, list) or not items:
            raise Poc3FormError(f"{base}.personal_information_items는 비어 있을 수 없음")
        if not isinstance(retention, dict):
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
                ),
            ]
        )

        for item_index, item in enumerate(items):
            item_path = f"{base}.personal_information_items[{item_index}]"
            item_name = str(_required(item, "item_name", item_path))
            required = _required(item, "is_required", item_path)
            rationale = _required(item, "design_rationale", item_path)
            if not isinstance(required, bool):
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

    return facts
