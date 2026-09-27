import { ApiError, type FastApiValidationErrorItem } from './errors'

const DEFAULT_BASE_URL = 'http://127.0.0.1:8000'

export function getApiBaseUrl(): string {
  const configured: unknown = import.meta.env.VITE_API_BASE_URL
  if (typeof configured === 'string' && configured.trim().length > 0) {
    return configured.replace(/\/+$/, '')
  }
  return DEFAULT_BASE_URL
}

function isFastApiValidationArray(detail: unknown): detail is FastApiValidationErrorItem[] {
  return (
    Array.isArray(detail) &&
    detail.length > 0 &&
    detail.every(
      (item) => typeof item === 'object' && item !== null && 'msg' in item && 'loc' in item,
    )
  )
}

function summarizeValidationErrors(issues: FastApiValidationErrorItem[]): string {
  return issues
    .map((issue) => {
      const path = issue.loc.filter((segment) => segment !== 'body').join('.')
      return path ? `${path}: ${issue.msg}` : issue.msg
    })
    .join('; ')
}

async function readJsonBody(response: Response): Promise<unknown> {
  try {
    return await response.json()
  } catch {
    return undefined
  }
}

/**
 * POSTs a JSON payload and returns the parsed JSON response.
 * All failure modes (network, 422, other non-2xx) are normalized into ApiError
 * so callers never see raw fetch/HTTP internals or stack traces.
 */
export async function postJson<TResponse>(path: string, payload: unknown): Promise<TResponse> {
  const url = `${getApiBaseUrl()}${path}`

  let response: Response
  try {
    response = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
  } catch {
    throw new ApiError(
      'Unable to reach the compliance API. Check your connection and API base URL.',
      'network_error',
      null,
    )
  }

  if (response.status === 422) {
    const body = await readJsonBody(response)
    const detail = (body as { detail?: unknown } | undefined)?.detail

    if (typeof detail === 'string') {
      throw new ApiError(detail, 'input_error', 422)
    }

    if (isFastApiValidationArray(detail)) {
      throw new ApiError(summarizeValidationErrors(detail), 'validation_error', 422, detail)
    }

    throw new ApiError('The API rejected the request.', 'validation_error', 422)
  }

  if (!response.ok) {
    throw new ApiError(`Request failed with status ${response.status}.`, 'http_error', response.status)
  }

  return (await response.json()) as TResponse
}
