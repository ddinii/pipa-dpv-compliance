from __future__ import annotations

import unittest

from app.extractors.poc1_mock_extractor import MockPoC1Extractor
from app.mapping.fact_schema import validate_facts


EXPECTED_FACT_IDS = {
    "F1-01-001",
    "F1-02-001",
    "F1-03-001",
    "F1-04-001",
    "F1-05-001",
    "F1-06-001",
    "F1-07-001",
    "F1-08-001",
    "F1-09-001",
    "F1-10-001",
    "F1-11-001",
    "F1-12-001",
    "F1-03-002",
    "F1-04-002",
    "F1-13-001",
    "F1-14-001",
    "F1-15-001",
    "F1-16-001",
    "F1-17-001",
    "F1-18-001",
    "F1-19-001",
    "F1-20-001",
    "F1-21-001",
    "F1-22-001",
    "F1-23-001",
    "F1-24-001",
    "F1-25-001",
}

GLOBAL_SCOPE_FACT_IDS = {"F1-11-001", "F1-12-001", "F1-20-001", "F1-21-001", "F1-23-001", "F1-24-001", "F1-25-001"}


def _extract() -> list[dict]:
    return MockPoC1Extractor().extract(
        analysis_id="poc1-test-001",
        controller_id="controller-test-001",
        controller_name="Test Controller",
        policy_text="합성 테스트 정책 텍스트입니다.",
    )


class MockPoC1ExtractorTests(unittest.TestCase):
    def test_emits_the_frozen_twelve_plus_v11_fact_ids(self):
        facts = _extract()
        fact_ids = {fact["fact_id"] for fact in facts}
        self.assertEqual(fact_ids, EXPECTED_FACT_IDS)

    def test_output_passes_validate_facts_unchanged(self):
        facts = _extract()
        validated = validate_facts(facts)
        self.assertEqual(len(validated), len(facts))
        for original, checked in zip(facts, validated):
            self.assertEqual(original["fact_id"], checked["fact_id"])
            self.assertEqual(original["value_state"], checked["value_state"])
            self.assertEqual(original["value"], checked["value"])

    def test_all_facts_use_fact_1_0_schema_version(self):
        for fact in _extract():
            self.assertEqual(fact["schema_version"], "fact-1.0")

    def test_all_facts_use_confirmed_value_state(self):
        for fact in _extract():
            self.assertEqual(fact["value_state"], "confirmed")

    def test_all_facts_use_a_valid_poc1_source_type(self):
        for fact in _extract():
            self.assertIn(fact["source_type"], {"policy_text", "derived"})

    def test_document_scope_facts_are_exempt_from_activity_id(self):
        facts = {fact["fact_id"]: fact for fact in _extract()}
        for fact_id in GLOBAL_SCOPE_FACT_IDS:
            self.assertIsNone(facts[fact_id]["activity_id"])

    def test_other_facts_retain_activity_id_scope(self):
        facts = {fact["fact_id"]: fact for fact in _extract()}
        for fact_id, fact in facts.items():
            if fact_id in GLOBAL_SCOPE_FACT_IDS:
                continue
            self.assertTrue(fact["activity_id"], f"{fact_id} should retain activity_id")

    def test_every_fact_has_nonempty_evidence(self):
        for fact in _extract():
            self.assertIsInstance(fact["evidence"], list)
            self.assertGreater(len(fact["evidence"]), 0)

    def test_extraction_is_deterministic(self):
        first = _extract()
        second = _extract()
        self.assertEqual(first, second)

    def test_ignores_policy_text_content(self):
        baseline = MockPoC1Extractor().extract(
            analysis_id="poc1-test-001",
            controller_id="controller-test-001",
            controller_name="Test Controller",
            policy_text="합성 테스트 정책 텍스트입니다.",
        )
        different_text = MockPoC1Extractor().extract(
            analysis_id="poc1-test-001",
            controller_id="controller-test-001",
            controller_name="Test Controller",
            policy_text="완전히 다른 임의의 텍스트 내용이라도 결과는 동일해야 함.",
        )
        self.assertEqual(baseline, different_text)


if __name__ == "__main__":
    unittest.main()
