from rdflib import Graph

from app.core.config import RULES_DIR


def load_rules() -> Graph:
    graph = Graph()

    rule_files = sorted(RULES_DIR.glob("*.ttl"))

    if not rule_files:
        raise RuntimeError(
            f"No SHACL rule files found in {RULES_DIR}"
        )

    for rule_file in rule_files:
        graph.parse(
            rule_file,
            format="turtle",
        )

    return graph