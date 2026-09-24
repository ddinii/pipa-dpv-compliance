import { postJson } from './client'
import type { ComplianceResponse } from '../types/api'

/**
 * PoC1's and PoC2's outer request contracts are confirmed (see
 * app/services/compliance.py run_policy_check()/run_breach_check() and
 * examples/poc2_synthetic_breach_fixture.json, exercised by
 * tests/test_poc2_breach_check_api.py).
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

/**
 * PoC3's outer request contract is confirmed by app/builders/poc3_fact_builder.py
 * (required field checks), app/services/compliance.py run_design_check(),
 * docs/context/poc3/REQUIREMENTS.md, and examples/SC-D01_form.json.
 *
 * third_party_provision_state / cross_border_transfer_state: the only value
 * confirmed anywhere in the backend (app/rules/engine.py _conditional_no_targets,
 * examples/SC-D01_form.json) is "confirmed_false". Omitting the field is the
 * confirmed way to leave the state unconfirmed/unknown; no other literal value
 * is confirmed, so none is offered here.
 */
export type ScenarioState = 'confirmed_false'

export interface DesignCheckLegalBasis {
  type: string
  status: string
}

export interface DesignCheckConsentRequest {
  planned: boolean
}

export interface DesignCheckPersonalInformationItem {
  item_name: string
  is_required: boolean
  design_rationale: string
}

export interface DesignCheckRetention {
  end_condition: string
  destruction_method: string
}

export interface DesignCheckCollectionActivity {
  activity_id: string
  purpose: string
  legal_basis: DesignCheckLegalBasis
  consent_request: DesignCheckConsentRequest
  personal_information_items: DesignCheckPersonalInformationItem[]
  retention: DesignCheckRetention
  denies_service_on_optional_refusal: boolean
}

export interface DesignCheckEntrustedProcessing {
  activity_id: string
  processor: string
  task: string
}

export interface DesignCheckRequest {
  analysis_id: string
  controller: {
    controller_id: string
    name?: string | null
  }
  collection_activities: DesignCheckCollectionActivity[]
  entrusted_processings: DesignCheckEntrustedProcessing[]
  third_party_provision_state?: ScenarioState
  cross_border_transfer_state?: ScenarioState
}

export function policyCheck(payload: PolicyCheckRequest): Promise<ComplianceResponse> {
  return postJson<ComplianceResponse>('/api/v1/compliance/policy-check', payload)
}

export function breachCheck(payload: BreachCheckRequest): Promise<ComplianceResponse> {
  return postJson<ComplianceResponse>('/api/v1/compliance/breach-check', payload)
}

export function designCheck(payload: DesignCheckRequest): Promise<ComplianceResponse> {
  return postJson<ComplianceResponse>('/api/v1/compliance/design-check', payload)
}
