import type { InstanceRuleResult } from '../types/api'
import { EvidenceList } from './EvidenceList'

interface InstanceRuleResultListProps {
  instances: InstanceRuleResult[]
}

export function InstanceRuleResultList({ instances }: InstanceRuleResultListProps) {
  if (instances.length === 0) {
    return null
  }

  return (
    <ul className="instance-results">
      {instances.map((instance) => (
        <li key={instance.instance_id}>
          <div className="instance-header">
            <span className="status-badge">{instance.status}</span>
            <span>Applicability: {instance.applicability}</span>
            <span>{instance.instance_id}</span>
          </div>
          {instance.reason && <p>{instance.reason}</p>}
          {instance.recommendation && <p className="recommendation">{instance.recommendation}</p>}
          <EvidenceList evidence={instance.evidence} />
        </li>
      ))}
    </ul>
  )
}
