import standingOriginal from '../../../contracts/wording/standing-v1.txt?raw'
import syntheticOriginal from '../../../contracts/wording/synthetic-demo-v1.txt?raw'
import realOriginal from '../../../contracts/wording/real-data-v2.txt?raw'

import type { DataNoticeKind } from '@/lib/notices'

const standingArabic =
  'NeonRadar أداة تعليمية مفتوحة المصدر تكشف أنماطاً بنيوية في البيانات الاصطناعية أو العامة. تطابق نمط ما ليس دليلاً على غسل الأموال أو الفساد أو أي مخالفة أخرى. توجد أسباب مشروعة لكل بنية معروضة هنا تقريباً، بما فيها الشركات القابضة، ووكلاء التسجيل المشتركون، والمديرون المحترفون، ووسطاء المدفوعات، والأعمال التي تتعامل بالنقد. عند استخدام البيانات العامة، قد يشترك أشخاص وكيانات كثيرون في أسماء متطابقة أو متشابهة، وقد تحتوي سجلات المصادر على أخطاء. لا يشير أي محتوى هنا، صراحةً أو ضمناً، إلى أن شخصاً أو كياناً يمكن تحديد هويته قد خالف القانون. NeonRadar ليس نظام امتثال معتمداً، ولا يضمن امتثال أي طرف لأي متطلبات. إذا وجدت خطأً في NeonRadar، فأبلغنا لنصححه؛ أما أخطاء بيانات المصادر فلا يستطيع تصحيحها إلا المصدر نفسه، وسنوضح لك أين يمكنك الإبلاغ عنها.'

const syntheticArabic =
  'بيانات اصطناعية. جميع الشركات والأشخاص والعناوين والحسابات والمدفوعات في هذا العرض ولّدها NeonRadar، ولا وجود لأيٍّ منها في الواقع. أُدرجت عمداً أنماط تشبه غسل الأموال لتوضيح شكل هذه البنى في الرسم البياني، إلى جانب أنشطة عادية تتشابه معها ظاهرياً فقط. نتائج الكشف على البيانات الاصطناعية لا تدل على كيفية أداء NeonRadar عند استخدام بيانات حقيقية.'

const realArabic =
  'يتضمن هذا العرض سجلات من مصادر عامة: سجلات الشركات، ومؤشر GLEIF، وقاعدة بيانات ICIJ للتسريبات الخارجية المبنية من ملفات مسرّبة، وقوائم العقوبات الرسمية، وبيانات الأشخاص المعرّضين سياسياً عند اختيارها. تُدرج هذه المصادر مع تراخيصها في صفحة مصادر البيانات. تُعرض سجلات الأشخاص والشركات الحقيقيين كما نشرها المصدر، وقد تكون غير محدّثة. عندما يبدو أن عدة سجلات تصف الشخص أو الشركة نفسها، قد يعرضها NeonRadar ككيان واحد؛ وأي رابط موسوم بأنه تطابق محتمل هو تطابق غير مؤكّد. لا يضيف NeonRadar أي ادعاءات: أي نشاط دفع يظهر بجانب كيان حقيقي هو نشاط خلفي اصطناعي، وأي نمط يتصل بكيان حقيقي هو مجرد ملاحظة بنيوية. قد تؤدي مطابقة الأسماء إلى تحديد شخص أو شركة بالخطأ، لذا تحقّق من الهوية باستخدام العناوين أو التواريخ أو المعرّفات الرسمية قبل استخلاص أي نتيجة. غياب شارة العقوبات أو الشخص المعرّض سياسياً يعني فقط أن القوائم المحمّلة هنا لا تذكر السجل. قد تتضمن هذه السجلات بيانات شخصية، ويتحمّل من يحمّلها مسؤولية التعامل معها وفق القانون.'

function normalize(value: string): string {
  return value.replace(/\s+/g, ' ').trim()
}

function translate(value: string, original: string, arabic: string, locale: 'en' | 'ar'): string {
  return locale === 'ar' && normalize(value) === normalize(original) ? arabic : value
}

export function standingNoticeText(value: string, locale: 'en' | 'ar'): string {
  return translate(value, standingOriginal, standingArabic, locale)
}

export function localizedDataNotice(
  value: string,
  kind: DataNoticeKind,
  locale: 'en' | 'ar',
): string {
  return kind === 'synthetic_demo'
    ? translate(value, syntheticOriginal, syntheticArabic, locale)
    : translate(value, realOriginal, realArabic, locale)
}
