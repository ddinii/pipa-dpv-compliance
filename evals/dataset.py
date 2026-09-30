"""평가 데이터셋 탐색.

한 PoC의 평가 세트는 기준 문서 1묶음 + controlled variants n개다. 기준 문서 하나로만
재면 GREEN/AMBER 경로만 보게 되므로 RED 케이스까지 포함한 전체를 쓸어야 한다.

PoC마다 입력 문서 수가 다르다. PoC1은 처리방침 하나, PoC2는 사고 기록과 통지문
둘이다. EvalCase가 문서를 이름으로 들고, Extractor 호출 규약도 PoC별로 안다.

PoC를 늘릴 때는 아래 POC_DATASETS에 한 줄을 더한다. 러너와 채점기는 손대지 않는다.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from functools import cached_property
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
EVAL_ROOT = ROOT / "evals"


@dataclass(frozen=True)
class DatasetSpec:
    """한 PoC의 평가 세트가 디스크에 놓인 모양.

    ``base_documents``와 ``variant_documents``는 {논리 이름: 파일명}이다. 논리
    이름은 Extractor 호출 규약과 채점기의 근거 대조에서 문서를 고르는 키다.
    """

    poc: str
    base_gold: str
    base_documents: dict[str, str]
    variant_documents: dict[str, str] = field(default_factory=dict)
    gold_name: str = "gold_facts.json"
    # 없어도 되는 문서. PoC2 통지문이 없는 케이스는 "통지하지 않음"을 뜻한다.
    optional_documents: frozenset[str] = frozenset()

    @property
    def directory(self) -> Path:
        return EVAL_ROOT / self.poc

    @property
    def variant_directory(self) -> Path:
        return self.directory / "variants"

    @property
    def heldout_directory(self) -> Path:
        return self.directory / "heldout"

    @property
    def prediction_directory(self) -> Path:
        return self.directory / "predictions"


POC_DATASETS: dict[str, DatasetSpec] = {
    "poc1": DatasetSpec(
        poc="poc1",
        base_gold="sc_p01_gold_facts.json",
        base_documents={"policy": "sc_p01_policy.txt"},
        variant_documents={"policy": "policy.txt"},
    ),
    "poc2": DatasetSpec(
        poc="poc2",
        base_gold="sc_p02_gold_facts.json",
        base_documents={
            "incident": "sc_p02_incident.txt",
            "notice": "sc_p02_notice.txt",
        },
        variant_documents={"incident": "incident.txt", "notice": "notice.txt"},
        optional_documents=frozenset({"notice"}),
    ),
}

# Fact의 source_type -> 그 근거가 실재해야 하는 문서의 논리 이름.
# PoC2는 사고 Fact와 통지문 Fact의 근거 문서가 다르다 (Fact Dictionary 8장).
SOURCE_TYPE_DOCUMENT = {
    "policy_text": "policy",
    "incident_record": "incident",
    "notification_notice": "notice",
}


@dataclass(frozen=True)
class EvalCase:
    name: str
    document_paths: dict[str, Path]
    gold_path: Path
    poc: str = "poc1"

    @cached_property
    def documents(self) -> dict[str, str]:
        return {
            name: path.read_text(encoding="utf-8")
            for name, path in self.document_paths.items()
        }

    @property
    def document(self) -> str:
        """문서가 하나뿐인 PoC의 원문.

        둘 이상이면 어느 것을 뜻하는지 알 수 없으므로 실패한다.
        """
        if len(self.documents) != 1:
            raise ValueError(
                f"{self.poc}는 문서가 {len(self.documents)}개다. documents[이름]을 쓸 것"
            )
        return next(iter(self.documents.values()))

    def document_for(self, source_type: str) -> str:
        """Fact의 source_type에 맞는 근거 문서를 고른다.

        ``derived``는 특정 문서를 가리키지 않으므로 전체를 이어 붙여 돌려준다.
        근거가 어느 쪽에서든 해결되면 통과시키기 위해서다.
        """
        name = SOURCE_TYPE_DOCUMENT.get(source_type)
        if name is not None and name in self.documents:
            return self.documents[name]
        return "\n".join(self.documents.values())

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
    def gold_system_metadata(self) -> list[dict]:
        """정답 activity presence metadata. Fact가 아니므로 facts와 따로 둔다."""
        return self.payload.get("system_metadata", [])

    @property
    def description(self) -> str:
        meta = self.payload.get("variant") or self.payload.get("heldout")
        return meta["description"] if meta else "기준 문서 (변형 없음)"

    @property
    def target_rule(self) -> str | None:
        variant = self.payload.get("variant")
        return variant["target_rule"] if variant else None

    def extract_with(
        self, extractor: Any, *, analysis_id: str, controller_id: str,
        controller_name: str | None = None,
    ) -> list[dict]:
        """PoC별 Protocol 호출 규약에 맞춰 Extractor를 부른다.

        app/extractors/base.py의 Poc1Extractor / Poc2Extractor는 파라미터가
        다르다. 그 차이를 러너가 아니라 여기서 흡수한다.
        """
        common = {
            "analysis_id": analysis_id,
            "controller_id": controller_id,
            "controller_name": controller_name,
        }
        if self.poc == "poc1":
            return extractor.extract(**common, policy_text=self.documents["policy"])
        if self.poc == "poc2":
            return extractor.extract(
                **common,
                incident={"record": self.documents["incident"]},
                notification={"notice_text": self.documents["notice"]}
                if "notice" in self.documents
                else None,
            )
        raise ValueError(f"Extractor 호출 규약이 정의되지 않은 PoC입니다: {self.poc}")


SPLITS = ("dev", "heldout", "all")


def _cases_in(directory: Path, spec: DatasetSpec, poc: str) -> list[EvalCase]:
    """하위 디렉터리마다 문서와 gold_facts.json이 모두 있으면 케이스 하나다."""
    cases = []
    if not directory.is_dir():
        return cases
    for case_dir in sorted(directory.iterdir()):
        if not case_dir.is_dir():
            continue
        documents = {
            name: case_dir / filename for name, filename in spec.variant_documents.items()
        }
        required = [p for n, p in documents.items() if n not in spec.optional_documents]
        documents = {
            n: p for n, p in documents.items()
            if n not in spec.optional_documents or p.is_file()
        }
        gold = case_dir / spec.gold_name
        if gold.is_file() and all(path.is_file() for path in required):
            cases.append(EvalCase(case_dir.name, documents, gold, poc=poc))
    return cases


def load_cases(poc: str = "poc1", split: str = "dev") -> list[EvalCase]:
    """평가 케이스를 돌려준다.

    dev      기준 문서 + 변형. 프롬프트를 고칠 때 보는 세트
    heldout  프롬프트를 고칠 때 보지 않는 세트. 일반화 성능은 여기서만 말한다
    all      dev 다음 heldout
    """
    if split not in SPLITS:
        raise ValueError(f"split은 {list(SPLITS)} 중 하나여야 합니다. 받은 값: {split!r}")
    try:
        spec = POC_DATASETS[poc]
    except KeyError:
        raise ValueError(
            f"평가 세트가 등록되지 않은 PoC입니다: {poc!r}. "
            f"등록된 것: {sorted(POC_DATASETS)}. "
            "evals/dataset.py의 POC_DATASETS에 DatasetSpec을 추가하세요."
        ) from None

    cases: list[EvalCase] = []
    if split in ("dev", "all"):
        base_documents = {
            name: spec.directory / filename for name, filename in spec.base_documents.items()
        }
        base_gold = spec.directory / spec.base_gold
        missing = [str(p) for p in [*base_documents.values(), base_gold] if not p.is_file()]
        if missing:
            raise FileNotFoundError(f"{poc} 평가 세트 파일이 없습니다: {missing}")
        cases.append(EvalCase("base", base_documents, base_gold, poc=poc))
        cases += _cases_in(spec.variant_directory, spec, poc)
    if split in ("heldout", "all"):
        cases += _cases_in(spec.heldout_directory, spec, poc)
    return cases


def load_poc1_cases() -> list[EvalCase]:
    return load_cases("poc1")
