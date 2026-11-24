import { describe, expect, it } from 'vitest'

import { disclaimers } from '@/__tests__/fixtures'
import { localizedDataNotice, standingNoticeText } from '@/lib/notice-translations'

describe('notice translations', () => {
  it('translates the known standing disclaimer into Arabic', () => {
    const translated = standingNoticeText(disclaimers.standing, 'ar')

    expect(translated).toContain('أداة تعليمية مفتوحة المصدر')
    expect(translated).toContain('ليس دليلاً')
    expect(translated).toContain('ليس نظام امتثال معتمداً')
    expect(translated).not.toBe(disclaimers.standing)
  })

  it('translates the synthetic-data notice', () => {
    const translated = localizedDataNotice(disclaimers.synthetic_demo, 'synthetic_demo', 'ar')

    expect(translated).toContain('بيانات اصطناعية')
    expect(translated).toContain('لا تدل على كيفية أداء')
    expect(translated).not.toBe(disclaimers.synthetic_demo)
  })

  it('translates the real-data notice', () => {
    const translated = localizedDataNotice(disclaimers.real_data, 'real_data', 'ar')

    expect(translated).toContain('تطابق غير مؤكّد')
    expect(translated).toContain('نشاط خلفي اصطناعي')
    expect(translated).toContain('وفق القانون')
    expect(translated).not.toBe(disclaimers.real_data)
  })

  it('preserves all original texts in English', () => {
    expect(standingNoticeText(disclaimers.standing, 'en')).toBe(disclaimers.standing)
    expect(localizedDataNotice(disclaimers.synthetic_demo, 'synthetic_demo', 'en')).toBe(
      disclaimers.synthetic_demo,
    )
    expect(localizedDataNotice(disclaimers.real_data, 'real_data', 'en')).toBe(
      disclaimers.real_data,
    )
  })

  it('preserves unfamiliar or changed source texts', () => {
    const changedStanding = `${disclaimers.standing} Updated.`
    const changedSynthetic = `${disclaimers.synthetic_demo} Updated.`
    const changedReal = `${disclaimers.real_data} Updated.`

    expect(standingNoticeText(changedStanding, 'ar')).toBe(changedStanding)
    expect(localizedDataNotice(changedSynthetic, 'synthetic_demo', 'ar')).toBe(changedSynthetic)
    expect(localizedDataNotice(changedReal, 'real_data', 'ar')).toBe(changedReal)
  })

  it('does not use a translation for the wrong notice kind', () => {
    expect(localizedDataNotice(disclaimers.synthetic_demo, 'real_data', 'ar')).toBe(
      disclaimers.synthetic_demo,
    )
  })

  it('accepts whitespace differences in otherwise identical source text', () => {
    const spaced = disclaimers.standing.replace(/ /g, ' \n ')

    expect(standingNoticeText(spaced, 'ar')).toBe(standingNoticeText(disclaimers.standing, 'ar'))
  })
})
