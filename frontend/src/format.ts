// Daty w interfejsie: zawsze czas polski, niezależnie od strefy przeglądarki.
const TZ = 'Europe/Warsaw'

const dateTime = new Intl.DateTimeFormat('pl-PL', {
  timeZone: TZ,
  day: 'numeric',
  month: 'long',
  year: 'numeric',
  hour: '2-digit',
  minute: '2-digit',
})
const dayMonth = new Intl.DateTimeFormat('pl-PL', { timeZone: 'UTC', day: 'numeric', month: 'long' })
const dayMonthYear = new Intl.DateTimeFormat('pl-PL', {
  timeZone: 'UTC',
  day: 'numeric',
  month: 'long',
  year: 'numeric',
})

export function formatDateTime(iso: string): string {
  return dateTime.format(new Date(iso))
}

// Daty kalendarzowe ('YYYY-MM-DD') liczymy w UTC, żeby uniknąć przesunięć strefowych.
function parseDay(day: string): Date {
  return new Date(`${day}T00:00:00Z`)
}

function addDays(day: string, days: number): string {
  const d = parseDay(day)
  d.setUTCDate(d.getUTCDate() + days)
  return d.toISOString().slice(0, 10)
}

/** Zakres tygodnia, np. „5–11 października 2026”. weekEnd jest wyłączny (następny poniedziałek). */
export function formatWeekRange(weekStart: string, weekEnd: string): string {
  const last = addDays(weekEnd, -1)
  const [a, b] = [parseDay(weekStart), parseDay(last)]
  if (a.getUTCMonth() === b.getUTCMonth()) {
    return `${a.getUTCDate()}–${dayMonthYear.format(b)}`
  }
  return `${dayMonth.format(a)} – ${dayMonthYear.format(b)}`
}

function warsawToday(now: Date): string {
  const parts = new Intl.DateTimeFormat('en-CA', {
    timeZone: TZ,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).format(now)
  return parts // en-CA daje format YYYY-MM-DD
}

export interface Week {
  start: string
  end: string
  label: string
  current: boolean
}

/** Ostatnie tygodnie (od bieżącego wstecz), poniedziałek–poniedziałek w czasie polskim. */
export function recentWeeks(count: number, now = new Date()): Week[] {
  const today = warsawToday(now)
  const weekday = (parseDay(today).getUTCDay() + 6) % 7 // 0 = poniedziałek
  const currentStart = addDays(today, -weekday)
  return Array.from({ length: count }, (_, i) => {
    const start = addDays(currentStart, -7 * i)
    const end = addDays(start, 7)
    return { start, end, label: formatWeekRange(start, end), current: i === 0 }
  })
}
