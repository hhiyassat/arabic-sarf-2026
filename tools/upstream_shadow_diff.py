"""tools/upstream_shadow_diff.py — فروق الانتقال الظلي (SARF_UPSTREAM_CONSUMPTION_2026_11_08 §١٠-٢)، فرقاً فرقاً بهوية الوقوع والوجه ومسار الحقل.

    python3 tools/upstream_shadow_diff.py <الأساس.pkl.gz> <الظلي.pkl.gz> <HFN_الأساس> <HFN_الظلي> <OUT_PREFIX>

المدخلان تفريغا tools/snapshot_outputs.py لشيفرةٍ واحدة على إصدارين من HFN، فكل فرقٍ أثرُ البيانات وحدها (لا الشيفرة).
لكل فرقٍ ورقي: الآية، ورقم الكلمة والخانة، ومعرّف الوجه (analysis_id) في الطرفين، ومسار الحقل، والقيمتان؛ وسببه من مقارنة أحداث
(الجذر، الوزن) في الإصدارين: رسم «ٱ»، حدثٌ جديد، حدثٌ مسحوب يُقرأ حياً، تصحيح رسم الفعل، بناءٌ جديد؛ وما لا يتّصل بتغيّر أحداث وجهه
يُعلَّم بما يتّصل به (فرقٌ تابعٌ لفرقٍ صرفي في الكلمة نفسها) أو UNATTRIBUTED. ولا يُحكم على فرقٍ بالصواب لموافقته المصدر الحديث.
المخرج: <OUT_PREFIX>.jsonl.gz (الفروق كلها) و<OUT_PREFIX>.json (الملخّص).
"""
import collections, csv, gzip, json, os, pickle, re, sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sarf.root import hfn_class                       # تصنيف الصيغة كما يصنّفه المحلّل نفسه (قراءة فقط)


def events(path):
    out = collections.defaultdict(dict)
    for e in csv.DictReader(open(os.path.join(path, 'events.csv'), encoding='utf-8')):
        out[(e['root_K'], hfn_class(e['form']))][e['event_id']] = e
    return out


def reasons_for(key, E0, E1):
    a, b = E0.get(key, {}), E1.get(key, {})
    rs = set()
    for k in set(b) - set(a):
        rs.add('NEW_EVENT_TAFALLALA' if b[k]['form'].startswith('تَفَعْلَلَ') else 'NEW_EVENT')
        if b[k].get('event_review_v36', '').startswith('WITHDRAWN'):
            rs.add('WITHDRAWN_EVENT_READ_AS_LIVE')
    for k in set(a) & set(b):
        if a[k]['verb'] != b[k]['verb']:
            rs.add('WASL_SPELLING' if a[k]['verb'].replace('ٱ', 'ا') == b[k]['verb'].replace('ٱ', 'ا') else 'VERB_SPELLING_CORRECTED')
        for f in ('transitivity', 'masdar', 'form'):
            if a[k].get(f) != b[k].get(f):
                rs.add(f'EVENT_FIELD_CHANGED:{f}')
        if b[k].get('event_review_v36', '').startswith('WITHDRAWN'):
            rs.add('WITHDRAWN_EVENT_READ_AS_LIVE')
    for k in set(a) - set(b):
        rs.add('EVENT_REMOVED')
    return rs


def main():
    A0, A1, H0, H1, OUT = sys.argv[1:6]
    S0, S1 = pickle.load(gzip.open(A0)), pickle.load(gzip.open(A1))
    E0, E1 = events(H0), events(H1)
    leaves = []

    def walk(x, y, p):
        if isinstance(x, dict) and isinstance(y, dict):
            for k in set(x) | set(y):
                if k not in x:
                    leaves.append((p + [k], '<ABSENT>', y[k], 'ADDED'))
                elif k not in y:
                    leaves.append((p + [k], x[k], '<ABSENT>', 'REMOVED'))
                else:
                    walk(x[k], y[k], p + [k])
        elif isinstance(x, list) and isinstance(y, list) and len(x) == len(y):
            for i, (u, w) in enumerate(zip(x, y)):
                walk(u, w, p + [i])
        elif x != y:
            leaves.append((p, x, y, 'CHANGED' if type(x) == type(y) and not isinstance(x, list) else 'SHAPE_CHANGED'))

    for v in S0:
        walk(S0[v], S1.get(v), [v])
    # هوية الوقوع والوجه من مدخل morph في الطرفين
    S = collections.Counter()
    by_word = collections.defaultdict(set)
    rows = []
    for p, x, y, kind in leaves:
        verse = p[0]
        rec = dict(verse=verse, path='/'.join(map(str, p[1:])), kind=kind, base=x, shadow=y)
        wi = slot = None
        face0 = face1 = None
        if len(p) > 3 and p[1] == 'a' and p[2] == 'morph' and isinstance(p[3], int):
            m0 = S0[verse]['a']['morph'][p[3]] if p[3] < len(S0[verse]['a']['morph']) else {}
            m1 = (S1.get(verse) or {}).get('a', {}).get('morph', [])
            m1 = m1[p[3]] if p[3] < len(m1) else {}
            wi, slot = m0.get('word_index', m1.get('word_index')), m0.get('slot', m1.get('slot'))
            face0, face1 = m0.get('analysis_id'), m1.get('analysis_id')
            keys = {(m.get('root'), m.get('form_class')) for m in (m0, m1) if m.get('root')}
            rs = set().union(*[reasons_for(k, E0, E1) for k in keys]) if keys else set()
            rec['face_keys'] = sorted(map(list, keys))
            rec['reasons'] = sorted(rs) or ['NO_EVENT_CHANGE_FOR_FACE_KEY (أثرٌ من فهرسٍ آخر: لمّات الأسماء أو الكلمة كلها)']
            by_word[(verse, wi)].add('MORPH')
        else:
            m = re.search(r'\((\d+), (\d+)\)', rec['path']) or re.search(r'\.w(\d+)', rec['path'])
            wi = int(m.group(1)) if m else None
            if wi is None and len(p) > 3 and p[1] == 'a' and isinstance(p[3], int):
                it = S0[verse]['a'][p[2]][p[3]] if isinstance(S0[verse]['a'].get(p[2]), list) and p[3] < len(S0[verse]['a'][p[2]]) else {}
                wi = it.get('word_index') if isinstance(it, dict) else None
        rec.update(word_index=wi, slot=slot, analysis_id_base=face0, analysis_id_shadow=face1)
        rows.append(rec)
    for r in rows:
        if 'reasons' not in r:
            vm = any(k[0] == r['verse'] for k in by_word)
            r['reasons'] = (['DOWNSTREAM_OF_MORPH_CHANGE_IN_SAME_WORD'] if (r['verse'], r['word_index']) in by_word else
                            ['VERSE_LEVEL_AGGREGATE (S/trace)'] if r['path'].split('/')[0] in ('S', 'trace') and vm else
                            ['DOWNSTREAM_IN_SAME_VERSE'] if vm else ['UNATTRIBUTED'])
        top = r['path'].split('/')[0]
        S[f"top:{top}"] += 1
        for x in r['reasons']:
            S[f"reason:{x}"] += 1
        S[f"kind:{r['kind']}"] += 1
    with gzip.open(OUT + '.jsonl.gz', 'wt', encoding='utf-8') as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False, default=str) + '\n')
    words = {(r['verse'], r['word_index']) for r in rows if r['word_index'] is not None}
    summ = dict(base=A0, shadow=A1, hfn_base=H0, hfn_shadow=H1, verses=len(S0), verses_changed=len({r['verse'] for r in rows}),
                leaf_differences=len(rows), words_changed=len(words), morph_entries_changed=len({(r['verse'], r['path'].split('/')[2])
                                                                                                for r in rows if r['path'].startswith('a/morph/')}),
                counts=dict(sorted(S.items())), examples=[{k: r[k] for k in ('verse', 'word_index', 'path', 'base', 'shadow', 'reasons')}
                                                          for r in rows if r['path'].startswith('a/morph/')][:60],
                note='الفرق أثرُ تبديل بيانات HFN وحدها (الشيفرة واحدة في الطرفين)؛ ولا يُسمّى فرقٌ صحيحاً لموافقته الإصدار الحديث')
    json.dump(summ, open(OUT + '.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1, default=str)
    print(json.dumps({k: summ[k] for k in ('verses_changed', 'leaf_differences', 'words_changed', 'morph_entries_changed')}, ensure_ascii=False))
    print(json.dumps({k: v for k, v in summ['counts'].items() if k.startswith('reason:')}, ensure_ascii=False))


if __name__ == '__main__':
    main()
