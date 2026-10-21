// Display helpers. Values are shown as the API returns them; nothing here adds meaning.

/** `2026-10-21T10:15:02Z` as `2026-10-21 10:15:02 UTC`; other strings (partial dates) unchanged. */
export function formatTimestamp(value: string): string {
  const match = /^(\d{4}-\d{2}-\d{2})T(\d{2}:\d{2}:\d{2})Z$/.exec(value)
  return match ? `${match[1]} ${match[2]} UTC` : value
}

/** An amount in major units with its currency's minor units, for example `EUR 120,000.00`. */
export function formatAmount(amount: number, currency: string): string {
  try {
    return new Intl.NumberFormat('en-GB', {
      style: 'currency',
      currency,
      currencyDisplay: 'code',
    })
      .format(amount)
      .replace(/ /g, ' ')
  } catch {
    return `${currency} ${amount}`
  }
}

/** Pattern strength in [0, 1] with two decimals. */
export function formatStrength(value: number): string {
  return value.toFixed(2)
}

/** `registration_number` as `registration number`. */
export function humanizeKey(key: string): string {
  return key.replace(/_/g, ' ')
}

/** A metric value: numbers with thousands separators and at most two decimals, codes as is. */
export function formatMetric(value: unknown): string {
  if (typeof value === 'number') {
    return new Intl.NumberFormat('en-GB', { maximumFractionDigits: 2 }).format(value)
  }
  return formatValue(value)
}

/** A property value as text: lists joined, objects as JSON, everything else as is. */
export function formatValue(value: unknown): string {
  if (value === null || value === undefined) return ''
  if (Array.isArray(value)) return value.map(formatValue).join(', ')
  if (typeof value === 'object') return JSON.stringify(value)
  return String(value)
}
