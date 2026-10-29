import type { Applicability, RuleStatus } from '../types/api'

const TERM_LABELS: Record<string, string> = {
  collect: '수집·이용 처리행위',
  destroy: '파기 처리행위',
  entrust: '처리위탁 활동',
  user: '정보주체',
  controller: '개인정보처리자',
  incident: '개인정보 유출등 사고',
  'breach-incident': '개인정보 유출등 사고',
  'breach-notice': '정보주체 통지문',
  breachNotice: '정보주체 통지문',
  provision: '제3자 제공 처리행위',
  collection: '개인정보 수집 처리행위',
  use: '개인정보 이용 처리행위',
  entrustment: '개인정보 처리위탁 활동',
  retention: '개인정보 보유 활동',
  destruction: '개인정보 파기 활동',
  crossBorderTransfer: '개인정보 국외이전 활동',
  crossborder: '국외 이전 처리행위',
  'privacy-officer': '개인정보 보호책임자',
  __document__: '문서 전체',
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
  Consent: '동의',
  // PoC3 법적 근거 유형. 입력 화면(DesignCheckPage)의 선택지 이름과 같게 둔다.
  Contract: '계약 이행',
  LegalObligation: '법적 의무',
  LegitimateInterest: '정당한 이익 검토',
  PersonalInformation: '개인정보',
  LegalBasis: '법적 근거',
  ProcessingPurpose: '처리 목적',
  RetentionPeriod: '보유기간',
  RetentionEndCondition: '보유 종료조건',
  EntrustedProcessor: '수탁자',
  ThirdParty: '제3자',
  DestinationCountry: '이전 대상 국가',
  OverseasRecipient: '국외 이전받는 자',
  PersonalInformationController: '개인정보처리자',
  PrivacyOfficer: '개인정보 보호책임자',
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
  hasTransferRecipient: '국외 이전받는 자',
  hasTransferTimingAndMethod: '이전 시기 및 방법',
  hasTransferRefusalProcedure: '이전 거부 방법·절차·효과',
  hasPrivacyOfficer: '개인정보 보호책임자',
  hasPersonName: '성명',
  hasDepartmentName: '부서 명칭',
  hasContact: '연락처',
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
  crossBorderTransferState: '국외 이전 존재 여부',
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
  'P1-R08': '정보주체 권리 목록 누락 점검',
  'P1-R09': '국외 이전 기재',
  'P1-R10': '개인정보 보호책임자·연락처 기재',
  'P1-R11': '처리하는 개인정보 항목 기재',
  'P2-R01': '개인정보 유출등 사고와 통지문 확인',
  'P2-R02': '통지 개인정보 항목 확인',
  'P2-R03': '통지 시점·경위 확인',
  'P2-R08': '피해 최소화·대응·구제 정보 확인',
  'P2-R09': '사고 기록과 통지문 기재 사고 시점 일치',
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
  'F1-13': '이전 대상 국가', 'F1-14': '이전 개인정보 항목', 'F1-15': '이전받는 자의 이용 목적',
  'F1-16': '이전받는 자 성명·명칭', 'F1-17': '이전받는 자 연락처',
  'F1-18': '이전 시기 및 방법', 'F1-19': '이전 거부 방법·절차·효과',
  'F1-20': '보호책임자 성명 또는 담당 부서', 'F1-21': '보호책임자 연락처',
  'F1-22': '처리하는 개인정보 항목',
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
  confirmed_false: '없음이 명시적으로 확인됨', unknown: '확인 필요',
  absent: '명시적으로 없음', missing_envelope: '입력 데이터가 전달되지 않음',
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

const ACTIVITY_LABELS: Record<string, string> = {
  AccountCollection: '계정 정보 수집',
  LocationRecommendation: '위치 기반 모임 추천',
  InterestRecommendation: '관심분야 맞춤 추천',
  EntrustKCloud: 'K-Cloud 서버 운영 위탁',
  EntrustMessageLink: 'MessageLink 인증번호 발송 위탁',
}

const ACTIVITY_SUFFIX_LABELS: Array<[string, string]> = [
  ['-retention-end', '보유 종료조건'],
  ['-retention', '보유정보'],
  ['-destruction', '파기 계획'],
  ['-consent-request', '동의요청'],
]

/** 사용자 입력 activity_id를 한글 명칭으로. 등록되지 않은 ID는 원문 ID를 그대로 보여 서로 구분되게 한다. */
export function activityLabel(activityId: string): string {
  return ACTIVITY_LABELS[activityId] ?? `'${activityId}'`
}

/** `{activity_id}-destruction` 같은 매퍼 생성 ID → `계정 정보 수집 · 파기 계획`. */
export function activityResourceLabel(name: string): string | null {
  for (const [suffix, label] of ACTIVITY_SUFFIX_LABELS) {
    if (name.length > suffix.length && name.endsWith(suffix)) {
      return `${activityLabel(name.slice(0, -suffix.length))} · ${label}`
    }
  }
  return null
}

/** 파기 객체 ID(`X-destruction`)에서 처리행위 ID를 추출. */
function destructionActivityId(text: string | null | undefined): string | null {
  if (!text) return null
  const name = localName(text)
  const match = /^(.+)-destruction$/.exec(name)
  return match ? match[1] : null
}

interface InstanceLike {
  instance_id: string
  matched_facts: string[]
  missing_facts: string[]
  uncertain_facts: string[]
  evidence: Array<{ subject: string | null; value: string | boolean | null }>
}

function instanceActivityId(instance: InstanceLike): string | null {
  const candidates: Array<string | null> = [
    ...[...instance.matched_facts, ...instance.uncertain_facts, ...instance.missing_facts].map((fact) => {
      const rdf = /^rdf:([^:]+):[^:]+$/.exec(fact)
      return destructionActivityId(rdf?.[1])
    }),
    ...instance.evidence.flatMap((item) => [
      destructionActivityId(item.subject),
      destructionActivityId(typeof item.value === 'string' ? item.value : null),
    ]),
  ]
  return candidates.find((id): id is string => id !== null) ?? null
}

/** 해시 기반 인스턴스 ID(보유 종료조건 등)를 같은 인스턴스의 파기 객체로부터 처리행위별로 구분한다. */
export function instanceLabel(instance: InstanceLike): string {
  const base = termLabel(instance.instance_id)
  const activityId = instanceActivityId(instance)
  return activityId ? `${activityLabel(activityId)} — ${base}` : base
}

/** 해시 인스턴스 로컬명 → 처리행위 한글명. 규칙 단위 fact 목록에서 동일 라벨 반복을 구분하는 데 쓴다. */
export function instanceActivityAliases(instances: InstanceLike[]): Record<string, string> {
  const aliases: Record<string, string> = {}
  for (const instance of instances) {
    const activityId = instanceActivityId(instance)
    if (activityId) aliases[localName(instance.instance_id)] = activityLabel(activityId)
  }
  return aliases
}

export function termLabel(value: string): string {
  const name = localName(value)
  return TERM_LABELS[name]
    ?? FACT_LABELS[name]
    ?? ROLE_LABELS[name]
    ?? generatedResourceLabel(name)
    ?? activityResourceLabel(name)
    ?? ACTIVITY_LABELS[name]
    ?? readableFallback(name)
}

export function generatedResourceLabel(value: string): string | null {
  const normalized = value.toLowerCase().replaceAll('-', '_')
  // LLM 추출기가 만드는 대응조치 ID: `F2-10:breach-incident-measure-N` (번호는 보존)
  const measure = /^f2_10:breach_incident(?:#\d+)?_measure_(\d+)$/.exec(normalized)
  if (measure) return `사고 대응조치 (${measure[1]})`
  const patterns: Array<[RegExp, string]> = [
    [/^rights?_procedure_[0-9a-f]{6,}$/, '권리 행사절차'],
    [/^right_[0-9a-f]{6,}$/, '정보주체 권리'],
    [/^(personal_?information|pi)_[0-9a-f]{6,}$/, '개인정보 항목'],
    [/^purpose_[0-9a-f]{6,}$/, '처리 목적'],
    [/^(third_?party|recipient)_[0-9a-f]{6,}$/, '제공받는 자'],
    [/^processor_[0-9a-f]{6,}$/, '수탁자'],
    [/^overseas_recipient_[0-9a-f]{6,}$/, '국외 이전받는 자'],
    [/^privacy_officer_[0-9a-f]{6,}$/, '개인정보 보호책임자'],
    [/^country_[0-9a-f]{6,}$/, '이전 대상 국가'],
    [/^retention_[0-9a-f]{6,}$/, '보유정보'],
    [/^retention_period_[0-9a-z]{6,}$/, '보유기간'],
    [/^retention_end_[0-9a-f]{6,}$/, '보유 종료조건'],
    [/^consent_?request_[0-9a-f]{6,}$/, '동의요청'],
    [/^(legal_?basis|basis)_[0-9a-f]{6,}$/, '법적 근거'],
    [/^(destruction|destroy)_[0-9a-f]{6,}$/, '파기 계획'],
    [/^(response_?measure|measure)_[0-9a-f]{6,}$/, '사고 대응조치'],
    [/^f2_10_\d+_measure_\d+$/, '사고 대응조치'],
    [/^(act_)?collect(ion)?_\d+$/, '수집·이용 처리행위'],
    [/^(act_)?destr(oy|uction)_\d+$/, '파기 처리행위'],
    [/^(act_)?entrust(ment)?_\d+$/, '처리위탁 활동'],
    [/^(act_)?(third_?party_?)?provision_\d+$/, '제3자 제공 처리행위'],
    [/^(act_)?cross_?border(_?transfer)?_\d+$/, '국외 이전 처리행위'],
    [/^breach_?notice(?:_[0-9a-z]+)?$/, '정보주체 통지문'],
  ]
  return patterns.find(([pattern]) => pattern.test(normalized))?.[1] ?? null
}

export function humanizeFactReference(
  value: string,
  subjectAliases: Record<string, string> = {},
): string {
  const factMatch = /^fact:(F[123]-\d{2}):(.+)$/.exec(value)
  if (factMatch) {
    return `${FACT_LABELS[factMatch[1]] ?? factMatch[1]} — ${STATE_LABELS[factMatch[2]] ?? termLabel(factMatch[2])}`
  }

  const rdfMatch = /^rdf:([^:]+):([^:]+)$/.exec(value)
  if (rdfMatch) {
    const alias = subjectAliases[rdfMatch[1]]
    const subject = alias ? `${alias} — ${termLabel(rdfMatch[1])}` : termLabel(rdfMatch[1])
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

  // P1-R08: `right:<권리>` 미확인 권리, `right:unrecognized:<문구>` 인식하지 못한 권리 표현
  const unrecognizedRight = /^right:unrecognized:(.+)$/.exec(value)
  if (unrecognizedRight) return `인식하지 못한 권리 표현 · ${unrecognizedRight[1]}`
  const missingRight = /^right:(.+)$/.exec(value)
  if (missingRight) return `확인되지 않은 정보주체 권리 · ${missingRight[1]}`

  // P1-R09 / P1-R10: 항목 이름은 엔진이 한글로 보낸다
  const transferItem = /^transfer_item:(.+)$/.exec(value)
  if (transferItem) return `국외 이전 기재사항 · ${transferItem[1]}`
  const officerItem = /^officer_item:(.+)$/.exec(value)
  if (officerItem) return `보호책임자 기재사항 · ${officerItem[1]}`

  if (value === 'applicability') return '규칙 적용 대상 여부'
  if (value === 'no_optional_items') return '선택 개인정보 항목 없음'
  // P2-R09
  if (value === 'incident_time_mismatch') return '사고 기록과 통지문의 사고 시점이 다름'
  if (value === 'incident_time_precision') return '날짜는 같으나 한쪽에 시각이 없음'

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
      ?? activityResourceLabel(part)
      ?? ACTIVITY_LABELS[part]
      ?? part
  }).join(' · ')
}

export function evidenceTypeLabel(value: string): string {
  return EVIDENCE_TYPE_LABELS[value] ?? '판단 근거'
}

export function ruleLabel(ruleId: string): string {
  return RULE_LABELS[ruleId] ?? '개인정보 보호법 준수 검토'
}

/** 상태 배지는 영어 원문(GREEN/YELLOW/RED/N/A)만 표시한다. */
export function statusLabel(status: RuleStatus): string {
  return status
}

export function applicabilityLabel(value: Applicability): string {
  return { TRUE: '적용 대상', FALSE: '적용 대상 아님', UNKNOWN: '확인 필요' }[value]
}

const P2_R03_RECHECK_RECOMMENDATION =
  '필수 Fact의 value_state를 confirmed 또는 명시적 absent로 확정한 뒤 다시 평가하세요.'

/** 마지막 글자에 받침이 있으면 '이', 없으면 '가'. 한글이 아니면 '가'. */
function withSubjectParticle(word: string): string {
  const code = word.charCodeAt(word.length - 1) - 0xac00
  return code >= 0 && code < 11172 && code % 28 !== 0 ? '이' : '가'
}

export function humanizeNarrative(value: string, ruleId?: string): string {
  // 같은 문장이 여러 규칙에 쓰이므로 P2-R03(통지 시점·경위)에서만 사고시점 문맥으로 바꾼다.
  if (ruleId === 'P2-R03') {
    value = value.replaceAll(
      P2_R03_RECHECK_RECOMMENDATION,
      '사고시점에 관한 정보를 추가 확인하고, 확인 결과를 반영하여 다시 검토하세요.',
    )
  }

  const narrativeLabels: Record<string, string> = {
    measure_role: '대응조치 유형',
    data_subject_guidance: '정보주체 피해 최소화 안내',
    controller_response: '개인정보처리자의 대응조치',
    remedy_procedure: '피해구제 절차 안내',
    post_incident_mitigation: '사고 후 피해 완화조치',
    confirmed_false: '없음이 명시적으로 확인된 상태',
    UNKNOWN: '확인 필요',
    value_state: '정보 확인 상태',
    confirmed: '확인됨',
    absent: '명시적으로 없음',
    threshold: '판단 기준',
    ProcessingPurpose: '처리 목적',
    hasPurposeDescription: '처리 목적 설명',
    hasPurpose: '처리 목적',
    Destruction: '개인정보 파기',
    hasDestructionMethod: '파기 방법',
    DataBreachIncident: '개인정보 유출등 사고',
    'breach-incident': '개인정보 유출등 사고',
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

  // 백엔드 문장 중 개발자 용어가 섞인 구절은 문맥이 보존되도록 구절 단위로 먼저 바꾼다.
  const phrases: Array<[string | RegExp, string]> = [
    ['Frozen Fact input contract에서 필수 Fact가 absent로 확인되었습니다.',
      '필수 검토 정보 중 일부가 명시적으로 없는 것으로 확인되었습니다.'],
    ['Frozen Fact input contract가 불완전하거나 UNKNOWN 상태를 포함합니다.',
      '필수 검토 정보가 충분히 전달되지 않았거나 확인이 필요한 상태를 포함합니다.'],
    ['absent인 필수 Fact를 원문/구조화 Form 근거로 보완한 뒤 다시 평가하세요.',
      '명시적으로 없는 것으로 확인된 필수 검토 정보를 원문 또는 입력 양식의 근거로 보완한 뒤 다시 검토하세요.'],
    ['필수 Fact의 value_state를 confirmed 또는 명시적 absent로 확정한 뒤 다시 평가하세요.',
      "필수 검토 정보의 정보 확인 상태를 '확인됨' 또는 '명시적으로 없음'으로 확정한 뒤 다시 검토하세요."],
    ['명시적 부재(confirmed_false)', '없음이 명시적으로 확인된 상태'],
    ['UNKNOWN/모호', '확인 필요 또는 모호'],
    ['threshold를', '판단 기준을'],
    ['absent로', '명시적으로 없음으로'],
    ['RDF 그래프에서', '분석 데이터에서'],
    ['Fact extraction 단계', '정보 추출 단계'],
    [/P\d-R\d{2} frozen coverage의 F\d-\d{2} /g, '필수 검토 범위의 '],
    ['frozen coverage', '필수 검토 범위'],
    ['대응정보는 존재하지만 v1 필수 4개 역할 중 일부가 누락되었거나 허용되지 않은 역할 값이 포함되어 있습니다.',
      '대응정보는 존재하지만 필수 대응조치 4개 유형 중 일부가 확인되지 않았거나 허용되지 않은 유형이 포함되어 있습니다.'],
    ['v1에서 허용된', '현재 버전에서 허용된'],
    ['isRequired=true인 각 항목', '필수 항목으로 지정된 각 항목'],
    ['deniesServiceOnOptionalRefusal을 true/false로', '선택정보 거부 시 서비스 제한 여부를 예 또는 아니오로'],
    ['서비스 제공 거부가 false로 명시', "서비스 제공 거부가 '아니오'로 명시"],
  ]
  // 처리행위 부재 판정 문장(`{클래스}가 없다고 …`, `{클래스}의 존재/부재를 …`)은 조사까지 맞춰 바꾼다.
  const activityClassLabels: Record<string, string> = {
    ThirdPartyProvision: '제3자 제공',
    EntrustedProcessing: '개인정보 처리위탁',
    CrossBorderTransfer: '개인정보 국외 이전',
    NotificationNotice: '정보주체 통지문',
  }
  let result = value.replace(
    /\b(ThirdPartyProvision|EntrustedProcessing|CrossBorderTransfer|NotificationNotice)(가 없다고|의 존재\/부재를)/g,
    (_, cls: string, tail: string) => {
      const label = activityClassLabels[cls]
      return tail.startsWith('가')
        ? `${label}${withSubjectParticle(label)} 없다고`
        : `${label}의 존재 여부를`
    },
  )
  for (const [from, to] of phrases) {
    result = typeof from === 'string' ? result.replaceAll(from, to) : result.replace(from, to)
  }
  result = result
    .replace(
      /\b(?:rights?[-_ ]procedure|retention[-_ ]period|retention[-_ ]end|consent[-_ ]request|legal[-_ ]basis|third[-_ ]party|right|retention|purpose|processor|pi)[-_ ][0-9a-f]{12}\b/gi,
      (match) => generatedResourceLabel(match.replace(/ /g, '_')) ?? match,
    )
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
    .replace(/\bFact\b/g, '검토 정보')
  return result
}

const EVALUATED_AT_WITH_OFFSET =
  /^(\d{4}-\d{2}-\d{2})[T ](\d{2}:\d{2})(:\d{2})?(\.\d+)?(Z|[+-]\d{2}:?\d{2})$/i

/**
 * `검토 시각`을 `YYYY.MM.DD HH:mm (KST)`로 표시한다.
 * UTC(Z) 또는 오프셋이 명시된 값만 Asia/Seoul로 변환하고, 시간대 정보가 없거나
 * 해석할 수 없는 값은 임의로 가정하지 않고 원문을 그대로 돌려준다.
 */
export function formatEvaluatedAt(value: string): string {
  const match = EVALUATED_AT_WITH_OFFSET.exec(value.trim())
  if (!match) return value
  const [, date, hm, seconds = '', , zone] = match
  const offset = /^z$/i.test(zone) ? 'Z' : zone.includes(':') ? zone : `${zone.slice(0, 3)}:${zone.slice(3)}`
  const parsed = new Date(`${date}T${hm}${seconds || ':00'}${offset}`)
  if (Number.isNaN(parsed.getTime())) return value
  const parts = Object.fromEntries(
    new Intl.DateTimeFormat('en-GB', {
      timeZone: 'Asia/Seoul', hourCycle: 'h23',
      year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit',
    }).formatToParts(parsed).map((part) => [part.type, part.value]),
  )
  return `${parts.year}.${parts.month}.${parts.day} ${parts.hour}:${parts.minute} (KST)`
}

/** `Fact IDs: F2-08:breach-notice` → `관련 검토 항목: 정보주체 통지문` (대상 객체가 없으면 원문 유지). */
export function humanizeFactIdsNote(note: string): string {
  const match = /^Fact IDs:\s*(.+)$/.exec(note)
  if (!match) return note
  const subjects = match[1].split(',').map((id) => /^\s*F[123]-\d{2}:([^#\s]+)(?:#\d+)?\s*$/.exec(id)?.[1])
  if (subjects.some((subject) => !subject)) return note
  const labels = [...new Set(subjects.map((subject) => termLabel(subject as string)))]
  return `관련 검토 항목: ${labels.join(', ')}`
}

const RED_WITHOUT_MISSING_NOTICE =
  '필수 검토 정보의 누락은 없지만, 확인된 내용이 해당 검토 기준을 충족하지 않아 미충족으로 판정되었습니다.'

/** PoC3 RED인데 누락 항목이 없을 때만 보여 줄 안내. 그 외에는 null. */
export function redWithoutMissingNotice(
  ruleId: string,
  status: RuleStatus,
  missingFacts: string[],
): string | null {
  return /^P3-/.test(ruleId) && status === 'RED' && missingFacts.length === 0
    ? RED_WITHOUT_MISSING_NOTICE
    : null
}
