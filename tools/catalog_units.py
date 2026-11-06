#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tools/catalog_units.py — T14-5 (SARF_COMPREHENSIVE_REPAIR_04 §٨): مصالحة وحدات العدّ بين ملفَي الجرد دون تعديل أيٍّ منهما.

- وحدة العدّ: صفٌّ في operators_catalog_split_vocalized.csv بمفتاح (الصيغة، المجموعة) — 100 وحدة.
- ملف المعاني operators_catalog.jsonl: 140 معنى على 98 وحدة بالمفتاح نفسه.
- معرّف الوحدة منفصلٌ عن المجموعة التعليمية وعن الوظيفة (المعنى) وعن الأثر الإعرابي؛ فنقل التصنيف لا يغيّر الهوية.
- المقارنة بالحروف والحركات (لا تجريد)؛ وما اختلف ترتيب محارفه وحده (الشدّة قبل الحركة أو بعدها) يُعرض فرقاً في الترميز.

    python3 tools/catalog_units.py [--json out.json]
"""
import argparse, csv, json, os, sys, unicodedata
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def canon_order(s):
    """ترتيب العلامات المركّبة ترتيباً قانونياً (NFC/NFD لا يحذف شيئاً): فرقٌ في الترميز لا في الحروف والحركات"""
    return unicodedata.normalize('NFD', s)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--json')
    args = ap.parse_args()
    C = list(csv.DictReader(open(os.path.join(ROOT, 'operators_catalog_split_vocalized.csv'), encoding='utf-8-sig')))
    L = [json.loads(l) for l in open(os.path.join(ROOT, 'operators_catalog.jsonl'), encoding='utf-8') if l.strip()]
    units = {}
    for i, r in enumerate(C):
        k = (r['Operator'].strip(), r['Group Number'].strip())
        units.setdefault(k, dict(unit_id=f'U{len(units) + 1:03d}', form=k[0], teaching_group=k[1], group_name=r['Arabic Group Name'].strip(),
                                 csv_rows=[]))['csv_rows'].append(i + 2)
    mk = {}
    for x in L:
        mk.setdefault((x['vocalized_form'], x['group_number']), []).append(x)
    by_canon = {}
    for k in mk:
        by_canon.setdefault((canon_order(k[0]), k[1]), []).append(k)
    out_units, enc_diff, no_meaning = [], [], []
    for k, u in units.items():
        ms = mk.get(k)
        how = 'EXACT' if ms else None
        if not ms:
            alt = by_canon.get((canon_order(k[0]), k[1]))
            if alt:
                ms = [m for a in alt for m in mk[a]]
                how = 'ENCODING_ORDER_ONLY'
                enc_diff.append(dict(unit=u['unit_id'], csv_form=k[0], jsonl_form=alt[0][0], group=k[1]))
        if not ms:
            how = 'VARIANT_OR_MISSING'
        u.update(meaning_match=how, functions=[m['meaning_label'] for m in ms or []],
                 effects=sorted({m['grammatical_effect'] for m in ms or []}))
        if how == 'VARIANT_OR_MISSING':
            no_meaning.append(dict(unit=u['unit_id'], form=k[0], group=k[1]))
        out_units.append(u)
    jsonl_only = sorted(k for k in mk if k not in units and not any(
        canon_order(k[0]) == canon_order(u['form']) and k[1] == u['teaching_group'] for u in out_units))
    idha = [u for u in out_units if u['form'] == 'إِذَا']
    rep = dict(
        counting_key='(Operator, Group Number) في operators_catalog_split_vocalized.csv',
        units=len(units), meanings_jsonl=len(L), jsonl_units=len(mk),
        why_98=('ملف المعاني يحمل 98 وحدةً بالمفتاح نفسه لأن وحداتٍ من الجرد بلا سجلّ معنى فيه، وأخرى صيغتها فيه غير صيغة الجرد '
                '(فرق ترتيب محارف أو علامة إعراب الصيغة المذكورة: أَلْفٌ/أَلْفَ)؛ والجرد المئوي محفوظ، ولم يُعدَّل أيٌّ من الملفين'),
        units_without_exact_meaning=no_meaning, encoding_order_only=enc_diff, jsonl_keys_not_in_inventory=[list(k) for k in jsonl_only],
        conflict='CATALOG_UNIT_KEY_CONFLICT: صيغ الوحدة تختلف بين الملفين؛ وتوحيدها تعديلٌ للجرد ينتظر قرار المالك',
        split_18_82='لم يُعثر في المستودع على نصّ تقسيم 18/82؛ ولم يُمسّ شيءٌ من تقسيم الوحدات (حكم المالك محفوظ كما هو)',
        idha_effect=dict(units=[u['unit_id'] for u in idha], recorded=[e for u in idha for e in u['effects']],
                         issue='«لا تجزم في الغالب» توهم جزماً في بعض الفصيح بلا سندٍ ولا استثناءٍ محدَّد',
                         proposal='مقترحٌ ينتظر المالك: «لا تجزم في النطاق الفصيح المعتمد؛ والجزم بها في الشعر ضرورةٌ خارج النطاق '
                                  '(ابن هشام، مغني اللبيب)»؛ والتنفيذ يتّبعه فعلاً: NO_JAZM في sarf/segment.py'),
        unit_table=out_units)
    if args.json:
        json.dump(rep, open(args.json, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f"وحدات العدّ {rep['units']}، ومعاني jsonl {rep['meanings_jsonl']} على {rep['jsonl_units']} وحدة؛ "
          f"بلا معنى مطابق {len(no_meaning)}، وفرق ترتيبٍ وحده {len(enc_diff)}")
    for x in no_meaning:
        print('  بلا سجل معنى بالصيغة نفسها:', x['unit'], x['form'], 'مج', x['group'])
    return rep


if __name__ == '__main__':
    main()
