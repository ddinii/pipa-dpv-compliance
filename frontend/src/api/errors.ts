/**
 * Normalized API error shapes.
 *
 * The backend currently returns two possible 422 detail shapes:
 *   a. a plain string (raised via ComplianceInputError -> HTTPException(detail=str(exc)))
 *   b. a FastAPI request-validation array (Pydantic body validation failures)
 * Both are normalized into a single ApiError so callers never branch on shape.
 */

export interface FastApiValidationErrorItem {
  loc: (string | number)[]
  msg: string
  type: string
}

export type ApiErrorKind =
  | 'input_error' // ComplianceInputError (string detail)
  | 'validation_error' // FastAPI request validation (detail array)
  | 'http_error' // any other non-2xx response
  | 'network_error' // request never reached the server

export class ApiError extends Error {
  readonly kind: ApiErrorKind
  readonly status: number | null
  readonly issues?: FastApiValidationErrorItem[]

  constructor(
    message: string,
    kind: ApiErrorKind,
    status: number | null,
    issues?: FastApiValidationErrorItem[],
  ) {
    super(message)
    this.name = 'ApiError'
    this.kind = kind
    this.status = status
    this.issues = issues
  }
}
