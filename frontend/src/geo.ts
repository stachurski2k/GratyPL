// Jedyne miejsce konwersji współrzędnych.
// Backend (GeoJSON/PostGIS): [lng, lat]. Leaflet: [lat, lng].
import type { LatLngBounds, LatLngExpression, LatLngTuple } from 'leaflet'
import type { BBox, LngLat } from './types'

export function toLeaflet([lng, lat]: LngLat): LatLngTuple {
  return [lat, lng]
}

export function fromLeaflet(latlng: { lat: number; lng: number }): LngLat {
  return [latlng.lng, latlng.lat]
}

export function boundsToBBox(bounds: LatLngBounds): BBox {
  const sw = bounds.getSouthWest()
  const ne = bounds.getNorthEast()
  return [sw.lng, sw.lat, ne.lng, ne.lat]
}

export function bboxToLeaflet([minLng, minLat, maxLng, maxLat]: BBox): [LatLngTuple, LatLngTuple] {
  return [
    [minLat, minLng],
    [maxLat, maxLng],
  ]
}

// Okolice Gliwic i Zabrza.
export const DEFAULT_CENTER: LngLat = [18.72, 50.3]
export const DEFAULT_CENTER_LEAFLET: LatLngExpression = toLeaflet(DEFAULT_CENTER)
