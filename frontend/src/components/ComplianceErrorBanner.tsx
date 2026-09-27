import { ApiError } from '../api/errors'
import './ComplianceResults.css'

interface ComplianceErrorBannerProps {
  error: unknown
}

function describeError(error: unknown): string {
  if (error instanceof ApiError) {
    return error.message
  }
  if (error instanceof Error) {
    return error.message
  }
  return '예상하지 못한 오류가 발생함.'
}

export function ComplianceErrorBanner({ error }: ComplianceErrorBannerProps) {
  return (
    <div className="compliance-error-banner" role="alert">
      <strong>요청 실패:</strong> {describeError(error)}
    </div>
  )
}
