import type { RuleResult } from '../types/api'
import './ComplianceResults.css'
import { EvidenceList } from './EvidenceList'
import { InstanceRuleResultList } from './InstanceRuleResultList'

interface RuleResultCardProps {
  result: RuleResult
}

export function RuleResultCard({ result }: RuleResultCardProps) {
  return (
    <article className="rule-result-card">
      <div className="rule-summary">
        <header>
          <h3>{result.rule_id}</h3>
          <span className="status-badge">{result.status}</span>
          <span>Applicability: {result.applicability}</span>
        </header>

        {result.rule_version && <p className="rule-version">Rule version: {result.rule_version}</p>}

        {result.reason && <p className="rule-reason">{result.reason}</p>}
        {result.recommendation && <p className="recommendation">{result.recommendation}</p>}

        {result.legal_basis.length > 0 && <p>Legal basis: {result.legal_basis.join(', ')}</p>}

        <p className="status-disclaimer">
          Automated indicator only — not a legal compliance certification and not confirmation of a
          legal violation.
        </p>
      </div>

      {result.instance_results.length > 0 && (
        <section className="instance-results-section">
          <h4>Instance Results</h4>
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

      <p className="evaluated-at">Evaluated at: {result.evaluated_at}</p>
    </article>
  )
}
