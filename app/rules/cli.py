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
    args = parser.parse_args()

    graph = Graph().parse(args.rdf_file, format="turtle")
    engine = P0RuleEngine()
    results = [result.to_dict() for result in engine.evaluate_graph(graph, poc=args.poc)]
    print(json.dumps({"results": results}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
