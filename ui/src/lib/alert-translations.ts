type Locale = 'en' | 'ar'

const circularTexts: Record<string, string> = {
  'Round-tripping or circular flows': 'التحويلات الدائرية أو عودة الأموال إلى منشئها',

  'Funds leave an account, pass through other accounts and return to the originator or to a party under the same control.':
    'تخرج الأموال من حساب، وتمر عبر حسابات أخرى، ثم تعود إلى الطرف الذي بدأ التحويل أو إلى طرف خاضع للسيطرة نفسها.',

  'Refunds and payment reversals': 'ردّ المبالغ وعكس عمليات الدفع',

  'Loan drawdown followed by repayment': 'سحب مبلغ قرض ثم سداده',

  'Intra-group cash pooling and treasury sweeps':
    'تجميع السيولة داخل المجموعة والتحويلات الآلية لإدارة أرصدة الخزينة',
}

function normalize(value: string): string {
  return value.replace(/\s+/g, ' ').trim()
}

export function localizedAlertText(value: string, typology: string, locale: Locale): string {
  if (locale !== 'ar' || typology !== 'circular_flow') return value

  return circularTexts[normalize(value)] ?? value
}

export function localizedAlertHeadline(value: string, typology: string, locale: Locale): string {
  if (locale !== 'ar' || typology !== 'circular_flow') return value

  const match =
    /^(Synthetic scenario: funds|Funds) returned to the originating account through (\d+) transfers within (\d+) days$/.exec(
      value,
    )

  if (!match) return value

  const prefix = match[1] === 'Synthetic scenario: funds' ? 'سيناريو اصطناعي: ' : ''

  return `${prefix}عادت الأموال إلى الحساب الذي بدأت منه؛ عدد التحويلات: ${match[2]}، والمدة بالأيام: ${match[3]}`
}

const arabicMonths: Record<string, string> = {
  January: 'يناير',
  February: 'فبراير',
  March: 'مارس',
  April: 'أبريل',
  May: 'مايو',
  June: 'يونيو',
  July: 'يوليو',
  August: 'أغسطس',
  September: 'سبتمبر',
  October: 'أكتوبر',
  November: 'نوفمبر',
  December: 'ديسمبر',
}

const accountCounts: Record<string, string> = {
  no: '0',
  one: '1',
  two: '2',
  three: '3',
  four: '4',
  five: '5',
  six: '6',
  seven: '7',
  eight: '8',
}

function isolate(value: string): string {
  return `\u2068${value}\u2069`
}

export function localizedPaymentStep(value: string, typology: string, locale: Locale): string {
  if (locale !== 'ar' || typology !== 'circular_flow') return value

  const match =
    /^(.+?) sent ([A-Z]{3}) ([\d,]+(?:\.\d{2})?) to (.+?) on (\d{1,2}) ([A-Za-z]+) (\d{4})\.$/.exec(
      value,
    )

  if (!match) return value

  const [, sender, currency, amount, receiver, day, month, year] = match
  if (!sender || !currency || !amount || !receiver || !day || !month || !year) {
    return value
  }

  const translatedMonth = arabicMonths[month]
  if (!translatedMonth) return value

  return `حوّل ${isolate(sender)} مبلغ ${isolate(`${currency} ${amount}`)} إلى ${isolate(receiver)} بتاريخ ${day} ${translatedMonth} ${year}.`
}

export function localizedCycleSummary(value: string, typology: string, locale: Locale): string {
  if (locale !== 'ar' || typology !== 'circular_flow') return value

  const match =
    /^([A-Z]{3}) ([\d,]+(?:\.\d{2})?) left account (.+?) and ([A-Z]{3}) ([\d,]+(?:\.\d{2})?) came back to it after passing through (no|one|two|three|four|five|six|seven|eight|\d+) other accounts? in ([\d,]+(?:\.\d+)?) (hour|hours|days)\.$/.exec(
      value,
    )

  if (!match) return value

  const [, sentCurrency, sent, origin, returnedCurrency, returned, count, duration, unit] = match

  if (
    !sentCurrency ||
    !sent ||
    !origin ||
    !returnedCurrency ||
    !returned ||
    !count ||
    !duration ||
    !unit
  ) {
    return value
  }

  const accountCount = accountCounts[count] ?? count
  const durationUnit = unit === 'days' ? 'يوم' : 'ساعة'

  return `خرج مبلغ ${isolate(`${sentCurrency} ${sent}`)} من الحساب ${isolate(origin)}، وعاد إليه مبلغ ${isolate(`${returnedCurrency} ${returned}`)} بعد المرور عبر حسابات أخرى عددها ${accountCount}، خلال ${isolate(duration)} ${durationUnit}.`
}
