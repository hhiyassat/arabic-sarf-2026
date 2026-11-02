#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tools/check_coverage.py — فحص سجل التغطية (coverage/registry.jsonl): يمنع إخفاء النقص.

لكل بابٍ أو سمةٍ أو علاقةٍ سطرٌ واحد، وحالته واحدةٌ من خمس مراتب، ولكل مرتبةٍ ما يثبتها:

    unrepresented  غير ممثَّل في المعمار         تعريفٌ فقط
    represented    ممثَّل، وقاعدته غير مكتوبة    + التمثيل المطلوب
    rule_written   القاعدة مكتوبة، غير منفَّذة   + القاعدة ومرجعها
    implemented    منفَّذ، غير مختبَر           + الشيفرة (ملفٌّ ورمزٌ موجودان)
    tested         مختبَر في نطاقٍ معلوم         + الاختبار (ملفٌّ ونصّ الفحص فيه) والنطاق؛ والقياس إن ذُكر يجب أن يوجد،
                                                ولا يُدَّعى نطاق «القرآن كله» بلا قياسٍ مسجَّل

ويفشل الفحص إن:
  - غابت مرحلةٌ من المراحل الثلاثين، أو بابٌ من قائمة الحصر (coverage/checklist.json)؛
  - ادُّعيت مرتبةٌ بلا ما يثبتها، أو أشار السجل إلى ملفٍّ أو رمزٍ أو فحصٍ أو مقياسٍ غير موجود؛
  - تكرّر معرّف، أو جاءت حالةٌ غير معروفة.

    python3 tools/check_coverage.py              # الفحص، ويكتب coverage/STATUS.md
    python3 tools/check_coverage.py --run        # ويشغّل ملفات الاختبار المذكورة، فيفشل إن فشل أحدها
    python3 tools/check_coverage.py --stage 13   # تفصيل مرحلة
"""
import argparse, json, os, re, subprocess, sys, collections

H = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REG = os.path.join(H, 'coverage', 'registry.jsonl')
CHK = os.path.join(H, 'coverage', 'checklist.json')
OUT = os.path.join(H, 'coverage', 'STATUS.md')

RANK = ['unrepresented', 'represented', 'rule_written', 'implemented', 'tested']
AR = {'unrepresented': 'غير ممثَّل', 'represented': 'ممثَّل بلا قاعدة', 'rule_written': 'قاعدة غير منفَّذة',
      'implemented': 'منفَّذ غير مختبَر', 'tested': 'مختبَر في نطاق'}
FIELDS = ('id', 'stage', 'topic', 'definition', 'status', 'representation', 'rule', 'conditions', 'reference', 'code',
          'tests', 'scope', 'measurement', 'positive', 'contrast', 'ambiguity', 'open')


def load(p):
    rows = []
    for n, l in enumerate(open(p, encoding='utf-8'), 1):
        if l.strip():
            try:
                rows.append(json.loads(l))
            except ValueError as e:
                rows.append({'_bad': f'سطر {n}: JSON غير صالح ({e})'})
    return rows


def symbol_in(path, sym):
    s = open(path, encoding='utf-8').read()
    return re.search(rf'^\s*(def|class)\s+{re.escape(sym)}\b|^{re.escape(sym)}\s*=', s, re.M) is not None


def resolve_json(path, keys):
    x = json.load(open(path, encoding='utf-8'))
    for k in keys:
        if not isinstance(x, dict) or k not in x:
            return False
        x = x[k]
    return True


def check(rows, checklist):
    """→ (الأخطاء، التنبيهات، السطور بمراحلها)"""
    errs, warns = [], []
    stages = {int(k): v for k, v in checklist['stages'].items()}
    seen = collections.Counter(r.get('id') for r in rows)
    for r in rows:
        if '_bad' in r:
            errs.append(r['_bad']); continue
        rid = r.get('id', '?')
        E = lambda m: errs.append(f'{rid}: {m}')
        if seen[rid] > 1:
            E('معرّفٌ مكرَّر')
        unknown = set(r) - set(FIELDS)
        if unknown:
            E('حقولٌ غير معروفة: ' + '، '.join(sorted(unknown)))
        st = r.get('status')
        if st not in RANK:
            E(f'حالةٌ غير معروفة: {st}'); continue
        if r.get('stage') not in stages:
            E(f'مرحلةٌ غير معروفة: {r.get("stage")}')
        for f in ('topic', 'definition'):
            if not r.get(f):
                E(f'«{f}» فارغ')
        k = RANK.index(st)
        if k >= 1 and not r.get('representation'):
            E(f'{AR[st]} بلا «representation»')
        if k >= 2:
            for f in ('rule', 'reference'):
                if not r.get(f):
                    E(f'{AR[st]} بلا «{f}»')
        if k >= 3:
            if not r.get('code'):
                E(f'{AR[st]} بلا «code»')
            for c in r.get('code') or []:
                f, _, sym = c.partition(':')
                p = os.path.join(H, f)
                if not os.path.isfile(p):
                    E(f'الشيفرة غير موجودة: {f}')
                elif sym and not symbol_in(p, sym):
                    E(f'الرمز «{sym}» غير معرَّف في {f}')
        elif r.get('code'):
            E(f'{AR[st]} ومعه «code»: إن وُجدت الشيفرة فالمرتبة «منفَّذ» على الأقل')
        if k == 4:
            if not r.get('tests'):
                E('مختبَر بلا «tests»')
            if not r.get('scope'):
                E('مختبَر بلا «scope» (النطاق المعلوم)')
            for t in r.get('tests') or []:
                f, _, needle = t.partition('::')
                p = os.path.join(H, f)
                if not os.path.isfile(p):
                    E(f'ملف الاختبار غير موجود: {f}')
                elif needle and needle not in open(p, encoding='utf-8').read():
                    E(f'نصّ الفحص «{needle}» غير موجود في {f}')
            if 'القرآن كله' in (r.get('scope') or '') and not r.get('measurement'):
                E('النطاق «القرآن كله» بلا قياسٍ مسجَّل («measurement»)')
            if not r.get('positive'):
                warns.append(f'{rid}: مختبَر بلا شواهد موجبة')
        elif r.get('tests'):
            E(f'{AR[st]} ومعه «tests»: إن وُجد الاختبار فالمرتبة «مختبَر»')
        for m in r.get('measurement') or []:
            f, _, keys = m.partition('#')
            p = os.path.join(H, f)
            if not os.path.isfile(p):
                E(f'ملف القياس غير موجود: {f}')
            elif keys and not resolve_json(p, keys.split('.')):
                E(f'المفتاح «{keys}» غير موجود في {f}')
    by_stage = collections.defaultdict(list)
    for r in rows:
        if '_bad' not in r:
            by_stage[r.get('stage')].append(r)
    for s, (name, topics) in sorted(stages.items()):
        if not by_stage.get(s):
            errs.append(f'المرحلة {s} «{name}» بلا أي سطر في السجل')
        have = {r['topic'] for r in by_stage.get(s, [])}
        for t in topics:
            if t not in have:
                errs.append(f'المرحلة {s} «{name}»: الباب «{t}» من قائمة الحصر غائبٌ عن السجل')
    return errs, warns, by_stage


def run_tests(rows):
    files = sorted({t.partition('::')[0] for r in rows for t in r.get('tests') or []})
    bad = []
    for f in files:
        p = subprocess.run([sys.executable, os.path.join(H, f)], capture_output=True, text=True, cwd=H)
        print(('OK  ' if p.returncode == 0 else 'BAD ') + f)
        if p.returncode:
            bad.append(f)
    return bad


def status_md(rows, stages, by_stage):
    C = collections.Counter(r['status'] for r in rows if '_bad' not in r)
    L = ['# حال التغطية', '',
         'مولَّد من `coverage/registry.jsonl` بـ`python3 tools/check_coverage.py`؛ لا يُحرَّر باليد.',
         'وجود الباب في السجل لا يعني تنفيذه: المرتبة هي الحكم، ولكلٍّ منها ما يثبتها.', '',
         '| المرتبة | العدد |', '|---|---:|'] + [f'| {AR[k]} | {C[k]} |' for k in RANK] + \
        [f'| **المجموع** | **{sum(C.values())}** |', '',
         '| # | المرحلة | ' + ' | '.join(AR[k] for k in RANK) + ' |', '|---:|---|' + '---:|' * len(RANK)]
    for s, (name, _) in sorted(stages.items()):
        c = collections.Counter(r['status'] for r in by_stage.get(s, []))
        L.append(f'| {s} | {name} | ' + ' | '.join(str(c[k] or '') for k in RANK) + ' |')
    L.append('')
    for s, (name, _) in sorted(stages.items()):
        L += [f'## {s}. {name}', '', '| المعرّف | الباب | المرتبة | الشيفرة | المسائل غير المحسومة |', '|---|---|---|---|---|']
        for r in sorted(by_stage.get(s, []), key=lambda r: (RANK.index(r['status']), r['id'])):
            L.append(f"| {r['id']} | {r['topic']} | {AR[r['status']]} | {'، '.join('`' + c + '`' for c in r.get('code') or []) or '—'} | "
                     f"{'؛ '.join(r.get('open') or []) or '—'} |")
        L.append('')
    return '\n'.join(L)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--run', action='store_true')
    ap.add_argument('--stage', type=int)
    ap.add_argument('--no-write', action='store_true')
    a = ap.parse_args()
    rows, checklist = load(REG), json.load(open(CHK, encoding='utf-8'))
    stages = {int(k): v for k, v in checklist['stages'].items()}
    errs, warns, by_stage = check(rows, checklist)
    if a.stage:
        for r in by_stage.get(a.stage, []):
            print(f"{r['id']}\t{AR.get(r['status'], r['status'])}\t{r['topic']}")
    if a.run:
        errs += [f'الاختبار فشل: {f}' for f in run_tests(rows)]
    if not a.no_write:
        open(OUT, 'w', encoding='utf-8').write(status_md(rows, stages, by_stage))
    C = collections.Counter(r.get('status') for r in rows)
    print('، '.join(f'{AR[k]}: {C[k]}' for k in RANK) + f' — المجموع {len(rows)}')
    for w in warns:
        print('تنبيه:', w)
    for e in errs:
        print('خطأ:', e)
    print('ALL OK' if not errs else f'FAILED {len(errs)}')
    sys.exit(1 if errs else 0)
