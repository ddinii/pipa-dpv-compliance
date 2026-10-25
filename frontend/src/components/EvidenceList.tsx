import type { Evidence, RuleStatus } from '../types/api'
import {
  evidenceTypeLabel,
  humanizeFactIdsNote,
  humanizeDisplayValue,
  humanizeNarrative,
  termLabel,
} from '../utils/complianceLabels'

interface EvidenceListProps {
  evidence: Evidence[]
  status: RuleStatus
}

const KST_DATETIME = /^(\d{4}-\d{2}-\d{2})T(\d{2}:\d{2})(?::\d{2}(?:\.\d+)?)?\+09:00$/

function formatEvidenceValue(value: Evidence['value']): string | null {
  if (value === null) return null
  if (typeof value === 'boolean') return value ? '예' : '아니오'
  const datetime = KST_DATETIME.exec(value)
  if (datetime) return `${datetime[1]} ${datetime[2]} (한국시간)`
  return humanizeDisplayValue(value)
}

function humanizeNote(rawNote: string): string {
  const note = humanizeFactIdsNote(rawNote)
  return humanizeNarrative(note
    .replace('명시적 부재(confirmed_false)', '없음이 명시적으로 확인된 상태')
    .replace('required Fact envelope missing', '필수 입력자료가 전달되지 않았음')
    .replace('Fact IDs:', '관련 검토 항목:')
    .replace('confirmed_false', '명시적 부재 확인')
    .replace('미확인 역할:', '확인되지 않은 대응조치:')
    .replace('v1 비허용 역할:', '지원하지 않는 대응조치 유형:'))
}

function evidenceTone(evidenceType: string, status: RuleStatus): string {
  if (evidenceType === 'rdf_assertion') return 'evidence-confirmed'
  if (evidenceType === 'absence' || evidenceType === 'fact_contract') {
    return status === 'RED' ? 'evidence-critical' : 'evidence-warning'
  }
  return 'evidence-neutral'
}

export function EvidenceList({ evidence, status }: EvidenceListProps) {
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
                <span className={`evidence-type ${evidenceTone(item.evidence_type, status)}`}>
                  {evidenceTypeLabel(item.evidence_type)}
                </span>
                {predicateLabel && item.evidence_type !== 'source_text' && (
                  <span className="evidence-predicate">{predicateLabel}</span>
                )}
                {formattedValue !== null && <span className="evidence-value">{formattedValue}</span>}
              </div>

              {item.source_text && (
                <blockquote className="evidence-source-text">“{item.source_text}”</blockquote>
              )}
              {item.note && <p className="evidence-note">{humanizeNote(item.note)}</p>}

            </li>
          )
        })}
      </ul>
    </details>
  )
}
