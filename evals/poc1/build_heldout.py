"""PoC1 held-out 평가 세트의 gold Fact를 생성한다.

held-out은 **프롬프트를 고칠 때 보지 않는** 문서다. SC-P01과 그 변형은 프롬프트를
다듬는 데 이미 쓰였으므로, 그 점수만으로는 처음 보는 문서에서의 성능을 말할 수 없다.
이 세트의 결과를 보고 프롬프트를 고쳤다면 그 순간 이 세트도 오염된 것이다.

SC-P01과 일부러 다르게 만든다.
    h1-fitness-app     목록형. 숫자 보유기간(F1-03 confirmed), 항목이 겹치는
                       제3자 제공 2건 (TST-002 혼합 함정)
    h2-online-academy  서술형(조문 안 문장). 제공 목적 누락, 수탁자명 누락

offset은 손으로 적지 않는다. 근거 문자열을 문서에서 찾고, 정확히 한 번 나오지 않으면
실패한다. 같은 문자열이 여러 번 나오면 유일한 줄(anchor) 안에서 찾는다.

실행:
    python evals/poc1/build_heldout.py
"""

from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
HELDOUT_DIR = HERE / "heldout"
SCHEMA_VERSION = "fact-1.0"
SOURCE_TYPE = "policy_text"


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


def fact(fact_type, activity_id, ontology_class, ontology_property, evidence, *,
         value=None, value_state="confirmed", subject_id=None, suffix=None, note=None):
    subject = subject_id or activity_id
    item = {
        "fact_id": f"{fact_type}:{suffix or subject}",
        "subject_id": subject,
        "activity_id": activity_id,
        "ontology_class": ontology_class,
        "ontology_property": ontology_property,
        "value": value,
        "value_state": value_state,
        "source_type": SOURCE_TYPE,
        "evidence": evidence,
        "schema_version": SCHEMA_VERSION,
    }
    if note:
        item["_note"] = note
    return item


def collection(act, ev, *, heading, heading_anchor=None, purpose, purpose_anchor=None):
    """F1-01 존재와 F1-02 목적."""
    return [
        fact("F1-01", act, "CollectionAndUse", None, [ev(heading, within=heading_anchor)]),
        fact("F1-02", act, "CollectionAndUse", "hasPurpose",
             [ev(purpose, within=purpose_anchor)], value=purpose),
    ]


def retention(act, ontology_class, ev, *, period=None, end=None, anchor=None, searched):
    """F1-03(숫자 기간)과 F1-04(종료조건). 적히지 않은 쪽은 absent로, 찾아본 구간을 근거로 둔다."""
    items = []
    if period:
        items.append(fact("F1-03", act, "PersonalInformationProcessing", "hasRetention",
                          [ev(period, within=anchor)], value=period))
    else:
        items.append(fact("F1-03", act, "PersonalInformationProcessing", "hasRetention",
                          [ev(searched)], value_state="absent",
                          note="숫자 기간 기재 없음. 근거는 확인한 구간"))
    if end:
        items.append(fact("F1-04", act, ontology_class, "hasRetention",
                          [ev(end, within=anchor)], value=end))
    else:
        items.append(fact("F1-04", act, ontology_class, "hasRetention",
                          [ev(searched)], value_state="absent",
                          note="종료조건 기재 없음. 근거는 확인한 구간"))
    return items


def rights(ev, names, procedure, *, anchor=None):
    items = [fact("F1-11", None, "DataSubject", "hasRight",
                  [ev(name, within=anchor) for name in names],
                  value=list(names), subject_id="subj-001")]
    for name in names:
        items.append(fact("F1-12", None, "DataSubjectRight", "hasExerciseProcedure",
                          [ev(procedure)], value={"right": name, "procedure": procedure},
                          subject_id="subj-001", suffix=name))
    return items


# --- h1: 목록형, 숫자 기간, 겹치는 제3자 제공 -----------------------------


def build_h1(document: str) -> dict:
    ev = locator(document)
    searched = "2. 개인정보의 보유 기간"
    facts = [
        *collection("act-collection-001", ev, heading="회원 관리",
                    heading_anchor="가. 회원 관리\n", purpose="본인 확인, 계정 생성 및 도용 방지"),
        *collection("act-collection-002", ev, heading="운동 기록 서비스",
                    heading_anchor="나. 운동 기록 서비스\n",
                    purpose="운동 기록 저장·분석 및 맞춤형 운동 추천"),
        *collection("act-collection-003", ev, heading="경품 이벤트",
                    purpose="이벤트 응모 확인 및 경품 발송"),
        *retention("act-collection-001", "CollectionAndUse", ev,
                   end="회원 탈퇴 시", searched=searched),
        *retention("act-collection-002", "CollectionAndUse", ev,
                   period="수집일로부터 2년", searched=searched),
        # 경품 이벤트는 2절에 없고, 일반 보유 문장도 없다 -> 둘 다 absent
        *retention("act-collection-003", "CollectionAndUse", ev, searched=searched),
    ]

    # 제공 2건은 항목이 겹친다(이름, 휴대전화번호). 2번의 "걸음 수"가 1번으로 새면 혼합이다.
    for act, recipient, purpose, items_line, items, period, end in [
        ("act-provision-001", "주식회사 짐파트너스", "제휴 헬스장 이용권 발급 및 출입 확인",
         " - 제공 항목: 이름, 휴대전화번호\n", ["이름", "휴대전화번호"],
         None, "이용권 만료 시"),
        ("act-provision-002", "한빛손해보험 주식회사", "운동량 연계 보험 상품 안내",
         " - 제공 항목: 이름, 휴대전화번호, 걸음 수\n", ["이름", "휴대전화번호", "걸음 수"],
         "제공일로부터 1년", None),
    ]:
        facts += [
            fact("F1-05", act, "ThirdPartyProvision", "hasRecipient",
                 [ev(recipient)], value=recipient),
            fact("F1-06", act, "ThirdPartyProvision", "hasPersonalInformation",
                 [ev(item, within=items_line) for item in items], value=items),
            fact("F1-07", act, "ThirdPartyProvision", "hasPurpose",
                 [ev(purpose)], value=purpose),
        ]
        retention_line = (" - 보유 기간: 이용권 만료 시까지" if end
                          else " - 보유 기간: 제공일로부터 1년")
        facts += retention(act, "ThirdPartyProvision", ev, period=period, end=end,
                           anchor=retention_line, searched=retention_line)

    facts += [
        fact("F1-09", "act-entrust-001", "EntrustedProcessing", "hasProcessor",
             [ev("주식회사 알림톡스")], value="주식회사 알림톡스"),
        fact("F1-10", "act-entrust-001", "EntrustedProcessing", None,
             [ev("인증번호 및 이벤트 당첨 알림 발송")], value="인증번호 및 이벤트 당첨 알림 발송",
             note="system field entrusted_task_text"),
        fact("F1-08", "act-destruction-001", "Destruction", "hasDestructionMethod",
             [ev("전자적 파일은 복원할 수 없는 기술적 방법으로 영구 삭제하고, 출력물은 분쇄합니다.")],
             value="전자적 파일은 복원할 수 없는 기술적 방법으로 영구 삭제하고, 출력물은 분쇄합니다."),
        *rights(ev, ["개인정보 열람", "정정·삭제", "처리정지"],
                "앱 내 설정 > 개인정보 메뉴 또는 고객센터 이메일"),
    ]
    return {
        "heldout": {
            "name": "h1-fitness-app",
            "description": "목록형 처리방침. 숫자 보유기간과 항목이 겹치는 제3자 제공 2건",
        },
        "expected_rule_status": {
            "P1-R01": "GREEN",
            "P1-R02": "AMBER",  # 경품 이벤트에 보유 정보가 없다
            "P1-R03": "GREEN",
            "P1-R04": "GREEN",
            "P1-R06": "GREEN",
            "P1-R07": "GREEN",
        },
        "facts": facts,
    }


# --- h2: 서술형, 목적 누락 제공, 이름 없는 수탁자 ------------------------


def build_h2(document: str) -> dict:
    ev = locator(document)
    searched = "제2조 (보유 기간)"
    provision = "회사는 이용자의 이름과 수강 이력을 한국직무교육협회에 제공하고 있습니다."
    entrust = "회사는 강의 영상 전송과 결제 대행 업무를 외부 전문업체에 맡기고 있습니다."
    streaming = "강의 영상 전송은 주식회사 스트림원이 수행합니다."
    crossborder = "이전된 정보는 이용자가 회원 탈퇴 시 함께 삭제합니다."
    rights_sentence = "처리정지를 요구하거나 동의를 철회할 수 있습니다."

    facts = [
        *collection("act-collection-001", ev, heading="수강 신청을 받고 학습 진도를 관리",
                    purpose="수강 신청을 받고 학습 진도를 관리"),
        *collection("act-collection-002", ev, heading="강의료 결제와 환불을 처리",
                    purpose="강의료 결제와 환불을 처리"),
        *collection("act-collection-003", ev, heading="신규 강좌 안내 메일을 보내기",
                    purpose="신규 강좌 안내 메일을 보내기"),
        *retention("act-collection-001", "CollectionAndUse", ev, end="회원 탈퇴 시",
                   anchor="수강 신청 및 학습 관리 정보는 회원 탈퇴 시까지 보유합니다.",
                   searched=searched),
        *retention("act-collection-002", "CollectionAndUse", ev, period="5년간",
                   searched=searched),
        *retention("act-collection-003", "CollectionAndUse", ev, end="수신 동의를 철회할 때",
                   searched=searched),

        # 제공 목적이 없다 -> F1-07 absent -> P1-R03 RED. 보유 정보도 없다 -> P1-R02 AMBER
        fact("F1-05", "act-provision-001", "ThirdPartyProvision", "hasRecipient",
             [ev("한국직무교육협회")], value="한국직무교육협회"),
        fact("F1-06", "act-provision-001", "ThirdPartyProvision", "hasPersonalInformation",
             [ev("이름", within=provision), ev("수강 이력", within=provision)],
             value=["이름", "수강 이력"]),
        fact("F1-07", "act-provision-001", "ThirdPartyProvision", "hasPurpose",
             [ev(provision)], value_state="absent", note="제공 목적 기재 없음"),
        *retention("act-provision-001", "ThirdPartyProvision", ev, searched=provision),

        # 위탁 2건 중 결제 대행은 수탁자명이 없다 -> P1-R06 RED
        fact("F1-09", "act-entrust-001", "EntrustedProcessing", "hasProcessor",
             [ev("주식회사 스트림원")], value="주식회사 스트림원"),
        fact("F1-10", "act-entrust-001", "EntrustedProcessing", None,
             [ev("강의 영상 전송", within=streaming)], value="강의 영상 전송",
             note="system field entrusted_task_text"),
        fact("F1-09", "act-entrust-002", "EntrustedProcessing", "hasProcessor",
             [ev(entrust)], value_state="absent", note="결제 대행 수탁자명 기재 없음"),
        fact("F1-10", "act-entrust-002", "EntrustedProcessing", None,
             [ev("결제 대행")], value="결제 대행", note="system field entrusted_task_text"),

        *retention("act-crossborder-001", "CrossBorderTransfer", ev, end="회원 탈퇴 시",
                   anchor=crossborder, searched=crossborder),

        fact("F1-08", "act-destruction-001", "Destruction", "hasDestructionMethod",
             [ev("복구할 수 없도록 전자적 방법으로 삭제합니다.")],
             value="복구할 수 없도록 전자적 방법으로 삭제합니다."),
    ]
    rights_facts = rights(ev, ["열람", "정정·삭제", "처리정지"],
                          "홈페이지 1:1 문의 게시판에 글을 남기거나 개인정보 보호책임자에게 "
                          "서면으로 제출하는 방법")
    # "동의를 철회"는 제2조에도 나오므로 제7조 문장 안에서 찾는다
    rights_facts[0]["value"].append("동의를 철회")
    rights_facts[0]["evidence"].append(ev("동의를 철회", within=rights_sentence))
    rights_facts.append(fact(
        "F1-12", None, "DataSubjectRight", "hasExerciseProcedure",
        rights_facts[1]["evidence"],
        value={"right": "동의를 철회", "procedure": rights_facts[1]["value"]["procedure"]},
        subject_id="subj-001", suffix="동의를 철회",
    ))
    facts += rights_facts

    return {
        "heldout": {
            "name": "h2-online-academy",
            "description": "서술형 처리방침. 제공 목적 누락, 수탁자명 누락, 국외 이전",
        },
        "expected_rule_status": {
            "P1-R01": "GREEN",
            "P1-R02": "AMBER",  # 제3자 제공에 보유 정보가 없다
            "P1-R03": "RED",    # 제공 목적 누락
            "P1-R04": "GREEN",
            "P1-R06": "RED",    # 결제 대행 수탁자명 누락
            "P1-R07": "GREEN",
        },
        "facts": facts,
    }


BUILDERS = {"h1-fitness-app": build_h1, "h2-online-academy": build_h2}


def main() -> int:
    for name, builder in BUILDERS.items():
        directory = HELDOUT_DIR / name
        document = (directory / "policy.txt").read_text(encoding="utf-8")
        payload = {
            "source_document_id": f"HELDOUT-P01-{name}",
            "poc": "poc1",
            "policy_text_file": "policy.txt",
            "fact_schema_version": SCHEMA_VERSION,
            **builder(document),
        }
        (directory / "gold_facts.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        print(f"{name}: fact {len(payload['facts'])}개")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
