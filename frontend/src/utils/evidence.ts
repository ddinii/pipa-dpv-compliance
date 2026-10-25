import type { Evidence } from '../types/api'

export function evidenceKey(item: Evidence): string {
  return JSON.stringify([
    item.evidence_type, item.subject, item.predicate, item.value, item.source_text, item.note,
  ])
}

/** Top-level evidence is the union of instance evidence; keep only items not already shown per instance. */
export function evidenceNotInInstances(
  evidence: Evidence[],
  instances: Array<{ evidence: Evidence[] }>,
): Evidence[] {
  const shown = new Set(instances.flatMap((instance) => instance.evidence.map(evidenceKey)))
  return evidence.filter((item) => !shown.has(evidenceKey(item)))
}
