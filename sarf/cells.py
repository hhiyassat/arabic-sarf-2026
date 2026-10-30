# -*- coding: utf-8 -*-
"""
sarf.cells — الخلايا من الرسم، ورخصة بناء الاسم (مشتركٌ بين المقشِّر والجبر):
  - cells_of: خلايا الوحدة ⟨C, H, L, O⟩ من رسمها المطبَّع
  - lex_index: المصدر واسما الفاعل والمفعول من lexical_units.csv في HFN
  - participle_analyses: اسما الفاعل والمفعول قياساً بقوالبهما، مرخَّصين بحدثٍ أو جذرٍ في HFN
  - sibawayh_analyses: أبنية الاسم عند سيبويه، وجذرها في HFN
"""
from dataclasses import dataclass, field
from functools import lru_cache

from .chars import (FATHA, DAMMA, KASRA, SUKUN, SHADDA, FATHATAN, DAMMATAN, KASRATAN,
                    DAGGER_ALIF, letters, mudgham)

H_OF = {FATHA: 'a', DAMMA: 'u', KASRA: 'i', FATHATAN: 'a', DAMMATAN: 'u', KASRATAN: 'i'}
MADD_OF = {'a': 'اى', 'u': 'و', 'i': 'ي'}
HAMZA = {'أ': 'ء', 'إ': 'ء', 'ؤ': 'ء', 'ئ': 'ء', 'ء': 'ء'}
# ---------- الخلية ----------
@dataclass
class Cell:
    id: str
    C: str            # الصامت (الهمزات موحَّدة ء)
    H: str            # a / u / i / ∅
    L: int = 1        # 2: بعدها حرف مدّ من جنسها
    O: dict = field(default_factory=dict)    # tok: موضع الرسم، glyph، role، silent: [مواضع لا تُنطق]

    def key(self):
        return (self.C, self.H, self.L)

    def show(self):
        return f"⟨{self.C},{self.H}{'ː' if self.L == 2 else ''}⟩"


# ---------- المستوى 0: الخلايا من الرسم ----------
def cells_of(text, base_id, wasl_vowel=None):
    """خلايا الوحدة من رسمها المطبَّع، ومعها كل حرفٍ لا يُنطق في O['silent'] لخليةٍ مجاورة.
    → (الخلايا، رموز الرسم [(الحرف، العلامات)])"""
    toks = letters(text)
    out = []
    pending_silent = []
    for j, (L, m) in enumerate(toks):
        prev = out[-1] if out else None
        nxt = toks[j + 1] if j + 1 < len(toks) else None
        role = None
        # همزة الوصل أول الوحدة: تُنطق ابتداءً (اصطلاح المقطِّع: كل خانة تبدأ بما يُبتدأ به)
        if L == 'ا' and j == 0 and not m and nxt is not None:
            v = wasl_vowel or ('a' if nxt[0] == 'ل' else 'u' if len(toks) > 2 and DAMMA in toks[2][1] else 'i')
            out.append(Cell(f'{base_id}.{len(out)}', 'ء', v, 1, dict(tok=[j], glyph='ا', role='همزة وصل')))
            continue
        if L == 'آ':
            out.append(Cell(f'{base_id}.{len(out)}', 'ء', 'a', 2, dict(tok=[j], glyph=L, role='همزة ومدّة')))
            continue
        # ألف الوصل بعد سابقةٍ من حرف واحد (لَّٱصۡطَفَىٰ، وَّٱسۡتَغۡنَى): لا تُنطق، وما بعدها ساكن
        if L == 'ا' and not m and len(out) == 1 and out[0].C in 'لوفبك' and out[0].H == 'a' and \
                nxt is not None and SUKUN in nxt[1]:
            prev.O.setdefault('silent', []).append((j, 'ألف وصل بعد السابقة')); prev.O['tok'].append(j)
            continue
        # حرف المد: يُطيل حركة ما قبله (الألف بعد الفتح، والواو بعد الضم، والياء بعد الكسر)
        if not m and prev is not None and prev.L == 1 and not prev.O.get('tanwin') and \
                prev.H in MADD_OF and L in MADD_OF[prev.H]:
            prev.L = 2
            prev.O['tok'].append(j); prev.O['madd'] = L
            continue
        # ما لا يُنطق: الألف الفارقة، وألف تنوين النصب، والحرف العاري قبل المشدَّد (مدغمٌ تامّاً في الرسم)
        is_mudgham = mudgham([(x, set(y)) for x, y in toks], j)
        if not m and (L in 'اى' or L == 'ل' and nxt is not None and SHADDA in nxt[1]) or is_mudgham:
            why = ('لام شمسية' if L == 'ل' else 'ياء زائدة رسماً') if L not in 'اى' else \
                'ألف بعد التنوين' if prev is not None and prev.O.get('tanwin') else 'ألف لا تُنطق'
            if prev is not None:
                prev.O.setdefault('silent', []).append((j, why)); prev.O['tok'].append(j)
            else:
                pending_silent.append((j, why))
            continue
        # الواو أو الياء تحمل الخنجرية بلا حركة: كرسيٌّ للألف (ٱلصَّلَوٰةَ = صَلَاة): يُطيل ما قبله ولا يُنطق صامتاً
        if DAGGER_ALIF in m and not m & {FATHA, DAMMA, KASRA, SUKUN, SHADDA} and L in 'وي' and \
                prev is not None and prev.H == 'a':
            prev.L = 2
            prev.O['tok'].append(j); prev.O['madd'] = L + 'ٰ'
            continue
        C = HAMZA.get(L, L)
        H = next((H_OF[x] for x in (FATHA, DAMMA, KASRA, FATHATAN, DAMMATAN, KASRATAN) if x in m), '∅')
        tanwin = bool(m & {FATHATAN, DAMMATAN, KASRATAN})
        if SHADDA in m and out:
            out.append(Cell(f'{base_id}.{len(out)}', C, '∅', 1, dict(tok=[j], glyph=L, role='شدة: الأول')))
            role = 'شدة: الثاني'
        elif SHADDA in m:
            role = 'شدة أول الوحدة: لا تُكرَّر'
        c = Cell(f'{base_id}.{len(out)}', C, H, 1, dict(tok=[j], glyph=L, role=role, tanwin=tanwin))
        if DAGGER_ALIF in m:
            c.H, c.L = 'a', 2
            c.O['madd'] = 'ٰ'
        if pending_silent:
            c.O['silent'] = pending_silent; c.O['tok'] = [s for s, _ in pending_silent] + c.O['tok']
            pending_silent = []
        out.append(c)
    if pending_silent:
        # حرفٌ لا يُنطق ولا خلية في وحدته (ى وحدها بعد تنوينٍ في الوحدة السابقة): يُحفظ وقوعاً بلا خلية
        cells_of.orphans = pending_silent
    else:
        cells_of.orphans = []
    return out, toks


# ---------- البناء المعجمي المرخَّص للاسم: المصدر واسم الفاعل واسم المفعول من HFN ----------
_LEX = None
NOUN_POS = ('مصدر', 'اسم فاعل', 'اسم مفعول')


def _lex_key(t):
    """مفتاح المطابقة: الحروف والحركات بلا علامة الإعراب الأخيرة (ولا ألف تنوين النصب)، والهمزات موحَّدة،
    والخنجرية ألف"""
    import re
    t = re.sub('[\u06D6-\u06ED\u0640\u0653]', '', t).replace('\u0670', 'ا')
    toks = letters(t)
    if toks and toks[-1][0] in 'اى' and not toks[-1][1] and len(toks) > 1 and toks[-2][1] & {FATHATAN}:
        toks = toks[:-1]
    out = []
    for i, (L, m) in enumerate(toks):
        m = set(m) - {SUKUN}
        if i == len(toks) - 1:
            m -= {FATHA, DAMMA, KASRA, FATHATAN, DAMMATAN, KASRATAN}
        out.append(HAMZA.get(L, L) + ''.join(sorted(m)))
    return ''.join(out)


def lex_index():
    """مفتاح الاسم ← [(الجذر، النوع، الوزن، المعرِّف)] من lexical_units.csv في HFN"""
    global _LEX
    if _LEX is None:
        import csv, os
        from .root import hfn
        _LEX = {}
        H = hfn()
        if H.path and os.path.exists(os.path.join(H.path, 'lexical_units.csv')):
            ev_root = {}
            for e in csv.DictReader(open(os.path.join(H.path, 'events.csv'), encoding='utf-8')):
                ev_root[e['event_id']] = e['root_K']
            for x in csv.DictReader(open(os.path.join(H.path, 'lexical_units.csv'), encoding='utf-8')):
                if x['pos_ar'] in NOUN_POS and x['event_id'] in ev_root:
                    _LEX.setdefault(_lex_key(x['lemma']), []).append(
                        (ev_root[x['event_id']], x['pos_ar'], x['pattern'], x['lu_id'], x['lemma']))
    return _LEX


# ---------- اسما الفاعل والمفعول قياساً: Realize(R, P) مرخَّصاً بحدث (R، الوزن) في HFN ----------
# كل عنصر: (الصامت أو Rk، الحركة أو *، الطول أو *)؛ والأخير حركته حركة الإعراب
def _t(spec):
    out = []
    for x in spec.split():
        C, H, L = x.split(':')
        out.append((C, H, int(L) if L != '*' else '*'))
    return out


PARTICIPLES = {
    ('I', 'فاعل'): _t('R1:a:2 R2:i:1 R3:*:*'),
    ('I', 'مفعول'): _t('م:a:1 R1:∅:1 R2:u:2 R3:*:*'),
    ('II', 'فاعل'): _t('م:u:1 R1:a:1 R2:∅:1 R2:i:1 R3:*:*'),
    ('II', 'مفعول'): _t('م:u:1 R1:a:1 R2:∅:1 R2:a:1 R3:*:*'),
    ('III', 'فاعل'): _t('م:u:1 R1:a:2 R2:i:1 R3:*:*'),
    ('III', 'مفعول'): _t('م:u:1 R1:a:2 R2:a:1 R3:*:*'),
    ('IV', 'فاعل'): _t('م:u:1 R1:∅:1 R2:i:1 R3:*:*'),
    ('IV', 'مفعول'): _t('م:u:1 R1:∅:1 R2:a:1 R3:*:*'),
    ('V', 'فاعل'): _t('م:u:1 ت:a:1 R1:a:1 R2:∅:1 R2:i:1 R3:*:*'),
    ('VI', 'فاعل'): _t('م:u:1 ت:a:1 R1:a:2 R2:i:1 R3:*:*'),
    ('VII', 'فاعل'): _t('م:u:1 ن:∅:1 R1:a:1 R2:i:1 R3:*:*'),
    ('VIII', 'فاعل'): _t('م:u:1 R1:∅:1 ت:a:1 R2:i:1 R3:*:*'),
    ('VIII', 'مفعول'): _t('م:u:1 R1:∅:1 ت:a:1 R2:a:1 R3:*:*'),
    ('X', 'فاعل'): _t('م:u:1 س:∅:1 ت:a:1 R1:∅:1 R2:i:1 R3:*:*'),
    ('X', 'مفعول'): _t('م:u:1 س:∅:1 ت:a:1 R1:∅:1 R2:a:1 R3:*:*'),
}
# لواحق الاسم بعد آخر الأصول: التاء المربوطة، ونون الجمع والمثنى، وتاء جمع المؤنث
NOUN_SUFFIX = ('ة', 'ن', 'ت')


def suffix_ok(c, prev=None):
    """نون المثنى والجمع لا تُنوَّن (فَرِهَٰنٌ ليس مثنى «فَرِه»: التنوين على النون يمنع أن تكون لاحقة)؛
    وبعد الألف تُكسر نون المثنى، وبعد الواو والياء تُفتح نون الجمع (هَٰمَٰنَ: النون من البناء لا لاحقة)"""
    if c.C != 'ن':
        return True
    if c.O.get('tanwin'):
        return False
    if prev is not None and prev.L == 2:
        return c.H == ('i' if prev.H == 'a' else 'a')
    return True


def _match_participle(cells, tmpl):
    """→ (الأصول، α، العمليات) أو None. صحيح الأصول وحده (المعتل يُترك للمدخل المعجمي)"""
    if len(cells) < len(tmpl):
        return None
    rad, alpha, ops = {}, [], []
    for (C, H, L), c in zip(tmpl, cells):
        if C.startswith('R'):
            if c.C in 'وي' and not c.O.get('virtual') and not (C == 'R2' and tmpl[0] == ('R1', 'a', 2) and c.H == 'i') or \
                    rad.get(C, c.C) != c.C:
                return None
            rad[C] = c.C
            alpha.append(C.lower())
        else:
            if c.C != C and not (C == 'ت' and c.C in 'طد'):
                return None
            if c.C != C:
                ops.append(f'إبدال ت ← {c.C}')
            alpha.append(f'زائد:{C}')
        if H != '*' and c.H != H or L != '*' and c.L != L:
            return None
    rest = cells[len(tmpl):]
    if len(rest) > 1 or rest and (rest[0].C not in NOUN_SUFFIX or not suffix_ok(rest[0], cells[len(tmpl) - 1])):
        return None
    alpha += ['لاحقة'] * len(rest)
    return ''.join(rad[k] for k in sorted(rad)), alpha, ops


import os as _os
RANK_BY_ATTESTATION = _os.environ.get('SARF_RANK_ATTESTATION') == '1'


def _verb_ilal(H, root):
    """عين الفعل الثلاثي في HFN: «معلّ» إن جاء ماضيه بألفٍ بعد الفاء (قَامَ، بَاعَ)، و«صحيح» إن ثبتت العين
    واواً أو ياءً متحركة (عَوِرَ)، وإلا None"""
    out = set()
    for e in H.index.get((root, 'I'), []):
        t = letters(e['verb'])
        if len(t) >= 2 and t[1][0] == 'ا':
            out.add('معلّ')
        elif len(t) >= 2 and t[1][0] in 'وي' and t[1][1] & {FATHA, DAMMA, KASRA}:
            out.add('صحيح')
    return 'معلّ' if out == {'معلّ'} else 'صحيح' if out == {'صحيح'} else ('كلاهما' if out else None)


def participle_analyses(cells):
    """→ [(الجذر، الوزن، فاعل/مفعول، α، العمليات، المستوى)] مرخَّصة بحدثٍ في HFN بالجذر والوزن،
    أو بالجذر وحده إن لم يُرخَّص بحدثٍ شيء (كما في الفعل)"""
    from .root import hfn
    H = hfn()
    matched = []
    for (cls, kind), tmpl in PARTICIPLES.items():
        m = _match_participle(cells, tmpl)
        if m:
            root, alpha, ops = m
            matched.append((root, cls, kind, alpha, ops))
            # الأجوف: «اسم الفاعل يعتلّ باعتلال فعله» (ابن يعيش، شرح المفصل ج5 ص448): قَامَ ← قَائِم، بَاعَ ← بَائِع.
            # فهمزة فاعل بعد الطول بدلٌ من العين بشرط أن يكون الفعل نفسه مُعَلَّ العين (في ماضيه ألف: قَامَ)؛
            # فإن صحّت عينه في الفعل (عَوِرَ) صحّت في اسم الفاعل (عَاوِر) ولم تُهمز
            if cls == 'I' and kind == 'فاعل' and root[1] == 'ء':
                for w in 'وي':
                    r2 = root[0] + w + root[2]
                    if _verb_ilal(H, r2) in ('معلّ', 'كلاهما'):
                        matched.append((r2, cls, kind, alpha, ops + [f'إبدال العين {w} ← ء: الفعل معلّ العين']))
            # المثال والمهموز في افتعل: الفاء تاء مدغمة (مُتَّخِذ ← ءخذ)
            if cls == 'VIII' and root[0] == 'ت':
                for w in 'ءوي':
                    matched.append((w + root[1:], cls, kind, alpha, ops + [f'إبدال الفاء {w} ← ت']))
        # الناقص: اللام محذوفة، فالعين آخر الأصول بكسرٍ طويل قبل نون الجمع أو بتنوين (مُعۡتَدِينَ، مُعۡتَدٍ)
        if tmpl[-1][0] == 'R3' and len(cells) >= len(tmpl) - 1:
            short = tmpl[:-1]
            head = cells[:len(short)]
            last = head[-1] if head else None
            if last is not None and last.H == 'i' and (last.L == 2 or last.O.get('tanwin')):
                m = _match_participle(head, short[:-1] + [(short[-1][0], 'i', '*')]) if \
                    len(cells) - len(short) <= 1 else None
                if m and (len(cells) == len(short) or cells[-1].C == 'ن'):
                    for w in 'وي':
                        matched.append((m[0] + w, cls, kind, m[1] + ['لاحقة'] * (len(cells) - len(short)),
                                        m[2] + [f'حذف اللام {w}']))
    # وعينٌ واو أو ياء صحيحة في فاعل (عَاوِر) لا تكون إلا من فعلٍ صحيح العين (عَوِرَ)
    matched = [x for x in matched if not (x[1] == 'I' and x[2] == 'فاعل' and x[0][1] in 'وي' and
                                          'إبدال العين' not in ' '.join(x[4]) and _verb_ilal(H, x[0]) not in ('صحيح', 'كلاهما'))]
    ev = [x + ('حدث',) for x in matched if (x[0], x[1]) in H.index]
    if RANK_BY_ATTESTATION and len({x[0] for x in ev}) > 1:
        # الترجيح بقوة الشهادة في HFN (A أقوى من B … E)، إن تفاضلت؛ وإلا بقي الاحتمال (تجربة تنتظر الإقرار)
        rank = {x[0]: min((e['tier'][:1] or 'Z') for e in H.index[(x[0], x[1])]) for x in ev}
        best = min(rank.values())
        if sum(1 for r in set(rank) if rank[r] == best) == 1:
            ev = [x + () for x in ev if rank[x[0]] == best]
    return ev or [x + ('جذر',) for x in matched if x[0] in H.roots]


# ---------- أبنية الأسماء عند سيبويه (الكتاب ج4 ص242 وما بعدها): قوالب للاسم ----------
_SIB = None
SIB_PATHS = ['data/patterns/awzan_sibawayh_308.csv']


def sibawayh_patterns():
    """→ [(المعرِّف، الصفحة، البناء، القالب، الأمثلة)] من ملف أبنية سيبويه: الموجود والنادر المعيَّن الضبط،
    والقالب بخلايا البناء: ف ع ل ↦ R1 R2 R3 (والرباعي والخماسي لاماته R3…R5)، وآخر خلية حركتها حركة الإعراب"""
    global _SIB
    if _SIB is not None:
        return _SIB
    import csv, os
    H = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    path = next((os.path.join(H, x) for x in SIB_PATHS if os.path.exists(os.path.join(H, x))), None)
    _SIB = []
    if not path:
        return _SIB
    for x in csv.DictReader(open(path, encoding='utf-8-sig')):
        pat = x['pattern_vocalized']
        if x['status'] not in ('EXISTS', 'RARE') or x['vocalization_basis'] == 'UNDETERMINED' or '?' in pat:
            continue
        cs, _ = cells_of(pat, 'p')
        if not cs:
            continue
        quad = x['section'].startswith(('رباعي', 'خماسي'))
        seen, tmpl = {}, []
        lams = 0
        for c in cs:
            if c.C in 'فع':
                C = 'R1' if c.C == 'ف' else 'R2'
            elif c.C == 'ل':
                if quad and not (c.H == 'a' and False):
                    # الرباعي والخماسي: كل لامٍ أصلٌ جديد، إلا الشدة (اللام الثانية من خليتي الشدة)
                    if c.O.get('role') == 'شدة: الثاني':
                        C = f'R{2 + lams}'
                    else:
                        lams += 1
                        C = f'R{2 + lams}'
                else:
                    C = 'R3'
            else:
                C = c.C
            tmpl.append((C, c.H, c.L))
        last = len(tmpl) - 1
        if pat[-1] in '\u064C\u064F':                # الحركة الأخيرة إعراب
            C, H_, L = tmpl[last]
            tmpl[last] = (C, '*', '*' if L == 1 else L)
        _SIB.append((x['id'], x['page'], pat, tmpl, x['examples']))
    return _SIB


def weak_variants(cells, toks):
    """صور الخلايا التي تُقرأ بها الكتابة على أصلٍ معتلّ (لرخصة الجذع وحدها، لا تغيّر خلايا التحليل):
    - الياء المشدَّدة بعد كسر (وَلِيّ) والواو المشدَّدة بعد ضم (عَدُوّ): ياءُ فعيل أو واوُ فعول مدغمةٌ في لامٍ مثلها
    - الألف المقصورة آخراً (مُسَمًّى، مُصۡطَفَى): اللام ياءٌ أو واو لم تُكتب صامتاً
    → [(الخلايا، العمليات)]، أولها الخلايا كما هي"""
    from dataclasses import replace
    out = [(cells, [])]
    for i in range(len(cells) - 2):
        a, b, c = cells[i], cells[i + 1], cells[i + 2]
        if b.H == '∅' and b.C == c.C and (b.C == 'ي' and a.H == 'i' or b.C == 'و' and a.H == 'u') and a.L == 1:
            out.append((cells[:i] + [replace(a, L=2, O=dict(a.O, madd=b.C))] + cells[i + 2:],
                        [f'«{b.C}» المشدَّدة بعد حركتها: حرف مدٍّ مدغمٌ في لامٍ مثله']))
            break
    for i in range(len(cells) - 1):
        a = cells[i]
        if a.L == 2 and a.O.get('madd') in ('ي', 'و') and (a.H, a.O['madd']) in (('i', 'ي'), ('u', 'و')):
            # الأجوف: حرف المدّ وسط الاسم قد يكون عيناً ساكنة (دِين = دِيۡن، زِينَة، حُور)
            w = Cell(a.id + 'w', a.O['madd'], '∅', 1, dict(tok=[], virtual=True))
            out.append((cells[:i] + [replace(a, L=1, O=dict(a.O, madd=None)), w] + cells[i + 1:],
                        [f'«{a.O["madd"]}» وسط الاسم عينٌ ساكنة']))
            break
    if cells:
        last = cells[-1]
        maqsur = last.O.get('madd') in ('ى', 'ا') or any(toks[j][0] == 'ى' for j, _ in last.O.get('silent', [])
                                                         if j < len(toks))
        if maqsur and last.H == 'a':
            v = Cell(last.id + 'v', 'ي', '∅', 1, dict(tok=[], virtual=True))
            out.append((cells[:-1] + [replace(last, L=1, O=dict(last.O))] + [v],
                        ['الألف آخراً: اللام واوٌ أو ياءٌ قُلبت ألفاً' if last.O.get('madd') in ('ا', 'ى') else
                         'الألف المقصورة: اللام ياءٌ أو واو لم تُكتب صامتاً']))
    return out


def _resolve_root(root, H, virtual):
    """الجذر المسجَّل: كما هو، أو بإبدال اللام الهمزة بعد الألف واواً أو ياءً (لِقَاء ← لقي)، أو اللام المقدَّرة واواً"""
    if root in H.roots:
        return root
    if root[-1:] == 'ء' or virtual:
        for w in 'يو':
            if root[:-1] + w in H.roots:
                return root[:-1] + w
    return None


def sibawayh_analyses(cells, toks=None):
    """→ [(الجذر، المعرِّف، الصفحة، البناء، α، الأمثلة)] لكل بناءٍ يطابق الخلايا وجذرُه في HFN.
    toks: إن أُعطيت جُرِّبت صور المعتلّ أيضاً (weak_variants) — للرخصة وحدها، فطول α قد لا يساوي الخلايا"""
    from .root import hfn
    H = hfn()
    out = []
    for cs, ops in (weak_variants(cells, toks) if toks is not None else [(cells, [])]):
        for x in _sibawayh_match(cs, H, bool(ops)):
            if x not in out:
                out.append(x)
    return tuple(out)


def _sibawayh_match(cells, H, weak):
    out = []
    for sid, page, pat, tmpl, ex in sibawayh_patterns():
        if len(cells) < len(tmpl):
            continue
        rad, alpha, ok = {}, [], True
        for (C, Hh, L), c in zip(tmpl, cells):
            if C.startswith('R'):
                if rad.get(C, c.C) != c.C or (c.C in 'وي' and c.H == '∅' and False):
                    ok = False; break
                rad[C] = c.C
                alpha.append(C.lower())
            elif c.C != C:
                ok = False; break
            else:
                alpha.append(f'زائد:{C}')
            if Hh != '*' and c.H != Hh or L != '*' and c.L != L:
                ok = False; break
            if Hh == '*' and c.O.get('madd') == 'ى':
                ok = False; break                    # الألف المقصورة ليست حركة إعراب (عِيسَىٰ ليس فَعِيلًا)
        if not ok:
            continue
        rest = cells[len(tmpl):]
        if len(rest) > 1 or rest and (rest[0].C not in NOUN_SUFFIX or not suffix_ok(rest[0], cells[len(tmpl) - 1])):
            continue
        root = ''.join(rad[k] for k in sorted(rad))
        root = _resolve_root(root, H, weak) if (weak or root[-1:] == 'ء' and cells[len(tmpl) - 2].L == 2) else \
            (root if root in H.roots else None)
        if root:
            out.append((root, sid, page, pat, alpha + ['لاحقة'] * len(rest), ex))
    return out


# ---------- رخصة الجذع: هل الكتابة كلمةٌ مرخَّصة بالمعجم أو بالبناء؟ ----------
ENCLITICS_V = ('هُمَا', 'هِمَا', 'كُمَا', 'هُنَّ', 'هِنَّ', 'كُنَّ', 'هُمْ', 'هِمْ', 'كُمْ', 'هُ', 'هِ', 'هَا', 'كَ', 'كِ',
               'نَا', 'نِي', 'يَ', 'ي')


# أعلام القرآن بصورتها في المصحف: العلم مدخلٌ معجمي بعينه لا يُبنى على قالب (وَمُوسَىٰ = وَ + مُوسَىٰ، لا «ومس»)
PROPER_V = ('مُوسَى', 'عِيسَى', 'هَٰمَٰنَ', 'هَٰرُونَ', 'فِرْعَوْنَ', 'قَٰرُونَ', 'إِبْرَٰهِيمَ', 'إِسْمَٰعِيلَ', 'إِسْحَٰقَ',
            'يَعْقُوبَ', 'يُوسُفَ', 'دَاوُۥدَ', 'دَاوُدَ', 'سُلَيْمَٰنَ', 'أَيُّوبَ', 'يُونُسَ', 'زَكَرِيَّا', 'يَحْيَى', 'إِلْيَاسَ',
            'لُوطٍ', 'لُوطًا', 'لُوطٌ', 'نُوحٍ', 'نُوحًا', 'نُوحٌ', 'هُودٍ', 'هُودًا', 'هُودٌ', 'صَٰلِحٍ', 'صَٰلِحًا', 'شُعَيْبٍ',
            'شُعَيْبًا', 'مَرْيَمَ', 'ءَادَمَ', 'مُحَمَّدٍ', 'مُحَمَّدٌ', 'جِبْرِيلَ', 'مِيكَىٰلَ', 'ثَمُودَ', 'عَادٍ', 'عَادًا',
            'مَدْيَنَ', 'طَالُوتَ', 'جَالُوتَ', 'لُقْمَٰنَ', 'إِدْرِيسَ', 'عُزَيْرٌ', 'تُبَّعٍ', 'إِرَمَ', 'مِصْرَ', 'بَابِلَ',
            'يَأْجُوجَ', 'مَأْجُوجَ', 'إِبْلِيسَ', 'هَٰرُوتَ', 'مَٰرُوتَ', 'إِسْرَٰٓءِيلَ', 'إِسْرَٰءِيلَ', 'يَسَعَ', 'ٱلْيَسَعَ')


# الأسماء المحذوفة اللام (باب ما حُذفت لامه): لا تُبنى على ثلاثة أصول مكتوبة، فهي مرخَّصة بأعيانها
BILITERAL_V = {'يَد': 'يدي', 'دَم': 'دمي', 'غَد': 'غدو', 'أَب': 'أبو', 'أَخ': 'أخو', 'بَنِي': 'بني', 'بَنُو': 'بني',
               'سْم': 'سمو', 'فَم': 'فوه', 'شَفَة': 'شفه', 'سَنَة': 'سنو', 'لُغَة': 'لغو', 'مِائَة': 'مءي'}


def _madi_exact(t, verb):
    """الماضي المكتوب بلاحقته يطابق فعل HFN حرفاً وحركة إلا حركة لامه (وَضَعَتۡهَا ← وَضَعَ، فَشِلۡتُمۡ ← فَشِلَ):
    حروفه وحركاته إلى ما قبل اللام هي هي، ثم اللام، ثم لواحق الإسناد والمفعول"""
    vt, tt = letters(verb), letters(t)
    k = len(vt) - 1
    if k < 2 or len(tt) <= k + 0 or [x for x in tt[:k]] != [x for x in vt[:k]] or tt[k][0] != vt[k][0]:
        return False
    return len(tt) > k + 1 and all(L in 'تنواهمكيا' for L, _ in tt[k + 1:])


def _hollow_fatha(t, root, cls):
    """الأجوف الماضي المسند إلى ضمير رفعٍ متحرك تُضمّ فاؤه أو تُكسر (قُلۡنَا، بِعۡنَا، خِفۡنَا)، ولا تُفتح:
    فـ«جَدۡنَا» ليس من «جاد»"""
    toks = letters(t)
    return cls == 'I' and len(root) == 3 and root[1] in 'وي' and len(toks) > 2 and \
        toks[0][1] == {FATHA} and SUKUN in toks[1][1]


def licence_strength(lics):
    """قوة الرخصة بمرتبة دليلها: 2 شهادة معجمية (مدخلٌ في HFN، أو فعلٌ يطابق حدثاً فيه حرفاً وحركة، أو محذوف
    اللام بعينه)؛ 1 بناءٌ أو قالبٌ جذرُه في HFN (بناء سيبويه، أو اسم فاعل أو مفعول قياساً، أو قالب فعل)؛
    0.5 بصورة المعتلّ (weak_variants) أو المحذوف الفاء؛ 0 لا رخصة"""
    best = 0
    for kind, root, what in lics:
        if kind in ('معجم', 'محذوف اللام', 'فعل', 'علم'):
            s_ = 2
        elif kind == 'فعل بالكتابة':
            s_ = 1.5                             # قالبٌ ودليلٌ مكتوب على الفعلية، دون مطابقة فعلٍ في HFN حرفاً وحركة
        elif 'قُلبت ألفاً' in what or kind in ('محذوف الفاء', 'أمر المثال') or kind == 'فعل محتمل':
            s_ = 1                               # الناقص بألفٍ بعد فتح (بَدَا، عَفَا، هَدَىٰ)، ومصدر المثال (سَعَة)
                                                 # وأمره (عِظۡ، ذَرۡ): كتابةٌ مطّردة
        elif '[' in what or kind == 'محذوف الفاء' or kind == 'مشتق' and '(' in what:
            s_ = 0.5
        else:
            s_ = 1
        best = max(best, s_)
    return best


@lru_cache(maxsize=None)
def stem_licence(text, verbs=True):
    """→ [(النوع، الجذر، البيان)]: ما يرخّص الكتابة كلمةً: مدخلٌ معجمي في HFN (مصدر، اسم فاعل أو مفعول)،
    أو بناءٌ من أبنية سيبويه جذرُه في HFN، أو اسم فاعل أو مفعول قياساً، أو فعلٌ يطابق HFN.
    ويُجرَّب بعد نزع الضمير المتصل من آخره (وَلِيُّهُ ← وَلِيُّ). الخالي: لا رخصة"""
    from .match import vform_match
    from .root import morph, hfn, READING, _plain_vowels
    from .affix import stem_info
    out = []
    forms = [text]
    toks = letters(text)
    for suf in ENCLITICS_V:
        st = letters(suf)
        if len(toks) > len(st) + 1 and vform_match(toks[-len(st):], [suf]):
            forms.append(''.join(L + ''.join(sorted(m)) for L, m in toks[:-len(st)]))
            break
    if vform_match(text, PROPER_V, loose=True):
        return (('علم', '', text),)
    for t in forms:
        for b, root in BILITERAL_V.items():
            bt = letters(b)
            tt = letters(t)
            if len(tt) - len(bt) in (0, 1) and vform_match(tt[:len(bt)], [b], loose=True) and \
                    (len(tt) == len(bt) or tt[-1][0] in 'يوان'):
                out.append(('محذوف اللام', root, b))
        cs, tk = cells_of(t, 'lic')
        if not cs:
            continue
        if len(cs) == 3 and cs[-1].C == 'ة' and cs[0].H in ('i', 'a') and cs[0].L == 1 and cs[1].H == 'a' and \
                'و' + cs[0].C + cs[1].C in hfn().roots:
            # المثال المحذوف الفاء بتاءٍ عوضاً عنها (سَعَة، دِيَة، عِدَة، صِلَة): الفاء واوٌ
            out.append(('محذوف الفاء', 'و' + cs[0].C + cs[1].C, 'عِلَة'))
            continue
        if len(cs) == 2 and cs[0].H in ('i', 'a') and cs[0].L == 1 and cs[1].C not in 'وي' and \
                (cs[1].H == '∅' or t != text) and t == forms[-1] and \
                'و' + cs[0].C + cs[1].C in hfn().roots and not stem_info(t)['pos'] == 'noun':
            # أمر المثال الواوي: حُذفت فاؤه (عِظۡ، عِدۡ، ذَرۡ، دَعۡ)
            out.append(('أمر المثال', 'و' + cs[0].C + cs[1].C, 'عِلۡ'))
        k = _lex_key(t)
        for root, pos, pat, lu, lemma in (lex_index().get(k, []) if len(cs) >= 3 else [])[:1]:
            out.append(('معجم', root, f'{pos} «{lemma}»'))
        for vs, ops in weak_variants(cs, tk):
            hits = _sibawayh_match(vs, hfn(), bool(ops))[:2]
            for root, sid, page, pat, alpha, ex in hits:
                out.append(('بناء', root, f'{pat} ({sid})' + (f' [{ops[0]}]' if ops else '')))
            if hits:
                break
        x = next(iter(participle_analyses(cs)), None)
        if x:
            out.append(('مشتق', x[0], f'{x[2]} {x[1]}'))
        else:
            # المعتلّ اللام (مُسَمًّى): القالب على الصورة المعتلّة، والجذر مسجَّلاً بلامه واواً أو ياءً
            for vs, ops in weak_variants(cs, tk)[1:]:
                hit = next(((cls, kind, m) for (cls, kind), tm in PARTICIPLES.items()
                            for m in [_match_participle(vs, tm)] if m), None)
                root = hit and _resolve_root(hit[2][0], hfn(), True)
                if root:
                    out.append(('مشتق', root, f'{hit[1]} {hit[0]} ({ops[0]})'))
                    break
        if verbs and t == text and stem_info(t)['pos'] != 'noun':
            # الفعل على نصّه كله (لا بعد نزع «نَا» ضميراً)، وما عليه دليل الاسم ليس فعلاً
            m = morph(t)
            if m:
                # قراءة الكلمة كلها، لا بقيتها بعد سابقةٍ نزعها المرشِّح (فَجَعَلۡتُمۡ ← جَعَلۡتُمۡ)
                own = lambda r, c: READING.get((r, c)) == t and not _hollow_fatha(t, r, c)
                # الشهادة المعجمية: فعلٌ في HFN يطابق المكتوب حرفاً وحركة (الماضي)؛ وما سواه قالبٌ مرشَّح
                ev = [x for x in m.get('licensed', []) if own(x['root'], x['form_class']) and
                      (_plain_vowels(x['verb']) == _plain_vowels(t) or _madi_exact(t, x['verb']))]
                if ev:
                    out.append(('فعل', ev[0]['root'], ev[0]['form_class']))
                else:
                    cand = [(x['root'], x['form_class']) for x in m.get('licensed', []) if own(x['root'], x['form_class'])] + \
                        [(r, c) for r, c in m.get('candidates', []) if r in hfn().roots and own(r, c)]
                    if cand:
                        # قالب فعلٍ والكتابةُ تثبت فعليته (ضمير رفعٍ بعد ساكن، أو حرف مضارعة بقرينته): شهادة أولى
                        kind = 'فعل بالكتابة' if stem_info(t)['pos'] == 'verb' and m.get('status') == 'accepted' and \
                            m.get('root') == cand[0][0] else 'فعل محتمل'
                        out.append((kind, cand[0][0], cand[0][1]))
    return tuple(out)
