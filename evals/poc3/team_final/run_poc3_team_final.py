"""Re-run the 20 PoC3 evaluation scenarios against the current code (read-only on the evaluation package).

* Inputs: P3-01..P3-18 from the external evaluation folder, P3-19/P3-20 from
  ``evals/poc3/p3_19|20_explicit_absent.json`` (nothing else is substituted).
* Gold: the original rule-level answer sheet (CSV inside the evaluation ZIP, cross-checked
  with the original xlsx). Nothing is hardcoded.
* Execution: the real FastAPI endpoint ``POST /api/v1/compliance/design-check`` is called
  in-process (fastapi TestClient: no server, no network), and the statuses are read with the
  evaluation tool's own ``extract_api_predictions`` / ``normalize_status`` / metrics functions.

Usage (from the repository root):
    .venv/bin/python evals/poc3/team_final/run_poc3_team_final.py --eval-root <evaluation folder>
The evaluation folder is only read; the script writes into evals/poc3/team_final/.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import io
import json
import platform
import re
import subprocess
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path
import xml.etree.ElementTree as ET

sys.dont_write_bytecode = True          # never create __pycache__ in the evaluation folder
REPO = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))

EVAL_DIR_LABEL = "<EVAL_ROOT>"
RULES = ["P3-R01", "P3-R02", "P3-R03", "P3-R04", "P3-R05", "P3-R06", "P3-R08", "P3-R11"]
POC = "POC3"
NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_original_tool(eval_root: Path):
    spec = importlib.util.spec_from_file_location("pipa_evaluate_original", eval_root / "pipa_evaluate.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)      # definitions only (main() is guarded)
    return module


def gold_from_zip(zip_path: Path) -> dict[tuple[str, str], str]:
    with zipfile.ZipFile(zip_path) as z:
        text = z.read("정답표_360개_rule_level.csv").decode("utf-8-sig")
    return {(r["시나리오"], r["Rule_ID"]): r["정답상태"] for r in csv.DictReader(io.StringIO(text)) if r["PoC"].upper() == POC}


def gold_from_xlsx(xlsx_path: Path) -> dict[tuple[str, str], str]:
    with zipfile.ZipFile(xlsx_path) as z:
        shared = [
            "".join(t.text or "" for t in si.iter("{%s}t" % NS["m"]))
            for si in ET.fromstring(z.read("xl/sharedStrings.xml")).findall("m:si", NS)
        ]
        sheet = ET.fromstring(z.read("xl/worksheets/sheet1.xml"))
    rows = []
    for row in sheet.iter("{%s}row" % NS["m"]):
        cells = {}
        for c in row.findall("m:c", NS):
            v = c.find("m:v", NS)
            col = re.match(r"[A-Z]+", c.get("r")).group()
            cells[col] = shared[int(v.text)] if c.get("t") == "s" and v is not None else (v.text if v is not None else None)
        rows.append(cells)
    return {(r["B"], r["C"]): r["D"] for r in rows[1:] if r.get("A") == POC}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--eval-root", type=Path, required=True)
    args = parser.parse_args()
    root: Path = args.eval_root.resolve()

    head = subprocess.check_output(["git", "-C", str(REPO), "rev-parse", "HEAD"], text=True).strip()
    # The output folder of this very script is excluded; anything else would be a real change.
    dirty = [
        line for line in subprocess.check_output(["git", "-C", str(REPO), "status", "--porcelain"], text=True).splitlines()
        if "evals/poc3/team_final/" not in line
    ]

    tool = load_original_tool(root)
    zip_path = root / "평가입력팩.zip"
    xlsx_path = root / "정답표_360개_rule_level.xlsx"
    gold = gold_from_zip(zip_path)
    gold_x = gold_from_xlsx(xlsx_path)
    assert len(gold) == 160 and gold == gold_x, "gold sources disagree"

    inputs = {}
    for i in range(1, 21):
        sid = f"P3-{i:02d}"
        if i in (19, 20):
            inputs[sid] = (REPO / "evals" / "poc3" / f"p3_{i}_explicit_absent.json", f"evals/poc3/p3_{i}_explicit_absent.json", "repository explicit_absent")
        else:
            p = root / "PoC3_설계JSON_20건" / f"{sid}.json"
            inputs[sid] = (p, f"{EVAL_DIR_LABEL}/PoC3_설계JSON_20건/{sid}.json", "external original")

    from fastapi.testclient import TestClient
    from app.main import app
    client = TestClient(app)

    rows, pred, mismatch_details = [], {}, []
    for sid, (path, label, _source) in inputs.items():
        payload = json.loads(path.read_text(encoding="utf-8"))
        response = client.post("/api/v1/compliance/design-check", json=payload)
        assert response.status_code == 200, (sid, response.status_code, response.text[:200])
        data = response.json()
        statuses = tool.extract_api_predictions(data, set(RULES))     # same normalisation as the original tool
        raw = {r["rule_id"]: r["status"] for r in data["results"]}
        for rule in RULES:
            expected = tool.normalize_status(gold[(sid, rule)])
            actual = statuses[rule]
            pred[(POC, sid, rule)] = actual
            ok = expected == actual
            rows.append([sid, rule, expected, actual, raw[rule], "1" if ok else "0", label])
            if not ok:
                item = next(r for r in data["results"] if r["rule_id"] == rule)
                mismatch_details.append({
                    "scenario": sid, "rule": rule, "expected": expected, "actual": actual,
                    "instance_reasons": [i.get("reason") for i in item.get("instance_results", [])],
                })
    assert len(rows) == 160

    keys = [(POC, s, r) for s in inputs for r in RULES]
    gold_n = {(POC, s, r): tool.normalize_status(v) for (s, r), v in gold.items()}
    metrics = tool.calc_metrics(keys, gold_n, pred)
    far_frr = tool.calc_far_frr(keys, gold_n, pred)
    correct = sum(r[5] == "1" for r in rows)

    csv_path = OUT / "poc3_team_final_rule_results.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["시나리오", "Rule_ID", "정답", "예측", "API_status", "일치(1/0)", "입력파일"])
        w.writerows(rows)

    previous = {}
    prev_path = REPO / "evals" / "poc3" / "results_v2" / "A_original_inputs_original_gold.json"
    if prev_path.exists():
        previous = {(d["scenario"], d["rule"]): d["actual"] for d in json.loads(prev_path.read_text(encoding="utf-8"))["rule_results"]}
    diffs = [
        {"scenario": s, "rule": r, "previous": previous[(s, r)], "current": pred[(POC, s, r)]}
        for (s, r) in previous if previous[(s, r)] != pred[(POC, s, r)]
    ]

    def pkg(name: str) -> str:
        try:
            from importlib.metadata import version
            return version(name)
        except Exception:
            return "unknown"

    manifest = {
        "scope": "PoC3 team submission re-evaluation (series A): original inputs and original answer sheet; only P3-19/P3-20 use the repository explicit_absent JSON",
        "executed_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "git_head": head,
        "git_status_clean_at_run": not dirty,
        "git_status_note": "status excluding the script's own output folder evals/poc3/team_final/",
        "git_status_lines": dirty,
        "environment": {
            "python": platform.python_version(), "platform": platform.platform(),
            "packages": {n: pkg(n) for n in ("fastapi", "rdflib", "pyshacl", "pydantic", "httpx")},
        },
        "command": "cd <repository root> && .venv/bin/python evals/poc3/team_final/run_poc3_team_final.py --eval-root <EVAL_ROOT>",
        "execution_path": "fastapi TestClient (in-process, no server, no network) -> POST /api/v1/compliance/design-check -> run_design_check (Fact builder -> Ontology mapper -> P0 Rule Engine)",
        "evaluation_tool_functions_reused": ["normalize_status", "extract_api_predictions", "calc_metrics", "calc_far_frr"],
        "eval_root_note": "<EVAL_ROOT> is the external, read-only evaluation package folder PIPA_PoC_60시나리오_입력원문_및_정답표 (not part of this repository)",
        "inputs": [
            {"scenario": s, "path": label, "source": src, "sha256": sha256(p)} for s, (p, label, src) in inputs.items()
        ],
        "gold": {
            "used": f"{EVAL_DIR_LABEL}/평가입력팩.zip :: 정답표_360개_rule_level.csv (PoC3 rows)",
            "zip_sha256": sha256(zip_path),
            "csv_member_sha256": hashlib.sha256(zipfile.ZipFile(zip_path).read("정답표_360개_rule_level.csv")).hexdigest(),
            "cross_checked_with": f"{EVAL_DIR_LABEL}/정답표_360개_rule_level.xlsx",
            "xlsx_sha256": sha256(xlsx_path),
            "zip_and_xlsx_identical_for_poc3": True,
            "rows": len(gold),
            "corrections_applied": "none",
        },
        "evaluation_tool_script_sha256": sha256(root / "pipa_evaluate.py"),
        "results": {
            "csv": "evals/poc3/team_final/poc3_team_final_rule_results.csv",
            "csv_sha256": sha256(csv_path),
            "rows": len(rows), "correct": correct, "accuracy": round(correct / len(rows), 6),
            "macro_f1": metrics["macro_f1"],
            "far": far_frr["FAR"], "frr": far_frr["FRR"],
            "far_counts": f'{far_frr["FA_false_accept"]}/{far_frr["negative_amber_red"]}',
            "frr_counts": f'{far_frr["FR_false_reject"]}/{far_frr["positive_green"]}',
            "confusion": metrics["confusion"],
            "mismatches": mismatch_details,
            "compared_with_previous_series_A_file": {
                "file": "evals/poc3/results_v2/A_original_inputs_original_gold.json",
                "file_sha256": sha256(prev_path) if prev_path.exists() else None,
                "verdict_differences": diffs,
            },
        },
    }
    (OUT / "poc3_team_final_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{correct}/{len(rows)} accuracy={correct / len(rows):.4%} macro_f1={metrics['macro_f1']} far={far_frr['FAR']} ({far_frr['FA_false_accept']}/{far_frr['negative_amber_red']}) frr={far_frr['FRR']} ({far_frr['FR_false_reject']}/{far_frr['positive_green']})")
    print("mismatches:", [(m["scenario"], m["rule"], m["expected"], m["actual"]) for m in mismatch_details])
    print("differences vs previous series A file:", diffs)
    return 0


if __name__ == "__main__":
    sys.exit(main())
