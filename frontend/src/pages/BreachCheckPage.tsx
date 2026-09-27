import { useState } from 'react'
import { breachCheck } from '../api/compliance'
import type { ComplianceResponse } from '../types/api'
import { ComplianceErrorBanner } from '../components/ComplianceErrorBanner'
import { ComplianceResultsPanel } from '../components/ComplianceResultsPanel'
import { breachDemo } from '../data/demoExamples'
import './BreachCheckPage.css'

export function BreachCheckPage() {
  const [analysisId, setAnalysisId] = useState('')
  const [controllerId, setControllerId] = useState('')
  const [controllerName, setControllerName] = useState('')

  const [incidentId, setIncidentId] = useState('')
  const [incidentDescription, setIncidentDescription] = useState('')

  const [includeNotification, setIncludeNotification] = useState(false)
  const [noticeId, setNoticeId] = useState('')
  const [noticeText, setNoticeText] = useState('')

  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<unknown>(null)
  const [result, setResult] = useState<ComplianceResponse | null>(null)

  function loadDemo() {
    setAnalysisId(breachDemo.analysis_id)
    setControllerId(breachDemo.controller.controller_id)
    setControllerName(breachDemo.controller.name ?? '')
    setIncidentId(breachDemo.incident.incident_id)
    setIncidentDescription(breachDemo.incident.description)
    setIncludeNotification(Boolean(breachDemo.notification))
    setNoticeId(breachDemo.notification?.notice_id ?? '')
    setNoticeText(breachDemo.notification?.notice_text ?? '')
    setError(null)
    setResult(null)
  }

  function resetForm() {
    setAnalysisId('')
    setControllerId('')
    setControllerName('')
    setIncidentId('')
    setIncidentDescription('')
    setIncludeNotification(false)
    setNoticeId('')
    setNoticeText('')
    setError(null)
    setResult(null)
  }

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setLoading(true)
    setError(null)
    setResult(null)

    try {
      const response = await breachCheck({
        analysis_id: analysisId,
        controller: {
          controller_id: controllerId,
          name: controllerName.trim() ? controllerName : null,
        },
        incident: {
          incident_id: incidentId,
          description: incidentDescription,
        },
        notification: includeNotification
          ? {
              notice_id: noticeId,
              notice_text: noticeText,
            }
          : undefined,
      })
      setResult(response)
    } catch (err) {
      setError(err)
    } finally {
      setLoading(false)
    }
  }

  return (
    <section className="breach-check-page">
      <h2 className="page-title">개인정보 침해사고 통지 요건 검토 지원</h2>
      <p className="page-subtitle">PoC2 — 사고 사실과 통지문을 분리하여 4개 P0 규칙을 검토함.</p>

      <div className="form-actions form-actions-top">
        <button type="button" className="secondary-button" onClick={loadDemo} disabled={loading}>
          사고·통지문 예제 불러오기
        </button>
        <button type="button" className="ghost-button" onClick={resetForm} disabled={loading}>
          입력 초기화
        </button>
      </div>

      <form onSubmit={handleSubmit} className="breach-check-form">
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

        <label htmlFor="controller-name">개인정보처리자명 (선택)</label>
        <input
          id="controller-name"
          type="text"
          value={controllerName}
          onChange={(event) => setControllerName(event.target.value)}
        />

        <fieldset className="incident-fieldset">
          <legend>침해사고 사실</legend>
          <p className="fieldset-hint">
            실제로 발생한 침해사고에 대한 사실 정보입니다. 아래 통지문 정보와는 별개입니다.
          </p>

          <label htmlFor="incident-id">사고 ID</label>
          <input
            id="incident-id"
            type="text"
            value={incidentId}
            onChange={(event) => setIncidentId(event.target.value)}
            required
          />

          <label htmlFor="incident-description">사고 사실 원문</label>
          <textarea
            id="incident-description"
            value={incidentDescription}
            onChange={(event) => setIncidentDescription(event.target.value)}
            rows={10}
            required
          />
        </fieldset>

        <fieldset className="notification-fieldset">
          <legend>정보주체 통지문 — 선택사항</legend>
          <p className="fieldset-hint">
            정보주체에게 실제로 발송된 통지문의 내용입니다. 위 침해사고 정보와 동일하지 않을 수
            있으며(예: 통지문에 기재된 시점·항목은 실제 사고 발생 시점·항목과 다를 수 있음), 통지문이
            아직 없다면 이 섹션 전체를 생략할 수 있습니다.
          </p>

          <label className="checkbox-label" htmlFor="include-notification">
            <input
              id="include-notification"
              type="checkbox"
              checked={includeNotification}
              onChange={(event) => setIncludeNotification(event.target.checked)}
            />
            통지문 정보 포함
          </label>

          {includeNotification && (
            <>
              <label htmlFor="notice-id">통지문 ID</label>
              <input
                id="notice-id"
                type="text"
                value={noticeId}
                onChange={(event) => setNoticeId(event.target.value)}
                required
              />

              <label htmlFor="notice-text">통지문 원문</label>
              <textarea
                id="notice-text"
                value={noticeText}
                onChange={(event) => setNoticeText(event.target.value)}
                rows={10}
                required
              />
            </>
          )}
        </fieldset>

        <button type="submit" disabled={loading}>
          {loading ? '분석 중...' : '통지 요건 검토하기'}
        </button>
      </form>

      {error !== null && <ComplianceErrorBanner error={error} />}

      {result && <ComplianceResultsPanel result={result} />}
    </section>
  )
}
