from urllib.parse import quote
from uuid import uuid4

from rdflib import Graph, Literal, Namespace, RDF, URIRef

from app.models.request import ProcessingFact


PIPA = Namespace("https://example.org/pipa-dpv#")


def _local_term(value: str) -> URIRef:
    encoded = quote(value, safe="")
    return URIRef(f"{PIPA}{encoded}")


def processing_fact_to_graph(fact: ProcessingFact) -> Graph:
    graph = Graph()

    graph.bind("pipa", PIPA)

    subject = URIRef(
        f"urn:processing-fact:{uuid4()}"
    )

    graph.add(
        (
            subject,
            RDF.type,
            PIPA.ProcessingFact,
        )
    )

    graph.add(
        (
            subject,
            PIPA.processingType,
            _local_term(fact.processing_type),
        )
    )

    graph.add(
        (
            subject,
            PIPA.legalBasis,
            _local_term(fact.legal_basis),
        )
    )

    for item in fact.personal_data:
        graph.add(
            (
                subject,
                PIPA.personalData,
                _local_term(item),
            )
        )

    if fact.purpose:
        graph.add(
            (
                subject,
                PIPA.purpose,
                _local_term(fact.purpose),
            )
        )

    if fact.recipient:
        graph.add(
            (
                subject,
                PIPA.recipient,
                Literal(fact.recipient),
            )
        )

    if fact.recipient_role:
        graph.add(
            (
                subject,
                PIPA.recipientRole,
                _local_term(fact.recipient_role),
            )
        )

    if fact.retention_period:
        graph.add(
            (
                subject,
                PIPA.retentionPeriod,
                Literal(fact.retention_period),
            )
        )

    for notice_item in fact.notice_items:
        graph.add(
            (
                subject,
                PIPA.noticeItem,
                Literal(notice_item),
            )
        )

    return graph