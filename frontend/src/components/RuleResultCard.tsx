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
      <header>
        <h3>{result.rule_id}</h3>
        <span className="status-badge">{result.status}</span>
        <span>Applicability: {result.applicability}</span>
      </header>

      <p className="status-disclaimer">
        Automated indicator only — not a legal compliance certification and not confirmation of a
        legal violation.
      </p>

      <p className="rule-version">Rule version: {result.rule_version}</p>

      {result.reason && <p>{result.reason}</p>}
      {result.recommendation && <p className="recommendation">{result.recommendation}</p>}

      {result.legal_basis.length > 0 && <p>Legal basis: {result.legal_basis.join(', ')}</p>}

      <EvidenceList evidence={result.evidence} />
      <InstanceRuleResultList instances={result.instance_results} />

      {result.implementation_notes.length > 0 && (
        <ul className="implementation-notes">
          {result.implementation_notes.map((note, index) => (
            <li key={index}>{note}</li>
          ))}
        </ul>
      )}

      <p className="evaluated-at">Evaluated at: {result.evaluated_at}</p>
    </article>
  )
}
