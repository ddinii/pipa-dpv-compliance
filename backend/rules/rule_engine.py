"""
PIPA Machine-Readable Rules Profile (2계층)

주제 제안 문서의 PoC 범위: "개인정보 처리방침 필수 기재사항" 관련 10개 규칙.
전체 개인정보 보호법을 구현하지 않고, 처리방침 자동점검(Killer Application #1)에
필요한 최소 규칙 집합만 구현합니다.

각 Rule은:
  1. 어떤 Fact 필드를 검사하는지 (field_name)
  2. 그 근거가 되는 법 조문 (legal_basis) — ⚠️ 팀원 검증 필요, placeholder
  3. 판정 로직 (evaluate)
로 구성됩니다.

판정은 GREEN / RED / AMBER 세 가지로만 나뉩니다 (Yes/No 이분법 지양).
  - GREEN: 필수 항목이 명시적으로 존재
  - RED:   필수 항목이 명시적으로 부재 (텍스트 어디에도 언급 없음)
  - AMBER: LLM 추출 신뢰도가 낮거나, 조건부 판단(예: 미성년자 포함 여부)이
           필요해 사람의 검토가 필요한 경우
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Callable, List

from backend.models import PolicyFacts, RuleResult, Verdict, FieldStatus, ComplianceReport

# 신뢰도가 이 값 미만이면 GREEN/RED로 확정하지 않고 AMBER로 내려보냄
CONFIDENCE_THRESHOLD = 0.6


@dataclass
class Rule:
    rule_id: str
    rule_name: str
    legal_basis: str  # TODO(팀원): 실제 최신 조문 번호로 검증/치환
    field_name: str
    extra_check: Callable[[PolicyFacts], Verdict | None] | None = None
    """extra_check: 단순 존재유무를 넘어선 추가 판정 로직이 필요한 경우 사용.
    None을 반환하면 기본 존재유무 판정 로직으로 fallback."""


def _base_verdict(field) -> Verdict:
    """ExtractedField 하나에 대한 기본 판정 로직"""
    if field.confidence < CONFIDENCE_THRESHOLD:
        return Verdict.AMBER
    if field.status == FieldStatus.PRESENT:
        return Verdict.GREEN
    if field.status == FieldStatus.ABSENT:
        return Verdict.RED
    return Verdict.AMBER  # UNCLEAR


def _rule_cross_border(facts: PolicyFacts) -> Verdict | None:
    """국외이전은 '언급이 없으면 RED'가 아니라, 국외이전이 실제로 없다면
    해당 항목 자체가 불필요할 수 있음 -> 이런 경우가 AMBER의 대표 예시."""
    field = facts.cross_border_transfer
    if field.status == FieldStatus.ABSENT and field.confidence >= CONFIDENCE_THRESHOLD:
        # 국외이전이 없다고 '명시'되어 있으면 GREEN (해당 없음도 명시가 되어야 함)
        # 단순히 언급이 아예 없는 것과는 다름 -> extraction 단계에서 구분 필요
        return Verdict.AMBER
    return None  # 기본 로직으로 fallback


def _rule_minor_context(facts: PolicyFacts) -> Verdict | None:
    """만 14세 미만 아동 대상 처리가 포함된 경우, 법정대리인 동의 등
    추가 요건이 발생할 수 있어 규칙만으로 GREEN 확정이 어려움 -> AMBER."""
    if facts.involves_minor:
        return Verdict.AMBER
    return None


RULES: List[Rule] = [
    Rule("R01", "처리목적 명시", "개인정보 보호법 제30조제1항제1호(placeholder)", "purpose"),
    Rule("R02", "수집항목 명시", "개인정보 보호법 제30조제1항제1호(placeholder)", "collection_items"),
    Rule("R03", "보유기간 명시", "개인정보 보호법 제30조제1항제2호(placeholder)", "retention_period"),
    Rule("R04", "제3자 제공 관련 사항", "개인정보 보호법 제30조제1항제3호(placeholder)", "third_party_provision"),
    Rule("R05", "처리위탁 관련 사항", "개인정보 보호법 제30조제1항제4호(placeholder)", "outsourcing"),
    Rule("R06", "파기절차 및 방법 명시", "개인정보 보호법 제30조제1항제5호(placeholder)", "destruction_procedure"),
    Rule("R07", "국외이전 관련 사항", "개인정보 보호법 제28조의8(placeholder)", "cross_border_transfer",
         extra_check=_rule_cross_border),
    Rule("R08", "동의 철회 방법 명시", "개인정보 보호법 제30조제1항제6호(placeholder)", "consent_withdrawal_method"),
    Rule("R09", "정보주체 권리행사 방법 명시", "개인정보 보호법 제30조제1항제6호(placeholder)", "data_subject_rights_method"),
    Rule("R10", "개인정보보호책임자 연락처 명시", "개인정보 보호법 제30조제1항제7호(placeholder)", "privacy_officer_contact"),
]


def evaluate_rule(rule: Rule, facts: PolicyFacts) -> RuleResult:
    field = getattr(facts, rule.field_name)

    verdict: Verdict | None = None
    if rule.extra_check is not None:
        verdict = rule.extra_check(facts)
    if verdict is None:
        verdict = _base_verdict(field)

    # 미성년자 컨텍스트가 있으면 개별 규칙 전체를 한 단계 보수적으로 조정할 수도 있음
    # (여기서는 단순화하여 별도 규칙(R_minor)으로 분리)

    rationale_map = {
        Verdict.GREEN: f"'{rule.rule_name}' 항목이 명시적으로 확인됨. (근거: {field.evidence or '텍스트 내 명시'})",
        Verdict.RED: f"'{rule.rule_name}' 항목이 처리방침 내에서 발견되지 않음. 필수 기재사항 누락 가능성.",
        Verdict.AMBER: f"'{rule.rule_name}' 항목의 판단을 위해 추가 검토가 필요함 "
                        f"(추출 신뢰도: {field.confidence:.2f}, 상태: {field.status.value}).",
    }

    return RuleResult(
        rule_id=rule.rule_id,
        rule_name=rule.rule_name,
        legal_basis=rule.legal_basis,
        verdict=verdict,
        rationale=rationale_map[verdict],
    )


def evaluate_policy(facts: PolicyFacts) -> ComplianceReport:
    """전체 10개 규칙을 순회하며 판정 후 종합 리포트 생성"""
    results = [evaluate_rule(rule, facts) for rule in RULES]

    # 미성년자 컨텍스트에 대한 별도 안내 규칙 (선택적 부가 규칙)
    minor_verdict = _rule_minor_context(facts)
    if minor_verdict is not None:
        results.append(RuleResult(
            rule_id="R11",
            rule_name="미성년자 정보주체 처리 관련 추가요건",
            legal_basis="개인정보 보호법 제22조의2(placeholder)",
            verdict=minor_verdict,
            rationale="만 14세 미만 아동 대상 처리가 포함되어 법정대리인 동의 등 "
                      "추가 요건 충족 여부에 대한 사람의 검토가 필요함.",
        ))

    green = sum(1 for r in results if r.verdict == Verdict.GREEN)
    red = sum(1 for r in results if r.verdict == Verdict.RED)
    amber = sum(1 for r in results if r.verdict == Verdict.AMBER)

    if red > 0:
        overall = Verdict.RED
    elif amber > 0:
        overall = Verdict.AMBER
    else:
        overall = Verdict.GREEN

    return ComplianceReport(
        overall_verdict=overall,
        results=results,
        green_count=green,
        red_count=red,
        amber_count=amber,
    )
