"""Validation for the PIPA Fact Dictionary v1.0 common envelope."""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from copy import deepcopy
from typing import Any


FACT_SCHEMA_VERSION = "fact-1.0"
VALUE_STATES = {"confirmed", "unknown", "absent"}
SOURCE_TYPES = {
    "policy_text",
    "incident_record",
    "notification_notice",
    "structured_form",
    "derived",
}
PIPA_NAMESPACE = "https://w3id.org/pipa-compliance/ontology#"
FACT_TYPE_PATTERN = re.compile(r"^(F[123]-\d{2})(?:[-_:].+)?$")

REQUIRED_FIELDS = {
    "fact_id",
    "subject_id",
    "activity_id",
    "ontology_class",
    "ontology_property",
    "value",
    "value_state",
    "source_type",
    "evidence",
    "schema_version",
}


class FactValidationError(ValueError):
    """Raised when a Fact violates the frozen Fact Dictionary contract."""


def fact_type(fact_id: str) -> str:
    match = FACT_TYPE_PATTERN.match(fact_id)
    if not match:
        raise FactValidationError(f"지원하지 않는 fact_id 형식: {fact_id!r}")
    return match.group(1)


def local_name(value: str | None) -> str | None:
    if value is None:
        return None
    if value.startswith(PIPA_NAMESPACE):
        return value[len(PIPA_NAMESPACE) :]
    if "://" in value:
        raise FactValidationError(
            f"온톨로지 IRI는 {PIPA_NAMESPACE} 네임스페이스만 허용됨: {value}"
        )
    return value


def _validate_evidence(evidence: Any, fact_id: str) -> None:
    if not isinstance(evidence, list):
        raise FactValidationError(f"{fact_id}: evidence는 배열이어야 함")
    for index, item in enumerate(evidence):
        if not isinstance(item, Mapping):
            raise FactValidationError(f"{fact_id}: evidence[{index}]는 객체여야 함")
        if not any(key in item for key in ("text", "field_path", "offset")):
            raise FactValidationError(
                f"{fact_id}: evidence[{index}]에는 text, field_path 또는 offset이 필요함"
            )


def validate_fact(raw: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(raw, Mapping):
        raise FactValidationError("Fact는 JSON 객체여야 함")

    missing = REQUIRED_FIELDS - set(raw)
    if missing:
        raise FactValidationError(f"Fact 필수 필드 누락: {sorted(missing)}")

    fact = deepcopy(dict(raw))
    identifier = fact["fact_id"]
    if not isinstance(identifier, str) or not identifier.strip():
        raise FactValidationError("fact_id는 비어 있지 않은 문자열이어야 함")
    fact["fact_type"] = fact_type(identifier)

    for field in ("subject_id", "ontology_class", "source_type", "schema_version"):
        if not isinstance(fact[field], str) or not fact[field].strip():
            raise FactValidationError(f"{identifier}: {field}는 비어 있지 않은 문자열이어야 함")

    if fact["activity_id"] is not None and not isinstance(fact["activity_id"], str):
        raise FactValidationError(f"{identifier}: activity_id는 문자열 또는 null이어야 함")
    if fact["ontology_property"] is not None and not isinstance(
        fact["ontology_property"], str
    ):
        raise FactValidationError(
            f"{identifier}: ontology_property는 문자열 또는 null이어야 함"
        )

    fact["ontology_class"] = local_name(fact["ontology_class"])
    fact["ontology_property"] = local_name(fact["ontology_property"])

    if fact["value_state"] not in VALUE_STATES:
        raise FactValidationError(
            f"{identifier}: value_state는 {sorted(VALUE_STATES)} 중 하나여야 함"
        )
    if fact["source_type"] not in SOURCE_TYPES:
        raise FactValidationError(
            f"{identifier}: source_type은 {sorted(SOURCE_TYPES)} 중 하나여야 함"
        )
    if fact["schema_version"] != FACT_SCHEMA_VERSION:
        raise FactValidationError(
            f"{identifier}: schema_version은 {FACT_SCHEMA_VERSION!r}이어야 함"
        )

    _validate_evidence(fact["evidence"], identifier)
    return fact


def validate_facts(raw_facts: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    facts = [validate_fact(item) for item in raw_facts]
    identifiers = [item["fact_id"] for item in facts]
    duplicate_ids = sorted({item for item in identifiers if identifiers.count(item) > 1})
    if duplicate_ids:
        raise FactValidationError(f"중복 fact_id: {duplicate_ids}")
    return facts

