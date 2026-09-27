import type { BreachCheckRequest, DesignCheckRequest, PolicyCheckRequest } from '../api/compliance'

export const policyDemo: PolicyCheckRequest = {
  analysis_id: 'SC-P01',
  controller: {
    controller_id: 'MoaCommerce',
    name: '주식회사 모아커머스',
  },
  policy_text: `주식회사 모아커머스는 온라인 쇼핑 서비스 모아마켓을 운영합니다.

1. 개인정보 처리 목적
회사는 회원 식별·관리, 상품 주문 및 배송, 결제 및 환불, 고객 상담과 분쟁 처리, 서비스 개선을 위하여 개인정보를 처리합니다.

2. 처리 항목
회원가입 시 이름, 이메일 주소, 휴대전화번호, 비밀번호를 필수로 처리하고 생년월일은 선택적으로 처리합니다. 주문·배송 시 주문자와 수령인의 이름, 휴대전화번호, 이메일 주소, 배송지 주소 및 주문상품 정보를 처리합니다.

3. 보유기간
회원 계정정보는 회원 탈퇴 시까지, 고객 상담 기록은 상담 및 분쟁 처리가 종료될 때까지 처리합니다. 목적 달성 또는 보유기간 종료 후 지체 없이 파기합니다.

4. 제3자 제공
상품 배송을 위해 입점 판매자에게 주문자 이름, 수령인 이름, 휴대전화번호, 배송지 주소와 주문상품 정보를 제공합니다. 제공 목적은 주문 확인, 배송, 교환 및 반품이며 거래 관련 업무 종료 시까지 보유합니다.

5. 처리위탁
모아페이먼츠에 결제·환불, 빠른택배에 배송, 클라우드원에 인프라 운영·데이터 보관, 메시지온에 주문·배송 알림 발송을 위탁합니다.

6. 파기
전자파일은 복구하기 어렵도록 삭제하고 종이문서는 분쇄합니다.

7. 정보주체 권리
이용자는 열람, 정정·삭제, 처리정지, 동의 철회를 요청할 수 있습니다. 마이페이지 개인정보 관리 메뉴 또는 privacy@moamarket.example로 신청할 수 있습니다.`,
}

export const breachDemo: BreachCheckRequest = {
  analysis_id: 'SC-P02',
  controller: {
    controller_id: 'OntoLogistics',
    name: '주식회사 온투로지스틱스',
  },
  incident: {
    incident_id: 'SC-P02-INCIDENT-001',
    description:
      '2026년 9월 5일 뉴스레터 발송 과정에서 수신자 5,200명의 이메일 주소를 숨은참조가 아닌 일반 참조로 입력하여 수신자 사이에 이메일 주소가 노출되었습니다.',
  },
  notification: {
    notice_id: 'SC-P02-NOTICE-001',
    notice_text:
      '2026년 9월 5일 뉴스레터 발송 설정 오류로 고객 이메일 주소가 다른 수신자에게 노출되었습니다. 회사는 잘못된 발송 절차를 중단하고 재발 방지를 위한 발송 검수 절차를 적용했습니다. 의심 메일 삭제와 비밀번호 변경을 권고하며, 문의 및 피해구제는 개인정보보호 담당부서로 접수할 수 있습니다.',
  },
}

export const designDemo: DesignCheckRequest = {
  analysis_id: 'SC-D01',
  controller: {
    controller_id: 'CampusMate',
    name: 'CampusMate',
  },
  collection_activities: [
    {
      activity_id: 'AccountCollection',
      purpose: '회원 식별, 대학생 인증, 본인확인 및 계정 관리',
      legal_basis: { type: 'Consent', status: 'planned' },
      consent_request: { planned: true },
      personal_information_items: [
        { item_name: '이름', is_required: true, design_rationale: '회원 식별' },
        { item_name: '닉네임', is_required: true, design_rationale: '서비스 내 사용자 표시' },
        { item_name: '학교 이메일', is_required: true, design_rationale: '대학생 인증' },
        { item_name: '휴대전화번호', is_required: true, design_rationale: '본인확인' },
      ],
      retention: { end_condition: '회원 탈퇴', destruction_method: '탈퇴 처리 완료 후 삭제' },
      denies_service_on_optional_refusal: false,
    },
    {
      activity_id: 'LocationRecommendation',
      purpose: '주변 모임 검색 및 추천',
      legal_basis: { type: 'Consent', status: 'planned' },
      consent_request: { planned: true },
      personal_information_items: [
        {
          item_name: '현재 위치',
          is_required: false,
          design_rationale: '위치기능 미사용 시 수집하지 않음',
        },
      ],
      retention: {
        end_condition: '주변 모임 추천 처리 완료',
        destruction_method: '처리 완료 후 지속 저장하지 않음',
      },
      denies_service_on_optional_refusal: false,
    },
    {
      activity_id: 'InterestRecommendation',
      purpose: '맞춤형 모임 추천',
      legal_basis: { type: 'Consent', status: 'planned' },
      consent_request: { planned: true },
      personal_information_items: [
        {
          item_name: '관심분야',
          is_required: false,
          design_rationale: '추천기능 미사용 시 수집하지 않음',
        },
      ],
      retention: {
        end_condition: '회원 탈퇴 또는 이용자 설정 삭제',
        destruction_method: '해당 정보 삭제',
      },
      denies_service_on_optional_refusal: false,
    },
  ],
  entrusted_processings: [
    {
      activity_id: 'EntrustKCloud',
      processor: 'K-Cloud 주식회사',
      task: '서비스 서버 및 데이터베이스 운영',
    },
    {
      activity_id: 'EntrustMessageLink',
      processor: 'MessageLink 주식회사',
      task: '휴대전화 인증번호 발송',
    },
  ],
  third_party_provision_state: 'confirmed_false',
  cross_border_transfer_state: 'confirmed_false',
}
