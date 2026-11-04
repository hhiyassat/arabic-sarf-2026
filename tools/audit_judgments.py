#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tools/audit_judgments.py — فحص أحكام العوامل كلها في المرحلتين ٧ و١١ (المقبول والممنوع والمؤجَّل): الرفض حكمٌ مثبت يحتاج دليلاً كالقبول.

لكل حكم: العامل واستعماله (مجموعته ومعانيه المرفقة)، والمعمول وتحليله (نصّه، وصنفه وصيغته وعلامته من sarf.affix.stem_info)،
والقاعدة (الموانع المفحوصة R1…R10 وM01، وشروط القبول في sarf.judge)، والمانع إن مُنع، وسبب التأجيل، ونطاق الدليل:
  كتابة المعمول (حرفٌ وحركة)، أو بنية الفعل (M01)، أو رخصة البقية (R10: الأبنية والمعجم وHFN)، أو منافسة الخانة، أو علاقة المرحلة ١١.

    PYTHONHASHSEED=0 python3 tools/audit_judgments.py 2:282 [--json out.json]
    PYTHONHASHSEED=0 python3 tools/audit_judgments.py --corpus [--json out.json] [--jobs N]
"""
import argparse, collections, json, os, re, sys

H = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, H)
_CAT = []

SCOPE = (('R10', 'رخصة البقية: الأبنية والمعجم وHFN (sarf.cells)'), ('R8', 'كتابة أول البقية (ساكن أو مشدَّد)'),
         ('R9', 'صنف ما بعد الجار (sarf.affix)'), ('R1/R2: ', 'بنية الفعل بعدها (M01): حذف اللام أو الإدغام'),
         ('R1/R2', 'كتابة المعمول: صنفه وعلامة آخره'), ('R4', 'ما بعد الواو: فعل أو عامل أو ضمير رفع'),
         ('R5', 'حركة اللام وصنف ما بعدها'), ('R6', 'علامة آخر المعمول (الرفع أو السكون)'), ('R7', 'علامة ما بعد أداة الشرط'),
         ('R3', 'علامة ما بعد اسم الفعل'))


def _scope(f):
    ch = ' '.join(f.get('checked') or [])
    why = f.get('reject_reason') or ''
    if 'العلامة المكتوبة على' in why:
        return 'علامة المعمول في علاقة المرحلة ١١ (sarf.judge._written_case)'
    for k, s in SCOPE:
        if k in ch and (k != 'R1/R2: ' or f.get('mood_faces')):
            return s
    if 'منافسة' in ' '.join((f.get('judgement') or {}).get('deferred_because') or []):
        return 'منافسة الخانة'
    return 'علاقة المرحلة ١١ (العلامة في المعمول)'


def judgments(a, ref):
    from sarf.affix import stem_info
    from sarf.evidence import _target_after
    words = [s['word'] for s in a['segments']]
    out = []
    for f in a['operators']:
        r = f.get('relation') or {}
        tgt = _target_after(f, words)
        info = stem_info(tgt) if tgt else {}
        j = f.get('judgement') or {}
        out.append(dict(
            position=f'{ref}:{f["word_index"] + 1}', operator=f['operator'], group=f['group'], operator_class=f.get('operator_class'),
            usage=[m.get('label') for m in f.get('meanings') or []], status=f['status'],
            target=tgt, target_analysis=dict(pos=info.get('pos'), kind=info.get('kind'), mood=info.get('mood'), suffix=info.get('suffix'),
                                             evidence=info.get('evidence')),
            rule_checks=f.get('checked') or [], conditions=j.get('proof') or [], blocker=f.get('reject_reason'),
            deferred_because=j.get('deferred_because') or [], mood_faces=f.get('mood_faces'),
            relation=dict(expected=r.get('expected'), observed=r.get('observed'), consistent=r.get('consistent'), role=r.get('role')) if r else None,
            evidence_scope=_scope(f)))
    return out


def _one(t):
    from sarf.analyze import analyze
    from sarf import quran_source
    s, v, text = t
    return judgments(analyze(_CAT[0], text, quran_source.uthmani_mode()), f'{s}:{v}')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('ref', nargs='?')
    ap.add_argument('--corpus', action='store_true')
    ap.add_argument('--json')
    ap.add_argument('--jobs', type=int, default=2)
    a = ap.parse_args()
    from sarf.catalog import Catalog
    from sarf import quran_source
    _CAT.append(Catalog([os.path.join(H, 'operators_catalog.jsonl'), os.path.join(H, 'operators_catalog_split_vocalized.csv')]))
    V = quran_source.rows()
    if a.corpus:
        import multiprocessing as mp
        with mp.get_context('fork').Pool(a.jobs) as P:
            J = [x for r in P.map(_one, V, chunksize=20) for x in r]
    else:
        s, v = map(int, a.ref.split(':'))
        J = _one(next(t for t in V if t[0] == s and t[1] == v))
    st = collections.Counter(x['status'] for x in J)
    blk = collections.Counter(re.sub(r'«[^»]*»|\([^)]*\)', '…', x['blocker'])[:70] for x in J if x['status'] == 'blocked')
    sc = collections.Counter((x['status'], x['evidence_scope']) for x in J)
    rep = dict(source=quran_source.name(), scope='corpus' if a.corpus else a.ref, by_status=dict(st), blockers=dict(blk.most_common()),
               by_status_scope={f'{k[0]}|{k[1]}': n for k, n in sc.most_common()}, judgments=J if not a.corpus else
               [x for x in J if x.get('mood_faces')])
    print('by status', dict(st))
    for k, n in blk.most_common(25):
        print(f'  {n:6d} {k}')
    if a.json:
        json.dump(rep, open(a.json, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)


if __name__ == '__main__':
    main()
