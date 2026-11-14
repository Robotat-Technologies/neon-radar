import { computed, ref } from 'vue'
import { defineStore } from 'pinia'

type Locale = 'en' | 'ar'

const STORAGE_KEY = 'neonradar-locale'

function savedLocale(): Locale {
  try {
    return localStorage.getItem(STORAGE_KEY) === 'ar' ? 'ar' : 'en'
  } catch {
    return 'en'
  }
}

export const useLocaleStore = defineStore('locale', () => {
  const locale = ref<Locale>(savedLocale())
  const isArabic = computed(() => locale.value === 'ar')

  function applyDirection(): void {
    document.documentElement.lang = locale.value
    document.documentElement.dir = isArabic.value ? 'rtl' : 'ltr'
  }

  function setLocale(value: Locale): void {
    locale.value = value
    applyDirection()

    try {
      localStorage.setItem(STORAGE_KEY, value)
    } catch {
      // Language switching still works when browser storage is unavailable.
    }
  }

  function toggleLocale(): void {
    setLocale(isArabic.value ? 'en' : 'ar')
  }

  applyDirection()

  return { locale, isArabic, setLocale, toggleLocale }
})
