# -*- coding: utf-8 -*-
"""sarf/realize.py — التحقيق العكسي للفعل (AR02 §١٠): بناء اللمّة من الجذر وصيغة الوزن بعملياتٍ مسمّاة، ثم مقارنتها بالهدف.

    realize_lemma(root, form_class, hfn_form) → dict(reconstructed_form, operations, covered, note)
    verify(root, form_class, hfn_form, target, policy='NFC_LITERAL') → سجلّ التحقيق

العمليات (كلٌّ بشرطها، ولا تُطبَّق إلا حيث تنطبق):
  SUBSTITUTE           الأصول في مواضع ف ع ل من صيغة الوزن (الرباعي: لامان)
  VIII_TA_TO_TA'/DAL   افتعل: التاء طاءً بعد ص ض ط ظ، ودالاً بعد د ذ ز، وتُدغم في الدال والذال الدالَ (ادَّكَرَ)؛ والفاء الواو والياء تاءً مدغمة
  GEMINATE_MERGE       العين واللام من جنسٍ واحد متحرّكتين في آخر الماضي: تُسكَّن الأولى وتُدغم، وتنتقل حركتها إلى ساكنٍ قبلها
  WEAK_LAM             اللام واوٌ أو ياءٌ مفتوحة بعد فتح في آخر الماضي: ألفاً (دَعَا) أو ياءً مقصورة (رَمَى)، وبعد ياءٍ ألفاً (أَحْيَا)؛
                       والواو بعد كسرٍ ياءً (رَضِيَ)
  HOLLOW_AYN           الأجوف المعلّم في صيغة HFN: العين ألفاً بين فتحتين (قَالَ)
  HAMZA_SEAT           كرسيّ الهمزة بالقاعدة الإملائية: أولاً بحركتها، ووسطاً وآخراً بأقوى الحركتين، و«ءَا» أولاً آ
والتحقيق شرطُ اتساقٍ صرفي، لا إثباتٌ للصنف ولا للمعنى ولا للاختيار.
"""
import re, unicodedata
from .chars import FATHA, DAMMA, KASRA, SUKUN, SHADDA, letters

SHORT = (FATHA, DAMMA, KASRA)


def _nfc(s):
    return unicodedata.normalize('NFC', s or '')


def _toks(s):
    return [[L, set(m)] for L, m in letters(s)]


def _text(toks):
    return _nfc(''.join(x[0] + ''.join(sorted(x[1])) for x in toks))


def _vowel(m):
    return next((v for v in SHORT if v in m), SUKUN if SUKUN in m else None)


HOLLOW_CLASSES = ('I', 'IV', 'VII', 'VIII', 'X')


def realize_lemma(root, form_class, hfn_form, _hollow=None):
    """→ dict(reconstructed_form, operations, covered, note, alternatives).
    AR03 §٧: تُجرَّب البدائل المرخّصة كلها لا أولها — كل صيغةٍ مفصولة بـ«/» في HFN (فَعَلَ/فَعِلَ)، والأجوف غير المعلّم صحيحاً ومُعَلّاً
    في الأبواب التي يُعَلّ فيها (I، IV، VII، VIII، X)، واللفيف المقرون اليائي فكّاً وإدغاماً (حَيِيَ/حَيَّ)، وافتعل مهموز الفاء
    قياساً وإبدالاً (ائْتَمَنَ/اتَّخَذَ). ولا اختيار بين البدائل: الاختيار للمطابقة مع الهدف المكتوب"""
    form = re.sub(r'\s*\(.*\)$', '', hfn_form or '')
    note = hfn_form or ''
    rad = list(root)
    pats = [x for x in form.split('/') if x]
    if not pats or len(rad) not in (3, 4):
        return dict(reconstructed_form=None, operations=[], covered=False, note='صيغةٌ أو جذرٌ خارج التغطية', alternatives=[],
                    not_covered_reason='PATTERN_OR_ROOT_OUT_OF_SCOPE')
    if _hollow is not None:
        hollow_v = [_hollow]
    elif 'أجوف' in note:
        hollow_v = [True] if form_class in HOLLOW_CLASSES else [False]     # فَعَّلَ وتَفَعَّلَ وفَاعَلَ الأجوف: العين لا تُعَلّ (بَيَّنَ)
    elif form_class in HOLLOW_CLASSES and len(rad) == 3 and rad[1] in 'وي' and rad[2] not in 'وي':
        hollow_v = [False, True]
    else:
        hollow_v = [False]
    merge_v = [False, True] if form_class == 'I' and len(rad) == 3 and rad[1] == rad[2] == 'ي' else [False]
    hamza_v = [False, True] if form_class == 'VIII' and rad[0] == 'ء' else [False]
    alts = []
    for pat in pats:
        for h in hollow_v:
            for mg in merge_v:
                for hz in hamza_v:
                    r = _realize_one(rad, form_class, pat, note, h, mg, hz)
                    if r and all(x['form'] != r['form'] for x in alts):
                        alts.append(r)
    if not alts:
        return dict(reconstructed_form=None, operations=[], covered=False, note=note, alternatives=[],
                    not_covered_reason='NO_RULE_APPLIES')
    return dict(reconstructed_form=alts[0]['form'], operations=alts[0]['operations'], covered=True, note=note, alternatives=alts)


def _realize_one(rad, form_class, pat, note, hollow, merge_weak, hamza_assim):
    ops = []
    if 'ع' not in pat:
        hollow = False                     # الصيغة في HFN متحققةٌ بإعلالها (أَفَالَ، اسْتَفَالَ): لا عين تُعَلّ
    n_l = pat.count('ل')
    out, roles, k = [], [], 0
    for c in pat:
        if c == 'ف':
            out.append(rad[0]); roles.append('F')
        elif c == 'ع':
            out.append(rad[1]); roles.append('A')
        elif c == 'ل':
            if len(rad) == 4 and n_l == 2:
                out.append(rad[2 + k]); k += 1
            else:
                out.append(rad[-1])
            roles.append('L')
        else:
            out.append(c); roles.append(None)
    t = _toks(''.join(out))
    # الأدوار بحسب الحروف (الحركات لا تُعدّ حروفاً في letters)
    base = [c for c in pat if c not in (FATHA, DAMMA, KASRA, SUKUN, SHADDA)]
    rl = [r for c, r in zip(out, roles) if c not in (FATHA, DAMMA, KASRA, SUKUN, SHADDA)]
    if len(rl) == len(t):
        for x, r in zip(t, rl):
            x.append(r)
    else:
        for x in t:
            x.append(None)
    ops.append('SUBSTITUTE')
    # افتعل: التاء بعد الفاء
    if form_class == 'VIII' and len(t) > 2 and t[0][0] == 'ا' and t[2][0] == 'ت':
        fa = t[1][0]
        if fa == 'ط':
            t[1] = None; t[2][0] = 'ط'; t[2][1] = t[2][1] | {SHADDA}; ops.append("VIII_TA_TO_TA'_ASSIMILATED")   # اطَّلَعَ
        elif fa in 'صضظ':
            t[2][0] = 'ط'; ops.append("VIII_TA_TO_TA'")
        elif fa in 'دذ':
            t[2][0] = 'د'; t[1] = None; t[2][1] = t[2][1] | {SHADDA}; ops.append('VIII_TA_TO_DAL_ASSIMILATED')
        elif fa == 'ز':
            t[2][0] = 'د'; ops.append('VIII_TA_TO_DAL')
        elif fa in 'وي' or fa == 'ت':
            t[1] = None; t[2][1] = t[2][1] | {SHADDA}; ops.append('VIII_FA_ASSIMILATED_TO_TA')
        elif fa == 'ء' and hamza_assim:
            t[1] = None; t[2][1] = t[2][1] | {SHADDA}; ops.append('VIII_HAMZA_FA_ASSIMILATED_TO_TA')   # اتَّخَذَ
        t = [x for x in t if x is not None]
    # الأجوف: العين المتحرّكة ألفاً — في الثلاثي بين فتحتين (قَالَ)، وفي المزيد تنقل فتحتها إلى الساكن قبلها (أَقَامَ، اسْتَقَامَ)
    # أو تُقلب بعد فتح (انْقَادَ، اخْتَارَ)
    if hollow:
        ai = next((i for i, x in enumerate(t) if x[2] == 'A'), None)
        if ai is None or ai == 0 or t[ai][0] not in 'وي' or _vowel(t[ai][1]) not in SHORT or SHADDA in t[ai][1] or \
                (form_class != 'I' and FATHA not in t[ai][1]):          # الثلاثي بأي حركة (قَالَ، خَافَ)، والمزيد بالفتح
            return None
        if form_class == 'I':
            if FATHA not in t[ai - 1][1]:
                return None
            t[ai] = ['ا', set(), 'A']; ops.append('HOLLOW_AYN')
        else:
            if SUKUN in t[ai - 1][1]:
                t[ai - 1][1] = (t[ai - 1][1] - {SUKUN}) | {FATHA}
            elif FATHA not in t[ai - 1][1]:
                return None
            t[ai] = ['ا', set(), 'A']; ops.append('HOLLOW_AYN_DERIVED')
    # الإدغام: العين واللام من جنس واحد متحرّكتين في الآخر (لا في اللفيف المقرون إلا اليائي بديلاً: حَيَّ)
    weak_pair = len(rad) == 3 and rad[1] == rad[2] and rad[2] in 'وي'
    if len(t) >= 2 and t[-1][0] == t[-2][0] and _vowel(t[-2][1]) in SHORT and _vowel(t[-1][1]) in SHORT and \
            SHADDA not in t[-2][1] and len(rad) == 3 and rad[1] == rad[2] and (not weak_pair or merge_weak):
        v2 = _vowel(t[-2][1])
        if len(t) >= 3 and SUKUN in t[-3][1]:
            t[-3][1] = (t[-3][1] - {SUKUN}) | {v2}
        t[-1][1] = t[-1][1] | {SHADDA}
        del t[-2]
        ops.append('GEMINATE_MERGE')
    elif merge_weak:
        return None
    # اللام المعتلّة في آخر الماضي: مفتوحةً بعد فتح تُكتب ألفاً في الثلاثي الواوي (دَعَا) وبعد الياء (أَحْيَا)، وياءً مقصورةً فيما
    # سوى ذلك (رَمَى، أَعْطَى، سَمَّى، ادَّعَى)؛ والواو بعد كسرٍ ياءً (رَضِيَ)
    if len(rad) == 3 and rad[2] in 'وي' and t and t[-1][0] == rad[2] and len(t) >= 2 and SHADDA not in t[-1][1]:
        prev = _vowel(t[-2][1])
        if FATHA in t[-1][1] and prev == FATHA:
            alif = (rad[2] == 'و' and form_class == 'I' and len(t) == 3) or t[-2][0] == 'ي'
            t[-1] = ['ا' if alif else 'ى', set(), 'L']
            ops.append('WEAK_LAM')
        elif rad[2] == 'و' and prev == KASRA:
            t[-1][0] = 'ي'; ops.append('WEAK_LAM')
    # «ى» بعد ياءٍ تُكتب ألفاً (أَحْيَا، اسْتَحْيَا) — ولو جاءت الصيغة في HFN متحققةً بالياء المقصورة (أَفْعَى)
    if len(t) >= 2 and t[-1][0] == 'ى' and t[-2][0] == 'ي':
        t[-1][0] = 'ا'; ops.append('WEAK_LAM')
    # كرسيّ الهمزة
    if any(x[0] == 'ء' for x in t):
        t = _hamza_seats(t); ops.append('HAMZA_SEAT')
    return dict(form=_text(t), operations=ops)


def _hamza_seats(t):
    out = [list(x) for x in t]
    i = 0
    while i < len(out):
        L, m = out[i][0], out[i][1]
        if L != 'ء':
            i += 1
            continue
        own = _vowel(m)
        prev = _vowel(out[i - 1][1]) if i > 0 else None
        nxt = out[i + 1] if i + 1 < len(out) else None
        if i == 1 and out[0][0] == 'أ' and FATHA in out[0][1] and own == SUKUN:
            out[0] = ['آ', set()]; del out[1]                   # أَأْ ← آ (آمَنَ، آتَى)
            continue
        if i > 0 and own == FATHA and nxt is not None and nxt[0] == 'ا' and not nxt[1]:
            out[i] = ['آ', set()]; del out[i + 1]               # ءَا وسطاً وآخراً ← آ (فَآ)
            i += 1
            continue
        if i == 0:
            if own == FATHA and nxt is not None and nxt[0] == 'ء' and SUKUN in nxt[1]:
                out[0] = ['آ', set()]; del out[1]               # أَءْ ← آ (آمَنَ)
            elif own == FATHA and nxt is not None and nxt[0] == 'ا' and not nxt[1]:
                out[0] = ['آ', set()]; del out[1]               # ءَا ← آ (آخَذَ)
            else:
                out[0][0] = 'إ' if own == KASRA else 'أ'
        else:
            if i == 1 and out[0][0] == 'ا' and not out[0][1] and own == SUKUN:
                out[i][0] = 'ئ'                                 # ساكنةٌ بعد همزة الوصل في الماضي المزيد: الوصل مكسور (ائْتَمَنَ)
            elif prev is None and out[i - 1][0] == 'ا' and own == FATHA:
                pass                                            # بعد ألفٍ ساكنة مفتوحةً: على السطر (سَاءَلَ)
            else:
                cand = [v for v in (own, prev) if v in SHORT]
                seat = 'ئ' if KASRA in cand or (out[i - 1][0] == 'ي' and own != SUKUN) else 'ؤ' if DAMMA in cand else 'أ' if FATHA in cand else 'ء'
                out[i][0] = seat
        i += 1
    return out


def verify(root, form_class, hfn_form, target, policy='NFC_LITERAL'):
    r = realize_lemma(root, form_class, hfn_form)
    rec = dict(reconstruction_target=target, reconstructed_form=r['reconstructed_form'], comparison_policy=policy,
               operations=r['operations'], matched=None, differences=[], status=None)
    if not r['covered'] or not r['reconstructed_form']:
        rec.update(status='NOT_COVERED', matched=False, differences=[r['note']], not_covered_reason=r.get('not_covered_reason'))
        return rec
    if policy != 'NFC_LITERAL':
        raise ValueError(policy)
    tgt = _text(_toks(target))
    alts = r['alternatives']
    hit = next((x for x in alts if x['form'] == tgt), None)
    if hit:
        rec.update(matched=True, status='MATCHED', reconstructed_form=hit['form'], operations=hit['operations'],
                   alternatives=[x['form'] for x in alts])
        return rec
    # الفرق في كرسيّ الهمزة وحده: حالةٌ مسمّاة لا مطابقة (الهدف في HFN v36 بهمزةٍ بلا كرسيّ، كما صحّحه MORPH_TESTSET_v3)
    seatless = lambda x: re.sub('[أإؤئ]', 'ء', x)
    seat = next((x for x in alts if seatless(x['form']) == seatless(tgt)), None)
    a, b = _toks(alts[0]['form']), _toks(tgt)
    n = max(len(a), len(b))
    diffs = [dict(position=i, reconstructed=(a[i][0] + ''.join(sorted(a[i][1]))) if i < len(a) else None,
                  target=(b[i][0] + ''.join(sorted(b[i][1]))) if i < len(b) else None)
             for i in range(n) if i >= len(a) or i >= len(b) or a[i][0] != b[i][0] or a[i][1] != b[i][1]]
    rec.update(matched=False, status='MISMATCH_HAMZA_SEAT_ONLY' if seat else 'MISMATCH', differences=diffs,
               alternatives=[x['form'] for x in alts])
    return rec
