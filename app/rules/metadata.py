from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any


ROOT_DIR = Path(__file__).resolve().parents[2]
RULE_METADATA_PATH = ROOT_DIR / "rules" / "p0_rules.json"


@dataclass(frozen=True)
class RuleMetadata:
    rule_id: str
    poc: str
    title: str
    version: str
    applicability: str
    legal_basis: tuple[str, ...]
    source_spec_legal_basis: tuple[str, ...]
    ontology_terms: tuple[str, ...]
    notes: tuple[str, ...]


@lru_cache(maxsize=1)
def load_rule_profile() -> dict[str, Any]:
    with RULE_METADATA_PATH.open("r", encoding="utf-8") as file:
        return json.load(file)


@lru_cache(maxsize=1)
def load_rule_metadata() -> dict[str, RuleMetadata]:
    profile = load_rule_profile()
    rules: dict[str, RuleMetadata] = {}
    for item in profile["rules"]:
        rules[item["rule_id"]] = RuleMetadata(
            rule_id=item["rule_id"],
            poc=item["poc"],
            title=item["title"],
            version=item.get("rule_version", profile["rule_version"]),
            applicability=item["applicability"],
            legal_basis=tuple(item["legal_basis"]),
            source_spec_legal_basis=tuple(item.get("source_spec_legal_basis", item["legal_basis"])),
            ontology_terms=tuple(item.get("ontology_terms", [])),
            notes=tuple(item.get("notes", [])),
        )
    return rules
