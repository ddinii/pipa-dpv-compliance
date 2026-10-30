"""Validation for the PIPA Fact Dictionary v1.0 common envelope."""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from copy import deepcopy
from typing import Any

from .mapping_registry import DOCUMENT_SCOPE_FACTS


FACT_SCHEMA_VERSION = "fact-1.0"
VALUE_STATES = {"confirmed", "unknown", "absent"}
SOURCE_TYPES = {
    "policy_text",
    "incident_record",
    "notification_notice",
    "structured_form",
    "derived",
}
POC2_INCIDENT_FACTS = {"F2-01", "F2-02", "F2-05", "F2-06"}
POC2_NOTICE_FACTS = {"F2-03", "F2-04", "F2-07", "F2-08", "F2-09", "F2-10", "F2-11", "F2-12"}
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
    if not evidence:
        raise FactValidationError(f"{fact_id}: evidence는 하나 이상이어야 함")
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

    # Rights facts are global to the data subject. Every other frozen P0 Fact
    # belongs to a processing activity or incident group and must retain that
    # scope explicitly; falling back to subject_id would hide malformed input.
    if fact_type(identifier) not in DOCUMENT_SCOPE_FACTS and not fact["activity_id"]:
        raise FactValidationError(f"{identifier}: activity_id가 필요함")

    if fact["value_state"] not in VALUE_STATES:
        raise FactValidationError(
            f"{identifier}: value_state는 {sorted(VALUE_STATES)} 중 하나여야 함"
        )
    if fact["source_type"] not in SOURCE_TYPES:
        raise FactValidationError(
            f"{identifier}: source_type은 {sorted(SOURCE_TYPES)} 중 하나여야 함"
        )
    base_type = fact_type(identifier)
    if base_type.startswith("F1-") and fact["source_type"] not in {"policy_text", "derived"}:
        raise FactValidationError(f"{identifier}: PoC1 Fact source_type은 policy_text여야 함")
    if base_type in POC2_INCIDENT_FACTS and fact["source_type"] not in {"incident_record", "derived"}:
        raise FactValidationError(f"{identifier}: 사고 Fact source_type은 incident_record여야 함")
    if base_type in POC2_NOTICE_FACTS and fact["source_type"] not in {"notification_notice", "derived"}:
        raise FactValidationError(f"{identifier}: 통지 Fact source_type은 notification_notice여야 함")
    if base_type.startswith("F3-") and fact["source_type"] not in {"structured_form", "derived"}:
        raise FactValidationError(f"{identifier}: PoC3 Fact source_type은 structured_form이어야 함")
    if fact["schema_version"] != FACT_SCHEMA_VERSION:
        raise FactValidationError(
            f"{identifier}: schema_version은 {FACT_SCHEMA_VERSION!r}이어야 함"
        )

    # Frozen Fact Dictionary v1.0 defines F1-12 (권리 행사절차) as string.
    # The existing PoC1 extractor predates that freeze and emits
    # {right, procedure}.  Accept both at the integration boundary and map
    # them to the same RDF shape so the frozen string form remains canonical
    # without breaking the already integrated extractor.
    if base_type == "F1-12" and fact["value_state"] == "confirmed":
        value = fact["value"]
        valid_string = isinstance(value, str) and bool(value.strip())
        valid_legacy_object = (
            isinstance(value, Mapping)
            and any(value.get(key) not in (None, "") for key in ("right", "right_name"))
            and any(value.get(key) not in (None, "") for key in ("procedure", "description"))
        )
        if not (valid_string or valid_legacy_object):
            raise FactValidationError(
                f"{identifier}: F1-12 value는 비어 있지 않은 문자열 또는 "
                "right/procedure 객체여야 함"
            )

    # F1-20: 보호책임자 성명 또는 담당 부서 명칭 (제30조 제1항 제6호). 둘 중 하나는 있어야 한다.
    if base_type == "F1-20" and fact["value_state"] == "confirmed":
        value = fact["value"]
        if not (
            isinstance(value, Mapping)
            and any(value.get(key) not in (None, "") for key in ("name", "department"))
        ):
            raise FactValidationError(
                f"{identifier}: F1-20 value는 name 또는 department가 있는 객체여야 함"
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
