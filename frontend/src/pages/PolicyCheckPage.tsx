import { useState } from 'react'
import { policyCheck } from '../api/compliance'
import type { ComplianceResponse } from '../types/api'
import { ComplianceErrorBanner } from '../components/ComplianceErrorBanner'
import { RuleResultCard } from '../components/RuleResultCard'
import './PolicyCheckPage.css'

export function PolicyCheckPage() {
  const [analysisId, setAnalysisId] = useState('')
  const [controllerId, setControllerId] = useState('')
  const [controllerName, setControllerName] = useState('')
  const [policyText, setPolicyText] = useState('')

  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<unknown>(null)
  const [result, setResult] = useState<ComplianceResponse | null>(null)

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
      <h1>개인정보 처리방침 준수점검</h1>
      <p className="page-subtitle">PoC1 — 개인정보 처리방침 텍스트 기반 형식 규칙 점검</p>

      <form onSubmit={handleSubmit} className="policy-check-form">
        <label htmlFor="analysis-id">Analysis ID</label>
        <input
          id="analysis-id"
          type="text"
          value={analysisId}
          onChange={(event) => setAnalysisId(event.target.value)}
          required
        />

        <label htmlFor="controller-id">Controller ID</label>
        <input
          id="controller-id"
          type="text"
          value={controllerId}
          onChange={(event) => setControllerId(event.target.value)}
          required
        />

        <label htmlFor="controller-name">Controller Name (optional)</label>
        <input
          id="controller-name"
          type="text"
          value={controllerName}
          onChange={(event) => setControllerName(event.target.value)}
        />

        <label htmlFor="policy-text">Policy Text</label>
        <textarea
          id="policy-text"
          value={policyText}
          onChange={(event) => setPolicyText(event.target.value)}
          rows={16}
          required
        />

        <button type="submit" disabled={loading}>
          {loading ? 'Checking...' : 'Run Policy Check'}
        </button>
      </form>

      {error !== null && <ComplianceErrorBanner error={error} />}

      {result && (
        <div className="policy-check-results">
          {result.rule_results.map((ruleResult) => (
            <RuleResultCard key={ruleResult.rule_id} result={ruleResult} />
          ))}
        </div>
      )}
    </section>
  )
}
