import { humanizeKey } from '@/lib/format'
type Locale = 'en' | 'ar'

const arabicTerms: Record<string, string> = {
  cycle_length: 'عدد التحويلات في الدورة',
  sent_amount: 'المبلغ المرسل',
  returned_amount: 'المبلغ العائد',
  currency: 'العملة',
  duration_hours: 'المدة بالساعات',
  duration_days: 'المدة بالأيام',
  return_ratio: 'نسبة المبلغ العائد',
  origin: 'الحساب الذي بدأت منه التحويلات',
  origin_holder: 'صاحب الحساب الذي بدأت منه التحويلات',
  draft: 'مسودة',
  approved: 'معتمد',
  retired: 'متقاعد',
  Person: 'شخص',
  Company: 'شركة',
  Organization: 'منظمة',
  LegalEntity: 'كيان قانوني',
  Address: 'عنوان',
  Account: 'حساب',
  Sanction: 'سجل عقوبات',

  birthDate: 'تاريخ الميلاد',
  birth_date: 'تاريخ الميلاد',
  deathDate: 'تاريخ الوفاة',
  death_date: 'تاريخ الوفاة',
  gender: 'الجنس',
  nationality: 'الجنسية',
  nationalities: 'الجنسيات',
  incorporationDate: 'تاريخ التأسيس',
  incorporation_date: 'تاريخ التأسيس',
  dissolutionDate: 'تاريخ الحل',
  dissolution_date: 'تاريخ الحل',
  registrationNumber: 'رقم التسجيل',
  registration_number: 'رقم التسجيل',
  idNumber: 'رقم الهوية',
  id_number: 'رقم الهوية',
  passportNumber: 'رقم جواز السفر',
  passport_number: 'رقم جواز السفر',
  taxNumber: 'الرقم الضريبي',
  tax_number: 'الرقم الضريبي',
  accountNumber: 'رقم الحساب',
  account_number: 'رقم الحساب',
  iban: 'IBAN',
  lei: 'LEI',
  address: 'العنوان',
  country: 'الدولة',
  countries: 'الدول',
  jurisdiction: 'الولاية القضائية',
  status: 'الحالة',
  legalForm: 'الشكل القانوني',
  legal_form: 'الشكل القانوني',

  DIRECTOR_OF: 'عضوية مجلس الإدارة',
  HOLDS_ACCOUNT: 'حيازة حساب',
  OWNS: 'ملكية',
  HAS_ADDRESS: 'ارتباط بعنوان',
  PAID: 'تحويل مالي',
  CONTROLS: 'سيطرة',
  CONSOLIDATES: 'توحيد القوائم المالية',
  POSSIBLY_SAME_AS: 'تطابق محتمل غير مؤكّد',
}

export function displayTerm(value: string, locale: Locale): string {
  if (locale === 'ar' && Object.hasOwn(arabicTerms, value)) {
    return arabicTerms[value]!
  }

  return humanizeKey(value)
}
