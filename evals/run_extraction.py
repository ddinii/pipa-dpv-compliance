"""Extractor를 한 PoC의 평가 세트 전체에 돌리고 채점한다.

    문서 ──LLM 2-pass──> Fact ──검증──> RDF ──> Rule Engine
                          │                        │
                     Fact-level 채점          Rule-level 비교

평가 세트는 기준 문서 1개 + controlled variants n개다. 기준 문서 하나로만 재면
GREEN/AMBER 경로만 보게 되므로 RED와 N/A 케이스까지 함께 돌린다.

이 스크립트는 Claude API를 호출하므로 비용이 발생한다.

    $env:ANTHROPIC_API_KEY = "sk-ant-..."
    python evals\\run_extraction.py

자격증명은 환경변수에서만 읽는다. 키를 인자나 소스에 넣지 않는다.

옵션:
    --poc        평가할 PoC (기본 poc1). evals/dataset.py의 POC_DATASETS 참고
    --model      기본 claude-opus-5
    --split      dev(기본) | heldout | all. heldout은 프롬프트를 고칠 때 보지 않는
                 세트다. 그 결과를 보고 프롬프트를 고치면 heldout도 오염된다
    --case       특정 케이스만 실행 (반복 지정 가능). 생략하면 전체
    --no-cache   원문 prompt caching 비활성화 (캐시 효과 측정용)
    --out-dir    예측 Fact 저장 위치 (기본 evals/<poc>/predictions)
    --label      실행 이름 (기본 <poc>-<model>-cache|nocache). 실행마다 결과가
                 <out-dir>/runs/<label>.json으로 따로 남아 서로 덮어쓰지 않는다.

여러 실행을 비교하려면:
    python evals\\compare_runs.py evals\\poc1\\predictions\\runs
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.extractors.poc1 import DEFAULT_MODEL  # noqa: E402
from app.extractors.poc1_llm_extractor import LlmPoC1Extractor  # noqa: E402
from app.extractors.poc2_llm_extractor import LlmPoc2Extractor  # noqa: E402
from app.facts.graph import facts_to_mapping
from app.mapping.fact_schema import FactValidationError as FactMappingError  # noqa: E402
from app.facts.models import FactEnvelope  # noqa: E402
from app.facts.validator import FactValidationError, validate_facts  # noqa: E402
from app.rules.engine import P0RuleEngine  # noqa: E402
from app.services.compliance import (  # noqa: E402
    _split_extractor_output,
    with_notice_presence,
)
from app.extractors.usage import Usage, format_usage  # noqa: E402
from evals.dataset import POC_DATASETS, SPLITS, EvalCase, load_cases  # noqa: E402
from evals.score import (  # noqa: E402
    RuleScore,
    Score,
    format_report,
    format_rule_report,
    score_facts,
)

# PoC별 Extractor. 모두 app/extractors/base.py의 Protocol을 구현한다.
EXTRACTORS = {"poc1": LlmPoC1Extractor, "poc2": LlmPoc2Extractor}

CONTROLLER_ID = "ctrl-001"


def run_case(
    case: EvalCase,
    extractor,
    engine: P0RuleEngine,
    out_dir: Path,
    diagnostics: list,
) -> dict:
    """한 케이스를 추출부터 Rule 판정까지 돌린다."""
    print(f"\n[{case.name}] {case.description}")

    diagnostics.clear()
    raw_facts, presence = _split_extractor_output(
        case.extract_with(extractor, analysis_id=case.name, controller_id=CONTROLLER_ID)
    )
    if case.poc == "poc2":
        # 서비스(run_breach_check)와 같은 경로. 통지문이 없으면 명시적 부재다.
        presence = with_notice_presence(
            presence, notification_provided="notice" in case.documents
        )
    for item in presence:
        print(f"  presence {item['activity_type']}={item['state']}")
    rejected = diagnostics[0].rejected if diagnostics else []
    usage = diagnostics[0].usage if diagnostics else Usage()
    print(f"  Fact {len(raw_facts)}개 추출 · {len(rejected)}개 거부")
    for item in rejected:
        quote = f" | 인용={item.quote!r}" if item.quote else ""
        print(f"    거부 {item.fact_id}: {item.reason}{quote}")

    result = type("R", (), {"facts": raw_facts, "rejected": rejected})()

    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"{case.name}.json").write_text(
        json.dumps(
            {
                "case": case.name,
                "poc": case.poc,
                "fact_schema_version": "fact-1.0",
                "facts": result.facts,
                "system_metadata": presence,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    # COM-002. 검증에 실패하면 이 케이스는 Rule까지 가지 않는다.
    try:
        facts = validate_facts(result.facts)
    except FactValidationError as exc:
        print(f"  Fact 검증 실패 {len(exc.issues)}건")
        for issue in exc.issues[:10]:
            print(f"    {issue}")
        return {"case": case, "facts": None, "statuses": {}, "rejected": len(result.rejected), "usage": usage}

    try:
        mapping = facts_to_mapping(facts, system_metadata=presence)
    except FactMappingError as exc:
        print(f"  매핑 실패: {exc}")
        return {"case": case, "facts": facts, "statuses": {}, "rejected": len(result.rejected), "usage": usage}

    statuses = {
        item.rule_id: item.status.value
        for item in engine.evaluate_mapping_result(mapping, poc=case.poc)
    }
    return {
        "case": case,
        "facts": facts,
        "statuses": statuses,
        "rejected": len(result.rejected),
        "usage": usage,
    }


def summarize(
    rows: list[dict], fact_score: Score, rule_score: RuleScore, usage: Usage
) -> None:
    print("\n" + "=" * 78)
    print("케이스별 요약")
    print("=" * 78)
    header = f"  {'케이스':28s} {'겨냥 Rule':10s} {'gold':7s} {'예측':7s} {'거부':>4s}"
    print(header)
    for row in rows:
        case: EvalCase = row["case"]
        target = case.target_rule or "-"
        gold = case.expected_rule_status.get(target, "-") if case.target_rule else "-"
        actual = row["statuses"].get(target, "-") if case.target_rule else "-"
        mark = "" if gold == actual or not case.target_rule else "   <-- 불일치"
        print(f"  {case.name:28s} {target:10s} {gold:7s} {actual:7s} {row['rejected']:>4d}{mark}")

    print()
    print(format_report(fact_score))
    print()
    print(format_rule_report(rule_score))
    print()
    print("호출량")
    print(f"  {format_usage(usage)}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--poc", default="poc1", choices=sorted(POC_DATASETS))
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--split", default="dev", choices=SPLITS)
    parser.add_argument("--case", action="append", default=None)
    parser.add_argument("--no-cache", action="store_true")
    parser.add_argument("--out-dir", type=Path, default=None)
    parser.add_argument("--label", default=None)
    args = parser.parse_args()
    started_at = datetime.now(timezone.utc).isoformat(timespec="seconds")

    if args.poc not in EXTRACTORS:
        print(f"{args.poc}용 Extractor가 아직 없습니다. 있는 것: {sorted(EXTRACTORS)}")
        return 2

    out_dir = args.out_dir or POC_DATASETS[args.poc].prediction_directory
    # 실행마다 다른 이름을 붙여 서로 덮어쓰지 않게 한다. 모델 비교와 캐시 효과
    # 측정이 이것 없이는 불가능하다.
    split_tag = "" if args.split == "dev" else f"-{args.split}"
    label = args.label or (
        f"{args.poc}{split_tag}-{args.model}-{'nocache' if args.no_cache else 'cache'}"
    )
    run_dir = out_dir / label
    cases = load_cases(args.poc, split=args.split)
    if args.case:
        wanted = set(args.case)
        cases = [case for case in cases if case.name in wanted]
        if not cases:
            print(f"해당 케이스가 없습니다: {sorted(wanted)}")
            return 2

    print(f"[{label}] 평가 세트({args.split}) {len(cases)}개 · model={args.model} "
          f"· caching={'off' if args.no_cache else 'on'}")

    # 거부 사유를 러너가 볼 수 있도록 훅을 단다. 원문은 기록하지 않는다.
    diagnostics: list = []
    try:
        # from_environment()가 키 유무를 먼저 본다. 키를 인자로 받지 않으므로
        # 이 코드가 키 값을 보지 않는다 (handoff 7장).
        extractor = EXTRACTORS[args.poc].from_environment(
            model=args.model,
            cache_document=not args.no_cache,
            on_result=diagnostics.append,
        )
    except ModuleNotFoundError:
        print("anthropic SDK가 없습니다: python -m pip install anthropic")
        return 2
    except RuntimeError as exc:
        print(exc)
        print('  PowerShell: $env:ANTHROPIC_API_KEY = "sk-ant-..."')
        return 2
    engine = P0RuleEngine()

    rows = []
    fact_score = Score()
    rule_score = RuleScore()
    total_usage = Usage()

    for case in cases:
        row = run_case(case, extractor, engine, run_dir, diagnostics)
        rows.append(row)
        total_usage.merge(row["usage"])

        if row["facts"] is not None:
            gold_facts = [FactEnvelope.model_validate(item) for item in case.gold_facts]
            case_score = score_facts(gold_facts, row["facts"], case.document_for)
            _accumulate(fact_score, case_score)

        rule_score.add(case.name, case.expected_rule_status, row["statuses"])

    summarize(rows, fact_score, rule_score, total_usage)

    runs_dir = out_dir / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)
    report = runs_dir / f"{label}.json"
    report.write_text(
        json.dumps(
            {
                "label": label,
                "poc": args.poc,
                "split": args.split,
                "model": args.model,
                "caching": not args.no_cache,
                "started_at": started_at,
                "usage": total_usage.as_dict(),
                "cases": [row["case"].name for row in rows],
                "fact_level": fact_score.as_dict(),
                "rule_level": rule_score.as_dict(),
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"\n리포트 -> {report}")

    # 위험 오판(GREEN 또는 결함을 가리는 N/A)이 하나라도 있으면 실패로 끝낸다. CI에 걸 수 있다.
    return 1 if rule_score.false_greens or rule_score.false_nas else 0


def _accumulate(total: Score, part: Score) -> None:
    total.gold_total += part.gold_total
    total.predicted_total += part.predicted_total
    total.matched += part.matched
    total.value_correct += part.value_correct
    total.evidence_total += part.evidence_total
    total.evidence_offset_correct += part.evidence_offset_correct
    total.hallucinated += part.hallucinated
    total.activity_leaks += part.activity_leaks
    total.missed += part.missed
    total.spurious += part.spurious


if __name__ == "__main__":
    raise SystemExit(main())
