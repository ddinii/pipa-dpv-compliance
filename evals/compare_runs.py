"""여러 추출 실행을 나란히 놓고 본다.

모델 비교(Opus vs Sonnet)와 캐시 효과 측정은 실행 결과가 서로 남아 있어야 한다.
`run_extraction.py`가 실행마다 `<out-dir>/runs/<label>.json`을 남기므로, 이
스크립트는 그 디렉터리를 읽어 표로 만든다. API를 부르지 않는다.

실행:
    python evals/compare_runs.py evals/poc1/predictions/runs
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

# 표에 세울 지표. (표시 이름, 경로, 포맷, 클수록 좋은가)
COLUMNS: list[tuple[str, tuple[str, ...], str, bool]] = [
    ("F1", ("fact_level", "f1"), ".3f", True),
    ("정밀도", ("fact_level", "precision"), ".3f", True),
    ("재현율", ("fact_level", "recall"), ".3f", True),
    ("값정확도", ("fact_level", "value_accuracy"), ".3f", True),
    ("환각률", ("fact_level", "hallucination_rate"), ".3f", False),
    ("혼합률", ("fact_level", "activity_leak_rate"), ".3f", False),
    ("Rule일치", ("rule_level", "agreement"), ".3f", True),
    ("위험오판", ("rule_level", "false_green_rate"), ".3f", False),
]

USAGE_COLUMNS: list[tuple[str, tuple[str, ...], str]] = [
    ("호출", ("usage", "calls"), ",d"),
    ("입력토큰", ("usage", "total_input_tokens"), ",d"),
    ("출력토큰", ("usage", "output_tokens"), ",d"),
    ("캐시적중", ("usage", "cache_hit_rate"), ".0%"),
]


def dig(payload: dict, path: tuple[str, ...]) -> Any:
    for key in path:
        if not isinstance(payload, dict) or key not in payload:
            return None
        payload = payload[key]
    return payload


def cell(value: Any, spec: str) -> str:
    if value is None:
        return "-"
    try:
        return format(value, spec)
    except (TypeError, ValueError):
        return str(value)


def load_runs(directory: Path) -> list[dict]:
    files = sorted(directory.glob("*.json"))
    runs = []
    for path in files:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            print(f"건너뜀 {path.name}: {exc}", file=sys.stderr)
            continue
        payload.setdefault("label", path.stem)
        runs.append(payload)
    return runs


def table(runs: list[dict], columns: list[tuple]) -> str:
    label_width = max([len("실행")] + [len(run["label"]) for run in runs])
    widths = [max(len(name), 8) for name, *_ in columns]

    header = "  " + "실행".ljust(label_width)
    for (name, *_), width in zip(columns, widths):
        header += " " + name.rjust(width)
    lines = [header, "  " + "-" * (len(header) - 2)]

    for run in runs:
        line = "  " + run["label"].ljust(label_width)
        for (_, path, spec, *_), width in zip(columns, widths):
            line += " " + cell(dig(run, path), spec).rjust(width)
        lines.append(line)
    return "\n".join(lines)


def best_and_worst(runs: list[dict]) -> str:
    """가장 중요한 지표 하나로 순위를 매긴다.

    F1이 아니라 위험 오판율이다. Fact를 몇 개 맞췄는지보다 "추출 오류가 판정을
    뒤집는가"가 실무 영향이기 때문이다 (evals/README.md 채점 지표 참고).
    """
    scored = [
        (run["label"], dig(run, ("rule_level", "false_green_rate")))
        for run in runs
        if dig(run, ("rule_level", "false_green_rate")) is not None
    ]
    if not scored:
        return ""
    scored.sort(key=lambda item: item[1])
    lines = ["", "위험 오판율 기준 (낮을수록 좋음)"]
    for rank, (label, value) in enumerate(scored, start=1):
        lines.append(f"  {rank}. {label}  {value:.3f}")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path, help="runs 디렉터리")
    args = parser.parse_args()

    if not args.directory.is_dir():
        print(f"디렉터리가 없습니다: {args.directory}")
        print("먼저 python evals/run_extraction.py 를 돌려 실행 결과를 만드세요.")
        return 2

    runs = load_runs(args.directory)
    if not runs:
        print(f"{args.directory}에 실행 결과가 없습니다.")
        return 2

    print(f"실행 {len(runs)}건 · {args.directory}")
    print()
    print("추출 품질")
    print(table(runs, COLUMNS))
    print()
    print("호출량")
    print(table(runs, USAGE_COLUMNS))
    print(best_and_worst(runs))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
