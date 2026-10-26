#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
cv_syllabifier.py — محوّل CV رباعي الطبقات للعربية (وضع MEASURE)
    Normalize ∘ CVmap ∘ Syllabify ∘ Classify
لا تُطبَّق قوانين المقاطع كقيود؛ يُقطَّع بالتعريف فقط (كل نواة تأخذ الصامت الذي قبلها)
ثم يُعَدّ ما خرج. أي نوع خارج الستة يُبلَّغ OTHER مع المقدمة المخروقة.
"""
import sys, json, hashlib
from collections import Counter, OrderedDict

# ---------- Unicode ----------
FATHA, DAMMA, KASRA = 'َ', 'ُ', 'ِ'
SUKUN, SHADDA = 'ْ', 'ّ'
FATHATAN, DAMMATAN, KASRATAN = 'ً', 'ٌ', 'ٍ'
MADDA_MARK, DAGGER_ALIF, TATWEEL = 'ٓ', 'ٰ', 'ـ'
MARKS = {FATHA, DAMMA, KASRA, SUKUN, SHADDA, FATHATAN, DAMMATAN, KASRATAN, MADDA_MARK, DAGGER_ALIF}
SHORT = {FATHA: 'a', DAMMA: 'u', KASRA: 'i'}
TANWIN = {FATHATAN: 'a', DAMMATAN: 'u', KASRATAN: 'i'}

HAMZA_FORMS = {'أ': 'ء', 'إ': 'ء', 'ؤ': 'ء', 'ئ': 'ء', 'ء': 'ء'}
SOLAR = set('تثدذرزسشصضطظلن')
PROCLITIC_FATHA = set('وف')            # وَ / فَ قبل همزة الوصل
DAMMA_BEFORE_WASL = ('كُمْ', 'هُمْ', 'تُمْ')   # قائمة مغلقة: تُحرَّك بالضم عند الوصل
FATHA_BEFORE_WASL = ('مِنْ',)                 # قائمة مغلقة: تُحرَّك بالفتح عند الوصل

# قاموس مغلق: ألف محذوفة خطاً (تُدرَج قبل المعالجة)
LEXICAL_MADD = OrderedDict([
    ('اللَّه', 'اللَّاه'),
    ('ذَلِك', 'ذَالِك'),
    ('هَذَا', 'هَاذَا'),
    ('هَذِه', 'هَاذِه'),
    ('الرَّحْمَن', 'الرَّحْمَان'),
])

SIX = ['CV', 'CVV', 'CVC', 'CVVC', 'CVCC', 'CVVCC']

class Events(Counter):
    pass

# ---------- Stage 0: tokenize ----------
def tokenize(word):
    """→ [(letter, set(marks))]"""
    out = []
    for ch in word:
        if ch == TATWEEL:
            continue
        if ch in MARKS:
            if out:
                out[-1][1].add(ch)
        else:
            out.append([ch, set()])
    return out

# ---------- Stage 1: Normalize ----------
def normalize(word, ev):
    for k, v in LEXICAL_MADD.items():
        if k in word:
            word = word.replace(k, v)
            ev['LEXICAL_MADD_INSERTION'] += 1
    word = word.replace('آ', 'ء' + FATHA + 'ا')            # المدّة
    if 'آ' in word:
        ev['MADDA_EXPANDED'] += 1
    toks = tokenize(word)
    for t in toks:
        if t[0] in HAMZA_FORMS and t[0] != 'ء':
            t[0] = 'ء'
            ev['HAMZA_UNIFIED'] += 1
        if MADDA_MARK in t[1]:
            t[1].discard(MADDA_MARK)
    return toks

def vowel_of(marks):
    for m in (FATHA, DAMMA, KASRA):
        if m in marks:
            return m
    return None

def tanwin_of(marks):
    for m in (FATHATAN, DAMMATAN, KASRATAN):
        if m in marks:
            return m
    return None

# ---------- Stage 2: CVmap → abstract segments ----------
# segment kinds: ('C',letter) ('V',x) ('VV',x) ('HW',) ('TANWIN',x) ('TAA',) ('POISON',letter)
def cvmap(toks, ev):
    seg = []
    n = len(toks)
    i = 0
    while i < n:
        L, mk = toks[i]
        prev_v = None
        for s in reversed(seg):
            if s[0] in ('V', 'VV'):
                prev_v = s[1][0]; break
            if s[0] == 'C':
                break
        nxt = toks[i + 1] if i + 1 < n else None
        is_last = (i == n - 1)

        # --- ا / ى ---
        if L in ('ا', 'ى'):
            if L == 'ى' and i > 0 and tanwin_of(toks[i - 1][1]) == FATHATAN:
                ev['SILENT_ALIF_TANWIN'] += 1; i += 1; continue
            if L == 'ا' and i > 0 and tanwin_of(toks[i - 1][1]) == FATHATAN:
                ev['SILENT_ALIF_TANWIN'] += 1; i += 1; continue
            if L == 'ا' and is_last and i > 0 and toks[i - 1][0] == 'و' and not toks[i - 1][1] \
                    and seg and seg[-1][0] == 'VV' and seg[-1][1] == 'uu':
                ev['SILENT_ALIF_FARIQA'] += 1; i += 1; continue
            # همزة وصل؟
            wasl = False
            if i == 0:
                wasl = True
            elif prev_v != 'a':
                wasl = True                      # بعد ضمة/كسرة لا تكون مدّاً
            elif nxt is not None:
                nl, nm = nxt
                if nl == 'ل' and vowel_of(nm) is None and tanwin_of(nm) is None:
                    wasl = True                  # ال (لام ساكنة/مجردة/مشددة)
                elif SUKUN in nm:
                    wasl = True                  # CVVC غير مدغم مستحيل وصلاً ⇒ وصل
                elif SHADDA in nm and i == 1 and toks[0][0] in PROCLITIC_FATHA:
                    wasl = True                  # وَاتَّقُوا / فَادَّعَى
            if wasl:
                seg.append(('HW',)); ev['HAMZAT_WASL'] += 1; i += 1; continue
            if prev_v == 'a' and seg and seg[-1][0] == 'V':
                seg[-1] = ('VV', 'aa'); ev['MADD_ALIF'] += 1; i += 1; continue
            seg.append(('POISON', L)); ev['POISON_ALIF_UNRESOLVED'] += 1; i += 1; continue

        # --- لام التعريف ---
        if L == 'ل' and not mk and seg and seg[-1][0] == 'HW':
            if nxt is not None and SHADDA in nxt[1] and nxt[0] in SOLAR:
                ev['SOLAR_LAM_DELETED'] += 1; i += 1; continue   # الشمسية: اللام محذوفة والحرف مشدد
            seg.append(('POISON', L)); ev['POISON_BARE_LAM'] += 1; i += 1; continue
        if L == 'ل' and not mk and nxt is not None and SHADDA in nxt[1] and nxt[0] in SOLAR \
                and i >= 1 and toks[i - 1][0] == 'ل':
            ev['SOLAR_LAM_DELETED'] += 1; i += 1; continue       # لِلشَّهَادَةِ

        # --- و / ي حاملة للألف الخنجرية: الصَّلَوٰة / الزَّكَوٰة — الحرف رسم فقط، والخنجرية مدّ للفتحة قبلها ---
        if L in ('و', 'ي') and mk == {DAGGER_ALIF} and prev_v == 'a' and seg and seg[-1][0] == 'V':
            seg[-1] = ('VV', 'aa'); ev['DAGGER_ALIF_ON_CARRIER'] += 1; i += 1; continue

        # --- و / ي ---
        if L in ('و', 'ي') and not mk:
            if (L == 'و' and prev_v == 'u') or (L == 'ي' and prev_v == 'i'):
                seg[-1] = ('VV', prev_v * 2); ev['MADD_WAW_YA'] += 1; i += 1; continue
            if prev_v == 'a':
                seg.append(('C', L)); ev['WAW_YA_AFTER_FATHA_AS_C'] += 1; i += 1; continue
            seg.append(('POISON', L)); ev['POISON_WAW_YA_UNRESOLVED'] += 1; i += 1; continue

        # --- ة ---
        if L == 'ة':
            seg.append(('TAA',))
            tw = tanwin_of(mk); v = vowel_of(mk)
            if tw: seg.append(('TANWIN', TANWIN[tw])); ev['TANWIN'] += 1
            elif v: seg.append(('V', SHORT[v]))
            elif SUKUN in mk: pass
            else: ev['POISON_UNMARKED'] += 1; seg.append(('POISON', L))
            i += 1; continue

        # --- صامت عادي ---
        if SHADDA in mk:
            seg.append(('C', L)); ev['SHADDA_SPLIT'] += 1
        seg.append(('C', L))
        tw = tanwin_of(mk); v = vowel_of(mk)
        if tw:
            seg.append(('TANWIN', TANWIN[tw])); ev['TANWIN'] += 1
        elif v and DAGGER_ALIF in mk and v == FATHA:
            seg.append(('VV', 'aa')); ev['DAGGER_ALIF'] += 1          # يَٰ / الرَّحْمَٰن: فتحة + خنجرية = مدّ
        elif v:
            seg.append(('V', SHORT[v]))
            if DAGGER_ALIF in mk:
                ev['DAGGER_ALIF_IGNORED_NON_FATHA'] += 1
        elif SUKUN in mk:
            pass
        elif DAGGER_ALIF in mk:
            seg.append(('VV', 'aa')); ev['DAGGER_ALIF'] += 1
        else:
            seg.append(('POISON', L)); ev['POISON_UNMARKED'] += 1
        i += 1
    return seg

# ---------- Stage 3: resolve junctions (ابتداء/وصل/وقف) ----------
def resolve(words_seg, raw_words, mode, ev):
    """
    mode='WASL_RUN' : النص سلسلة واحدة؛ ابتداء في أول كلمة فقط، وقف في آخرها فقط
    mode='WAQF_RUN' : كل كلمة مفردة: ابتداء في أولها، وقف في آخرها
    → list of per-word phoneme lists (C / V / VV), plus junction events
    """
    out = []
    N = len(words_seg)
    for wi, seg in enumerate(words_seg):
        seg = list(seg)
        initial = (mode == 'WAQF_RUN') or wi == 0
        final = (mode == 'WAQF_RUN') or wi == N - 1
        ph = []
        # --- بداية الكلمة ---
        k = 0
        while k < len(seg):
            s = seg[k]
            if s[0] == 'HW':
                if initial or (k > 0 and ph):          # ابتداء مطلق، أو همزة وصل بعد سابقة داخل الكلمة (فَاكْتُبُوهُ)
                    if k > 0 and ph:
                        ev['WASL_INTERNAL_AFTER_PROCLITIC'] += 1   # تُحذف
                    else:
                        nxt = seg[k + 1] if k + 1 < len(seg) else None
                        v = 'a' if (nxt and nxt[0] == 'C' and nxt[1] == 'ل') or \
                                   (nxt and nxt[0] == 'C' and k + 2 < len(seg) and seg[k + 2][0] == 'C' and seg[k + 1][1] == seg[k + 2][1]) \
                            else 'i'
                        ph += [('C', 'ء'), ('V', v)]
                        ev['HAMZAT_WASL_REALIZED_' + v] += 1
                else:
                    # وصل عبر حدّ كلمة: عالج نهاية الكلمة السابقة
                    prev = out[-1]
                    if prev and prev[-1][0] == 'VV':
                        prev[-1] = ('V', prev[-1][1][0]); ev['VV_SHORTENED_BEFORE_WASL'] += 1
                    elif prev and prev[-1][0] == 'C':
                        rw = raw_words[wi - 1]
                        if rw.endswith(DAMMA_BEFORE_WASL):
                            prev.append(('V', 'u')); ev['C_PLUS_DAMMA_BEFORE_WASL'] += 1
                        elif rw.endswith(FATHA_BEFORE_WASL):
                            prev.append(('V', 'a')); ev['C_PLUS_FATHA_BEFORE_WASL'] += 1
                        else:
                            prev.append(('V', 'i')); ev['C_PLUS_KASRA_BEFORE_WASL'] += 1
                    ev['HAMZAT_WASL_ELIDED'] += 1
                k += 1; continue
            if s[0] == 'TAA':
                tail_only_vowel = all(x[0] in ('V', 'TANWIN') for x in seg[k + 1:])
                if final and tail_only_vowel:
                    ph.append(('C', 'h')); ev['WAQF_TAA_TO_HA'] += 1
                else:
                    ph.append(('C', 't'))
                k += 1; continue
            if s[0] == 'TANWIN':
                if final and k == len(seg) - 1:
                    after_taa = (k >= 1 and seg[k - 1][0] == 'TAA')
                    if s[1] == 'a' and not after_taa:
                        ph.append(('VV', 'aa')); ev['WAQF_TANWIN_NASB_TO_ALIF'] += 1
                    elif after_taa:
                        ev['WAQF_TANWIN_DROPPED_AFTER_TAA'] += 1
                    else:
                        ev['WAQF_TANWIN_DROPPED'] += 1
                else:
                    ph += [('V', s[1]), ('C', 'ن')]
                k += 1; continue
            if s[0] == 'POISON':
                ph.append(s); k += 1; continue
            ph.append(s); k += 1
        # وقف: حذف الحركة القصيرة الأخيرة
        if final and ph and ph[-1][0] == 'V':
            ph.pop(); ev['WAQF_FINAL_VOWEL_DROPPED'] += 1
        out.append(ph)
    return out

# ---------- Stage 4: Syllabify (بالتعريف فقط) + Classify ----------
def syllabify(stream):
    """stream: list of ('C',x)/('V',x)/('VV',x)/('POISON',x) with ('#',wi) word markers.
       كل نواة تأخذ الصامت الذي قبلها مباشرة onset؛ ما بين نواتين من صوامت زائدة → coda السابقة."""
    sylls = []
    cur = None          # dict(onset=[], nuc=None, coda=[], words=set())
    pending_C = []      # صوامت لم تُسنَد بعد
    pending_words = set()
    cur_word = -1
    for item in stream:
        if item[0] == '#':
            cur_word = item[1]; pending_words = {cur_word}; continue
        if item[0] == 'POISON':
            # يُغلق كل شيء ويُسجَّل مقطع سُمّ
            if cur is not None:
                cur['coda'] += pending_C; cur['words'] |= pending_words; sylls.append(cur); cur = None
            sylls.append({'onset': [], 'nuc': None, 'coda': [], 'words': set(pending_words), 'poison': item[1]})
            pending_C = []; pending_words = set(); continue
        if item[0] == 'C':
            pending_C.append(item[1]); continue
        # نواة
        if pending_C:
            onset = [pending_C[-1]]; extra = pending_C[:-1]
        else:
            onset = []; extra = []
        if cur is not None:
            cur['coda'] += extra; sylls.append(cur)
        else:
            if extra:   # صوامت قبل أول نواة بلا مقطع سابق
                sylls.append({'onset': [], 'nuc': None, 'coda': extra, 'words': set(pending_words), 'poison': None})
        cur = {'onset': onset, 'nuc': item, 'coda': [], 'words': {cur_word}, 'poison': None}
        pending_C = []; pending_words = {cur_word}
    if cur is not None:
        cur['coda'] += pending_C; cur['words'] |= pending_words; sylls.append(cur)
    elif pending_C:
        sylls.append({'onset': [], 'nuc': None, 'coda': pending_C, 'words': set(pending_words), 'poison': None})
    return sylls

def classify(s):
    if s.get('poison') is not None:
        return 'POISON', 'DEFER:تشكيل_ناقص'
    if s['nuc'] is None:
        return 'OTHER', 'BLOCK:A1(صوامت_بلا_نواة)'
    pat = 'C' * len(s['onset']) + ('VV' if s['nuc'][0] == 'VV' else 'V') + 'C' * len(s['coda'])
    if pat in SIX:
        return pat, 'OK'
    if len(s['onset']) == 0:
        return pat, 'BLOCK:A1(لا_يُبتدأ_بساكن/بحركة)'
    if len(s['coda']) >= 3:
        return pat, 'BLOCK:A3+A2(أكثر_من_ثلاثة_سواكن)'
    return pat, 'BLOCK:?'

# ---------- rendering ----------
AR_V = {'a': FATHA, 'u': DAMMA, 'i': KASRA}
AR_MADD = {'aa': 'ا', 'uu': 'و', 'ii': 'ي'}
AR_C = {'h': 'ه', 't': 'ت'}
def render(s):
    if s.get('poison') is not None:
        return '⟪' + s['poison'] + '⟫'
    r = ''.join(AR_C.get(c, c) for c in s['onset'])
    if s['nuc'] is not None:
        if s['nuc'][0] == 'V':
            r += AR_V[s['nuc'][1]]
        else:
            r += AR_V[s['nuc'][1][0]] + AR_MADD[s['nuc'][1]]
    for c in s['coda']:
        r += AR_C.get(c, c) + SUKUN
    return r

# ---------- driver ----------
def run(text, mode):
    ev = Events()
    raw_words = text.split()
    segs = [cvmap(normalize(w, ev), ev) for w in raw_words]
    phon = resolve(segs, raw_words, mode, ev)
    stream = []
    for wi, ph in enumerate(phon):
        stream.append(('#', wi))
        stream += ph
    sylls = syllabify(stream)
    counts = Counter()
    rows = []
    others = []
    cv_line = []
    for s in sylls:
        pat, verdict = classify(s)
        counts[pat] += 1
        cv_line.append(pat)
        rows.append((render(s), pat, verdict, sorted(s['words'])))
        if verdict != 'OK':
            others.append((render(s), pat, verdict, [raw_words[w] for w in sorted(s['words'])]))
    return dict(mode=mode, counts=counts, rows=rows, others=others, events=ev,
                cv_line=cv_line, n_words=len(raw_words), n_syll=len(sylls), phon=phon, raw_words=raw_words)

def word_view(res):
    """عرض كل كلمة بمقاطعها (في WASL_RUN قد يمتد مقطع عبر حدّ كلمتين؛ يُعرَض مع الكلمة التي تحوي نواته)"""
    lines = []
    # إعادة بناء بحسب الكلمات: كل مقطع يُنسب لكلمة نواته (أول كلمة في words إن تعددت)
    by_word = {}
    for rend, pat, verdict, ws in res['rows']:
        key = ws[0] if ws else -1
        by_word.setdefault(key, []).append((rend, pat))
    for wi, w in enumerate(res['raw_words']):
        items = by_word.get(wi, [])
        lines.append(f"{w:<16} {' . '.join(r for r, _ in items):<40} {' '.join(p for _, p in items)}")
    return '\n'.join(lines)

def report(res):
    c = res['counts']
    n_ok = sum(c[k] for k in SIX)
    n_other = sum(v for k, v in c.items() if k not in SIX and k != 'POISON')
    n_poison = c.get('POISON', 0)
    out = []
    out.append(f"```\nMODE={res['mode']}\nWORDS={res['n_words']}\nSYLLABLES={res['n_syll']}")
    for k in SIX:
        out.append(f"{k}={c[k]}")
    out.append(f"SIX_TOTAL={n_ok}\nOTHER={n_other}\nPOISON={n_poison}")
    out.append("EVENTS:")
    for k, v in sorted(res['events'].items()):
        out.append(f"  {k}={v}")
    out.append("```")
    if res['others']:
        out.append("\nOTHER/POISON:")
        for rend, pat, verdict, ws in res['others']:
            out.append(f"  {rend}  {pat}  {verdict}  ← {' '.join(ws)}")
    return '\n'.join(out)

if __name__ == '__main__':
    text = open(sys.argv[1], encoding='utf-8').read().strip() if len(sys.argv) > 1 else sys.stdin.read().strip()
    for mode in ('WASL_RUN', 'WAQF_RUN'):
        res = run(text, mode)
        print(report(res))
        print()
        print(word_view(res))
        print('\n' + '=' * 80 + '\n')
