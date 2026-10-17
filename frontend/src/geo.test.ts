import type { LatLngBounds } from 'leaflet'
import { describe, expect, it } from 'vitest'
import { bboxToLeaflet, boundsToBBox, fromLeaflet, toLeaflet } from './geo'

describe('geo', () => {
  it('zamienia [lng, lat] z API na [lat, lng] Leafleta i z powrotem', () => {
    expect(toLeaflet([18.67, 50.29])).toEqual([50.29, 18.67])
    expect(fromLeaflet({ lat: 50.29, lng: 18.67 })).toEqual([18.67, 50.29])
  })

  it('zamienia granice widoku na bbox API i odwrotnie', () => {
    // Atrapa: Leaflet w Node nie działa (wymaga window), a geo.ts potrzebuje tylko tych metod.
    const bounds = {
      getSouthWest: () => ({ lat: 50.2, lng: 18.5 }),
      getNorthEast: () => ({ lat: 50.4, lng: 18.9 }),
    } as LatLngBounds
    expect(boundsToBBox(bounds)).toEqual([18.5, 50.2, 18.9, 50.4])
    expect(bboxToLeaflet([18.5, 50.2, 18.9, 50.4])).toEqual([
      [50.2, 18.5],
      [50.4, 18.9],
    ])
  })
})
