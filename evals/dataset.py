"""평가 데이터셋 탐색.

한 PoC의 평가 세트는 기준 문서 1개 + controlled variants n개다. 기준 문서 하나로만
재면 GREEN/AMBER 경로만 보게 되므로 RED와 N/A 케이스까지 포함한 전체를 쓸어야 한다.

PoC를 늘릴 때는 아래 POC_DATASETS에 한 줄을 더한다. 로더·러너·채점기는 손대지 않는다.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import cached_property
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVAL_ROOT = ROOT / "evals"


@dataclass(frozen=True)
class DatasetSpec:
    """한 PoC의 평가 세트가 디스크에 놓인 모양."""

    poc: str
    base_document: str
    base_gold: str
    document_name: str = "policy.txt"
    gold_name: str = "gold_facts.json"

    @property
    def directory(self) -> Path:
        return EVAL_ROOT / self.poc

    @property
    def variant_directory(self) -> Path:
        return self.directory / "variants"

    @property
    def prediction_directory(self) -> Path:
        return self.directory / "predictions"


POC_DATASETS: dict[str, DatasetSpec] = {
    "poc1": DatasetSpec(
        poc="poc1",
        base_document="sc_p01_policy.txt",
        base_gold="sc_p01_gold_facts.json",
    ),
    # poc2는 SC-P02 원문과 gold set이 준비되면 추가한다. 그 전에 등록하면
    # load_cases()가 빈 세트를 조용히 돌려주어 "0건 평가 통과"가 되어 버린다.
}


@dataclass(frozen=True)
class EvalCase:
    name: str
    document_path: Path
    gold_path: Path
    poc: str = "poc1"

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
        return variant["description"] if variant else "기준 문서 (변형 없음)"

    @property
    def target_rule(self) -> str | None:
        variant = self.payload.get("variant")
        return variant["target_rule"] if variant else None


def load_cases(poc: str = "poc1") -> list[EvalCase]:
    """기준 문서를 먼저, 그다음 변형을 이름순으로 돌려준다."""
    try:
        spec = POC_DATASETS[poc]
    except KeyError:
        raise ValueError(
            f"평가 세트가 등록되지 않은 PoC입니다: {poc!r}. "
            f"등록된 것: {sorted(POC_DATASETS)}. "
            "evals/dataset.py의 POC_DATASETS에 DatasetSpec을 추가하세요."
        ) from None

    base_document = spec.directory / spec.base_document
    base_gold = spec.directory / spec.base_gold
    if not base_document.is_file() or not base_gold.is_file():
        raise FileNotFoundError(
            f"{poc} 기준 문서 또는 gold set이 없습니다: {base_document}, {base_gold}"
        )

    cases = [EvalCase("base", base_document, base_gold, poc=poc)]

    if spec.variant_directory.is_dir():
        for directory in sorted(spec.variant_directory.iterdir()):
            if not directory.is_dir():
                continue
            document = directory / spec.document_name
            gold = directory / spec.gold_name
            if document.is_file() and gold.is_file():
                cases.append(EvalCase(directory.name, document, gold, poc=poc))

    return cases


def load_poc1_cases() -> list[EvalCase]:
    return load_cases("poc1")
