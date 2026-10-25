import type { RuleResult } from '../types/api'
import {
  applicabilityLabel,
  formatEvaluatedAt,
  humanizeFactReference,
  humanizeNarrative,
  instanceActivityAliases,
  redWithoutMissingNotice,
  ruleLabel,
  statusLabel,
} from '../utils/complianceLabels'
import { evidenceNotInInstances } from '../utils/evidence'
import './ComplianceResults.css'
import { EvidenceList } from './EvidenceList'
import { InstanceRuleResultList } from './InstanceRuleResultList'

interface RuleResultCardProps {
  result: RuleResult
}

export function RuleResultCard({ result }: RuleResultCardProps) {
  const statusClass = `status-${result.status.replace('/', '-').toLowerCase()}`

  const hasInstances = result.instance_results.length > 0
  const aliases = instanceActivityAliases(result.instance_results)
  const redNotice = redWithoutMissingNotice(result.rule_id, result.status, result.missing_facts)
  const ruleEvidence = evidenceNotInInstances(result.evidence, result.instance_results)

  return (
    <article className={`rule-result-card ${statusClass}`}>
      <div className="rule-summary">
        <header>
          <h3>{ruleLabel(result.rule_id)}</h3>
          <span className={`status-badge ${statusClass}`} title={result.status}>
            {statusLabel(result.status)}
          </span>
          <span>규칙 적용: {applicabilityLabel(result.applicability)}</span>
        </header>

        {result.rule_version && <p className="rule-version">규칙 버전: {result.rule_version}</p>}
        {result.reason && <p className="rule-reason">{humanizeNarrative(result.reason, result.rule_id)}</p>}
        {result.recommendation && (
          <p className="recommendation">{humanizeNarrative(result.recommendation, result.rule_id)}</p>
        )}
        {result.legal_basis.length > 0 && <p>법적 근거: {result.legal_basis.join(', ')}</p>}

        <p className="status-disclaimer">
          자동화된 검토 지표이며 법적 적법성 인증 또는 법 위반 확정을 의미하지 않음.
        </p>
      </div>

      <details className="fact-details">
        <summary>판정에 사용된 검토 항목 보기</summary>
        <div className="fact-groups">
          <FactGroup title="확인된 사항" items={result.matched_facts} aliases={aliases} tone="confirmed" />
          <FactGroup title="누락된 필수사항" items={result.missing_facts} aliases={aliases} tone="missing" />
          <FactGroup title="추가 확인사항" items={result.uncertain_facts} aliases={aliases} tone="uncertain" />
        </div>
        {redNotice && <p className="fact-red-notice">{redNotice}</p>}
      </details>

      {result.instance_results.length > 0 && (
        <section className="instance-results-section">
          <h4>처리행위별 검토 결과</h4>
          <InstanceRuleResultList instances={result.instance_results} ruleId={result.rule_id} />
        </section>
      )}

      {(!hasInstances || ruleEvidence.length > 0) && (
        <EvidenceList evidence={hasInstances ? ruleEvidence : result.evidence} status={result.status} />
      )}

      <p className="evaluated-at">검토 시각: {formatEvaluatedAt(result.evaluated_at)}</p>
    </article>
  )
}

interface FactGroupProps {
  title: string
  items: string[]
  aliases: Record<string, string>
  tone: 'confirmed' | 'missing' | 'uncertain'
}

function FactGroup({ title, items, aliases, tone }: FactGroupProps) {
  return (
    <section className={`fact-group fact-${tone}`}>
      <h4>{title}</h4>
      {items.length > 0 ? (
        <ul>
          {items.map((item, index) => (
            <li key={`${tone}-${index}`}>{humanizeFactReference(item, aliases)}</li>
          ))}
        </ul>
      ) : <p>없음</p>}
    </section>
  )
}
