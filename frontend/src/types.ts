// Typy odpowiedzi backendu. Współrzędne zawsze [lng, lat] (GeoJSON); konwersja tylko w geo.ts.

export type LngLat = [number, number]
export type BBox = [number, number, number, number] // [minLng, minLat, maxLng, maxLat]

export interface Photo {
  url: string
  thumb_url: string
  taken_at: string | null
}

export interface Report {
  id: string
  created_at: string
  location: LngLat
  description: string | null
  has_plates: boolean | null
  source: 'web' | 'seed'
  photos: Photo[]
}

export interface SnapshotReport {
  id: string
  created_at: string
  location: LngLat
  description: string | null
  has_plates: boolean | null
  thumb_urls: string[]
}

export interface Summary {
  id: string
  week_start: string
  week_end: string
  generated_at: string
  report_count: number
  bbox: BBox | null
  reports: SnapshotReport[]
}

export type FeedItem = (Report & { type: 'report' }) | (Summary & { type: 'summary' })

export interface FeedPage {
  items: FeedItem[]
  next_cursor: string | null
}

export interface ReportFeature {
  type: 'Feature'
  id: string
  geometry: { type: 'Point'; coordinates: LngLat }
  properties: {
    id: string
    created_at: string
    description: string | null
    has_plates: boolean | null
    source: 'web' | 'seed'
    thumb_url: string | null
  }
}

export interface ReportCollection {
  type: 'FeatureCollection'
  features: ReportFeature[]
}
