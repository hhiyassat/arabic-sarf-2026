"""مساعد: تحليل نصٍّ مشكول حرٍّ (شاهد) بالمسار نفسه، وإرجاع أطر الفعل وسجلات الفاعل والمحاور."""
import os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def analyze_text(text, ref='T:1'):
    from sarf.catalog import Catalog
    from sarf.analyze import analyze
    from sarf.algebra import Trace, sentence_geo, linguistic_layer, closure_certificate
    from sarf.features import unit_features
    from sarf import relations as RL, quran_source
    CAT = Catalog([os.path.join(ROOT, 'operators_catalog.jsonl'), os.path.join(ROOT, 'operators_catalog_split_vocalized.csv')])
    s, v = (int(x) for x in ref.split(':')) if ref[0].isdigit() else (999, 1)
    a = analyze(CAT, text, quran_source.uthmani_mode())
    S_, U = sentence_geo(a, f'Q{s}:{v}', Trace())
    C, Rl = [], []
    LT, _, _ = linguistic_layer([(s, v, a, U, S_)], Trace(), 'mp', cond_out=C, rel_out=Rl)
    o = RL.verse_relations(a, U, unit_features(a, U), f'{s}:{v}', legacy_cond=C, legacy_rel=Rl)
    Js = [J for SP in LT for D in SP.A + SP.O.get('pending', []) for J in D.A + D.O.get('pending', [])]
    o['certs'] = [closure_certificate(J, o['records']) for J in Js]
    o['Js'] = Js
    return o
