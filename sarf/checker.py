# -*- coding: utf-8 -*-
"""
sarf.checker — فاحصٌ مستقل لإغلاق الجملة (مراجعة التقرير ٩ و١١): لا يثق بشهادة الإغلاق ولا بقائمة الالتزامات
التي ولّدها البناء، بل يعيد اشتقاق ما يلزم من سجلّ التحليل نفسه (العوامل المقبولة، والنواسخ، والإسناد)،
ويرفض الإغلاق إن:
  ١. خلت شهادة الإكمال أو الحدّ، أو لم تصحّ (سببٌ فارغ، أو شرطٌ فارغ، أو مانعٌ بلا برهان انتفاء)
  ٢. بقي في Ω التزامٌ لازم غير مستوفى، أو مستوفى بلا دليلٍ صحيح
  ٣. نقص من Ω التزامٌ يلزم بالتحليل: معمول كل عاملٍ مقبول في الجملة، وخبر كل ناسخ، وإغلاق كل وحدة فيها
  ٤. لم تُغطَّ كلمةٌ من مواضع الجملة بوحدةٍ منها، أو بقيت كلمةٌ بلا موضعٍ مرخَّص
  ٥. أشار دليلٌ إلى وحدةٍ ليست في الجملة (رابطٌ طرفه خارجها)
  ٦. لم يوافق نوعُ طرفَي العلاقة اسمَها (ValidRelation = TypeOK ∧ ScopeOK): خبرٌ «جملة فعلية» طرفه ضمير،
     أو مفعولٌ مصدره غير فعل، أو طرفٌ واحد خبرٌ ومفعولٌ معاً
  ونطاقه: اتساق السجل وأنواع أطرافه، لا صحة مقدّماته اللغوية (أن «ما» شرطية، أو أن الفاء جوابٌ لهذه الأداة):
  تلك تُقاس بمرجعٍ مستقل

    check_sentence(J, analyses) → [أسباب الرفض]؛ والقائمة الخالية قبول
"""
from .status import ACCEPTED


def _ev_ok(ev):
    return ev is not None and ev.valid()


def expected_obligations(J, analyses):
    """الالتزامات اللازمة للجملة J مشتقّةً من سجلّ التحليل وحده: analyses[(سورة، آية)] = a"""
    out = set()
    locs = set(J.O.get('location', []))
    for (s, v), a in analyses.items():
        acc = {(f['word_index'], f['operator'], f['group']) for f in a['operators'] if f.get('status') == ACCEPTED}
        for r in a.get('relations', []):
            if (s, v, r['word_index']) not in locs or (r['word_index'], r['operator'], r['group']) not in acc:
                continue
            if r.get('target') is not None:
                out.add(f'معمول «{r["operator"]}»')
            if r['group'] in ('2', '10'):
                out.add(f'خبر «{r["operator"]}»')
    return out


def _kind(G, verbs):
    """نوع طرف العلاقة من الوحدة نفسها: فعل، أو ضمير (خاناته مبنية كلها)، أو اسم"""
    if G is None:
        return None
    F = (G.Theta.get('F') or {}).get('kind')
    if G.id in verbs or F in ('madi', 'mudari', 'amr'):
        return 'فعل'
    slots = G.O.get('slots', [])
    if slots and all(t == 'مبني' for t, _ in slots):
        return 'ضمير'
    return 'اسم'


# العلاقة ← (أنواع المصدر المقبولة، أنواع الطرف المقبولة)؛ None: أيّ نوع
RELATION_TYPES = [
    ('لام الجحود', None, {'فعل'}),
    ('جملة فعلية', None, {'فعل'}),
    ('خبر', None, {'اسم', 'ضمير', 'فعل'}),
    ('مفعول به', {'فعل'}, {'اسم', 'ضمير'}),
    ('إسناد', {'فعل'}, None),
    ('مجرور', None, {'اسم', 'ضمير'}),
    ('في محلّ جر', None, {'اسم', 'ضمير'}),
    ('اسم «', None, {'اسم', 'ضمير'}),
    ('منصوب بأن مضمرة', None, {'فعل'}),
    ('مجزوم', None, {'فعل'}),
]
# أدوار الحجّة: لا تجتمع اثنتان منها على طرفٍ واحد (الضمير لا يكون خبراً جملياً ومفعولاً معاً)
ARG_ROLES = ('خبر', 'مفعول به', 'اسم «', 'مجرور', 'في محلّ جر')


def relation_problems(J):
    """ValidRelation(r, A, B) = TypeOK ∧ ScopeOK: نوع الطرفين يوافق اسم العلاقة، وطرفاها في الجملة، ولا يحمل
    طرفٌ دوري حجّةٍ متنافيين. → [أسباب الرفض]"""
    units = {}
    stack = list(J.A)
    while stack:
        X = stack.pop()
        if hasattr(X, 'Theta') and X.id.startswith('Q'):
            units[X.id] = X
    verbs = {b[1] for b in J.B if b[0] == 'إسناد'}
    why = []
    roles = {}
    for b in J.B:
        name, a, d = b[0], b[1], b[2]
        if not isinstance(a, str) or not isinstance(d, str) or name == 'تجاور':
            continue
        A, B = units.get(a.split('.s')[0]), units.get(d.split('.s')[0])
        if A is None or (d.startswith('Q') and B is None):
            continue                                      # الطرف خارج الجملة: يرفضه فحص النطاق
        ka, kb = _kind(A, verbs), _kind(B, verbs)
        rule = next(((ra, rb) for key, ra, rb in RELATION_TYPES if key in name), None)
        if rule and '.s' not in d:
            ra, rb = rule
            if ra is not None and ka not in ra:
                why.append(f'نوع المصدر لا يوافق العلاقة: «{name}» من {ka} ({A.O.get("text")})')
            if rb is not None and B is not None and kb not in rb:
                why.append(f'نوع الطرف لا يوافق العلاقة: «{name}» طرفه {kb} ({B.O.get("text")})')
        role = next((r for r in ARG_ROLES if r in name), None)
        if role and B is not None:
            roles.setdefault(d, set()).add('خبر' if role == 'خبر' else 'مفعول' if role == 'مفعول به' else role)
    for d, rs in roles.items():
        if 'خبر' in rs and 'مفعول' in rs:
            why.append(f'طرفٌ واحد خبرٌ ومفعولٌ معاً: {units[d.split(".s")[0]].O.get("text")}')
    return why


def check_sentence(J, analyses):
    why = []
    if not J.closed:
        return why
    if not _ev_ok(J.ec):
        why.append('شهادة الإكمال خالية أو غير صحيحة')
    if not _ev_ok(J.eb):
        why.append('شهادة الحدّ خالية أو غير صحيحة')
    for o in J.Omega:
        if o.required and not o.met:
            why.append(f'التزامٌ لازم غير مستوفى: {o.name}')
        elif o.required and o.met and not _ev_ok(o.ev):
            why.append(f'التزامٌ مستوفى بلا دليلٍ صحيح: {o.name}')
    have = {o.name for o in J.Omega}
    for name in sorted(expected_obligations(J, analyses) - have):
        why.append(f'التزامٌ يلزم بالتحليل ولم يُولَّد: {name}')
    ids = set()
    stack = list(J.A)
    while stack:
        X = stack.pop()
        if hasattr(X, 'closed'):
            ids.add(X.id)
            if not X.closed:
                why.append(f'وحدةٌ غير مغلقة في جملةٍ مغلقة: {X.id}')
    words = {tuple(x) for x in J.O.get('location', [])}
    covered = {tuple(int(t) for t in i.split('.w')[0].lstrip('Q').split(':')) + (int(i.split('.w')[1].split('.')[0]),)
               for i in ids if '.w' in i}
    for w in sorted(words - covered):
        why.append(f'كلمةٌ لا تغطّيها وحدةٌ من الجملة: {w}')
    if J.O.get('unplaced'):
        why.append('كلماتٌ بلا موضعٍ مرخَّص: ' + '، '.join(J.O['unplaced'][:4]))
    why += relation_problems(J)
    for b in J.B:
        for end in (b[1], b[2]):
            if isinstance(end, str) and end.startswith('Q') and end.split('.s')[0] not in ids:
                why.append(f'رابطٌ طرفه خارج الجملة: {b[0]} ({end})')
    return why


def check_layer(LT, analyses):
    """→ (المفحوص، المرفوض، [(معرِّف الجملة، الأسباب)]) لكل جملةٍ مغلقة في الطبقة اللغوية"""
    n, bad = 0, []
    for SP in LT:
        for D in SP.A + SP.O.get('pending', []):
            for J in D.A + D.O.get('pending', []):
                if getattr(J, 'closed', False):
                    n += 1
                    why = check_sentence(J, analyses)
                    if why:
                        bad.append((J.id, why))
    return n, len(bad), bad
