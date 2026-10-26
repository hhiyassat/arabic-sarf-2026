#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
cv_syllabifier.py — محوّل CV رباعي الطبقات للعربية (وضع MEASURE)
    Normalize ∘ CVmap ∘ Syllabify ∘ Classify
لا تُطبَّق قوانين المقاطع كقيود؛ يُقطَّع بالتعريف فقط (كل نواة تأخذ الصامت الذي قبلها)
ثم يُعَدّ ما خرج. أي نوع خارج الستة يُبلَّغ OTHER مع المقدمة المخروقة.
النص يُعالَج كما هو: كل كلمة مستقلة، بلا وصل بين الكلمات ولا وقف في آخرها؛
والتنوين حركة واحدة من جنسه (نواته TV وتُعدّ V).
"""
import sys, re, json, hashlib
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

# قاموس مغلق: ألف محذوفة خطاً (تُدرَج قبل المعالجة)
LEXICAL_MADD = OrderedDict([
    ('ذَلِك', 'ذَالِك'),
    ('هَذَا', 'هَاذَا'),
    ('هَذِه', 'هَاذِه'),
    ('الرَّحْمَن', 'الرَّحْمَان'),
])

# لفظ الجلالة: اسم علم جامد لا تصريف له — يُعرَف كلمةً واحدة بما يتصل به من سوابق،
# ويُعطى صورة ثابتة واحدة (لَّاه بألف مدّ) بدل مطابقة أجزاء من الكلمة.
#   [ءَ][وَ|فَ][بِ|تَ|كَ] + (ال | لِ) + لَّ + ه + [حركة] + [مَّ]
#   ٱللَّه، لِلَّه، فَلِلَّه، بِٱللَّه، تَٱللَّه، وَٱللَّه، ءَآللَّه، ٱللَّهُمَّ — ولا يطابق ٱللَّهْو
_SHADDA_FATHA = '(?:\u0651\u064E?|\u064E\u0651|\u064E)?'   # علامات الاسم نفسه اختيارية: صورته ثابتة
DIVINE_NAME = re.compile(
    '^(?P<q>[ءأ]\u064E)?(?P<conj>[وف]\u064E)?(?P<prep>ب\u0650|ت\u064E|ك\u064E)?'
    '(?P<art>[اٱآ]\u064E?ل\u0652?|ل\u0650)'
    'ل' + _SHADDA_FATHA + '\u0670?ه'
    '(?P<tail>[\u064E\u064F\u0650\u0652]?(?:م(?:\u0651\u064E|\u064E\u0651|\u0651))?)$')

def divine_name(word):
    """→ الصورة الثابتة لِلفظ الجلالة، أو None إن لم تكن الكلمة لفظَ الجلالة"""
    m = DIVINE_NAME.match(word)
    if not m:
        return None
    pre = (m['q'] or '') + (m['conj'] or '') + (m['prep'] or '')
    core = 'لَّاه' + m['tail']
    if m['art'].startswith('ل'):                  # لِلَّه: لام الجر + الاسم، سقطت همزة الوصل ولام التعريف
        return pre + 'لِ' + core
    if m['q']:                                    # ءَآللَّه: همزة الاستفهام + همزة الوصل ⇒ مدّ، ولام مشددة
        return pre + 'ا' + core
    return pre + 'ال' + core                      # ٱللَّه: ال + لام مشددة (شمسية)

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
    fixed = divine_name(word)
    if fixed is not None:
        word = fixed
        ev['DIVINE_NAME'] += 1
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

        # --- ى متحركة أو مشددة أو ساكنة (شَىْءٍ): ياء صامتة لا ألف مقصورة (إِلَىَّ، عَلَىَّ = إلى/على + ياء المتكلم؛ شَىْءٍ = ياء لين) ---
        if L == 'ى' and (vowel_of(mk) or SHADDA in mk or SUKUN in mk):
            L = 'ي'; ev['ALIF_MAQSURA_AS_YA'] += 1
        # --- ى بعد كسرة: ياء مدّ في الرسم العثماني (فِى، رَبِّى، إِنِّى) ---
        elif L == 'ى' and not mk and prev_v == 'i' and seg and seg[-1][0] == 'V':
            seg[-1] = ('VV', 'ii'); ev['MADD_YA_AS_ALIF_MAQSURA'] += 1; i += 1; continue

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
        if SHADDA in mk and i == 0:
            ev['INITIAL_SHADDA_IGNORED'] += 1      # شدة أول الكلمة إدغام من الكلمة السابقة: ظاهرة عابرة للحدود
        elif SHADDA in mk:
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

# ---------- Stage 3: resolve (كل كلمة كما كُتبت) ----------
def resolve(words_seg, ev):
    """
    النص كما هو: كل كلمة مستقلة، بلا وصل بين الكلمات ولا وقف في آخرها.
    - همزة الوصل في أول الكلمة تُنطق ابتداءً (ءَ مع لام التعريف والمشدّد، وءِ في غيرهما)،
      وبعد سابقة داخل الكلمة لا تُنطق (فَٱكْتُبُوهُ)
    - التاء المربوطة تبقى «ة» صامتاً
    - التنوين حركة واحدة من جنسه (نواة TV)، بلا نون مضافة
    → list of per-word phoneme lists
    """
    out = []
    for seg in words_seg:
        ph = []
        for k, s in enumerate(seg):
            if s[0] == 'HW':
                if ph:
                    ev['WASL_INTERNAL_AFTER_PROCLITIC'] += 1          # لا تُنطق بعد سابقة
                else:
                    nxt = seg[k + 1] if k + 1 < len(seg) else None
                    third_u = (k + 3 < len(seg) and seg[k + 1][0] == 'C' and seg[k + 2][0] == 'C'
                               and seg[k + 3][0] == 'V' and seg[k + 3][1] == 'u')
                    if (nxt and nxt[0] == 'C' and nxt[1] == 'ل') or \
                            (nxt and nxt[0] == 'C' and k + 2 < len(seg) and seg[k + 2][0] == 'C' and seg[k + 1][1] == seg[k + 2][1]):
                        v = 'a'                    # لام التعريف
                    elif third_u:
                        v = 'u'                    # الثالث مضموم: اُكْتُبْ، اُخْرُجْ
                    else:
                        v = 'i'
                    ph += [('C', 'ء'), ('V', v)]
                    ev['HAMZAT_WASL_REALIZED_' + v] += 1
            elif s[0] == 'TAA':
                ph.append(('C', 'ة'))
            elif s[0] == 'TANWIN':
                ph.append(('TV', s[1]))
            else:
                ph.append(s)
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
            if cur is not None and pending_C:       # لا يعبر مقطع حدّ الكلمة
                cur['coda'] += pending_C; pending_C = []
            elif pending_C:
                sylls.append({'onset': [], 'nuc': None, 'coda': pending_C, 'words': set(pending_words), 'poison': None})
                pending_C = []
            if cur is not None:
                sylls.append(cur); cur = None
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
AR_C = {}
AR_TANWIN = {'a': FATHATAN, 'u': DAMMATAN, 'i': KASRATAN}
def render(s):
    if s.get('poison') is not None:
        return '⟪' + s['poison'] + '⟫'
    r = ''.join(AR_C.get(c, c) for c in s['onset'])
    if s['nuc'] is not None:
        if s['nuc'][0] == 'V':
            r += AR_V[s['nuc'][1]]
        elif s['nuc'][0] == 'TV':
            r += AR_TANWIN[s['nuc'][1]]
        else:
            r += AR_V[s['nuc'][1][0]] + AR_MADD[s['nuc'][1]]
    for c in s['coda']:
        r += AR_C.get(c, c) + SUKUN
    return r

# ---------- driver ----------
def run(text):
    ev = Events()
    raw_words = text.split()
    segs = [cvmap(normalize(w, ev), ev) for w in raw_words]
    phon = resolve(segs, ev)
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
    return dict(counts=counts, rows=rows, others=others, events=ev,
                cv_line=cv_line, n_words=len(raw_words), n_syll=len(sylls), phon=phon, raw_words=raw_words)

def word_view(res):
    """عرض كل كلمة بمقاطعها"""
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
    out.append(f"```\nWORDS={res['n_words']}\nSYLLABLES={res['n_syll']}")
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
    res = run(text)
    print(report(res))
    print()
    print(word_view(res))
