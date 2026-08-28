from dataclasses import dataclass

from pyshacl import validate
from rdflib import Graph

from app.core.config import ONTOLOGY_PATH
from app.services.rule_loader import load_rules


@dataclass
class ValidationRun:
    conforms: bool
    report_graph: Graph
    report_text: str
    rules_graph: Graph


def validate_graph(data_graph: Graph) -> ValidationRun:
    rules_graph = load_rules()

    ontology_graph = Graph()
    ontology_graph.parse(
        ONTOLOGY_PATH,
        format="turtle",
    )

    conforms, report_graph, report_text = validate(
        data_graph=data_graph,
        shacl_graph=rules_graph,
        ont_graph=ontology_graph,
        inference="rdfs",
        abort_on_first=False,
        allow_infos=False,
        allow_warnings=False,
        meta_shacl=False,
        advanced=True,
        debug=False,
    )

    return ValidationRun(
        conforms=bool(conforms),
        report_graph=report_graph,
        report_text=str(report_text),
        rules_graph=rules_graph,
    )