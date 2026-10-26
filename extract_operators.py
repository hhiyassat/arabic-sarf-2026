#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
extract_operators.py — استخراج العوامل من الآية بحسب الفهرس ثم تطبيق cv_syllabifier عليها
    UthmaniNorm ∘ Match(catalog) ∘ Syllabify(verse) ∘ Align(operator → syllables)

الاستعمال:
    python3 extract_operators.py "وَٱمْسَحُوا۟ بِرُءُوسِكُمْ"
    python3 extract_operators.py -f verse.txt [--catalog operators_catalog.jsonl operators_catalog_split_vocalized.csv] [--json]

المطابقة (بالترتيب، لكل كلمة):
  1. عامل متعدد الكلمات (مَا زَالَ …)
  2. الكلمة كاملة = عامل        (مِنْ، إِذَا، لَيْسَ …)
  3. عامل + ضمير/لاحقة مغلقة     (عَلَيْهِمْ، لَعَلَّكُمْ، كَانُوا …)
  4. سابقة حرفية + بقية الكلمة   (بِـ، لِـ، كَـ، وَـ، تَـ)
  يُسبَق 2–4 بتقشير وَ/فَ العاطفتين إن وُجدتا.
  عند وجود التشكيل تُستبعد الصيغ المخالفة في الحركة أو الشدة (مِنْ ≠ مَنْ، إِذَا ≠ إِذًا، أَنْ ≠ أَنَّ).
"""
import sys, os, re, csv, json, argparse, unicodedata
from collections import OrderedDict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cv_syllabifier as cv
from cv_syllabifier import (FATHA, DAMMA, KASRA, SUKUN, SHADDA,
                            FATHATAN, DAMMATAN, KASRATAN, DAGGER_ALIF, MARKS, TATWEEL)

VOWELS = {FATHA, DAMMA, KASRA, FATHATAN, DAMMATAN, KASRATAN}

# ---------- Stage 0: Uthmani → إملائي يفهمه المقطِّع ----------
UTHMANI_MAP = {
    'ٱ': 'ا',          # ألف الوصل
    'ۡ': SUKUN,        # السكون العثماني (رأس الخاء)
    'ۥ': 'و',          # واو الصلة الصغيرة
    'ۦ': 'ي',          # ياء الصلة الصغيرة
    'ۧ': 'ي',          # الياء الصغيرة (إِبْرَٰهِـۧمَ)
}
UTHMANI_DROP = set(chr(c) for c in range(0x06D6, 0x06EE)) - set(UTHMANI_MAP) | {'۟', 'ـ'}
MADD_AFTER_FATHA = re.compile('(\u064E\u0651?|\u0651\u064E)\u0622')

MADD_LETTERS = set('اويىآ')
UTHMANI_SIGNS = {'ٱ'} | set(chr(c) for c in range(0x06D6, 0x06EE))

def uthmani_normalize(text, implicit_sukun=None):
    """
    implicit_sukun: في الرسم العثماني الحرف العاري (غير المدّي) ساكن مُخفى/مدغم (تَدَايَنتُم).
    None ⇒ يُفعَّل تلقائياً إن ظهرت علامات عثمانية في النص.
    """
    text = unicodedata.normalize('NFC', text)
    # «آ» بعد فتحة = ألف مدّ عليها علامة المدّ العثمانية لا همزة: إِنَّمَآ، جَآءَ (وتبقى همزةً بعد ساكن: ٱلْقُرْآنُ)
    text = MADD_AFTER_FATHA.sub(r'\1ا', text)
    if implicit_sukun is None:
        implicit_sukun = any(ch in UTHMANI_SIGNS for ch in text)
    out = []
    for ch in text:
        if ch in UTHMANI_MAP:
            out.append(UTHMANI_MAP[ch])
        elif ch in UTHMANI_DROP:          # ومنها ۠: تُحذف العلامة وتبقى الألف مدّاً كما رُسمت
            continue
        else:
            out.append(ch)
    text = ' '.join(''.join(out).split())
    if not implicit_sukun:
        return text
    words = []
    for w in text.split():
        toks = letters(w)
        rebuilt = []
        for i, (L, mk) in enumerate(toks):
            mk = set(mk)
            if not mk and L not in MADD_LETTERS and L != 'ة' and 'ء' <= L <= 'ي':
                prev_al = i > 0 and toks[i - 1][0] == 'ا'
                if not (L == 'ل' and prev_al):          # لام التعريف تبقى للمقطِّع
                    mk.add(SUKUN)
            rebuilt.append(L + ''.join(sorted(mk)))
        words.append(''.join(rebuilt))
    return ' '.join(words)

# ---------- أدوات الحروف ----------
def letters(word):
    """→ [(letter, frozenset(marks))] مع حذف التطويل"""
    out = []
    for ch in word:
        if ch == TATWEEL:
            continue
        if ch in MARKS:
            if out:
                out[-1][1].add(ch)
        else:
            out.append([ch, set()])
    return [(l, frozenset(m)) for l, m in out]

LOOSE = str.maketrans({'أ': 'ا', 'إ': 'ا', 'آ': 'ا', 'ٱ': 'ا', 'ى': 'ي', 'ة': 'ه'})

def plain(toks, loose=False):
    s = ''.join(l for l, _ in toks)
    return s.translate(LOOSE) if loose else s

def vowel(marks):
    for m in marks:
        if m in VOWELS:
            return m
    return None

def vocal_compatible(word_toks, op_toks, skip_first_shadda=True):
    """
    هل تشكيل الكلمة لا يناقض تشكيل العامل؟ (الحروف متساوية العدد)
    - حركتان مختلفتان على الحرف نفسه ⇒ تعارض
    - شدة في أحدهما دون الآخر (والآخر مشكول) ⇒ تعارض، إلا شدة الإدغام على الحرف الأول (مِّنْ)
    - غير المشكول لا يناقض شيئاً
    → (compatible, n_checked_letters)
    """
    checked = 0
    for idx, ((_, wm), (_, om)) in enumerate(zip(word_toks, op_toks)):
        if not wm or not om:
            continue
        wv, ov = vowel(wm), vowel(om)
        if wv and ov:
            checked += 1
            if wv != ov:
                return False, checked
        if (SHADDA in wm) != (SHADDA in om):
            if not (idx == 0 and skip_first_shadda):
                # السكون مقابل الشدة/الحركة تعارض صريح؛ غياب الشدة مع حركة متفقة يُتسامح فيه للكلمة غير التامة التشكيل
                if (SHADDA in om and SUKUN in wm) or (SHADDA in wm and SUKUN in om) or (wv and ov):
                    return False, checked
        if (SUKUN in wm) and ov and SHADDA not in om:
            # حرف ساكن في الكلمة متحرك في العامل — يُتسامح في آخر الكلمة (سكون الوقف)
            if idx != len(op_toks) - 1:
                return False, checked
    return True, checked

# ---------- الفهرس ----------
PRON_SUFFIXES = ['هُو', 'هِي', 'هُمَا', 'كُمَا', 'هُمْ', 'هُنَّ', 'كُمْ', 'كُنَّ', 'هَا', 'نَا', 'نِي', 'هُ', 'هِ', 'كَ', 'كِ', 'ي', 'هِمْ', 'هِمَا', 'هِنَّ']
VERB_SUFFIXES = ['ُوا', 'ُوا۟', 'َتْ', 'َا', 'ُونَ', 'ْتُمْ', 'ْتُ', 'ْتَ', 'ْنَا', 'ْنَ', 'ْتِ']
# العوامل التي تقبل لاحقة: (المجموعة) → قائمة اللواحق
SUFFIX_GROUPS = {'1': 'pron', '2': 'pron', '10': 'both', '11': 'both', '13': 'pron'}
# ى/ا الأخيرة تنقلب ياءً قبل الضمير: عَلَى → عَلَيْهِمْ، إِلَى → إِلَيْهِ
ALIF_TO_YA = {'على', 'إلى', 'لدى', 'حتى'}

# السوابق الحرفية: الحرف → الحركات المقبولة
PROCLITICS = {
    'ب': {KASRA},
    'ل': {KASRA, FATHA, SUKUN},   # لِ الجر/الأمر، لَ التوكيد، لْ الأمر بعد وَ/فَ
    'ك': {FATHA},
    'و': {FATHA},
    'ت': {FATHA},
}
CONJ = {'و', 'ف'}   # عاطفتان تُقشَّران قبل البحث

# ما الكافة بعد إنّ وأخواتها: تكفّها عن العمل (إلا ليت فيجوز فيها الوجهان)
KAFFA_GROUPS = {'2'}
KAFFA_EFFECT = {
    'إن': 'مكفوفة عن العمل؛ أداة حصر وقصر — ما بعدها مبتدأ وخبر أو جملة فعلية',
    'أن': 'مكفوفة عن العمل؛ تفيد الحصر — ما بعدها مبتدأ وخبر أو جملة فعلية',
    'ليت': 'يجوز إعمالها (نصب الاسم ورفع الخبر) وإهمالها',
    None: 'مكفوفة عن العمل — ما بعدها مبتدأ وخبر أو جملة فعلية',
}

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

def _strip_marks(s):
    return ''.join(ch for ch in s if ch not in MARKS)

# ---------- Stage 1: Match ----------
def match_letters(word, expand_dagger=True):
    """للمطابقة فقط: الألف الخنجرية = ألف (يَٰ → يَا) أو تُحذف (لَٰكِنَّ → لَكِنَّ)، والمدّة تُهمَل"""
    out = []
    for L, mk in letters(word):
        if DAGGER_ALIF in mk and L not in ('ى', 'ا') and expand_dagger:
            out.append((L, mk - {DAGGER_ALIF})); out.append(('ا', frozenset()))
        else:
            out.append((L, mk - {DAGGER_ALIF, 'ٓ'}))
    return out

FUSED_GROUPS = {'4'}   # أدوات نداء تُوصَل رسماً بما بعدها: يَٰٓأَيُّهَا

def match_word(cat, word, wi):
    """→ قائمة تطابقات للكلمة wi؛ الخنجرية تُجرَّب ألفاً ثم محذوفة، ويُقدَّم ما وجد عاملاً حرّاً"""
    first = _match_word(cat, word, wi, match_letters(word, True))
    if DAGGER_ALIF not in word or any(not f['method'].startswith('proclitic') for f in first):
        return first
    second = _match_word(cat, word, wi, match_letters(word, False))
    if any(not f['method'].startswith('proclitic') for f in second):
        return second
    return first

def _match_word(cat, word, wi, toks):
    results = []

    def emit(op, span, method, checked, conf, host_rest=None, note=None):
        results.append(dict(word_index=wi, word=word, method=method, operator=op['form'],
                            group=op['group'], operator_class=op['cls'], char_span=span,
                            confidence=conf, vocal_checks=checked, host_rest=host_rest, note=note,
                            meanings=[dict(id=m['operator_id'], label=m['meaning_label'],
                                           prior=m['detection_probabilistic'].get('prior'),
                                           effect=m['grammatical_effect'])
                                      for m in op['meanings']]))

    def conf_of(checked, n_letters):
        if checked == 0:
            return 'low'          # بلا تشكيل: مطابقة رسمية فقط
        return 'high' if checked >= max(1, n_letters - 1) else 'medium'

    def lexical(off, t, tag=None):
        """2/3/3b: عامل حرّ (كلمة كاملة، أو + لاحقة، أو نداء موصول) → هل وُجد؟"""
        if tag is None:
            tag = '' if off == 0 else '+conj'
        hit = False
        # 2. الكلمة كاملة
        for op, n, how in cat.by_plain(t, cat.single):
            if op['plain'] in ALIF_TO_YA and SHADDA in t[-1][1]:
                emit(op, (off, len(toks) - 1), 'operator+suffix' + tag, n, conf_of(n, len(t)),
                     host_rest='ي', note='ياء المتكلم مدغمة في ياء الحرف')
            else:
                emit(op, (off, len(toks)), 'whole_word' + tag, n, conf_of(n, len(t)),
                     note=None if how == 'strict' else 'مطابقة مرنة للهمزات')
            hit = True
        if hit:
            return True
        # 3. عامل + لاحقة
        for op in cat.single:
            mode = SUFFIX_GROUPS.get(op['group'])
            if not mode:
                continue
            otoks = list(op['toks'])
            if op['plain'] in ALIF_TO_YA:
                otoks = otoks[:-1] + [('ي', frozenset({SUKUN}))]
            k = len(otoks)
            if len(t) <= k or plain(t[:k], True) != plain(otoks, True):
                continue
            rest = plain(t[k:])
            sufs = (PRON_SUFFIXES if mode in ('pron', 'both') else []) + \
                   (VERB_SUFFIXES if mode in ('verb', 'both') else [])
            if not any(_strip_marks(s) == rest for s in sufs):
                continue
            ok, n = vocal_compatible(t[:k], otoks)
            if ok:
                emit(op, (off, off + k), 'operator+suffix' + tag, n, conf_of(n, k), host_rest=rest)
                hit = True
        if hit:
            return True
        # 3a. إنّ وأخواتها + ما الكافة (إِنَّمَا، أَنَّمَا، كَأَنَّمَا، لَكِنَّمَا، لَيْتَمَا، لَعَلَّمَا)
        for op in cat.single:
            if op['group'] not in KAFFA_GROUPS:
                continue
            k = len(op['toks'])
            if len(t) != k + 2 or plain(t[:k], True) != plain(op['toks'], True) or plain(t[k:]) != 'ما':
                continue
            ok, n = vocal_compatible(t[:k], op['toks'])
            if not ok or vowel(t[k][1]) not in (FATHA, None):
                continue
            emit(op, (off, off + k), 'operator+kaffa' + tag, n, conf_of(n, k), host_rest='ما',
                 note='مكفوفة بـ«ما» الكافة: تدخل على الجملتين الاسمية والفعلية')
            effect = KAFFA_EFFECT.get(op['plain'], KAFFA_EFFECT[None])
            results[-1]['kaffa'] = 'مَا'
            for m in results[-1]['meanings']:
                m['effect'] = effect
            hit = True
        if hit:
            return True
        # 3b. أداة نداء موصولة رسماً (يَا + أَيُّهَا)
        for op in cat.single:
            if op['group'] not in FUSED_GROUPS:
                continue
            k = len(op['toks'])
            if len(t) > k + 1 and plain(t[:k], True) == plain(op['toks'], True) and t[k][0] in ('أ', 'ء'):
                ok, n = vocal_compatible(t[:k], op['toks'])
                if ok:
                    emit(op, (off, off + k), 'fused_prefix' + tag, n, conf_of(n, k), host_rest=plain(t[k:]))
                    hit = True
        return hit

    def proclitic(off, t, lexical_rest=False):
        """4. سابقة حرفية في الموضع off"""
        if len(t) < 2 or t[0][0] not in PROCLITICS:
            return False
        L, mk = t[0]
        v = vowel(mk) or (SUKUN if SUKUN in mk else None)
        if v is not None and v not in PROCLITICS[L]:
            return False
        rest = plain(t[1:], True)
        if L == 'ت' and not rest.startswith('الله'):
            return False                          # تاء القسم مع لفظ الجلالة فقط
        if L == 'و' and off == 1:
            return False
        if t[1][0] == 'ا' and len(t) > 2 and t[2][0] != 'ل' and SUKUN not in t[2][1] and vowel(t[2][1]):
            return False                          # كَاتِب: ألف مدّ بعد الحرف ⇒ الحرف من الأصل (لا تُمدّ حركة السابقة)
        strong = lexical_rest or rest.startswith('ال') or (L == 'ل' and v == SUKUN) or \
                 any(_strip_marks(s) == rest for s in PRON_SUFFIXES)
        hit = False
        for op in cat.clitic:
            if op['plain'] != L:
                continue
            # لام الأمر الساكنة لا تكون جارّة؛ لام مفتوحة = التوكيد فقط
            if L == 'ل' and v == SUKUN and op['group'] != '6':
                continue
            if L == 'ل' and lexical_rest and op['group'] == '6':
                continue                          # لام الأمر لا تدخل إلا على مضارع، لا على أداة (لِأَنَّ، لِمَا)
            if L == 'ل' and v == FATHA:
                op = dict(op, meanings=[m for m in op['meanings'] if 'التوكيد' in m['meaning_label']])
                if not op['meanings']:
                    continue
            conf = 'low' if v is None else ('high' if strong else 'medium')
            if L == 'و':
                note = 'قد تكون واو العطف (غير مفهرسة)'
            elif not strong and v is not None:
                note = 'قد يكون الحرف من أصل الكلمة'
            else:
                note = None
            emit(op, (off, off + 1), 'proclitic' + ('' if off == 0 else '+conj'),
                 1 if v else 0, conf, host_rest=plain(t[1:]), note=note)
            hit = True
        return hit

    if lexical(0, toks):
        return results
    conj = len(toks) > 2 and toks[0][0] in CONJ and vowel(toks[0][1]) in (FATHA, None)
    if conj and lexical(1, toks[1:]):
        proclitic(0, toks, lexical_rest=True)     # وَ نفسها مفهرسة (قسم/معية/رُبّ)
        return results
    # عامل حرّ بعد حرف جر متصل: بِأَنَّهُمْ، لِأَنَّ، كَأَنْ …
    inner = len(toks) > 2 and toks[0][0] in ('ب', 'ل', 'ك') and lexical(1, toks[1:], tag='+proclitic')
    divine = cv.divine_name(word) is not None     # ما بعد السابقة لفظ الجلالة: السابقة حرف يقيناً (لا أمر ولا أصل)
    if not proclitic(0, toks, lexical_rest=inner or divine) and conj:
        proclitic(1, toks[1:], lexical_rest=divine)   # فَلْيَكْتُبْ، فَبِمَا، فَلِلَّهِ
    return results

def match_multi(cat, words):
    res = []
    toks_list = [match_letters(w) for w in words]
    for op in cat.multi:
        parts = [letters(p) for p in op['form'].split()]
        n = len(parts)
        for i in range(len(words) - n + 1):
            ok_all, checked = True, 0
            for j, p in enumerate(parts):
                wt = toks_list[i + j]
                if plain(wt, True) != plain(p, True):
                    ok_all = False; break
                ok, c = vocal_compatible(wt, p)
                if not ok:
                    ok_all = False; break
                checked += c
            if ok_all:
                res.append(dict(word_index=i, word=' '.join(words[i:i + n]), method='multi_word',
                                operator=op['form'], group=op['group'], operator_class=op['cls'],
                                char_span=None, words_span=(i, i + n), confidence='high' if checked else 'low',
                                vocal_checks=checked, host_rest=None, note=None,
                                meanings=[dict(id=m['operator_id'], label=m['meaning_label'],
                                               prior=m['detection_probabilistic'].get('prior'),
                                               effect=m['grammatical_effect']) for m in op['meanings']]))
    return res

def extract(cat, text):
    words = text.split()
    found = match_multi(cat, words)
    covered = set()
    for f in found:
        covered.update(range(*f['words_span']))
    for wi, w in enumerate(words):
        if wi in covered:
            continue
        found += match_word(cat, w, wi)
    found.sort(key=lambda f: (f['word_index'], f['char_span'][0] if f['char_span'] else -1))
    return words, found

# ---------- Stage 2: Syllabify + Align ----------
def syllables_by_word(res):
    by_word = {}
    for rend, pat, verdict, ws in res['rows']:
        key = ws[0] if ws else -1
        by_word.setdefault(key, []).append(dict(syl=rend, cv=pat, verdict=verdict))
    return by_word

def isolated_cv(form):
    """تقطيع العامل منفرداً كما كُتب — لمعرفة بنيته المقطعية الذاتية"""
    r = cv.run(form)
    return [dict(syl=rend, cv=pat) for rend, pat, _, _ in r['rows']]

def align(found, by_word, words):
    for f in found:
        if f['method'] == 'multi_word':
            a, b = f['words_span']
            f['syllables'] = [s for w in range(a, b) for s in by_word.get(w, [])]
            continue
        sy = by_word.get(f['word_index'], [])
        off = f['char_span'][0]
        # بعد عاطفة متحركة (وَ/فَ) يبدأ العامل بالمقطع الثاني، إلا إن كان ساكناً فيُغلق مقطع العاطفة (فَلْ)
        idx = 0
        if off == 1:
            op_marks = match_letters(words[f['word_index']])[1][1]
            idx = 0 if SUKUN in op_marks else 1
        if f['method'].startswith('proclitic'):
            f['syllables'] = sy[idx:idx + 1]       # السابقة = مقدمة مقطع واحد من الكلمة المضيفة
        elif f['method'].startswith('fused_prefix'):
            f['syllables'] = sy[idx:idx + len(isolated_cv(f['operator']))]
        else:
            # كلمة كاملة، أو عامل + لاحقة (تُعرض مقاطع العامل ولاحقته معاً)
            f['syllables'] = sy[idx:]
        f['cv'] = ' '.join(s['cv'] for s in f['syllables'])
        f['isolated'] = isolated_cv(f['operator'])
    for f in found:
        f.setdefault('cv', ' '.join(s['cv'] for s in f['syllables']))
        f.setdefault('isolated', isolated_cv(f['operator']))
    return found

def analyze(cat, verse, uthmani='auto'):
    """النص كما هو: التقطيع على النص المطبَّع نفسه، كل كلمة مستقلة، بلا وصل ولا وقف"""
    isk = {'auto': None, 'on': True, 'off': False}[uthmani]   # auto←None (تلقائي) / on←True / off←False
    text = uthmani_normalize(verse, implicit_sukun=isk)
    words, found = extract(cat, text)
    res = cv.run(text)
    found = align(found, syllables_by_word(res), words)
    return dict(verse=verse, normalized=text, syllabified_text=text,
                words=words, operators=found, syll=res)

# ---------- report ----------
def text_report(a):
    out = [f"الآية:    {a['verse']}", f"المُطبَّع: {a['normalized']}"]
    out.append('')
    out.append(f"العوامل المستخرجة: {len(a['operators'])}")
    out.append('-' * 80)
    for f in a['operators']:
        top = f['meanings'][0]
        out.append(f"[{f['word_index']}] {f['word']}  ⟵  {f['operator']}  (مج {f['group']}: {f['operator_class']})")
        out.append(f"     طريقة={f['method']}  ثقة={f['confidence']}"
                   + (f"  بقية={f['host_rest']}" if f.get('host_rest') else '')
                   + (f"  ملاحظة: {f['note']}" if f.get('note') else ''))
        out.append(f"     المقاطع في السياق: {' . '.join(s['syl'] for s in f['syllables'])}   [{f['cv']}]")
        out.append(f"     العامل منفرداً:    {' . '.join(s['syl'] for s in f['isolated'])}   "
                   f"[{' '.join(s['cv'] for s in f['isolated'])}]")
        out.append(f"     المعاني المرشحة:  " + ' | '.join(
            f"{m['label']} ({m['prior'] if m['prior'] is not None else '—'})" for m in f['meanings']))
        out.append(f"     العمل: {top['effect']}")
        out.append('')
    out.append('=' * 80)
    out.append(cv.report(a['syll']))
    out.append('')
    out.append(cv.word_view(a['syll']))
    return '\n'.join(out)

def to_json(a):
    d = {k: v for k, v in a.items() if k != 'syll'}
    r = a['syll']
    d['syllable_counts'] = dict(r['counts'])
    d['cv_line'] = r['cv_line']
    d['events'] = dict(r['events'])
    return d

if __name__ == '__main__':
    here = os.path.dirname(os.path.abspath(__file__))
    ap = argparse.ArgumentParser(description='استخراج العوامل من الآية + التقطيع المقطعي')
    ap.add_argument('verse', nargs='*', help='نص الآية (أو استعمل -f)')
    ap.add_argument('-f', '--file', help='ملف يحوي آية في كل سطر')
    ap.add_argument('--catalog', nargs='+',
                    default=[p for p in (os.path.join(here, 'operators_catalog.jsonl'),
                                         os.path.join(here, 'operators_catalog_split_vocalized.csv'))
                             if os.path.exists(p)],
                    help='ملف أو أكثر (.jsonl/.csv)؛ الأول أساس وما بعده يضيف العوامل الغائبة فقط')
    ap.add_argument('--uthmani', default='auto', choices=['auto', 'on', 'off'],
                    help='المعاملة العثمانية (السكون الضمني): auto=تلقائي بوجود علامة عثمانية، on=دائماً، off=أبداً')
    ap.add_argument('--json', action='store_true', help='إخراج JSON Lines')
    args = ap.parse_args()

    cat = Catalog(args.catalog)
    if args.file:
        verses = [l.strip() for l in open(args.file, encoding='utf-8') if l.strip()]
    elif args.verse:
        verses = [' '.join(args.verse)]
    else:
        verses = [l.strip() for l in sys.stdin if l.strip()]

    for v in verses:
        a = analyze(cat, v, uthmani=args.uthmani)
        if args.json:
            print(json.dumps(to_json(a), ensure_ascii=False))
        else:
            print(text_report(a))
            print('\n' + '#' * 80 + '\n')
