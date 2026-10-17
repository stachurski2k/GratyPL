import { useMemo, useState } from 'react'
import { ApiError, generateSummary } from '../api'
import { recentWeeks } from '../format'
import { ConfirmDialog } from './ConfirmDialog'

// Ręczne generowanie raportu (w demo nie ma harmonogramu).
export function GenerateSummary({ onGenerated }: { onGenerated: () => void }) {
  const weeks = useMemo(() => recentWeeks(8), [])
  const [week, setWeek] = useState(weeks[1].start)
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState<{ text: string; error?: boolean } | null>(null)
  const [askReplace, setAskReplace] = useState(false)

  async function run(force: boolean) {
    setBusy(true)
    setMessage(null)
    try {
      const summary = await generateSummary(week, force)
      setMessage({ text: `Raport gotowy: ${summary.report_count} zgłoszeń.` })
      onGenerated()
    } catch (e) {
      if (e instanceof ApiError && e.status === 409) setAskReplace(true)
      else setMessage({ text: e instanceof Error ? e.message : 'Nie udało się wygenerować raportu.', error: true })
    } finally {
      setBusy(false)
    }
  }

  return (
    <section className="card generate">
      <h2>Raport tygodniowy</h2>
      <p className="muted">W wersji demo raport generuje się ręcznie. Wybierz tydzień (pon.–niedz.).</p>
      <div className="generate-row">
        <select value={week} onChange={(e) => setWeek(e.target.value)} aria-label="Tydzień">
          {weeks.map((w) => (
            <option key={w.start} value={w.start}>
              {w.label}
              {w.current ? ' (bieżący, niepełny)' : ''}
            </option>
          ))}
        </select>
        <button type="button" className="button button-primary" onClick={() => run(false)} disabled={busy}>
          {busy ? 'Generuję…' : 'Generuj raport'}
        </button>
      </div>
      {message && <p className={message.error ? 'error' : 'success'}>{message.text}</p>}
      <ConfirmDialog
        open={askReplace}
        title="Raport już istnieje"
        message="Dla tego tygodnia jest już raport. Wygenerować go od nowa? Nowy raport zastąpi poprzedni i uwzględni stan zgłoszeń na dziś."
        confirmLabel="Zastąp raport"
        onConfirm={() => run(true)}
        onClose={() => setAskReplace(false)}
      />
    </section>
  )
}
