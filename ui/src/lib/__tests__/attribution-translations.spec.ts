import { describe, expect, it } from 'vitest'

import { localizedAttribution } from '@/lib/attribution-translations'
import translations from '@/lib/attributions.json'

describe('attribution translations', () => {
  it('translates every known attribution into Arabic', () => {
    for (const [slug, entry] of Object.entries(translations)) {
      expect(localizedAttribution(slug, entry.original, 'ar')).toBe(entry.arabic)
      expect(entry.arabic.trim().length).toBeGreaterThan(0)
    }
  })

  it('preserves the original attribution in English', () => {
    for (const [slug, entry] of Object.entries(translations)) {
      expect(localizedAttribution(slug, entry.original, 'en')).toBe(entry.original)
    }
  })

  it('preserves changed source text instead of using an outdated translation', () => {
    for (const [slug, entry] of Object.entries(translations)) {
      const changed = `${entry.original} Updated.`

      expect(localizedAttribution(slug, changed, 'ar')).toBe(changed)
    }
  })

  it('preserves unknown sources and does not mix sources', () => {
    const original = translations.gb_companies_house.original

    expect(localizedAttribution('unknown_source', original, 'ar')).toBe(original)
    expect(localizedAttribution('gleif_lei', original, 'ar')).toBe(original)
  })

  it('accepts whitespace differences in otherwise identical text', () => {
    const entry = translations.gb_companies_house
    const wrapped = entry.original.replace(/ /g, ' \n ')

    expect(localizedAttribution('gb_companies_house', wrapped, 'ar')).toBe(entry.arabic)
  })

  it('retains links present in the original attribution', () => {
    for (const entry of Object.values(translations)) {
      const links = entry.original.match(/https?:\/\/[^\s)]+/g) ?? []

      for (const link of links) {
        expect(entry.arabic).toContain(link)
      }
    }
  })
})
