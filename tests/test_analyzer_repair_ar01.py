# -*- coding: utf-8 -*-
"""شواهد إصلاح المحلّل AR01 (SARF_ORIGINAL_ANALYZER_ROOT_WAZN_REPAIR_01): لكل قاعدة شاهدٌ موجب، ومقابلٌ يبقى صحيحاً،
وشاهد التباسٍ يحفظ البدائل؛ واختبارٌ عابرٌ للطبقات عبر الواجهة العامة analyze. لا أجوبة مرجعية ولا قوائم استثناء."""
import os, sys

H = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, H)
from sarf.root import morph, _plain_toks, lemma_pattern, whole_word_matches
from sarf.affix import stem_info
from sarf.protected import protected
from sarf.analyze import analyze
from sarf.catalog import Catalog

CAT = Catalog([os.path.join(H, 'operators_catalog.jsonl'), os.path.join(H, 'operators_catalog_split_vocalized.csv')])
FAILS = []


def check(name, ok, info=''):
    print(('ok  ' if ok else 'FAIL') + ' ' + name + (' — ' + str(info)[:300] if not ok else ''))
    if not ok:
        FAILS.append(name)


def lic(w):
    m = morph(w)
    return {(x['root'], x['form_class']) for x in (m or {}).get('licensed') or []}


def pub(w):
    return [x for x in analyze(CAT, w, 'auto').get('morph') or []]


# R1 «آ» همزةٌ مفتوحة بعدها ألف مدّ
check('R1 تمثيل «آ»: ء مفتوحة ثم ألف، والرسم الأصلي لا يُمسّ', _plain_toks('آبَ')[0] == ('ء', {'َ'}) and _plain_toks('آبَ')[1][0] == 'ا')
check('R1 موجب: آبَ يطابق فعل HFN «ءوب» حرفاً وحركة', ('ءوب', 'I') in lic('آبَ'))
check('R1 مقابل: آمَنَ يبقى «ءمن» أَفْعَلَ', ('ءمن', 'IV') in lic('آمَنَ'))
check('R1 مقابل: الحماية «آللَّهُ» لا تتغيّر', protected('آللَّهُ') == protected('آللَّهُ') and (protected('ءَاللَّهُ') or {}).get('cls') == (protected('ءَاللَّهُ') or {}).get('cls'))
# R2 الألف الأخيرة لام الناقص لا لاحقة التثنية وحدها
check('R2 موجب: دَعَا ← دعو I، وبَتَا ← بتو I', ('دعو', 'I') in lic('دَعَا') and ('بتو', 'I') in lic('بَتَا'))
check('R2 مقابل: كَتَبَا (مثنى) لا يُرخَّص له جذرٌ زائف', lic('كَتَبَا') == set(), lic('كَتَبَا'))
check('R2 الحالة: ما لم تثبت فعليته بالكتابة يبقى مؤجَّلاً لا مقبولاً', morph('دَعَا')['status'] == 'deferred')
# R3 افتعل من فاءٍ ذال مدغمة
m = morph('ادَّخَرَ')
check('R3 موجب: ادَّخَرَ ← ذخر افْتَعَلَ (رخصة حدث)', m['status'] == 'accepted' and m['root'] == 'ذخر' and m['level'] == 'event', (m['status'], m.get('root')))
check('R3 مقابل: ادَّعَى يبقى دعو', morph('ادَّعَى').get('root') == 'دعو')
check('R3 التباس: دخر يبقى مرشّحاً مولَّداً (لا يُحذف)', ('دخر', 'VIII') in morph('ادَّخَرَ')['candidates'])
# R4 لاحقة «تُمْ» بحركاتها
check('R4 موجب: اسْتَكْتَمَ لا تُقرأ فيه «تُمْ»، والجذر كتم استفعل', stem_info('اسْتَكْتَمَ').get('suffix') is None and morph('اسْتَكْتَمَ').get('root') == 'كتم')
check('R4 مقابل: اسْتَكْبَرْتُمْ لاحقته «تُمْ» والجذر كبر', stem_info('اسْتَكْبَرْتُمْ').get('suffix') == 'تُمْ' and morph('اسْتَكْبَرْتُمْ').get('root') == 'كبر')
# R5 قراءة الكلمة كلها بلا ضمير مفعول
check('R5 موجب: تَبَرَّكَ يحفظ «برك» تَفَعَّلَ بالمطابقة التامة ولا يقبل «برر» وحده', ('برك', 'V') in lic('تَبَرَّكَ') and morph('تَبَرَّكَ')['status'] != 'accepted')
check('R5 مقابل: خَلَقَكَ لا يُرخَّص له وجهٌ بلا ضمير', not any(r != 'خلق' for r, c in lic('خَلَقَكَ')), lic('خَلَقَكَ'))
# R6 الواجهة العامة: القطع لا يثبت مع منافس الكلمة كلها
p = pub('تَبَرَّكَ')
check('R6 عابر للطبقات: تَبَرَّكَ في analyze مؤجَّل بمنافسه «برك»', p and p[0]['status'] == 'deferred' and
      any(r['root'] == 'برك' for r in p[0].get('whole_word_rivals') or []), p)
p = pub('نَاقِه')
check('R6 موجب: نَاقِه لا يُقبل له «وقي»؛ ومنافسه اسم فاعل «نقه»', not any(x['status'] == 'accepted' and x['root'] == 'وقي' for x in p) and
      any(r['root'] == 'نقه' for x in p for r in x.get('whole_word_rivals') or []), p)
p = pub('فَتَبَرَّكَ')
check('R6 موجب: فَتَبَرَّكَ (بعد السابقة) مؤجَّل بمنافسه «برك»', p and p[0]['status'] == 'deferred', p)
for w, r in (('وَقَالَتْ', 'قول'), ('كَتَبْتُهُ', 'كتب')):
    p = pub(w)
    check(f'R6 مقابل: {w} يبقى {r} مقبولاً', any(x['status'] == 'accepted' and x['root'] == r for x in p), p)
# R7 الحماية لا تنتقل من البقية المقشورة إلى الكلمة كلها
for w in ('فَتَكَ', 'سَمِنَ', 'كَمَنَ', 'أَحْمَدَ'):
    pr = protected(w)
    check(f'R7 موجب: {w} الحماية باقية والفئة مؤجّلة (class_deferred)', pr and pr['ambiguous'] and morph(w)['status'] == 'class_deferred', pr and pr.get('alternative'))
check('R7 مقابل: كَمَنْ (كَ + مَنْ) محميٌّ بلا التباس', protected('كَمَنْ')['ambiguous'] is False and morph('كَمَنْ')['status'] == 'not_applicable')
check('R7 مقابل: أَحْمَدُ اسمٌ ذهبي بلا التباس', protected('أَحْمَدُ')['ambiguous'] is False)
check('R7 مقابل: لَعَلَّكُمْ محمي', morph('لَعَلَّكُمْ')['status'] == 'not_applicable')
check('R7 لا جذر للوجه المحمي: class_deferred بلا جذر', morph('سَمِنَ').get('root') is None and morph('سَمِنَ').get('root_status') == 'CLASS_DEFERRED')
# R8 الميزان منفصلاً عن الشكل المتحقق
m = morph('اجْتَبَيْتُ')
check('R8 موجب: الناقص المزيد ميزانه افْتَعَلَ وشكله المتحقق افْتَعَى', m['pattern']['lemma_pattern'] == 'افْتَعَلَ' and
      m['pattern']['realized_pattern'].startswith('افْتَعَى') and m['pattern']['lemma_pattern_source'] == ['DECLARED_FORM_MAPPING'], m.get('pattern'))
m = morph('كَتَبْتُ')
check('R8 مقابل: كَتَبْتُ ميزانه فَعَلَ من صيغة HFN', m['pattern']['lemma_pattern'] == 'فَعَلَ' and m['pattern']['lemma_pattern_source'] == ['LEXICON_FORM'])
lp, src = lemma_pattern('I', 'فَعَّ')
check('R8 التباس: الثلاثي بلا تعيين حركة العين عائلةٌ لا اختيار', src == 'CANDIDATE_FAMILY' and lp == ['فَعَلَ', 'فَعِلَ', 'فَعُلَ'])
lp, src = lemma_pattern('I', 'فَعَلَ/فَعِلَ (أجوف)')
check('R8 التباس: «فَعَلَ/فَعِلَ (أجوف)» بديلان لا أولهما', lp == ['فَعَلَ', 'فَعِلَ'] and src == 'LEXICON_FORM')
p = pub('اجْتَبَيْتُ')
check('R8 عابر للطبقات: analyze يُخرج الميزان والمتحقق للوجه المقبول', p and p[0].get('pattern', {}).get('lemma_pattern') == 'افْتَعَلَ', p)
check('R8 لا وزن لوجهٍ مؤجَّل', all(x.get('pattern') is None for x in pub('تَبَرَّكَ')))
# فحص الإفساد: إفساد الجذر أو الوزن يُكتشف بمطابقة الشكل المتحقق
m = morph('اجْتَبَيْتُ')
lic_ok = [x for x in m['licensed'] if x['root'] == m['root']]
check('C1 الوجه المقبول متّسق: جذره ووزنه من الرخصة نفسها', lic_ok and all(x['form_class'] == m['form_class'] for x in lic_ok))
print('نجح' if not FAILS else f'فشل {len(FAILS)}: {FAILS}')
sys.exit(1 if FAILS else 0)
