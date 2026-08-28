from rdflib import Namespace, RDF

from app.models.request import ProcessingFact
from app.services.rdf_mapper import processing_fact_to_graph


PIPA = Namespace("https://example.org/pipa-dpv#")


def test_processing_fact_is_mapped_to_rdf():
    fact = ProcessingFact.model_validate(
        {
            "processingType": "ThirdPartyTransfer",
            "personalData": ["EmailAddress"],
            "purpose": "Advertising",
            "recipient": "외부 광고업체",
            "recipientRole": "ThirdParty",
            "legalBasis": "Consent",
            "retentionPeriod": "1년",
            "noticeItems": ["recipient"],
        }
    )

    graph = processing_fact_to_graph(fact)

    subjects = list(
        graph.subjects(
            RDF.type,
            PIPA.ProcessingFact,
        )
    )

    assert len(subjects) == 1

    subject = subjects[0]

    assert (
        subject,
        PIPA.processingType,
        PIPA.ThirdPartyTransfer,
    ) in graph

    assert (
        subject,
        PIPA.legalBasis,
        PIPA.Consent,
    ) in graph

    assert (
        subject,
        PIPA.personalData,
        PIPA.EmailAddress,
    ) in graph