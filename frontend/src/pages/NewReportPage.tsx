import type { Map as LeafletMap } from 'leaflet'
import { useEffect, useMemo, useState } from 'react'
import { CircleMarker, MapContainer, useMapEvents } from 'react-leaflet'
import { useNavigate } from 'react-router-dom'
import { createReport } from '../api'
import { OsmTiles } from '../components/OsmTiles'
import { DEFAULT_CENTER_LEAFLET, fromLeaflet, toLeaflet } from '../geo'
import type { LngLat } from '../types'

const MAX_PHOTOS = 5
const MAX_BYTES = 10 * 1024 * 1024
const TYPES = ['image/jpeg', 'image/png', 'image/webp']

function PickPoint({ onPick }: { onPick: (point: LngLat) => void }) {
  useMapEvents({ click: (e) => onPick(fromLeaflet(e.latlng)) })
  return null
}

export function NewReportPage() {
  const navigate = useNavigate()
  const [photos, setPhotos] = useState<File[]>([])
  const [location, setLocation] = useState<LngLat | null>(null)
  const [description, setDescription] = useState('')
  const [hasPlates, setHasPlates] = useState<boolean | null>(null)
  const [map, setMap] = useState<LeafletMap | null>(null)
  const [geoStatus, setGeoStatus] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const previews = useMemo(() => photos.map((f) => URL.createObjectURL(f)), [photos])
  useEffect(() => () => previews.forEach((url) => URL.revokeObjectURL(url)), [previews])

  function addPhotos(files: FileList | null) {
    if (!files) return
    const picked = Array.from(files)
    const wrong = picked.find((f) => !TYPES.includes(f.type))
    const tooBig = picked.find((f) => f.size > MAX_BYTES)
    if (wrong) return setError(`Plik ${wrong.name}: dozwolone są tylko zdjęcia JPEG, PNG i WebP.`)
    if (tooBig) return setError(`Plik ${tooBig.name} jest za duży (maks. 10 MB).`)
    const next = [...photos, ...picked]
    if (next.length > MAX_PHOTOS) return setError(`Możesz dodać najwyżej ${MAX_PHOTOS} zdjęć.`)
    setError(null)
    setPhotos(next)
  }

  function useMyLocation() {
    if (!window.isSecureContext || !navigator.geolocation) {
      setGeoStatus('Geolokalizacja działa tylko przez HTTPS lub na localhost. Zaznacz punkt na mapie.')
      return
    }
    setGeoStatus('Ustalam położenie…')
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        const point: LngLat = [pos.coords.longitude, pos.coords.latitude]
        setLocation(point)
        map?.setView(toLeaflet(point), 17)
        setGeoStatus(null)
      },
      () => setGeoStatus('Nie udało się ustalić położenia. Zaznacz punkt na mapie.'),
      { enableHighAccuracy: true, timeout: 10000 },
    )
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    if (photos.length === 0) return setError('Dodaj przynajmniej jedno zdjęcie.')
    setBusy(true)
    setError(null)
    try {
      await createReport({ photos, location, description, hasPlates })
      navigate('/posty')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Nie udało się wysłać zgłoszenia.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <form className="page new-report" onSubmit={submit}>
      <h1>Zgłoś grata</h1>

      <section className="card form-section">
        <h2>1. Zdjęcia</h2>
        <p className="muted">Od 1 do {MAX_PHOTOS} zdjęć, JPEG, PNG lub WebP, do 10 MB każde.</p>
        <div className="photo-picker">
          {previews.map((url, i) => (
            <figure key={url} className="photo-preview">
              <img src={url} alt={`Zdjęcie ${i + 1}`} />
              <button
                type="button"
                className="close"
                aria-label={`Usuń zdjęcie ${i + 1}`}
                onClick={() => setPhotos(photos.filter((_, j) => j !== i))}
              >
                ×
              </button>
            </figure>
          ))}
          {photos.length < MAX_PHOTOS && (
            <label className="photo-add">
              <span>+ Dodaj zdjęcia</span>
              <input
                type="file"
                accept={TYPES.join(',')}
                multiple
                onChange={(e) => {
                  addPhotos(e.target.files)
                  e.target.value = ''
                }}
              />
            </label>
          )}
        </div>
      </section>

      <section className="card form-section">
        <h2>2. Gdzie stoi?</h2>
        <p className="muted">
          Kliknij na mapie miejsce, w którym stoi auto. Jeśli nie zaznaczysz punktu, spróbujemy odczytać lokalizację
          z danych GPS zdjęcia.
        </p>
        <div className="location-actions">
          <button type="button" className="button" onClick={useMyLocation}>
            📍 Użyj mojej lokalizacji
          </button>
          {location && (
            <button type="button" className="button" onClick={() => setLocation(null)}>
              Usuń punkt
            </button>
          )}
          <span className="muted">
            {location ? `Wybrano: ${location[1].toFixed(5)}, ${location[0].toFixed(5)}` : 'Nie wybrano punktu'}
          </span>
        </div>
        {geoStatus && <p className="muted">{geoStatus}</p>}
        <MapContainer center={DEFAULT_CENTER_LEAFLET} zoom={12} className="pick-map" ref={setMap}>
          <OsmTiles />
          <PickPoint onPick={setLocation} />
          {location && <CircleMarker center={toLeaflet(location)} radius={10} pathOptions={{ className: 'pin pin-selected' }} />}
        </MapContainer>
      </section>

      <section className="card form-section">
        <h2>3. Szczegóły</h2>
        <label className="field">
          <span>Opis (opcjonalnie)</span>
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            maxLength={2000}
            rows={4}
            placeholder="Np. stoi od miesięcy, brak kół, wybite szyby…"
          />
        </label>
        <fieldset className="field">
          <legend>Czy auto ma tablice rejestracyjne?</legend>
          <div className="radio-row">
            {(
              [
                [true, 'Tak'],
                [false, 'Nie'],
                [null, 'Nie wiem'],
              ] as const
            ).map(([value, label]) => (
              <label key={label} className="radio">
                <input type="radio" name="plates" checked={hasPlates === value} onChange={() => setHasPlates(value)} />
                {label}
              </label>
            ))}
          </div>
        </fieldset>
      </section>

      {error && <p className="error">{error}</p>}
      <button type="submit" className="button button-primary button-large" disabled={busy}>
        {busy ? 'Wysyłam…' : 'Wyślij zgłoszenie'}
      </button>
    </form>
  )
}
