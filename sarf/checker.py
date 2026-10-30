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
