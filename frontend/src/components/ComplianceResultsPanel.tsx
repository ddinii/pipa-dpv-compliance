import type { ComplianceResponse, RuleStatus } from '../types/api'
import { RuleResultCard } from './RuleResultCard'
import './ComplianceResults.css'

interface ComplianceResultsPanelProps {
  result: ComplianceResponse
}

const STATUSES: RuleStatus[] = ['GREEN', 'AMBER', 'RED', 'N/A']

export function ComplianceResultsPanel({ result }: ComplianceResultsPanelProps) {
  const counts = Object.fromEntries(
    STATUSES.map((status) => [
      status,
      result.rule_results.filter((item) => item.status === status).length,
    ]),
  ) as Record<RuleStatus, number>

  return (
    <section className="compliance-results-panel" aria-live="polite">
      <div className="result-overview">
        <div>
          <p className="eyebrow">{result.poc} 검토 결과</p>
          <h2>총 {result.rule_results.length}개 규칙을 검토함</h2>
        </div>
        <div className="status-counts" aria-label="상태별 규칙 수">
          {STATUSES.map((status) => (
            <div className={`status-count status-${status.replace('/', '-').toLowerCase()}`} key={status}>
              <span>{status}</span>
              <strong>{counts[status]}</strong>
            </div>
          ))}
        </div>
      </div>

      <p className="legal-disclaimer">
        본 결과는 입력된 사실과 구현된 기계판독형 규칙에 따른 검토 지원 결과이며, 법적 적법성이나
        법 위반을 확정하지 않음.
      </p>

      <div className="rule-results-list">
        {result.rule_results.map((ruleResult) => (
          <RuleResultCard key={ruleResult.rule_id} result={ruleResult} />
        ))}
      </div>
    </section>
  )
}
