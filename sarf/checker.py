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
  ٧. استشهد دليلٌ بلاحقةٍ أو حرف مضارعة ليس في خلايا وحدته (تُوبُوا: «وا» لا «ون»)
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


VERBAL_GROUPS = {'10', '11', '12', '13'}     # كان وأخواتها، وأفعال المقاربة، والمدح والذم، والظن: عواملُ أفعال


def _verbal_operator(G, analyses):
    """الوحدة عاملٌ فعلي (كَانَ عَلِيمًا): خانتها «عامل»، وفي سجلّ التحليل عاملٌ من مجموعات الأفعال في كلمتها"""
    if not analyses or not any(t == 'عامل' for t, _ in G.O.get('slots', [])) or '.w' not in G.id:
        return False
    s, v = (int(x) for x in G.id.split('.w')[0].lstrip('Q').split(':'))
    wi = int(G.id.split('.w')[1].split('.')[0])
    a = analyses.get((s, v))
    return bool(a) and any(f['word_index'] == wi and f['group'] in VERBAL_GROUPS for f in a['operators'])


def _kind(G, verbs, analyses=None):
    """نوع طرف العلاقة من الوحدة نفسها: فعل، أو ضمير (خاناته مبنية كلها)، أو اسم"""
    if G is None:
        return None
    F = (G.Theta.get('F') or {}).get('kind')
    if G.id in verbs or F in ('madi', 'mudari', 'amr') or _verbal_operator(G, analyses):
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


def relation_problems(J, analyses=None):
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
        ka, kb = _kind(A, verbs, analyses), _kind(B, verbs, analyses)
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


def _letters_of(t):
    from .chars import letters
    return [L for L, _ in letters(t)]


def witness_problems(J):
    """الشاهد يقابل الخلايا (مراجعة التقرير الثالثة ١): كل لاحقةٍ أو حرف مضارعة يستشهد به دليلُ التزامٍ مستوفى
    يجب أن يكون حروفاً مكتوبةً في وحدته: اللاحقة في آخرها (قبل ضميرٍ متصل)، وحرف المضارعة في أولها
    (بعد سابقة). والتحويل المسجَّل (حذف النون) يُذكر بجانب الصورة المكتوبة، ولا يحلّ محلّها"""
    import re
    units = {}
    stack = list(J.A)
    while stack:
        X = stack.pop()
        if hasattr(X, 'Theta') and X.id.startswith('Q'):
            units[X.id] = X
    why = []
    for o in J.Omega:
        if not (o.met and o.ev) or not o.units:
            continue
        G = units.get(o.units[0])
        if G is None:
            continue
        word = _letters_of(G.O.get('text', ''))
        for cond in [o.ev.cause] + list(o.ev.conditions):
            for kind, x in re.findall(r'(لاحقة[^«]*|اللاحقة|حرف المضارعة)\s*«([^»]+)»', cond):
                if x == '—':
                    continue
                xs = _letters_of(x)
                if 'المضارعة' in kind:
                    ok = word[:len(xs)] == xs or word[1:1 + len(xs)] == xs
                else:
                    ok = any(word[len(word) - j - len(xs):len(word) - j] == xs for j in range(0, 4))
                if not ok:
                    why.append(f'شاهدٌ لا يقابل الخلايا: {o.name}: «{x}» ليست في «{G.O.get("text")}»')
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
    why += relation_problems(J, analyses)
    why += witness_problems(J)
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
