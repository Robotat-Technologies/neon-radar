import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { useLocaleStore } from '@/stores/locale'

const STORAGE_KEY = 'neonradar-locale'

let previousLang: string | null
let previousDir: string | null
let previousLocale: string | null

describe('locale store', () => {
  beforeEach(() => {
    previousLang = document.documentElement.getAttribute('lang')
    previousDir = document.documentElement.getAttribute('dir')
    previousLocale = localStorage.getItem(STORAGE_KEY)

    localStorage.removeItem(STORAGE_KEY)
    setActivePinia(createPinia())
  })

  afterEach(() => {
    vi.restoreAllMocks()

    if (previousLocale === null) localStorage.removeItem(STORAGE_KEY)
    else localStorage.setItem(STORAGE_KEY, previousLocale)

    if (previousLang === null) document.documentElement.removeAttribute('lang')
    else document.documentElement.setAttribute('lang', previousLang)

    if (previousDir === null) document.documentElement.removeAttribute('dir')
    else document.documentElement.setAttribute('dir', previousDir)
  })

  it('defaults to English and left-to-right layout', () => {
    const store = useLocaleStore()

    expect(store.locale).toBe('en')
    expect(store.isArabic).toBe(false)
    expect(document.documentElement.lang).toBe('en')
    expect(document.documentElement.dir).toBe('ltr')
  })

  it('switches both language and direction and saves the choice', () => {
    const store = useLocaleStore()

    store.toggleLocale()

    expect(store.locale).toBe('ar')
    expect(store.isArabic).toBe(true)
    expect(document.documentElement.lang).toBe('ar')
    expect(document.documentElement.dir).toBe('rtl')
    expect(localStorage.getItem(STORAGE_KEY)).toBe('ar')

    store.toggleLocale()

    expect(store.locale).toBe('en')
    expect(document.documentElement.dir).toBe('ltr')
    expect(localStorage.getItem(STORAGE_KEY)).toBe('en')
  })

  it('restores Arabic from a previous session', () => {
    localStorage.setItem(STORAGE_KEY, 'ar')

    const store = useLocaleStore()

    expect(store.locale).toBe('ar')
    expect(document.documentElement.lang).toBe('ar')
    expect(document.documentElement.dir).toBe('rtl')
  })

  it('falls back to English for an unsupported saved value', () => {
    localStorage.setItem(STORAGE_KEY, 'unsupported')

    expect(useLocaleStore().locale).toBe('en')
    expect(document.documentElement.dir).toBe('ltr')
  })

  it('starts normally when reading browser storage fails', () => {
    vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
      throw new Error('Storage unavailable')
    })

    expect(useLocaleStore().locale).toBe('en')
    expect(document.documentElement.dir).toBe('ltr')
  })

  it('still switches language when saving the choice fails', () => {
    const store = useLocaleStore()

    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
      throw new Error('Storage unavailable')
    })

    expect(() => store.setLocale('ar')).not.toThrow()
    expect(store.locale).toBe('ar')
    expect(document.documentElement.dir).toBe('rtl')
  })
})
