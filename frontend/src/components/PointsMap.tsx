import { CircleMarker, MapContainer, Tooltip } from 'react-leaflet'
import { bboxToLeaflet, toLeaflet } from '../geo'
import type { BBox, LngLat } from '../types'
import { OsmTiles } from './OsmTiles'

interface Props {
  points: { id: string; location: LngLat; label?: string }[]
  bbox: BBox | null
}

// Mała, statyczna mapa z punktami (np. w raporcie tygodniowym).
export function PointsMap({ points, bbox }: Props) {
  if (!bbox || points.length === 0) return null
  const single = bbox[0] === bbox[2] && bbox[1] === bbox[3]
  const view = single
    ? { center: toLeaflet(points[0].location), zoom: 15 }
    : { bounds: bboxToLeaflet(bbox), boundsOptions: { padding: [24, 24] as [number, number] } }

  return (
    <MapContainer {...view} className="mini-map" scrollWheelZoom={false}>
      <OsmTiles />
      {points.map((p) => (
        <CircleMarker key={p.id} center={toLeaflet(p.location)} radius={7} pathOptions={{ className: 'pin' }}>
          {p.label && <Tooltip>{p.label}</Tooltip>}
        </CircleMarker>
      ))}
    </MapContainer>
  )
}
