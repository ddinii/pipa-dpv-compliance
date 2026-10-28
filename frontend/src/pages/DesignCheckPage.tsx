import { useState } from 'react'
import { designCheck } from '../api/compliance'
import type {
  DesignCheckCollectionActivity,
  DesignCheckEntrustedProcessing,
  DesignCheckPersonalInformationItem,
  DesignCheckRequest,
  ScenarioState,
} from '../api/compliance'
import type { ComplianceResponse } from '../types/api'
import { ComplianceErrorBanner } from '../components/ComplianceErrorBanner'
import { ComplianceResultsPanel } from '../components/ComplianceResultsPanel'
import { designDemo } from '../data/demoExamples'
import './DesignCheckPage.css'

let localIdCounter = 0
function nextLocalId(prefix: string): string {
  localIdCounter += 1
  return `${prefix}-${localIdCounter}`
}

interface ItemDraft {
  localId: string
  item_name: string
  is_required: boolean
  design_rationale: string
}

interface ActivityDraft {
  localId: string
  activity_id: string
  purpose: string
  legal_basis_type: string
  legal_basis_status: string
  consent_planned: boolean
  personal_information_items: ItemDraft[]
  retention_end_condition: string
  retention_destruction_method: string
  denies_service_on_optional_refusal: boolean
}

interface EntrustedDraft {
  localId: string
  activity_id: string
  processor: string
  task: string
}

function newItem(): ItemDraft {
  return {
    localId: nextLocalId('item'),
    item_name: '',
    is_required: true,
    design_rationale: '',
  }
}

function newActivity(): ActivityDraft {
  return {
    localId: nextLocalId('activity'),
    activity_id: '',
    purpose: '',
    legal_basis_type: 'Consent',
    legal_basis_status: 'planned',
    consent_planned: true,
    personal_information_items: [newItem()],
    retention_end_condition: '',
    retention_destruction_method: '',
    denies_service_on_optional_refusal: false,
  }
}

function newEntrusted(): EntrustedDraft {
  return {
    localId: nextLocalId('entrusted'),
    activity_id: '',
    processor: '',
    task: '',
  }
}

// "unspecified" is a UI-only option meaning "omit this field from the
// request"; it is not a value the backend contract confirms.
type ScenarioStateChoice = ScenarioState | 'unspecified'

export function DesignCheckPage() {
  const [analysisId, setAnalysisId] = useState('')
  const [controllerId, setControllerId] = useState('')
  const [controllerName, setControllerName] = useState('')

  const [activities, setActivities] = useState<ActivityDraft[]>([newActivity()])
  const [entrustedProcessings, setEntrustedProcessings] = useState<EntrustedDraft[]>([])

  const [thirdPartyProvisionState, setThirdPartyProvisionState] =
    useState<ScenarioStateChoice>('unspecified')
  const [crossBorderTransferState, setCrossBorderTransferState] =
    useState<ScenarioStateChoice>('unspecified')

  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<unknown>(null)
  const [result, setResult] = useState<ComplianceResponse | null>(null)

  function activityFromExample(
    activity: DesignCheckCollectionActivity,
  ): ActivityDraft {
    return {
      localId: nextLocalId('activity'),
      activity_id: activity.activity_id,
      purpose: activity.purpose,
      legal_basis_type: activity.legal_basis.type,
      legal_basis_status: activity.legal_basis.status,
      consent_planned: activity.consent_request.planned,
      personal_information_items: activity.personal_information_items.map((item) => ({
        localId: nextLocalId('item'),
        ...item,
      })),
      retention_end_condition: activity.retention.end_condition,
      retention_destruction_method: activity.retention.destruction_method,
      denies_service_on_optional_refusal: activity.denies_service_on_optional_refusal,
    }
  }

  function entrustedFromExample(entry: DesignCheckEntrustedProcessing): EntrustedDraft {
    return {
      localId: nextLocalId('entrusted'),
      ...entry,
    }
  }

  function loadDemo() {
    setAnalysisId(designDemo.analysis_id)
    setControllerId(designDemo.controller.controller_id)
    setControllerName(designDemo.controller.name ?? '')
    setActivities(designDemo.collection_activities.map(activityFromExample))
    setEntrustedProcessings(designDemo.entrusted_processings.map(entrustedFromExample))
    setThirdPartyProvisionState(designDemo.third_party_provision_state ?? 'unspecified')
    setCrossBorderTransferState(designDemo.cross_border_transfer_state ?? 'unspecified')
    setError(null)
    setResult(null)
  }

  function resetForm() {
    setAnalysisId('')
    setControllerId('')
    setControllerName('')
    setActivities([newActivity()])
    setEntrustedProcessings([])
    setThirdPartyProvisionState('unspecified')
    setCrossBorderTransferState('unspecified')
    setError(null)
    setResult(null)
  }

  function updateActivity(localId: string, patch: Partial<ActivityDraft>) {
    setActivities((current) =>
      current.map((activity) => (activity.localId === localId ? { ...activity, ...patch } : activity)),
    )
  }

  function addActivity() {
    setActivities((current) => [...current, newActivity()])
  }

  function removeActivity(localId: string) {
    setActivities((current) => current.filter((activity) => activity.localId !== localId))
  }

  function updateItem(activityLocalId: string, itemLocalId: string, patch: Partial<ItemDraft>) {
    setActivities((current) =>
      current.map((activity) =>
        activity.localId === activityLocalId
          ? {
              ...activity,
              personal_information_items: activity.personal_information_items.map((item) =>
                item.localId === itemLocalId ? { ...item, ...patch } : item,
              ),
            }
          : activity,
      ),
    )
  }

  function addItem(activityLocalId: string) {
    setActivities((current) =>
      current.map((activity) =>
        activity.localId === activityLocalId
          ? { ...activity, personal_information_items: [...activity.personal_information_items, newItem()] }
          : activity,
      ),
    )
  }

  function removeItem(activityLocalId: string, itemLocalId: string) {
    setActivities((current) =>
      current.map((activity) =>
        activity.localId === activityLocalId
          ? {
              ...activity,
              personal_information_items: activity.personal_information_items.filter(
                (item) => item.localId !== itemLocalId,
              ),
            }
          : activity,
      ),
    )
  }

  function updateEntrusted(localId: string, patch: Partial<EntrustedDraft>) {
    setEntrustedProcessings((current) =>
      current.map((entry) => (entry.localId === localId ? { ...entry, ...patch } : entry)),
    )
  }

  function addEntrusted() {
    setEntrustedProcessings((current) => [...current, newEntrusted()])
  }

  function removeEntrusted(localId: string) {
    setEntrustedProcessings((current) => current.filter((entry) => entry.localId !== localId))
  }

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setLoading(true)
    setError(null)
    setResult(null)

    const collection_activities: DesignCheckCollectionActivity[] = activities.map((activity) => {
      const personal_information_items: DesignCheckPersonalInformationItem[] =
        activity.personal_information_items.map((item) => ({
          item_name: item.item_name,
          is_required: item.is_required,
          design_rationale: item.design_rationale,
        }))

      return {
        activity_id: activity.activity_id,
        purpose: activity.purpose,
        legal_basis: {
          type: activity.legal_basis_type,
          status: activity.legal_basis_status,
        },
        consent_request: { planned: activity.consent_planned },
        personal_information_items,
        retention: {
          end_condition: activity.retention_end_condition,
          destruction_method: activity.retention_destruction_method,
        },
        denies_service_on_optional_refusal: activity.denies_service_on_optional_refusal,
      }
    })

    const entrusted_processings: DesignCheckEntrustedProcessing[] = entrustedProcessings.map((entry) => ({
      activity_id: entry.activity_id,
      processor: entry.processor,
      task: entry.task,
    }))

    const payload: DesignCheckRequest = {
      analysis_id: analysisId,
      controller: {
        controller_id: controllerId,
        name: controllerName.trim() ? controllerName : null,
      },
      collection_activities,
      entrusted_processings,
      ...(thirdPartyProvisionState !== 'unspecified'
        ? { third_party_provision_state: thirdPartyProvisionState }
        : {}),
      ...(crossBorderTransferState !== 'unspecified'
        ? { cross_border_transfer_state: crossBorderTransferState }
        : {}),
    }

    try {
      const response = await designCheck(payload)
      setResult(response)
    } catch (err) {
      setError(err)
    } finally {
      setLoading(false)
    }
  }

  return (
    <section className="design-check-page">
      <h2 className="page-title">Privacy-by-Design 개발 지원</h2>
      <p className="page-subtitle">PoC3 - 구조화된 서비스 설계정보로 8개 P0 규칙을 검토함.</p>

      <div className="form-actions form-actions-top">
        <button type="button" className="secondary-button" onClick={loadDemo} disabled={loading}>
          CampusMate 예제 불러오기
        </button>
        <button type="button" className="ghost-button" onClick={resetForm} disabled={loading}>
          입력 초기화
        </button>
      </div>

      <form onSubmit={handleSubmit} className="design-check-form">
        <label htmlFor="analysis-id">분석 ID</label>
        <input
          id="analysis-id"
          type="text"
          value={analysisId}
          onChange={(event) => setAnalysisId(event.target.value)}
          required
        />

        <label htmlFor="controller-id">개인정보처리자 ID</label>
        <input
          id="controller-id"
          type="text"
          value={controllerId}
          onChange={(event) => setControllerId(event.target.value)}
          required
        />

        <label htmlFor="controller-name">서비스·개인정보처리자명 (선택)</label>
        <input
          id="controller-name"
          type="text"
          value={controllerName}
          onChange={(event) => setControllerName(event.target.value)}
        />

        <fieldset className="activities-fieldset">
          <legend>수집·이용 활동 (Collection Activities)</legend>

          {activities.map((activity, activityIndex) => (
            <div className="activity-card" key={activity.localId}>
              <div className="card-header">
                <h3>활동 {activityIndex + 1}</h3>
                {activities.length > 1 && (
                  <button
                    type="button"
                    className="remove-button"
                    onClick={() => removeActivity(activity.localId)}
                  >
                    활동 삭제
                  </button>
                )}
              </div>

              <label htmlFor={`${activity.localId}-activity-id`}>처리행위 ID</label>
              <input
                id={`${activity.localId}-activity-id`}
                type="text"
                value={activity.activity_id}
                onChange={(event) => updateActivity(activity.localId, { activity_id: event.target.value })}
                required
              />

              <label htmlFor={`${activity.localId}-purpose`}>처리 목적</label>
              <textarea
                id={`${activity.localId}-purpose`}
                value={activity.purpose}
                onChange={(event) => updateActivity(activity.localId, { purpose: event.target.value })}
                rows={2}
                required
              />

              <div className="field-row">
                <div>
                  <label htmlFor={`${activity.localId}-legal-basis-type`}>설계상 처리 근거</label>
                  <select
                    id={`${activity.localId}-legal-basis-type`}
                    value={activity.legal_basis_type}
                    onChange={(event) =>
                      updateActivity(activity.localId, { legal_basis_type: event.target.value })
                    }
                    required
                  >
                    <option value="Consent">동의</option>
                    <option value="Contract">계약 이행</option>
                    <option value="LegalObligation">법적 의무</option>
                    <option value="LegitimateInterest">정당한 이익 검토</option>
                  </select>
                </div>
                <div>
                  <label htmlFor={`${activity.localId}-legal-basis-status`}>근거 확인 상태</label>
                  <select
                    id={`${activity.localId}-legal-basis-status`}
                    value={activity.legal_basis_status}
                    onChange={(event) =>
                      updateActivity(activity.localId, { legal_basis_status: event.target.value })
                    }
                    required
                  >
                    <option value="planned">설계 예정</option>
                    <option value="confirmed">확인됨</option>
                    <option value="unknown">추가 검토 필요</option>
                  </select>
                </div>
              </div>

              <label className="checkbox-label" htmlFor={`${activity.localId}-consent-planned`}>
                <input
                  id={`${activity.localId}-consent-planned`}
                  type="checkbox"
                  checked={activity.consent_planned}
                  onChange={(event) =>
                    updateActivity(activity.localId, { consent_planned: event.target.checked })
                  }
                />
                동의 요청 예정 (consent_request.planned)
              </label>

              <fieldset className="items-fieldset">
                <legend>수집 항목 (Personal Information Items)</legend>

                {activity.personal_information_items.map((item, itemIndex) => (
                  <div className="item-card" key={item.localId}>
                    <div className="card-header">
                      <h4>항목 {itemIndex + 1}</h4>
                      {activity.personal_information_items.length > 1 && (
                        <button
                          type="button"
                          className="remove-button"
                          onClick={() => removeItem(activity.localId, item.localId)}
                        >
                          항목 삭제
                        </button>
                      )}
                    </div>

                    <label htmlFor={`${item.localId}-item-name`}>개인정보 항목명</label>
                    <input
                      id={`${item.localId}-item-name`}
                      type="text"
                      value={item.item_name}
                      onChange={(event) =>
                        updateItem(activity.localId, item.localId, { item_name: event.target.value })
                      }
                      required
                    />

                    <label className="checkbox-label" htmlFor={`${item.localId}-is-required`}>
                      <input
                        id={`${item.localId}-is-required`}
                        type="checkbox"
                        checked={item.is_required}
                        onChange={(event) =>
                          updateItem(activity.localId, item.localId, { is_required: event.target.checked })
                        }
                      />
                      필수 항목 (is_required)
                    </label>

                    <label htmlFor={`${item.localId}-design-rationale`}>수집 필요성·설계 사유</label>
                    <textarea
                      id={`${item.localId}-design-rationale`}
                      value={item.design_rationale}
                      onChange={(event) =>
                        updateItem(activity.localId, item.localId, { design_rationale: event.target.value })
                      }
                      rows={2}
                      required
                    />
                  </div>
                ))}

                <button type="button" className="add-button" onClick={() => addItem(activity.localId)}>
                  + 수집 항목 추가
                </button>
              </fieldset>

              <div className="field-row">
                <div>
                  <label htmlFor={`${activity.localId}-retention-end`}>보유 종료조건</label>
                  <input
                    id={`${activity.localId}-retention-end`}
                    type="text"
                    value={activity.retention_end_condition}
                    onChange={(event) =>
                      updateActivity(activity.localId, { retention_end_condition: event.target.value })
                    }
                    required
                  />
                </div>
                <div>
                  <label htmlFor={`${activity.localId}-retention-destruction`}>파기 방법</label>
                  <input
                    id={`${activity.localId}-retention-destruction`}
                    type="text"
                    value={activity.retention_destruction_method}
                    onChange={(event) =>
                      updateActivity(activity.localId, { retention_destruction_method: event.target.value })
                    }
                    required
                  />
                </div>
              </div>

              <label className="checkbox-label" htmlFor={`${activity.localId}-denies-service`}>
                <input
                  id={`${activity.localId}-denies-service`}
                  type="checkbox"
                  checked={activity.denies_service_on_optional_refusal}
                  onChange={(event) =>
                    updateActivity(activity.localId, {
                      denies_service_on_optional_refusal: event.target.checked,
                    })
                  }
                />
                선택항목 거부 시 서비스 거부 (denies_service_on_optional_refusal)
              </label>
            </div>
          ))}

          <button type="button" className="add-button" onClick={addActivity}>
            + 수집·이용 활동 추가
          </button>
        </fieldset>

        <fieldset className="entrusted-fieldset">
          <legend>수탁 처리 (Entrusted Processings) — 선택사항</legend>

          {entrustedProcessings.map((entry, entryIndex) => (
            <div className="entrusted-card" key={entry.localId}>
              <div className="card-header">
                <h4>수탁 {entryIndex + 1}</h4>
                <button
                  type="button"
                  className="remove-button"
                  onClick={() => removeEntrusted(entry.localId)}
                >
                  수탁 삭제
                </button>
              </div>

              <label htmlFor={`${entry.localId}-activity-id`}>위탁 처리행위 ID</label>
              <input
                id={`${entry.localId}-activity-id`}
                type="text"
                value={entry.activity_id}
                onChange={(event) => updateEntrusted(entry.localId, { activity_id: event.target.value })}
                required
              />

              <label htmlFor={`${entry.localId}-processor`}>수탁자</label>
              <input
                id={`${entry.localId}-processor`}
                type="text"
                value={entry.processor}
                onChange={(event) => updateEntrusted(entry.localId, { processor: event.target.value })}
                required
              />

              <label htmlFor={`${entry.localId}-task`}>위탁업무</label>
              <input
                id={`${entry.localId}-task`}
                type="text"
                value={entry.task}
                onChange={(event) => updateEntrusted(entry.localId, { task: event.target.value })}
                required
              />
            </div>
          ))}

          <button type="button" className="add-button" onClick={addEntrusted}>
            + 수탁 처리 추가
          </button>
        </fieldset>

        <details className="advanced-scenario-details">
          <summary>고급 시나리오 메타데이터</summary>
          <fieldset className="scenario-state-fieldset">
          <legend>조건부 처리 상태</legend>
          <p className="fieldset-hint">
            현재 PoC3의 8개 P0 규칙에서 직접 판정하지 않는 보조 시나리오 정보임. 확정되지 않았다면 미지정으로 둠.
          </p>

          <label htmlFor="third-party-provision-state">제3자 제공 여부</label>
          <select
            id="third-party-provision-state"
            value={thirdPartyProvisionState}
            onChange={(event) =>
              setThirdPartyProvisionState(event.target.value as ScenarioStateChoice)
            }
          >
            <option value="unspecified">미지정</option>
            <option value="confirmed_false">제3자 제공하지 않음</option>
          </select>

          <label htmlFor="cross-border-transfer-state">국외이전 여부</label>
          <select
            id="cross-border-transfer-state"
            value={crossBorderTransferState}
            onChange={(event) =>
              setCrossBorderTransferState(event.target.value as ScenarioStateChoice)
            }
          >
            <option value="unspecified">미지정</option>
            <option value="confirmed_false">국외이전하지 않음</option>
          </select>
          </fieldset>
        </details>

        <button type="submit" disabled={loading}>
          {loading ? '분석 중...' : '설계 검토하기'}
        </button>
      </form>

      {error !== null && <ComplianceErrorBanner error={error} />}

      {result && <ComplianceResultsPanel result={result} />}
    </section>
  )
}
