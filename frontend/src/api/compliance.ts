import { postJson } from './client'
import type { ComplianceResponse } from '../types/api'

/**
 * PoC1's and PoC2's outer request contracts are confirmed (see
 * app/services/compliance.py run_policy_check()/run_breach_check() and
 * examples/poc2_synthetic_breach_fixture.json, exercised by
 * tests/test_poc2_breach_check_api.py). PoC3's outer request body is still
 * only confirmed as an opaque JSON object (app/api/compliance.py accepts it
 * as `Body(...)` typed `dict[str, Any]`), so that one remains conservative.
 */
export interface PolicyCheckRequest {
  analysis_id: string
  controller: {
    controller_id: string
    name?: string | null
  }
  policy_text: string
}

/**
 * incident and notification are intentionally separate, differently-shaped
 * objects: they become distinct Facts (e.g. incident.affectsPersonalInformation
 * vs. notice.mentionsPersonalInformation, incidentDate vs. the notice-stated
 * incident time) and must never be merged or derived from one another.
 * notification is optional — the backend supports a request with no
 * notification (omitted or null).
 */
export interface BreachCheckRequest {
  analysis_id: string
  controller: {
    controller_id: string
    name?: string | null
  }
  incident: {
    incident_id: string
    description: string
  }
  notification?: {
    notice_id: string
    notice_text: string
  } | null
}

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
