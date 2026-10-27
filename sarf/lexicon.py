# -*- coding: utf-8 -*-
"""
sarf.lexicon — معجم المبنيات (lexicon/mabniyat_lexicon.jsonl) للبحث عن الكلمة المبنية بصورتها المشكولة.
الفهرس (sarf.catalog) للعوامل، وهذا للمبنيات: العامل يؤثّر فيما بعده، والمبني صورة ثابتة.
"""
import os, json

from .chars import plain, DAGGER_ALIF, FATHATAN, DAMMATAN, KASRATAN
from .match import match_letters, vocal_compatible

TANWIN = {FATHATAN, DAMMATAN, KASRATAN}

DEFAULT_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                            'lexicon', 'mabniyat_lexicon.jsonl')


class MabniLexicon:
    def __init__(self, path=DEFAULT_PATH):
        self.entries = []
        self.by_plain = {}
        if not os.path.exists(path):
            return
        for line in open(path, encoding='utf-8'):
            if not line.strip():
                continue
            e = json.loads(line)
            if ' ' in e['form']:
                continue                          # المداخل متعددة الكلمات خارج البحث بالكلمة
            self.entries.append(e)
            for exp in (True, False):
                toks = match_letters(e['form'], exp)
                self.by_plain.setdefault(plain(toks, True), []).append((e, toks))

    def lookup(self, word):
        """→ مداخل المعجم التي تطابق الكلمة حروفاً وتشكيلاً (الخنجرية تُجرَّب ألفاً ثم محذوفة)"""
        hits, seen = [], set()
        for exp in ((True, False) if DAGGER_ALIF in word else (True,)):
            toks = match_letters(word, exp)
            for e, etoks in self.by_plain.get(plain(toks, True), []):
                ok, n = vocal_compatible(toks, etoks)
                if (toks[-1][1] & TANWIN) != (etoks[-1][1] & TANWIN):
                    ok = False                    # التنوين في آخر الكلمة علامة إعراب (أَجَلٍ ≠ أَجَلْ)
                if ok and n and e['entry_id'] not in seen:
                    seen.add(e['entry_id'])
                    hits.append(e)
        return hits
