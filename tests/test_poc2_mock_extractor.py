from __future__ import annotations

import unittest

from app.extractors.poc2_mock_extractor import MockPoc2Extractor
from app.mapping.fact_schema import validate_facts
from app.mapping.ontology_mapper import RESPONSE_MEASURE_ROLES


INCIDENT_ONLY_FACT_IDS = {
    "F2-01-001",
    "F2-02-001",
    "F2-05-001",
    "F2-06-001",
    "F2-10-001",
}

NOTICE_FACT_IDS = {
    "F2-03-001",
    "F2-04-001",
    "F2-07-001",
    "F2-08-001",
    "F2-09-001",
    "F2-11-001",
    "F2-12-001",
}

ALL_FACT_IDS = INCIDENT_ONLY_FACT_IDS | NOTICE_FACT_IDS

SAMPLE_INCIDENT = {
    "incident_id": "synthetic-incident-001",
    "description": "합성 테스트 사고 기록입니다.",
}

SAMPLE_NOTIFICATION = {
    "notice_id": "synthetic-notice-001",
    "notice_text": "합성 테스트 통지문입니다.",
}


def _extract(*, notification=SAMPLE_NOTIFICATION) -> list[dict]:
    return MockPoc2Extractor().extract(
        analysis_id="poc2-test-001",
        controller_id="controller-test-001",
        controller_name="Test Controller",
        incident=SAMPLE_INCIDENT,
        notification=notification,
    )


class MockPoc2ExtractorTests(unittest.TestCase):
    def test_emits_exactly_the_ten_frozen_f2_fact_ids_when_notification_present(self):
        facts = _extract()
        fact_ids = {fact["fact_id"] for fact in facts}
        self.assertEqual(fact_ids, ALL_FACT_IDS)

    def test_emits_exactly_the_ten_frozen_f2_fact_ids_when_notification_absent(self):
        facts = _extract(notification=None)
        fact_ids = {fact["fact_id"] for fact in facts}
        self.assertEqual(fact_ids, ALL_FACT_IDS)

    def test_output_passes_validate_facts_unchanged_with_notification(self):
        facts = _extract()
        validated = validate_facts(facts)
        self.assertEqual(len(validated), len(facts))
        for original, checked in zip(facts, validated):
            self.assertEqual(original["fact_id"], checked["fact_id"])
            self.assertEqual(original["value_state"], checked["value_state"])
            self.assertEqual(original["value"], checked["value"])

    def test_output_passes_validate_facts_unchanged_without_notification(self):
        facts = _extract(notification=None)
        validated = validate_facts(facts)
        self.assertEqual(len(validated), len(facts))

    def test_all_facts_use_fact_1_0_schema_version(self):
        for fact in _extract():
            self.assertEqual(fact["schema_version"], "fact-1.0")

    def test_all_facts_retain_activity_id(self):
        for fact in _extract():
            self.assertTrue(fact["activity_id"], f"{fact['fact_id']} should retain activity_id")

    def test_every_fact_has_nonempty_evidence(self):
        for fact in _extract():
            self.assertIsInstance(fact["evidence"], list)
            self.assertGreater(len(fact["evidence"]), 0)

    def test_incident_side_facts_use_incident_or_derived_source_type(self):
        facts = {fact["fact_id"]: fact for fact in _extract()}
        for fact_id in ("F2-01-001", "F2-02-001", "F2-05-001", "F2-06-001"):
            self.assertEqual(facts[fact_id]["source_type"], "incident_record")

    def test_notice_side_facts_use_notification_notice_source_type_when_present(self):
        facts = {fact["fact_id"]: fact for fact in _extract()}
        for fact_id in NOTICE_FACT_IDS:
            self.assertEqual(facts[fact_id]["source_type"], "notification_notice")

    def test_f2_10_uses_a_source_type_allowed_by_the_frozen_schema(self):
        # app/mapping/fact_schema.py POC2_NOTICE_FACTS includes F2-10, so its
        # source_type must be "notification_notice" or "derived" (never
        # "incident_record") to pass validate_facts().
        facts = {fact["fact_id"]: fact for fact in _extract()}
        self.assertIn(
            facts["F2-10-001"]["source_type"], {"notification_notice", "derived"}
        )

    def test_all_facts_are_confirmed_when_notification_present(self):
        for fact in _extract():
            self.assertEqual(fact["value_state"], "confirmed")

    def test_notice_side_facts_are_absent_when_notification_missing(self):
        facts = {fact["fact_id"]: fact for fact in _extract(notification=None)}
        for fact_id in NOTICE_FACT_IDS:
            self.assertEqual(facts[fact_id]["value_state"], "absent")

    def test_incident_side_facts_remain_confirmed_when_notification_missing(self):
        facts = {fact["fact_id"]: fact for fact in _extract(notification=None)}
        for fact_id in INCIDENT_ONLY_FACT_IDS:
            self.assertEqual(facts[fact_id]["value_state"], "confirmed")

    def test_notification_missing_does_not_convert_absent_to_unknown_or_vice_versa(self):
        facts = {fact["fact_id"]: fact for fact in _extract(notification=None)}
        for fact_id in NOTICE_FACT_IDS:
            self.assertIn(facts[fact_id]["value_state"], {"absent"})
            self.assertNotEqual(facts[fact_id]["value_state"], "unknown")

    def test_f2_05_incident_date_and_f2_08_notice_incident_time_are_distinct(self):
        facts = {fact["fact_id"]: fact for fact in _extract()}
        self.assertNotEqual(facts["F2-05-001"]["value"], facts["F2-08-001"]["value"])

    def test_f2_08_not_present_does_not_borrow_f2_05_value(self):
        with_notification = {fact["fact_id"]: fact for fact in _extract()}
        without_notification = {
            fact["fact_id"]: fact for fact in _extract(notification=None)
        }
        # F2-05 (incidentDate) is unaffected by notification presence/absence.
        self.assertEqual(
            with_notification["F2-05-001"]["value"],
            without_notification["F2-05-001"]["value"],
        )
        # F2-08 becomes absent (value=None), never a copy of F2-05's value.
        self.assertIsNone(without_notification["F2-08-001"]["value"])

    def test_f2_10_measure_roles_are_within_frozen_allowed_set(self):
        facts = {fact["fact_id"]: fact for fact in _extract()}
        measures = facts["F2-10-001"]["value"]
        self.assertTrue(measures)
        for measure in measures:
            self.assertIn(measure["measure_role"], RESPONSE_MEASURE_ROLES)

    def test_extraction_is_deterministic(self):
        first = _extract()
        second = _extract()
        self.assertEqual(first, second)

    def test_ignores_incident_and_notification_text_content(self):
        baseline = _extract()
        different_text = MockPoc2Extractor().extract(
            analysis_id="poc2-test-001",
            controller_id="controller-test-001",
            controller_name="Test Controller",
            incident={
                "incident_id": "completely-different-id",
                "description": "완전히 다른 임의의 사고 설명 텍스트라도 결과는 동일해야 함.",
            },
            notification={
                "notice_id": "completely-different-notice-id",
                "notice_text": "완전히 다른 임의의 통지문 텍스트라도 결과는 동일해야 함.",
            },
        )
        self.assertEqual(baseline, different_text)

    def test_notification_omitted_does_not_fabricate_notice_content(self):
        facts = {fact["fact_id"]: fact for fact in _extract(notification=None)}
        for fact_id in NOTICE_FACT_IDS:
            self.assertIsNone(facts[fact_id]["value"])


if __name__ == "__main__":
    unittest.main()
