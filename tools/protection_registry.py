#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tools/protection_registry.py — سجل حماية الإصلاحات السابقة (SARF_COMPREHENSIVE_REPAIR_04 §٣).

لكل بندٍ معرّفه ووصفه، والاختبارات التي تفشل إن عاد الخلل (ملفّها ومعرّف الفحص)، مستخرجةً من مخرجات تشغيلٍ فعلي (سطور PASS) بكلماتٍ
مفتاحية مسمّاة؛ وبندٌ بلا اختبار يُعلَن فجوةً لا يُعدّ محمياً.

    python3 tools/protection_registry.py <مجلد مخرجات الاختبارات> --out tests/protection_registry.json
"""
import argparse, glob, json, os, re

# الربط سلوكيٌّ مسمّى (SARF_DEPENDENCY_PIPELINE_AND_COMPLETION_05 §٩): لكل بندٍ فحوصٌ بعينها (الملف، ونصّ الفحص الذي يطبعه)
# تفشل إن عاد الخلل؛ لا كلمةٌ مفتاحية في عنوان. وما لا فحص سلوكياً له يُعلن فجوة.
ITEMS = [
    ('PR01', 'لا جذر ولا وزن للأوجه المحمية دستورياً', [('test_root', 'وَلَسۡتُمۡ: «ليس» عاملٌ محمي دستورياً'), ('test_root', 'مُوسَىٰ: اسمٌ ذهبي لا جذر له'),
                                                       ('test_root', 'لَنۡ نَّبۡرَحَ، حَتَّىٰ يَرۡجِعَ')]),
    ('PR02', 'استمرار التحليل النحوي للوحدات المحمية', [('test_round006', 'X01 «الذين»'), ('test_round006', 'X05 «أيّ» منادى'), ('test_inflection', 'I09 الحماية تنتقل إلى المحور')]),
    ('PR03', 'منع التقشير الزائف والضمير المتصل بلا مضيف والإدغام عبر حدٍّ غير مرخّص',
     [('test_segment', 'فِيهِمْ'), ('test_closure', 'E02 A02 لا يقول «مضيفها الوحيد»'), ('test_normalize_trace', 'ج: الشدّة محفوظة كلها في الناتج المعياري')]),
    ('PR04', 'حفظ الشدّة والحركات ومواقع المصدر', [('test_cell_rules', 'خليتا الشدة وقوعان مختلفان'), ('test_cell_rules', 'إعادة التركيب: الشدة المفكوكة'),
                                                 ('test_normalize_trace', 'السجل: كل عمليةٍ تحمل الحقول الثلاثة عشر')]),
    ('PR05', 'حذف الخنجرية مع الألف المقصورة وإبقاء المقصورة', [('test_normalize_trace', 'ب: «إِحۡدَىٰهُمَا»'),
                                                              ('test_normalize_trace', 'ب مقابل: المقصورة الخنجرية آخر الكلمة تبقى ى')]),
    ('PR06', 'أحكام «تكونَ» و«يكونا» و«يأبَ» و«يضارَّ» و«ليتقِ» و«ليمللِ»',
     [('test_inflection', 'I06 أن تكونَ'), ('test_round006', 'D02 «يَكُونَا»'), ('test_inflection', 'I11 يأبَ'), ('test_closure', 'F02 ن٦ «لَا يُضَآرَّ'),
      ('test_inflection', 'I05 ليتقِ'), ('test_round006', 'X20 «يتقِ» مجزومٌ بحذف حرف العلة، و«يمللِ»')]),
    ('PR07', 'آخر حركةٍ ليست إعراباً بلا صنف الكلمة وقاعدة العلامة', [('test_inflection', 'I03 عليهِ'), ('test_inflection', 'I04 علَّمَ'),
                                                                   ('test_round006', 'I18 ذلكم: لا تُذكر حركة بناءٍ من ميم الخطاب')]),
    ('PR08', 'اتفاق العامل والمعمول والعبارة الإعرابية', [('test_inflection', 'I01 في البيتِ'), ('test_round006', 'I19 العدد المرشّح'),
                                                        ('test_inflection', 'M01 إفساد العلامة')]),
    ('PR09', 'حماية لفظ الجلالة في المحاور كلها', [('test_inflection', 'I09 الحماية تنتقل إلى المحور'), ('test_round006', 'X15 «اللَّهُ»')]),
    ('PR10', 'عرض الأدلة كاملة', [('test_closure', 'R08 ن٣ لا بتر في السجل')]),
    ('PR11', 'ترخيص الوجه المحلي مع تأجيل الاختيار', [('test_round006', 'X44 ترخيص الوجه غير اختياره'), ('test_round006', 'X16 «لا يأبَ»')]),
    ('PR12', 'X04: تغيير حالة الوجه إلى LICENSED لا يصنع دليله', [('test_mudari', 'X04 '), ('test_mudari', 'X04b')]),
    ('PR13', 'سجل المستتر وهويته وعدم اختلاق محارف مصدرٍ له', [('test_mudari', 'X01b'), ('test_mudari', 'X01c')]),
    ('PR14', 'تضييق مانع التباس مضارع «تفعّل/تفاعل»', [('test_mudari', 'G01'), ('test_mudari', 'W13')]),
    ('PR15', 'فصل طرف الإسناد المشترك في «يكونا» عن الخبر واختيار الاستعمال', [('test_mudari', 'K01 «يَكُونَا» في الشهادة مفكَّك')]),
    ('PR16', 'هوية الوجه بالمرشّح الكامل، وشروط الاستيفاء، والقاعدة والمقدّمات', [('test_mudari', 'G04 '), ('test_mudari', 'G06 '),
                                                                                 ('test_mudari', 'G07 '), ('test_mudari', 'G08 '), ('test_mudari', 'G09 ')]),
    ('PR17', 'مدقّق الفقرة يكشف الإفسادات ولا يثق بالمكتوب', [('test_paragraph', 'M14 '), ('test_paragraph', 'M15 '), ('test_paragraph', 'M18 '),
                                                          ('test_paragraph', 'M12 ')]),
    ('PR18', 'آخر السورة آخر كلمةٍ فيها', [('test_paragraph', 'S01 '), ('test_paragraph', 'S03 '), ('test_engine', 'E16 ')]),
    ('PR19', '«إذا»: لا يحذف الشرط مسلكٌ دون العتبة', [('test_paragraph', 'K01 '), ('test_paragraph', 'K06 '), ('test_paragraph', 'K11 ')]),
    ('PR20', 'المحرّك: المخرج المعلن والإصدار والدورة والمراجعة', [('test_engine', 'E06 '), ('test_engine', 'E10 '), ('test_engine', 'E11 '),
                                                               ('test_engine', 'E09 ')]),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('outdir')
    ap.add_argument('--out', required=True)
    args = ap.parse_args()
    out = {}
    for f in sorted(glob.glob(os.path.join(args.outdir, 'test_*.txt'))):
        out[os.path.basename(f)[:-4]] = [l.rstrip('\n') for l in open(f, encoding='utf-8', errors='ignore')]
    reg = []
    for iid, desc, tests in ITEMS:
        rows = []
        for t, label in tests:
            lines = [l for l in out.get(t, []) if label in l]
            ok = any(l.startswith(('PASS ', 'OK ')) for l in lines)
            rows.append(dict(test=t, check_id=label, observed='PASS' if ok else ('FAIL' if lines else 'NOT_FOUND_IN_RUN')))
        reg.append(dict(id=iid, description=desc, tests=rows, n_tests=len(rows),
                        status='PROTECTED' if rows and all(r['observed'] == 'PASS' for r in rows) else 'GAP_OR_FAIL'))
    json.dump(dict(source=os.path.abspath(args.outdir), method='ربطٌ سلوكيٌّ مسمّى بفحوصٍ بعينها', items=reg),
              open(args.out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    for r in reg:
        print(r['id'], r['status'], [x['observed'] for x in r['tests']])


if __name__ == '__main__':
    main()
