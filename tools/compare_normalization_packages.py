# -*- coding: utf-8 -*-
"""مقارنة حزمتي تطبيع على القرآن كله (المكتبة القياسية وحدها)، وحماية إصلاحات N3 بالاسم.

    python3 compare_normalization_packages.py --a <حزمة الأساس> --b <الحزمة الجديدة> [--out ملف.json]

الحكم صارم (N04، بعد المراجعة): أي فرقٍ غير مأذون يُفشل المقارنة (رمز خروج 1)، ولو تساوت النصوص والأعداد.
يُقارَن كل شيءٍ كاملاً لا حقولاً مختارة، ومنه:
  - مجموعة الآيات في الاتجاهين، والتكرار في الخلايا والعمليات وسجلات الفروق؛
  - كل حقلٍ في سجل الآية، وفي كل خلية، وفي كل عملية، وفي كل سجلّ فرق؛
  - وأقسام run.json كلها، إلا الهوية وبصمات الملفات.
والإضافة المأذونة وحدها: source_length في سجل الآية، بشرط أن تساوي طول المصدر. وكل إضافةٍ سواها، أو حذفٌ، أو تغيير،
فرقٌ غير مأذون.
"""
import argparse, collections, gzip, json, os, sys

ap = argparse.ArgumentParser()
ap.add_argument('--a', required=True)
ap.add_argument('--b', required=True)
ap.add_argument('--out')
a = ap.parse_args()
ALLOWED_ADDITIONS = {'cells_record': {'source_length'}}
RUN_EXEMPT = {'identity', 'ops_log', 'cells_log'}       # تختلف بطبيعتها بين تشغيلين (الهوية، وبصمات الملفات المضغوطة)


def load(d):
    dup = collections.Counter()
    cells = {}
    with gzip.open(os.path.join(d, 'normalization_cells.jsonl.gz'), 'rt', encoding='utf-8') as f:
        for line in f:
            R = json.loads(line)
            if R['verse'] in cells:
                dup['cells_verse'] += 1
            cells[R['verse']] = R
    ops = collections.defaultdict(lambda: {'display': [], 'analysis': []})
    seen = set()
    with gzip.open(os.path.join(d, 'normalization_ops.jsonl.gz'), 'rt', encoding='utf-8') as f:
        for line in f:
            o = json.loads(line)
            key = (o['verse'], o['representation'], o.get('op_id'))
            if key in seen:
                dup['op_id'] += 1
            seen.add(key)
            ops[o['verse']][o['representation']].append(o)
    run = json.load(open(os.path.join(d, 'normalization_run.json'), encoding='utf-8'))
    occ = collections.Counter(o['occurrence_id'] for o in run['differences'])
    dup['difference_occurrence_id'] = sum(n - 1 for n in occ.values() if n > 1)
    return cells, ops, run, +dup


A, B = load(a.a), load(a.b)
C = collections.Counter()
ex = collections.defaultdict(list)
added = collections.Counter()


def note(k, v):
    C[k] += 1
    if len(ex[k]) < 5:
        ex[k].append(v)


for side, d in (('a', A[3]), ('b', B[3])):
    for k, n in d.items():
        for _ in range(n):
            note(f'duplicate_{k}_{side}', k)
va, vb = set(A[0]), set(B[0])
for v in sorted(va - vb):
    note('verse_removed', v)
for v in sorted(vb - va):
    note('verse_added', v)
for v in sorted(set(A[1]) ^ set(B[1])):
    note('ops_verse_set_differs', v)


def cmp_dict(x, y, where, allowed=frozenset()):
    """كل مفتاحٍ في الاتجاهين؛ والإضافة المأذونة تُعدّ ولا تُعدّ تغييراً"""
    for key in set(x) | set(y):
        if key not in x:
            if key in allowed:
                added[f'{where}:{key}'] += 1
            else:
                note(f'unauthorized_added_field:{where}:{key}', where)
        elif key not in y:
            note(f'removed_field:{where}:{key}', where)
        elif x[key] != y[key]:
            note(f'changed:{where}:{key}', where)


for v in sorted(va & vb):
    ra, rb = A[0][v], B[0][v]
    flat_a = {k: w for k, w in ra.items() if not k.startswith('cells_')}
    flat_b = {k: w for k, w in rb.items() if not k.startswith('cells_')}
    cmp_dict(flat_a, flat_b, 'cells_record', ALLOWED_ADDITIONS['cells_record'])
    if 'source_length' in rb and (not isinstance(rb['source_length'], int) or rb['source_length'] != len(rb.get('source', ''))):
        note('invalid_source_length', v)
    for which in ('display', 'analysis'):
        ca, cb_ = ra.get('cells_' + which, []), rb.get('cells_' + which, [])
        if len(ca) != len(cb_):
            note(f'cells_{which}_count', v)
        for x, y in zip(ca, cb_):
            cmp_dict(x, y, f'cells_{which}')
        oa, ob_ = A[1][v][which], B[1][v][which]
        if len(oa) != len(ob_):
            note(f'ops_{which}_count', v)
        for x, y in zip(oa, ob_):
            cmp_dict(x, y, f'ops_{which}')
da = {o['occurrence_id']: o for o in A[2]['differences']}
db = {o['occurrence_id']: o for o in B[2]['differences']}
for k in sorted(set(da) ^ set(db)):
    note('difference_record_presence', k)
for k in sorted(set(da) & set(db)):
    cmp_dict(da[k], db[k], 'difference_record')
for key in set(A[2]) | set(B[2]):
    if key in RUN_EXEMPT or key == 'differences':
        continue
    if A[2].get(key) != B[2].get(key):
        note(f'run_json_section:{key}', key)
ka, kb = A[2]['counts'], B[2]['counts']
count_diffs = {k: (ka.get(k), kb.get(k)) for k in set(ka) | set(kb) if ka.get(k) != kb.get(k)}

# حماية إصلاحات N3 بالاسم (في الحزمة الجديدة، وبمقارنتها بالأساس)
P = []
cb, ob, rb = B[:3]


def prot(no, name, ok, ev):
    P.append(dict(no=no, name=name, ok=bool(ok), evidence=ev))


r = cb['2:282']
prot(1, 'حفظ المصدر الأصلي حرفياً (نص المصدر في الخلايا كما هو في الأساس)',
     va == vb and all(B[0][v].get('source') == A[0][v].get('source') for v in A[0]), 'مقارنة حقل source للآيات كلها')
prot(2, 'فصل العرض المعياري عن التمثيل التحليلي',
     sum(1 for v in cb if cb[v]['display'] != cb[v]['analysis']) == sum(1 for v in A[0] if A[0][v]['display'] != A[0][v]['analysis']) > 0,
     'عدد الآيات التي يختلف فيها الناتجان مساوٍ للأساس')
tan = [c for v in cb for w in ('display', 'analysis') for c in cb[v]['cells_' + w] if c['c'] in 'ًٌٍ']
prot(3, 'شكل التنوين ومصدره: mark.form، وmark.function = null، وحالة الوظيفة',
     tan and all(c.get('mark') and c['mark']['form'] and c['mark']['function'] is None and c['mark'].get('function_status')
                 for c in tan), f'{len(tan)} محرف تنوين')
five = {'Q96:15:5', 'Q12:32:17-18', 'Q7:113:7', 'Q26:41:8', 'Q68:3:3'}
mf = {o['occurrence_id'] for v in ob for w in ('display', 'analysis') for o in ob[v][w]
      if o['rule_id'] == 'N-MARK-FUNCTION' and o['status'] == 'غير محسوم'}
prot(4, 'تأجيل الوظيفة في المواضع الخمسة', mf == five, sorted(mf))
iq = [o for v in ob for o in ob[v]['display'] if o['rule_id'] == 'N-IQLAB-TANWIN']
prot(5, 'تركيب الحركة والميم الصغيرة في عمليةٍ واحدة مع حفظ مصدريهما',
     iq and all(o['operation'] == 'تركيب' and any(p['function'].startswith('ميم الإقلاب') for p in o['preserved_information'])
                and len(o['preserved_information']) >= 2 for o in iq), f'{len(iq)} عملية')
words = lambda R, w: R[w].split(' ')
k14 = [d for d in rb['differences'] if d['occurrence_id'] in ('Q2:282:14', 'Q2:282:121')]
prot(6, '«كاتب» و«فسوق» في العرض والتمثيل التحليلي',
     sorted((d['new_output'], d['analysis_representation']) for d in k14) == [('فُسُوقٌ', 'فُسُوقٌ'), ('كَاتِبٌ', 'كَاتِبٌ')],
     [(d['occurrence_id'], d['new_output'], d['analysis_representation']) for d in k14])
prot(7, 'أسباب الفروق، ومنها 3103 بالسكون المشتقّ',
     rb['counts'].get('differences_unexplained') == 0 and rb['counts'].get('differences_only_derived_sukun') == 3103,
     (rb['counts'].get('differences_unexplained'), rb['counts'].get('differences_only_derived_sukun')))
rules8 = ('I-HAMZA', 'I-HAMZA-MADD', 'I-DAGGER-ALIF', 'I-WAW-ALIF', 'I-ALIF-OMIT', 'I-SMALL-LETTER', 'I-ULA-WAW',
          'N-JOIN-LONE-ALIF', 'I-TANWIN-HAMZA-ALIF', 'N-SMALL-NOON', 'N-SMALL-CARRIER')
prot(8, 'إصلاحات الهمزة والخنجرية والحروف الصغيرة والمسافات',
     all(A[2]['counts']['operations']['by_rule'].get(x) == rb['counts']['operations']['by_rule'].get(x) for x in rules8),
     {x: rb['counts']['operations']['by_rule'].get(x) for x in rules8})
sh = lambda P_: sum(c['c'] == 'ّ' for v in P_[0] for c in P_[0][v]['cells_display'])
prot(9, 'حفظ الشدّة والحركات ومعلومات الرسم', sh(A) == sh(B) and C.get('ops_display_preserved_information', 0) == 0,
     f'شدّات العرض {sh(B)}؛ تغيّر المحفوظ {C.get("ops_display_preserved_information", 0)}')
der = lambda P_: sum(1 for v in P_[0] for c in P_[0][v]['cells_analysis'] if c['derived'] and not c['src'])
prot(10, 'تمييز السكون المشتقّ من المكتوب', der(A) == der(B) > 0 and
     all(not (c['derived'] and not c['src']) for v in cb for c in cb[v]['cells_display']), f'مشتقّ بلا مصدر في التحليلي {der(B)}')
prot(11, 'الحالات غير المحسومة وأسبابها وروابطها بالمصدر',
     A[2]['counts']['words_unresolved'] == rb['counts']['words_unresolved'] and A[2]['unresolved_by_reason'] == rb['unresolved_by_reason'],
     rb['counts']['words_unresolved'])

out = dict(a=a.a, b=a.b, run_a=A[2]['identity']['run_id'], run_b=B[2]['identity']['run_id'],
           changes=dict(C), examples={k: v for k, v in ex.items()}, allowed_additions=dict(added),
           allowed_additions_rule={k: sorted(v) for k, v in ALLOWED_ADDITIONS.items()},
           count_differences=count_diffs, protection=P,
           texts_identical=not any(k.startswith('changed:cells_record:display') or k.startswith('changed:cells_record:analysis')
                                   for k in C),
           all_protected=all(p['ok'] for p in P))
out['verdict_ok'] = not C and not count_diffs and out['all_protected']
if a.out:
    json.dump(out, open(a.out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('فروقٌ غير مأذونة:', dict(C) or 'لا شيء')
print('إضافاتٌ مأذونة (source_length، بقيمٍ صحيحة):', dict(added) or 'لا شيء')
print('فروق الأعداد:', count_diffs or 'لا شيء')
for p in P:
    print(('OK  ' if p['ok'] else 'BAD ') + f"{p['no']} {p['name']}")
print('PASS' if out['verdict_ok'] else 'FAIL')
sys.exit(0 if out['verdict_ok'] else 1)
