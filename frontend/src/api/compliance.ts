import { postJson } from './client'
import type { ComplianceResponse } from '../types/api'

/**
 * PoC1's outer request contract is confirmed (see app/services/compliance.py
 * run_policy_check()). PoC2/PoC3 outer request bodies are still only
 * confirmed as opaque JSON objects (app/api/compliance.py accepts each as
 * `Body(...)` typed `dict[str, Any]`), so those remain conservative.
 */
export interface PolicyCheckRequest {
  analysis_id: string
  controller: {
    controller_id: string
    name?: string | null
  }
  policy_text: string
}
export type BreachCheckRequest = Record<string, unknown>
export type DesignCheckRequest = Record<string, unknown>

export function policyCheck(payload: PolicyCheckRequest): Promise<ComplianceResponse> {
  return postJson<ComplianceResponse>('/api/v1/compliance/policy-check', payload)
}

export function breachCheck(payload: BreachCheckRequest): Promise<ComplianceResponse> {
  return postJson<ComplianceResponse>('/api/v1/compliance/breach-check', payload)
}

export function designCheck(payload: DesignCheckRequest): Promise<ComplianceResponse> {
  return postJson<ComplianceResponse>('/api/v1/compliance/design-check', payload)
}
