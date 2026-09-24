import { postJson } from './client'
import type { ComplianceResponse } from '../types/api'

/**
 * Outer request bodies are currently only confirmed as opaque JSON objects
 * (app/api/compliance.py accepts each as `Body(...)` typed `dict[str, Any]`).
 * Field-level PoC1/PoC2/PoC3 request schemas are not yet frozen, so these are
 * intentionally conservative and kept separate per PoC rather than shared.
 */
export type PolicyCheckRequest = Record<string, unknown>
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
