# -*- coding: utf-8 -*-
"""
sarf.catalog — فهرس العوامل: الوحدة = (الصيغة المشكولة، المجموعة) ← معانيها.
"""
import os, re, csv, json
from collections import OrderedDict

from .chars import letters, plain, LOOSE, strip_marks as _strip_marks
from .match import vocal_compatible

def _csv_rows(path):
    """الفهرس المسطّح (CSV) → صفوف بصيغة JSONL؛ معنى واحد لكل صف وبلا prior"""
    out = []
    for r in csv.DictReader(open(path, encoding='utf-8-sig')):
        form = r['Operator'].strip()
        purpose = r['Purpose/Usage'].strip()
        label = re.sub(r'^للدلالة على ', '', purpose)
        label = re.sub(r'^لل', 'ال', label)            # للتوكيد → التوكيد
        out.append({
            'operator_id': f"{_strip_marks(form)}_{label}".replace(' ', '_'),
            'vocalized_form': form, 'operator_plain': _strip_marks(form),
            'group_number': str(int(r['Group Number'])), 'operator_class': r['Arabic Group Name'].strip(),
            'meaning_label': label, 'catalog_purpose': purpose,
            'grammatical_effect': r['Note'].strip(), 'catalog_example_vocalized': r['Example_Vocalized'].strip(),
            'detection_probabilistic': {}, 'source': os.path.basename(path),
        })
    return out

def _catalog_key(form, group):
    """مفتاح الدمج: الحروف (بلا تشكيل، همزات موحّدة) + المجموعة — يتجاوز اختلاف ترتيب العلامات"""
    return (_strip_marks(form).translate(LOOSE).replace(' ', ''), str(group))

class Catalog:
    def __init__(self, paths):
        """
        paths: ملف أو أكثر (.jsonl أو .csv). الأول هو الأساس؛ ما بعده يضيف العوامل الغائبة فقط
        (مفتاح الحروف + المجموعة)، فلا تُكرَّر معاني عامل موجود ولا يُستبدل تشكيله.
        """
        if isinstance(paths, str):
            paths = [paths]
        self.rows, self.added = [], []
        seen = set()
        for i, path in enumerate(paths):
            rows = _csv_rows(path) if path.endswith('.csv') else \
                   [json.loads(l) for l in open(path, encoding='utf-8') if l.strip()]
            new_keys = set()
            for r in rows:
                key = _catalog_key(r['vocalized_form'], r['group_number'])
                if i > 0 and key in seen:
                    continue
                new_keys.add(key)
                self.rows.append(r)
                if i > 0:
                    self.added.append(r)
            seen |= new_keys
        # عامل = (vocalized_form, group_number) ← كل معانيه
        self.ops = OrderedDict()
        for r in self.rows:
            key = (r['vocalized_form'], r['group_number'])
            if key not in self.ops:
                toks = letters(r['vocalized_form'].replace(' ', ''))
                self.ops[key] = dict(form=r['vocalized_form'], plain=r['operator_plain'],
                                     group=r['group_number'], cls=r['operator_class'],
                                     n_words=len(r['vocalized_form'].split()),
                                     toks=toks, meanings=[])
            self.ops[key]['meanings'].append(r)
        for op in self.ops.values():
            op['meanings'].sort(key=lambda m: -(m['detection_probabilistic'].get('prior') or 0))
        self.single = [o for o in self.ops.values() if o['n_words'] == 1 and len(o['toks']) > 1]
        self.multi = [o for o in self.ops.values() if o['n_words'] > 1]
        self.clitic = [o for o in self.ops.values() if o['n_words'] == 1 and len(o['toks']) == 1]

    def by_plain(self, word_toks, pool):
        """مطابقة الكلمة كاملة؛ صارم بالهمزات أولاً ثم مرن"""
        hits = []
        for loose in (False, True):
            p = plain(word_toks, loose)
            for op in pool:
                if plain(op['toks'], loose) != p:
                    continue
                ok, n = vocal_compatible(word_toks, op['toks'])
                if ok:
                    hits.append((op, n, 'strict' if not loose else 'loose'))
            if hits:
                return hits
        return hits
