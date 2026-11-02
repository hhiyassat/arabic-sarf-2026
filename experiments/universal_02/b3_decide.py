# -*- coding: utf-8 -*-
"""B3 (R1–R4 المصحَّح): الأساسُ مرشّحاتُ المقشِّر A (لا تُفقَد فصولُها)؛ وتُضاف تفكيكاتُ المورد
المنصوصة (decomposition_index + RULE_SPLITS) للألفاظ المطابقة؛ وR1 يرفض الفصلَ الضميريّ فقط
إذا ثبت أنّ السابق غيرُ مضيف (همزةُ استفهام/نداء، عطفٌ غيرُ جرّ)، مع سجلّ الموانع والبدائل.
KEEP_AS_UNIT للـ22 المسمّاة في المورد وحدها."""
import os, sys, json, importlib, unicodedata, csv
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE); sys.path.insert(0, ROOT)
import mabniyat_reader as mr
HARAKAT = set('ًٌٍَُِّْ')
def norm(s):
    s = unicodedata.normalize('NFC', s)
    while s and s[-1] in HARAKAT: s = s[:-1]
    return s

def load_index():
    J, _ = mr.load(); idx = {}; named = set()
    for e in J['decomposition_index']:
        comps = [c['text'] for c in e.get('components', [])]
        ref = f"{e.get('file')}#{e.get('record_id')}"
        if e.get('surface'): idx[norm(e['surface'])] = (comps, ref)
        for f in e.get('form_decompositions', []) or []:
            sf = f.get('surface') or f.get('form')
            if sf: idx[norm(sf)] = ([c['text'] for c in f.get('components', [])] or comps, ref + '/form')
    for u in J['unsegmented_or_deferred_items']:
        s = u.get('surface') or u.get('name') or (u if isinstance(u, str) else None)
        if s: named.add(norm(s))
    return idx, named

def load_rules():
    r = {}
    for row in csv.DictReader(open(os.path.join(HERE, 'RULE_SPLITS.tsv'), encoding='utf-8'), delimiter='\t'):
        r[norm(row['السطح'])] = (row['الأجزاء'].split('|'),
                                 'RULE_SPLITS:' + row['السند'].split('؛')[0].strip(),
                                 row.get('النوع', 'نصّ'))
    return r

def peeler_slots(word, policy):
    for k in ('SARF_SEG_POLICY', 'SARF_SEG_RAISE_OPS'): os.environ.pop(k, None)
    if policy != 'A': os.environ['SARF_SEG_POLICY'] = policy
    import sarf.segment, sarf.analyze, sarf.catalog
    importlib.reload(sarf.segment); importlib.reload(sarf.analyze)
    from sarf.analyze import analyze
    from sarf.catalog import Catalog
    cat = Catalog([os.path.join(ROOT, 'operators_catalog.jsonl'), os.path.join(ROOT, 'operators_catalog_split_vocalized.csv')])
    return [s['text'] for s in analyze(cat, word)['segments'][0]['slots']]

_IDX, _NAMED = load_index(); _RULES = load_rules()

# ————— مفاتيحُ المطابقة بالتشكيل (الجولة 3، البند ١): بِ ≠ بَ ؛ حركةُ الآخر لا تُحتسب للكلمات ذوات الحرفين فأكثر —————
def _bare(s):   # الهيكلُ الأصمّ (لكشف همزة/عطف/نداء بلا نظرٍ للحركة)
    s = unicodedata.normalize('NFC', s)
    return ''.join(c for c in s if not unicodedata.combining(c) and c != 'ـ')
def hk(s):      # مفتاحُ المضيف: يبقي التشكيلَ الداخليّ، ويُسقِط حركةَ الآخر وحدها إن كان أكثرَ من حرف
    s = unicodedata.normalize('NFC', s)
    cons = [c for c in s if not unicodedata.combining(c)]
    if len(cons) > 1:
        while s and s[-1] in HARAKAT: s = s[:-1]
    return s
def skel(s):    # الحروف + الشدّة وحدها (لكشف إدغام النون)
    s = unicodedata.normalize('NFC', s)
    return ''.join(c for c in s if c == 'ّ' or not unicodedata.combining(c))

from sarf.catalog import Catalog as _Catalog
_OPC = _Catalog([os.path.join(ROOT, 'operators_catalog.jsonl'),
                 os.path.join(ROOT, 'operators_catalog_split_vocalized.csv')])
# العواملُ الأحاديّة بتشكيلها (hk) — المضيفُ الموجب (البند ٢: stem_info يُسقَط من الأدلّة)
_OP_HK = {hk(o['form']) for o in _OPC.ops.values() if o['n_words'] == 1}
_JARR  = {hk(o['form']) for o in _OPC.ops.values() if o['n_words'] == 1 and str(o.get('group')) == '1'}   # حروف الجرّ
_NASIKH= {hk(o['form']) for o in _OPC.ops.values() if o['n_words'] == 1 and str(o.get('group')) == '2'}   # إنّ وأخواتها
_JARR_F  = {hk(o['form']): o['form'] for o in _OPC.ops.values() if o['n_words'] == 1 and str(o.get('group')) == '1'}
_NASIKH_F= {hk(o['form']): o['form'] for o in _OPC.ops.values() if o['n_words'] == 1 and str(o.get('group')) == '2'}

# الضمائرُ المنفصلة من فهرس pronouns_classification (البند ٣: R5) — لا قائمةٌ في الشفرة
def _load_sep_pron():
    import json as _json
    J = _json.load(open(os.path.expanduser('~/arabic-sarf-2026/mabniyat_v4/MABNIYAT_FULL_WITH_DECOMPOSITION.json'), encoding='utf-8'))
    s = set()
    for r in J.get('resources', []):
        if r.get('file', '').endswith('pronouns_classification.json'):
            for d in r.get('data', []):
                if 'منفصل' in str(d.get('category', '')):
                    pf = d.get('pronoun_form') or d.get('pronoun')
                    if pf: s.add(hk(pf))
    return s
_SEP_PRON = _load_sep_pron()
# الضمائرُ المتّصلة (لتحديد موضع المضيف الملاصق)
PRONOUNS = {'ه','هِ','هُ','ها','هَا','هم','هُم','هُمْ','هِم','هِمْ','هما','هُمَا','هِمَا',
            'هن','هُنَّ','هِنَّ','ك','كَ','كِ','كم','كُم','كُمْ','كُنَّ','كما','كُمَا',
            'نا','نَا','ني','نِي','ي','يَ'}
_PRON_BARE = {_bare(x) for x in PRONOUNS}
def _is_pron(p): return _bare(p) in _PRON_BARE
_PROCLITIC = {'و', 'ف', 'أ'}   # عطفٌ/استفهام (هل تُعالَج ببادئة الكلمة)

def _proven_non_host(part):
    "R1: الوحدةُ غيرُ مضيفٍ إن كانت همزةَ استفهام/نداء أو عطفًا (و/ف/أ/ء)."
    return _bare(part) in {'أ', 'إ', 'آ', 'ء', 'و', 'ف', 'ا', 'ى'}

def _adjacent_host(parts):
    "مضيفُ الضمير المتّصل = الوحدةُ الملاصقةُ له من الجهة السابقة (في وَ+لَ+هُمْ المضيفُ لَ)."
    if len(parts) >= 2 and _is_pron(parts[-1]):
        return parts[-2]
    return None

def _host_proof(h):
    "البند ٢: المضيفُ الموجب = جدول العوامل بتشكيله وحدَه (stem_info غيرُ موثوق، مُسقَط)."
    if h is None: return None
    return 'عامل' if hk(h) in _OP_HK else None

def _naa_split(word):
    """البند ٤: الكلمةُ تنتهي بـنَّا/نِّي، وما قبلها (بردّ النون ساكنةً) ناسخٌ أو جارٌّ مثبَتٌ بتشكيله
    ← فصلٌ نصّيّ بالحدّ بين وقوعَي النون (سيبويه الإدغام + R1). الأفعالُ تبقى في GENERATOR_GAPS."""
    w = unicodedata.normalize('NFC', word)
    while w and w[-1] in HARAKAT: w = w[:-1]
    sk = skel(w)
    if sk.endswith('نّا'): pron, vowel = 'نَا', 'ا'
    elif sk.endswith('نّي'): pron, vowel = 'نِي', 'ي'
    else: return None
    if not w.endswith(vowel): return None
    base = w[:-1]                                   # ...نّ (يُبقي الشدّة)
    hostB = base                                    # ناسخ (إِنَّ/أَنَّ): يُبقي الشدّة
    hostA = base.replace('ّ', 'ْ')                   # جارّ (مِنْ/عَنْ): النونُ ساكنةٌ (ردُّ الإدغام)
    for host, fmap, snd in [(hostB, _NASIKH_F, 'ناسخ'), (hostA, _JARR_F, 'جارّ')]:
        form = fmap.get(hk(host))                    # الصورةُ القانونيّة من الجدول (لا المركَّبةُ يدويًّا)
        if form:
            return ([form, pron],
                    f'RULE(نا-إدغام): {snd}ٌ مثبَتٌ بالجدول + إدغامُ النون (سيبويه) + R1', 'نصّ')
    return None

def _r5(lib, A, word):
    """البند ٣: ضميرٌ منفصل (pronouns_classification) بعد و/ف/أ/هل بلا مضيف يُفصَل (الألفية 105، القطر 126).
    يُعاد تصنيفُ ما كان يُرفَض بـR1 إن كان الملحقُ ضميرًا منفصلًا بعد هذه الأدوات."""
    if not (len(lib) > len(A) and len(lib) >= 2): return None
    if hk(lib[-1]) not in _SEP_PRON: return None
    prev = lib[-2]
    starts_hal = unicodedata.normalize('NFC', word).startswith('هَل') or _bare(word).startswith('هل')
    if _bare(prev) in _PROCLITIC or (starts_hal and len(lib) == 2):
        return (lib, 'R5 (ضمير منفصل بعد و/ف/أ/هل): الألفية 105، القطر 126', 'نصّ')
    return None

def _attest(word):
    "نصٌّ/تقديرٌ من المورد: الفهرس، ثمّ RULE_SPLITS، ثمّ مولِّدُ نا-الإدغام."
    nf = norm(word)
    if nf in _IDX: return ('index', _IDX[nf][0], _IDX[nf][1], 'نصّ')
    if nf in _RULES:
        p, snd, knd = _RULES[nf]; return ('rule', p, snd, knd)
    na = _naa_split(word)
    if na: return ('naa', na[0], na[1], na[2])
    return None

def _classify_liberal(parts):
    """مرشّحٌ شاملٌ يزيد على A بلا نصّ ولا R5: REJECTED بمانعٍ ثابتٍ مسمًّى، أو DEFERRED نقصَ تغطيةٍ باسم ما ينقصه.
    «لا دليلَ موجب» لا يُسمّى رفضًا أبدًا (البند ٢)."""
    for p in parts:
        if p and p[0] == 'ْ':
            return ('REJECTED', 'لا ابتداء بساكن', p)
    host = _adjacent_host(parts)
    if host is not None and _proven_non_host(host):
        return ('REJECTED', 'R1: لا مضيف ملاصق (همزة/نداء/عطف)', host)
    pr = _host_proof(host) if host is not None else None
    if host is None:
        miss = 'الفهرس (فصلٌ غيرُ منصوص)'
    elif pr == 'عامل':
        miss = 'الفهرس (المضيفُ عاملٌ مثبَت بتشكيله، الفصلُ غيرُ منصوص)'
    else:
        miss = 'جدول العوامل (المضيفُ غيرُ مثبَت عاملًا؛ stem_info غيرُ موثوق)'
    return ('DEFERRED', 'لا دليلَ موجب', miss)

def _decide_core(word, A, lib):
    nf = norm(word)
    att = _attest(word)
    r5 = _r5(lib, A, word) if not att else None
    cands = []
    if att:
        knd = att[3]
        if att[0] == 'naa':
            b1 = ('الحدّ بين وقوعَي النون (سيبويه)', 'ثبت'); b2 = ('المضيفُ ناسخٌ/جارٌّ مثبَتٌ بتشكيله', 'ثبت')
        else:
            b1 = ('الحدّ بين وقوعَي الشدّة (R3)', 'ثبت') if knd == 'نصّ' else ('نمطٌ من الفهرس (تقدير)', 'ثبت')
            b2 = ('الجزءُ الملحق حرفٌ لا ضمير', 'ثبت') if knd == 'تقدير' else ('الجزءان منصوصان بالمورد', 'ثبت')
        cands.append(dict(parts=att[1], source=att[0], ref=att[2], decision='ACCEPT', barriers=[b1, b2]))
    cands.append(dict(parts=A, source='peeler_A', ref=None, decision='ACCEPT' if len(A) > 1 else 'UNIT', barriers=[]))
    if r5:
        cands.append(dict(parts=r5[0], source='R5', ref=r5[1], decision='ACCEPT',
                          barriers=[('ضميرٌ منفصلٌ بعد و/ف/أ/هل', 'ثبت')]))
    # مرشّحُ الفحص الشامل: يُقبل بـR5، وإلّا يُسجَّل REJECTED/DEFERRED (لا يُقبل بلا نصّ)
    if lib != A and len(lib) > len(A) and (not att or lib != att[1]) and (not r5 or lib != r5[0]):
        status, barrier, detail = _classify_liberal(lib)
        cands.append(dict(parts=lib, source='universal', ref=None, decision=status, barriers=[(barrier, detail)]))
    # الاختيار
    if att:
        chosen = att[1]
        rule = {'naa': 'R(نا-إدغام، منصوص)', 'index': 'R3 (منصوص بالمورد)', 'rule': 'R3 (منصوص بالمورد)'}[att[0]] \
            if att[3] == 'نصّ' else 'نمطٌ من الفهرس (تقدير)'
        qarina = att[2]
    elif r5:
        chosen = r5[0]; rule = 'R5 (ضمير منفصل)'; qarina = r5[1]
    elif len(A) > 1:
        chosen = A; rule = 'R1 (مضيفٌ صالح، فصلُ A)'; qarina = 'دليلُ A'
    elif nf in _NAMED:
        chosen = A; rule = 'KEEP_AS_UNIT (الـ22)'; qarina = 'وحدةٌ بالمورد'
    else:
        chosen = A; rule = 'جذع/اسمٌ كامل'; qarina = '—'
    # A→B3
    if chosen == A: col = 'ثابت'
    elif att and att[3] == 'نصّ': col = 'فُصل بنصّ'
    elif r5: col = 'فُصل بنصّ'
    elif att and att[3] == 'تقدير': col = 'فُصل تقديرًا'
    elif len(chosen) < len(A):
        col = 'أُسقط بمانع' if any(c['parts'] == A and c['barriers'] for c in cands) else 'أُسقط بلا مانع'
    else: col = 'فُصل بلا دليل'
    if nf in _IDX:
        ref_col = ('مطابق', _IDX[nf][1]) if chosen == _IDX[nf][0] else ('مخالف', _IDX[nf][1])
    elif att and att[0] == 'naa':
        ref_col = ('مطابق النمط', att[2])
    elif att and att[3] == 'تقدير':
        ref_col = ('مطابق النمط', att[2])
    elif r5:
        ref_col = ('مطابق النمط', r5[1])
    else:
        ref_col = ('خارج الفهرس', None)
    return dict(word=word, norm=nf, A=A, chosen=chosen, rule=rule, qarina=qarina, a_b3=col,
                candidates=cands, alternatives=[c['parts'] for c in cands if c['parts'] != chosen], ref=ref_col)

def decide_word(word):
    A = peeler_slots(word, 'A'); lib = peeler_slots(word, 'B')
    return _decide_core(word, A, lib)

def decide(word, A, lib):
    "منطقُ decide_word بمعطَيات A وlib محسوبة (للدفعات)."
    return _decide_core(word, A, lib)
