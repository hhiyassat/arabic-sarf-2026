# -*- coding: utf-8 -*-
"""اختبار عزل المقياس الأعمى (SARF_ROOT_WAZN_BENCHMARK_01):
  T1 المدخل الأعمى عموداه id وword وحدهما، ويُرفض غيره
  T2 قسم الاختبار المحجوب لا يُبنى له مدخل
  T3 تغيير الأجوبة المرجعية لا يغيّر مخرج المحلّل (بايتاً ببايت)
  T4 تغيير ترتيب الصفوف لا يغيّر مخرج كل صف
  T5 التحويل المعلن من الباب إلى الميزان: الباب الأول عائلة، والمزيد ميزانٌ واحد، ولا مقارنة لـ«IV» بوزنٍ عربي مباشرة
  T6 نسخة المقارنة لا تجرّد الحركات ولا تسوّي الهمزات ولا الواو والياء
  T7 المقارنة ترفض صفاً من غير dev
لا تحتاج الحزمة: تُبنى حزمةٌ صغيرة مصطنعة من كلماتٍ عامة"""
import json, os, subprocess, sys, tempfile

H = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, H)
sys.path.insert(0, os.path.join(H, 'tools'))
import root_wazn_bench as B

COLS = B.COLS
WORDS = [('MTX01', 'dev', 'كتب', 'كَتَبَ', 'فعل ماضٍ', 'فَعَلَ'), ('MTX02', 'dev', 'حرش', 'حَارِش', 'اسم فاعل', 'فَاعِل'),
         ('MTX03', 'dev', 'دين', 'دَيْن', 'مصدر', 'فَعْل'), ('MTX04', 'test', 'قول', 'قَالَ', 'فعل ماضٍ', 'فَعَلَ'),
         ('MTX05', 'dev', 'صبر', 'اِصْطَبَرَ', 'فعل ماضٍ', 'افْتَعَلَ')]


def pkg(d, wrong=False):
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, 'testset_all.tsv'), 'w', encoding='utf-8') as f:
        f.write('\t'.join(COLS) + '\n')
        for i, sp, r, w, pos, wz in WORDS:
            if wrong:                                   # أجوبةٌ مقلوبة: جذرٌ ووزنٌ وصنفٌ آخر
                r, wz, pos = 'زيف', 'مُفْتَعَل', 'مصدر'
            row = dict(id=i, split=sp, root=r, root_spaced=' '.join(r), root_type='سالم', word=w, pos=pos, wazn=wz, surface_pattern=wz,
                       wazn_status='VERIFIED', verb='', verb_form='', source='TEST', evidence='', event_id='', rank='CANDIDATE')
            f.write('\t'.join(row[c] for c in COLS) + '\n')


def run_blind(d, order=None):
    inp, out = os.path.join(d, 'in.tsv'), os.path.join(d, 'out.jsonl')
    B.blind_input(d, inp, 'dev')
    if order:
        lines = open(inp, encoding='utf-8').read().splitlines()
        body = lines[1:]
        body = [body[k] for k in order]
        open(inp, 'w', encoding='utf-8').write('\n'.join([lines[0]] + body) + '\n')
    env = dict(os.environ, PYTHONHASHSEED='0')
    subprocess.run([sys.executable, '-P', '-s', os.path.join(H, 'tools', 'root_wazn_bench.py'), 'run', inp, out], check=True, env=env,
                   capture_output=True)
    recs = [json.loads(l) for l in open(out, encoding='utf-8')]
    return {r['id']: json.dumps(r, ensure_ascii=False, sort_keys=True) for r in recs[1:]}, recs[0]['meta']


def main():
    fails = 0

    def check(name, ok, info=''):
        nonlocal fails
        print(('ok  ' if ok else 'FAIL') + ' ' + name + (' — ' + str(info) if info and not ok else ''))
        fails += 0 if ok else 1
    with tempfile.TemporaryDirectory() as t:
        a, b = os.path.join(t, 'a'), os.path.join(t, 'b')
        pkg(a)
        pkg(b, wrong=True)
        # T1
        inp = os.path.join(a, 'in.tsv')
        B.blind_input(a, inp, 'dev')
        head = open(inp, encoding='utf-8').readline().rstrip('\n').split('\t')
        check('T1 المدخل الأعمى (id، word) وحدهما', head == ['id', 'word'], head)
        txt = open(inp, encoding='utf-8').read()
        check('T1 لا جذر ولا وزن ولا صنف في المدخل', not any(x in txt for x in ('كتب\t', 'فَعَلَ', 'فعل ماضٍ', 'فَاعِل')))
        bad = os.path.join(a, 'bad.tsv')
        open(bad, 'w', encoding='utf-8').write('id\tword\troot\nMTX01\tكَتَبَ\tكتب\n')
        r = subprocess.run([sys.executable, '-P', '-s', os.path.join(H, 'tools', 'root_wazn_bench.py'), 'run', bad, os.path.join(a, 'x.jsonl')],
                           capture_output=True, text=True)
        check('T1 يُرفض مدخلٌ فيه عمود الجذر', r.returncode != 0 and not os.path.exists(os.path.join(a, 'x.jsonl')))
        # T2
        try:
            B.blind_input(a, os.path.join(a, 't.tsv'), 'test')
            check('T2 قسم الاختبار مرفوض', False)
        except SystemExit:
            check('T2 قسم الاختبار مرفوض', not os.path.exists(os.path.join(a, 't.tsv')))
        check('T2 المدخل الأعمى لا يحوي صف الاختبار', 'MTX04' not in txt)
        # T3
        ra, ma = run_blind(a)
        rb, mb = run_blind(b)
        check('T3 تغيير الأجوبة لا يغيّر المخرج', ra == rb and ma['input_sha256'] == mb['input_sha256'])
        # T4
        rc, _ = run_blind(a, order=[3, 1, 0, 2])
        check('T4 تغيير الترتيب لا يغيّر مخرج كل صف', ra == rc)
        # T7
        an = os.path.join(a, 'out.jsonl')
        recs = open(an, encoding='utf-8').read().splitlines()
        rec = json.loads(recs[1])
        rec['id'] = 'MTX04'
        open(os.path.join(a, 'leak.jsonl'), 'w', encoding='utf-8').write(recs[0] + '\n' + json.dumps(rec, ensure_ascii=False) + '\n')
        try:
            B.compare(a, os.path.join(a, 'leak.jsonl'), os.path.join(a, 'cmp'))
            check('T7 المقارنة ترفض صف الاختبار', False)
        except SystemExit:
            check('T7 المقارنة ترفض صف الاختبار', True)
    # T5
    check('T5 الباب الأول عائلة ثلاثة موازين', B.FORM_CLASS_TO_WAZN['I'] == {'فَعَلَ', 'فَعِلَ', 'فَعُلَ'})
    from sarf.root import WAZN
    check('T5 التحويل يوافق جدول المحلّل WAZN', all(B.cmp_form(WAZN[k]) in {B.cmp_form(x) for x in v} for k, v in B.FORM_CLASS_TO_WAZN.items() if k in WAZN),
          {k: WAZN.get(k) for k in B.FORM_CLASS_TO_WAZN})
    check('T5 «IV» لا يساوي وزناً عربياً', B.cmp_form('IV') != B.cmp_form('أَفْعَلَ'))
    # T6
    check('T6 لا تجريد', B.cmp_form('فَعَلَ') != B.cmp_form('فعل') and B.cmp_form('فَعَلَ') != B.cmp_form('فَعِلَ'))
    check('T6 لا تسوية للهمزات ولا الواو والياء', B.cmp_form('أَفْعَلَ') != B.cmp_form('إِفْعَلَ') and B.cmp_form('فَوْعَل') != B.cmp_form('فَيْعَل'))
    check('T6 ألف الوصل المكسورة في أول الميزان فرق ترميز', B.cmp_form('اِفْتَعَلَ') == B.cmp_form('افْتَعَلَ'))
    check('T6 NFC', B.cmp_form('فَعَّلَ') == B.cmp_form('فَعَّلَ'))
    print('نجح' if not fails else f'فشل {fails}')
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
