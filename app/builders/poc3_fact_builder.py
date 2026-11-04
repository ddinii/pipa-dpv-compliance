"""Build frozen P0 PoC3 Facts directly from a structured PbD form."""

from __future__ import annotations

from typing import Any

from app.mapping.legal_basis_tokens import (
    STATUS_TO_VALUE_STATE,
    is_consent_token,
    legal_basis_type_text,
)


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


def _is_absent(value: Any, path: str) -> bool:
    """True only for the exact explicit-absence marker ``{"state": "absent"}``.

    No string heuristics: sentinel text such as "미기재" stays a confirmed
    string.  A dict carrying a ``state`` key that is not exactly the marker is
    an input error, never silently treated as a value or as absent.
    """
    if isinstance(value, dict) and "state" in value:
        if value == {"state": "absent"}:
            return True
        raise Poc3FormError(
            f"잘못된 상태 객체: {path} (허용 형식은 정확히 {{\"state\": \"absent\"}})"
        )
    return False


def _is_consent_basis(legal_basis: Any) -> bool:
    """Exact Consent token (shared with the Ontology Mapper)."""
    return is_consent_token(legal_basis_type_text(legal_basis))


def _legal_basis_state(legal_basis: Any, path: str) -> str:
    """F3-02 value_state from ``legal_basis.status`` (missing key -> confirmed)."""
    if not isinstance(legal_basis, dict) or "status" not in legal_basis:
        return "confirmed"
    status = legal_basis["status"]
    if not isinstance(status, str) or status not in STATUS_TO_VALUE_STATE:
        raise Poc3FormError(
            f"지원하지 않는 legal_basis.status: {path}.status "
            f"(허용: {', '.join(STATUS_TO_VALUE_STATE)})"
        )
    return STATUS_TO_VALUE_STATE[status]


def _consent_request_state(
    activity: dict[str, Any], legal_basis: Any, legal_basis_state: str
) -> tuple[Any, str]:
    """Return (value, value_state) for F3-03.

    * field missing / null -> unknown (a planned=true default is never invented)
    * planned == false on a CONFIRMED consent basis -> absent (explicit "not
      designed"); with an unknown legal basis it stays confirmed so the
      unknown F3-02 yields YELLOW instead of RED
    * anything else -> confirmed, unchanged (including non-consent bases, so
      the consent Rules stay N/A for them)
    """
    consent_request = activity.get("consent_request")
    if consent_request is None:
        return None, "unknown"
    if (
        isinstance(consent_request, dict)
        and consent_request.get("planned") is False
        and legal_basis_state == "confirmed"
        and _is_consent_basis(legal_basis)
    ):
        return None, "absent"
    return consent_request, "confirmed"


def _retention_fact_value(retention: dict[str, Any], base: str) -> dict[str, Any]:
    """F3-06 value.  An absent end_condition marker is replaced by None so it
    never reaches the Mapper; every other key is passed through unchanged."""
    if _is_absent(retention.get("end_condition"), f"{base}.retention.end_condition"):
        return {**retention, "end_condition": None}
    return retention


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
        legal_basis_state = _legal_basis_state(legal_basis, f"{base}.legal_basis")
        consent_value, consent_state = _consent_request_state(
            activity, legal_basis, legal_basis_state
        )
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

        item_path_of = lambda i: f"{base}.personal_information_items[{i}]"  # noqa: E731
        # Explicitly absent item names are kept out of the aggregate F3-05 value
        # (so named items keep their information) and are recorded as separate
        # F3-05 absent Facts whose evidence points at the missing item.
        absent_name_indexes = [
            i for i, item in enumerate(items)
            if _is_absent(
                _required(item, "item_name", item_path_of(i)),
                f"{item_path_of(i)}.item_name",
            )
        ]
        named_items = [
            _required(item, "item_name", item_path_of(i))
            for i, item in enumerate(items)
            if i not in absent_name_indexes
        ]
        f3_05_facts: list[dict[str, Any]] = []
        if named_items:
            f3_05_facts.append(
                _fact(
                    next_id("F3-05"),
                    subject_id=activity_id,
                    activity_id=activity_id,
                    ontology_class="CollectionAndUse",
                    ontology_property="hasPersonalInformation",
                    value=named_items,
                    field_path=f"{base}.personal_information_items",
                )
            )
        for missing_index in absent_name_indexes:
            f3_05_facts.append(
                _fact(
                    next_id("F3-05"),
                    # item-level absence: reuse the existing item subject_id
                    subject_id=f"{activity_id}-item-{missing_index + 1}",
                    activity_id=activity_id,
                    ontology_class="CollectionAndUse",
                    ontology_property="hasPersonalInformation",
                    value=None,
                    value_state="absent",
                    field_path=f"{item_path_of(missing_index)}.item_name",
                )
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
                    value=legal_basis if legal_basis_state == "confirmed" else None,
                    value_state=legal_basis_state,
                    field_path=f"{base}.legal_basis",
                ),
                _fact(
                    next_id("F3-03"),
                    subject_id=activity_id,
                    activity_id=activity_id,
                    ontology_class="CollectionAndUse",
                    ontology_property="hasConsentRequest",
                    value=consent_value,
                    value_state=consent_state,
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
                *f3_05_facts,
                _fact(
                    next_id("F3-06"),
                    subject_id=activity_id,
                    activity_id=activity_id,
                    ontology_class="CollectionAndUse",
                    ontology_property="hasRetention",
                    value=_retention_fact_value(retention, base),
                    field_path=f"{base}.retention",
                ),
            ]
        )
        for item_index, item in enumerate(items):
            item_path = f"{base}.personal_information_items[{item_index}]"
            # An explicitly absent name keeps the item addressable by its
            # existing subject_id; F3-07/F3-08 then carry item_name=None.
            name_absent = item_index in absent_name_indexes
            item_name = None if name_absent else str(_required(item, "item_name", item_path))
            required = _required(item, "is_required", item_path)
            rationale = _required(item, "design_rationale", item_path)
            if not isinstance(required, bool):
                raise Poc3FormError(f"{item_path}.is_required는 boolean이어야 함")
            rationale_absent = _is_absent(rationale, f"{item_path}.design_rationale")
            # Optional-item absence is preserved as an absent F3-08 Fact; the
            # engine scopes it per item (P3-R05 evaluates required items only).
            facts.append(
                _fact(
                    next_id("F3-07"),
                    subject_id=f"{activity_id}-item-{item_index + 1}",
                    activity_id=activity_id,
                    ontology_class="PersonalInformation",
                    ontology_property="isRequired",
                    value={"item_name": item_name, "is_required": required},
                    field_path=f"{item_path}.is_required",
                )
            )
            facts.append(
                _fact(
                    next_id("F3-08"),
                    subject_id=f"{activity_id}-item-{item_index + 1}",
                    activity_id=activity_id,
                    ontology_class="PersonalInformation",
                    ontology_property="designRationale",
                    value=None
                    if rationale_absent
                    else {"item_name": item_name, "design_rationale": rationale},
                    value_state="absent" if rationale_absent else "confirmed",
                    field_path=f"{item_path}.design_rationale",
                )
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
        # The explicit marker applies to this field only (F3-10).  It does not
        # imply anything about destruction_method (F3-11), nor the reverse.
        end_absent = _is_absent(end_condition, f"{base}.retention.end_condition")
        if end_condition:
            facts.append(
                _fact(
                    next_id("F3-10"),
                    subject_id=f"{activity_id}-retention",
                    activity_id=activity_id,
                    ontology_class="Retention",
                    ontology_property="hasRetentionEndCondition",
                    value=None if end_absent else end_condition,
                    value_state="absent" if end_absent else "confirmed",
                    field_path=f"{base}.retention.end_condition",
                )
            )
        if end_condition and destruction_method:
            method_absent = _is_absent(
                destruction_method, f"{base}.retention.destruction_method"
            )
            # No end condition to link a concrete method to: no F3-11 (the
            # method itself is not absent and stays in the F3-06 value).
            if not (end_absent and not method_absent):
                facts.append(
                    _fact(
                        next_id("F3-11"),
                        subject_id=f"{activity_id}-retention-end",
                        activity_id=activity_id,
                        ontology_class="RetentionEndCondition",
                        ontology_property="triggersDestruction",
                        value=None
                        if method_absent
                        else {
                            "end_condition": end_condition,
                            "destruction_method": destruction_method,
                        },
                        value_state="absent" if method_absent else "confirmed",
                        field_path=(
                            f"{base}.retention.destruction_method"
                            if method_absent
                            else f"{base}.retention"
                        ),
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
        processor_absent = _is_absent(processor, f"{base}.processor")
        task_absent = _is_absent(task, f"{base}.task")
        facts.extend(
            [
                _fact(
                    next_id("F3-12"),
                    subject_id=activity_id,
                    activity_id=activity_id,
                    ontology_class="EntrustedProcessing",
                    ontology_property="hasProcessor",
                    value=None if processor_absent else processor,
                    value_state="absent" if processor_absent else "confirmed",
                    field_path=f"{base}.processor",
                ),
                _fact(
                    next_id("F3-13"),
                    subject_id=activity_id,
                    activity_id=activity_id,
                    ontology_class="EntrustedProcessing",
                    ontology_property=None,
                    value=None if task_absent else task,
                    value_state="absent" if task_absent else "confirmed",
                    field_path=f"{base}.task",
                ),
            ]
        )

    return facts
