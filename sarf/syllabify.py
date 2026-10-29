# -*- coding: utf-8 -*-
"""
sarf.syllabify — محوّل CV رباعي الطبقات للعربية (وضع MEASURE)
    Normalize ∘ CVmap ∘ Syllabify ∘ Classify
لا تُطبَّق قوانين المقاطع كقيود؛ يُقطَّع بالتعريف فقط (كل نواة تأخذ الصامت الذي قبلها)
ثم يُعَدّ ما خرج. أي نوع خارج الستة يُبلَّغ OTHER مع المقدمة المخروقة.
النص يُعالَج كما هو: كل كلمة مستقلة، بلا وصل بين الكلمات ولا وقف في آخرها؛
والتنوين حركة واحدة من جنسه (نواته TV وتُعدّ V).
لفظ الجلالة لا يُقطَّع (sarf.divine).
"""
from collections import Counter

from .chars import (FATHA, DAMMA, KASRA, SUKUN, SHADDA, FATHATAN, DAMMATAN, KASRATAN, mudgham,
                    DAGGER_ALIF, vowel_of, tanwin_of)
from .normalize import normalize
from .divine import divine_name

SHORT = {FATHA: 'a', DAMMA: 'u', KASRA: 'i'}
TANWIN = {FATHATAN: 'a', DAMMATAN: 'u', KASRATAN: 'i'}
SOLAR = set('تثدذرزسشصضطظلن')
PROCLITIC_FATHA = set('وف')            # وَ / فَ قبل همزة الوصل

SIX = ['CV', 'CVV', 'CVC', 'CVVC', 'CVCC', 'CVVCC']

class Events(Counter):
    pass

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
                seg[-1] = ('HW', 'al')                            # همزة وصل أل (تُفتح ابتداءً)
                ev['SOLAR_LAM_DELETED'] += 1; i += 1; continue   # الشمسية: اللام محذوفة والحرف مشدد
            seg.append(('POISON', L)); ev['POISON_BARE_LAM'] += 1; i += 1; continue
        if L == 'ل' and not mk and nxt is not None and SHADDA in nxt[1] and nxt[0] in SOLAR \
                and i >= 1 and toks[i - 1][0] == 'ل':
            ev['SOLAR_LAM_DELETED'] += 1; i += 1; continue       # لِلشَّهَادَةِ
        # المدغم إدغاماً تامّاً في الرسم: عارٍ قبل مشدَّد (أَرَدتُّمۡ، يُوَجِّههُّ، بِأَييِّكُمُ): لا يُقطَّع
        if mudgham([(x, set(y)) for x, y in toks], i):
            ev['MUDGHAM_DELETED'] += 1; i += 1; continue

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
        elif nxt is not None and nxt[0] not in 'اى':
            ev['BARE_AS_SUKUN'] += 1        # العاري قبل حرفٍ غير مشدَّد ساكنٌ كما كُتب (أَحَطتُ، بَسَطتَ)
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
                    if s == ('HW', 'al') or (nxt and nxt[0] == 'C' and nxt[1] == 'ل'):
                        v = 'a'                    # لام التعريف (القمرية، أو الشمسية المدغمة)
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
    divine = {i for i, w in enumerate(raw_words) if divine_name(w) is not None}
    ev['DIVINE_NAME'] += len(divine)
    segs = [[] if i in divine else cvmap(normalize(w, ev), ev) for i, w in enumerate(raw_words)]
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
    return dict(counts=counts, rows=rows, others=others, events=ev, divine_words=sorted(divine),
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
        if wi in res.get('divine_words', ()):
            lines.append(f"{w:<16} لفظ الجلالة (لا يُقطَّع)")
            continue
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
