import type { InstanceRuleResult } from '../types/api'
import {
  applicabilityLabel,
  humanizeNarrative,
  statusLabel,
  termLabel,
} from '../utils/complianceLabels'
import { EvidenceList } from './EvidenceList'

interface InstanceRuleResultListProps {
  instances: InstanceRuleResult[]
}

export function InstanceRuleResultList({ instances }: InstanceRuleResultListProps) {
  if (instances.length === 0) return null

  return (
    <ul className="instance-results">
      {instances.map((instance) => (
        <li key={instance.instance_id}>
          <div className="instance-header">
            <span
              className={`status-badge status-${instance.status.replace('/', '-').toLowerCase()}`}
              title={instance.status}
            >
              {statusLabel(instance.status)}
            </span>
            <span>규칙 적용: {applicabilityLabel(instance.applicability)}</span>
            <span>검토 대상: {termLabel(instance.instance_id)}</span>
          </div>
          {instance.reason && <p>{humanizeNarrative(instance.reason)}</p>}
          {instance.recommendation && (
            <p className="recommendation">{humanizeNarrative(instance.recommendation)}</p>
          )}
          <EvidenceList evidence={instance.evidence} />
        </li>
      ))}
    </ul>
  )
}
