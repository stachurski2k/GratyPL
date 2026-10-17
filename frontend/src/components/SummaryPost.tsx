import { formatDateTime, formatWeekRange } from '../format'
import type { Summary } from '../types'
import { Gallery } from './Gallery'
import { PointsMap } from './PointsMap'

function pluralReports(n: number): string {
  if (n === 1) return 'zgłoszenie'
  const lastTwo = n % 100
  const last = n % 10
  if (last >= 2 && last <= 4 && (lastTwo < 12 || lastTwo > 14)) return 'zgłoszenia'
  return 'zgłoszeń'
}

export function SummaryPost({ summary }: { summary: Summary }) {
  const thumbs = summary.reports.flatMap((r) => r.thumb_urls.map((thumb) => ({ thumb })))

  return (
    <article className="card post post-summary">
      <header className="post-header">
        <span className="post-icon" aria-hidden>
          📊
        </span>
        <div>
          <strong>Raport tygodniowy: {formatWeekRange(summary.week_start, summary.week_end)}</strong>
          <div className="muted">Wygenerowano {formatDateTime(summary.generated_at)}</div>
        </div>
      </header>
      <p className="summary-count">
        <span className="big-number">{summary.report_count}</span> {pluralReports(summary.report_count)} w tym tygodniu
      </p>
      <PointsMap
        bbox={summary.bbox}
        points={summary.reports.map((r) => ({
          id: r.id,
          location: r.location,
          label: r.description ?? formatDateTime(r.created_at),
        }))}
      />
      <Gallery items={thumbs.slice(0, 12)} alt="Zgłoszenie z raportu" />
      {thumbs.length > 12 && <p className="muted">…i {thumbs.length - 12} kolejnych zdjęć</p>}
    </article>
  )
}
