import { useEffect, useRef, useState } from 'react'

interface Props {
  open: boolean
  title: string
  message: string
  confirmLabel: string
  danger?: boolean
  onConfirm: () => Promise<void>
  onClose: () => void
}

export function ConfirmDialog({ open, title, message, confirmLabel, danger, onConfirm, onClose }: Props) {
  const ref = useRef<HTMLDialogElement>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const dialog = ref.current
    if (!dialog) return
    if (open && !dialog.open) {
      setError(null)
      dialog.showModal()
    } else if (!open && dialog.open) {
      dialog.close()
    }
  }, [open])

  async function confirm() {
    setBusy(true)
    setError(null)
    try {
      await onConfirm()
      onClose()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Coś poszło nie tak.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <dialog ref={ref} className="dialog" onClose={onClose} onCancel={busy ? (e) => e.preventDefault() : undefined}>
      <h2>{title}</h2>
      <p>{message}</p>
      {error && <p className="error">{error}</p>}
      <div className="dialog-actions">
        <button type="button" className="button" onClick={onClose} disabled={busy}>
          Anuluj
        </button>
        <button
          type="button"
          className={danger ? 'button button-danger' : 'button button-primary'}
          onClick={confirm}
          disabled={busy}
          autoFocus
        >
          {busy ? 'Chwileczkę…' : confirmLabel}
        </button>
      </div>
    </dialog>
  )
}
