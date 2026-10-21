import { describe, expect, it, vi } from 'vitest'

import { meta, readExample, registry } from '@/__tests__/fixtures'
import { ApiError, buildQuery, createApiClient, type FetchLike } from '@/api/client'
import type { EntityDetail, Problem } from '@/api/types'

function jsonResponse(body: unknown, status = 200, contentType = 'application/json'): Response {
  return new Response(JSON.stringify(body), { status, headers: { 'content-type': contentType } })
}

function mockFetch(response: Response | (() => Promise<Response>)) {
  return vi.fn<FetchLike>(() =>
    typeof response === 'function' ? response() : Promise.resolve(response),
  )
}

describe('buildQuery', () => {
  it('repeats array parameters and leaves out null and undefined', () => {
    expect(buildQuery({ q: 'fen', labels: ['Company', 'Person'], limit: 20, cursor: null })).toBe(
      '?q=fen&labels=Company&labels=Person&limit=20',
    )
    expect(buildQuery({ a: undefined })).toBe('')
    expect(buildQuery()).toBe('')
  })

  it('encodes values', () => {
    expect(buildQuery({ q: 'A & B Ltd' })).toBe('?q=A+%26+B+Ltd')
  })
})

describe('createApiClient', () => {
  it('reads GET /api/v1/meta', async () => {
    const body = meta(registry({ nr_synthetic: 10 }))
    const fetch = mockFetch(jsonResponse(body))
    const client = createApiClient({ fetch })

    await expect(client.getMeta()).resolves.toEqual(body)
    expect(fetch).toHaveBeenCalledOnce()
    expect(fetch.mock.calls[0]?.[0]).toBe('/api/v1/meta')
  })

  it('sends search parameters as C3 expects them', async () => {
    const fetch = mockFetch(jsonResponse({ query: 'fen', items: [], total_estimate: 0 }))
    await createApiClient({ fetch }).search({ q: 'fen', labels: ['Company', 'Account'] })
    expect(fetch.mock.calls[0]?.[0]).toBe('/api/v1/search?q=fen&labels=Company&labels=Account')
  })

  it('encodes ids in paths and passes network and alert parameters', async () => {
    const detail = readExample<EntityDetail>('c3/entity-detail.json')
    const fetch = mockFetch(() => Promise.resolve(jsonResponse(detail)))
    const client = createApiClient({ fetch, baseUrl: '/base' })

    await client.getEntity('syn-co-0003')
    await client.getNetwork('a b/c', { depth: 2, rel_types: ['PAID', 'OWNS'] })
    await client.listAlerts({ priority: 'high', cursor: 'abc=' })
    await client.getAlert('alr-f82a84574538090f0624')
    await client.listTypologies()
    await client.getTypology('circular_flow')

    expect(fetch.mock.calls.map((call) => call[0])).toEqual([
      '/base/entities/syn-co-0003',
      '/base/entities/a%20b%2Fc/network?depth=2&rel_types=PAID&rel_types=OWNS',
      '/base/alerts?priority=high&cursor=abc%3D',
      '/base/alerts/alr-f82a84574538090f0624',
      '/base/typologies',
      '/base/typologies/circular_flow',
    ])
  })

  it('throws an ApiError carrying the problem details', async () => {
    const problem: Problem = {
      type: 'about:blank',
      title: 'Not Found',
      status: 404,
      detail: 'No entity has the id syn-co-9999.',
      instance: '/api/v1/entities/syn-co-9999',
    }
    const fetch = mockFetch(jsonResponse(problem, 404, 'application/problem+json'))
    const error = await createApiClient({ fetch })
      .getEntity('syn-co-9999')
      .catch((caught: unknown) => caught)

    expect(error).toBeInstanceOf(ApiError)
    expect(error).toMatchObject({ status: 404, problem, message: problem.detail })
  })

  it('reports a 422 problem with the failed checks as its detail', async () => {
    const problem: Problem = {
      type: 'about:blank',
      title: 'Unprocessable Content',
      status: 422,
      detail: 'query.q: String should have at least 2 characters',
      instance: '/api/v1/search',
    }
    const fetch = mockFetch(jsonResponse(problem, 422, 'application/problem+json'))
    const error = await createApiClient({ fetch })
      .search({ q: 'f' })
      .catch((caught: unknown) => caught)

    expect(error).toBeInstanceOf(ApiError)
    expect(error).toMatchObject({ status: 422, problem, message: problem.detail })
  })

  it('reports a 501 problem as the contract example has it', async () => {
    const problem = readExample<Problem>('c3/problem-501.json')
    expect(problem.status).toBe(501)
    const fetch = mockFetch(jsonResponse(problem, 501, 'application/problem+json'))
    const error = await createApiClient({ fetch })
      .getMeta()
      .catch((caught: unknown) => caught)

    expect(error).toBeInstanceOf(ApiError)
    expect(error).toMatchObject({ status: 501, problem, message: problem.detail })
  })

  it('keeps the status line when the error body is not a problem', async () => {
    const fetch = mockFetch(
      new Response('upstream down', { status: 502, statusText: 'Bad Gateway' }),
    )
    const error = await createApiClient({ fetch })
      .getMeta()
      .catch((caught: unknown) => caught)

    expect(error).toMatchObject({
      status: 502,
      problem: null,
      message: 'The API answered 502 Bad Gateway.',
    })
  })

  it('reports an unreachable API as status 0', async () => {
    const fetch = mockFetch(() => Promise.reject(new TypeError('Failed to fetch')))
    const error = await createApiClient({ fetch })
      .getMeta()
      .catch((caught: unknown) => caught)

    expect(error).toBeInstanceOf(ApiError)
    expect(error).toMatchObject({ status: 0, problem: null })
  })

  it('asks for JSON and problem details', async () => {
    const fetch = mockFetch(jsonResponse([]))
    await createApiClient({ fetch }).listTypologies()
    expect(fetch.mock.calls[0]?.[1]).toEqual({
      headers: { accept: 'application/json, application/problem+json' },
    })
  })
})
