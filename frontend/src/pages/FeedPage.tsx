import { useCallback, useEffect, useState } from 'react'
import { getFeed } from '../api'
import { GenerateSummary } from '../components/GenerateSummary'
import { ReportPost } from '../components/ReportPost'
import { SummaryPost } from '../components/SummaryPost'
import type { FeedItem } from '../types'

export function FeedPage() {
  const [items, setItems] = useState<FeedItem[]>([])
  const [cursor, setCursor] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async (from: string | null) => {
    setLoading(true)
    setError(null)
    try {
      const page = await getFeed(from)
      setItems((prev) => (from ? [...prev, ...page.items] : page.items))
      setCursor(page.next_cursor)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Nie udało się wczytać postów.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    load(null)
  }, [load])

  return (
    <div className="page feed">
      <GenerateSummary onGenerated={() => load(null)} />
      {items.map((item) =>
        item.type === 'report' ? (
          <ReportPost
            key={item.id}
            report={item}
            onDeleted={(id) => setItems((prev) => prev.filter((i) => i.id !== id))}
          />
        ) : (
          <SummaryPost key={item.id} summary={item} />
        ),
      )}
      {error && <p className="error">{error}</p>}
      {!loading && !error && items.length === 0 && (
        <p className="empty">Nie ma jeszcze żadnych postów. Dodaj pierwsze zgłoszenie!</p>
      )}
      {cursor && (
        <button type="button" className="button load-more" onClick={() => load(cursor)} disabled={loading}>
          {loading ? 'Wczytuję…' : 'Pokaż starsze'}
        </button>
      )}
      {loading && !cursor && <p className="muted center">Wczytuję…</p>}
    </div>
  )
}
