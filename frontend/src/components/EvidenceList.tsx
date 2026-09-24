import type { Evidence } from '../types/api'

interface EvidenceListProps {
  evidence: Evidence[]
}

export function EvidenceList({ evidence }: EvidenceListProps) {
  if (evidence.length === 0) {
    return <p className="evidence-empty">No evidence recorded.</p>
  }

  return (
    <ul className="evidence-list">
      {evidence.map((item, index) => (
        <li key={`${item.evidence_type}-${index}`}>
          <span className="evidence-type">{item.evidence_type}</span>
          {item.source_text && <p>{item.source_text}</p>}
          {item.note && <p>{item.note}</p>}
        </li>
      ))}
    </ul>
  )
}
