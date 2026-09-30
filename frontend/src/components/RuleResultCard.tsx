import type { RuleResult } from '../types/api'
import './ComplianceResults.css'
import { EvidenceList } from './EvidenceList'
import { InstanceRuleResultList } from './InstanceRuleResultList'
import { PipeSeparatedValue } from './PipeSeparatedValue'

interface RuleResultCardProps {
  result: RuleResult
}

export function RuleResultCard({ result }: RuleResultCardProps) {
  const statusClass = `status-${result.status.replace('/', '-').toLowerCase()}`

  return (
    <article className={`rule-result-card ${statusClass}`}>
      <div className="rule-summary">
        <header>
          <h3>{result.rule_id}</h3>
          <span className={`status-badge ${statusClass}`}>{result.status}</span>
          <span>적용 여부: {result.applicability}</span>
        </header>

        {result.rule_version && <p className="rule-version">규칙 버전: {result.rule_version}</p>}

        {result.reason && <p className="rule-reason">{result.reason}</p>}
        {result.recommendation && <p className="recommendation">{result.recommendation}</p>}

        {result.legal_basis.length > 0 && <p>법적 근거: {result.legal_basis.join(', ')}</p>}

        <p className="status-disclaimer">
          자동화된 검토 지표이며 법적 적법성 인증 또는 법 위반 확정을 의미하지 않음.
        </p>
      </div>

      <details className="fact-details">
        <summary>판정에 사용된 Fact 보기</summary>
        <div className="fact-groups">
          <FactGroup title="확인된 Fact" items={result.matched_facts} tone="confirmed" />
          <FactGroup title="누락된 Fact" items={result.missing_facts} tone="missing" />
          <FactGroup title="불확실한 Fact" items={result.uncertain_facts} tone="uncertain" />
        </div>
      </details>

      {result.instance_results.length > 0 && (
        <section className="instance-results-section">
          <h4>처리행위별 검토 결과</h4>
          <InstanceRuleResultList instances={result.instance_results} />
        </section>
      )}

      <EvidenceList evidence={result.evidence} />

      {result.implementation_notes.length > 0 && (
        <details className="implementation-notes-details">
          <summary>기술 상세 보기</summary>
          <ul className="implementation-notes">
            {result.implementation_notes.map((note, index) => (
              <li key={index}>{note}</li>
            ))}
          </ul>
        </details>
      )}

      <p className="evaluated-at">검토 시각: {result.evaluated_at}</p>
    </article>
  )
}

interface FactGroupProps {
  title: string
  items: string[]
  tone: 'confirmed' | 'missing' | 'uncertain'
}

function FactGroup({ title, items, tone }: FactGroupProps) {
  return (
    <section className={`fact-group fact-${tone}`}>
      <h4>{title}</h4>
      {items.length > 0 ? (
        <ul>
          {items.map((item, index) => (
            <li key={`${tone}-${index}`}>
              <PipeSeparatedValue value={item} />
            </li>
          ))}
        </ul>
      ) : (
        <p>없음</p>
      )}
    </section>
  )
}
