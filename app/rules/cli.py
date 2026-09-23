from __future__ import annotations

import argparse
import json
from pathlib import Path

from rdflib import Graph

from app.rules.engine import P0RuleEngine


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate PIPA P0 rules against a Turtle RDF graph")
    parser.add_argument("rdf_file", type=Path)
    parser.add_argument("--poc", choices=["poc1", "poc2", "poc3"], default=None)
    parser.add_argument(
        "--facts",
        type=Path,
        default=None,
        help="Optional fact-1.0 JSON file. When supplied, frozen value_state and Rule↔Fact coverage are enforced.",
    )
    args = parser.parse_args()

    graph = Graph().parse(args.rdf_file, format="turtle")
    facts = None
    if args.facts is not None:
        payload = json.loads(args.facts.read_text(encoding="utf-8-sig"))
        facts = payload.get("facts") if isinstance(payload, dict) else payload
        if not isinstance(facts, list):
            parser.error("--facts JSON must be an array or an object containing a 'facts' array")

    engine = P0RuleEngine()
    results = [
        result.to_dict()
        for result in engine.evaluate_graph(graph, poc=args.poc, facts=facts)
    ]
    print(json.dumps({"results": results}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
