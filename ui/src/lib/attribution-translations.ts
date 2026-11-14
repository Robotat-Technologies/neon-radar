import translations from './attributions.json'

const entries: Record<string, { original: string; arabic: string }> = translations

function normalize(value: string): string {
  return value.replace(/\s+/g, ' ').trim()
}

export function localizedAttribution(slug: string, original: string, locale: 'en' | 'ar'): string {
  const entry = entries[slug]

  if (locale !== 'ar' || !entry || normalize(original) !== normalize(entry.original)) {
    return original
  }

  return entry.arabic
}
