"""Deterministic mock PoC2 Fact extractor.

INTEGRATION-MOCK ONLY. This is a deterministic synthetic-data test double,
not an LLM simulator, not a natural-language extraction-quality
implementation, and not a legal reasoning component.

It ignores the content of ``incident`` and ``notification`` entirely (no
keyword parsing of arbitrary incident/notice text) and always returns the
same fixed, structured synthetic scenario covering F2-01 through F2-10. The
only input it inspects structurally is whether ``notification`` was provided
at all -- it never fabricates a NotificationNotice when it is absent. Its
only purpose is to validate the HTTP -> extractor boundary -> OntologyMapper
-> P0RuleEngine pipeline end-to-end before a real LLM extractor is
integrated. See docs/context/backend/EXTRACTOR_INTEGRATION.md and
EXTRACTOR_DECISIONS.md.
"""

from __future__ import annotations

from typing import Any


_INCIDENT_ID = "breach-incident"
_NOTICE_ID = "breach-notice"

# F2-05 (actual incidentDate) and F2-08 (notice-stated incident time) are
# deliberately different fixed literals. F2-08 must never be derived from
# F2-05 (docs/context/backend/EXTRACTOR_DECISIONS.md #2).
_INCIDENT_DATE = "2026-08-01T09:00:00+09:00"
_DETECTION_DATE = "2026-08-01T15:00:00+09:00"
_NOTIFICATION_DATE = "2026-08-03T10:00:00+09:00"
_NOTICE_STATED_INCIDENT_TIME = "2026-08-02T18:00:00+09:00"

# F2-02 actual affected items vs F2-04 notice-mentioned items intentionally
# differ (전화번호 omitted from the notice) so the fixture is not tuned for an
# all-GREEN P2-R02 result; it is an integration-contract double, not a
# compliance-scoring demo.
_AFFECTED_ITEMS = [
    {"item_name": "이름"},
    {"item_name": "이메일 주소"},
    {"item_name": "전화번호"},
]
_NOTICE_MENTIONED_ITEMS = [
    {"item_name": "이름"},
    {"item_name": "이메일 주소"},
]


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
    value_state: str,
    source_type: str,
    field_path: str,
) -> dict[str, Any]:
    return {
        "fact_id": fact_id,
        "subject_id": subject_id,
        "activity_id": activity_id,
        "ontology_class": ontology_class,
        "ontology_property": ontology_property,
        "value": value,
        "value_state": value_state,
        "source_type": source_type,
        "evidence": _evidence(field_path),
        "schema_version": "fact-1.0",
    }


class MockPoc2Extractor:
    """Deterministic synthetic-data PoC2 extractor integration test double.

    ``extract()`` always returns the same fixed F2-01..F2-10 scenario
    regardless of ``incident``/``notification`` content. Only the presence or
    absence of ``notification`` (a structural check, not text parsing) is
    used, to decide whether the notice-side Facts (F2-03, F2-04, F2-07,
    F2-08, F2-09) are ``confirmed`` or ``absent``.
    """

    def extract(
        self,
        *,
        analysis_id: str,
        controller_id: str,
        controller_name: str | None,
        incident: dict[str, Any],
        notification: dict[str, Any] | None,
    ) -> list[dict[str, Any]]:
        del analysis_id, controller_id, controller_name, incident

        has_notification = notification is not None

        facts: list[dict[str, Any]] = [
            _fact(
                "F2-01-001",
                subject_id=_INCIDENT_ID,
                activity_id=_INCIDENT_ID,
                ontology_class="DataBreachIncident",
                ontology_property=None,
                value=None,
                value_state="confirmed",
                source_type="incident_record",
                field_path="incident.record",
            ),
            _fact(
                "F2-02-001",
                subject_id=_INCIDENT_ID,
                activity_id=_INCIDENT_ID,
                ontology_class="DataBreachIncident",
                ontology_property="affectsPersonalInformation",
                value=_AFFECTED_ITEMS,
                value_state="confirmed",
                source_type="incident_record",
                field_path="incident.affected_items",
            ),
            _fact(
                "F2-05-001",
                subject_id=_INCIDENT_ID,
                activity_id=_INCIDENT_ID,
                ontology_class="DataBreachIncident",
                ontology_property="incidentDate",
                value=_INCIDENT_DATE,
                value_state="confirmed",
                source_type="incident_record",
                field_path="incident.incident_date",
            ),
            _fact(
                "F2-06-001",
                subject_id=_INCIDENT_ID,
                activity_id=_INCIDENT_ID,
                ontology_class="DataBreachIncident",
                ontology_property="detectionDate",
                value=_DETECTION_DATE,
                value_state="confirmed",
                source_type="incident_record",
                field_path="incident.detection_date",
            ),
            # F2-10 is required only by frozen source_type
            # {"notification_notice", "derived"} per
            # app/mapping/fact_schema.py POC2_NOTICE_FACTS, so "derived" is
            # used here rather than "incident_record".
            _fact(
                "F2-10-001",
                subject_id=_INCIDENT_ID,
                activity_id=_INCIDENT_ID,
                ontology_class="DataBreachIncident",
                ontology_property="hasResponseMeasure",
                value=[
                    {
                        "measure_role": "data_subject_guidance",
                        "text": "정보주체 안내(합성 테스트 데이터)",
                    },
                    {
                        "measure_role": "controller_response",
                        "text": "처리자 대응 조치(합성 테스트 데이터)",
                    },
                ],
                value_state="confirmed",
                source_type="derived",
                field_path="incident.response_measures",
            ),
        ]

        if has_notification:
            facts.extend(
                [
                    _fact(
                        "F2-03-001",
                        subject_id=_INCIDENT_ID,
                        activity_id=_INCIDENT_ID,
                        ontology_class="DataBreachIncident",
                        ontology_property="hasNotificationNotice",
                        value={"notice_id": _NOTICE_ID},
                        value_state="confirmed",
                        source_type="notification_notice",
                        field_path="notification.notice_id",
                    ),
                    _fact(
                        "F2-04-001",
                        subject_id=_NOTICE_ID,
                        activity_id=_INCIDENT_ID,
                        ontology_class="NotificationNotice",
                        ontology_property="mentionsPersonalInformation",
                        value=_NOTICE_MENTIONED_ITEMS,
                        value_state="confirmed",
                        source_type="notification_notice",
                        field_path="notification.mentioned_items",
                    ),
                    _fact(
                        "F2-07-001",
                        subject_id=_INCIDENT_ID,
                        activity_id=_INCIDENT_ID,
                        ontology_class="DataBreachIncident",
                        ontology_property="notificationDate",
                        value=_NOTIFICATION_DATE,
                        value_state="confirmed",
                        source_type="notification_notice",
                        field_path="notification.notification_date",
                    ),
                    _fact(
                        "F2-08-001",
                        subject_id=_NOTICE_ID,
                        activity_id=_INCIDENT_ID,
                        ontology_class="NotificationNotice",
                        ontology_property=None,
                        value=_NOTICE_STATED_INCIDENT_TIME,
                        value_state="confirmed",
                        source_type="notification_notice",
                        field_path="notification.stated_incident_time",
                    ),
                    _fact(
                        "F2-09-001",
                        subject_id=_NOTICE_ID,
                        activity_id=_INCIDENT_ID,
                        ontology_class="NotificationNotice",
                        ontology_property="hasIncidentCircumstances",
                        value="합성 테스트용 유출 경위 설명(가상 시나리오)",
                        value_state="confirmed",
                        source_type="notification_notice",
                        field_path="notification.circumstances",
                    ),
                ]
            )
        else:
            # notification omitted at the request level. Represent this as
            # explicit absence rather than fabricating a NotificationNotice
            # (docs/context/backend/EXTRACTOR_DECISIONS.md #6). "derived" is
            # used because there is no actual notification_notice document to
            # cite as provenance.
            for fact_id, subject_id, ontology_class, ontology_property, field_path in (
                ("F2-03-001", _INCIDENT_ID, "DataBreachIncident", "hasNotificationNotice", "notification"),
                ("F2-04-001", _NOTICE_ID, "NotificationNotice", "mentionsPersonalInformation", "notification"),
                ("F2-07-001", _INCIDENT_ID, "DataBreachIncident", "notificationDate", "notification"),
                ("F2-08-001", _NOTICE_ID, "NotificationNotice", None, "notification"),
                ("F2-09-001", _NOTICE_ID, "NotificationNotice", "hasIncidentCircumstances", "notification"),
            ):
                facts.append(
                    _fact(
                        fact_id,
                        subject_id=subject_id,
                        activity_id=_INCIDENT_ID,
                        ontology_class=ontology_class,
                        ontology_property=ontology_property,
                        value=None,
                        value_state="absent",
                        source_type="derived",
                        field_path=field_path,
                    )
                )

        return facts
