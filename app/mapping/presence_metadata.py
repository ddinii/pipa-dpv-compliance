"""Validation helpers for rule-applicability presence metadata.

Activity presence is deliberately separate from frozen Fact ``value_state``.
For example, an absent F1-05 means that a recipient value is absent from an
existing ThirdPartyProvision, while ``ThirdPartyProvision=confirmed_false``
means that the activity itself is explicitly declared not to exist.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from copy import deepcopy
from typing import Any

from .fact_schema import FactValidationError, SOURCE_TYPES


ACTIVITY_PRESENCE_FIELD = "activity_presence"
ACTIVITY_PRESENCE_STATES = {"confirmed_true", "confirmed_false", "unknown"}
ACTIVITY_PRESENCE_TYPES = {
    "ThirdPartyProvision",
    "EntrustedProcessing",
    "NotificationNotice",
}


def activity_presence_metadata(
    activity_type: str,
    state: str,
    *,
    source_type: str,
    evidence: list[dict[str, Any]],
) -> dict[str, Any]:
    item = {
        "field": ACTIVITY_PRESENCE_FIELD,
        "activity_type": activity_type,
        "state": state,
        "source_type": source_type,
        "evidence": evidence,
    }
    return validate_activity_presence_metadata(item)


def validate_activity_presence_metadata(raw: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(raw, Mapping):
        raise FactValidationError("activity presence metadata는 객체여야 함")

    item = deepcopy(dict(raw))
    if item.get("field") != ACTIVITY_PRESENCE_FIELD:
        raise FactValidationError("activity presence metadata field가 올바르지 않음")
    if item.get("activity_type") not in ACTIVITY_PRESENCE_TYPES:
        raise FactValidationError(
            f"activity_type은 {sorted(ACTIVITY_PRESENCE_TYPES)} 중 하나여야 함"
        )
    if item.get("state") not in ACTIVITY_PRESENCE_STATES:
        raise FactValidationError(
            f"activity presence state는 {sorted(ACTIVITY_PRESENCE_STATES)} 중 하나여야 함"
        )
    if item.get("source_type") not in SOURCE_TYPES:
        raise FactValidationError(
            f"activity presence source_type은 {sorted(SOURCE_TYPES)} 중 하나여야 함"
        )

    evidence = item.get("evidence")
    if not isinstance(evidence, list) or not evidence:
        raise FactValidationError("activity presence evidence는 하나 이상이어야 함")
    for index, evidence_item in enumerate(evidence):
        if not isinstance(evidence_item, Mapping):
            raise FactValidationError(
                f"activity presence evidence[{index}]는 객체여야 함"
            )
        if not any(key in evidence_item for key in ("text", "field_path", "offset")):
            raise FactValidationError(
                "activity presence evidence에는 text, field_path 또는 offset이 필요함"
            )
    return item


def validate_system_metadata(
    items: Iterable[Mapping[str, Any]] | None,
) -> list[dict[str, Any]]:
    """Validate externally supplied metadata before mapper metadata is added."""

    if items is None:
        return []
    validated = [validate_activity_presence_metadata(item) for item in items]
    activity_types = [item["activity_type"] for item in validated]
    duplicates = sorted(
        {item for item in activity_types if activity_types.count(item) > 1}
    )
    if duplicates:
        raise FactValidationError(f"중복 activity presence metadata: {duplicates}")
    return validated
