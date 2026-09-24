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
  return 'An unexpected error occurred.'
}

export function ComplianceErrorBanner({ error }: ComplianceErrorBannerProps) {
  return (
    <div className="compliance-error-banner" role="alert">
      <strong>Request failed:</strong> {describeError(error)}
    </div>
  )
}
