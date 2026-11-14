import { describe, expect, it } from 'vitest'

import {
  localizedAlertHeadline,
  localizedAlertText,
  localizedCycleSummary,
  localizedPaymentStep,
} from '@/lib/alert-translations'

describe('Arabic alert translations', () => {
  const typology = 'circular_flow'

  it('preserves the synthetic qualification and headline numbers', () => {
    const original =
      'Synthetic scenario: funds returned to the originating account through 4 transfers within 4 days'

    expect(localizedAlertHeadline(original, typology, 'ar')).toBe(
      'سيناريو اصطناعي: عادت الأموال إلى الحساب الذي بدأت منه؛ عدد التحويلات: 4، والمدة بالأيام: 4',
    )
    expect(localizedAlertHeadline(original, typology, 'en')).toBe(original)
  })

  it('does not add a synthetic qualification to a structural headline', () => {
    const original = 'Funds returned to the originating account through 2 transfers within 12 days'

    expect(localizedAlertHeadline(original, typology, 'ar')).toBe(
      'عادت الأموال إلى الحساب الذي بدأت منه؛ عدد التحويلات: 2، والمدة بالأيام: 12',
    )
  })

  it('translates the catalog name and alternative explanations', () => {
    expect(localizedAlertText('Round-tripping or circular flows', typology, 'ar')).toBe(
      'التحويلات الدائرية أو عودة الأموال إلى منشئها',
    )

    expect(localizedAlertText('Refunds and payment reversals', typology, 'ar')).toBe(
      'ردّ المبالغ وعكس عمليات الدفع',
    )

    expect(localizedAlertText('Loan drawdown followed by repayment', typology, 'ar')).toBe(
      'سحب مبلغ قرض ثم سداده',
    )

    expect(localizedAlertText('Intra-group cash pooling and treasury sweeps', typology, 'ar')).toBe(
      'تجميع السيولة داخل المجموعة والتحويلات الآلية لإدارة أرصدة الخزينة',
    )
  })

  it('preserves payment accounts, amount, currency and calendar day', () => {
    const original = 'NRSYN0000000013 sent EUR 103,753.63 to NRSYN0000000004 on 16 February 2026.'

    expect(localizedPaymentStep(original, typology, 'ar')).toBe(
      'حوّل \u2068NRSYN0000000013\u2069 مبلغ \u2068EUR 103,753.63\u2069 إلى \u2068NRSYN0000000004\u2069 بتاريخ 16 فبراير 2026.',
    )
    expect(localizedPaymentStep(original, typology, 'en')).toBe(original)
  })

  it('supports whole payment amounts without adding decimals', () => {
    const original = 'Account A sent GBP 120,000 to Account B on 2 March 2026.'
    const translated = localizedPaymentStep(original, typology, 'ar')

    expect(translated).toContain('\u2068GBP 120,000\u2069')
    expect(translated).toContain('2 مارس 2026')
  })

  it('preserves the summary amounts, account, account count and duration', () => {
    const original =
      'EUR 103,753.63 left account NRSYN0000000013 and EUR 97,690.35 came back to it after passing through three other accounts in 3.7 days.'

    expect(localizedCycleSummary(original, typology, 'ar')).toBe(
      'خرج مبلغ \u2068EUR 103,753.63\u2069 من الحساب \u2068NRSYN0000000013\u2069، وعاد إليه مبلغ \u2068EUR 97,690.35\u2069 بعد المرور عبر حسابات أخرى عددها 3، خلال \u20683.7\u2069 يوم.',
    )
    expect(localizedCycleSummary(original, typology, 'en')).toBe(original)
  })

  it('supports a single intermediary and duration in hours', () => {
    const original =
      'GBP 100 left account Account A and GBP 95 came back to it after passing through one other account in 1 hour.'

    const translated = localizedCycleSummary(original, typology, 'ar')

    expect(translated).toContain('عددها 1')
    expect(translated).toContain('\u20681\u2069 ساعة')
  })

  it('keeps unfamiliar text, unknown months and other typologies unchanged', () => {
    const unknown = 'A different explanation.'
    const unknownMonth = 'A sent EUR 100 to B on 2 Unknown 2026.'
    const payment = 'A sent EUR 100 to B on 2 March 2026.'

    expect(localizedAlertText(unknown, typology, 'ar')).toBe(unknown)
    expect(localizedAlertHeadline(unknown, typology, 'ar')).toBe(unknown)
    expect(localizedCycleSummary(unknown, typology, 'ar')).toBe(unknown)
    expect(localizedPaymentStep(unknownMonth, typology, 'ar')).toBe(unknownMonth)
    expect(localizedPaymentStep(payment, 'another_typology', 'ar')).toBe(payment)
  })
})
