import type { Applicability, RuleStatus } from '../types/api'

const TERM_LABELS: Record<string, string> = {
  collect: '수집·이용 처리행위',
  destroy: '파기 처리행위',
  entrust: '처리위탁 활동',
  user: '정보주체',
  controller: '개인정보처리자',
  incident: '개인정보 유출등 사고',
  'breach-notice': '정보주체 통지문',
  breachNotice: '정보주체 통지문',
  provision: '제3자 제공 처리행위',
  collection: '개인정보 수집 처리행위',
  use: '개인정보 이용 처리행위',
  entrustment: '개인정보 처리위탁 활동',
  retention: '개인정보 보유 활동',
  destruction: '개인정보 파기 활동',
  crossBorderTransfer: '개인정보 국외이전 활동',
  CollectionAndUse: '개인정보 수집·이용',
  PersonalInformationProcessing: '개인정보 처리',
  ThirdPartyProvision: '제3자 제공',
  EntrustedProcessing: '개인정보 처리위탁',
  CrossBorderTransfer: '개인정보 국외이전',
  Retention: '개인정보 보유',
  Destruction: '개인정보 파기',
  DataSubject: '정보주체',
  DataSubjectRight: '정보주체 권리',
  RightsExerciseProcedure: '권리 행사절차',
  DataBreachIncident: '개인정보 유출등 사고',
  NotificationNotice: '정보주체 통지문',
  ConsentRequest: '동의요청',
  PersonalInformation: '개인정보',
  LegalBasis: '법적 근거',
  ProcessingPurpose: '처리 목적',
  RetentionPeriod: '보유기간',
  RetentionEndCondition: '보유 종료조건',
  EntrustedProcessor: '수탁자',
  ThirdParty: '제3자',
  DestinationCountry: '이전 대상 국가',
  ResponseMeasure: '사고 대응조치',
  hasPurpose: '처리 목적',
  hasPurposeDescription: '처리 목적 설명',
  hasPersonalInformation: '처리 개인정보',
  hasItemName: '개인정보 항목명',
  hasName: '명칭',
  hasRecipient: '제공받는 자',
  hasProcessor: '수탁자',
  hasLegalBasis: '법적 근거',
  hasRetention: '보유정보',
  hasRetentionPeriod: '보유기간',
  hasDurationValue: '보유기간 값',
  hasRetentionEndCondition: '보유 종료조건',
  hasEndConditionDescription: '보유 종료조건 설명',
  triggersDestruction: '파기 계획',
  hasDestructionMethod: '파기 방법',
  hasDestinationCountry: '이전 대상 국가',
  hasRight: '보장된 정보주체 권리',
  hasExerciseProcedure: '권리 행사절차',
  hasProcedureDescription: '권리 행사방법 설명',
  hasNotificationNotice: '정보주체 통지문',
  affectsPersonalInformation: '실제 사고 영향 개인정보',
  mentionsPersonalInformation: '통지문 기재 개인정보',
  incidentDate: '실제 사고 발생시점',
  detectionDate: '사고 인지시점',
  notificationDate: '통지시점',
  noticeIncidentTime: '통지문 기재 사고시점',
  hasIncidentCircumstances: '통지문 기재 사고경위',
  hasResponseMeasure: '사고 대응조치',
  measureRole: '대응조치 역할',
  entrustedTaskText: '위탁업무',
  hasConsentRequest: '동의요청',
  isRequired: '필수 항목 여부',
  designRationale: '수집 필요성',
  deniesServiceOnOptionalRefusal: '선택정보 거부 시 서비스 제한 여부',
  hasSourceEvidence: '입력 문서의 원문 근거',
  activityPresence: '처리행위 존재 여부',
  collectionAndUseState: '수집·이용 존재 여부',
  thirdPartyProvisionState: '제3자 제공 존재 여부',
  entrustedProcessingState: '처리위탁 존재 여부',
  dataBreachIncidentState: '개인정보 유출등 사고 존재 여부',
  notificationNoticeState: '정보주체 통지문 존재 여부',
}

const RULE_LABELS: Record<string, string> = {
  'P1-R01': '처리목적 명시',
  'P1-R02': '처리·보유기간 명시',
  'P1-R03': '제3자 제공 기재',
  'P1-R04': '파기 절차·방법 기재',
  'P1-R06': '처리위탁 기재',
  'P1-R07': '정보주체 권리행사 방법',
  'P2-R01': '개인정보 유출등 사고와 통지문 확인',
  'P2-R02': '통지 개인정보 항목 확인',
  'P2-R03': '통지 시점·경위 확인',
  'P2-R08': '피해 최소화·대응·구제 정보 확인',
  'P3-R01': '수집·이용 법적 근거 확인',
  'P3-R02': '동의 처리목적 고지 설계',
  'P3-R03': '동의 개인정보 항목 고지 설계',
  'P3-R04': '동의 보유·이용기간 고지 설계',
  'P3-R05': '최소수집 설계 사유',
  'P3-R06': '선택항목 미동의 시 서비스 거부 금지',
  'P3-R08': '보유 종료 후 파기 설계',
  'P3-R11': '처리위탁 설계',
}

const FACT_LABELS: Record<string, string> = {
  'F1-01': '수집·이용 활동', 'F1-02': '처리 목적', 'F1-03': '보유기간',
  'F1-04': '보유 종료조건', 'F1-05': '제공받는 자', 'F1-06': '제공 개인정보',
  'F1-07': '제3자 제공 목적', 'F1-08': '파기 방법', 'F1-09': '수탁자',
  'F1-10': '위탁업무', 'F1-11': '정보주체 권리', 'F1-12': '권리 행사절차',
  'F2-01': '개인정보 유출등 사고', 'F2-02': '실제 사고 영향 개인정보',
  'F2-03': '사고와 통지문 연결', 'F2-04': '통지문 기재 개인정보',
  'F2-05': '실제 사고 발생시점', 'F2-06': '사고 인지시점', 'F2-07': '통지시점',
  'F2-08': '통지문 기재 사고시점', 'F2-09': '통지문 기재 사고경위',
  'F2-10': '사고 대응조치', 'F3-01': '수집·이용 활동', 'F3-02': '처리 법적 근거',
  'F3-03': '동의요청 설계', 'F3-04': '처리 목적', 'F3-05': '처리 개인정보',
  'F3-06': '보유·파기 계획', 'F3-07': '필수 항목 여부', 'F3-08': '수집 필요성',
  'F3-09': '선택정보 거부 시 서비스 제한 여부', 'F3-10': '보유 종료조건',
  'F3-11': '파기 계획', 'F3-12': '수탁자', 'F3-13': '위탁업무',
}

const STATE_LABELS: Record<string, string> = {
  confirmed: '확인됨', confirmed_true: '있음이 명시적으로 확인됨',
  confirmed_false: '없음이 명시적으로 확인됨', unknown: '추가 확인 필요',
  absent: '문서에서 확인되지 않음', missing_envelope: '입력 데이터가 전달되지 않음',
  true: '예', false: '아니오',
}

const ROLE_LABELS: Record<string, string> = {
  data_subject_guidance: '정보주체 피해 최소화 안내',
  controller_response: '개인정보처리자의 대응조치',
  remedy_procedure: '피해구제 절차 안내',
  post_incident_mitigation: '사고 후 피해 완화조치',
}

const EVIDENCE_TYPE_LABELS: Record<string, string> = {
  source_text: '원문 근거', rdf_assertion: '확인된 관계',
  absence: '확인 필요', fact_contract: '입력자료 확인',
}

function localName(value: string): string {
  const withoutQuery = value.split('?')[0]
  const index = Math.max(
    withoutQuery.lastIndexOf('#'),
    withoutQuery.lastIndexOf('/'),
    withoutQuery.lastIndexOf(':'),
  )
  const candidate = index >= 0 ? withoutQuery.slice(index + 1) : withoutQuery
  try {
    return decodeURIComponent(candidate)
  } catch {
    return candidate
  }
}

function readableFallback(value: string): string {
  return value.replace(/([a-z0-9])([A-Z])/g, '$1 $2').replace(/[_-]+/g, ' ').trim() || value
}

export function termLabel(value: string): string {
  const name = localName(value)
  return TERM_LABELS[name]
    ?? FACT_LABELS[name]
    ?? ROLE_LABELS[name]
    ?? generatedResourceLabel(name)
    ?? readableFallback(name)
}

function generatedResourceLabel(value: string): string | null {
  const normalized = value.toLowerCase().replaceAll('-', '_')
  const patterns: Array<[RegExp, string]> = [
    [/^rights?_procedure_[0-9a-f]{6,}$/, '권리 행사절차'],
    [/^right_[0-9a-f]{6,}$/, '정보주체 권리'],
    [/^(personal_?information|pi)_[0-9a-f]{6,}$/, '개인정보 항목'],
    [/^purpose_[0-9a-f]{6,}$/, '처리 목적'],
    [/^(third_?party|recipient)_[0-9a-f]{6,}$/, '제공받는 자'],
    [/^processor_[0-9a-f]{6,}$/, '수탁자'],
    [/^retention_[0-9a-f]{6,}$/, '보유정보'],
    [/^retention_period_[0-9a-z]{6,}$/, '보유기간'],
    [/^(legal_?basis|basis)_[0-9a-f]{6,}$/, '법적 근거'],
    [/^(destruction|destroy)_[0-9a-f]{6,}$/, '파기 계획'],
    [/^(response_?measure|measure)_[0-9a-f]{6,}$/, '사고 대응조치'],
    [/^f2_10_\d+_measure_\d+$/, '사고 대응조치'],
    [/^(act_)?collect(ion)?_\d+$/, '수집·이용 처리행위'],
    [/^(act_)?destroy(uction)?_\d+$/, '파기 처리행위'],
    [/^(act_)?entrust(ment)?_\d+$/, '처리위탁 활동'],
    [/^breach_?notice(?:_[0-9a-z]+)?$/, '정보주체 통지문'],
  ]
  return patterns.find(([pattern]) => pattern.test(normalized))?.[1] ?? null
}

export function humanizeFactReference(value: string): string {
  const factMatch = /^fact:(F[123]-\d{2}):(.+)$/.exec(value)
  if (factMatch) {
    return `${FACT_LABELS[factMatch[1]] ?? factMatch[1]} — ${STATE_LABELS[factMatch[2]] ?? termLabel(factMatch[2])}`
  }

  const rdfMatch = /^rdf:([^:]+):([^:]+)$/.exec(value)
  if (rdfMatch) {
    const subject = termLabel(rdfMatch[1])
    const predicate = termLabel(rdfMatch[2])
    return subject === predicate ? predicate : `${subject} · ${predicate}`
  }

  const metadataMatch = /^metadata:([^=]+)=(.+)$/.exec(value)
  if (metadataMatch) {
    return `${termLabel(metadataMatch[1])} — ${STATE_LABELS[metadataMatch[2]] ?? termLabel(metadataMatch[2])}`
  }

  const typedMatch = /^(measure_role|unexpected_measure_role|legal_basis_type|notice_item):(.+)$/.exec(value)
  if (typedMatch) {
    const headings: Record<string, string> = {
      measure_role: '필수 대응조치', unexpected_measure_role: '정의되지 않은 대응조치',
      legal_basis_type: '법적 근거 유형', notice_item: '통지문에 기재할 개인정보',
    }
    return `${headings[typedMatch[1]]} · ${termLabel(typedMatch[2])}`
  }

  if (value === 'applicability') return '규칙 적용 대상 여부'
  if (value === 'no_optional_items') return '선택 개인정보 항목 없음'

  const dotted = /^([A-Za-z][A-Za-z0-9_]*)\.([A-Za-z][A-Za-z0-9_/]*)$/.exec(value)
  if (dotted) {
    return `${termLabel(dotted[1])} · ${dotted[2].split('/').map(termLabel).join(' 또는 ')}`
  }
  return humanizeDisplayValue(value)
}

export function humanizeDisplayValue(value: string): string {
  if (STATE_LABELS[value]) return STATE_LABELS[value]
  const parts = value.includes('|')
    ? value.split('|').map((part) => part.trim()).filter(Boolean)
    : [value]
  return parts.map((part) => {
    if (/^(https?:\/\/|urn:)/.test(part)) return termLabel(part)
    return TERM_LABELS[part]
      ?? FACT_LABELS[part]
      ?? ROLE_LABELS[part]
      ?? generatedResourceLabel(part)
      ?? part
  }).join(' · ')
}

export function evidenceTypeLabel(value: string): string {
  return EVIDENCE_TYPE_LABELS[value] ?? '판단 근거'
}

export function ruleLabel(ruleId: string): string {
  return RULE_LABELS[ruleId] ?? '개인정보 보호법 준수 검토'
}

export function statusLabel(status: RuleStatus): string {
  return { GREEN: '충족', YELLOW: '추가 확인', RED: '미충족', 'N/A': '해당 없음' }[status]
}

export function applicabilityLabel(value: Applicability): string {
  return { TRUE: '적용 대상', FALSE: '적용 대상 아님', UNKNOWN: '확인 필요' }[value]
}

export function humanizeNarrative(value: string): string {
  const narrativeLabels: Record<string, string> = {
    measure_role: '대응조치 유형',
    data_subject_guidance: '정보주체 피해 최소화 안내',
    controller_response: '개인정보처리자의 대응조치',
    remedy_procedure: '피해구제 절차 안내',
    post_incident_mitigation: '사고 후 피해 완화조치',
    confirmed_false: '없음이 명시적으로 확인된 상태',
    UNKNOWN: '확인 필요',
    ProcessingPurpose: '처리 목적',
    hasPurposeDescription: '처리 목적 설명',
    hasPurpose: '처리 목적',
    Destruction: '개인정보 파기',
    hasDestructionMethod: '파기 방법',
    DataBreachIncident: '개인정보 유출등 사고',
    affectsPersonalInformation: '실제 사고 영향 개인정보',
    NotificationNotice: '정보주체 통지문',
    hasNotificationNotice: '정보주체 통지문',
    incidentDate: '실제 사고 발생시점',
    CollectionAndUse: '개인정보 수집·이용',
    ConsentRequest: '동의요청',
    RetentionPeriod: '보유기간',
    RetentionEndCondition: '보유 종료조건',
    Retention: '개인정보 보유',
    isRequired: '필수 항목 여부',
    designRationale: '수집 필요성',
    deniesServiceOnOptionalRefusal: '선택정보 거부 시 서비스 제한 여부',
    triggersDestruction: '파기 계획',
    EntrustedProcessor: '수탁자',
    hasName: '명칭',
    entrustedTaskText: '위탁업무',
  }

  let result = value
    .replace(
      /measure_role을 data_subject_guidance, controller_response, remedy_procedure, post_incident_mitigation 4종으로만 구분해 명시하세요\./g,
      '대응조치를 정보주체 피해 최소화 안내, 개인정보처리자의 대응조치, 피해구제 절차 안내, 사고 후 피해 완화조치의 네 유형으로 구분해 명시하세요.',
    )
    .replaceAll('processing activity', '처리행위')
    .replaceAll('해당 activity', '해당 처리행위')
    .replaceAll('activity 연결', '처리행위와의 연결')
    .replaceAll('provision', '제3자 제공 처리행위')

  for (const [technicalTerm, label] of Object.entries(narrativeLabels)) {
    result = result.replace(new RegExp(`\\b${technicalTerm}\\b`, 'g'), label)
  }
  result = result
    .replace(/\bF[123][- ]?\d{2}(?:[- ]?\d{3})?\b/g, '관련 검토 항목')
    .replace(/\bP[123]-R\d{2}\b/g, '해당 준수 기준')
  return result
}
