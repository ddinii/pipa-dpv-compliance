"""PoC2 held-out 평가 세트의 gold Fact를 생성한다.

held-out은 **프롬프트를 고칠 때 보지 않는** 문서다. SC-P02 기준 케이스는 F2-03과
날짜 형식 규칙을 고치는 데 이미 쓰였다. 이 세트의 결과를 보고 프롬프트를 고쳤다면
그 순간 이 세트도 오염된 것이다.

SC-P02와 일부러 다르게 만든다. 특히 날짜 표기를 여러 방식으로 섞는다.
    h1-shop-hacking        "2026. 8. 14. 오전 3시 20분경", "2026-08-14 10:05",
                           통지문이 배송지 주소를 빠뜨림 (P2-R02 RED)
    h2-clinic-misdirected  "오후 2시 15분", 통지문에 경위 없음 (P2-R03 RED),
                           대응조치 4역할 중 2개만 (P2-R08 YELLOW)

사고 Fact의 근거는 사고 기록에서만, 통지문 Fact의 근거는 통지문에서만 찾는다
(build_gold_facts.py와 같은 규칙).

실행:
    python evals/poc2/build_heldout.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
HELDOUT_DIR = HERE / "heldout"
SCHEMA_VERSION = "fact-1.0"

# v1은 요청 하나가 사고 하나를 뜻한다 (EXTRACTOR_DECISIONS #4).
INCIDENT_ID = "breach-incident"
NOTICE_ID = "breach-notice"


def locator(document: str):
    def ev(text: str, *, within: str | None = None) -> dict:
        base, region = 0, document
        if within is not None:
            count = document.count(within)
            if count != 1:
                raise ValueError(f"anchor {within!r} 출현 {count}회, 기대 1회")
            base, region = document.index(within), within
        count = region.count(text)
        if count != 1:
            raise ValueError(f"근거 {text!r} 출현 {count}회 (anchor={within!r}), 기대 1회")
        start = base + region.index(text)
        return {"text": text, "start_offset": start, "end_offset": start + len(text)}

    return ev


def fact(fact_type, subject_id, ontology_class, source_type, evidence, *,
         ontology_property=None, value=None, value_state="confirmed", note=None):
    item = {
        "fact_id": f"{fact_type}:{subject_id}",
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
    if note:
        item["_note"] = note
    return item


def incident_facts(inc, *, occurrence, items, items_anchor, incident_time, detection_time,
                   measures):
    """사고 기록 Fact. 날짜는 (원문 인용, KST ISO 값) 쌍으로 받는다."""
    facts = [
        fact("F2-01", INCIDENT_ID, "DataBreachIncident", "incident_record", [inc(occurrence)]),
        fact("F2-02", INCIDENT_ID, "DataBreachIncident", "incident_record",
             [inc(item, within=items_anchor) for item in items],
             ontology_property="affectsPersonalInformation", value=list(items)),
        fact("F2-05", INCIDENT_ID, "DataBreachIncident", "incident_record",
             [inc(incident_time[0])], ontology_property="incidentDate", value=incident_time[1]),
        fact("F2-06", INCIDENT_ID, "DataBreachIncident", "incident_record",
             [inc(detection_time[0])], ontology_property="detectionDate",
             value=detection_time[1]),
        # F2-10은 POC2_NOTICE_FACTS에 속해 incident_record를 쓸 수 없다 -> derived
        fact("F2-10", INCIDENT_ID, "DataBreachIncident", "derived",
             [inc(quote) for _, quote, _ in measures],
             ontology_property="hasResponseMeasure",
             value=[{"measure_role": role, "text": text} for role, _, text in measures]),
    ]
    return facts


# --- h1: 해킹, 통지문 항목 누락 -------------------------------------------


def build_h1(incident: str, notice: str) -> dict:
    inc, note = locator(incident), locator(notice)
    facts = incident_facts(
        inc,
        occurrence="주문 조회 페이지의 SQL 인젝션 취약점을 이용해 회원 데이터베이스 일부를 조회하였습니다",
        items=["이름", "휴대전화번호", "배송지 주소"],
        items_anchor="실제로 유출된 개인정보는 이름, 휴대전화번호, 배송지 주소입니다.",
        incident_time=("2026. 8. 14. 오전 3시 20분경", "2026-08-14T03:20:00+09:00"),
        detection_time=("2026-08-14 10:05", "2026-08-14T10:05:00+09:00"),
        measures=[
            ("controller_response", "취약한 주문 조회 페이지를 즉시 차단하고 보안 패치를 적용하였습니다",
             "취약한 주문 조회 페이지를 즉시 차단하고 보안 패치를 적용"),
            ("data_subject_guidance", "이용자에게 스미싱 문자에 주의하도록 안내하였습니다",
             "이용자에게 스미싱 문자에 주의하도록 안내"),
            ("remedy_procedure", "피해 신고 전용 창구를 개설하여 피해 접수와 구제 절차를 안내하고 있습니다",
             "피해 신고 전용 창구를 개설하여 피해 접수와 구제 절차를 안내"),
            ("post_incident_mitigation",
             "전체 웹 페이지에 대한 취약점 점검을 실시하고 입력값 검증을 강화하였습니다",
             "전체 웹 페이지에 대한 취약점 점검을 실시하고 입력값 검증을 강화"),
        ],
    )
    circumstances = ("외부 공격자가 주문 조회 페이지의 보안 취약점을 이용하여 회원 정보를 "
                     "무단으로 조회하였습니다.")
    facts += [
        fact("F2-03", INCIDENT_ID, "DataBreachIncident", "notification_notice",
             [note("고객님께 개인정보 유출 사실을 알려드리며 깊이 사과드립니다.")],
             ontology_property="hasNotificationNotice", value={"notice_id": NOTICE_ID}),
        fact("F2-04", NOTICE_ID, "NotificationNotice", "notification_notice",
             [note("이름", within="■ 유출 항목: 이름, 휴대전화번호"),
              note("휴대전화번호", within="■ 유출 항목: 이름, 휴대전화번호")],
             ontology_property="mentionsPersonalInformation", value=["이름", "휴대전화번호"],
             note="배송지 주소를 빠뜨렸다. 보완하지 않고 적힌 그대로 둔다"),
        fact("F2-07", INCIDENT_ID, "DataBreachIncident", "notification_notice",
             [note("통지일: 2026년 8월 16일")], ontology_property="notificationDate",
             value="2026-08-16T00:00:00+09:00"),
        fact("F2-08", NOTICE_ID, "NotificationNotice", "notification_notice",
             [note("■ 유출 시점: 2026년 8월 14일")], value="2026-08-14T00:00:00+09:00",
             note="통지문은 날짜만 적었다. 사고 기록의 03:20을 가져오지 않는다"),
        fact("F2-09", NOTICE_ID, "NotificationNotice", "notification_notice",
             [note(circumstances)], ontology_property="hasIncidentCircumstances",
             value=circumstances),
    ]
    return {
        "heldout": {
            "name": "h1-shop-hacking",
            "description": "해킹 사고. 날짜 표기 혼합, 통지문이 배송지 주소를 빠뜨림",
        },
        "expected_rule_status": {
            "P2-R01": "GREEN",
            "P2-R02": "RED",    # 배송지 주소가 통지문에 없다
            "P2-R03": "GREEN",
            "P2-R08": "GREEN",
            "P2-R09": "YELLOW",  # 통지문은 날짜만 기재, 실제 시각과 불일치
        },
        "facts": facts,
    }


# --- h2: 오발송, 경위 없는 통지문, 일부 대응조치 ---------------------------


def build_h2(incident: str, notice: str) -> dict:
    inc, note = locator(incident), locator(notice)
    facts = incident_facts(
        inc,
        occurrence="수신자 목록 파일이 잘못 선택되어, 다른 환자에게 예약 안내 메일이 발송되었습니다",
        items=["이름", "진료 예약 일시"],
        items_anchor="잘못 발송된 메일에는 환자의 이름과 진료 예약 일시가 포함되어 있었습니다.",
        incident_time=("사고 발생 일시: 2026년 7월 3일 오후 2시 15분", "2026-07-03T14:15:00+09:00"),
        detection_time=("사고 인지 일시: 2026년 7월 3일 오후 5시 40분", "2026-07-03T17:40:00+09:00"),
        # 정보주체 안내와 재발방지 조치는 적혀 있지 않다 -> P2-R08 YELLOW
        measures=[
            ("controller_response", "오발송 메일 수신자에게 삭제를 요청하고 발송 시스템을 일시 중지하였습니다",
             "오발송 메일 수신자에게 삭제를 요청하고 발송 시스템을 일시 중지"),
            ("remedy_procedure", "개인정보 보호책임자 연락처를 통해 문의 및 피해구제 신청을 받고 있습니다",
             "개인정보 보호책임자 연락처를 통해 문의 및 피해구제 신청 접수"),
        ],
    )
    items_line = "1. 유출된 개인정보: 이름, 진료 예약 일시"
    facts += [
        fact("F2-03", INCIDENT_ID, "DataBreachIncident", "notification_notice",
             [note("○○님의 개인정보가 유출된 사실을 알려드립니다.")],
             ontology_property="hasNotificationNotice", value={"notice_id": NOTICE_ID}),
        fact("F2-04", NOTICE_ID, "NotificationNotice", "notification_notice",
             [note("이름", within=items_line), note("진료 예약 일시", within=items_line)],
             ontology_property="mentionsPersonalInformation", value=["이름", "진료 예약 일시"]),
        fact("F2-07", INCIDENT_ID, "DataBreachIncident", "notification_notice",
             [note("통지일: 2026년 7월 5일")], ontology_property="notificationDate",
             value="2026-07-05T00:00:00+09:00"),
        fact("F2-08", NOTICE_ID, "NotificationNotice", "notification_notice",
             [note("2. 유출 일시: 2026년 7월 3일 오후 2시 15분")],
             value="2026-07-03T14:15:00+09:00"),
        fact("F2-09", NOTICE_ID, "NotificationNotice", "notification_notice",
             [note("개인정보 유출 통지\n")], ontology_property="hasIncidentCircumstances",
             value_state="absent", note="통지문 전체에 경위 기재가 없다. 근거는 확인한 문서"),
    ]
    return {
        "heldout": {
            "name": "h2-clinic-misdirected",
            "description": "오발송 사고. 오후 표기, 통지문 경위 누락, 대응조치 일부만 기재",
        },
        "expected_rule_status": {
            "P2-R01": "GREEN",
            "P2-R02": "GREEN",
            "P2-R03": "RED",    # 통지문에 경위가 없다
            "P2-R08": "YELLOW",  # 4역할 중 2개만 확인
            "P2-R09": "GREEN",  # 사고 기록과 통지문 기재 시각이 일치
        },
        "facts": facts,
    }


# --- h3: 통지문 없음 -> 통지문 Rule N/A --------------------------------------


def build_h3(incident: str, notice: str | None) -> dict:
    """통지문이 제공되지 않은 사고. 서비스와 러너가 NotificationNotice 부재를 붙인다."""
    from app.extractors.poc2 import NOTICE_ABSENCE_SHAPE

    inc = locator(incident)
    facts = incident_facts(
        inc,
        occurrence="다른 수강생의 이름과 휴대전화번호가 포함된 안내문이 잘못 발송되었습니다",
        items=["이름", "휴대전화번호"],
        items_anchor="유출 항목: 이름, 휴대전화번호",
        incident_time=("사고 발생 일시: 2026년 6월 11일 오전 10시 20분", "2026-06-11T10:20:00+09:00"),
        detection_time=("사고 인지 일시: 2026년 6월 11일 오후 1시", "2026-06-11T13:00:00+09:00"),
        # 정보주체 안내와 피해구제 절차는 적혀 있지 않다 -> P2-R08 YELLOW
        measures=[
            ("controller_response", "잘못 받은 수신자에게 문자 삭제를 요청하였습니다",
             "잘못 받은 수신자에게 문자 삭제를 요청"),
            ("post_incident_mitigation", "재발 방지를 위해 발송 시스템의 수신자 선택 절차를 개선하였습니다",
             "발송 시스템의 수신자 선택 절차 개선"),
        ],
    )
    # 통지문이 없을 때 Extractor가 내는 모양과 같아야 한다 (다시 적지 않고 가져온다)
    facts += [
        fact(fact_id, subject_id, ontology_class, "derived", [{"field_path": "notification"}],
             ontology_property=prop, value_state="absent")
        for fact_id, (subject_id, ontology_class, prop) in NOTICE_ABSENCE_SHAPE.items()
    ]
    return {
        "heldout": {
            "name": "h3-academy-no-notice",
            "description": "통지문 없는 오발송 사고. 통지문 Rule N/A, 대응조치 일부만",
        },
        "expected_rule_status": {
            "P2-R01": "RED",    # 사고는 있으나 통지문이 없다 (통지 의무 판정이 아니다)
            "P2-R02": "N/A",
            "P2-R03": "N/A",
            "P2-R08": "YELLOW",  # 4역할 중 2개
            "P2-R09": "N/A",  # 통지문이 명시적으로 없음
        },
        "system_metadata": [{
            "field": "activity_presence",
            "activity_type": "NotificationNotice",
            "state": "confirmed_false",
            "source_type": "derived",
            "evidence": [{"field_path": "notification"}],
        }],
        "facts": facts,
    }


BUILDERS = {
    "h1-shop-hacking": build_h1,
    "h2-clinic-misdirected": build_h2,
    "h3-academy-no-notice": build_h3,
}


def main() -> int:
    for name, builder in BUILDERS.items():
        directory = HELDOUT_DIR / name
        incident = (directory / "incident.txt").read_text(encoding="utf-8")
        notice_path = directory / "notice.txt"
        notice = notice_path.read_text(encoding="utf-8") if notice_path.is_file() else None
        payload = {
            "source_document_id": f"HELDOUT-P02-{name}",
            "poc": "poc2",
            "incident_text_file": "incident.txt",
            "notice_text_file": "notice.txt" if notice is not None else None,
            "fact_schema_version": SCHEMA_VERSION,
            **builder(incident, notice),
        }
        (directory / "gold_facts.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        print(f"{name}: fact {len(payload['facts'])}개")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
