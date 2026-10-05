from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class RuleStatus(str, Enum):
    GREEN = "GREEN"
    YELLOW = "YELLOW"
    RED = "RED"
    NOT_APPLICABLE = "N/A"


class Applicability(str, Enum):
    TRUE = "TRUE"
    FALSE = "FALSE"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class Evidence:
    evidence_type: str
    subject: str | None = None
    predicate: str | None = None
    value: str | bool | None = None
    source_text: str | None = None
    note: str | None = None


@dataclass
class InstanceRuleResult:
    instance_id: str
    status: RuleStatus
    applicability: Applicability
    matched_facts: list[str] = field(default_factory=list)
    missing_facts: list[str] = field(default_factory=list)
    uncertain_facts: list[str] = field(default_factory=list)
    evidence: list[Evidence] = field(default_factory=list)
    reason: str = ""
    recommendation: str = ""


@dataclass
class RuleResult:
    rule_id: str
    rule_version: str
    status: RuleStatus
    applicability: Applicability
    matched_facts: list[str]
    missing_facts: list[str]
    uncertain_facts: list[str]
    evidence: list[Evidence]
    legal_basis: list[str]
    reason: str
    recommendation: str
    evaluated_at: str
    instance_results: list[InstanceRuleResult] = field(default_factory=list)
    implementation_notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["status"] = self.status.value
        payload["applicability"] = self.applicability.value
        for instance in payload["instance_results"]:
            instance["status"] = instance["status"].value
            instance["applicability"] = instance["applicability"].value
        return payload


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
