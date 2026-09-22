"""Fact 검증 — 파이프라인 계약 검증 + 근거 offset 검증.

계약 검증(필수 필드/enum/중복 ID)은 app.mapping.fact_schema가 정본이다. 여기서는
그 위에 두 가지를 더한다.

  1. 근거 offset이 원문에서 실제로 그 문자열을 가리키는지 (LLM 추출 경로에 필수)
  2. 타입이 붙은 FactEnvelope 객체로 변환 (평가·채점 계층에서 쓴다)

Fact -> RDF 매핑은 app.mapping.OntologyMapper가 담당한다. 이 모듈은 매핑하지 않는다.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from pydantic import ValidationError

from app.facts.models import FactEnvelope
from app.mapping.fact_schema import FactValidationError as SchemaError
from app.mapping.fact_schema import validate_facts as validate_contract


@dataclass(frozen=True)
class FactIssue:
    index: int
    fact_id: str | None
    message: str

    def __str__(self) -> str:
        where = self.fact_id or f"#{self.index}"
        return f"[{where}] {self.message}"


class FactValidationError(ValueError):
    def __init__(self, issues: list[FactIssue]) -> None:
        self.issues = issues
        super().__init__(
            f"Fact 검증 실패 {len(issues)}건:\n"
            + "\n".join(f"  {issue}" for issue in issues)
        )


def validate_facts(
    raw_facts: Iterable[dict[str, Any]],
    *,
    document: str | None = None,
) -> list[FactEnvelope]:
    """Fact 목록을 검증하고 타입이 붙은 객체로 돌려준다.

    document를 주면 각 evidence의 offset이 원문에서 실제로 그 문자열을 가리키는지도
    확인한다. LLM이 반환하는 offset은 자주 틀리므로 (NFR-07) 추출 경로에서는 반드시 준다.

    하나라도 실패하면 FactValidationError를 던진다. 값을 임의로 보완하지 않는다
    (COM-002).
    """
    raw_facts = list(raw_facts)
    issues: list[FactIssue] = []

    # 1) 파이프라인 계약 검증 (정본: app.mapping.fact_schema)
    try:
        validate_contract(raw_facts)
    except SchemaError as exc:
        raise FactValidationError([FactIssue(-1, None, str(exc))]) from exc

    # 2) 타입 변환 + offset 검증
    facts: list[FactEnvelope] = []
    for index, raw in enumerate(raw_facts):
        fact_id = raw.get("fact_id") if isinstance(raw, dict) else None
        try:
            fact = FactEnvelope.model_validate(raw)
        except ValidationError as exc:
            for error in exc.errors():
                location = ".".join(str(part) for part in error["loc"]) or "(root)"
                issues.append(FactIssue(index, fact_id, f"{location}: {error['msg']}"))
            continue

        if document is not None:
            for position, piece in enumerate(fact.evidence):
                if not piece.resolves_in(document):
                    actual = document[piece.start_offset : piece.end_offset]
                    issues.append(FactIssue(
                        index,
                        fact.fact_id,
                        f"evidence[{position}] offset이 {piece.text!r}가 아니라 "
                        f"{actual!r}를 가리킵니다.",
                    ))

        facts.append(fact)

    if issues:
        raise FactValidationError(issues)
    return facts


def group_by_activity(facts: Iterable[FactEnvelope]) -> dict[str | None, list[FactEnvelope]]:
    """COM-003 process-centered 그룹화.

    같은 activity_id에 속한 Fact끼리만 함께 평가되도록 묶는다. 제3자 제공 A의
    recipient와 제공 B의 purpose를 섞지 않기 위한 기본 단위다 (Fact Dictionary 8장).
    """
    groups: dict[str | None, list[FactEnvelope]] = {}
    for fact in facts:
        groups.setdefault(fact.activity_id, []).append(fact)
    return groups
