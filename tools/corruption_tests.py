# -*- coding: utf-8 -*-
"""اختبارات الإفساد (N04): هل يكشف المدقّق المستقل الخلل المصطنع؟ بالمكتبة القياسية، ودوالّ المدقّق نفسه.

    python3 corruption_tests.py --dir <مجلد الحزمة> --quran <quran_hafs.tsv> --verifier <verify_normalization_package.py>
                                [--out corruption_results.json]

كل اختبارٍ على نسخةٍ عميقة مستقلة من سجلّ آية؛ والحزمة المرجعية لا تُمسّ. ويُستدعى الفاحص المختص مباشرة
(check_verse)، فالإخفاق يُرى في التحقق البنيوي والدلالي لا في البصمة وحدها. واختبارٌ واحد من طرفٍ إلى طرف على نسخةٍ
من الحزمة كاملةً بعد إفسادها وتحديث بصماتها في نسختها وحدها.
"""
import argparse, copy, gzip, hashlib, importlib.util, json, os, shutil, subprocess, sys, tempfile

ap = argparse.ArgumentParser()
ap.add_argument('--dir', required=True)
ap.add_argument('--quran', required=True)
ap.add_argument('--verifier', required=True)
ap.add_argument('--out')
a = ap.parse_args()
spec = importlib.util.spec_from_file_location('verifier', a.verifier)
V = importlib.util.module_from_spec(spec)
spec.loader.exec_module(V)

WANT = ('2:282', '2:7', '1:1')
CELLS, OPS = {}, {k: {'display': [], 'analysis': []} for k in WANT}
with gzip.open(os.path.join(a.dir, 'normalization_cells.jsonl.gz'), 'rt', encoding='utf-8') as f:
    for line in f:
        R = json.loads(line)
        if R['verse'] in WANT:
            CELLS[R['verse']] = R
with gzip.open(os.path.join(a.dir, 'normalization_ops.jsonl.gz'), 'rt', encoding='utf-8') as f:
    for line in f:
        o = json.loads(line)
        if o['verse'] in WANT:
            OPS[o['verse']][o['representation']].append(o)
ORIG = {f'{x[0]}:{x[1]}': x[2] for x in (l.rstrip('\n').split('\t')[:3] for l in open(a.quran, encoding='utf-8'))
        if f'{x[0]}:{x[1]}' in WANT}


def summary(res, which):
    x = res[which]
    failed = [k for k in ('A_coverage', 'B_reconstructed', 'C_match', 'G_output_consistent', 'text_vs_cells') if x[k] is False]
    if x['D_alignment_errors']:
        failed.append('D_alignment')
    return failed, x['fail_codes'] + ([x['C_code']] if x['C_code'] else [])


# الأساس: الآيتان سليمتان قبل الإفساد
base = {v: V.check_verse({k: w for k, w in CELLS[v].items() if k != 'source'}, OPS[v], ORIG[v]) for v in WANT}
for v in WANT:
    for w in ('display', 'analysis'):
        assert not summary(base[v], w)[0], (v, w, base[v][w])


def find_pres(ops, pred):
    for o in ops:
        for p in o['preserved_information']:
            if pred(o, p):
                return o, p
    raise LookupError


TESTS = []


def test(no, name, verse, which, expect):
    def deco(fn):
        TESTS.append((no, name, verse, which, expect, fn))
        return fn
    return deco


@test(1, 'تغيير محرفٍ محفوظ (دون تحديث رمزه)', '2:282', 'display', ['B_reconstructed:R3_CODEPOINT'])
def _(R, ops):
    o, p = find_pres(ops, lambda o, p: p['function'] == 'علامة وقف')
    p['char'] = '\u06D6' if p['char'] == '\u06D7' else '\u06D7'
    return f"{o['op_id']} @{p['at']}: علامة الوقف ← {V.cpstr(p['char'])}، والرمز المسجَّل باقٍ {p['codepoint']}"


@test(2, 'تغيير محرفٍ مع تحديث رمزه تحديثاً متّسقاً', '2:282', 'display', ['B_reconstructed:R8_OP_SOURCE_MISMATCH'])
def _(R, ops):
    o, p = find_pres(ops, lambda o, p: p['function'] == 'علامة وقف')
    p['char'] = '\u06D6' if p['char'] == '\u06D7' else '\u06D7'
    p['codepoint'] = f"U+{ord(p['char']):04X}"
    return f"{o['op_id']} @{p['at']}: علامة الوقف ← {p['codepoint']} ورمزها معاً"


@test(3, 'حذف محرفٍ محفوظ لازمٍ للاسترجاع', '2:282', 'display', ['A_coverage', 'B_reconstructed:R1_MISSING'])
def _(R, ops):
    o, p = find_pres(ops, lambda o, p: p['function'] == 'ميم الإقلاب')
    o['preserved_information'].remove(p)
    return f"{o['op_id']}: حُذفت ميم الإقلاب المحفوظة @{p['at']}"


@test(4, 'تغيير موضع محرفٍ محفوظ', '2:282', 'display', ['A_coverage', 'B_reconstructed:R1_MISSING'])
def _(R, ops):
    o, p = find_pres(ops, lambda o, p: p['function'] == 'علامة وقف')
    old = p['at']
    p['at'] = old - 1
    return f"{o['op_id']}: موضع علامة الوقف {old} ← {old - 1}"


@test(5, 'قيمتان متعارضتان للموضع نفسه', '2:282', 'display', ['B_reconstructed:R2_CONFLICT'])
def _(R, ops):
    o, p = find_pres(ops, lambda o, p: p['function'] == 'ميم الإقلاب')
    q = dict(p, char='ۭ', codepoint='U+06ED')
    o['preserved_information'].append(q)
    return f"{o['op_id']} @{p['at']}: سجلٌّ ثانٍ للموضع بقيمة U+06ED"


@test('6a', 'حذف خليةٍ أصلية', '2:282', 'display', ['A_coverage', 'B_reconstructed:R1_MISSING'])
def _(R, ops):
    k = next(i for i, c in enumerate(R['cells_display']) if not c['derived'] and len(c['src']) == 1 and c['c'] == 'ك')
    at = R['cells_display'][k]['src'][0]
    del R['cells_display'][k]
    R['display'] = ''.join(c['c'] for c in R['cells_display'])
    return f'حُذفت خلية «ك» الأصلية (المصدر @{at})، والنص حُدِّث معها لتبقى الخلايا متّسقة'


@test('6b', 'تغيير قيمة خليةٍ أصلية', '2:282', 'display', ['C_match:V1_MISMATCH'])
def _(R, ops):
    k = next(i for i, c in enumerate(R['cells_display']) if not c['derived'] and len(c['src']) == 1 and c['c'] == 'ك')
    R['cells_display'][k]['c'] = 'ق'
    R['display'] = ''.join(c['c'] for c in R['cells_display'])
    return f"خلية «ك» (المصدر @{R['cells_display'][k]['src'][0]}) ← «ق»، والنص حُدِّث معها"


@test(7, 'إفساد تركيبٍ متعدّد المحارف (الحركة والميم ← التنوين)', '2:282', 'display',
      ['A_coverage', 'B_reconstructed:R5_COMPOSITE_UNPRESERVED'])
def _(R, ops):
    o = next(o for o in ops if o['rule_id'] == 'N-IQLAB-TANWIN')
    p = next(p for p in o['preserved_information'] if p['function'].startswith('ضمة'))
    o['preserved_information'].remove(p)
    return f"{o['op_id']}: حُذفت الضمة المحفوظة @{p['at']} من تركيبٍ مصدره الضمة والميم"


@test('8a', 'تغيير mark.form لعلامة تنوين', '2:282', 'display', ['B_reconstructed:R9_MARK_FORM_MISMATCH'])
def _(R, ops):
    c = next(c for c in R['cells_display'] if c.get('mark') and ' ' in c['mark']['form'])
    old = c['mark']['form']
    c['mark']['form'] = 'U+064C'
    return f'mark.form {old} ← U+064C'


@test('8b', 'تغيير مصدر علامة تنوين (src)', '2:282', 'display', ['B_reconstructed:R9_MARK_FORM_MISMATCH'])
def _(R, ops):
    c = next(c for c in R['cells_display'] if c.get('mark') and ' ' in c['mark']['form'])
    old = list(c['src'])
    c['src'] = [old[0]]
    return f'src {old} ← {[old[0]]} (سقطت الميم من مصدر التنوين)'


@test('8c', 'إسناد وظيفةٍ إلى علامة التنوين', '2:282', 'display', ['B_reconstructed:R9_MARK_FORM_MISMATCH'])
def _(R, ops):
    c = next(c for c in R['cells_display'] if c.get('mark'))
    c['mark']['function'] = 'تنوين اسم'
    return 'mark.function null ← «تنوين اسم»'


@test(9, 'محرفٌ مشتقّ يُنسب إلى المكتوب', '2:282', 'analysis', ['B_reconstructed:R6_NONDERIVED_WITHOUT_SOURCE'])
def _(R, ops):
    c = next(c for c in R['cells_analysis'] if c['derived'] and not c['src'])
    c['derived'] = False
    return f'سكونٌ مشتقّ ({V.cpstr(c["c"])}) ← derived=false'


@test('10a', 'فقد مسافةٍ محفوظة (جمع الأجزاء)', '2:282', 'display', ['A_coverage', 'B_reconstructed:R1_MISSING'])
def _(R, ops):
    o, p = find_pres(ops, lambda o, p: p['char'] == ' ')
    o['preserved_information'].remove(p)
    return f"{o['op_id']}: حُذفت المسافة المحفوظة @{p['at']}"


@test('10b', 'فقد علامة الاتجاه المحفوظة', '2:7', 'display', ['A_coverage', 'B_reconstructed:R1_MISSING'])
def _(R, ops):
    o, p = find_pres(ops, lambda o, p: p['char'] == '‏')
    o['preserved_information'].remove(p)
    return f"{o['op_id']}: حُذفت U+200F المحفوظة @{p['at']}"


@test('10c', 'فقد علامة وقفٍ محفوظة', '2:282', 'analysis', ['A_coverage', 'B_reconstructed:R1_MISSING'])
def _(R, ops):
    o, p = find_pres(ops, lambda o, p: p['function'] == 'علامة وقف')
    o['preserved_information'].remove(p)
    return f"{o['op_id']}: حُذفت علامة الوقف المحفوظة @{p['at']}"


def _set_out(R, which, k, ch):
    R['cells_' + which][k]['c'] = ch
    R[which] = ''.join(c['c'] for c in R['cells_' + which])


def _cell_of_op(R, ops, which, rule, pred=lambda c: True):
    """خليةٌ آخرُ عمليةٍ في مسارها من القاعدة rule"""
    last = {}
    for o in ops:
        for x, y in o['normalized_spans'] or []:
            for k in range(x, y):
                last[k] = o
    return next(k for k, o in sorted(last.items()) if o['rule_id'] == rule and pred(R['cells_' + which][k]))


@test(11, 'مراجعة: محرفٌ ناتج من تحويل يُغيَّر مع بقاء الأصل المحفوظ صحيحاً (ألف الوصل في «الرَّحْمَنِ» ← ب)', '1:1', 'display',
      ['G_output_consistent:O1_OUTPUT_NOT_FROM_OPERATION'])
def _(R, ops):
    sp = [i for i, c in enumerate(R['display']) if c == ' ']
    k = next(i for i in range(sp[1] + 1, len(R['cells_display'])) if R['cells_display'][i]['c'] == 'ا')
    _set_out(R, 'display', k, 'ب')
    return f"خلية {k} «ا» (من ٱ بقاعدة N-WASLA) ← «ب»، والعرض حُدِّث معها: {R['display']}"


@test(12, 'تغيير محرفٍ مشتقّ (السكون المضاف) إلى حركةٍ أخرى', '2:282', 'analysis', ['G_output_consistent:O1_OUTPUT_NOT_FROM_OPERATION'])
def _(R, ops):
    k = next(i for i, c in enumerate(R['cells_analysis']) if c['derived'] and not c['src'])
    _set_out(R, 'analysis', k, '\u0650')
    return f'خلية {k}: السكون المشتقّ ← كسرة، والتمثيل التحليلي حُدِّث معها'


@test(13, 'تغيير تنوينٍ ناتج من الإقلاب (ٌ ← ً) مع بقاء شكله ومصدره', '2:282', 'display', ['G_output_consistent:O1_OUTPUT_NOT_FROM_OPERATION'])
def _(R, ops):
    k = _cell_of_op(R, ops, 'display', 'N-IQLAB-TANWIN', lambda c: c['c'] == '\u064C')
    _set_out(R, 'display', k, '\u064B')
    return f'خلية {k}: تنوين الضم من N-IQLAB-TANWIN ← تنوين فتح، وmark.form كما هو'


@test(14, 'إرجاع محرفٍ إلى قيمته الوسيطة في مسارٍ متعدد العمليات (همزة تَسۡـَٔمُوا: أ ← ء)', '2:282', 'display',
      ['G_output_consistent:O1_OUTPUT_NOT_FROM_OPERATION'])
def _(R, ops):
    k = _cell_of_op(R, ops, 'display', 'I-HAMZA', lambda c: c['c'] == 'أ')
    _set_out(R, 'display', k, 'ء')
    return f'خلية {k}: «أ» (آخر مسارها I-HAMZA، وقبلها N-HAMZA-SEAT أنتجت «ء») ← «ء» الوسيطة'


@test(15, 'محرفٌ مشتقّ بلا عمليةٍ في مساره (إزالة موضعه من normalized_spans)', '2:282', 'analysis',
      ['G_output_consistent:O5_DERIVED_WITHOUT_OPERATION'])
def _(R, ops):
    k = next(i for i, c in enumerate(R['cells_analysis']) if c['derived'] and not c['src'])
    for o in ops:
        o['normalized_spans'] = [[x, y] for x, y in (o['normalized_spans'] or []) if not x <= k < y] + \
            [[x, k] for x, y in (o['normalized_spans'] or []) if x < k < y] + [[k + 1, y] for x, y in (o['normalized_spans'] or []) if x <= k < y - 1]
    return f'خلية {k} المشتقّة بلا عملية في مسارها'


results = []
for no, name, verse, which, expect, fn in TESTS:
    R = copy.deepcopy({k: w for k, w in CELLS[verse].items() if k != 'source'})
    ops = copy.deepcopy(OPS[verse])
    edit = fn(R, ops[which])
    res = V.check_verse(R, ops, ORIG[verse])
    failed, codes = summary(res, which)
    observed = set(failed) | {f'{k}:{c}' for k in failed for c in codes}
    hit = all(e in observed or (e.split(':')[0] in failed and e.split(':')[1] in codes if ':' in e else e in failed)
              for e in expect)
    results.append(dict(no=str(no), name=name, verse=verse, representation=which, edit=edit, expected_to_fail=expect,
                        failed_checks=failed, failure_codes=codes, detected=bool(failed), expected_hit=hit,
                        overall_success_reported=not failed))
    print(('DETECTED ' if failed else 'MISSED   ') + ('✓' if hit else '✗') + f' {no} {name}: فشل {failed} {codes}')

# من طرفٍ إلى طرف: نسخةٌ من الحزمة، يُفسد فيها محرفٌ محفوظ بتحديثٍ متّسق، وتُحدَّث بصماتها في النسخة وحدها
tmp = tempfile.mkdtemp()
for f in ('normalization_run.json', 'normalization_cells.jsonl.gz', 'normalization_ops.jsonl.gz', 'normalization_previous_output.json'):
    shutil.copy(os.path.join(a.dir, f), tmp)
lines = gzip.open(os.path.join(tmp, 'normalization_ops.jsonl.gz'), 'rt', encoding='utf-8').read().splitlines()
done = False
for i, line in enumerate(lines):
    o = json.loads(line)
    if not done and o['verse'] == '2:282' and o['representation'] == 'display':
        for p in o['preserved_information']:
            if p['function'] == 'علامة وقف':
                p['char'] = '\u06D6' if p['char'] == '\u06D7' else '\u06D7'; p['codepoint'] = f"U+{ord(p['char']):04X}"
                lines[i] = json.dumps(o, ensure_ascii=False)
                done = True
                break
with gzip.open(os.path.join(tmp, 'normalization_ops.jsonl.gz'), 'wt', encoding='utf-8') as f:
    f.write('\n'.join(lines) + '\n')
run = json.load(open(os.path.join(tmp, 'normalization_run.json'), encoding='utf-8'))
run['ops_log']['sha256'] = hashlib.sha256(open(os.path.join(tmp, 'normalization_ops.jsonl.gz'), 'rb').read()).hexdigest()
json.dump(run, open(os.path.join(tmp, 'normalization_run.json'), 'w', encoding='utf-8'), ensure_ascii=False)
p = subprocess.run([sys.executable, '-I', a.verifier, '--quran', a.quran, '--dir', tmp, '--json', os.path.join(tmp, 'v.json')],
                   capture_output=True, text=True)
vj = json.load(open(os.path.join(tmp, 'v.json'), encoding='utf-8'))
e2e = dict(edit='نسخةٌ من الحزمة: علامة وقفٍ محفوظة في 2:282 ← علامةٍ أخرى برمزها، وبصمة سجل العمليات حُدِّثت في النسخة',
           exit_code=p.returncode, hashes_ok=all(vj['E_hashes'].values()), all_ok=vj['all_ok'], failure_codes=vj['failure_codes'])
print('E2E', e2e)
shutil.rmtree(tmp)
# من طرفٍ إلى طرف (٢): حالة المراجع نفسها، على نسخةٍ من الحزمة، بتحديث نص العرض وبصمة الخلايا في النسخة وحدها
tmp = tempfile.mkdtemp()
for f in ('normalization_run.json', 'normalization_cells.jsonl.gz', 'normalization_ops.jsonl.gz', 'normalization_previous_output.json'):
    shutil.copy(os.path.join(a.dir, f), tmp)
lines = gzip.open(os.path.join(tmp, 'normalization_cells.jsonl.gz'), 'rt', encoding='utf-8').read().splitlines()
R0 = json.loads(lines[0])
sp = [i for i, c in enumerate(R0['display']) if c == ' ']
k = next(i for i in range(sp[1] + 1, len(R0['cells_display'])) if R0['cells_display'][i]['c'] == 'ا')
R0['cells_display'][k]['c'] = 'ب'
R0['display'] = ''.join(c['c'] for c in R0['cells_display'])
lines[0] = json.dumps(R0, ensure_ascii=False)
with gzip.open(os.path.join(tmp, 'normalization_cells.jsonl.gz'), 'wt', encoding='utf-8') as f:
    f.write('\n'.join(lines) + '\n')
run = json.load(open(os.path.join(tmp, 'normalization_run.json'), encoding='utf-8'))
run['cells_log']['sha256'] = hashlib.sha256(open(os.path.join(tmp, 'normalization_cells.jsonl.gz'), 'rb').read()).hexdigest()
json.dump(run, open(os.path.join(tmp, 'normalization_run.json'), 'w', encoding='utf-8'), ensure_ascii=False)
p = subprocess.run([sys.executable, '-I', '-B', a.verifier, '--quran', a.quran, '--dir', tmp, '--json', os.path.join(tmp, 'v.json')],
                   capture_output=True, text=True)
vj = json.load(open(os.path.join(tmp, 'v.json'), encoding='utf-8'))
e2e2 = dict(edit=f"مراجعة: ألف الوصل في «الرَّحْمَنِ» (1:1) ← «ب»، والعرض «{R0['display']}»، وبصمة الخلايا حُدِّثت في النسخة",
            exit_code=p.returncode, hashes_ok=all(vj['E_hashes'].values()), all_ok=vj['all_ok'], failure_codes=vj['failure_codes'])
print('E2E2', e2e2)
shutil.rmtree(tmp)
out = dict(tests=results, end_to_end=e2e, end_to_end_2=e2e2,
           all_detected=all(r['detected'] for r in results) and not e2e['all_ok'] and not e2e2['all_ok'],
           all_expected=all(r['expected_hit'] for r in results))
if a.out:
    json.dump(out, open(a.out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('ALL DETECTED' if out['all_detected'] else 'SOME MISSED', '· كلٌّ بفحصه المتوقَّع' if out['all_expected'] else '· بعضها بفحصٍ غير المتوقَّع')
sys.exit(0 if out['all_detected'] else 1)
