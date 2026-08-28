from rdflib import Namespace, RDF

from app.models.request import ProcessingFact
from app.models.response import AppliedRule, ValidationResponse
from app.services.validator import ValidationRun


SH = Namespace("http://www.w3.org/ns/shacl#")
PIPA = Namespace("https://example.org/pipa-dpv#")

ARTICLE17_SHAPE = PIPA.Article17ConsentThirdPartyTransferShape


def is_article17_consent_case(fact: ProcessingFact) -> bool:
    return (
        fact.processing_type == "ThirdPartyTransfer"
        and fact.legal_basis == "Consent"
    )


def _article17_rule(run: ValidationRun) -> AppliedRule:
    rule_id = run.rules_graph.value(
        ARTICLE17_SHAPE,
        PIPA.ruleId,
    )

    legal_reference = run.rules_graph.value(
        ARTICLE17_SHAPE,
        PIPA.legalReference,
    )

    return AppliedRule(
        ruleId=str(
            rule_id
            or "PIPA-17-CONSENT-001"
        ),
        legalBasis=str(
            legal_reference
            or "개인정보 보호법 제17조제1항제1호 및 제2항"
        ),
    )


def build_result(
    fact: ProcessingFact,
    run: ValidationRun,
) -> ValidationResponse:

    if not is_article17_consent_case(fact):
        return ValidationResponse(
            status="HUMAN_REVIEW_REQUIRED",
            appliedRules=[],
            missingInformation=[],
            humanReviewRequired=True,
        )

    applied_rule = _article17_rule(run)

    if run.conforms:
        return ValidationResponse(
            status="PASS",
            appliedRules=[applied_rule],
            missingInformation=[],
            humanReviewRequired=False,
        )

    missing: list[str] = []

    for result in run.report_graph.subjects(
        RDF.type,
        SH.ValidationResult,
    ):
        source_shape = run.report_graph.value(
            result,
            SH.sourceShape,
        )

        if source_shape is None:
            continue

        label = run.rules_graph.value(
            source_shape,
            PIPA.missingLabel,
        )

        if (
            label is not None
            and str(label) not in missing
        ):
            missing.append(str(label))

    return ValidationResponse(
        status="NEEDS_INFORMATION",
        appliedRules=[applied_rule],
        missingInformation=missing,
        humanReviewRequired=False,
    )