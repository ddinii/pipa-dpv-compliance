import type { Evidence } from '../types/api'
import {
  evidenceTypeLabel,
  humanizeDisplayValue,
  termLabel,
} from '../utils/complianceLabels'

interface EvidenceListProps {
  evidence: Evidence[]
}

const KST_DATETIME = /^(\d{4}-\d{2}-\d{2})T(\d{2}:\d{2})(?::\d{2}(?:\.\d+)?)?\+09:00$/

function formatEvidenceValue(value: Evidence['value']): string | null {
  if (value === null) return null
  if (typeof value === 'boolean') return value ? '예' : '아니오'
  const datetime = KST_DATETIME.exec(value)
  if (datetime) return `${datetime[1]} ${datetime[2]} (한국시간)`
  return humanizeDisplayValue(value)
}

function humanizeNote(note: string): string {
  return note
    .replace('required Fact envelope missing', '필수 입력자료가 전달되지 않았음')
    .replace('Fact IDs:', '입력 식별자:')
    .replace('confirmed_false', '명시적 부재 확인')
}

export function EvidenceList({ evidence }: EvidenceListProps) {
  if (evidence.length === 0) return <p className="evidence-empty">표시할 판단 근거가 없음.</p>

  return (
    <details className="evidence-details">
      <summary>판단 근거 보기 ({evidence.length})</summary>
      <ul className="evidence-list">
        {evidence.map((item, index) => {
          const formattedValue = formatEvidenceValue(item.value)
          const predicateLabel = item.predicate ? termLabel(item.predicate) : null
          return (
            <li key={`${item.evidence_type}-${index}`} className="evidence-item">
              <div className="evidence-row">
                <span className="evidence-type">{evidenceTypeLabel(item.evidence_type)}</span>
                {predicateLabel && item.evidence_type !== 'source_text' && (
                  <span className="evidence-predicate">{predicateLabel}</span>
                )}
                {formattedValue !== null && <span className="evidence-value">{formattedValue}</span>}
              </div>

              {item.source_text && (
                <blockquote className="evidence-source-text">“{item.source_text}”</blockquote>
              )}
              {item.note && <p className="evidence-note">{humanizeNote(item.note)}</p>}

              {(item.subject || item.predicate || item.evidence_type) && (
                <details className="developer-details">
                  <summary>개발자 정보</summary>
                  <dl>
                    <dt>근거 유형</dt>
                    <dd>{item.evidence_type}</dd>
                    {item.subject && (
                      <>
                        <dt>RDF 주체</dt>
                        <dd>{item.subject}</dd>
                      </>
                    )}
                    {item.predicate && (
                      <>
                        <dt>RDF 속성</dt>
                        <dd>{item.predicate}</dd>
                      </>
                    )}
                  </dl>
                </details>
              )}
            </li>
          )
        })}
      </ul>
    </details>
  )
}
