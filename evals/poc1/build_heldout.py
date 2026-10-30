"""PoC1 held-out 평가 세트의 gold Fact를 생성한다.

held-out은 **프롬프트를 고칠 때 보지 않는** 문서다. SC-P01과 그 변형은 프롬프트를
다듬는 데 이미 쓰였으므로, 그 점수만으로는 처음 보는 문서에서의 성능을 말할 수 없다.
이 세트의 결과를 보고 프롬프트를 고쳤다면 그 순간 이 세트도 오염된 것이다.

SC-P01과 일부러 다르게 만든다.
    h1-fitness-app     목록형. 숫자 보유기간(F1-03 confirmed), 항목이 겹치는
                       제3자 제공 2건 (TST-002 혼합 함정)
    h2-online-academy  서술형(조문 안 문장). 제공 목적 누락, 이름 없는 수탁자

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


def collected_items(act, ev, names, anchor):
    """F1-22 처리하는 개인정보 항목 (v1.1). 같은 항목명이 여러 조에 나오므로 anchor 안에서 찾는다."""
    return fact("F1-22", act, "CollectionAndUse", "hasPersonalInformation",
                [ev(name, within=anchor) for name in names], value=list(names))


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
        collected_items("act-collection-001", ev, ["휴대전화번호", "닉네임", "비밀번호"],
              " - 항목: 휴대전화번호, 닉네임, 비밀번호"),
        collected_items("act-collection-002", ev, ["키", "몸무게", "운동 기록", "걸음 수"],
              " - 항목: 키, 몸무게, 운동 기록, 걸음 수"),
        collected_items("act-collection-003", ev, ["이름", "휴대전화번호", "경품 수령 주소"],
              " - 항목: 이름, 휴대전화번호, 경품 수령 주소"),
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
        # 보호책임자를 직함("팀장")으로만 적었다. 성명도 부서 명칭도 아니므로 특정할 수 없다
        # -> unknown. 연락처는 아예 없다 -> absent. 국외 이전은 언급 자체가 없다.
        fact("F1-20", None, "PersonalInformationController", "hasPrivacyOfficer",
             [ev("개인정보 보호책임자: 개인정보보호팀장")], value_state="unknown",
             subject_id="privacy-officer", note="직함만 기재. 성명·부서 명칭을 특정할 수 없다"),
        fact("F1-21", None, "PrivacyOfficer", "hasContact",
             [ev("7. 개인정보 보호책임자")], value_state="absent",
             subject_id="privacy-officer", note="연락처 기재 없음. 근거는 확인한 구간"),
    ]
    return {
        "heldout": {
            "name": "h1-fitness-app",
            "description": "목록형 처리방침. 숫자 보유기간과 항목이 겹치는 제3자 제공 2건",
        },
        "expected_rule_status": {
            "P1-R01": "GREEN",
            "P1-R02": "RED",  # 경품 이벤트에 보유기간·종료조건이 모두 없다 (처리행위별 판정)
            "P1-R03": "GREEN",
            "P1-R04": "GREEN",
            "P1-R06": "GREEN",
            "P1-R07": "GREEN",
            "P1-R08": "YELLOW",
            "P1-R09": "YELLOW",  # 국외 이전 언급 없음. 부재 선언도 아니다
            "P1-R10": "RED",     # 연락처 누락 (성명·부서는 특정 불가)
            "P1-R11": "GREEN",  # 목적별 처리 항목 기재
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
    transfer = ("회사는 학습 데이터를 백업하기 위하여 싱가포르에 있는 클라우드 서버로 "
                "이름, 이메일 주소, 수강 이력을 이전하며")
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
        # 서술형: 목적 문장 안에 항목이 함께 있다
        collected_items("act-collection-001", ev, ["이름", "이메일 주소", "수강 이력"],
              "관리하기 위하여 이름, 이메일 주소, 수강 이력을 처리합니다."),
        collected_items("act-collection-002", ev, ["결제수단 정보", "결제 내역"],
              "결제수단 정보와 결제 내역을 처리하며"),
        collected_items("act-collection-003", ev, ["이메일 주소"],
              "신규 강좌 안내 메일을 보내기 위하여 이메일 주소를 이용합니다."),

        # 제공 목적이 없다 -> F1-07 absent -> P1-R03 RED. 보유 정보도 없다 -> P1-R02 RED
        fact("F1-05", "act-provision-001", "ThirdPartyProvision", "hasRecipient",
             [ev("한국직무교육협회")], value="한국직무교육협회"),
        fact("F1-06", "act-provision-001", "ThirdPartyProvision", "hasPersonalInformation",
             [ev("이름", within=provision), ev("수강 이력", within=provision)],
             value=["이름", "수강 이력"]),
        fact("F1-07", "act-provision-001", "ThirdPartyProvision", "hasPurpose",
             [ev(provision)], value_state="absent", note="제공 목적 기재 없음"),
        *retention("act-provision-001", "ThirdPartyProvision", ev, searched=provision),

        # 위탁 2건 중 결제 대행은 수탁자를 "외부 전문업체"로만 언급하고 이름이 없다.
        # 언급했지만 비어 있으므로 unknown -> P1-R06 YELLOW (dev v4 '추후 선정 예정'과 같은 갈래,
        # 아예 언급이 없는 dev v5는 absent -> RED).
        #
        # 정정 기록: 처음에는 absent(RED)로 붙였다. 첫 held-out 실행에서 Sonnet 5와
        # Opus 5가 모두 unknown으로 읽었고, dev v4/v5의 구분과 PASS2 8번 규칙에 비추어
        # 정답지가 틀렸다고 판단해 사용자 승인 후 고쳤다 (결과를 본 뒤의 정정이다).
        fact("F1-09", "act-entrust-001", "EntrustedProcessing", "hasProcessor",
             [ev("주식회사 스트림원")], value="주식회사 스트림원"),
        fact("F1-10", "act-entrust-001", "EntrustedProcessing", None,
             [ev("강의 영상 전송", within=streaming)], value="강의 영상 전송",
             note="system field entrusted_task_text"),
        fact("F1-09", "act-entrust-002", "EntrustedProcessing", "hasProcessor",
             [ev(entrust)], value_state="unknown",
             note="수탁자를 '외부 전문업체'로만 언급. 이름을 특정할 수 없다"),
        fact("F1-10", "act-entrust-002", "EntrustedProcessing", None,
             [ev("결제 대행")], value="결제 대행", note="system field entrusted_task_text"),

        *retention("act-crossborder-001", "CrossBorderTransfer", ev, end="회원 탈퇴 시",
                   anchor=crossborder, searched=crossborder),
        *cross_border_h2(ev, transfer),

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
    # 제7조 권리 문장에 "보호책임자에게 서면으로"라는 언급만 있다. 성명·부서·연락처는 없다
    facts += officer_absent(ev, "에듀브릿지 개인정보 처리방침")

    return {
        "heldout": {
            "name": "h2-online-academy",
            "description": "서술형 처리방침. 제공 목적 누락, 수탁자명 누락, 국외 이전",
        },
        "expected_rule_status": {
            "P1-R01": "GREEN",
            "P1-R02": "RED",  # 제3자 제공에 보유기간·종료조건이 모두 없다 (처리행위별 판정)
            "P1-R03": "RED",    # 제공 목적 누락
            "P1-R04": "GREEN",
            "P1-R06": "YELLOW",  # 결제 대행 수탁자명을 특정할 수 없다 (정정: 처음엔 RED)
            "P1-R07": "GREEN",
            "P1-R08": "GREEN",
            "P1-R09": "RED",    # 이전받는 자·연락처·거부 방법 누락
            "P1-R10": "RED",    # 보호책임자 조항 없음 (권리 행사 문장에 언급만 있다)
            "P1-R11": "GREEN",  # 목적별 처리 항목 기재
        },
        "facts": facts,
    }


def cross_border_h2(ev, sentence: str) -> list[dict]:
    """h2 제5조 한 문장. 국가·항목·목적은 있고, 이전받는 자는 "클라우드 서버"뿐이다.

    서버는 이전받는 자(법인·사람)가 아니므로 F1-16을 채우지 않는다 -> absent.
    "클라우드 서버로 이전"은 방법의 일부를 말하지만 시기가 없다 -> F1-18 unknown.
    """
    act = "act-crossborder-001"
    items = ["이름", "이메일 주소", "수강 이력"]
    return [
        fact("F1-13", act, "CrossBorderTransfer", "hasDestinationCountry",
             [ev("싱가포르")], value="싱가포르"),
        fact("F1-14", act, "CrossBorderTransfer", "hasPersonalInformation",
             # "이름"·"수강 이력"은 제3자 제공 문장에도 있다 -> 이전 문장 안에서 찾는다
             [ev(item, within=sentence) for item in items],
             value=items),
        fact("F1-15", act, "CrossBorderTransfer", "hasPurpose",
             [ev("학습 데이터를 백업")], value="학습 데이터를 백업"),
        fact("F1-16", act, "CrossBorderTransfer", "hasTransferRecipient",
             [ev("제5조 (국외 이전)")], value_state="absent",
             note="'클라우드 서버'는 이전받는 자가 아니다. 이름을 추정하지 않는다"),
        fact("F1-17", act, "OverseasRecipient", "hasContact",
             [ev("제5조 (국외 이전)")], value_state="absent"),
        fact("F1-18", act, "CrossBorderTransfer", "hasTransferTimingAndMethod",
             [ev("클라우드 서버로")], value_state="unknown",
             note="방법(클라우드 서버로)만 있고 시기가 없다"),
        fact("F1-19", act, "CrossBorderTransfer", "hasTransferRefusalProcedure",
             [ev("제5조 (국외 이전)")], value_state="absent"),
    ]


def officer_absent(ev, title: str) -> list[dict]:
    """보호책임자 조항이 문서에 없다. 의무가 항상 적용되므로 Fact를 빼지 않고 absent로 둔다.

    Fact가 아예 없으면 "추출하지 못함"과 구별되지 않아 YELLOW가 된다. 근거는 확인한 범위인
    문서 전체이고, 그 대표로 문서 제목을 가리킨다.
    """
    return [
        fact("F1-20", None, "PersonalInformationController", "hasPrivacyOfficer",
             [ev(title)], value_state="absent", subject_id="privacy-officer",
             note="보호책임자 기재 없음. 근거는 확인한 범위(문서 전체)"),
        fact("F1-21", None, "PrivacyOfficer", "hasContact",
             [ev(title)], value_state="absent", subject_id="privacy-officer",
             note="연락처 기재 없음. 근거는 확인한 범위(문서 전체)"),
    ]


def declared_absence(ev, activity_type: str, quote: str) -> dict:
    """원문이 그 유형의 처리행위를 하지 않는다고 명시함 (activity presence metadata)."""
    return {
        "field": "activity_presence",
        "activity_type": activity_type,
        "state": "confirmed_false",
        "source_type": SOURCE_TYPE,
        "evidence": [ev(quote)],
    }


# --- h3: 제공도 위탁도 하지 않는다고 명시 -> N/A ---------------------------


def build_h3(document: str) -> dict:
    ev = locator(document)
    retention_sentence = "회원 관리 정보와 메모 동기화 정보는 회원 탈퇴 시까지 보유합니다."
    facts = [
        *collection("act-collection-001", ev, heading="회원 관리",
                    heading_anchor="회원 관리: 로그인", purpose="로그인 및 계정 식별"),
        *collection("act-collection-002", ev, heading="메모 동기화",
                    heading_anchor="메모 동기화: 기기", purpose="기기 간 메모 동기화"),
        *retention("act-collection-001", "CollectionAndUse", ev, end="회원 탈퇴 시",
                   anchor=retention_sentence, searched="2. 보유 기간"),
        *retention("act-collection-002", "CollectionAndUse", ev, end="회원 탈퇴 시",
                   anchor=retention_sentence, searched="2. 보유 기간"),
        collected_items("act-collection-001", ev, ["이메일 주소", "비밀번호"],
              "로그인 및 계정 식별을 위하여 이메일 주소와 비밀번호를 처리합니다."),
        collected_items("act-collection-002", ev, ["메모 내용", "기기 식별값"],
              "기기 간 메모 동기화를 위하여 메모 내용과 기기 식별값을 처리합니다."),
        fact("F1-08", "act-destruction-001", "Destruction", "hasDestructionMethod",
             [ev("복구할 수 없는 방법으로 즉시 삭제합니다.")],
             value="복구할 수 없는 방법으로 즉시 삭제합니다."),
        *rights(ev, ["개인정보 열람", "정정·삭제", "처리정지"],
                "앱의 설정 > 계정 메뉴에서 직접 하거나 고객지원 이메일로 요청"),
        *officer_absent(ev, "라이트노트 개인정보 처리방침"),
    ]
    return {
        "heldout": {
            "name": "h3-no-sharing",
            "description": "제3자 제공과 처리 위탁을 하지 않는다고 명시 (N/A 두 건)",
        },
        "expected_rule_status": {
            "P1-R01": "GREEN",
            "P1-R02": "GREEN",
            "P1-R03": "N/A",   # "제3자에게 제공하지 않습니다"
            "P1-R04": "GREEN",
            "P1-R06": "N/A",   # "외부에 위탁하지 않습니다"
            "P1-R07": "GREEN",
            "P1-R08": "YELLOW",
            "P1-R09": "YELLOW",  # 국외 이전 언급 없음. 부재 선언이 아니다
            "P1-R10": "RED",     # 보호책임자 기재가 문서 어디에도 없다 (항상 적용되는 의무)
            "P1-R11": "GREEN",  # 목적별 처리 항목 기재
        },
        # 부재는 Fact가 아니라 presence metadata다 (35개 Fact에 더하지 않는다)
        "system_metadata": [
            declared_absence(ev, "ThirdPartyProvision",
                             "회사는 이용자의 개인정보를 제3자에게 제공하지 않습니다."),
            declared_absence(ev, "EntrustedProcessing",
                             "회사는 개인정보 처리업무를 외부에 위탁하지 않습니다."),
        ],
        "facts": facts,
    }


# --- h4: "원칙적으로 제공하지 않으나 다음의 경우 제공" + 위탁 언급 없음 -----
#
# 잘못된 N/A를 잡는 함정이다. 부정문으로 시작하지만 실제 제공이 뒤따르므로 부재
# 선언이 아니다. 그 제공에는 목적이 빠져 있어 P1-R03은 RED다. 여기서 N/A가 나오면
# 그 결함이 판정에서 사라지고, 채점기가 위험 오판(N/A)으로 센다.
# 위탁은 아예 언급이 없다. "기재 없음"은 부재 선언이 아니므로 YELLOW다.


def build_h4(document: str) -> dict:
    ev = locator(document)
    provision_retention = " - 보유 기간: 협력 대리점의 배송 업무 종료 시까지"
    items_line = " - 제공 항목: 받는 분 이름, 연락처, 주소"
    rights_sentence = "이용자는 개인정보 열람, 정정, 삭제를 요구할 수 있으며"
    facts = [
        *collection("act-collection-001", ev, heading="택배 예약 접수",
                    purpose="집하 및 배송"),
        *retention("act-collection-001", "CollectionAndUse", ev, end="배송 완료 시",
                   searched="제2조 (보유 기간)"),
        collected_items("act-collection-001", ev, ["이름", "연락처", "주소"],
              "보내는 분과 받는 분의 이름, 연락처, 주소를 처리합니다."),
        fact("F1-05", "act-provision-001", "ThirdPartyProvision", "hasRecipient",
             [ev("지역 배송 협력 대리점")], value="지역 배송 협력 대리점"),
        fact("F1-06", "act-provision-001", "ThirdPartyProvision", "hasPersonalInformation",
             [ev(item, within=items_line) for item in ("받는 분 이름", "연락처", "주소")],
             value=["받는 분 이름", "연락처", "주소"]),
        # 제공 목적이 없다. 이 결함이 있어야 잘못된 N/A가 "결함을 가린 위험 오판"으로
        # 잡힌다. 제공이 완전했다면 잘못된 N/A는 단순 불일치에 그친다.
        fact("F1-07", "act-provision-001", "ThirdPartyProvision", "hasPurpose",
             [ev("다만, 다음의 경우에는 제공합니다.")], value_state="absent",
             note="제공 목적 기재 없음"),
        *retention("act-provision-001", "ThirdPartyProvision", ev,
                   end="협력 대리점의 배송 업무 종료 시", anchor=provision_retention,
                   searched=provision_retention),
        fact("F1-08", "act-destruction-001", "Destruction", "hasDestructionMethod",
             [ev("전자적 파일의 경우 복구할 수 없도록 삭제하고, 운송장 출력물은 분쇄합니다.")],
             value="전자적 파일의 경우 복구할 수 없도록 삭제하고, 운송장 출력물은 분쇄합니다."),
        *rights(ev, ["개인정보 열람", "정정", "삭제"], "고객센터 게시판 또는 이메일",
                anchor=rights_sentence),
        *officer_absent(ev, "하루택배 개인정보 처리방침"),
    ]
    return {
        "heldout": {
            "name": "h4-partial-negation",
            "description": "'원칙적으로 제공하지 않으나 다음의 경우 제공' 함정, 위탁 언급 없음",
        },
        "expected_rule_status": {
            "P1-R01": "GREEN",
            "P1-R02": "GREEN",
            "P1-R03": "RED",    # 부분 부정은 부재가 아니다. 목적 누락 -> RED. N/A면 위험 오판
            "P1-R04": "GREEN",
            "P1-R06": "YELLOW",  # 위탁 언급 없음. 부재 선언도 아니다
            "P1-R07": "GREEN",
            "P1-R08": "YELLOW",
            "P1-R09": "YELLOW",  # 국외 이전 언급 없음
            "P1-R10": "RED",     # 보호책임자 기재 없음
            "P1-R11": "GREEN",  # 목적별 처리 항목 기재
        },
        "facts": facts,
    }


# --- h5: 국외 이전과 보호책임자를 빠짐없이 적은 문서 -> 둘 다 GREEN -----------
#
# 성명·연락처는 모두 합성 값이다 (관용 예시 성명, example.com/.org, 0000 번호).
# 이전받는 자와 연락처가 표 한 줄에 함께 있어도 F1-16(명칭)과 F1-17(연락처)로 나눈다.


def build_h5(document: str) -> dict:
    ev = locator(document)
    act = "act-crossborder-001"
    transfer_items_line = "이전 항목: 이메일 주소, 예약 내역, 접속 로그"
    items = ["이메일 주소", "예약 내역", "접속 로그"]
    timing = "예약 확정 시점에 전용 네트워크를 통해 암호화하여 전송"
    refusal = ("고객센터 이메일로 국외 이전 거부를 요청할 수 있으며, "
               "거부하는 경우 해외 지점 예약 기능을 이용할 수 없습니다.")
    facts = [
        *collection("act-collection-001", ev, heading="숙소 예약",
                    heading_anchor="숙소 예약: ", purpose="숙소 예약 접수 및 예약 확인 안내"),
        *retention("act-collection-001", "CollectionAndUse", ev, end="예약 완료 후 3년",
                   anchor="예약 정보는 예약 완료 후 3년까지 보유합니다.",
                   searched="제2조 (보유 기간)"),
        collected_items("act-collection-001", ev, ["이름", "이메일 주소", "휴대전화번호", "예약 내역"],
              "이름, 이메일 주소, 휴대전화번호, 예약 내역을 처리합니다."),
        fact("F1-08", "act-destruction-001", "Destruction", "hasDestructionMethod",
             [ev("복구할 수 없도록 영구 삭제합니다.")], value="복구할 수 없도록 영구 삭제합니다."),
        fact("F1-13", act, "CrossBorderTransfer", "hasDestinationCountry",
             [ev("일본")], value="일본"),
        fact("F1-14", act, "CrossBorderTransfer", "hasPersonalInformation",
             [ev(item, within=transfer_items_line) for item in items], value=items),
        fact("F1-15", act, "CrossBorderTransfer", "hasPurpose",
             [ev("해외 지점 숙소 예약 처리", within="이전받는 자의 이용 목적: 해외 지점 숙소 예약 처리")],
             value="해외 지점 숙소 예약 처리"),
        fact("F1-16", act, "CrossBorderTransfer", "hasTransferRecipient",
             [ev("Example Travel K.K.")], value="Example Travel K.K."),
        fact("F1-17", act, "OverseasRecipient", "hasContact",
             [ev("privacy@example.org")], value=["privacy@example.org"]),
        fact("F1-18", act, "CrossBorderTransfer", "hasTransferTimingAndMethod",
             [ev(timing)], value=timing),
        fact("F1-19", act, "CrossBorderTransfer", "hasTransferRefusalProcedure",
             [ev(refusal)], value=refusal),
        *retention(act, "CrossBorderTransfer", ev, end="예약 완료 후 3년",
                   anchor="보유 기간: 예약 완료 후 3년까지", searched="제4조 (개인정보의 국외 이전)"),
        *rights(ev, ["열람", "정정·삭제", "처리정지"], "고객센터 이메일 또는 서면",
                anchor="이용자는 개인정보 열람, 정정·삭제, 처리정지를 요구할 수 있습니다."),
        fact("F1-20", None, "PersonalInformationController", "hasPrivacyOfficer",
             [ev("홍길동"), ev("정보보호팀")],
             value={"name": "홍길동", "department": "정보보호팀"}, subject_id="privacy-officer"),
        fact("F1-21", None, "PrivacyOfficer", "hasContact",
             [ev("02-0000-0000"), ev("dpo@example.com")],
             value=["02-0000-0000", "dpo@example.com"], subject_id="privacy-officer"),
    ]
    return {
        "heldout": {
            "name": "h5-full-disclosure",
            "description": "국외 이전 기재사항과 보호책임자 성명·부서·연락처를 모두 적은 문서",
        },
        "expected_rule_status": {
            "P1-R01": "GREEN",
            "P1-R02": "GREEN",
            "P1-R03": "N/A",
            "P1-R04": "GREEN",
            "P1-R06": "N/A",
            "P1-R07": "GREEN",
            "P1-R08": "YELLOW",  # 동의 철회가 없다
            "P1-R09": "GREEN",
            "P1-R10": "GREEN",
            "P1-R11": "GREEN",  # 목적별 처리 항목 기재
        },
        "system_metadata": [
            declared_absence(ev, "ThirdPartyProvision",
                             "회사는 이용자의 개인정보를 제3자에게 제공하지 않습니다."),
            declared_absence(ev, "EntrustedProcessing",
                             "회사는 개인정보 처리업무를 외부에 위탁하지 않습니다."),
        ],
        "facts": facts,
    }


def automatic_collection_unknown_facts(document: str) -> list[dict]:
    """쿠키 등 장치 사용 여부가 나타나지 않는 문서의 확인 필요 Fact."""
    evidence = [{"text": document.splitlines()[0], "start_offset": 0,
                 "end_offset": len(document.splitlines()[0])}]
    return [fact(f"F1-{number}", None, "PersonalInformationController", prop,
                 evidence, value_state="absent", subject_id="automatic-collection")
            for number, prop in [(23, "hasAutomaticCollectionDevice"),
                                 (24, "hasAutomaticCollectionOperation"),
                                 (25, "hasAutomaticCollectionOptOutMethod")]]


BUILDERS = {
    "h1-fitness-app": build_h1,
    "h2-online-academy": build_h2,
    "h3-no-sharing": build_h3,
    "h4-partial-negation": build_h4,
    "h5-full-disclosure": build_h5,
}


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
        payload["facts"].extend(automatic_collection_unknown_facts(document))
        payload["expected_rule_status"]["P1-R12"] = "YELLOW"
        (directory / "gold_facts.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        print(f"{name}: fact {len(payload['facts'])}개")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
