import type { Map as LeafletMap } from 'leaflet'
import { useCallback, useEffect, useRef, useState } from 'react'
import { CircleMarker, MapContainer, useMap, useMapEvents } from 'react-leaflet'
import { useSearchParams } from 'react-router-dom'
import { getReport, getReportsInArea } from '../api'
import { OsmTiles } from '../components/OsmTiles'
import { ReportBody } from '../components/ReportPost'
import { DEFAULT_CENTER_LEAFLET, boundsToBBox, toLeaflet } from '../geo'
import type { Report, ReportFeature } from '../types'

// Przeładowuje punkty po każdym przesunięciu/zoomie mapy (z opóźnieniem i anulowaniem starych zapytań).
function BBoxLoader({ onLoad }: { onLoad: (features: ReportFeature[]) => void }) {
  const timer = useRef<number | undefined>(undefined)
  const abort = useRef<AbortController | null>(null)

  const map = useMap()

  const schedule = useCallback(() => {
    window.clearTimeout(timer.current)
    timer.current = window.setTimeout(async () => {
      abort.current?.abort()
      abort.current = new AbortController()
      try {
        const data = await getReportsInArea(boundsToBBox(map.getBounds()), abort.current.signal)
        onLoad(data.features)
      } catch (e) {
        if (!(e instanceof DOMException && e.name === 'AbortError')) console.error(e)
      }
    }, 250)
  }, [map, onLoad])

  useMapEvents({ moveend: schedule })

  useEffect(() => {
    schedule()
    return () => {
      window.clearTimeout(timer.current)
      abort.current?.abort()
    }
  }, [schedule])

  return null
}

export function MapPage() {
  const [params, setParams] = useSearchParams()
  const selectedId = params.get('zgloszenie')
  const [map, setMap] = useState<LeafletMap | null>(null)
  const [features, setFeatures] = useState<ReportFeature[]>([])
  const [loaded, setLoaded] = useState<Report | null>(null)
  const [error, setError] = useState<{ id: string; message: string } | null>(null)
  // Pokazujemy tylko dane pasujące do bieżącego parametru w URL.
  const selected = loaded && loaded.id === selectedId ? loaded : null
  const selectedError = error && error.id === selectedId ? error.message : null

  const select = (id: string | null) => setParams(id ? { zgloszenie: id } : {}, { replace: true })

  useEffect(() => {
    if (!selectedId) return
    let active = true
    getReport(selectedId)
      .then((report) => {
        if (!active) return
        setLoaded(report)
        // Wejście z linku „Pokaż na mapie”: wyśrodkuj, jeśli punkt jest poza widokiem.
        if (map && !map.getBounds().contains(toLeaflet(report.location))) {
          map.setView(toLeaflet(report.location), 16)
        }
      })
      .catch(
        (e) =>
          active &&
          setError({ id: selectedId, message: e instanceof Error ? e.message : 'Nie udało się wczytać zgłoszenia.' }),
      )
    return () => {
      active = false
    }
  }, [selectedId, map])

  return (
    <div className="map-page">
      <MapContainer center={DEFAULT_CENTER_LEAFLET} zoom={12} className="full-map" ref={setMap}>
        <OsmTiles />
        <BBoxLoader onLoad={setFeatures} />
        {/* Wybrane zgłoszenie rysujemy na końcu, żeby nie chowało się pod sąsiednimi. */}
        {[...features.filter((f) => f.id !== selectedId), ...features.filter((f) => f.id === selectedId)].map((f) => (
          <CircleMarker
            key={f.id}
            center={toLeaflet(f.geometry.coordinates)}
            radius={f.id === selectedId ? 11 : 8}
            pathOptions={{
              className: [
                'pin',
                f.properties.source === 'seed' ? 'pin-demo' : '',
                f.id === selectedId ? 'pin-selected' : '',
              ].join(' '),
            }}
            eventHandlers={{ click: () => select(f.id) }}
          />
        ))}
      </MapContainer>

      <div className="map-legend card">
        <span>
          Zgłoszeń w widoku: <strong>{features.length}</strong>
        </span>
        <span>
          <i className="dot dot-web" /> zgłoszenie <i className="dot dot-demo" /> dane przykładowe
        </span>
      </div>

      {(selected || selectedError) && (
        <aside className="map-panel card post">
          <button type="button" className="close" onClick={() => select(null)} aria-label="Zamknij podgląd">
            ×
          </button>
          {selectedError && <p className="error">{selectedError}</p>}
          {selected && (
            <ReportBody
              report={selected}
              showMapLink={false}
              onDeleted={(id) => {
                setFeatures((prev) => prev.filter((f) => f.id !== id))
                select(null)
              }}
            />
          )}
        </aside>
      )}
    </div>
  )
}
