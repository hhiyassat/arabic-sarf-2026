# -*- coding: utf-8 -*-
"""تحقّقٌ مستقل من حزمة التطبيع، دون استيراد شيءٍ من شيفرة المشروع (المكتبة القياسية وحدها).

    python3 verify_normalization_package.py --quran <quran_hafs.tsv> --dir <مجلد الحزمة>

يقرأ: normalization_run.json، normalization_cells.jsonl.gz، normalization_ops.jsonl.gz، normalization_previous_output.json
ويعيد حساب:
  ١ البصمات المسجّلة في run.json لملفات الحزمة ونص المصحف
  ٢ استرجاع المصدر حرفياً من محارف الناتج (src) والمحفوظ في السجل (preserved_information.at)، للناتجين
  ٣ اكتمال التسجيل: كل محرفٍ في المصدر إما في الناتج بعينه وموضعه، وإما داخل مجال عمليةٍ مسجَّلة
  ٤ المحاذاة: محارف كل كلمةٍ ناتجة من كلمة مصدرٍ واحدة، إلا ما جمعته N-JOIN-LONE-ALIF
  ٥ NFC للناتجين، ونصّ الناتج يساوي محارف الخلايا
  ٦ الأعداد: العمليات (الكل وبالقاعدة) في الناتج المعياري، والكلمات المتغيّرة عن الناتج السابق، والوقوعات غير المحسومة
  ٧ كل محرف تنوينٍ يحمل شكله في المصدر ووظيفةً غير معيَّنة (None)
ويطبع ما يطابق run.json وما يخالفه. الخروج 0 إن طابق كل شيء.
"""
import argparse, collections, gzip, hashlib, json, os, sys, unicodedata

ap = argparse.ArgumentParser()
ap.add_argument('--quran', required=True)
ap.add_argument('--dir', required=True)
a = ap.parse_args()
J = lambda f: os.path.join(a.dir, f)
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
bad = 0


def check(name, ok, got=''):
    global bad
    bad += not ok
    print(('OK  ' if ok else 'BAD ') + name + ('' if ok else f'  ← {got}'))


run = json.load(open(J('normalization_run.json'), encoding='utf-8'))
idn, cnt = run['identity'], run['counts']
print('هوية التشغيل', idn['run_id'], '· الالتزام', idn['commit'][:10])
check('١ بصمة نص المصحف', sha(a.quran) == idn['quran']['sha256'], sha(a.quran))
check('١ بصمة سجل العمليات', sha(J('normalization_ops.jsonl.gz')) == run['ops_log']['sha256'])
check('١ بصمة الخلايا', sha(J('normalization_cells.jsonl.gz')) == run['cells_log']['sha256'])
check('١ بصمة الناتج السابق', sha(J('normalization_previous_output.json')) == idn['previous_output']['sha256'])

Q = {f'{x[0]}:{x[1]}': x[2] for x in (l.rstrip('\n').split('\t')[:3] for l in open(a.quran, encoding='utf-8'))}
PREV = json.load(open(J('normalization_previous_output.json'), encoding='utf-8'))
OPS = collections.defaultdict(lambda: {'display': [], 'analysis': []})
with gzip.open(J('normalization_ops.jsonl.gz'), 'rt', encoding='utf-8') as f:
    for line in f:
        o = json.loads(line)
        OPS[o['verse']][o['representation']].append(o)

C = collections.Counter()
by_rule = collections.Counter()
TANWIN = {'ً', 'ٌ', 'ٍ'}
with gzip.open(J('normalization_cells.jsonl.gz'), 'rt', encoding='utf-8') as f:
    for line in f:
        R = json.loads(line)
        v, t = R['verse'], R['source']
        C['verses'] += 1
        if t != Q[v]:
            C['source_mismatch'] += 1
        for which in ('display', 'analysis'):
            cells, ops = R['cells_' + which], OPS[v][which]
            if which == 'display':
                for o in ops:
                    by_rule[o['rule_id']] += 1
            if ''.join(c['c'] for c in cells) != R[which]:
                C['text_vs_cells'] += 1
            if unicodedata.normalize('NFC', R[which]) != R[which]:
                C['nfc'] += 1
            got = {i for c in cells for i in c['src']} | {p['at'] for o in ops for p in o['preserved_information']}
            if ''.join(t[i] for i in sorted(got)) != t or len(got) != len(t):
                C['restore_' + which] += 1
            in_op = {i for o in ops for x, y in o['source_spans'] for i in range(x, y)}
            same = {c['src'][0] for c in cells if len(c['src']) == 1 and not c['derived'] and t[c['src'][0]] == c['c']}
            C['unrecorded_' + which] += sum(1 for i in range(len(t)) if i not in in_op and i not in same)
            for c in cells:
                if c['c'] in TANWIN and not (c.get('mark') and c['mark']['function'] is None and c['mark']['form']):
                    C['tanwin_without_form'] += 1
            # المحاذاة
            wof, k = [], 0
            for ch in t:
                wof.append(None if ch == ' ' else k)
                k += ch == ' '
            joined = {wof[i] for o in ops if o['rule_id'] == 'N-JOIN-LONE-ALIF' for x, y in o['source_spans']
                      for i in range(x, y) if wof[i] is not None}
            words, cur, cw = [], '', set()
            for c in cells + [dict(c=' ', src=[])]:
                if c['c'] == ' ':
                    if cur:
                        words.append((cur, cw))
                        if len(cw) > 1 and not cw <= joined:
                            C['alignment_' + which] += 1
                    cur, cw = '', set()
                else:
                    cur += c['c']
                    cw |= {wof[i] for i in c['src'] if wof[i] is not None}
            if which == 'display':
                prev = PREV[v].split(' ')
                if len(prev) != len(words):
                    C['word_count_mismatch'] += 1
                else:
                    C['words'] += len(words)
                    C['words_changed'] += sum(1 for (w, _), p in zip(words, prev) if w != p)
        un_words = set()
        for o in OPS[v]['display'] + OPS[v]['analysis']:
            if o['status'] == 'غير محسوم':
                un_words |= {(v, w) for w in o['words']}
        # الوقوع غير المحسوم يُعدّ بكلمة الناتج (قد تجمع كلمتين من المصدر)
        C['unresolved_source_words'] += len(un_words)

check('٢ نص المصدر في الخلايا يطابق المصحف', C['source_mismatch'] == 0, C['source_mismatch'])
check('٢ استرجاع المصدر حرفياً (الناتج المعياري)', C['restore_display'] == 0, C['restore_display'])
check('٢ استرجاع المصدر حرفياً (التمثيل التحليلي)', C['restore_analysis'] == 0, C['restore_analysis'])
check('٣ لا اختلاف غير مسجَّل (المعياري)', C['unrecorded_display'] == 0, C['unrecorded_display'])
check('٣ لا اختلاف غير مسجَّل (التحليلي)', C['unrecorded_analysis'] == 0, C['unrecorded_analysis'])
check('٤ لا خطأ محاذاة (المعياري)', C['alignment_display'] == 0, C['alignment_display'])
check('٤ لا خطأ محاذاة (التحليلي)', C['alignment_analysis'] == 0, C['alignment_analysis'])
check('٥ الناتجان على NFC، والنص يساوي الخلايا', C['nfc'] == 0 and C['text_vs_cells'] == 0, (C['nfc'], C['text_vs_cells']))
check('٦ عدد الآيات', C['verses'] == cnt['verses'], (C['verses'], cnt['verses']))
check('٦ مجموع العمليات في الناتج المعياري', sum(by_rule.values()) == cnt['operations']['total'],
      (sum(by_rule.values()), cnt['operations']['total']))
check('٦ العمليات بالقاعدة', dict(by_rule) == cnt['operations']['by_rule'],
      {k: (by_rule.get(k), cnt['operations']['by_rule'].get(k)) for k in set(by_rule) | set(cnt['operations']['by_rule'])
       if by_rule.get(k) != cnt['operations']['by_rule'].get(k)})
check('٦ الكلمات المقابَلة', C['words'] == cnt['words'] and C['word_count_mismatch'] == 0, (C['words'], cnt['words']))
check('٦ الكلمات التي تغيّر ناتجها المعياري عن السابق', C['words_changed'] == cnt['words_changed']['normalized_output'],
      (C['words_changed'], cnt['words_changed']['normalized_output']))
check('٧ كل محرف تنوينٍ يحمل شكله ووظيفةً غير معيَّنة', C['tanwin_without_form'] == 0, C['tanwin_without_form'])
print(f'كلمات مصدرٍ في عملياتٍ غير محسومة: {C["unresolved_source_words"]} (وفي run.json بكلمة الناتج: {cnt["words_unresolved"]})')
print('ALL OK' if not bad else f'FAILED {bad}')
sys.exit(1 if bad else 0)
