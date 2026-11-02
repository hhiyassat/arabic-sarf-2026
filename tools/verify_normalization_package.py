# -*- coding: utf-8 -*-
"""تحقّقٌ مستقل من حزمة التطبيع (N04)، بالمكتبة القياسية وحدها، دون استيراد شيءٍ من شيفرة المشروع.

    python3 verify_normalization_package.py --quran <quran_hafs.tsv> --dir <مجلد الحزمة> [--json <ملف النتائج>]

يقرأ من الحزمة: normalization_run.json، normalization_cells.jsonl.gz، normalization_ops.jsonl.gz،
normalization_previous_output.json.

إعادة البناء لا تقرأ قيمة أي محرفٍ من المصدر:
  - لا من حقل source في ملف الخلايا (لا يُقرأ هذا الحقل إطلاقاً)؛
  - ولا من المصحف، فهو يُقرأ بعد البناء للمقارنة والبصمة وحدهما.
  - ويُستعمل الطول المعلَن (source_length) لضبط المواضع وحده.
  - المحرف غير المتغيّر يؤخذ من خليته الأصلية.
  - والمحذوف أو المستبدل أو المركّب يؤخذ من preserved_information، ويُفحص اتساقه:
    المحرف ورمزه، وموضعه داخل مجالات عمليته، وتعارض السجلات، وحالة الاشتقاق.

النتائج منفصلة:
  A تغطية المواضع: لكل موضعٍ قيمةٌ من خليةٍ أو معلومةٍ محفوظة
  B إمكان إعادة البناء: لا إخفاق مسمّى (R1…R10)
  C مطابقة المستعاد للمصدر الأصلي (V1/V2)
  D سلامة المحاذاة
  E سلامة البصمات
  F الأعداد مقابل run.json
"""
import argparse, collections, gzip, hashlib, json, os, sys, unicodedata

TANWIN = {'ً', 'ٌ', 'ٍ'}


def cpstr(s):
    return ' '.join(f'U+{ord(c):04X}' for c in s)


def coverage(cells, ops, L):
    """A: هل لكل موضعٍ مصدرٌ لقيمته (بلا فحص القيم)؟ → [المواضع غير المغطّاة]"""
    have = {p['at'] for o in ops for p in o.get('preserved_information') or [] if isinstance(p.get('at'), int)}
    have |= {c['src'][0] for c in cells if not c.get('derived') and len(c.get('src') or []) == 1}
    return [i for i in range(L) if i not in have]


def reconstruct(cells, ops, L):
    """B: البناء من الخلايا والسجل وحدهما → (النص أو None، [إخفاقات {code, at, detail}])"""
    fails = []
    F = lambda code, at=None, d='': fails.append(dict(code=code, at=at, detail=d))
    pres = {}
    for o in ops:
        spans = o.get('source_spans') or []
        for p in o.get('preserved_information') or []:
            at, ch = p.get('at'), p.get('char')
            if not isinstance(at, int) or not 0 <= at < L:
                F('R7_OUT_OF_RANGE', at, o.get('op_id'))
                continue
            if not isinstance(ch, str) or len(ch) != 1 or p.get('codepoint') != f'U+{ord(ch):04X}':
                F('R3_CODEPOINT', at, f"{o.get('op_id')} {ch!r} {p.get('codepoint')}")
                continue
            if not any(a <= at < b for a, b in spans):
                F('R4_AT_OUTSIDE_SPANS', at, o.get('op_id'))
            if at in pres and pres[at] != ch:
                F('R2_CONFLICT', at, f'{cpstr(pres[at])} ≠ {cpstr(ch)}')
            pres.setdefault(at, ch)
    val = {}
    for k, c in enumerate(cells):
        src = c.get('src') or []
        if any(not isinstance(i, int) or not 0 <= i < L for i in src):
            F('R7_OUT_OF_RANGE', None, f'cell {k}')
            continue
        if c.get('derived'):
            continue
        if not src:
            F('R6_NONDERIVED_WITHOUT_SOURCE', None, f'cell {k} {cpstr(c.get("c", ""))}')
            continue
        if len(src) > 1:
            for i in src:
                if i not in pres:
                    F('R5_COMPOSITE_UNPRESERVED', i, f'cell {k}')
            continue
        i = src[0]
        if i in pres:
            if c.get('c') == pres[i]:
                F('R10_PRESERVED_BUT_UNCHANGED', i, f'cell {k}')
            continue
        if i in val and val[i] != c.get('c'):
            F('R2_CONFLICT', i, f'{cpstr(val[i])} ≠ {cpstr(c.get("c", ""))}')
        val.setdefault(i, c.get('c'))
    out = [pres.get(i, val.get(i)) for i in range(L)]
    for i, x in enumerate(out):
        if x is None:
            F('R1_MISSING', i)
    if any(x is None for x in out):
        return None, fails
    text = ''.join(out)
    for o in ops:
        spans = o.get('source_spans') or []
        got = ''.join(text[i] for a, b in spans for i in range(a, b) if 0 <= i < L)
        if spans and (got != o.get('source_text') or cpstr(got) != o.get('source_codepoints')):
            F('R8_OP_SOURCE_MISMATCH', spans[0][0], o.get('op_id'))
    for k, c in enumerate(cells):
        m = c.get('mark')
        if c.get('c') in TANWIN and (m is None or m.get('function') is not None):
            F('R9_MARK_FORM_MISMATCH', None, f'cell {k}: تنوين بلا شكلٍ أو بوظيفةٍ معيَّنة')
        elif m is not None and m.get('form') != cpstr(''.join(text[i] for i in c.get('src') or [] if 0 <= i < L)):
            F('R9_MARK_FORM_MISMATCH', (c.get('src') or [None])[0], f'cell {k}: {m.get("form")}')
    return (None if fails else text), fails


def compare(rec, original):
    """C: المقارنة بعد البناء"""
    if rec is None:
        return 'NOT_RECONSTRUCTED'
    if len(rec) != len(original):
        return 'V2_LENGTH'
    return None if rec == original else 'V1_MISMATCH'


def alignment(cells, ops, L, spaces):
    """D: محارف كل كلمةٍ ناتجة من كلمة مصدرٍ واحدة، إلا ما جمعته N-JOIN-LONE-ALIF أو حُذف كله وحُفظ.
    spaces: مواضع المسافات في المصدر، من الخلايا والمحفوظ (لا من النص)."""
    wof, k = [], 0
    for i in range(L):
        wof.append(None if i in spaces else k)
        k += i in spaces
    joined = {wof[i] for o in ops if o.get('rule_id') == 'N-JOIN-LONE-ALIF' for a, b in o.get('source_spans') or []
              for i in range(a, b) if 0 <= i < L and wof[i] is not None}
    bad, cur = 0, set()
    for c in cells + [dict(c=' ', src=[])]:
        if c.get('c') == ' ':
            if len(cur) > 1 and not cur <= joined:
                bad += 1
            cur = set()
        else:
            cur |= {wof[i] for i in c.get('src') or [] if 0 <= i < L and wof[i] is not None}
    return bad


def check_verse(R, ops_by_rep, original=None):
    """فحص آيةٍ واحدة بكل الفحوص (يُستدعى مباشرةً في اختبارات الإفساد) → dict بالنتائج المنفصلة"""
    L = R['source_length']
    res = {}
    for which in ('display', 'analysis'):
        cells, ops = R['cells_' + which], ops_by_rep[which]
        cov = coverage(cells, ops, L)
        rec, fails = reconstruct(cells, ops, L)
        spaces = {p['at'] for o in ops for p in o.get('preserved_information') or [] if p.get('char') == ' '} | \
                 {c['src'][0] for c in cells if c.get('c') == ' ' and len(c.get('src') or []) == 1}
        res[which] = dict(
            A_coverage=not cov, B_reconstructed=rec is not None, fail_codes=sorted({f['code'] for f in fails}),
            C_match=(compare(rec, original) is None) if original is not None else None,
            C_code=compare(rec, original) if original is not None else None,
            D_alignment_errors=alignment(cells, ops, L, spaces),
            text_vs_cells=''.join(c['c'] for c in cells) == R[which],
            nfc=unicodedata.normalize('NFC', R[which]) == R[which])
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--quran', required=True)
    ap.add_argument('--dir', required=True)
    ap.add_argument('--json')
    a = ap.parse_args()
    J = lambda f: os.path.join(a.dir, f)
    sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
    run = json.load(open(J('normalization_run.json'), encoding='utf-8'))
    idn, cnt = run['identity'], run['counts']
    out = dict(run_id=idn['run_id'], commit=idn['commit'], E_hashes={}, verses=0)
    out['E_hashes'] = dict(
        quran=sha(a.quran) == idn['quran']['sha256'], ops=sha(J('normalization_ops.jsonl.gz')) == run['ops_log']['sha256'],
        cells=sha(J('normalization_cells.jsonl.gz')) == run['cells_log']['sha256'],
        previous=sha(J('normalization_previous_output.json')) == idn['previous_output']['sha256'])
    OPS = collections.defaultdict(lambda: {'display': [], 'analysis': []})
    with gzip.open(J('normalization_ops.jsonl.gz'), 'rt', encoding='utf-8') as f:
        for line in f:
            o = json.loads(line)
            OPS[o['verse']][o['representation']].append(o)
    PREV = json.load(open(J('normalization_previous_output.json'), encoding='utf-8'))
    C = collections.Counter()
    codes = collections.Counter()
    ex = {}
    by_rule = collections.Counter()
    QF = open(a.quran, encoding='utf-8')
    with gzip.open(J('normalization_cells.jsonl.gz'), 'rt', encoding='utf-8') as f:
        for line in f:
            R = json.loads(line)
            v = R['verse']
            R.pop('source', None)                     # لا يُقرأ حقل المصدر في الخلايا
            # المصحف يُقرأ بعد البناء، للمقارنة وحدها (الترتيب نفسه في الملفين)
            ql = QF.readline().rstrip('\n').split('\t')
            assert f'{ql[0]}:{ql[1]}' == v, (v, ql[:2])
            original = ql[2]
            res = check_verse(R, OPS[v], original)
            C['verses'] += 1
            for which, x in res.items():
                for key in ('A_coverage', 'B_reconstructed', 'C_match', 'text_vs_cells', 'nfc'):
                    C[f'{which}:{key}:{"ok" if x[key] else "fail"}'] += 1
                C[f'{which}:D_alignment_errors'] += x['D_alignment_errors']
                for c_ in x['fail_codes'] + ([x['C_code']] if x['C_code'] else []):
                    codes[f'{which}:{c_}'] += 1
                    ex.setdefault(f'{which}:{c_}', v)
            for o in OPS[v]['display']:
                by_rule[o['rule_id']] += 1
            words = [w for w in R['display'].split(' ') if w]
            prev = PREV[v].split(' ')
            if len(prev) == len(words):
                C['words'] += len(words)
                C['words_changed'] += sum(1 for w, p in zip(words, prev) if w != p)
            else:
                C['word_count_mismatch'] += 1
    n = C['verses']
    out.update(verses=n, counts=dict(C), failure_codes=dict(codes), failure_examples=ex,
               F_counts=dict(verses=n == cnt['verses'], ops_total=sum(by_rule.values()) == cnt['operations']['total'],
                             ops_by_rule=dict(by_rule) == cnt['operations']['by_rule'], words=C['words'] == cnt['words'],
                             words_changed=C['words_changed'] == cnt['words_changed']['normalized_output']))
    bad = 0
    print('هوية التشغيل', idn['run_id'], '· الالتزام', idn['commit'][:10])
    for k, ok in out['E_hashes'].items():
        print(('OK  ' if ok else 'BAD ') + f'E بصمة {k}')
        bad += not ok
    for which in ('display', 'analysis'):
        for key, name in (('A_coverage', 'A تغطية المواضع'), ('B_reconstructed', 'B إعادة البناء دون استعارة'),
                          ('C_match', 'C مطابقة المستعاد للمصدر'), ('text_vs_cells', 'النص يساوي الخلايا'), ('nfc', 'NFC')):
            ok = C[f'{which}:{key}:ok'] == n
            bad += not ok
            print(('OK  ' if ok else 'BAD ') + f'{name} ({which}): {C[f"{which}:{key}:ok"]}/{n}')
        ok = C[f'{which}:D_alignment_errors'] == 0
        bad += not ok
        print(('OK  ' if ok else 'BAD ') + f'D المحاذاة ({which}): أخطاء {C[f"{which}:D_alignment_errors"]}')
    for k, ok in out['F_counts'].items():
        bad += not ok
        print(('OK  ' if ok else 'BAD ') + f'F الأعداد: {k}')
    if codes:
        print('رموز الإخفاق:', dict(codes), 'أمثلة:', ex)
    out['all_ok'] = bad == 0
    if a.json:
        json.dump(out, open(a.json, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('ALL OK' if not bad else f'FAILED {bad}')
    return 0 if not bad else 1


if __name__ == '__main__':
    sys.exit(main())
