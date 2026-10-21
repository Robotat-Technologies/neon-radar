// A small client for the NeonRadar API (contract C3). It only calls the API's own origin
// (`/api/v1`, proxied by Vite in development and by nginx in the container), so the UI never
// talks to any other host (guardrail G3).
import type {
  AlertDetail,
  AlertListParams,
  AlertPage,
  EntityDetail,
  MetaResponse,
  NetworkParams,
  Problem,
  SearchParams,
  SearchResponse,
  Subgraph,
  TypologyDetail,
  TypologySummary,
} from './types'

export type FetchLike = (input: string, init?: RequestInit) => Promise<Response>

type QueryScalar = string | number | boolean
type QueryValue = QueryScalar | readonly QueryScalar[] | null | undefined

/** An API error: `status` 0 means the API could not be reached at all. */
export class ApiError extends Error {
  readonly status: number
  readonly problem: Problem | null

  constructor(status: number, message: string, problem: Problem | null = null) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.problem = problem
  }
}

/** `?a=1&b=x&b=y` from a parameter object: arrays repeat the key, null and undefined are left out. */
export function buildQuery(params?: Record<string, QueryValue>): string {
  const search = new URLSearchParams()
  for (const [key, value] of Object.entries(params ?? {})) {
    if (value === null || value === undefined) continue
    const values: readonly QueryScalar[] = Array.isArray(value) ? value : [value as QueryScalar]
    for (const item of values) search.append(key, String(item))
  }
  const text = search.toString()
  return text ? `?${text}` : ''
}

function isProblem(value: unknown): value is Problem {
  if (typeof value !== 'object' || value === null) return false
  const v = value as Record<string, unknown>
  return (
    typeof v.type === 'string' &&
    typeof v.title === 'string' &&
    typeof v.status === 'number' &&
    typeof v.detail === 'string' &&
    typeof v.instance === 'string'
  )
}

export interface ApiClient {
  getMeta(): Promise<MetaResponse>
  search(params: SearchParams): Promise<SearchResponse>
  getEntity(entityId: string): Promise<EntityDetail>
  getNetwork(entityId: string, params?: NetworkParams): Promise<Subgraph>
  listAlerts(params?: AlertListParams): Promise<AlertPage>
  getAlert(alertId: string): Promise<AlertDetail>
  listTypologies(): Promise<TypologySummary[]>
  getTypology(slug: string): Promise<TypologyDetail>
}

export interface ApiClientOptions {
  fetch?: FetchLike
  baseUrl?: string
}

export function createApiClient(options: ApiClientOptions = {}): ApiClient {
  const doFetch: FetchLike = options.fetch ?? ((input, init) => globalThis.fetch(input, init))
  const baseUrl = options.baseUrl ?? '/api/v1'

  async function get<T>(path: string, query?: Record<string, QueryValue>): Promise<T> {
    let response: Response
    try {
      response = await doFetch(`${baseUrl}${path}${buildQuery(query)}`, {
        headers: { accept: 'application/json, application/problem+json' },
      })
    } catch {
      throw new ApiError(0, 'The NeonRadar API could not be reached.')
    }
    if (!response.ok) {
      let problem: Problem | null = null
      try {
        const body: unknown = await response.json()
        if (isProblem(body)) problem = body
      } catch {
        // Not JSON: keep the status line only.
      }
      const fallback = `The API answered ${response.status} ${response.statusText}`.trim() + '.'
      throw new ApiError(response.status, problem?.detail ?? fallback, problem)
    }
    return (await response.json()) as T
  }

  const segment = encodeURIComponent

  return {
    getMeta: () => get<MetaResponse>('/meta'),
    search: (params) => get<SearchResponse>('/search', params),
    getEntity: (entityId) => get<EntityDetail>(`/entities/${segment(entityId)}`),
    getNetwork: (entityId, params) =>
      get<Subgraph>(`/entities/${segment(entityId)}/network`, params),
    listAlerts: (params) => get<AlertPage>('/alerts', params),
    getAlert: (alertId) => get<AlertDetail>(`/alerts/${segment(alertId)}`),
    listTypologies: () => get<TypologySummary[]>('/typologies'),
    getTypology: (slug) => get<TypologyDetail>(`/typologies/${segment(slug)}`),
  }
}

/** The client the app uses: same-origin `/api/v1`. */
export const api: ApiClient = createApiClient()
