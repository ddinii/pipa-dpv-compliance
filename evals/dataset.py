"""평가 데이터셋 탐색.

PoC1 평가 세트는 기준 문서 1개 + controlled variants 6개로 이루어진다.
Extractor를 기준 문서 하나로만 재면 GREEN/AMBER 경로만 보게 되므로,
RED와 N/A 케이스까지 포함한 전체를 쓸어야 한다.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import cached_property
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
POC1_DIR = ROOT / "evals" / "poc1"
VARIANT_DIR = POC1_DIR / "variants"


@dataclass(frozen=True)
class EvalCase:
    name: str
    document_path: Path
    gold_path: Path

    @cached_property
    def document(self) -> str:
        return self.document_path.read_text(encoding="utf-8")

    @cached_property
    def payload(self) -> dict:
        return json.loads(self.gold_path.read_text(encoding="utf-8"))

    @property
    def gold_facts(self) -> list[dict]:
        return self.payload["facts"]

    @property
    def expected_rule_status(self) -> dict[str, str]:
        return self.payload["expected_rule_status"]

    @property
    def description(self) -> str:
        variant = self.payload.get("variant")
        return variant["description"] if variant else "기준 처리방침 (변형 없음)"

    @property
    def target_rule(self) -> str | None:
        variant = self.payload.get("variant")
        return variant["target_rule"] if variant else None


def load_poc1_cases() -> list[EvalCase]:
    """기준 문서를 먼저, 그다음 변형을 이름순으로 돌려준다."""
    cases = [
        EvalCase(
            name="base",
            document_path=POC1_DIR / "sc_p01_policy.txt",
            gold_path=POC1_DIR / "sc_p01_gold_facts.json",
        )
    ]

    if VARIANT_DIR.is_dir():
        for directory in sorted(VARIANT_DIR.iterdir()):
            if not directory.is_dir():
                continue
            document = directory / "policy.txt"
            gold = directory / "gold_facts.json"
            if document.is_file() and gold.is_file():
                cases.append(EvalCase(directory.name, document, gold))

    return cases
