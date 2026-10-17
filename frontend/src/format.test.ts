import { describe, expect, it } from 'vitest'
import { formatWeekRange, recentWeeks } from './format'

describe('tygodnie', () => {
  it('liczy tydzień w czasie polskim, nie UTC', () => {
    // Niedziela 22:30 UTC to już poniedziałek 00:30 w Warszawie.
    const weeks = recentWeeks(2, new Date('2026-10-18T22:30:00Z'))
    expect(weeks.map((w) => w.start)).toEqual(['2026-10-19', '2026-10-12'])
    expect(weeks[0]).toMatchObject({ end: '2026-10-26', current: true })
    expect(recentWeeks(1, new Date('2026-10-18T21:59:00Z'))[0].start).toBe('2026-10-12')
  })

  it('formatuje zakres dat po polsku', () => {
    expect(formatWeekRange('2026-10-05', '2026-10-12')).toBe('5–11 października 2026')
    expect(formatWeekRange('2026-09-28', '2026-10-05')).toBe('28 września – 4 października 2026')
  })
})
