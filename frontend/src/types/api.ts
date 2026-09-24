/**
 * Mirrors app/api/compliance.py response models field-for-field.
 * Source of truth: app/rules/models.py (RuleResult.to_dict()) and
 * the Pydantic response models in app/api/compliance.py.
 * Do not add, remove, or rename fields without updating the backend contract first.
 */

export type RuleStatus = 'GREEN' | 'AMBER' | 'RED' | 'N/A'

export type Applicability = 'TRUE' | 'FALSE' | 'UNKNOWN'

export interface Evidence {
  evidence_type: string
  subject: string | null
  predicate: string | null
  value: string | boolean | null
  source_text: string | null
  note: string | null
}

export interface InstanceRuleResult {
  instance_id: string
  status: RuleStatus
  applicability: Applicability
  matched_facts: string[]
  missing_facts: string[]
  uncertain_facts: string[]
  evidence: Evidence[]
  reason: string
  recommendation: string
}

export interface RuleResult {
  rule_id: string
  rule_version: string
  status: RuleStatus
  applicability: Applicability
  matched_facts: string[]
  missing_facts: string[]
  uncertain_facts: string[]
  evidence: Evidence[]
  legal_basis: string[]
  reason: string
  recommendation: string
  evaluated_at: string
  instance_results: InstanceRuleResult[]
  implementation_notes: string[]
}

export type PocId = 'PoC1' | 'PoC2' | 'PoC3'

export interface ComplianceResponse {
  poc: PocId
  rule_results: RuleResult[]
}
