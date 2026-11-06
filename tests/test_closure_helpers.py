"""مساعدٌ للاختبارات: سجلات آيةٍ واحدة ومحاورها بصيغة JSON ثابتة (للمقارنة قبل حدثٍ وبعده)."""
import json, os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def verse_records(s, v):
    from sarf.catalog import Catalog
    from sarf.analyze import analyze
    from sarf.algebra import Trace, sentence_geo, linguistic_layer
    from sarf.features import unit_features
    from sarf import relations as RL, quran_source
    CAT = Catalog([os.path.join(ROOT, 'operators_catalog.jsonl'), os.path.join(ROOT, 'operators_catalog_split_vocalized.csv')])
    text = next(t for s_, v_, t in quran_source.rows() if (s_, v_) == (s, v))
    a = analyze(CAT, text, quran_source.uthmani_mode())
    S_, U = sentence_geo(a, f'Q{s}:{v}', Trace())
    C, Rl = [], []
    linguistic_layer([(s, v, a, U, S_)], Trace(), 'h', cond_out=C, rel_out=Rl)
    o = RL.verse_relations(a, U, unit_features(a, U), f'{s}:{v}', legacy_cond=C, legacy_rel=Rl)
    return json.dumps(dict(records=o['records'], axes=o['axes']), ensure_ascii=False, sort_keys=True, default=str)
