import type { Evidence } from '../types/api'
import { PipeSeparatedValue } from './PipeSeparatedValue'

interface EvidenceListProps {
  evidence: Evidence[]
}

// Datetime Facts are stored as KST ISO 8601 (xsd:dateTime); show them as yyyy-mm-dd hh:mm (KST).
// Other offsets are left as-is rather than silently converted.
const KST_DATETIME = /^(\d{4}-\d{2}-\d{2})T(\d{2}:\d{2})(?::\d{2}(?:\.\d+)?)?\+09:00$/

function formatEvidenceValue(value: Evidence['value']): string | null {
  if (value === null) {
    return null
  }
  if (typeof value === 'boolean') {
    return value ? 'true' : 'false'
  }
  const datetime = KST_DATETIME.exec(value)
  if (datetime) {
    return `${datetime[1]} ${datetime[2]} (KST)`
  }
  return value
}

export function EvidenceList({ evidence }: EvidenceListProps) {
  if (evidence.length === 0) {
    return <p className="evidence-empty">기록된 근거 없음.</p>
  }

  return (
    <details className="evidence-details">
      <summary>상세 근거 보기 ({evidence.length})</summary>
      <ul className="evidence-list">
        {evidence.map((item, index) => {
          const formattedValue = formatEvidenceValue(item.value)
          const isCompact = item.evidence_type === 'rdf_assertion'
          return (
            <li
              key={`${item.evidence_type}-${index}`}
              className={isCompact ? 'evidence-item evidence-item-compact' : 'evidence-item'}
            >
              <div className="evidence-row">
                <span className="evidence-type">{item.evidence_type}</span>
                {item.predicate && <span className="evidence-predicate">{item.predicate}</span>}
                {formattedValue !== null && (
                  <span className="evidence-value">
                    <PipeSeparatedValue value={formattedValue} />
                  </span>
                )}
              </div>
              {item.subject && (
                <div className="evidence-subject" title={item.subject}>
                  <PipeSeparatedValue value={item.subject} />
                </div>
              )}
              {item.source_text && <p className="evidence-source-text">{item.source_text}</p>}
              {item.note && <p className="evidence-note">{item.note}</p>}
            </li>
          )
        })}
      </ul>
    </details>
  )
}
