import { describe, expect, it } from 'vitest'

import {
  formatAmount,
  formatMetric,
  formatStrength,
  formatTimestamp,
  formatValue,
  humanizeKey,
} from '@/lib/format'

describe('format helpers', () => {
  it('formats C3 timestamps and leaves partial dates alone', () => {
    expect(formatTimestamp('2026-10-21T10:15:02Z')).toBe('2026-10-21 10:15:02 UTC')
    expect(formatTimestamp('1979-08')).toBe('1979-08')
  })

  it('formats amounts with the currency minor units', () => {
    expect(formatAmount(120000, 'EUR')).toBe('EUR 120,000.00')
    expect(formatAmount(1, 'not a currency')).toBe('not a currency 1')
  })

  it('formats pattern strength, keys and property values', () => {
    expect(formatStrength(0.79)).toBe('0.79')
    expect(humanizeKey('registration_number')).toBe('registration number')
    expect(formatValue(['gb', 'ie'])).toBe('gb, ie')
    expect(formatValue({ a: 1 })).toBe('{"a":1}')
    expect(formatValue(null)).toBe('')
    expect(formatValue(3)).toBe('3')
  })

  it('formats metrics like the headline templates do', () => {
    expect(formatMetric(120000)).toBe('120,000')
    expect(formatMetric(151.7)).toBe('151.7')
    expect(formatMetric(0.9634)).toBe('0.96')
    expect(formatMetric('EUR')).toBe('EUR')
  })
})
