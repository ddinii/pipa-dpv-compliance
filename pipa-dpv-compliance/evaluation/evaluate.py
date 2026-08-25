"""
Model A (LLM Only) vs Model B (LLM + PIPA-DPV Ontology + Rule Engine) 비교 평가

주제 제안 문서의 실증 계획:
  - 실제 기업 처리방침 20~50개 확보, 전문가가 gold standard 라벨링
  - 지표: Precision/Recall(필수항목 누락 탐지), 근거조문 정확도,
          Hallucination률, 사람 판단과의 일치율, 평균 검토시간

이 스크립트는 PoC 단계의 평가 골격입니다. 실제 대규모 평가 전에
data/gold_standard/ 에 전문가 라벨(CSV)을 채워 넣어야 합니다.

실행:
    python -m evaluation.evaluate --gold data/gold_standard/gold_labels_template.csv
"""

from __future__ import annotations
import argparse
import csv
import os
import time
from collections import defaultdict

from backend.extraction.llm_extractor import get_extractor
from backend.rules.rule_engine import evaluate_policy

SAMPLE_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "sample_policies")


def load_gold_labels(path: str) -> dict[str, dict[str, str]]:
    """policy_file -> {rule_id: gold_verdict} 형태로 로드"""
    gold: dict[str, dict[str, str]] = defaultdict(dict)
    with open(path, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            gold[row["policy_file"]][row["rule_id"]] = row["gold_verdict"]
    return gold


def run_model_b(policy_text: str):
    """Model B: LLM 추출 -> 온톨로지 매핑(Fact 구조) -> Rule Engine 판정"""
    start = time.time()
    extractor = get_extractor()
    facts = extractor.extract(policy_text)
    report = evaluate_policy(facts)
    elapsed = time.time() - start
    predictions = {r.rule_id: r.verdict.value for r in report.results if r.rule_id != "R11"}
    return predictions, elapsed


def compute_agreement(predictions: dict[str, str], gold: dict[str, str]) -> tuple[int, int]:
    """(일치 개수, 전체 개수) 반환. AMBER는 '사람 판단 위임'이므로 정오답 채점에서
    엄격 일치가 아닌 별도 카테고리로 다룰 수도 있음 — 여기서는 단순 exact match."""
    matched = sum(1 for rule_id, gold_v in gold.items() if predictions.get(rule_id) == gold_v)
    return matched, len(gold)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--gold", default=os.path.join(
        os.path.dirname(__file__), "..", "data", "gold_standard", "gold_labels_template.csv"
    ))
    args = parser.parse_args()

    gold_by_file = load_gold_labels(args.gold)

    total_matched, total_rules, total_time = 0, 0, 0.0

    print(f"{'파일':40s} {'일치':>6s} {'전체':>6s} {'일치율':>8s} {'소요(s)':>8s}")
    print("-" * 75)

    for policy_file, gold in gold_by_file.items():
        policy_path = os.path.join(SAMPLE_DIR, policy_file)
        if not os.path.exists(policy_path):
            print(f"[경고] {policy_file} 을(를) data/sample_policies 에서 찾을 수 없음. 건너뜀.")
            continue

        with open(policy_path, encoding="utf-8") as f:
            text = f.read()

        predictions, elapsed = run_model_b(text)
        matched, n = compute_agreement(predictions, gold)

        total_matched += matched
        total_rules += n
        total_time += elapsed

        print(f"{policy_file:40s} {matched:6d} {n:6d} {matched/n*100:7.1f}% {elapsed:8.2f}")

    print("-" * 75)
    if total_rules:
        print(f"전체 일치율 (Model B, 사람 판단과의 일치율 근사): "
              f"{total_matched}/{total_rules} = {total_matched/total_rules*100:.1f}%")
        print(f"평균 처리 시간: {total_time/len(gold_by_file):.2f}초/건")

    print(
        "\nNOTE: 현재 MockExtractor 사용 시 정확도가 매우 낮게 나올 수 있습니다. "
        "실제 평가를 위해서는 ANTHROPIC_API_KEY를 설정해 ClaudeExtractor로 실행하고, "
        "Model A(LLM에게 직접 위반여부까지 판정시킨 결과)와의 비교 로직을 추가하세요."
    )


if __name__ == "__main__":
    main()
