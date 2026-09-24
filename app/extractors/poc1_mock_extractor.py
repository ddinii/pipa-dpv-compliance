"""Deterministic mock PoC1 Fact extractor.

INTEGRATION-MOCK ONLY. This is a deterministic synthetic-data test double,
not an LLM simulator, not a natural-language extraction-quality
implementation, and not a legal reasoning component.

It ignores the content of ``policy_text`` entirely (no keyword parsing of
arbitrary policy text) and always returns the same fixed, structured
synthetic scenario covering F1-01 through F1-12. Its only purpose is to
validate the HTTP -> extractor boundary -> OntologyMapper -> P0RuleEngine
pipeline end-to-end before a real LLM extractor is integrated. See
docs/context/backend/EXTRACTOR_INTEGRATION.md and EXTRACTOR_DECISIONS.md.
"""

from __future__ import annotations

from typing import Any


def _evidence(field_path: str) -> list[dict[str, str]]:
    return [{"field_path": f"mock_fixture.{field_path}"}]


def _fact(
    fact_id: str,
    *,
    subject_id: str,
    activity_id: str | None,
    ontology_class: str,
    ontology_property: str | None,
    value: Any,
    field_path: str,
) -> dict[str, Any]:
    return {
        "fact_id": fact_id,
        "subject_id": subject_id,
        "activity_id": activity_id,
        "ontology_class": ontology_class,
        "ontology_property": ontology_property,
        "value": value,
        "value_state": "confirmed",
        "source_type": "policy_text",
        "evidence": _evidence(field_path),
        "schema_version": "fact-1.0",
    }


class MockPoC1Extractor:
    """Deterministic synthetic-data PoC1 extractor integration test double.

    ``extract()`` always returns the same fixed F1-01..F1-12 scenario
    regardless of ``policy_text`` content. Facts are scoped per invocation by
    the ``OntologyMapper`` instance namespace (bound to ``analysis_id``), so
    the fixed subject/activity identifiers below do not collide across
    requests.
    """

    def extract(
        self,
        *,
        analysis_id: str,
        controller_id: str,
        controller_name: str | None,
        policy_text: str,
    ) -> list[dict[str, Any]]:
        del analysis_id, controller_id, controller_name, policy_text

        return [
            _fact(
                "F1-01-001",
                subject_id="collect",
                activity_id="collect",
                ontology_class="CollectionAndUse",
                ontology_property=None,
                value=None,
                field_path="collection.activity",
            ),
            _fact(
                "F1-02-001",
                subject_id="collect",
                activity_id="collect",
                ontology_class="CollectionAndUse",
                ontology_property="hasPurpose",
                value="회원 가입 및 서비스 제공(합성 테스트 데이터)",
                field_path="collection.purpose",
            ),
            _fact(
                "F1-03-001",
                subject_id="collect",
                activity_id="collect",
                ontology_class="CollectionAndUse",
                ontology_property="hasRetention",
                value="회원 탈퇴 시까지(합성 테스트 데이터)",
                field_path="collection.retention_period",
            ),
            _fact(
                "F1-04-001",
                subject_id="collect",
                activity_id="collect",
                ontology_class="CollectionAndUse",
                ontology_property="hasRetention",
                value="회원 탈퇴",
                field_path="collection.retention_end",
            ),
            _fact(
                "F1-05-001",
                subject_id="provision",
                activity_id="provision",
                ontology_class="ThirdPartyProvision",
                ontology_property="hasRecipient",
                value="합성 테스트 제휴사(가상)",
                field_path="third_party_provision.recipient",
            ),
            _fact(
                "F1-06-001",
                subject_id="provision",
                activity_id="provision",
                ontology_class="ThirdPartyProvision",
                ontology_property="hasPersonalInformation",
                value=["수령인 이름", "배송지 주소"],
                field_path="third_party_provision.items",
            ),
            _fact(
                "F1-07-001",
                subject_id="provision",
                activity_id="provision",
                ontology_class="ThirdPartyProvision",
                ontology_property="hasPurpose",
                value="상품 배송(합성 테스트 데이터)",
                field_path="third_party_provision.purpose",
            ),
            _fact(
                "F1-08-001",
                subject_id="destroy",
                activity_id="destroy",
                ontology_class="Destruction",
                ontology_property="hasDestructionMethod",
                value="복구 불가능한 방법으로 즉시 삭제(합성 테스트 데이터)",
                field_path="destruction.method",
            ),
            _fact(
                "F1-09-001",
                subject_id="entrust",
                activity_id="entrust",
                ontology_class="EntrustedProcessing",
                ontology_property="hasProcessor",
                value="합성 테스트 수탁사(가상)",
                field_path="entrusted_processing.processor",
            ),
            _fact(
                "F1-10-001",
                subject_id="entrust",
                activity_id="entrust",
                ontology_class="EntrustedProcessing",
                ontology_property=None,
                value="서비스 인프라 운영 및 유지보수(합성 테스트 데이터)",
                field_path="entrusted_processing.task",
            ),
            # F1-11/F1-12 are global rights-related Facts and are exempt from
            # the normal activity_id requirement (activity_id=None).
            _fact(
                "F1-11-001",
                subject_id="user",
                activity_id=None,
                ontology_class="DataSubject",
                ontology_property="hasRight",
                value=["열람", "정정·삭제", "처리정지"],
                field_path="rights.list",
            ),
            _fact(
                "F1-12-001",
                subject_id="right",
                activity_id=None,
                ontology_class="DataSubjectRight",
                ontology_property="hasExerciseProcedure",
                value={"right": "열람", "procedure": "마이페이지 또는 고객센터를 통해 신청(합성 테스트 데이터)"},
                field_path="rights.procedure",
            ),
        ]
