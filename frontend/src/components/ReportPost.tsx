import { useState } from 'react'
import { Link } from 'react-router-dom'
import { deleteReport } from '../api'
import { formatDateTime } from '../format'
import type { Report } from '../types'
import { DemoBadge, PlatesBadge } from './Badges'
import { ConfirmDialog } from './ConfirmDialog'
import { Gallery } from './Gallery'

interface Props {
  report: Report
  onDeleted: (id: string) => void
  showMapLink?: boolean
}

export function ReportBody({ report, onDeleted, showMapLink = true }: Props) {
  const [confirming, setConfirming] = useState(false)

  return (
    <>
      <header className="post-header">
        <span className="post-icon" aria-hidden>
          🚗
        </span>
        <div>
          <strong>Zgłoszenie grata</strong>
          <div className="muted">{formatDateTime(report.created_at)}</div>
        </div>
        {report.source === 'seed' && <DemoBadge />}
      </header>
      {report.description && <p className="post-text">{report.description}</p>}
      <Gallery
        items={report.photos.map((p) => ({ thumb: p.thumb_url, full: p.url }))}
        alt="Zgłoszony samochód"
      />
      <footer className="post-footer">
        <PlatesBadge hasPlates={report.has_plates} />
        {showMapLink && (
          <Link to={`/mapa?zgloszenie=${report.id}`} className="link">
            📍 Pokaż na mapie
          </Link>
        )}
        <button type="button" className="button button-small button-danger-outline" onClick={() => setConfirming(true)}>
          Usuń
        </button>
      </footer>
      <ConfirmDialog
        open={confirming}
        title="Usunąć zgłoszenie?"
        message="Zgłoszenie zniknie z listy postów i z mapy. Wygenerowane wcześniej raporty tygodniowe pozostaną bez zmian."
        confirmLabel="Tak, usuń"
        danger
        onConfirm={async () => {
          await deleteReport(report.id)
          onDeleted(report.id)
        }}
        onClose={() => setConfirming(false)}
      />
    </>
  )
}

export function ReportPost(props: Props) {
  return (
    <article className="card post">
      <ReportBody {...props} />
    </article>
  )
}
