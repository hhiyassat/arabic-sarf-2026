#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
mabniyat_lexicon.py — محوِّل data/02_mabniyat إلى معجم الكلمات المغلقة للمحلل.

    python3 mabniyat_lexicon.py [--src data/02_mabniyat] [--out lexicon]

الناتج:
    lexicon/mabniyat_lexicon.jsonl   مداخل مقبولة، كل سطر يطابق schema/lexicon_entry.schema.json
    lexicon/mabniyat_rejected.jsonl  سجلات مرفوضة مع أسبابها (قائمة عمل لتصحيح المصدر)
    lexicon/mabniyat_report.md       ملخّص لكل ملف، ومقارنة بـ operators_catalog

المبادئ:
- لا تخمين: الصيغة غير المشكولة تُرفض ولا يُفترض لها تشكيل (مِنْ ≠ مَنْ).
- التصحيح الإملائي الآلي محصور في ما لا لبس فيه، ويُسجَّل في normalizations.
- كل رفض له سبب صريح، وكل قبول يطابق المخطط.
"""
import sys, os, re, json, argparse, unicodedata
from collections import OrderedDict, defaultdict, Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from schema_check import Validator
import extract_operators as eo
import cv_syllabifier as cv

FATHA, DAMMA, KASRA, SUKUN, SHADDA = 'َ', 'ُ', 'ِ', 'ْ', 'ّ'
TANWIN = {'ً', 'ٌ', 'ٍ'}
VOWELS = {FATHA, DAMMA, KASRA}
MARK_RE = re.compile('[ً-ْٰ]')
LATIN = re.compile('[A-Za-z]')

# ---------- الإملاء ----------
def strip_marks(s):
    return MARK_RE.sub('', s).replace('ـ', '')

def loose(s):
    return strip_marks(s).translate(eo.LOOSE).replace(' ', '')

def normalize_form(raw):
    """→ (form, notes, problems). التصحيح محصور في ما لا لبس فيه؛ ما عداه مشكلة تُرفض بها الصيغة."""
    notes, problems = [], []
    s = unicodedata.normalize('NFC', (raw or '').strip()).replace('ـ', '')
    if not s:
        return s, notes, ['صيغة فارغة']
    if LATIN.search(s):
        problems.append('حروف لاتينية في الصيغة')
    t = re.sub(r'\s+([ً-ْ])', r'\1', s)
    if t != s:
        notes.append('حذف مسافة قبل علامة'); s = t
    t = re.sub(r'([ً-ْ])\1+', r'\1', s)
    if t != s:
        notes.append('دمج علامة مكرّرة على الحرف نفسه'); s = t
    t = re.sub('(ا)' + SUKUN + '|(' + DAMMA + 'و)' + SUKUN + '|(' + KASRA + 'ي)' + SUKUN,
               lambda m: m.group(1) or m.group(2) or m.group(3), s)
    if t != s:
        notes.append('حذف السكون عن حرف المدّ'); s = t
    t = re.sub('^(ا)' + FATHA + '(ل)', r'\1\2', s)
    if t != s:
        notes.append('حذف الفتحة عن همزة الوصل'); s = t
    t = re.sub('^(ا)ل' + FATHA + '(ل(?:' + SHADDA + '|' + FATHA + SHADDA + '))', r'\1ل\2', s)
    if t != s:
        notes.append('حذف الفتحة عن لام التعريف قبل اللام المشددة'); s = t
    # الَّلَذَانِ → اللَّذَانِ: الشدة لِلام الكلمة لا لِلام التعريف
    t = re.sub('^(ا)ل(?:' + SHADDA + FATHA + '?|' + FATHA + SHADDA + ')ل' + FATHA, r'\1لل' + SHADDA + FATHA, s)
    if t != s:
        notes.append('نقل الشدة من لام التعريف إلى لام الكلمة'); s = t
    s = unicodedata.normalize('NFC', s)
    for tok in eo.letters(s):
        marks = tok[1]
        if SHADDA in marks and SUKUN in marks:
            problems.append(f'شدة وسكون معاً على «{tok[0]}»')
        if len(marks & (VOWELS | TANWIN)) > 1:
            problems.append(f'حركتان على «{tok[0]}»')
    if not MARK_RE.search(s) and 'آ' not in s and not set(strip_marks(s)) <= set('اويى'):
        problems.append('غير مشكولة: لا يُفترض لها تشكيل')   # حروف المدّ وحدها (ا، وا، ي) لا تُشكَّل
    elif MARK_RE.search(s):
        first = eo.letters(s.split()[0])[0]
        if not first[1] and first[0] not in 'اآ':
            problems.append(f'مشكولة جزئياً: الحرف الأول «{first[0]}» بلا حركة')
    return s, notes, problems

def last_mark(form):
    toks = eo.letters(form.split()[-1])
    if not toks:
        return None
    L, m = toks[-1]
    for mk, name in ((DAMMA, 'damma'), (FATHA, 'fatha'), (KASRA, 'kasra'), (SUKUN, 'sukun')):
        if mk in m:
            return name
    if m & TANWIN:
        return 'tanwin'
    if L in 'اىوي' and len(toks) > 1:
        return 'sukun'          # المختوم بحرف مدّ مبني على السكون (أَنَا، هُمَا)
    return None

def stated_status(r):
    """الحالة المصرَّح بها في السجل: من التصحيحات (_status) أو من النسخة المصحَّحة (grammatical_status)"""
    return r.get('_status') or r.get('grammatical_status')

def has_tanwin(form):
    return any(m & TANWIN for _, m in eo.letters(form))

# ---------- الخصائص من النص العربي ----------
def parse_gender(txt):
    t = txt or ''
    if any(k in t for k in ('مشترك', 'للجنسين')) or ('مذكر' in t and 'مؤنث' in t):
        return 'common'
    if 'مؤنث' in t:
        return 'fem'
    if 'مذكر' in t:
        return 'masc'
    return None

def parse_number(txt):
    t = txt or ''
    if 'مثنى' in t:
        return 'dual'
    if 'جمع' in t:
        return 'plural'
    if 'مفرد' in t:
        return 'singular'
    return None

def parse_person(txt):
    t = txt or ''
    for k, p in (('المتكلم', 1), ('المخاطب', 2), ('الغائب', 3)):
        if k in t:
            return p
    return None

def agreement(gender, number):
    a = {}
    if gender in ('masc', 'fem'):
        a['gender'] = gender
    if number:
        a['number'] = number
    return a or None

META_FIELDS = {'id', 'al_bab_althani_id', 'section_id', 'category_id', 'created_at', 'updated_at',
               'edited_by', 'is_deleted', 'editor2', '_added'}   # حقول إدارية لا تصف الكلمة

BUILD = {'ضم': 'damma', 'فتح': 'fatha', 'كسر': 'kasra', 'سكون': 'sukun'}

# ---------- مراجع المقارنة ----------
# جرد الموصولات المرجعي (الخاص والعام وأل وذو وذا، كما في قطر الندى)، بصيغها في المثنى والجمع
REF_RELATIVES = {'الذي', 'التي', 'اللذان', 'اللذين', 'اللتان', 'اللتين', 'الذين', 'الالي', 'اللائي',
                 'اللاتي', 'من', 'ما', 'اي', 'ال', 'ذو', 'ذا'}
# تشكيل الجرد المرجعي (يُقارن بعد حذف حركة الآخر)
REF_RELATIVES_VOCALIZED = {'الَّذِي', 'الَّتِي', 'اللَّذَانِ', 'اللَّذَيْنِ', 'اللَّتَانِ', 'اللَّتَيْنِ', 'الَّذِينَ', 'الْأُلَى',
                 'اللَّائِي', 'اللَّاتِي', 'مَنْ', 'مَا', 'أَيّ', 'أَلْ', 'ذُو', 'ذَا'}

def drop_final_mark(form):
    toks = eo.letters(form)
    if toks:
        toks[-1] = (toks[-1][0], frozenset())
    return ''.join(l + ''.join(sorted(m)) for l, m in toks)
# نموذج الضمائر المنفصلة: (الشخص، العدد، الجنس) → الصيغة المتوقعة
PARADIGM_CELLS = [(1, 'singular', 'common'), (1, 'plural', 'common'), (2, 'singular', 'masc'), (2, 'singular', 'fem'),
                  (2, 'dual', 'common'), (2, 'plural', 'masc'), (2, 'plural', 'fem'), (3, 'singular', 'masc'),
                  (3, 'singular', 'fem'), (3, 'dual', 'common'), (3, 'plural', 'masc'), (3, 'plural', 'fem')]
IYYA_SUFFIXES = {'يَ', 'نَا', 'كَ', 'كِ', 'كُمَا', 'كُمْ', 'كُنَّ', 'هُ', 'هَا', 'هُمَا', 'هُمْ', 'هُنَّ'}
REF_ATTACHED = {'رفع': ['تُ', 'نَا', 'تَ', 'تِ', 'تُمَا', 'تُمْ', 'تُنَّ', 'ا', 'وا', 'نَ', 'ي'],
                'نصب/جر': ['ي', 'نَا', 'كَ', 'كِ', 'كُمَا', 'كُمْ', 'كُنَّ', 'هُ', 'هَا', 'هُمَا', 'هُمْ', 'هُنَّ']}
# صيغ صوتية للضمير نفسه بعد الكسرة أو الياء (بِهِ، عَلَيْهِمْ): مقبولة ولا تُعدّ خانات مستقلة
ATTACHED_VARIANTS = {'هِ', 'هِمَا', 'هِمْ', 'هِنَّ'}
HIDDEN_ALLOWED = {'أنا', 'نحن', 'أنتَ', 'هو', 'هي'}   # لا يستتر إلا هذه (المفرد غير المخاطبة، ونحن)


class Converter:
    def __init__(self, src, catalog):
        self.src = src
        self.cat = catalog
        self.cand = []                       # مداخل مرشحة قبل الدمج
        self.rejected = []
        self.rejected_ids = set()
        self.held = []
        self.corrected_data = {}
        self.fixes = {}
        self.stats = defaultdict(Counter)
        self.notes = defaultdict(list)       # ملاحظات تقرير لكل ملف
        self.validator = Validator(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                'schema', 'lexicon_entry.schema.json'))

    # ----- أدوات -----
    def rows(self, name):
        with open(os.path.join(self.src, name + '.json'), encoding='utf-8') as f:
            d = json.load(f)
        self.stats[name]['in'] += len(d['data'])
        return self.corrected(name, d['data'])

    def corrected(self, name, data):
        """تطبيق data_fixes على سجلات الملف: حذف، تعديل، إضافة، تعليق، وإصلاح البنية"""
        fixes = self.fixes.get(name, [])
        if not fixes:
            return data
        by_id = defaultdict(list)
        for x in fixes:
            if 'id' in x:
                by_id[x['id']].append(x)
        out, section = [], None
        for r in data:
            r = dict(r)
            fx = by_id.get(r['id'], [])
            if any(x.get('delete') for x in fx):
                self.stats[name]['deleted (correction)'] += 1
                continue
            if any(x.get('hold') for x in fx):
                self.held.append({'source': {'file': name, 'id': r['id']}, 'record': r,
                                  'reason': next(x['reason'] for x in fx if x.get('hold'))})
                self.stats[name]['held'] += 1
                continue
            if any(x.get('section_header') for x in fx):
                section = r.get('description')
                self.stats[name]['section headers'] += 1
                continue
            if any(x.get('continuation') for x in fx) and out:
                prev = out[-1]
                prev['example'] = ' | '.join(v for v in (prev.get('example'), r.get('example')) if v and v != 'nan')
                self.stats[name]['merged continuations'] += 1
                continue
            for x in fx:
                if 'set' in x:
                    r.update(x['set'])
                    self.stats[name]['edited (correction)'] += 1
            if section and 'section' not in r and name == 'grammatical_construction_cases':
                r['section'] = section
            out.append(r)
        next_id = 9001
        for x in fixes:
            if 'add' in x:
                out.append(dict(x['add'], id=next_id, _added=x['reason']))
                next_id += 1
                self.stats[name]['added (correction)'] += 1
        self.corrected_data[name] = out
        return out

    def reject(self, file, rid, raw, reasons):
        self.rejected.append({'source': {'file': file, 'id': rid}, 'form_original': raw, 'reasons': reasons})
        key = re.sub(r'«[^»]*»', '«…»', reasons[0]).split(':')[0].strip()
        self.stats[file]['rejected: ' + key] += 1
        self.rejected_ids.add((file, rid))

    def add(self, file, rid, raw, category, pos, *, noun=None, particle=None, pronoun=None, extra=None,
            meanings=(), examples=(), warnings=(), split_forms=False, status_src='file_scope'):
        forms = [p.strip() for p in re.split(r'\s+-\s+|\s*/\s*', raw)] if split_forms else [raw]
        self._added_reason = None if rid < 9000 else next(
            (r.get('_added') for r in self.corrected_data.get(file, []) if r['id'] == rid), None)
        for raw1 in forms:
            form, norm, problems = normalize_form(raw1)
            if problems:
                self.reject(file, rid, raw1, problems)
                continue
            e = OrderedDict(entry_id='', form=form, plain=strip_marks(form), category=category, pos=pos)
            if form != raw1.strip():
                e['form_original'] = raw1.strip()
            for k, v in (('noun', noun), ('particle', particle), ('pronoun', pronoun)):
                if v is not None:
                    e[k] = json.loads(json.dumps(v))
            ex = {k: v for k, v in (extra or {}).items() if v not in (None, '', [])}
            if ex:
                e['extra'] = ex
            e['meanings'] = [m.strip() for m in meanings if m and str(m).strip() and str(m) != 'None']
            e['examples'] = [x.strip() for x in examples if x and str(x).strip() and str(x) != 'None']
            e['sources'] = [{'file': file, 'id': rid}]
            e['normalizations'] = norm
            e['warnings'] = list(warnings)
            e['_status_src'] = status_src
            self.cand.append(e)
        if self._added_reason:
            for e in self.cand[-len(forms):]:
                if e['sources'][0]['id'] == rid and not any(w.startswith('مضاف بتصحيح') for w in e['warnings']):
                    e['warnings'].append('مضاف بتصحيح: ' + self._added_reason)

    def catalog_ids(self, form, groups=None):
        p = loose(form)
        out = []
        for op in self.cat.ops.values():
            if loose(op['form']) == p and (groups is None or op['group'] in groups):
                out += [m['operator_id'] for m in op['meanings']]
        return out

    # ----- الملفات -----
    def pronouns(self):
        f = 'pronouns_classification'
        seen_cells = defaultdict(dict)
        attached_seen = defaultdict(set)
        attached_in_file = defaultdict(set)
        in_file_cells = defaultdict(dict)
        for r in self.rows(f):
            cat = r['category'] or ''
            person, number, gender = parse_person(r['meaning']), parse_number(r['form']), parse_gender(r['form'])
            if 'منفصل' in cat:
                in_file_cells['nom' if 'رفع' in cat else 'acc'][(person, number, gender)] = r['pronoun']
                if strip_marks(r['pronoun']) != strip_marks(r['pronoun_form']):
                    self.reject(f, r['id'], r['pronoun'], [f'تعارض: pronoun «{r["pronoun"]}» ≠ pronoun_form «{r["pronoun_form"]}»'])
                    continue
                form, _, _ = normalize_form(r['pronoun'])
                if form.startswith('إِيَّا'):
                    suf = form[len('إِيَّا'):]
                    if suf not in IYYA_SUFFIXES:
                        self.reject(f, r['id'], r['pronoun'], [f'لاحقة «إِيَّا» ليست ضميراً متصلاً: «{suf}»'])
                        continue
                if person in (2, 3) and number == 'singular' and gender == 'common':
                    self.reject(f, r['id'], r['pronoun'], ['المفرد المخاطب والغائب يفرّق بين المذكر والمؤنث'])
                    continue
                case = 'nom' if 'رفع' in cat else 'acc'
                seen_cells[case][(person, number, gender)] = r['pronoun']
                self.add(f, r['id'], r['pronoun'], 'separate_pronoun', 'noun',
                         noun={'subtype': 'pronoun', 'definiteness': 'definite', 'definite_by': 'pronoun',
                               'inflection': {'status': 'mabni', 'build_mark': last_mark(form)}},
                         extra={'person': person, 'number': number, 'gender': gender, 'case_slot': case},
                         meanings=[cat], examples=[r['example']])
            elif 'متصل' in cat or 'مشترك' in cat:
                raw = r['pronoun_form'] or ''
                slots = ['رفع', 'نصب/جر'] if 'مشترك' in cat else ['رفع' if 'رفع' in cat else 'نصب/جر']
                for sl in slots:
                    attached_in_file[sl].add(normalize_form(raw)[0].lstrip('ـ'))
                if len(raw.split()) > 1:
                    self.reject(f, r['id'], raw, ['صيغ متعددة في سجل واحد بخصائص مشتركة: لا تُنسب الخصائص لكل صيغة دون تخمين'])
                    continue
                if person in (2, 3) and number == 'singular' and gender == 'common':
                    self.reject(f, r['id'], raw, [f'خصائص مستحيلة: «{r["form"]}» والمفرد المخاطب والغائب يفرّق بين المذكر والمؤنث'])
                    continue
                slot = slots[0]
                fns = (['subject', 'object', 'possessive'] if 'مشترك' in cat else ['subject'] if 'رفع' in cat
                       else ['governed_by_particle'] if ('إِنَّ' in r['pronoun'] or 'بِحَرْفِ' in r['pronoun'])
                       else ['object', 'possessive'] if ('نصب' in cat and 'جر' in cat)
                       else ['possessive'] if 'جر' in cat else ['object'] if 'نصب' in cat else [])
                pron = {'person': person, 'number': number}
                if gender:
                    pron['gender'] = gender
                if not person or not number:
                    self.reject(f, r['id'], raw, ['الشخص أو العدد غير مستخرج من الحقول meaning/form'])
                    continue
                form, _, _ = normalize_form(raw)
                if form.lstrip('ـ') not in REF_ATTACHED[slot] and form.lstrip('ـ') not in ATTACHED_VARIANTS:
                    self.reject(f, r['id'], raw, [f'«{form}» ليست من صيغ الضمائر المتصلة ({slot})']); continue
                for sl in slots:
                    attached_seen[sl].add(form.lstrip('ـ'))
                self.add(f, r['id'], raw, 'attached_pronoun', 'noun',
                         noun={'subtype': 'pronoun', 'definiteness': 'definite', 'definite_by': 'pronoun',
                               'inflection': {'status': 'mabni'}},
                         pronoun=pron, extra={'functions': fns, 'case_slot': ' + '.join(slots)},
                         meanings=[r['pronoun']], examples=[r['example']])
        # اكتمال النموذج
        for case, label in (('nom', 'المنفصلة للرفع'), ('acc', 'المنفصلة للنصب')):
            fmt = lambda cells: '، '.join(f'(شخص {p}، {n}، {g})' for p, n, g in cells)
            absent = [c for c in PARADIGM_CELLS if c not in in_file_cells[case]]
            rejected = [c for c in PARADIGM_CELLS if c in in_file_cells[case] and c not in seen_cells[case]]
            if absent:
                self.notes[f].append(f'خانات غائبة عن الملف في الضمائر {label}: ' + fmt(absent))
            if rejected:
                self.notes[f].append(f'خانات في الملف لكن سجلاتها مرفوضة في الضمائر {label}: ' +
                                     '، '.join(f'{fmt([c])} «{in_file_cells[case][c]}»' for c in rejected))
        for slot, ref in REF_ATTACHED.items():
            absent = [x for x in ref if x not in attached_in_file[slot]]
            rejected = [x for x in ref if x in attached_in_file[slot] and x not in attached_seen[slot]]
            if absent:
                self.notes[f].append(f'صيغ متصلة ({slot}) غائبة عن الملف: ' + '، '.join('ـ' + x for x in absent))
            if rejected:
                self.notes[f].append(f'صيغ متصلة ({slot}) في الملف لكن سجلاتها مرفوضة: ' + '، '.join('ـ' + x for x in rejected))

    def hidden_pronouns(self):
        """قواعد لا معجم: يُفحص كل سجل ولا يُكتب في المعجم"""
        f = 'hidden_pronouns'
        ok = 0
        for r in self.rows(f):
            m = re.search(r'\(([^)]+)\)', r['type'] or '')
            taqdir = m.group(1).strip() if m else ''
            reasons = []
            t0 = strip_marks(taqdir)
            if not (t0 in ('أنا', 'نحن', 'هو', 'هي') or (t0 == 'أنت' and KASRA not in taqdir)):
                reasons.append(f'المستتر لا يكون «{taqdir}»: لا يستتر إلا أنا، نحن، أنتَ، هو، هي')
            p = parse_person(r['reference'])
            tp = {'أنا': 1, 'نحن': 1, 'أنت': 2, 'هو': 3, 'هي': 3, 'هم': 3, 'هن': 3}.get(strip_marks(taqdir))
            if p and tp and p != tp:
                reasons.append(f'تعارض: التقدير «{taqdir}» والمرجع «{r["reference"]}»')
            first = (r['example'] or '').split()[0] if (r['example'] or '').split() else ''
            if strip_marks(taqdir) == 'أنت' and KASRA not in taqdir and strip_marks(first).endswith('ي'):
                reasons.append(f'المثال «{first}» فيه ياء المخاطبة البارزة')
            if reasons:
                self.reject(f, r['id'], r['type'], reasons)
            else:
                ok += 1
        self.stats[f]['valid_rules'] = ok
        self.notes[f].append('ملف قواعد لا معجم: لا يُكتب في المعجم؛ فُحصت سجلاته فقط.')

    def demonstratives(self):
        f = 'demonstrative_pronouns'
        for r in self.rows(f):
            numc = r['number_classification'] or ''
            place = 'مكان' in numc
            status = 'murab' if 'معرب' in (r['grammatical_status'] or '') else 'mabni'
            noun = {'subtype': 'demonstrative', 'definiteness': 'definite', 'definite_by': 'demonstrative',
                    'inflection': {'status': status}}
            g, n = parse_gender(r['gender']), (None if place else parse_number(numc))
            a = agreement(g, n)
            if a:
                noun['agreement'] = a
            dist = r['distance'] or ''
            self.add(f, r['id'], r['name'], 'demonstrative', 'noun', noun=noun, split_forms=True, status_src='record',
                     extra={'distance': 'near' if 'قريب' in dist else 'far' if 'بعيد' in dist else None,
                            'place': place or None, 'gender': g if g == 'common' else None},
                     meanings=[r['semantic_analysis']], examples=[r['example']])

    def relatives(self):
        f = 'relative_pronouns'
        for r in self.rows(f):
            form, _, problems = normalize_form(r['name'])
            if problems:
                self.reject(f, r['id'], r['name'], problems); continue
            if eo.cv.divine_name(form) is not None:
                self.reject(f, r['id'], r['name'], ['لفظ الجلالة (اللَّهُمَّ) ليس اسماً موصولاً']); continue
            p = loose(form)
            if p not in REF_RELATIVES:
                self.reject(f, r['id'], r['name'], ['ليست في جرد الموصولات المرجعي']); continue
            ref_v = {drop_final_mark(unicodedata.normalize('NFC', x)) for x in REF_RELATIVES_VOCALIZED}
            if drop_final_mark(form) not in ref_v:
                self.reject(f, r['id'], r['name'], [f'تشكيل «{form}» يخالف الصيغة في الجرد المرجعي']); continue
            n = parse_number(r['number'])
            if p.startswith(('اللذ', 'اللت')) and n != 'dual':
                self.reject(f, r['id'], r['name'], [f'صيغة مثنى موسومة «{r["number"]}»']); continue
            murab = stated_status(r) == 'معرب'
            noun = {'subtype': 'relative', 'definiteness': 'definite', 'definite_by': 'relative',
                    'inflection': {'status': 'murab' if murab else 'mabni'}}
            g = parse_gender(r['gender'])
            general = p in ('من', 'ما', 'اي', 'ال', 'ذو', 'ذا')
            if not general:
                a = agreement(g, n)
                if a:
                    noun['agreement'] = a
            self.add(f, r['id'], r['name'], 'relative', 'noun', noun=noun, status_src='record' if murab else 'file_scope',
                     extra={'general': general or None},
                     meanings=[r['grammatical_analysis']], examples=[r['example']])

    def adverbs(self, conj_forms):
        f = 'built_in_adverbs'
        for r in self.rows(f):
            form, _, problems = normalize_form(r['adverb'])
            if problems:
                self.reject(f, r['id'], r['adverb'], problems); continue
            if stated_status(r) == 'معرب':
                self.add(f, r['id'], r['adverb'], 'adverb', 'noun', status_src='record',
                         noun={'subtype': 'adverbial', 'inflection': {'status': 'murab'}},
                         meanings=[r['syntactic_analysis'], r['semantic_analysis']], examples=[r['example_sentence']])
                continue
            bm = BUILD.get((r['adverb_type'] or '').strip())
            lm = last_mark(form)
            reasons = []
            if has_tanwin(form):
                reasons.append('التنوين علامة إعراب: الكلمة معربة لا مبنية')
            elif lm in ('damma', 'fatha', 'kasra', 'sukun') and bm and lm != bm:
                reasons.append(f'علامة الآخر ({lm}) تخالف نوع البناء ({bm})')
            if strip_marks(form).replace('ّ', '') and form.replace(SHADDA, '') in conj_forms:
                reasons.append('الصيغة نفسها حرف عطف في coordinating_conjunctions')
            if reasons:
                self.reject(f, r['id'], r['adverb'], reasons); continue
            self.add(f, r['id'], r['adverb'], 'adverb', 'noun',
                     noun={'subtype': 'adverbial', 'inflection': {'status': 'mabni', 'build_mark': bm}},
                     meanings=[r['syntactic_analysis'], r['semantic_analysis']], examples=[r['example_sentence']])

    def verb_names(self):
        f = 'verb_name'
        tense_map = {'أمر': 'imperative', 'ماضٍ': 'past', 'مضارع': 'imperfect'}
        for r in self.rows(f):
            t = (r['tense'] or '').strip()
            warn = []
            first = (r['meaning'] or '').split()[0] if (r['meaning'] or '').split() else ''
            if t == 'أمر' and strip_marks(first).startswith('أت'):
                warn.append(f'الزمن «أمر» والمعنى «{first}» بصيغة المضارع')
            self.add(f, r['id'], r['name'], 'verb_name', 'noun', split_forms=True,
                     noun={'subtype': 'ism_fiil', 'inflection': {'status': 'mabni'}},
                     extra={'tense': tense_map.get(t, t), 'origin': (r['type'] or '').strip()},
                     meanings=[r['meaning']], examples=[r['example']], warnings=warn)
        g9 = {loose(op['form']) for op in self.cat.ops.values() if op['group'] == '9'}
        have = {loose(e['form']) for e in self.cand if e['category'] == 'verb_name'}
        miss = sorted(g9 - have)
        if miss:
            self.notes[f].append('أسماء أفعال في operators_catalog (المجموعة 9) غائبة عن الملف: ' + '، '.join(miss))

    def kinaya(self):
        f = 'kinaya_names'
        for r in self.rows(f):
            murab = stated_status(r) == 'معرب'
            self.add(f, r['id'], r['name'], 'kinaya', 'noun', status_src='record' if murab else 'file_scope',
                     noun={'subtype': 'kinaya', 'inflection': {'status': 'murab' if murab else 'mabni'}},
                     extra={'kind': r['type']}, meanings=[r['meaning_usage']], examples=[r['example']],
                     )

    def particle_file(self, f, head, effect_of, *, groups=None, meaning_keys=(), example_key='example',
                      is_noun=None, noun_subtype=None, category_noun=None, extra_of=None, skip=None):
        for r in self.rows(f):
            raw = r.get(head) or ''
            why = skip(r) if skip else None
            if why:
                self.reject(f, r['id'], raw, why)
                continue
            if f == 'jazm_tools' and len(raw.split()) == 2 and strip_marks(raw.split()[1]) == 'الناهية':
                raw = raw.split()[0]              # «لَا اَلنَّاهِيَة»: الوصف ليس جزءاً من الصيغة
            effect = effect_of(r)
            meanings = [r.get(k) for k in meaning_keys]
            examples = [r.get(example_key)]
            if is_noun and is_noun(r):
                txt = strip_marks(' '.join(str(v) for k, v in r.items() if k not in META_FIELDS))
                murab = re.search('معرب(?!ات)', txt) is not None
                stated = murab or re.search('مبني(?!ات)', txt) is not None
                self.add(f, r['id'], raw, category_noun, 'noun', status_src='record' if stated else 'file_scope',
                         noun={'subtype': noun_subtype, 'inflection': {'status': 'murab' if murab else 'mabni'}},
                         extra={'effect': effect, **(extra_of(r) if extra_of else {})},
                         meanings=meanings, examples=examples)
                continue
            ids = self.catalog_ids(raw, groups)
            part = {'governing': effect != 'none', 'effect': effect}
            if ids:
                part['operator_ids'] = ids
            self.add(f, r['id'], raw, 'particle', 'particle', particle=part,
                     extra=extra_of(r) if extra_of else None, meanings=meanings, examples=examples)

    def particles(self):
        self.particle_file('jazm_tools', 'tool',
                           lambda r: 'jazm_two' if r['jazm_type'] == 'فعلين' else 'jazm_one',
                           groups={'6', '7'}, meaning_keys=('category', 'description'),
                           is_noun=lambda r: (r['category'] or '').startswith('اسم'),
                           noun_subtype='conditional', category_noun='conditional_noun')
        self.particle_file('present_naseb_tools', 'tool', lambda r: 'nasb_verb', groups={'5', '1'},
                           meaning_keys=('parsing', 'meaning_usage'),
                           extra_of=lambda r: {'work_condition': r['work_condition']})
        self.particle_file('conditional_letters_tools', 'particle',
                           lambda r: 'none' if 'غير جازم' in (r['grammatical_function'] or '')
                           else 'jazm_two' if 'جازم' in (r['grammatical_function'] or '') else 'none',
                           groups={'6', '7'}, meaning_keys=('grammatical_function', 'notes'),
                           is_noun=lambda r: 'حرف' not in (r['grammatical_function'] or '') + (r['parsing'] or ''),
                           noun_subtype='conditional', category_noun='conditional_noun')
        self.particle_file('copulative_particle', 'copulative_particle', lambda r: 'nasb_ism_raf_khabar',
                           groups={'2', '3'}, meaning_keys=('indication', 'effect'))
        self.particle_file('vocative_particles', 'particle', lambda r: 'nasb', groups={'4'},
                           meaning_keys=('particle_type', 'usage'),
                           skip=lambda r: 'اسم' in (r['particle_type'] or '') and
                           [f'الملف نفسه يصنّفه «{r["particle_type"]}»: ليس حرف نداء'])
        self.particle_file('letters_answers', 'particle', lambda r: 'none', meaning_keys=('definition',),
                           example_key='examples')
        self.particle_file('coordinating_conjunctions', 'letter', lambda r: 'none', meaning_keys=('usages',),
                           extra_of=lambda r: {'role': 'عطف'})
        self.particle_file('interrogative_letters_tools', 'tool', lambda r: 'none',
                           meaning_keys=('type', 'question_about'))
        self.particle_file('interrogative_tools_categories', 'tool', lambda r: 'none',
                           meaning_keys=('subject', 'explanation'),
                           is_noun=lambda r: (r['type'] or '').strip() == 'اسم',
                           noun_subtype='interrogative', category_noun='interrogative_noun')
        for r in self.rows('preposition_meanings'):
            raw = r['preposition'] or ''
            if not strip_marks(raw).strip():
                self.reject('preposition_meanings', r['id'], raw, ['سجل فارغ']); continue
            for part in [p for p in re.split(r'\s+وَ?\s+', raw) if p.strip()]:
                ids = self.catalog_ids(part, {'1'})
                prt = {'governing': True, 'effect': 'jarr'}
                if ids:
                    prt['operator_ids'] = ids
                self.add('preposition_meanings', r['id'], part, 'particle', 'particle', particle=prt,
                         meanings=[r['meaning']], examples=[r['example']])

    def descriptive(self):
        for f in ('building_regulations', 'types_of_i3rab', 'estimated_parsing_indeclinables',
                  'functional_indeclinable_substitutes', 'indeclinable_discourse_roles', 'verb_building_rules',
                  'imperative_verb_building', 'present_tense_building_cases', 'past_tense_conjugation_rules',
                  'compound_numbers', 'compound_number_details', 'grammatical_construction_cases'):
            rows = self.rows(f)
            self.notes[f].append('ملف وصفي/قواعد: لا يُكتب في المعجم.')
            if f == 'grammatical_construction_cases':
                junk = [r['id'] for r in rows if str(r.get('case_type')).strip() in ('nan', '--', 'None', '')
                        or r.get('description') == 'الشرح']
                if junk:
                    self.notes[f].append(f'{len(junk)} سجلاً بلا case_type أو رأس جدول: {junk}')

    # ----- الدمج والتحقق -----
    def finalize(self):
        # الهوية: الصيغة + الفئة + ما يميّز المتجانسات رسماً (خصائص الضمير، عمل الحرف، النوع الفرعي)
        ident = lambda e: (e['category'], e['form'], json.dumps(e.get('pronoun'), sort_keys=True),
                           (e.get('particle') or {}).get('effect'), (e.get('noun') or {}).get('subtype'))
        groups = OrderedDict()
        for e in self.cand:
            groups.setdefault(ident(e), []).append(e)
        out = []
        for key, es in groups.items():
            form = key[1]
            status = lambda e: (e.get('noun') or {}).get('inflection', {}).get('status')
            stated = {status(e) for e in es if e.get('_status_src') == 'record' and status(e)}
            if len(stated) > 1:
                ids = sorted({(s['file'], s['id']) for e in es for s in e['sources']})
                for e in es:
                    if e.get('_status_src') == 'record':
                        self.reject(e['sources'][0]['file'], e['sources'][0]['id'], form,
                                    [f'تعارض صريح بين السجلات {[i for _, i in ids]}: معرب ومبني'])
                es = [e for e in es if e.get('_status_src') != 'record']
                if not es:
                    continue
            elif len(stated) == 1:
                st = stated.pop()
                for e in es:
                    if status(e) and status(e) != st:      # افتراض النطاق يُستبدل بالمصرَّح به في سجل آخر
                        e['noun']['inflection'] = {'status': st}
                        e['warnings'].append(f'حالة «{st}» مأخوذة من سجل يصرّح بها بدل افتراض نطاق الملف')
            core = lambda e: json.dumps({k: e.get(k) for k in ('pos', 'noun', 'particle', 'pronoun')}, sort_keys=True)
            by_core = OrderedDict()
            for e in es:
                by_core.setdefault(core(e), []).append(e)
            for es2 in by_core.values():
                m = es2[0]
                for e in es2[1:]:
                    for k in ('meanings', 'examples', 'sources', 'normalizations', 'warnings'):
                        m[k] += [x for x in e[k] if x not in m[k]]
                    if e.get('extra'):
                        for k, v in e['extra'].items():
                            if isinstance(v, list):
                                m.setdefault('extra', {}).setdefault(k, [])
                                m['extra'][k] += [x for x in v if x not in m['extra'][k]]
                if len(es2) > 1:
                    self.stats[m['sources'][0]['file']]['merged_duplicates'] += len(es2) - 1
                out.append(m)
        final = []
        for i, e in enumerate(out):
            if (e.pop('_status_src', None) == 'file_scope' and e.get('noun')
                    and e['category'] not in ('separate_pronoun', 'attached_pronoun')
                    and not any('من نطاق الملف' in w for w in e['warnings'])):
                e['warnings'].append('البناء افتراض من نطاق الملف (المبنيات)، لا تصريح في السجل')
            e['entry_id'] = f"mabniyat:{e['category']}:{i:04d}"
            for k in ('meanings', 'examples', 'normalizations', 'warnings'):
                if not e[k]:
                    del e[k]
            if e.get('noun', {}).get('inflection', {}).get('build_mark') is None:
                e.get('noun', {}).get('inflection', {}).pop('build_mark', None)
            if e['category'] != 'attached_pronoun' and len(e['plain']) > 1:
                rows = [x for w in e['form'].split() for x in cv.run(w)['rows']]
                if (e.get('noun') or {}).get('inflection', {}).get('status') == 'murab' and rows:
                    rows = rows[:-1]          # المعرب يُستشهد به بلا حركة إعراب على آخره
                bad = [(rend, pat) for rend, pat, ver, _ in rows if ver != 'OK']
                if bad:
                    e.setdefault('warnings', []).append(
                        'التقطيع: ' + '، '.join(f'«{x}» {p}' for x, p in bad) + ' (تشكيل ناقص في المصدر)')
            errs = self.validator.errors(e)
            if errs:
                self.reject(e['sources'][0]['file'], e['sources'][0]['id'], e['form'], ['لا يطابق المخطط: ' + errs[0]])
                continue
            final.append(e)
        accepted = {(s['file'], s['id']) for e in final for s in e['sources']}
        for f, rid in accepted:
            self.stats[f]['accepted_records'] += 1
        return final

    def catalog_crosscheck(self, final):
        lines = []
        cond = json.load(open(os.path.join(self.src, 'conditional_letters_tools.json'), encoding='utf-8'))['data']
        g7 = {loose(op['form']) for op in self.cat.ops.values() if op['group'] == '7'}
        for r in cond:
            if 'غير جازم' in (r['grammatical_function'] or '') and loose(r['particle']) in g7:
                lines.append(f'- **تعارض:** «{r["particle"]}» في المجموعة 7 من الفهرس (الشرط الجازمة فقط)، '
                             f'و`conditional_letters_tools` يقول: «{r["grammatical_function"].strip()[:40]}…».')
        have = defaultdict(set)
        for e in final:
            eff = (e.get('particle') or {}).get('effect') or (e.get('extra') or {}).get('effect')
            if eff:
                have[eff].add(e['plain'])
        cat_by = {'jazm_two': {'6', '7'}, 'jarr': {'1'}}
        for eff, grps in cat_by.items():
            cat_forms = {loose(op['form']) for op in self.cat.ops.values() if op['group'] in grps}
            extra = sorted(p for p in {loose(x) for x in have[eff]} - cat_forms)
            if extra:
                lines.append(f'- **في المعجم وليست في الفهرس** (`{eff}`، المجموعة {"/".join(sorted(grps))}): ' + '، '.join(extra))
        return lines


def write_report(conv, final, path, cross):
    st = conv.stats
    files = sorted(st)
    L = ['# تقرير تحويل `02_mabniyat` إلى المعجم', '',
         f'- **مداخل مقبولة:** {len(final)} (في `mabniyat_lexicon.jsonl`، كلها تطابق `schema/lexicon_entry.schema.json`)',
         f'- **سجلات مرفوضة:** {len(conv.rejected)} (في `mabniyat_rejected.jsonl` مع أسبابها)',
         f'- **تصحيحات إملائية آلية:** {sum(len(e.get("normalizations", [])) for e in final)} في المداخل المقبولة', '',
         '## لكل ملف', '', '| الملف | السجلات | مقبولة | مدموجة (تكرار) | مرفوضة | أسباب الرفض |', '|---|---|---|---|---|---|']
    for f in files:
        s = st[f]
        rej = {k[len('rejected: '):]: v for k, v in s.items() if k.startswith('rejected: ')}
        L.append(f"| `{f}` | {s['in']} | {s['accepted_records']} | {s['merged_duplicates'] or ''} | "
                 f"{sum(rej.values()) or ''} | {'؛ '.join(f'{k} ({v})' for k, v in sorted(rej.items(), key=lambda x: -x[1]))} |")
    corr = Counter()
    for f in files:
        for k in ('deleted (correction)', 'edited (correction)', 'added (correction)', 'held',
                  'section headers', 'merged continuations'):
            corr[k] += st[f][k]
    if sum(corr.values()):
        L += ['', '## التصحيحات المطبّقة من `data_fixes/mabniyat_corrections.json`', '',
              f"- حذف: {corr['deleted (correction)']}، تعديل: {corr['edited (correction)']}، إضافة: {corr['added (correction)']}",
              f"- معلّقة حتى التوثيق: {corr['held']} (في `mabniyat_held.jsonl`)",
              f"- إصلاح البنية: {corr['section headers']} عنوان قسم، {corr['merged continuations']} مثال أُلحق بسجله"]
        if conv.held:
            L += ['', '**المعلّقة:**', ''] + [f"- `{h['source']['file']}` ({h['source']['id']}): {h['reason']}" for h in conv.held]
    L += ['', '## ملاحظات الملفات', '']
    for f in files:
        for n in conv.notes.get(f, []):
            L.append(f'- `{f}`: {n}')
    L += ['', '## المقارنة بـ `operators_catalog`', ''] + (cross or ['- لا فروق.'])
    L += ['', '## التصحيحات الآلية المطبّقة', '']
    c = Counter(n for e in final for n in e.get('normalizations', []))
    L += [f'- {k}: {v}' for k, v in c.most_common()]
    L += ['', '## المداخل حسب الفئة', '']
    c = Counter(e['category'] for e in final)
    L += [f'- `{k}`: {v}' for k, v in c.most_common()]
    with open(path, 'w', encoding='utf-8') as fh:
        fh.write('\n'.join(L) + '\n')


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    ap = argparse.ArgumentParser(description='تحويل 02_mabniyat إلى معجم الكلمات المغلقة')
    ap.add_argument('--src', default=os.path.join(here, 'data', '02_mabniyat'))
    ap.add_argument('--out', default=os.path.join(here, 'lexicon'))
    ap.add_argument('--fixes', default=os.path.join(here, 'data_fixes', 'mabniyat_corrections.json'),
                    help='ملف التصحيحات؛ «none» لتعطيله')
    ap.add_argument('--write-corrected', metavar='DIR',
                    help='اكتب نسخة مصحَّحة من ملفات المصدر (البنية نفسها) في DIR')
    args = ap.parse_args()
    cat = eo.Catalog([p for p in (os.path.join(here, 'operators_catalog.jsonl'),
                                  os.path.join(here, 'operators_catalog_split_vocalized.csv')) if os.path.exists(p)])
    conv = Converter(args.src, cat)
    if args.fixes != 'none' and os.path.exists(args.fixes):
        with open(args.fixes, encoding='utf-8') as fh:
            conv.fixes = json.load(fh)['files']
    conj = set()
    for r in json.load(open(os.path.join(args.src, 'coordinating_conjunctions.json'), encoding='utf-8'))['data']:
        fm, _, _ = normalize_form(r['letter'])
        conj.add(fm.replace(SHADDA, ''))
    conv.pronouns(); conv.hidden_pronouns(); conv.demonstratives(); conv.relatives()
    conv.adverbs(conj); conv.verb_names(); conv.kinaya(); conv.particles(); conv.descriptive()
    final = conv.finalize()
    cross = conv.catalog_crosscheck(final)
    os.makedirs(args.out, exist_ok=True)
    with open(os.path.join(args.out, 'mabniyat_lexicon.jsonl'), 'w', encoding='utf-8') as fh:
        for e in final:
            fh.write(json.dumps(e, ensure_ascii=False) + '\n')
    with open(os.path.join(args.out, 'mabniyat_rejected.jsonl'), 'w', encoding='utf-8') as fh:
        for r in conv.rejected:
            fh.write(json.dumps(r, ensure_ascii=False) + '\n')
    with open(os.path.join(args.out, 'mabniyat_held.jsonl'), 'w', encoding='utf-8') as fh:
        for r in conv.held:
            fh.write(json.dumps(r, ensure_ascii=False) + '\n')
    write_report(conv, final, os.path.join(args.out, 'mabniyat_report.md'), cross)
    if args.write_corrected:
        write_corrected(args.src, args.write_corrected, conv.corrected_data)
    print(f'مقبولة: {len(final)}  مرفوضة: {len(conv.rejected)}  معلّقة: {len(conv.held)}  → {args.out}/')


def write_corrected(src, dst, corrected):
    """نسخة مصحَّحة من المصدر بالبنية نفسها؛ الحقول الداخلية تصير حقولاً صريحة"""
    os.makedirs(dst, exist_ok=True)
    for name in sorted(f[:-5] for f in os.listdir(src) if f.endswith('.json')):
        with open(os.path.join(src, name + '.json'), encoding='utf-8') as fh:
            d = json.load(fh)
        if name in corrected:
            rows = []
            for r in corrected[name]:
                r = dict(r)
                if '_status' in r:
                    r['grammatical_status'] = r.pop('_status')
                if '_added' in r:
                    r['added_reason'] = r.pop('_added')
                rows.append(r)
            d['data'] = rows
            if 'total' in d:
                d['total'] = len(rows)
            if 'pagination' in d:
                d['pagination'].update(total=len(rows), to=len(rows))
        with open(os.path.join(dst, name + '.json'), 'w', encoding='utf-8') as fh:
            json.dump(d, fh, ensure_ascii=False, indent=1)


if __name__ == '__main__':
    main()
