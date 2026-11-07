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
    return _nfc(''.join(L + ''.join(sorted(m)) for L, m in toks))


def _vowel(m):
    return next((v for v in SHORT if v in m), SUKUN if SUKUN in m else None)


def realize_lemma(root, form_class, hfn_form, _hollow=None):
    """→ dict(reconstructed_form, operations, covered, note, alternatives).
    الأجوف غير المعلّم في صيغة HFN (فَعَلَ والعين واوٌ أو ياء): البديلان، الصحيح العين (عَوِرَ) والمُعَلّ (قَالَ)، لا اختيار بينهما"""
    if _hollow is None and form_class == 'I' and len(root) == 3 and root[1] in 'وي' and 'أجوف' not in (hfn_form or ''):
        a = realize_lemma(root, form_class, hfn_form, _hollow=False)
        b = realize_lemma(root, form_class, hfn_form, _hollow=True)
        alts = [x for x in (a, b) if x['reconstructed_form']]
        return dict(a, alternatives=[dict(form=x['reconstructed_form'], operations=x['operations']) for x in alts])
    ops = []
    form = re.sub(r'\s*\(.*\)$', '', hfn_form or '')
    note = hfn_form or ''
    alts = form.split('/')
    pat = alts[0]
    rad = list(root)
    if not pat or len(rad) not in (3, 4):
        return dict(reconstructed_form=None, operations=[], covered=False, note='صيغةٌ أو جذرٌ خارج التغطية')
    n_l = pat.count('ل')
    out, k = [], 0
    for c in pat:
        if c == 'ف':
            out.append(rad[0])
        elif c == 'ع':
            out.append(rad[1])
        elif c == 'ل':
            if len(rad) == 4 and n_l == 2:
                out.append(rad[2 + k]); k += 1
            else:
                out.append(rad[-1])
        else:
            out.append(c)
    t = _toks(''.join(out))
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
        t = [x for x in t if x is not None]
    # الأجوف المعلّم
    if form_class == 'I' and ('أجوف' in note or _hollow) and len(t) == 3 and t[1][0] in 'وي' and FATHA in t[0][1]:
        t[1] = ['ا', set()]; ops.append('HOLLOW_AYN')
    # الإدغام: العين واللام من جنس واحد متحرّكتين في الآخر
    if len(t) >= 2 and t[-1][0] == t[-2][0] and _vowel(t[-2][1]) in SHORT and _vowel(t[-1][1]) in SHORT and \
            SHADDA not in t[-2][1] and len(rad) == 3 and rad[1] == rad[2]:          # لا في فَعَّلَ وتَفَعَّلَ (خَفَّفَ)
        v2 = _vowel(t[-2][1])
        if len(t) >= 3 and SUKUN in t[-3][1]:
            t[-3][1] = (t[-3][1] - {SUKUN}) | {v2}
        t[-1][1] = t[-1][1] | {SHADDA}
        del t[-2]
        ops.append('GEMINATE_MERGE')
    # اللام المعتلّة في آخر الماضي
    if len(rad) == 3 and rad[2] in 'وي' and t and t[-1][0] == rad[2] and len(t) >= 2:
        prev = _vowel(t[-2][1])
        if FATHA in t[-1][1] and prev == FATHA:
            t[-1] = ['ا' if rad[2] == 'و' or t[-2][0] == 'ي' else 'ى', set()]
            ops.append('WEAK_LAM')
        elif rad[2] == 'و' and prev == KASRA:
            t[-1][0] = 'ي'; ops.append('WEAK_LAM')
    # آخرٌ «ى» بعد ياء: ألف (أَحْيَى ← أَحْيَا)
    if len(t) >= 2 and t[-1][0] == 'ى' and t[-2][0] == 'ي':
        t[-1][0] = 'ا'; ops.append('WEAK_LAM')
    # كرسيّ الهمزة
    if any(L == 'ء' for L, _ in t):
        t = _hamza_seats(t); ops.append('HAMZA_SEAT')
    form_out = _text(t)
    return dict(reconstructed_form=form_out, operations=ops, covered=True, note=note,
                alternatives=[dict(form=form_out, operations=ops)])


def _hamza_seats(t):
    out = [list(x) for x in t]
    i = 0
    while i < len(out):
        L, m = out[i]
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
            if prev is None and out[i - 1][0] == 'ا' and own == FATHA:
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
        rec.update(status='NOT_COVERED', differences=[r['note']])
        return rec
    if policy != 'NFC_LITERAL':
        raise ValueError(policy)
    tgt = _text(_toks(target))
    alts = r.get('alternatives') or [dict(form=r['reconstructed_form'], operations=r['operations'])]
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
