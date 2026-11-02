# -*- coding: utf-8 -*-
"""اختبارات إفساد أداة المقارنة: كل فرقٍ غير مأذون يجب أن يُعيد رمز خروجٍ غير صفري، والنسخة السليمة صفراً.

    python3 compare_tool_tests.py --base <حزمة الأساس N3> --pkg <الحزمة الجديدة> --tool <compare_normalization_packages.py>
                                  [--out compare_tool_tests.json]

كل اختبارٍ على نسخةٍ مستقلة في مجلدٍ مؤقت؛ الحزمتان المرجعيتان لا تُمسّان.
"""
import argparse, gzip, json, os, shutil, subprocess, sys, tempfile

ap = argparse.ArgumentParser()
ap.add_argument('--base', required=True)
ap.add_argument('--pkg', required=True)
ap.add_argument('--tool', required=True)
ap.add_argument('--out')
ap.add_argument('--only', help='أرقام اختباراتٍ مختارة مفصولة بفاصلة (للتحقق من أداةٍ سابقة)')
a = ap.parse_args()
FILES = ('normalization_cells.jsonl.gz', 'normalization_ops.jsonl.gz', 'normalization_run.json')


def rd(d, f):
    return gzip.open(os.path.join(d, f), 'rt', encoding='utf-8').read().splitlines()


def wr(d, f, lines):
    with gzip.open(os.path.join(d, f), 'wt', encoding='utf-8') as g:
        g.write('\n'.join(lines) + '\n')


def edit_cells(d, fn):
    L = rd(d, FILES[0])
    out = fn(L)
    wr(d, FILES[0], out if out is not None else L)


def edit_run(d, fn):
    p = os.path.join(d, FILES[2])
    r = json.load(open(p, encoding='utf-8'))
    fn(r)
    json.dump(r, open(p, 'w', encoding='utf-8'), ensure_ascii=False)


def in_verse(L, verse, fn):
    for i, l in enumerate(L):
        R = json.loads(l)
        if R['verse'] == verse:
            fn(R)
            L[i] = json.dumps(R, ensure_ascii=False)
            return L
    raise LookupError(verse)


def t1(d):
    def f(R):
        c = next(c for c in R['cells_analysis'] if len(c['src']) == 1 and not c['derived'])
        c['src'] = [c['src'][0] + 1]
    edit_cells(d, lambda L: in_verse(L, '7:1', f))
    return 'مراجعة: موضع مصدر خليةٍ واحدة في التمثيل التحليلي لـ7:1 (+1)، والنصوص كما هي'


def t2(d):
    edit_cells(d, lambda L: in_verse(L, '2:282', lambda R: R['cells_display'][0].__setitem__('note', 'x')))
    return 'حقلٌ غير مأذون (note) في خليةٍ من 2:282'


def t3(d):
    edit_cells(d, lambda L: in_verse(L, '2:282', lambda R: R.__setitem__('source_length', R['source_length'] + 1)))
    return 'source_length خاطئ (+1) في 2:282'


def t4(d):
    edit_cells(d, lambda L: in_verse(L, '2:282', lambda R: R.__setitem__('extra', 1)))
    return 'حقلٌ مضاف غير source_length في سجل الآية 2:282'


def t5(d):
    edit_cells(d, lambda L: [l for l in L if json.loads(l)['verse'] != '114:6'])
    return 'حذف سجل الآية 114:6'


def t6(d):
    def f(L):
        R = json.loads(L[0])
        R['verse'] = '115:1'
        return L + [json.dumps(R, ensure_ascii=False)]
    edit_cells(d, f)
    return 'آيةٌ مضافة غير موجودة في الأساس (115:1)'


def t7(d):
    edit_cells(d, lambda L: L + [L[0]])
    return 'تكرار سجل الآية 1:1'


def t8(d):
    def f(R):
        c = next(c for c in R['cells_display'] if c.get('mark'))
        c['mark']['form'] = 'U+064C'
    edit_cells(d, lambda L: in_verse(L, '2:282', f))
    return 'mark.form لعلامة تنوين في 2:282 ← U+064C، والنصوص كما هي'


def t9(d):
    L = rd(d, FILES[1])
    o = json.loads(L[0])
    o['status'] = 'غير محسوم'
    L[0] = json.dumps(o, ensure_ascii=False)
    wr(d, FILES[1], L)
    return f"حالة العملية الأولى ({o['op_id']}) ← غير محسوم"


def t10(d):
    edit_run(d, lambda r: r['differences'][0].__setitem__('verification', 'x'))
    return 'حقل verification في أول سجلّ فرق'


def t11(d):
    edit_run(d, lambda r: r['counts'].__setitem__('words_unresolved', r['counts']['words_unresolved'] + 1))
    return 'counts.words_unresolved +1'


def t12(d):
    edit_run(d, lambda r: r['differences'].append(r['differences'][0]))
    return 'تكرار أول سجلّ فرق'


def t13(d):
    L = rd(d, FILES[1])
    wr(d, FILES[1], L + [L[0]])
    return 'تكرار أول عملية في سجل العمليات'


def t14(d):
    L = rd(d, FILES[1])
    o = json.loads(L[5])
    o['added_key'] = 1
    L[5] = json.dumps(o, ensure_ascii=False)
    wr(d, FILES[1], L)
    return 'حقلٌ غير مأذون في عملية'


def t15(d):
    edit_cells(d, lambda L: in_verse(L, '2:282', lambda R: R['cells_analysis'].pop()))
    return 'حذف آخر خليةٍ في التمثيل التحليلي لـ2:282 (والنص كما هو)'


def t16(d):
    edit_cells(d, lambda L: in_verse(L, '2:282', lambda R: R.__setitem__('cells_unapproved', [{'c': 'X', 'src': []}])))
    return 'مراجعة: حقلٌ غير مأذون يبدأ بـcells_ (cells_unapproved) في سجل الآية 2:282'


def t17(d):
    edit_run(d, lambda r: r.__setitem__('unapproved_section', None))
    return 'مراجعة: قسمٌ مضاف في run.json بقيمة null (unapproved_section)'


def t18(d):
    edit_run(d, lambda r: r['counts'].__setitem__('unapproved_count', None))
    return 'مفتاحٌ مضاف بقيمة null داخل counts'


def t19(d):
    edit_run(d, lambda r: r.pop('unresolved_by_reason'))
    return 'حذف قسمٍ من run.json (unresolved_by_reason)'


def t20(d):
    edit_cells(d, lambda L: in_verse(L, '2:282', lambda R: R['cells_display'][3].__setitem__('mark', None)))
    return 'مفتاح mark بقيمة null مضافٌ إلى خليةٍ بلا علامة'


def t21(d):
    edit_run(d, lambda r: r.pop('counts'))
    return 'حذف قسم counts كله من run.json (يجب أن يُرفض بحكمٍ مكتوب لا بانهيار)'


TESTS = [(0, 'النسخة السليمة', None, 0)] + [(i, f.__doc__ or '', f, 1) for i, f in enumerate(
    (t1, t2, t3, t4, t5, t6, t7, t8, t9, t10, t11, t12, t13, t14, t15, t16, t17, t18, t19, t20, t21), 1)]
res = []
ONLY = {int(x) for x in a.only.split(',')} if a.only else None
for no, _, fn, want in TESTS:
    if ONLY is not None and no not in ONLY:
        continue
    d = tempfile.mkdtemp()
    for f in FILES:
        shutil.copy(os.path.join(a.pkg, f), d)
    edit = fn(d) if fn else 'لا تعديل: نسخةٌ مطابقة للحزمة الجديدة'
    p = subprocess.run([sys.executable, '-I', a.tool, '--a', a.base, '--b', d, '--out', os.path.join(d, 'c.json')],
                       capture_output=True, text=True)
    c = json.load(open(os.path.join(d, 'c.json'), encoding='utf-8')) if os.path.exists(os.path.join(d, 'c.json')) else {}
    # الكشف حكمٌ مكتوب لا انهيار: المُفسَدة تُخرج 1 مع ملف نتائج حكمُه verdict_ok=false، والسليمة 0 مع true
    crashed = not c
    ok = p.returncode == want and not crashed and c.get('verdict_ok') is (want == 0)
    res.append(dict(no=no, edit=edit, expected_exit=want, exit_code=p.returncode, ok=ok, crashed=crashed,
                    verdict_ok=c.get('verdict_ok'), stderr_tail=p.stderr[-300:] if crashed else '',
                    detected_as=sorted((c.get('changes') or {}).keys())[:6],
                    count_differences=sorted((c.get('count_differences') or {}).keys())))
    print(('OK  ' if ok else 'BAD ') + f'{no} {edit}: خروج {p.returncode} (المتوقَّع {want}) {res[-1]["detected_as"]}')
    shutil.rmtree(d)
out = dict(tests=res, all_ok=all(r['ok'] for r in res))
if a.out:
    json.dump(out, open(a.out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('ALL OK' if out['all_ok'] else 'FAILED')
sys.exit(0 if out['all_ok'] else 1)
