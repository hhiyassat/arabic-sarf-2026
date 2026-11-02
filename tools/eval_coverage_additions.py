#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tools/eval_coverage_additions.py — قياس ما أُضيف من سجل التغطية على المصحف كله، بلا مدوّنة QAC:

  features_ext     عدد كل سمةٍ مضافة (sarf.features_ext) بحالتها وقيمتها، مع أمثلة بمواضعها
  reconstruction   صحة إعادة التركيب (S08.04): ضمّ نصوص الخانات بترتيبها يعيد الكلمة المطبَّعة حرفاً وحركة؛
                   والشدة المفكوكة على حدّ خانتين تُعاد شدّةً (merge_split_shadda) وتُعدّ مستقلة

    python3 tools/eval_coverage_additions.py [--jobs N] [--out reports/coverage_additions_eval.json]
"""
import argparse, collections, json, os, sys, multiprocessing as mp

H = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, H)
from sarf.catalog import Catalog
from sarf.analyze import analyze
from sarf.algebra import Trace, sentence_geo, merge_split_shadda
from sarf.features import unit_features
from sarf.features_ext import extra_features  # noqa: F401  (يضمن وجود الوحدة)

NEW = ('root_class', 'root_arity', 'conjugability', 'transformations', 'definiteness_kind', 'final_form', 'case_marking',
       'diptote', 'derivation_candidates', 'lemma', 'elative', 'enclitic_case', 'construction', 'stem_root_candidates', 'nisba', 'diminutive')
CAT = Catalog([os.path.join(H, 'operators_catalog.jsonl'), os.path.join(H, 'operators_catalog_split_vocalized.csv')])


def verses():
    for l in open(os.path.join(H, 'data', 'quran_hafs.tsv'), encoding='utf-8'):
        p = l.rstrip('\n').split('\t')
        if len(p) >= 3 and p[0].isdigit():
            yield int(p[0]), int(p[1]), p[2]


def val(v):
    if isinstance(v, dict):
        return v.get('type', '') + ('/' + '+'.join(v['kinds']) if v.get('kinds') else '')
    if isinstance(v, list):
        return 'تحويل' if v else 'بلا تحويل'
    return str(v)


def one(t):
    s, v, text = t
    a = analyze(CAT, text)
    _, units = sentence_geo(a, f'Q{s}:{v}', Trace())
    F = unit_features(a, units)
    feats, ex, rec = collections.Counter(), {}, collections.Counter()
    bad = []
    for (wi, ui), r in F.items():
        for k in NEW:
            if k in r:
                key = f"{k}|{r[k]['st']}|{val(r[k]['v'])}"
                feats[key] += 1
                ex.setdefault(key, f'{s}:{v}:{wi + 1} {units[(wi, ui)].O.get("text")}')
    for seg in a['segments']:
        rec['words'] += 1
        parts = [sl['text'] for sl in seg['slots']]
        joined = ''.join(parts)
        merged = parts[:1]
        split = False
        for x in parts[1:]:
            m = merge_split_shadda(merged[-1], x)
            if m is not None:
                merged[-1], split = m, True
            else:
                merged.append(x)
        if joined == seg['word']:
            rec['equal'] += 1
        elif split and ''.join(merged) == seg['word']:
            rec['equal_after_shadda_merge'] += 1          # المشدَّد خليتان على حدّ خانتين (كُنْ + نَ ← كُنَّ): تمثيلٌ مقصود
        else:
            rec['differ'] += 1
            bad.append(f"{s}:{v}:{seg['word_index'] + 1} {seg['word']} ← {joined}")
    return feats, ex, rec, bad


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--jobs', type=int, default=os.cpu_count() or 1)
    ap.add_argument('--out', default=os.path.join(H, 'reports', 'coverage_additions_eval.json'))
    a = ap.parse_args()
    with mp.get_context('fork').Pool(a.jobs) as P:
        R = P.map(one, list(verses()), chunksize=20)
    feats, ex, rec, bad = collections.Counter(), {}, collections.Counter(), []
    for f, e, r, b in R:
        feats.update(f); rec.update(r); bad += b
        for k, x in e.items():
            ex.setdefault(k, x)
    by_feat = collections.defaultdict(dict)
    for key, n in sorted(feats.items()):
        k, st, v = key.split('|', 2)
        by_feat[k].setdefault(st, {})[v] = n
    out = dict(range='1-114', features_ext={k: dict(counts=by_feat[k], total=sum(sum(x.values()) for x in by_feat[k].values()))
                                            for k in NEW if k in by_feat},
               examples={k: ex[k] for k in sorted(ex)},
               reconstruction=dict(rec, examples_differ=bad[:40]))
    json.dump(out, open(a.out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(json.dumps({k: v['total'] for k, v in out['features_ext'].items()}, ensure_ascii=False))
    print('reconstruction', dict(rec))
