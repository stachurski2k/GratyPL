import type { BBox, FeedPage, LngLat, Report, ReportCollection, Summary } from './types'

export class ApiError extends Error {
  status: number

  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

async function request<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, init)
  if (!res.ok) {
    let message = `Błąd serwera (${res.status})`
    try {
      const body = await res.json()
      if (typeof body.detail === 'string') message = body.detail
      else if (Array.isArray(body.detail)) message = 'Niepoprawne dane formularza.'
    } catch {
      // brak JSON-a w odpowiedzi
    }
    throw new ApiError(res.status, message)
  }
  return (res.status === 204 ? undefined : await res.json()) as T
}

export function getFeed(cursor: string | null, limit = 10): Promise<FeedPage> {
  const params = new URLSearchParams({ limit: String(limit) })
  if (cursor) params.set('cursor', cursor)
  return request(`/api/feed?${params}`)
}

export function getReport(id: string): Promise<Report> {
  return request(`/api/reports/${id}`)
}

export function getReportsInArea(bbox: BBox, signal?: AbortSignal): Promise<ReportCollection> {
  return request(`/api/reports/geojson?bbox=${bbox.join(',')}`, { signal })
}

export interface NewReport {
  photos: File[]
  location: LngLat | null
  description: string
  hasPlates: boolean | null
}

export function createReport(data: NewReport): Promise<Report> {
  const form = new FormData()
  for (const photo of data.photos) form.append('photos', photo)
  if (data.location) {
    form.append('lng', String(data.location[0]))
    form.append('lat', String(data.location[1]))
  }
  if (data.description.trim()) form.append('description', data.description)
  if (data.hasPlates !== null) form.append('has_plates', String(data.hasPlates))
  return request('/api/reports', { method: 'POST', body: form })
}

export function deleteReport(id: string): Promise<void> {
  return request(`/api/reports/${id}`, { method: 'DELETE' })
}

export function generateSummary(weekStart: string, force = false): Promise<Summary> {
  const params = new URLSearchParams({ week_start: weekStart, force: String(force) })
  return request(`/api/summaries/generate?${params}`, { method: 'POST' })
}
