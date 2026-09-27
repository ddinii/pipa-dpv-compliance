"""SC-P02 사고 기록과 통지문에서 PoC2 gold Fact set을 생성한다.

PoC1 빌더와 같이 offset을 손으로 적지 않는다. 근거 문자열을 **그 Fact가 속한
문서에서** 찾아 offset을 계산하고, 기대한 출현 횟수와 다르면 즉시 실패한다.

문서가 둘이라는 점이 PoC1과 다르다. 사고 Fact의 근거는 사고 기록에서만, 통지문
Fact의 근거는 통지문에서만 찾는다. 이 분리 자체가 Fact Dictionary 8장의
"F2-02와 F2-04, F2-05와 F2-08을 합치지 않는다"를 빌더 단계에서 강제한다.

실행:
    python evals/poc2/build_gold_facts.py

Fact ID / 필드 정의는 PIPA Fact Dictionary v1.0 4장(PoC2)과 2장(공통 Envelope),
Rule 기대값은 tests/SC-P02_FINAL_Protege.ttl의 Freeze 시나리오를 따른다.
"""

from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
INCIDENT_PATH = HERE / "sc_p02_incident.txt"
NOTICE_PATH = HERE / "sc_p02_notice.txt"
OUTPUT_PATH = HERE / "sc_p02_gold_facts.json"

SCHEMA_VERSION = "fact-1.0"
SOURCE_DOCUMENT_ID = "SC-P02"

# v1은 요청 하나가 사고 하나를 뜻한다 (EXTRACTOR_DECISIONS #4).
INCIDENT_ID = "breach-incident"
NOTICE_ID = "breach-notice"

INCIDENT = INCIDENT_PATH.read_text(encoding="utf-8")
NOTICE = NOTICE_PATH.read_text(encoding="utf-8")


def _locate(document: str, text: str, *, expect: int = 1) -> dict:
    count = document.count(text)
    if count != expect:
        raise ValueError(f"근거 문자열 {text!r} 출현 {count}회, 기대 {expect}회")
    start = document.index(text)
    return {"text": text, "start_offset": start, "end_offset": start + len(text)}


def inc(text: str, *, expect: int = 1) -> dict:
    """사고 기록에서 근거를 찾는다."""
    return _locate(INCIDENT, text, expect=expect)


def note(text: str, *, expect: int = 1) -> dict:
    """통지문에서 근거를 찾는다."""
    return _locate(NOTICE, text, expect=expect)


def fact(
    fact_id: str,
    subject_id: str,
    ontology_class: str,
    source_type: str,
    evidence: list[dict],
    *,
    ontology_property: str | None = None,
    value=None,
    value_state: str = "confirmed",
    comment: str | None = None,
) -> dict:
    item = {
        "fact_id": fact_id,
        "subject_id": subject_id,
        # 사고와 통지문 Fact는 같은 사고 그룹에 묶인다 (2장 activity_id)
        "activity_id": INCIDENT_ID,
        "ontology_class": ontology_class,
        "ontology_property": ontology_property,
        "value": value,
        "value_state": value_state,
        "source_type": source_type,
        "evidence": evidence,
        "schema_version": SCHEMA_VERSION,
    }
    if comment:
        item["_note"] = comment
    return item


# --- 사고 Fact (source_type = incident_record) ---------------------------

INCIDENT_FACTS = [
    fact(
        "F2-01:breach-incident", INCIDENT_ID, "DataBreachIncident", "incident_record",
        [inc("수신자 이메일 주소가 숨은참조가 아닌 일반 참조에 입력되어")],
        comment="사고 인스턴스의 존재. Class assertion이라 value가 없다",
    ),
    fact(
        "F2-02:breach-incident", INCIDENT_ID, "DataBreachIncident", "incident_record",
        [inc("이번 사고로 실제 노출된 개인정보 항목은 이메일 주소입니다.")],
        ontology_property="affectsPersonalInformation",
        value=["이메일 주소"],
        comment="실제 영향 항목. 통지문 기재 항목(F2-04)과 별개다",
    ),
    fact(
        "F2-05:breach-incident", INCIDENT_ID, "DataBreachIncident", "incident_record",
        [inc("사고 발생시점: 2026년 9월 5일 14시 30분")],
        ontology_property="incidentDate",
        value="2026-09-05T14:30:00+09:00",
        comment="실제 발생시점. 통지문 기재 시점(F2-08)과 절대 합치지 않는다",
    ),
    fact(
        "F2-06:breach-incident", INCIDENT_ID, "DataBreachIncident", "incident_record",
        [inc("사고 인지시점: 2026년 9월 5일 16시 10분")],
        ontology_property="detectionDate",
        value="2026-09-05T16:10:00+09:00",
        comment="P0 Rule이 직접 소비하지 않지만 입력이 뒷받침하므로 추출한다 (EXTRACTOR_DECISIONS #2)",
    ),
    fact(
        # F2-10만 POC2_NOTICE_FACTS에 속해 incident_record를 쓸 수 없다
        # (app/mapping/fact_schema.py). 사고 기록에서 뽑으므로 derived다.
        "F2-10:breach-incident", INCIDENT_ID, "DataBreachIncident", "derived",
        [
            inc("의심스러운 이메일과 링크에 주의하도록 안내하였습니다"),
            inc("발송 경로를 확인하고 추가 노출을 차단하였습니다"),
            inc("개인정보보호 담당부서 연락처를 통한 문의 및 피해구제 절차를 안내하였습니다"),
            inc("대량 메일 발송 절차 점검과 수신자 필드 검증 통제를 적용하였습니다"),
        ],
        ontology_property="hasResponseMeasure",
        value=[
            {"measure_role": "data_subject_guidance",
             "text": "의심스러운 이메일과 링크에 주의하도록 안내"},
            {"measure_role": "controller_response",
             "text": "발송 경로를 확인하고 추가 노출을 차단"},
            {"measure_role": "remedy_procedure",
             "text": "개인정보보호 담당부서 연락처를 통한 문의 및 피해구제 절차 안내"},
            {"measure_role": "post_incident_mitigation",
             "text": "대량 메일 발송 절차 점검과 수신자 필드 검증 통제 적용"},
        ],
        comment="4장 enum 4종. P2-R08은 넷이 모두 확인될 때만 GREEN이다",
    ),
]


# --- 통지문 Fact (source_type = notification_notice) ---------------------

NOTICE_FACTS = [
    fact(
        "F2-03:breach-incident", INCIDENT_ID, "DataBreachIncident", "notification_notice",
        [note("회원님의 개인정보가 유출된 사실을 알려드립니다.")],
        ontology_property="hasNotificationNotice",
        value={"notice_id": NOTICE_ID},
        comment="통지문이 존재한다는 사실 자체",
    ),
    fact(
        "F2-04:breach-notice", NOTICE_ID, "NotificationNotice", "notification_notice",
        [note("유출된 개인정보 항목은 이메일 주소입니다.")],
        ontology_property="mentionsPersonalInformation",
        value=["이메일 주소"],
        comment="통지문이 기재한 항목. 실제 영향 항목(F2-02)과 비교 대상이다",
    ),
    fact(
        "F2-07:breach-incident", INCIDENT_ID, "DataBreachIncident", "notification_notice",
        [note("통지 발송일: 2026년 9월 6일")],
        ontology_property="notificationDate",
        value="2026-09-06T00:00:00+09:00",
        comment="보조 Fact. 입력이 뒷받침하므로 추출한다",
    ),
    fact(
        # 4장 주석: F2-08은 Ontology에 별도 DataProperty를 만들지 않는 시스템 필드다.
        "F2-08:breach-notice", NOTICE_ID, "NotificationNotice", "notification_notice",
        [note("유출이 발생한 시점은 2026년 9월 5일 14시 30분입니다.")],
        ontology_property=None,
        value="2026-09-05T14:30:00+09:00",
        comment="통지문이 기재한 시점. 값이 F2-05와 같아도 별개 Fact다",
    ),
    fact(
        "F2-09:breach-notice", NOTICE_ID, "NotificationNotice", "notification_notice",
        [note("수신자 간 노출되었습니다.")],
        ontology_property="hasIncidentCircumstances",
        value=(
            "뉴스레터 발송 과정에서 수신자 이메일 주소가 숨은참조가 아닌 일반 참조에 "
            "입력되어 수신자 간 노출되었습니다."
        ),
        comment="통지문이 기재한 경위",
    ),
]


FACTS = INCIDENT_FACTS + NOTICE_FACTS

# tests/SC-P02_FINAL_Protege.ttl의 Freeze 기대값
EXPECTED_RULE_STATUS = {
    "P2-R01": "GREEN",
    "P2-R02": "GREEN",
    "P2-R03": "GREEN",
    "P2-R08": "GREEN",
}


def build() -> dict:
    return {
        "source_document_id": SOURCE_DOCUMENT_ID,
        "poc": "poc2",
        "incident_text_file": INCIDENT_PATH.name,
        "notice_text_file": NOTICE_PATH.name,
        "fact_schema_version": SCHEMA_VERSION,
        "expected_rule_status": EXPECTED_RULE_STATUS,
        "facts": FACTS,
    }


def main() -> int:
    payload = build()
    OUTPUT_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    incident = sum(1 for f in FACTS if f["source_type"] == "incident_record")
    notice = sum(1 for f in FACTS if f["source_type"] == "notification_notice")
    derived = sum(1 for f in FACTS if f["source_type"] == "derived")
    print(f"Fact {len(FACTS)}개 -> {OUTPUT_PATH}")
    print(f"  사고 기록 {incident}개 · 통지문 {notice}개 · derived {derived}개")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
