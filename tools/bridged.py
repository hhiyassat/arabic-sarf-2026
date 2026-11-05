# -*- coding: utf-8 -*-
"""
tools/bridged.py — علاقات الآيات كما تبنيها صفحة التتبّع: الطبقة القديمة (linguistic_layer) لكل سورة، ثم verse_relations
بجسرَيها (legacy_cond وlegacy_rel). تستعمله أدوات القياس كلها، فلا تقيس أداةٌ مساراً غير مسار الصفحة.
"""
import itertools


def groups(rows):
    """آيات المصدر مجمّعةً بالسورة (الطبقة القديمة تعمل على السورة)"""
    return [list(g) for _, g in itertools.groupby(rows, key=lambda x: x[0])]


def surah_outputs(items, cat, mode):
    """→ [(s, v, a, U, F, out)] لكل آيةٍ في السورة، بالجسرين"""
    from sarf.analyze import analyze
    from sarf.algebra import Trace, sentence_geo, linguistic_layer
    from sarf.features import unit_features
    from sarf.relations import verse_relations
    its, per = [], []
    for s, v, text in items:
        a = analyze(cat, text, mode)
        S_, U = sentence_geo(a, f'Q{s}:{v}', Trace())
        its.append((s, v, a, U, S_))
        per.append((s, v, a, U, unit_features(a, U)))
    C, Rl = [], []
    linguistic_layer(its, Trace(), 'bridged', cond_out=C, rel_out=Rl)
    return [(s, v, a, U, F, verse_relations(a, U, F, f'{s}:{v}', legacy_cond=C, legacy_rel=Rl)) for s, v, a, U, F in per]
