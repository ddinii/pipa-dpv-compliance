"""Deterministic mock PoC1 Fact extractor.

INTEGRATION-MOCK ONLY. This is a deterministic synthetic-data test double,
not an LLM simulator, not a natural-language extraction-quality
implementation, and not a legal reasoning component.

It ignores the content of ``policy_text`` entirely (no keyword parsing of
arbitrary policy text) and always returns the same fixed, structured
synthetic scenario covering F1-01 through F1-12, plus the v1.1
cross-border transfer (F1-13..F1-19), privacy officer (F1-20/F1-21) and
collection item (F1-22) Facts. Its only purpose is to
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

    ``extract()`` always returns the same fixed F1-01..F1-12 (+ F1-13..F1-22) scenario
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
            # v1.1 cross-border transfer (F1-13..F1-19). The activity also
            # carries its own retention (F1-03/F1-04) because P1-R02 checks
            # every processing activity.
            _fact(
                "F1-03-002",
                subject_id="crossborder",
                activity_id="crossborder",
                ontology_class="CrossBorderTransfer",
                ontology_property="hasRetention",
                value="이전 목적 달성 시까지(합성 테스트 데이터)",
                field_path="cross_border_transfer.retention_period",
            ),
            _fact(
                "F1-04-002",
                subject_id="crossborder",
                activity_id="crossborder",
                ontology_class="CrossBorderTransfer",
                ontology_property="hasRetention",
                value="회원 탈퇴",
                field_path="cross_border_transfer.retention_end",
            ),
            _fact(
                "F1-13-001",
                subject_id="crossborder",
                activity_id="crossborder",
                ontology_class="CrossBorderTransfer",
                ontology_property="hasDestinationCountry",
                value="미국(US)",
                field_path="cross_border_transfer.country",
            ),
            _fact(
                "F1-14-001",
                subject_id="crossborder",
                activity_id="crossborder",
                ontology_class="CrossBorderTransfer",
                ontology_property="hasPersonalInformation",
                value=["회원 식별정보", "서비스 이용기록"],
                field_path="cross_border_transfer.items",
            ),
            _fact(
                "F1-15-001",
                subject_id="crossborder",
                activity_id="crossborder",
                ontology_class="CrossBorderTransfer",
                ontology_property="hasPurpose",
                value="클라우드 서버 보관(합성 테스트 데이터)",
                field_path="cross_border_transfer.purpose",
            ),
            _fact(
                "F1-16-001",
                subject_id="crossborder",
                activity_id="crossborder",
                ontology_class="CrossBorderTransfer",
                ontology_property="hasTransferRecipient",
                value="Example Cloud Inc.",
                field_path="cross_border_transfer.recipient",
            ),
            _fact(
                "F1-17-001",
                subject_id="crossborder",
                activity_id="crossborder",
                ontology_class="OverseasRecipient",
                ontology_property="hasContact",
                value=["privacy@example.com"],
                field_path="cross_border_transfer.recipient_contact",
            ),
            _fact(
                "F1-18-001",
                subject_id="crossborder",
                activity_id="crossborder",
                ontology_class="CrossBorderTransfer",
                ontology_property="hasTransferTimingAndMethod",
                value="서비스 이용 시점에 네트워크로 전송(합성 테스트 데이터)",
                field_path="cross_border_transfer.timing_and_method",
            ),
            _fact(
                "F1-19-001",
                subject_id="crossborder",
                activity_id="crossborder",
                ontology_class="CrossBorderTransfer",
                ontology_property="hasTransferRefusalProcedure",
                value="보호책임자에게 이메일로 거부 의사를 알릴 수 있음(합성 테스트 데이터)",
                field_path="cross_border_transfer.refusal_procedure",
            ),
            # v1.1 Facts. F1-20/F1-21 are document-scope like F1-11/F1-12.
            # The officer name and contact are synthetic values.
            _fact(
                "F1-20-001",
                subject_id="privacy-officer",
                activity_id=None,
                ontology_class="PersonalInformationController",
                ontology_property="hasPrivacyOfficer",
                value={"name": "홍길동", "department": "개인정보보호팀"},
                field_path="privacy_officer.identity",
            ),
            _fact(
                "F1-21-001",
                subject_id="privacy-officer",
                activity_id=None,
                ontology_class="PrivacyOfficer",
                ontology_property="hasContact",
                value=["02-0000-0000", "privacy@example.com"],
                field_path="privacy_officer.contact",
            ),
            _fact(
                "F1-22-001",
                subject_id="collect",
                activity_id="collect",
                ontology_class="CollectionAndUse",
                ontology_property="hasPersonalInformation",
                value=["이름", "이메일 주소", "휴대전화번호"],
                field_path="collection.items",
            ),
        ]
