import { useState } from 'react'
import { policyCheck } from '../api/compliance'
import type { ComplianceResponse } from '../types/api'
import { ComplianceErrorBanner } from '../components/ComplianceErrorBanner'
import { ComplianceResultsPanel } from '../components/ComplianceResultsPanel'
import { policyDemo } from '../data/demoExamples'
import './PolicyCheckPage.css'

export function PolicyCheckPage() {
  const [analysisId, setAnalysisId] = useState('')
  const [controllerId, setControllerId] = useState('')
  const [controllerName, setControllerName] = useState('')
  const [policyText, setPolicyText] = useState('')

  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<unknown>(null)
  const [result, setResult] = useState<ComplianceResponse | null>(null)

  function loadDemo() {
    setAnalysisId(policyDemo.analysis_id)
    setControllerId(policyDemo.controller.controller_id)
    setControllerName(policyDemo.controller.name ?? '')
    setPolicyText(policyDemo.policy_text)
    setError(null)
    setResult(null)
  }

  function resetForm() {
    setAnalysisId('')
    setControllerId('')
    setControllerName('')
    setPolicyText('')
    setError(null)
    setResult(null)
  }

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setLoading(true)
    setError(null)
    setResult(null)

    try {
      const response = await policyCheck({
        analysis_id: analysisId,
        controller: {
          controller_id: controllerId,
          name: controllerName.trim() ? controllerName : null,
        },
        policy_text: policyText,
      })
      setResult(response)
    } catch (err) {
      setError(err)
    } finally {
      setLoading(false)
    }
  }

  return (
    <section className="policy-check-page">
      <h2 className="page-title">개인정보 처리방침 준수점검</h2>
      <p className="page-subtitle">PoC1 — 처리방침 원문에서 Fact를 추출하여 6개 P0 규칙을 검토함.</p>

      <div className="form-actions form-actions-top">
        <button type="button" className="secondary-button" onClick={loadDemo} disabled={loading}>
          모아마켓 예제 불러오기
        </button>
        <button type="button" className="ghost-button" onClick={resetForm} disabled={loading}>
          입력 초기화
        </button>
      </div>

      <form onSubmit={handleSubmit} className="policy-check-form">
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

        <label htmlFor="policy-text">개인정보 처리방침 원문</label>
        <textarea
          id="policy-text"
          value={policyText}
          onChange={(event) => setPolicyText(event.target.value)}
          rows={16}
          required
        />

        <button type="submit" disabled={loading}>
          {loading ? '분석 중...' : '처리방침 분석하기'}
        </button>
      </form>

      {error !== null && <ComplianceErrorBanner error={error} />}

      {result && <ComplianceResultsPanel result={result} />}
    </section>
  )
}
