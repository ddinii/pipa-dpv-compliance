from pathlib import Path
import sys

try:
    from rdflib import Graph, Namespace, RDF
    from pyshacl import validate
except ModuleNotFoundError as exc:
    print(f"필수 모듈이 없습니다: {exc.name}")
    print("PowerShell에서 다음 명령을 먼저 실행하세요:")
    print("  py -m pip install --user rdflib pyshacl")
    print("설치 후 다음 명령으로 다시 실행하세요:")
    print("  py validate_final_scenarios.py")
    raise SystemExit(2)

BASE = Path(__file__).resolve().parent
PIPA = Namespace("https://w3id.org/pipa-compliance/ontology#")
P01 = Namespace("https://example.org/pipa-test/sc-p01#")
P02 = Namespace("https://example.org/pipa-test/sc-p02-final#")
D01 = Namespace("https://example.org/pipa-test/sc-d01#")
TEST = Namespace("https://example.org/pipa-test/metadata#")

FILES = {
    "SC-P01": BASE / "SC-P01_FINAL_Protege.ttl",
    "SC-P02": BASE / "SC-P02_FINAL_Protege.ttl",
    "SC-D01": BASE / "SC-D01_FINAL_Protege.ttl",
}


def values(graph, subject, predicate):
    return set(graph.objects(subject, predicate))


def instances(graph, class_iri):
    return set(graph.subjects(RDF.type, class_iri))


def require(condition, message, errors):
    if condition:
        print(f"  PASS {message}")
    else:
        print(f"  FAIL {message}")
        errors.append(message)


def shacl_check(graph, shapes, name, errors):
    conforms, _, report = validate(
        data_graph=graph,
        shacl_graph=shapes,
        ont_graph=graph,
        inference="rdfs",
        abort_on_first=False,
    )
    require(conforms, f"{name} SHACL 구조 검증", errors)
    if not conforms:
        print(report)


def check_p01(graph, errors):
    print("\n[SC-P01 개인정보 처리방침]")
    controller = P01.MoaCommerce
    forbidden = {
        PIPA.hasPurpose, PIPA.hasPersonalInformation, PIPA.hasRecipient,
        PIPA.hasProcessor, PIPA.hasLegalBasis, PIPA.hasRetention,
        PIPA.hasDestinationCountry,
    }
    require(not any(p in forbidden for p, _ in graph.predicate_objects(controller)),
            "Controller에 처리 맥락을 직접 연결하지 않음", errors)
    require(len(instances(graph, PIPA.CollectionAndUse)) == 5,
            "수집·이용 활동 5개가 분리됨", errors)
    provision = P01.SellerProvision
    require(bool(values(graph, provision, PIPA.hasRecipient)), "판매자 제공의 recipient 존재", errors)
    require(bool(values(graph, provision, PIPA.hasPersonalInformation)), "판매자 제공의 개인정보 항목 존재", errors)
    require(bool(values(graph, provision, PIPA.hasPurpose)), "판매자 제공의 purpose 존재", errors)
    require(bool(values(graph, P01.CrossBorderCloud, PIPA.hasDestinationCountry)),
            "국외이전에 미국 destinationCountry가 연결됨", errors)
    require(len(instances(graph, PIPA.EntrustedProcessing)) == 4,
            "수탁자별 처리위탁 활동 4개가 분리됨", errors)
    print("  EXPECTED P1-R01 GREEN / P1-R02 AMBER / P1-R03 GREEN / P1-R04 GREEN / P1-R06 GREEN / P1-R07 GREEN")


def item_names(graph, subjects):
    return {str(name) for subject in subjects for name in graph.objects(subject, PIPA.hasItemName)}


def check_p02(graph, errors):
    print("\n[SC-P02 개인정보 침해사고 통지 요건 검토 지원]")
    incident = P02.Incident_B24
    notice = P02.Notice_B24
    linked_notice = notice in values(graph, incident, PIPA.hasNotificationNotice)
    require(linked_notice, "P2-R01: 사고에 별도 NotificationNotice가 연결됨", errors)

    actual_nodes = values(graph, incident, PIPA.affectsPersonalInformation)
    notice_nodes = values(graph, notice, PIPA.mentionsPersonalInformation)
    require(actual_nodes.isdisjoint(notice_nodes),
            "실제 영향 개인정보와 통지문 기재 개인정보 Individual이 분리됨", errors)
    actual_names = item_names(graph, actual_nodes)
    notice_names = item_names(graph, notice_nodes)
    require(actual_names <= notice_names,
            "P2-R02: 실제 영향 개인정보 항목이 통지문에 모두 포함됨", errors)

    has_notice_time = bool(values(graph, notice, PIPA.noticeIncidentTime))
    has_circumstances = bool(values(graph, notice, PIPA.hasIncidentCircumstances))
    require(has_notice_time and has_circumstances,
            "P2-R03: 통지문 자체에 유출등 시점과 경위가 존재함", errors)

    measures = values(graph, incident, PIPA.hasResponseMeasure)
    roles = {str(role) for measure in measures for role in graph.objects(measure, PIPA.measureRole)}
    required_roles = {
        "data_subject_guidance", "controller_response",
        "remedy_procedure", "post_incident_mitigation",
    }
    require(roles == required_roles,
            "P2-R08: 대응·안내·구제 역할 4종이 분리됨", errors)
    print("  EXPECTED P2-R01 GREEN / P2-R02 GREEN / P2-R03 GREEN / P2-R08 GREEN")
    print("  INFO 신고 threshold·ReportingObligation·통지문 생성·정정 provenance는 검사하지 않음")


def check_d01(graph, errors):
    print("\n[SC-D01 Privacy-by-Design]")
    collections = instances(graph, PIPA.CollectionAndUse)
    require(len(collections) == 3, "수집·이용 활동이 계정·위치·관심분야 3개로 분리됨", errors)
    require(all(values(graph, activity, PIPA.hasLegalBasis) for activity in collections),
            "P3-R01: 모든 수집·이용 활동에 설계상 법적근거가 있음", errors)
    require(all(values(graph, activity, PIPA.hasConsentRequest) for activity in collections),
            "P3-R02~R04: 동의요청이 활동별로 연결됨", errors)
    require(all(values(graph, activity, PIPA.hasPurpose) for activity in collections),
            "P3-R02: 목적이 활동별로 연결됨", errors)
    require(all(values(graph, activity, PIPA.hasPersonalInformation) for activity in collections),
            "P3-R03: 개인정보 항목이 활동별로 연결됨", errors)
    require(all(values(graph, activity, PIPA.hasRetention) for activity in collections),
            "P3-R04: 보유정보가 활동별로 연결됨", errors)

    required_items = {item for item in instances(graph, PIPA.PersonalInformation)
                      if any(str(v).lower() == "true" for v in values(graph, item, PIPA.isRequired))}
    require(bool(required_items) and all(values(graph, item, PIPA.designRationale) for item in required_items),
            "P3-R05: 필수 개인정보 항목마다 designRationale이 있음", errors)

    optional_requests = instances(graph, PIPA.ConsentRequest)
    refusal_values = {str(v).lower() for req in optional_requests
                      for v in values(graph, req, PIPA.deniesServiceOnOptionalRefusal)}
    require("false" in refusal_values, "P3-R06: 선택정보 거부 시 전체 서비스 거부가 false로 명시됨", errors)

    end_conditions = instances(graph, PIPA.RetentionEndCondition)
    require(bool(end_conditions) and all(values(graph, end, PIPA.triggersDestruction) for end in end_conditions),
            "P3-R08: 각 보유 종료조건이 파기 활동으로 연결됨", errors)
    require(len(instances(graph, PIPA.EntrustedProcessing)) == 2,
            "P3-R11: 수탁자별 위탁 활동 2개가 분리됨", errors)

    controller = D01.CampusMate
    require(str(next(iter(values(graph, controller, TEST.thirdPartyProvisionState)), "")) == "confirmed_false",
            "제3자 제공 없음이 confirmed_false로 기록됨", errors)
    require(str(next(iter(values(graph, controller, TEST.crossBorderTransferState)), "")) == "confirmed_false",
            "국외이전 없음이 confirmed_false로 기록됨", errors)
    print("  EXPECTED P3-R01/R02/R03/R04/R05/R06/R08/R11 GREEN")


def main():
    shapes = Graph().parse(BASE / "PIPA_Process_Centered_SHACL_v1.0.ttl", format="turtle")
    graphs = {name: Graph().parse(path, format="turtle") for name, path in FILES.items()}
    errors = []

    print("PIPA PoC Freeze v1.0 검증 시작")
    for name, graph in graphs.items():
        shacl_check(graph, shapes, name, errors)

    check_p01(graphs["SC-P01"], errors)
    check_p02(graphs["SC-P02"], errors)
    check_d01(graphs["SC-D01"], errors)

    if errors:
        print(f"\nFINAL: FAIL ({len(errors)}개 항목)")
        return 1
    print("\nFINAL: ALL AVAILABLE TESTS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())

