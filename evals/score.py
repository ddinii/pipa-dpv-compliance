"""Fact-level 채점기.

Extractor 출력과 gold Fact set을 비교한다. Rule 판정이 아니라 추출 품질을 잰다.

지표
    precision / recall / F1   (fact_id, activity_id, value_state) 일치 기준
    value 정확도              위 키가 맞은 Fact 중 값까지 맞은 비율
    offset 정확도             근거 offset이 원문에서 실제로 그 문자열을 가리키는 비율
    환각률                    원문에 없는 값을 실은 Fact의 비율 (NFR-07)
    activity 혼합률           다른 처리행위의 값을 가져온 Fact의 비율 (TST-002)

실행:
    python evals/score.py evals/poc1/sc_p01_gold_facts.json <예측파일.json>
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Iterable, Union

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.extractors.poc2 import DATETIME_FACT_IDS  # noqa: E402
from app.facts.models import FactEnvelope  # noqa: E402


# 비교 키. value까지 넣지 않는 이유는 "Fact를 찾아냈는가"와 "값이 정확한가"를
# 분리해서 봐야 어디가 약한지 알 수 있기 때문이다.
MatchKey = tuple[str, str | None, str]


def match_key(fact: FactEnvelope) -> MatchKey:
    return (fact.fact_type, fact.activity_id, fact.value_state)


def normalize(value: Any) -> Any:
    """값 비교용 정규화. 공백 차이로 오답 처리되는 것을 막는다."""
    if isinstance(value, str):
        return " ".join(value.split())
    if isinstance(value, list):
        return [normalize(item) for item in value]
    return value


@dataclass
class Score:
    gold_total: int = 0
    predicted_total: int = 0
    matched: int = 0
    value_correct: int = 0

    evidence_total: int = 0
    evidence_offset_correct: int = 0

    hallucinated: list[str] = field(default_factory=list)
    activity_leaks: list[str] = field(default_factory=list)
    missed: list[MatchKey] = field(default_factory=list)
    spurious: list[MatchKey] = field(default_factory=list)

    @property
    def precision(self) -> float:
        return self.matched / self.predicted_total if self.predicted_total else 0.0

    @property
    def recall(self) -> float:
        return self.matched / self.gold_total if self.gold_total else 0.0

    @property
    def f1(self) -> float:
        p, r = self.precision, self.recall
        return 2 * p * r / (p + r) if (p + r) else 0.0

    @property
    def value_accuracy(self) -> float:
        return self.value_correct / self.matched if self.matched else 0.0

    @property
    def offset_accuracy(self) -> float:
        if not self.evidence_total:
            return 0.0
        return self.evidence_offset_correct / self.evidence_total

    @property
    def hallucination_rate(self) -> float:
        return len(self.hallucinated) / self.predicted_total if self.predicted_total else 0.0

    @property
    def activity_leak_rate(self) -> float:
        return len(self.activity_leaks) / self.predicted_total if self.predicted_total else 0.0

    def as_dict(self) -> dict:
        return {
            "gold_total": self.gold_total,
            "predicted_total": self.predicted_total,
            "matched": self.matched,
            "precision": round(self.precision, 4),
            "recall": round(self.recall, 4),
            "f1": round(self.f1, 4),
            "value_accuracy": round(self.value_accuracy, 4),
            "offset_accuracy": round(self.offset_accuracy, 4),
            "hallucination_rate": round(self.hallucination_rate, 4),
            "activity_leak_rate": round(self.activity_leak_rate, 4),
            "missed": [list(key) for key in self.missed],
            "spurious": [list(key) for key in self.spurious],
            "hallucinated": self.hallucinated,
            "activity_leaks": self.activity_leaks,
        }


DocumentSource = Union[str, Callable[[str], str]]


def _resolve_document(source: DocumentSource, source_type: str) -> str:
    """Fact가 대조되어야 하는 문서를 고른다.

    PoC1은 문서가 하나라 문자열을 그대로 쓴다. PoC2는 사고 Fact와 통지문 Fact의
    근거 문서가 다르므로(Fact Dictionary 8장) source_type으로 고르는 함수를 받는다.
    EvalCase.document_for가 그 함수다.
    """
    return source if isinstance(source, str) else source(source_type)


def score_facts(
    gold: Iterable[FactEnvelope],
    predicted: Iterable[FactEnvelope],
    document: DocumentSource,
) -> Score:
    gold = list(gold)
    predicted = list(predicted)
    result = Score(gold_total=len(gold), predicted_total=len(predicted))

    gold_by_key: dict[MatchKey, list[FactEnvelope]] = {}
    for fact in gold:
        gold_by_key.setdefault(match_key(fact), []).append(fact)

    # gold의 activity별 근거 위치. 다른 처리행위 구간의 문장을 끌어왔는지 볼 때 쓴다.
    gold_activity_of_value: dict[Any, set[str | None]] = {}
    for fact in gold:
        if fact.value is not None:
            gold_activity_of_value.setdefault(
                json_key(normalize(fact.value)), set()
            ).add(fact.activity_id)

    unmatched = {key: list(items) for key, items in gold_by_key.items()}

    for fact in predicted:
        source = _resolve_document(document, fact.source_type)

        # 근거 offset 정확도 (매칭 여부와 무관하게 센다)
        for piece in fact.evidence:
            result.evidence_total += 1
            if piece.resolves_in(source):
                result.evidence_offset_correct += 1

        # NFR-07 환각: 원문에 없는 값을 실었다
        supported = (
            datetime_supported_by(source, fact.value)
            if fact.fact_type in DATETIME_FACT_IDS
            else value_supported_by(source, fact.value)
        )
        if fact.value is not None and not supported:
            result.hallucinated.append(fact.fact_id)

        # TST-002 혼합: 값은 gold에 있는데 다른 처리행위의 것이다
        if fact.value is not None:
            owners = gold_activity_of_value.get(json_key(normalize(fact.value)))
            if owners and fact.activity_id not in owners:
                result.activity_leaks.append(fact.fact_id)

        key = match_key(fact)
        candidates = unmatched.get(key)
        if not candidates:
            result.spurious.append(key)
            continue

        gold_fact = candidates.pop(0)
        if not candidates:
            unmatched.pop(key)
        result.matched += 1
        if normalize(gold_fact.value) == normalize(fact.value):
            result.value_correct += 1

    for key, leftovers in unmatched.items():
        result.missed.extend([key] * len(leftovers))

    return result


# --- Rule-level ---------------------------------------------------------
#
# 이 PoC의 헤드라인 지표다. Fact를 몇 개 맞췄는지보다 "추출 오류가 판정을 뒤집는가"가
# 중요하다. Fact 하나를 놓쳐도 판정이 안 바뀌면 실무 영향이 없고, 반대로 value_state
# 하나를 틀려서 YELLOW가 GREEN이 되면 준수한 것처럼 보이게 된다.


@dataclass
class RuleScore:
    total: int = 0
    agree: int = 0
    # (케이스, rule_id, gold status, 예측 status)
    mismatches: list[tuple[str, str, str, str]] = field(default_factory=list)
    # gold가 GREEN이 아닌데 GREEN으로 예측한 경우. 가장 위험한 방향이다.
    false_greens: list[tuple[str, str, str]] = field(default_factory=list)
    # gold가 RED/YELLOW인데 N/A로 예측한 경우. 잘못된 부재 선언(confirmed_false)이
    # Rule을 판정 대상에서 빼 버려 결함이 보이지 않게 된다. GREEN만큼 위험하다.
    false_nas: list[tuple[str, str, str]] = field(default_factory=list)

    @property
    def agreement(self) -> float:
        return self.agree / self.total if self.total else 0.0

    @property
    def false_green_rate(self) -> float:
        return len(self.false_greens) / self.total if self.total else 0.0

    @property
    def false_na_rate(self) -> float:
        return len(self.false_nas) / self.total if self.total else 0.0

    def add(self, case: str, gold: dict[str, str], predicted: dict[str, str]) -> None:
        for rule_id in sorted(gold):
            expected = gold[rule_id]
            actual = predicted.get(rule_id, "(없음)")
            self.total += 1
            if actual == expected:
                self.agree += 1
                continue
            self.mismatches.append((case, rule_id, expected, actual))
            if actual == "GREEN" and expected != "GREEN":
                self.false_greens.append((case, rule_id, expected))
            if actual == "N/A" and expected in {"RED", "YELLOW"}:
                self.false_nas.append((case, rule_id, expected))

    def as_dict(self) -> dict:
        return {
            "total": self.total,
            "agree": self.agree,
            "agreement": round(self.agreement, 4),
            "false_green_rate": round(self.false_green_rate, 4),
            "false_na_rate": round(self.false_na_rate, 4),
            "mismatches": [list(item) for item in self.mismatches],
            "false_greens": [list(item) for item in self.false_greens],
            "false_nas": [list(item) for item in self.false_nas],
        }


def score_rule_statuses(
    case: str, gold: dict[str, str], predicted: dict[str, str]
) -> RuleScore:
    score = RuleScore()
    score.add(case, gold, predicted)
    return score


def format_rule_report(score: RuleScore) -> str:
    lines = [
        "Rule-level 채점 결과",
        "=" * 46,
        f"  판정 {score.total}건 중 {score.agree}건 일치",
        f"  status 일치율       {score.agreement:.3f}",
        f"  위험 오판(GREEN)    {score.false_green_rate:.3f}  "
        f"({len(score.false_greens)}건)",
        f"  위험 오판(N/A)      {score.false_na_rate:.3f}  "
        f"({len(score.false_nas)}건)",
    ]
    if score.mismatches:
        lines += ["", "  불일치:"]
        for case, rule_id, expected, actual in score.mismatches[:20]:
            risky = (actual == "GREEN" and expected != "GREEN") or (
                actual == "N/A" and expected in {"RED", "YELLOW"}
            )
            mark = "  <-- 위험" if risky else ""
            lines.append(f"    {case:28s} {rule_id}  gold={expected:6s} 예측={actual}{mark}")
    return "\n".join(lines)


def json_key(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def value_supported_by(document: str, value: Any) -> bool:
    """값이 원문에 실제로 등장하는지 확인한다.

    문자열은 그대로, 배열은 모든 원소가 원문에 있어야 한다. 불린/숫자는 원문 대조가
    의미 없으므로 통과시킨다 (PoC3의 is_required 등).
    """
    if isinstance(value, str):
        return " ".join(value.split()) in " ".join(document.split())
    if isinstance(value, list):
        return all(value_supported_by(document, item) for item in value)
    return True


def datetime_supported_by(document: str, value: Any) -> bool:
    """ISO 날짜·시간 값의 연·월·일·시·분이 원문 표기로 등장하는지 확인한다.

    날짜 Fact는 원문 "2026년 9월 5일 14시 30분"을 "2026-09-05T14:30:00+09:00"으로
    바꿔 싣는다. 글자 그대로 대조하면 형식만 바꾼 값이 환각으로 잡힌다.
    """
    if not isinstance(value, str):
        return False
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return False
    text = " ".join(document.split())
    y, mo, d = parsed.year, parsed.month, parsed.day
    dates = {f"{y}년 {mo}월 {d}일", f"{y}년 {mo:02d}월 {d:02d}일",
             f"{y}-{mo:02d}-{d:02d}", f"{y}.{mo:02d}.{d:02d}", f"{y}. {mo}. {d}."}
    if not any(form in text for form in dates):
        return False
    h, mi = parsed.hour, parsed.minute
    if h == 0 and mi == 0:
        return True  # 날짜만 적힌 원문을 00:00으로 쓴 경우
    minute = f" {mi}분" if mi else ""
    times = {f"{h}시{minute}", f"{h:02d}:{mi:02d}"}
    if h > 12:
        times.add(f"오후 {h - 12}시{minute}")
    return any(form in text for form in times)


def load_facts(path: Path) -> tuple[list[FactEnvelope], dict]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    raw = payload["facts"] if isinstance(payload, dict) else payload
    return [FactEnvelope.model_validate(item) for item in raw], (
        payload if isinstance(payload, dict) else {}
    )


def format_report(score: Score) -> str:
    lines = [
        "Fact-level 채점 결과",
        "=" * 46,
        f"  gold {score.gold_total}개 / 예측 {score.predicted_total}개 / 일치 {score.matched}개",
        "",
        f"  precision          {score.precision:.3f}",
        f"  recall             {score.recall:.3f}",
        f"  F1                 {score.f1:.3f}",
        f"  value 정확도        {score.value_accuracy:.3f}",
        f"  offset 정확도       {score.offset_accuracy:.3f}",
        f"  환각률              {score.hallucination_rate:.3f}  (NFR-07)",
        f"  activity 혼합률     {score.activity_leak_rate:.3f}  (TST-002)",
    ]
    if score.missed:
        lines += ["", "  놓친 Fact:"]
        lines += [f"    - {key}" for key in score.missed[:20]]
    if score.spurious:
        lines += ["", "  gold에 없는 Fact:"]
        lines += [f"    - {key}" for key in score.spurious[:20]]
    if score.hallucinated:
        lines += ["", f"  환각 {len(score.hallucinated)}건: " + ", ".join(score.hallucinated[:10])]
    if score.activity_leaks:
        lines += ["", f"  혼합 {len(score.activity_leaks)}건: " + ", ".join(score.activity_leaks[:10])]
    return "\n".join(lines)


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print(__doc__)
        return 2

    gold_path, predicted_path = Path(argv[1]), Path(argv[2])
    gold_facts, gold_meta = load_facts(gold_path)
    predicted_facts, _ = load_facts(predicted_path)

    document = (gold_path.parent / gold_meta["policy_text_file"]).read_text(encoding="utf-8")

    score = score_facts(gold_facts, predicted_facts, document)
    print(format_report(score))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
