import assert from 'node:assert/strict'
import { test } from 'node:test'
import { evidenceNotInInstances } from '../src/utils/evidence.ts'
import {
  humanizeDisplayValue, humanizeFactReference, humanizeNarrative, instanceActivityAliases,
  formatEvaluatedAt, humanizeFactIdsNote, instanceLabel, redWithoutMissingNotice, termLabel,
} from '../src/utils/complianceLabels.ts'

const ev = (note: string) => ({
  evidence_type: 'absence', subject: null, predicate: null, value: null, source_text: null, note,
})

test('consent_request / consent-request hash is shown as 동의요청', () => {
  assert.equal(termLabel('consent_request_67435ec65d29'), '동의요청')
  assert.equal(termLabel('http://x/instance/consent-request-67435ec65d29'), '동의요청')
  assert.equal(humanizeDisplayValue('consent_request_67435ec65d29'), '동의요청')
  assert.equal(termLabel('retention-end-0123456789ab'), '보유 종료조건')
  assert.equal(humanizeNarrative('consent request 67435ec65d29 누락'), '동의요청 누락')
})

test('top-level evidence already shown per instance is not repeated', () => {
  const a = ev('a'), b = ev('b'), c = ev('c')
  const out = evidenceNotInInstances([a, b, c], [{ evidence: [{ ...a }, { ...b }] }])
  assert.deepEqual(out, [c])
  assert.deepEqual(evidenceNotInInstances([a, b], [{ evidence: [a, b] }]), [])
  assert.deepEqual(evidenceNotInInstances([a], []), [a])
})

test('PoC3 activity-derived resource IDs get Korean, distinguishable labels', () => {
  assert.equal(termLabel('AccountCollection-destruction'), '계정 정보 수집 · 파기 계획')
  assert.equal(
    humanizeDisplayValue('http://x/instance/LocationRecommendation-destruction'),
    '위치 기반 모임 추천 · 파기 계획',
  )
  assert.equal(termLabel('InterestRecommendation-retention-end'), '관심분야 맞춤 추천 · 보유 종료조건')
  assert.equal(termLabel('MyCustomActivity-destruction'), "'MyCustomActivity' · 파기 계획")
  assert.equal(humanizeFactReference('rdf:LocationRecommendation-destruction:hasDestructionMethod'),
    '위치 기반 모임 추천 · 파기 계획 · 파기 방법')
})

test('identical hashed retention-end instances are told apart by activity, none dropped', () => {
  const mk = (hash: string, activity: string) => ({
    instance_id: `http://x/instance/retention-end-${hash}`,
    matched_facts: [
      `rdf:retention-end-${hash}:triggersDestruction`,
      `rdf:${activity}-destruction:hasDestructionMethod`,
    ],
    missing_facts: [], uncertain_facts: [],
    evidence: [{ subject: `http://x/instance/${activity}-destruction`, value: '삭제' }],
  })
  const instances = [
    mk('aaaaaaaaaaaa', 'AccountCollection'),
    mk('bbbbbbbbbbbb', 'LocationRecommendation'),
    mk('cccccccccccc', 'InterestRecommendation'),
  ]
  const labels = instances.map(instanceLabel)
  assert.equal(new Set(labels).size, 3)
  assert.equal(labels[0], '계정 정보 수집 — 보유 종료조건')
  const aliases = instanceActivityAliases(instances)
  const facts = instances.map((i) => humanizeFactReference(i.matched_facts[0], aliases))
  assert.equal(new Set(facts).size, 3)
  assert.equal(facts[1], '위치 기반 모임 추천 — 보유 종료조건 · 파기 계획')
  // without aliases the label is unchanged (existing behavior preserved)
  assert.equal(humanizeFactReference(instances[0].matched_facts[0]), '보유 종료조건 · 파기 계획')
})

test('PoC2 generated IDs stay humanized', () => {
  assert.equal(termLabel('f2_10_1_measure_2'), '사고 대응조치')
  assert.equal(termLabel('breach-notice'), '정보주체 통지문')
})

test('LLM PoC2 response-measure IDs keep their number and do not catch other IDs', () => {
  const uri = 'https://w3id.org/pipa-compliance/instance/F2-10%3Abreach-incident-measure-1'
  assert.equal(termLabel(uri), '사고 대응조치 (1)')
  assert.equal(humanizeDisplayValue(uri), '사고 대응조치 (1)')
  assert.equal(termLabel('http://x/instance/F2-10%3Abreach-incident-measure-3'), '사고 대응조치 (3)')
  assert.notEqual(termLabel('http://x/instance/F2-10%3Aother-measure-1'), '사고 대응조치 (1)')
  assert.notEqual(termLabel('http://x/instance/F2-10%3Abreach-incident-measure-x'), '사고 대응조치 (x)')
})

test('PoC2 breach-incident ID is shown as 개인정보 유출등 사고', () => {
  assert.equal(termLabel('breach-incident'), '개인정보 유출등 사고')
  assert.equal(termLabel('http://x/instance/breach-incident'), '개인정보 유출등 사고')
  assert.equal(humanizeDisplayValue('breach-incident'), '개인정보 유출등 사고')
  assert.equal(humanizeFactReference('rdf:breach-incident:affectsPersonalInformation'), '개인정보 유출등 사고 · 실제 사고 영향 개인정보')
})

test('developer terms in reasons are shown in plain Korean, absent and unknown stay distinct', () => {
  const contract = humanizeNarrative(
    'Frozen Fact input contract에서 필수 Fact가 absent로 확인되었습니다. 통지문 시점 값이 UNKNOWN/모호하여 자동 확정할 수 없습니다.',
  )
  assert.equal(
    contract,
    '필수 검토 정보 중 일부가 명시적으로 없는 것으로 확인되었습니다. 통지문 시점 값이 확인 필요 또는 모호하여 자동 확정할 수 없습니다.',
  )
  assert.equal(
    humanizeNarrative('Frozen Fact input contract가 불완전하거나 UNKNOWN 상태를 포함합니다.'),
    '필수 검토 정보가 충분히 전달되지 않았거나 확인이 필요한 상태를 포함합니다.',
  )
  assert.equal(
    humanizeNarrative('필수 Fact의 value_state를 confirmed 또는 명시적 absent로 확정한 뒤 다시 평가하세요.'),
    "필수 검토 정보의 정보 확인 상태를 '확인됨' 또는 '명시적으로 없음'으로 확정한 뒤 다시 검토하세요.",
  )
  assert.equal(
    humanizeNarrative('P2-R01은 통지 대상 여부나 신고 threshold를 자동판정하지 않습니다.'),
    '해당 준수 기준은 통지 대상 여부나 신고 판단 기준을 자동판정하지 않습니다.',
  )
  assert.equal(humanizeNarrative('measure_role을 확인하세요'), '대응조치 유형을 확인하세요')
  assert.equal(humanizeFactReference('fact:F2-08:unknown'), '통지문 기재 사고시점 — 확인 필요')
  assert.equal(humanizeDisplayValue('absent'), '명시적으로 없음')
  assert.equal(humanizeDisplayValue('unknown'), '확인 필요')
  assert.notEqual(humanizeDisplayValue('absent'), humanizeDisplayValue('unknown'))
})

test('status-count summaries and source text are not rewritten', () => {
  const summary = '대표 상태=GREEN. 인스턴스 3개 평가 결과 GREEN=1, RED=1, YELLOW=1'
  assert.equal(humanizeNarrative(summary), summary)
})

test('evaluated_at is shown in KST only when an explicit offset is present', () => {
  assert.equal(formatEvaluatedAt('2026-10-25T17:37:03.640932+00:00'), '2026.10.26 02:37 (KST)')
  assert.equal(formatEvaluatedAt('2026-10-25T17:37:03Z'), '2026.10.26 02:37 (KST)')
  assert.equal(formatEvaluatedAt('2026-10-26T02:37:03+09:00'), '2026.10.26 02:37 (KST)')
  assert.equal(formatEvaluatedAt('2026-10-25T20:37:03-05:00'), '2026.10.26 10:37 (KST)')
  assert.equal(formatEvaluatedAt('2026-12-31T15:00:59+00:00'), '2027.01.01 00:00 (KST)')
  // 시간대가 없거나 해석할 수 없는 값은 가정하지 않고 원문 유지
  assert.equal(formatEvaluatedAt('2026-10-25T17:37:03.640932'), '2026-10-25T17:37:03.640932')
  assert.equal(formatEvaluatedAt('not a date'), 'not a date')
})

test('Fact IDs note shows object names without duplicated prefix or internal IDs', () => {
  assert.equal(humanizeFactIdsNote('Fact IDs: F2-08:breach-notice'), '관련 검토 항목: 정보주체 통지문')
  assert.equal(
    humanizeFactIdsNote('Fact IDs: F2-08:breach-notice, F2-09:breach-notice#2'),
    '관련 검토 항목: 정보주체 통지문',
  )
  assert.equal(
    humanizeFactIdsNote('Fact IDs: F2-01:breach-incident, F2-03:breach-notice'),
    '관련 검토 항목: 개인정보 유출등 사고, 정보주체 통지문',
  )
  // 대상 객체가 없거나 다른 노트는 그대로 둔다
  assert.equal(humanizeFactIdsNote('Fact IDs: F2-08'), 'Fact IDs: F2-08')
  assert.equal(humanizeFactIdsNote('required Fact envelope missing'), 'required Fact envelope missing')
})

test('the recheck recommendation is rephrased for P2-R03 only', () => {
  const generic = '필수 Fact의 value_state를 confirmed 또는 명시적 absent로 확정한 뒤 다시 평가하세요.'
  assert.equal(
    humanizeNarrative(generic, 'P2-R03'),
    '사고시점에 관한 정보를 추가 확인하고, 확인 결과를 반영하여 다시 검토하세요.',
  )
  assert.equal(
    humanizeNarrative(generic, 'P2-R08'),
    "필수 검토 정보의 정보 확인 상태를 '확인됨' 또는 '명시적으로 없음'으로 확정한 뒤 다시 검토하세요.",
  )
  assert.equal(humanizeNarrative(generic), humanizeNarrative(generic, 'P1-R01'))
})

test('P2-R08 partial-role reason uses 대응조치 유형 wording', () => {
  assert.equal(
    humanizeNarrative('대응정보는 존재하지만 v1 필수 4개 역할 중 일부가 누락되었거나 허용되지 않은 역할 값이 포함되어 있습니다.'),
    '대응정보는 존재하지만 필수 대응조치 4개 유형 중 일부가 확인되지 않았거나 허용되지 않은 유형이 포함되어 있습니다.',
  )
})

test('RED-without-missing notice appears only for PoC3 RED with empty missing_facts', () => {
  const notice = '필수 검토 정보의 누락은 없지만, 확인된 내용이 해당 검토 기준을 충족하지 않아 미충족으로 판정되었습니다.'
  assert.equal(redWithoutMissingNotice('P3-R06', 'RED', []), notice)
  assert.equal(redWithoutMissingNotice('P3-R06', 'RED', ['rdf:x:y']), null)
  for (const status of ['GREEN', 'YELLOW', 'N/A'] as const) {
    assert.equal(redWithoutMissingNotice('P3-R06', status, []), null)
  }
  assert.equal(redWithoutMissingNotice('P1-R01', 'RED', []), null)
  assert.equal(redWithoutMissingNotice('P2-R03', 'RED', []), null)
})

test('PoC1 v1.1 instance targets get Korean labels instead of raw IDs', () => {
  assert.equal(termLabel('https://example.org/pipa-instance/a1/act-crossborder-001'), '국외 이전 처리행위')
  assert.equal(termLabel('https://example.org/pipa-instance/a1/act-provision-001'), '제3자 제공 처리행위')
  assert.equal(termLabel('crossborder'), '국외 이전 처리행위')
  assert.equal(termLabel('__document__'), '문서 전체')
  assert.equal(humanizeFactIdsNote('Fact IDs: F1-20:privacy-officer'), '관련 검토 항목: 개인정보 보호책임자')
  assert.equal(humanizeFactIdsNote('Fact IDs: F1-16:act-crossborder-001'), '관련 검토 항목: 국외 이전 처리행위')
})

test('activity absence sentences use Korean class names with the right particle', () => {
  assert.equal(humanizeNarrative('CrossBorderTransfer가 없다고 명시적으로 확인되었습니다.'),
    '개인정보 국외 이전이 없다고 명시적으로 확인되었습니다.')
  assert.equal(humanizeNarrative('ThirdPartyProvision가 없다고 명시적으로 확인되었습니다.'),
    '제3자 제공이 없다고 명시적으로 확인되었습니다.')
  assert.equal(humanizeNarrative('NotificationNotice가 없다고 명시적으로 확인되었습니다.'),
    '정보주체 통지문이 없다고 명시적으로 확인되었습니다.')
  assert.equal(humanizeNarrative('CrossBorderTransfer의 존재/부재를 확정할 수 없습니다.'),
    '개인정보 국외 이전의 존재 여부를 확정할 수 없습니다.')
})

test('destruction activity IDs and PoC3 legal basis types are shown in Korean', () => {
  assert.equal(termLabel('https://example.org/pipa-instance/a1/act-destruction-001'), '파기 처리행위')
  assert.equal(termLabel('act-destroy-001'), '파기 처리행위')
  assert.equal(humanizeFactReference('rdf:act-destruction-001:hasDestructionMethod'), '파기 처리행위 · 파기 방법')
  assert.equal(humanizeDisplayValue('Contract'), '계약 이행')
  assert.equal(humanizeDisplayValue('LegalObligation'), '법적 의무')
  assert.equal(humanizeDisplayValue('LegitimateInterest'), '정당한 이익 검토')
})
