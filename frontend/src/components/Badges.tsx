export function DemoBadge() {
  return (
    <span className="badge badge-demo" title="Dane przykładowe wygenerowane na potrzeby demo, nie prawdziwe zgłoszenie">
      Dane przykładowe
    </span>
  )
}

export function PlatesBadge({ hasPlates }: { hasPlates: boolean | null }) {
  if (hasPlates === null) return <span className="badge">Tablice: nie wiadomo</span>
  return <span className="badge">{hasPlates ? 'Ma tablice' : 'Bez tablic'}</span>
}
