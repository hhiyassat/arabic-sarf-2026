#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tools/audit_protected.py — تدقيق النتائج السابقة ببوابة الحماية الدستورية: كل وقوعٍ من الفئات المحمية الثلاث
(العوامل المائة، والمبنيات، والأسماء الذهبية) كان يدخل مسار الجذر أو الوزن قبل البوابة: بمرشّحات الفعل
(root._morph بلا بوابة)، أو بالمدخل الاسمي في المعجم، مع حالته وجذره المستخرج آنذاك.
  → reports/protected_audit.json   (الآثار التابعة تُلغى بإعادة التشغيل؛ والمقارنة في التقرير)

    python3 tools/audit_protected.py [1-114]
"""
import sys, os, json, collections
H = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + '/'
sys.path.insert(0, H)
from sarf.analyze import analyze
from sarf.catalog import Catalog
from sarf.protected import protected_slot
from sarf.root import _morph
from sarf.cells import lex_index, _lex_key

lo, hi = (int(x) for x in (sys.argv[1] if len(sys.argv) > 1 else '1-114').split('-'))
cat = Catalog([H + 'operators_catalog.jsonl', H + 'operators_catalog_split_vocalized.csv'])
C = collections.Counter()
rows = collections.defaultdict(list)
for l in open(H + 'data/quran_hafs.tsv', encoding='utf-8'):
    s, v, text = l.rstrip('\n').split('\t')
    s, v = int(s), int(v)
    if not lo <= s <= hi:
        continue
    a = analyze(cat, text)
    for seg in a['segments']:
        stems = [x for x in seg['slots'] if x['type'] == 'جذع']
        if not stems:
            continue
        p = protected_slot(seg)
        if p is None:
            continue
        cls = p['cls'] + (' (فئة مؤجَّلة)' if p['ambiguous'] else '')
        C['محمي:' + cls] += 1
        for st in stems:
            m = _morph(st['text'])
            noun = lex_index().get(_lex_key(st['text']), [])
            entered = []
            if m and m.get('candidates'):
                entered.append(f"مرشّحات الفعل ({m['status']}" + (f": {m.get('root')}/{m.get('form_class')}" if m.get('root') else '') + ')')
            if noun:
                entered.append(f'مدخلٌ اسمي في المعجم: {noun[0][0]}')
            if entered:
                C['دخل مسار الجذر:' + cls] += 1
                C['دخل مسار الجذر'] += 1
                if m and m.get('status') in ('accepted', 'ranked'):
                    C[f'كان جذره {m["status"]}:' + cls] += 1
                if len(rows[cls]) < 80:
                    rows[cls].append(dict(loc=f'{s}:{v}:{seg["word_index"] + 1}', word=seg['word'], stem=st['text'],
                                          identity=p['identity'], entered=entered))
json.dump(dict(counts=dict(C), rows=rows), open(H + 'reports/protected_audit.json', 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)
for k, n in sorted(C.items()):
    print(k, n)
