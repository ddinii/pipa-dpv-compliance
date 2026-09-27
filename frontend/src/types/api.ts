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
  // 기능명세서 8장 필수 필드 (입력 추적 ID)
  source_document_id: string
  instance_results: InstanceRuleResult[]
  implementation_notes: string[]
}

export type PocId = 'PoC1' | 'PoC2' | 'PoC3'

// 기능명세서 9.1 공통 API 응답
export interface ComplianceResponse {
  analysis_id: string
  poc: PocId
  ontology_version: string
  rule_version: string
  fact_schema_version: string
  results: RuleResult[]
}
