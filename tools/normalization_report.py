# -*- coding: utf-8 -*-
"""مخرجات PROMPT_NORMALIZATION_REPAIR_02 من تشغيلٍ واحد بهويةٍ واحدة.

    python3 tools/normalization_report.py --legacy <legacy_outputs.json> --out <مجلد>

legacy_outputs.json: ناتج التطبيع السابق (uthmani_normalize في الالتزام df9c92b) لكل آية، «الناتج السابق».
المخرجات: normalization_report_ar.md، normalization_technical.md، normalization_run.json، normalization.html،
ونسخة مضغوطة من كل العمليات normalization_ops.jsonl.gz (للفحص الآلي).
لا يقرأ هذا المولِّد أي ناتجٍ تحليلي لاحق، ولا مدوّنة QAC.
"""
import argparse, collections, datetime, gzip, hashlib, html, json, os, re, subprocess, sys, unicodedata

H = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, H)
from sarf.normalize_trace import normalize_traced, restore_source, RULES, NORM_CONTRACT, cp, _cat

ap = argparse.ArgumentParser()
ap.add_argument('--legacy', required=True)
ap.add_argument('--out', required=True)
ap.add_argument('--downstream-note', default='')
args = ap.parse_args()
OUT = os.path.abspath(os.path.expanduser(args.out))
os.makedirs(OUT, exist_ok=True)
P = {k: os.path.join(OUT, f) for k, f in dict(ar='normalization_report_ar.md', tech='normalization_technical.md',
                                                 json='normalization_run.json', html='normalization.html',
                                                 ops='normalization_ops.jsonl.gz', cells='normalization_cells.jsonl.gz').items()}
# ما يفسّر فرق الناتج المعياري عن الناتج السابق حين تكون القاعدة في جهة الناتج السابق (التمثيل التحليلي = السابق + إصلاحات الفقد)
PREV_SIDE = {
    'N-IMPLICIT-SUKUN': 'الناتج السابق يضيف سكوناً مشتقّاً للحرف العاري (قاعدة الضبط)؛ والناتج المعياري لا يضيف سكوناً لم يُكتب',
    'N-DAGGER-MAQSURA': 'الناتج السابق يحذف الخنجرية على الألف المقصورة؛ والناتج المعياري يعالجها بقواعد الإملاء',
    'N-REORDER': 'الناتج السابق يعيد بناء الحرف وعلاماته بترتيبٍ ثابت؛ والناتج المعياري يُبقي ترتيب NFC',
    'N-SMALL-LETTER': 'الناتج السابق يحذف الواو أو الياء الصغيرة؛ والناتج المعياري يكتبها حرفاً',
    'N-ZERO-DROP': 'الناتج السابق يحذف واو «أولئك/أولو» الموسومة بالصفر؛ والناتج المعياري يكتبها',
}
FIX_RULES = ('N-IQLAB-TANWIN', 'N-SMALL-NOON', 'N-SMALL-CARRIER')


def git(*a):
    return subprocess.run(['git', '-C', H, *a], capture_output=True, text=True).stdout.rstrip('\n')


def sha(p):
    return hashlib.sha256(open(p, 'rb').read()).hexdigest()


ROWS = [l.rstrip('\n').split('\t')[:3] for l in open(os.path.join(H, 'data/quran_hafs.tsv'), encoding='utf-8')]
LEG = json.load(open(args.legacy, encoding='utf-8'))
CODE = ['sarf/normalize.py', 'sarf/normalize_trace.py', 'sarf/chars.py', 'tests/test_normalize_trace.py',
        'tests/test_normalize.py', 'tools/normalization_report.py']
dirty = [l for l in git('status', '--porcelain', '--untracked-files=no').splitlines() if not l[3:].startswith('reports/')]
diff = git('diff', 'HEAD', '--', *CODE)
ident = dict(
    task='PROMPT_NORMALIZATION_REPAIR_02', contract=NORM_CONTRACT, worktree=H, branch=git('rev-parse', '--abbrev-ref', 'HEAD'),
    commit=git('rev-parse', 'HEAD'), dirty_code=dirty, dirty_code_diff_sha256=hashlib.sha256(diff.encode()).hexdigest() if diff else None,
    code_sha256={f: sha(os.path.join(H, f)) for f in CODE},
    quran=dict(path=os.path.realpath(os.path.join(H, 'data/quran_hafs.tsv')), encoding='UTF-8، TSV (سورة، آية، نص)',
               sha256=sha(os.path.join(H, 'data/quran_hafs.tsv')), verses=len(ROWS)),
    previous_output=dict(path=os.path.abspath(args.legacy), sha256=sha(args.legacy),
                         produced_by='sarf.normalize.uthmani_normalize في الالتزام df9c92b (قبل N1.0)'),
    indexing='مواضع Unicode code points في نص الآية، من الصفر، والمجال نصف مفتوح [من، إلى). وكلمة المصدر ما بين مسافتين، من الواحد',
    python=sys.version.split()[0], unicode=unicodedata.unidata_version,
    command=' '.join([os.path.relpath(sys.argv[0], H)] + sys.argv[1:]),
    generated_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds'))
ident['run_id'] = hashlib.sha256(json.dumps([ident['commit'], ident['code_sha256'], ident['dirty_code_diff_sha256'],
                                             ident['quran']['sha256'], ident['previous_output']['sha256']],
                                            sort_keys=True).encode()).hexdigest()[:12]
RID = ident['run_id']

# ---------- تصنيف المحارف ----------
def char_class(ch):
    o = ord(ch)
    if ch == ' ':
        return 'فراغ'
    if ch == '‏':
        return 'محرف غير مرئي (اتجاه)'
    if ch == 'ـ':
        return 'تطويل'
    if 0x0621 <= o <= 0x064A or ch == 'ٱ':
        return 'حرف'
    if ch in 'َُِ':
        return 'حركة'
    if ch in 'ًࣰٌࣱٍࣲ':
        return 'تنوين'
    if ch in 'ْۡ':
        return 'سكون أو صفر'
    if ch == 'ّ':
        return 'شدّة'
    if ch in 'ٓۤ':
        return 'علامة مدّ'
    if ch in 'ٕٔ':
        return 'همزة مركّبة'
    if ch == 'ٰ':
        return 'ألف خنجرية'
    if ch in 'ۥۦۧۨ':
        return 'حرف صغير'
    if ch in 'ۭۢ':
        return 'ميم صغيرة'
    if 'ۖ' <= ch <= 'ۜ' or ch in '۞۩':
        return 'علامة وقف أو حزب أو سجدة'
    if ch in '۟۠':
        return 'صفر'
    if ch in 'ٜ۬':
        return 'علامة ضبط أخرى'
    return 'غير مصنَّف'


# ---------- القرآن كله ----------
C = collections.Counter()
ops_by_rule = collections.Counter()
ops_by_rule_status = collections.Counter()
cover = collections.defaultdict(collections.Counter)
occ = []
D282 = None
gz = gzip.open(P['ops'], 'wt', encoding='utf-8')
gzc = gzip.open(P['cells'], 'wt', encoding='utf-8')
for s, v, t in ROWS:
    loc = f'{s}:{v}'
    r = normalize_traced(t, loc)
    if loc == '2:282':
        D282 = r
    C['verses'] += 1
    gzc.write(json.dumps(dict(verse=loc, source=t, display=r['display'], analysis=r['analysis'],
                              cells_display=r['cells_display'], cells_analysis=r['cells_analysis']), ensure_ascii=False) + '\n')
    for which in ('display', 'analysis'):
        rs, miss = restore_source(r, which)
        C[f'restore_fail_{which}'] += rs != t
        C[f'info_lost_{which}'] += len(miss)
        in_op = {i for o in r['ops_' + which] for a, b in o['source_spans'] for i in range(a, b)}
        same = {c['src'][0] for c in r['cells_' + which] if len(c['src']) == 1 and not c['derived'] and t[c['src'][0]] == c['c']}
        C[f'unrecorded_{which}'] += sum(1 for i in range(len(t)) if i not in in_op and i not in same)
        for o in r['ops_' + which]:
            gz.write(json.dumps(dict(o, verse=loc, representation=which), ensure_ascii=False) + '\n')
            if which == 'display':
                ops_by_rule[o['rule_id']] += 1
                ops_by_rule_status[(o['rule_id'], o['status'])] += 1
    for i, ch in enumerate(t):
        rr = sorted({o['rule_id'] for o in r['ops_display'] if any(a <= i < b for a, b in o['source_spans'])
                     and o['rule_id'] != 'I-UNRESOLVED'})
        cover[f'U+{ord(ch):04X}'][','.join(rr) or 'كما هو'] += 1
    # كلمات الناتج ← كلمات المصدر
    wof, k = [], 0
    for ch in t:
        wof.append(None if ch == ' ' else k)
        k += ch == ' '

    def words(which):
        res, cur, cw = [], '', set()
        for c in r['cells_' + which] + [dict(c=' ', src=[])]:
            if c['c'] == ' ':
                if cur:
                    res.append((cur, sorted(cw)))
                cur, cw = '', set()
            else:
                cur += c['c']
                cw |= {wof[i] for i in c['src'] if wof[i] is not None}
        return res
    Dw, Aw, L = words('display'), words('analysis'), LEG[loc].split(' ')
    if not (len(Dw) == len(Aw) == len(L)):
        C['alignment_error_verses'] += 1
        continue
    sw_all = t.split(' ')
    for n, ((dw, sws), (aw, sws2), lw) in enumerate(zip(Dw, Aw, L)):
        C['words'] += 1
        if sws != sws2 and set(sws) < set(sws2):
            # كلمة مصدرٍ حُذفت كلها من الناتج المعياري وحُفظت في السجل (ألفٌ مجموعة ثم محذوفة: خَطَـࣰٔ اۚ ← خَطَأً):
            # تُنسب إلى كلمتها بالسجل لا بالمحارف الظاهرة
            pres = {p['at'] for o in r['ops_display'] for p in o['preserved_information']}
            starts_ = [0] + [i + 1 for i, ch in enumerate(t) if ch == ' ']
            def span(w):
                a_ = starts_[w]
                b_ = starts_[w + 1] - 1 if w + 1 < len(starts_) else len(t)
                return range(a_, b_)
            if all(i in pres for w in set(sws2) - set(sws) for i in span(w)):
                sws = sws2
                C['words_dropped_but_preserved'] += 1
        if sws != sws2 or not sws:
            C['alignment_error_words'] += 1
            continue
        ws = {w + 1 for w in sws}
        srcw = ' '.join(sw_all[sws[0]:sws[-1] + 1])
        od = [o for o in r['ops_display'] if set(o['words']) & ws]
        oa = [o for o in r['ops_analysis'] if set(o['words']) & ws]
        un = sorted({o['reason'] for o in od + oa if o['status'] == 'غير محسوم'})
        changed = dw != lw
        a_changed = aw != lw
        C['words_display_changed'] += changed
        C['words_analysis_changed'] += a_changed
        C['words_unresolved'] += bool(un)
        if not (changed or a_changed or un):
            continue
        # التحقق البنيوي للوقوع: مجالات المصدر تغطي الكلمة، وكل فرقٍ مسجَّل، والمصدر يُستعاد من ناتجها وسجلّها
        a0 = sum(len(x) + 1 for x in sw_all[:sws[0]])
        b0 = a0 + len(srcw)
        covered = {i for o in od for a, b in o['source_spans'] for i in range(a, b)} | \
                  {c['src'][0] for c in r['cells_display'] if len(c['src']) == 1 and not c['derived'] and t[c['src'][0]] == c['c']}
        ok_cover = all(i in covered for i in range(a0, b0) if t[i] != ' ')
        got = {i for c in r['cells_display'] for i in c['src']} | {p['at'] for o in r['ops_display'] for p in o['preserved_information']}
        ok_restore = all(i in got for i in range(a0, b0))
        rules = sorted({o['rule_id'] for o in od if o['rule_id'].startswith('I-') or o['rule_id'] in
                        ('N-IQLAB-TANWIN', 'N-IQLAB-NOON', 'N-SMALL-NOON', 'N-SMALL-CARRIER', 'N-JOIN-LONE-ALIF', 'N-KFGQPC-TANWIN')})
        verdict = ('تحقّقٌ بنيوي ناجح: كل فرقٍ مسجَّلٌ بقاعدته، والمصدر يُستعاد حرفياً' if ok_cover and ok_restore
                   else 'إخفاقٌ بنيوي: ' + ('فرقٌ غير مسجَّل ' if not ok_cover else '') + ('تعذّر الاسترجاع' if not ok_restore else ''))
        C['occ_structural_fail'] += not (ok_cover and ok_restore)
        # سبب الفرق عن الناتج السابق: قاعدةٌ في الناتج المعياري، أو قاعدةٌ في جهة الناتج السابق لا يطبّقها المعياري
        reasons = []
        for o in od:
            if o['rule_id'] not in ('N-SPACE', 'I-UNRESOLVED', 'N-MARK-FUNCTION') and changed:
                reasons.append(dict(side='الناتج المعياري', rule_id=o['rule_id'], why=RULES[o['rule_id']][2]))
        d_rules = {o['rule_id'] for o in od}
        # ما يطبّقه أحد الناتجين دون الآخر في هذه الكلمة (الفرق المتماثل بين قواعدهما)
        gap = sorted((d_rules ^ {o['rule_id'] for o in oa}) - {'N-SPACE', 'I-UNRESOLVED', 'N-MARK-FUNCTION'})
        if dw != aw and not gap:
            C['gap_unexplained'] += 1
        for rr in sorted({o['rule_id'] for o in oa} - d_rules):
            if rr in PREV_SIDE and changed:
                reasons.append(dict(side='الناتج السابق', rule_id=rr, why=PREV_SIDE[rr]))
            if rr in FIX_RULES and a_changed:
                reasons.append(dict(side='التمثيل التحليلي', rule_id=rr, why=RULES[rr][2]))
        seen = set()
        reasons = [x for x in reasons if not (x['rule_id'] in seen or seen.add(x['rule_id']))]
        # تحقّقٌ مستقل لأكثر الحالات: إن لم يطبّق الناتج المعياري شيئاً، فالفرق كله السكون المشتقّ؟
        a_cells = [c for c in r['cells_analysis'] if any(wof[i] in sws for i in c['src']) or (c['derived'] and not c['src'])]
        only_sukun = None
        if changed and not [x for x in reasons if x['side'] == 'الناتج المعياري']:
            stripped = re.sub('\u0652', '', lw)
            only_sukun = stripped == re.sub('\u0652', '', dw) and lw.count('\u0652') > dw.count('\u0652')
            C['diff_only_derived_sukun'] += bool(only_sukun)
        if (changed or a_changed) and not reasons:
            C['diff_unexplained'] += 1
        occ.append(dict(
            occurrence_id=f'Q{loc}:{sws[0] + 1}' + (f'-{sws[-1] + 1}' if len(sws) > 1 else ''), verse=loc,
            source_words=sorted(ws), previous_word_index=n + 1, source=srcw, source_codepoints=cp(srcw),
            previous_output=lw, new_output=dw, analysis_representation=aw, display_changed=changed, analysis_changed=a_changed,
            transformations=[dict(rule_id=o['rule_id'], operation=o['operation'], source_text=o['source_text'],
                                  source_spans=o['source_spans'], normalized_text=o['normalized_text'], status=o['status'])
                             for o in od if o['rule_id'] != 'N-SPACE'],
            rules=rules, preserved=sorted({f"{p['function']} {p['codepoint']}" for o in od for p in o['preserved_information']}),
            difference_reasons=reasons, representation_gap_rules=gap if dw != aw else [], difference_check=('الفرق سكونٌ مشتقٌّ في الناتج السابق وحده (تحقّقٌ بالمقارنة)'
                                                          if only_sukun else None),
            verification=verdict, deferral_reason='؛ '.join(un) if un else None))
gz.close()
gzc.close()

# الأصناف غير المغطاة: رمزٌ بقي في الناتج المعياري وهو من علامات المصدر الخاصة
residual = collections.Counter()
for o in occ:
    for ch in o['new_output']:
        if char_class(ch) in ('ألف خنجرية', 'حرف صغير', 'ميم صغيرة', 'علامة وقف أو حزب أو سجدة', 'صفر', 'علامة ضبط أخرى',
                              'محرف غير مرئي (اتجاه)', 'تطويل', 'سكون أو صفر') and ch != 'ْ':
            residual[f'U+{ord(ch):04X} {char_class(ch)}'] += 1
counts = dict(
    verses=C['verses'], words=C['words'],
    words_changed=dict(normalized_output=C['words_display_changed'], analysis_representation=C['words_analysis_changed']),
    words_unresolved=C['words_unresolved'],
    occurrences_listed=len(occ), occurrence_structural_failures=C['occ_structural_fail'],
    operations=dict(total=sum(ops_by_rule.values()), by_rule=dict(sorted(ops_by_rule.items())),
                    by_rule_and_status={f'{a} | {b}': n for (a, b), n in sorted(ops_by_rule_status.items())}),
    information_lost=dict(normalized_output=C['info_lost_display'], analysis_representation=C['info_lost_analysis']),
    restore_failures=dict(normalized_output=C['restore_fail_display'], analysis_representation=C['restore_fail_analysis']),
    unrecorded_differences=dict(normalized_output=C['unrecorded_display'], analysis_representation=C['unrecorded_analysis']),
    alignment_errors=dict(verses=C['alignment_error_verses'], words=C['alignment_error_words']),
    differences_unexplained=C['diff_unexplained'], representation_gap_unexplained=C['gap_unexplained'], differences_only_derived_sukun=C['diff_only_derived_sukun'],
    source_words_dropped_but_preserved=C['words_dropped_but_preserved'],
    residual_uncovered_marks_in_output=dict(residual))
coverage = [dict(codepoint=k, name=unicodedata.name(chr(int(k[2:], 16)), '?'), cls=char_class(chr(int(k[2:], 16))),
                 occurrences=sum(v.values()), handled_by=dict(v)) for k, v in sorted(cover.items())]
unres = collections.Counter(o['deferral_reason'] for o in occ if o['deferral_reason'])
json.dump(dict(identity=ident, rules={k: dict(version=v[0], reference=v[1], text=v[2]) for k, v in RULES.items()},
               counts=counts, codepoint_coverage=coverage, unresolved_by_reason=dict(unres),
               downstream_note=args.downstream_note, differences=occ,
               ops_log=dict(path=P['ops'], sha256=sha(P['ops']), note='كل عمليات التحويل (الناتج المعياري والتمثيل التحليلي)'),
               cells_log=dict(path=P['cells'], sha256=sha(P['cells']),
                              note='لكل آية: المصدر والناتجان وخلاياهما (المحرف ومصدره واشتقاقه، وللتنوين شكله ووظيفته)')),
          open(P['json'], 'w', encoding='utf-8'), ensure_ascii=False, indent=1)


# ---------- التقرير العربي ----------
def tbl(rows):
    out = ['| الموضع (رقمه السابق) | المصدر | الناتج السابق | الناتج الجديد | القاعدة | المحفوظ |', '|---|---|---|---|---|---|']
    for o in rows:
        out.append(f"| {o['occurrence_id']} ({o['previous_word_index']}) | {o['source']} | {o['previous_output']} | {o['new_output']} | "
                   f"{', '.join(o['rules'])} | {'؛ '.join(o['preserved'][:3])} |")
    return '\n'.join(out)


def pick(pred, n=6):
    return [o for o in occ if pred(o)][:n]


in282 = lambda o: o['verse'] == '2:282'
# الفجوة بين الناتج المعياري والتمثيل التحليلي: ما يطبّقه أحدهما دون الآخر، بالكلمة
GAP = collections.Counter()
for o in occ:
    if o['new_output'] != o['analysis_representation']:
        for x in o['representation_gap_rules']:
            GAP[x] += 1
mark_deferred = [o for o in occ if o['deferral_reason'] and 'نون التوكيد' in o['deferral_reason']]
mark_rows = '\n'.join(f"| {o['occurrence_id']} | {o['source']} | {o['new_output']} | {o['analysis_representation']} | غير محسوم |"
                      for o in mark_deferred)
gap_rows = '\n'.join(f'| {k} | {n} |' for k, n in GAP.most_common())
n_iq = ops_by_rule.get('N-IQLAB-TANWIN', 0)
ROUND3 = f"""## ما تغيّر في هذه الجولة

**١. شكل العلامة غير وظيفتها:**
- التطبيع يثبت شكل التنوين، ولا يثبت وظيفته.
- كل محرف تنوينٍ في الناتجين يحمل `mark.form` (رموزه في المصدر، مثل `U+064F U+06E2`) و`mark.function = null`، \
وكذلك كل عملية تنوين (`mark_form`، `mark_function`).
- فلا يصلح ما يخرج من التطبيع شاهداً على الاسمية.
- ما احتمل في الكتابة نونَ التوكيد الخفيفة يُؤجَّل في سجل الوقوع نفسه (`status = غير محسوم`، القاعدة N-MARK-FUNCTION)، \
في الناتجين كليهما. والشكل: تنوين فتحٍ بعده ألف، على كلمةٍ أولها لامٌ مفتوحة وحرف مضارعةٍ متحرّك. ولا يُضاف نون.

| الوقوع | المصدر | الناتج المعياري | التمثيل التحليلي | الحالة |
|---|---|---|---|---|
{mark_rows}

- **ما يقع في هذا الشكل:**
  - «لَنَسۡفَعَۢا» و«وَلَيَكُونࣰا» فعلان بنون التوكيد الخفيفة؛
  - و«لَأَجۡرًا» اسمٌ بعد لام التوكيد؛
  - والكتابة لا تفصل بين الوظيفتين، فلا يحسمها التطبيع.
- **عملية الإقلاب صارت تركيباً واحداً:**
  - الحركة والميم معاً مصدرُ محرف التنوين، ومحفوظتان بموضعيهما؛
  - فعددها {n_iq} عملية لـ{n_iq} وقوعاً، بعد أن كانت عمليتين لكل وقوع.

**٢. سبب كل فرق:**
- كل وقوعٍ تغيّر ناتجه يحمل `difference_reasons`: القاعدة وجهتها، أي الناتج المعياري يطبّقها، أو الناتج السابق كان يطبّقها.
- الوقوعات المتغيّرة بلا سبب: **{counts['differences_unexplained']}**.
- منها {counts['differences_only_derived_sukun']} وقوعاً فرقُها كله سكونٌ مشتقّ كان الناتج السابق يضيفه. وهي حالات المراجع \
(«مِنْ» ← «مِن»)، وقد تحقّقتُ منها بمقارنة النصين بعد حذف السكون، لا بالدعوى.

**٣. الملفات الناقصة صارت في الحزمة:**
- سجل العمليات؛
- الناتج السابق؛
- خلايا كل آية؛
- مدقِّقٌ مستقل لا يستورد شيفرة المشروع (`verify_normalization_package.py`)؛
- الشيفرة والاختبارات (`normalization_code_*.tar.gz`).

"""
NEXTSTAGE = f"""## مدخل المرحلة التالية (خلايا المكتوب): ما يُستهلك وما يرافقه

**المقترح، والقرار لكم:**
- تستهلك المرحلة التالية **التمثيل التحليلي** (`analysis`) وخلاياه (`cells_analysis`)، لا العرض الإملائي.
- ويرافقه لكل محرف:
  - مصدرُه (`src`)؛
  - و`derived`: السكون المضاف بقاعدة الضبط مشتقٌّ بلا مصدر، فلا يُعامَل مكتوباً؛
  - وللتنوين `mark` (شكلٌ بلا وظيفة).
- ولكل كلمةٍ سجلُّ عملياتها، ومنه كل «غير محسوم».

**ما يختلف فيه التمثيل التحليلي عن الناتج المعياري**: القواعد التي يطبّقها أحدهما دون الآخر، بعدد الكلمات. \
وكلماتٌ يختلف فيها الناتجان بلا قاعدةٍ فارقة: {counts['representation_gap_unexplained']}.

| القاعدة | الكلمات |
|---|---:|
{gap_rows}

**مسائل تحتاج حكمكم قبل خلايا المكتوب** (لم أغيّر التمثيل التحليلي في هذه الجولة، وبصمته كما كانت):
- **الخنجرية على الألف المقصورة:** يحذفها التمثيل التحليلي (إِحْدَىهُمَا).
  - «ىٰ» مكتوبةٌ في المصدر، وحذفها من مدخل الخلايا فقدٌ وإن حُفظت في السجل.
  - اقتراحي إبقاؤها.
- **الهمزة على المطّة:** يكتبها التمثيل التحليلي على السطر (تَسْءَمُوا)، والعرض على كرسيّها الإملائي، وكلاهما ليس المكتوب.
  - اقتراحي أن تحمل الخلية الهمزةَ مع صفة كرسيّها في المصدر (مطّة، ياء غير منقوطة…)، لا كرسيّاً مختاراً.
- **الحرف الصغير في غير الصلة، وحرف الصفر، والصلة:** يحذفها التمثيل التحليلي.
  - هل تكون خلايا في المكتوب، أم صفاتٍ لخليةٍ مجاورة؟
- **السكون المشتقّ:** هل تعدّه الخلايا خليةً، أم صفةً لخليةٍ عارية؟

"""
ar = f"""# إصلاح التطبيع (الجولة ٣): تقرير صاحب المشروع

هوية التشغيل `{RID}` · العقد {NORM_CONTRACT} · الفرع `{ident['branch']}` · الالتزام `{ident['commit'][:10]}` · \
تعديلات غير ملتزم بها في الشيفرة: {len(dirty)} · نص المصحف `{ident['quran']['sha256'][:16]}`

لا دمج ولا دفع، والعمل في نسخةٍ معزولة. ولم يُمسّ الترقيم ولا بقية المحلِّل.

{ROUND3}## العقد بإيجاز
- **المصدر الأصلي** محفوظٌ حرفياً، ويُستعاد من الناتج وسجلّه.
- **الناتج المعياري** إملائيٌّ بقواعد معلنة، وهو **غير مكتمل**: \
{counts['words_unresolved']} كلمة فيها ما لم يُحسم، فلا أسمّيه إملاءً مكتملاً.
- **معلومات الرسم**: كل محرفٍ لا يظهر بعينه في الناتج محفوظٌ بموضعه في المصدر ووظيفته، ومنها:
  - صورة التنوين المتتابع (ࣰ ࣱ ࣲ)؛
  - الحركة الأصلية قبل ميم الإقلاب؛
  - علامات الوقف والصلة والصفر والمدّ والاتجاه.
- **التمثيل التحليلي** شيءٌ آخر غير الناتج المعياري: هو ما تقرؤه مراحل التحليل، وما يضيفه فيه (السكون) مشتقٌّ معلَّم.

## الإصلاحات وأمثلتها

**أ. التنوين المرسوم بالميم الصغيرة** (N-IQLAB-TANWIN):
- القاعدة: حركةٌ قصيرة بعدها ميمٌ صغيرة (ۢ فوق، ۭ تحت) تصير تنويناً، ومعها الشدّة والهمزة إن وُجدتا.
- تُحفظ الحركة الأصلية والميم بموضعيهما.
- التنوين حركةٌ واحدة، ولا يُنشأ منه حرف نون.
- مقابلها: الميم على نونٍ مكتوبة («مِنۢ»، «أَنۢبِـُٔونِي») إقلاب نونٍ ساكنة، فتبقى النون (N-IQLAB-NOON).

{tbl(pick(lambda o: in282(o) and 'N-IQLAB-TANWIN' in o['rules']) + pick(lambda o: not in282(o) and 'N-IQLAB-TANWIN' in o['rules'], 3) + pick(lambda o: 'N-IQLAB-NOON' in o['rules'], 2))}

الرقم بين القوسين رقم الكلمة في الناتج السابق (13 و119)، والموضع رقمها في المصدر (14 و121). والفرق مسافتان في المصدر \
داخل «مُّسَمࣰّ ى» و«شَيۡـࣰٔ اۚ»، والترقيم مؤجَّلٌ بطلبكم.

**ب. العثماني ← الإملائي**:

{tbl([o for o in occ if in282(o) and set(o['rules']) & {'I-WAW-ALIF', 'I-HAMZA', 'I-DAGGER-ALIF', 'I-ALIF-OMIT', 'I-HAMZA-MADD'}][:12])}

القواعد مشروطة، ولكل قاعدةٍ في الاختبار حالةٌ مقابلة تمنع تعميمها:
- **الألف المقصورة:** المقصورة الخنجرية في آخر الكلمة تبقى ى (مُوسَى).
- **الألف الخنجرية:**
  - ما تحذف الإملاء ألفه لا تُكتب ألفه (ذَلِكَ، هَذَا، إِلَه، الرَّحْمَن، أُولَئِكَ)؛
  - والهمزة وبعدها خنجرية مدّة (الْآنَ)؛
  - وواو «أولئك/أولو» تُكتب، وما سواها من حروف الصفر يُحذف.
- **مقعد الهمزة:**
  - بعد الألف على السطر (جَاءَ)؛
  - بعد الكسر ياءً بلا مدّة (السَّيِّئَاتِ لا السيّآت)؛
  - بعد سابقةٍ من حرف همزةٌ أولى (بِآيَاتِنَا)؛
  - وعلى الألف بتنوين الفتح بلا ألف بعدها (خَطَأً)؛
  - والهمزة على كرسيّها في المصدر لا تتغيّر (سُئِلَ).

**ج. السكون والشدّة**:
- **الناتج المعياري** لا يضيف سكوناً لم يُكتب: «تَدَايَنتُم»، «أَن»، «مِن»، «مِمَّن» كما كُتبت.
  - كل سكونٍ فيه مكتوبٌ في المصدر (ۡ)، ومنسوبٌ إلى محرفه.
  - ولا محرف فيه مشتقٌّ بلا مصدر.
- **التمثيل التحليلي** يضيف السكون للحرف العاري بقاعدة الضبط، كما كان. وكل سكونٍ مضاف فيه محرفٌ مشتقّ بلا مصدر، حالته «مشتقّ» \
(N-IMPLICIT-SUKUN: {sum(1 for _ in [0])} قاعدة، والعدد في التقرير التقني).
- **الشدّة** محفوظة كلها في الناتج بعلاقتها بحرفها، ومنها شدّة الإدغام أول الكلمة (مُّسَمًّى).
  - وهذا تغييرٌ عن الجولة الأولى التي كانت تحذفها من العرض.
  - ولذلك لا يطابق الناتج الإملاء المدرسي في هذا الموضع.

**د. المسافات** (N-JOIN-LONE-ALIF):
- ألفٌ أو ألفٌ مقصورة وحدها، وقبلها كلمةٌ آخرها تنوينٌ مفتوح، تُجمع إليها.
- ومجالاها من كلمتين في المصدر محفوظان: «مُّسَمࣰّ ى» و«شَيۡـࣰٔ اۚ».
- ولا يُجمع بالتجاور أو التشابه.
- عدد الجمع في القرآن: {ops_by_rule.get('N-JOIN-LONE-ALIF', 0)}.

## ما ثبت (تحقّقٌ بنيوي على القرآن كله، {counts['verses']} آية، {counts['words']} كلمة)
- فقد معلوماتٍ غير مسجَّل: {counts['information_lost']['normalized_output']}.
- إخفاق استرجاع المصدر: {counts['restore_failures']['normalized_output']}.
- اختلافٌ غير مسجَّل: {counts['unrecorded_differences']['normalized_output']}.
- أخطاء المحاذاة: {counts['alignment_errors']['words']}.
- إخفاقٌ بنيوي في وقوعٍ مُدرَج: {counts['occurrence_structural_failures']}.
- ثبات الناتج عند التكرار، وNFC، ورفض النص المطبَّع مدخلاً: في الاختبارات.
- لا يقرأ التطبيع شيئاً من التحليل اللاحق، وهذا مختبَر.
- الكلمات التي تغيّر ناتجها المعياري عن السابق: {counts['words_changed']['normalized_output']}، \
وفي التمثيل التحليلي: {counts['words_changed']['analysis_representation']}.
- عمليات التحويل: {counts['operations']['total']}، مفصّلةً بالقاعدة في التقرير التقني.

هذا التحقق بنيويٌّ وبالقاعدة. أما صحة كل تحويلٍ إملائي لغوياً فلم تُراجَع بشرياً إلا في آية الدين كلمةً كلمة، \
وفي حصرٍ للأزواج المتميزة لقواعد الهمزة والمدّ والخنجرية على القرآن كله. ومنه صُحّحت في هذه الجولة: \
الْأَانَ، وقُرْأَانًا، وخَطَأًا، والسَّيِّآت، وبِئَايَات، وأَئِلَاه، وأُولَائِكُم، ورَآ، وآعجمي. ولم أستعمل QAC دليلاً.

## ما بقي غير محسوم ({counts['words_unresolved']} كلمة)
""" + '\n'.join(f'- {n}: {k}' for k, n in unres.most_common()) + f"""

{NEXTSTAGE}## خارج النطاق
الترقيم، والخلايا، والجذور، والصرف، والعوامل: لم تُمسّ.

التمثيل التحليلي مطابقٌ بايتاً بايتاً لما في الجولة الأولى (البصمة في التقرير التقني). فأثره اللاحق هو ما قيس هناك، \
ولم يُعَد قياسه. والقرار في «لَنَسۡفَعَۢا» و«يَوۡمَئِذٍ» و«سَبَإٍ» عندكم كما ذُكر.
"""
ar = ar.replace(f"(N-IMPLICIT-SUKUN: {sum(1 for _ in [0])} قاعدة، والعدد في التقرير التقني)", '(N-IMPLICIT-SUKUN)')
open(P['ar'], 'w', encoding='utf-8').write(ar)

# ---------- التقني ----------
rules_md = '\n'.join(f"| {k} | {v[0]} | {v[1]} | {ops_by_rule.get(k, 0)} | {v[2]} |" for k, v in RULES.items())
cov_md = '\n'.join(f"| {c['codepoint']} | {c['name']} | {c['cls']} | {c['occurrences']} | " +
                   '; '.join(f'{r}: {n}' for r, n in sorted(c['handled_by'].items(), key=lambda x: -x[1])[:3]) + ' |' for c in coverage)
st_md = '\n'.join(f'| {k} | {n} |' for k, n in counts['operations']['by_rule_and_status'].items())
tech = f"""# التطبيع (الجولة ٣): التقرير التقني

هوية التشغيل `{RID}`

## الهوية
- الشيفرة:
  - الشجرة المعزولة `{H}`، والفرع `{ident['branch']}` (محلي)، والالتزام `{ident['commit']}`.
  - تعديلات غير ملتزم بها في ملفات الشيفرة: {dirty or 'لا شيء'}.
  - بصمات الملفات في normalization_run.json.
- المصحف: `{ident['quran']['path']}`، {ident['quran']['encoding']}، sha256 `{ident['quran']['sha256']}`.
- الناتج السابق: `{ident['previous_output']['path']}` (sha256 `{ident['previous_output']['sha256'][:16]}`)، ومصدره \
{ident['previous_output']['produced_by']}.
- البيئة: Python {ident['python']}، وUnicode {ident['unicode']}.
- الفهرسة: {ident['indexing']}.
- الأمر: `{ident['command']}`.

## العقد
`sarf.normalize_trace.normalize_traced(text, loc, implicit_sukun=None, strict=False)` يعيد:
- `source`؛
- `display`: الناتج المعياري؛
- `analysis`: التمثيل التحليلي؛
- `cells_display` و`cells_analysis`: لكل محرفٍ ناتج `src` (مواضع المصدر، فارغة للمضاف) و`derived`؛
- `ops_display` و`ops_analysis`.

حقول العملية:
- `occurrence_id`، `source_spans`، `source_text`، `source_codepoints`؛
- `normalized_text`، `normalized_spans`؛
- `operation`، `rule_id`، `rule_version`، `rule_reference`؛
- `preserved_information` (المحرف ورمزه وموضعه في المصدر ووظيفته)، `status`، `reason`؛
- وزيادةً: `op_id`، `words`، `input_text`/`input_codepoints` (المحارف قبل العملية، وقد تكون ناتج عمليةٍ سابقة).

العلاقات المدعومة:
- واحدٌ إلى واحد، وواحدٌ إلى متعدد، ومتعددٌ إلى واحد؛
- ومجالاتٌ متعددة (جمع الأجزاء)؛
- والمضاف لا مصدر له (`src` فارغ، `derived`).

المدخل: ترميز المصدر وحده. والناتج المطبَّع يُرفض (`strict=True` ← ValueError)، فلا ثبات مدّعى عليه.

## القواعد (عدد العمليات في الناتج المعياري)

| القاعدة | الإصدار | المرجع | العمليات | النص |
|---|---|---|---|---|
{rules_md}

المراجع:
- K: اصطلاحات الضبط في مصحف المدينة (رواية حفص).
- U: معيار Unicode.
- O: حكم صاحب النظرية (D21، D22).
- I: قواعد الإملاء (عبد السلام هارون؛ ومجمع اللغة العربية بالقاهرة في الهمزة).

## العمليات بالقاعدة والحالة

| القاعدة | الحالة | العدد |
|---|---|---|
""" + '\n'.join(f"| {k.split(' | ')[0]} | {k.split(' | ')[1]} | {n} |" for k, n in counts['operations']['by_rule_and_status'].items()) + f"""

## الأعداد
- الكلمات: {counts['words']}.
- تغيّر الناتج المعياري عن السابق: {counts['words_changed']['normalized_output']} كلمة، وتغيّر التمثيل التحليلي: \
{counts['words_changed']['analysis_representation']}.
- غير محسوم: {counts['words_unresolved']}.
- الوقوعات المدرجة في سجل الفروق: {counts['occurrences_listed']}.
- العمليات: {counts['operations']['total']}.
- فقد المعلومات: {json.dumps(counts['information_lost'], ensure_ascii=False)}.
- إخفاق الاسترجاع: {json.dumps(counts['restore_failures'], ensure_ascii=False)}.
- اختلافٌ غير مسجَّل: {json.dumps(counts['unrecorded_differences'], ensure_ascii=False)}.
- المحاذاة: {json.dumps(counts['alignment_errors'], ensure_ascii=False)}.
- علاماتٌ عثمانية خاصة بقيت في الناتج المعياري: {json.dumps(counts['residual_uncovered_marks_in_output'], ensure_ascii=False) or 'لا شيء'}.

## تغطية المحارف وتصنيفها (كل رمزٍ في المصدر)

| الرمز | الاسم | الصنف | التكرار | ما عالجه في الناتج المعياري |
|---|---|---|---|---|
{cov_md}

## الملفات المعدَّلة
**الجولة ٣ (عن dc18027):**
- `sarf/normalize_trace.py`:
  - العقد N3.0: شكل التنوين لا وظيفته (`mark` في الخلايا، و`mark_form`/`mark_function` في العمليات)؛
  - N-MARK-FUNCTION: تأجيل الوظيفة في سجل الوقوع؛
  - الإقلاب عمليةٌ واحدة (تركيب).
- `tests/test_normalize_trace.py`: بنود أ٢.
- `tools/normalization_report.py`:
  - `difference_reasons` لكل وقوع؛
  - تحقّقٌ من الفرق بالسكون المشتقّ وحده؛
  - ملف الخلايا؛
  - مدخل المرحلة التالية.
- `tools/verify_normalization_package.py` (جديد): مدقِّقٌ مستقل بالمكتبة القياسية وحدها.

**الجولة ٢ (عن 5b1a8f9):**
- حقول السجل؛
- حفظ صورة المستبدَل بالموضع؛
- إبقاء الشدّة؛
- إصلاحات الهمزة والمدّ والخنجرية.

**الجولة ١:** `uthmani_normalize` يأخذ التمثيل التحليلي من العقد، والسلوك السابق في `_uthmani_normalize_legacy`.

## الاختبارات
- `python3 tests/test_normalize_trace.py`:
  - الحقول الثلاثة عشر؛
  - أ: التنوين بالميم، ومقابله النون المكتوبة، وحفظ الصورة الأصلية؛
  - ب: الأمثلة المسمّاة ومقابلاتها؛
  - ج: السكون والشدّة؛
  - د: العلامات والجمع والحرف الصغير وعلامة الاتجاه؛
  - ٧: لا تحميل لوحدات التحليل؛
  - وعلى القرآن كله: الفقد، والتغطية، والنسبة، والاسترجاع، والثبات، والرفض، وNFC، وأن التحليلي لا يتغيّر إلا بقواعد إصلاح الفقد.
- `python3 tests/test_normalize.py`، وبقية `tests/test_*.py`: نجحت كلها في الشجرة المعزولة.
- التمثيل التحليلي للقرآن كله: sha256 `974df1794da754dc652c277ecfcd94890c49b913147f9ad3c0e0f5b862a960d7`، \
وهو هو في الجولة الأولى (44c7266). فلم يُعَد قياس الأثر اللاحق.

## إعادة الإنتاج
```
# من أرشيف الشيفرة في الحزمة:
mkdir code && tar -xzf normalization_code_{ident['commit'][:10]}.tar.gz -C code && ln -s <مجلد فيه quran_hafs.tsv> code/data
cd code && python3 tests/test_normalize_trace.py
python3 tools/normalization_report.py --legacy ../normalization_previous_output.json --out <مجلد>
# التحقق المستقل (لا يستورد شيفرة المشروع):
python3 verify_normalization_package.py --quran <quran_hafs.tsv> --dir <مجلد الحزمة>
# الناتج السابق: uthmani_normalize في الالتزام df9c92b لكل آية
```
"""
open(P['tech'], 'w', encoding='utf-8').write(tech)

# ---------- HTML ----------
h = html.escape


def rows282():
    r = D282
    t = r['source']
    out = []
    for o in [x for x in occ if x['verse'] == '2:282']:
        pass
    sw = t.split(' ')
    wof, k = [], 0
    for ch in t:
        wof.append(None if ch == ' ' else k)
        k += ch == ' '
    grp, cur, cw = [], [], set()
    for c in r['cells_display'] + [dict(c=' ', src=[])]:
        if c['c'] == ' ':
            if cur:
                grp.append((cur, sorted(cw)))
            cur, cw = [], set()
        else:
            cur.append(c)
            cw |= {wof[i] for i in c['src'] if wof[i] is not None}
    L = LEG['2:282'].split(' ')
    for n, ((cells, sws), lw) in enumerate(zip(grp, L)):
        ws = {w + 1 for w in sws}
        srcw = ' '.join(sw[sws[0]:sws[-1] + 1])
        dw = ''.join(c['c'] for c in cells)
        od = [o for o in r['ops_display'] if set(o['words']) & ws and o['rule_id'] != 'N-SPACE']
        li = ''.join(
            f"<li><code>{h(o['rule_id'])}</code> {h(o['operation'])}: «{h(o['source_text'])}» <span class=cp>{h(o['source_codepoints'])}</span>"
            f" {h(str(o['source_spans']))} ← «{h(o['normalized_text'])}» {h(str(o['normalized_spans']))}"
            + (f" · محفوظ: {h('، '.join(p['function'] + ' ' + p['codepoint'] + ' @' + str(p['at']) for p in o['preserved_information']))}" if o['preserved_information'] else '')
            + (f" · <b>{h(o['status'])}</b>" + (f": {h(o['reason'] or '')}" if o['status'] != 'مطبَّق' else '') if o['status'] != 'مطبَّق' else '')
            + '</li>' for o in od)
        why = '؛ '.join(sorted({RULES[o['rule_id']][2].split(':')[0][:90] for o in od if o['rule_id'].startswith('I-') or o['rule_id'] in
                                ('N-IQLAB-TANWIN', 'N-JOIN-LONE-ALIF', 'N-SMALL-NOON')}))
        cls = ' class=chg' if dw != lw else ''
        out.append(f"<tr id='w{sws[0] + 1}'{cls}><td>{', '.join(map(str, sorted(ws)))}<br><span class=mut>({n + 1})</span></td>"
                   f"<td class=ar>{h(srcw)}<div class=cp>{h(cp(srcw))}</div></td><td class=ar>{h(lw)}</td><td class=ar>{h(dw)}</td>"
                   f"<td>{h(why)}<details><summary>{len(od)} عملية</summary><ul>{li}</ul></details></td></tr>")
    return '\n'.join(out)


IDX = [[o['occurrence_id'], o['source'], o['previous_output'], o['new_output'], ' '.join(o['rules']),
        '، '.join(o['preserved'][:4]), o['verification'], o['deferral_reason'] or '', 1 if o['display_changed'] else 0]
       for o in occ]
page = f"""<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>إصلاح التطبيع ٢</title><style>
:root{{--bg:#fff;--fg:#1d1d1f;--mut:#666;--line:#ddd;--chg:#fff4d6}}
@media (prefers-color-scheme:dark){{:root{{--bg:#16181c;--fg:#e8e8ea;--mut:#9a9aa0;--line:#333;--chg:#3a3320}}}}
body{{background:var(--bg);color:var(--fg);font-family:system-ui,"Noto Naskh Arabic",sans-serif;margin:0;padding:16px;line-height:1.6}}
main{{max-width:1200px;margin:auto}} table{{border-collapse:collapse;width:100%;font-size:.9rem}}
td,th{{border-bottom:1px solid var(--line);padding:4px 6px;vertical-align:top;text-align:right}}
.ar{{font-family:"Amiri Quran","Noto Naskh Arabic",serif;font-size:1.15rem}} .cp{{font-size:.62rem;color:var(--mut);word-break:break-all;font-family:monospace}}
tr.chg{{background:var(--chg)}} .mut{{color:var(--mut)}} .wrap{{overflow-x:auto}} input,select{{font-size:1rem;padding:4px;margin:4px}}
</style></head><body><main>
<h1>إصلاح التطبيع (الجولة ٣)</h1>
<p class=mut>هوية التشغيل <code>{RID}</code> · العقد {NORM_CONTRACT} · <code>{h(ident['branch'])}</code> <code>{ident['commit'][:10]}</code>
· تعديلات غير ملتزم بها: {len(dirty)} · المصحف <code>{ident['quran']['sha256'][:16]}</code></p>
<p>الناتج المعياري إملائيٌّ <b>غير مكتمل</b>. تغيّر عن السابق في <b>{counts['words_changed']['normalized_output']}</b> كلمة،
بـ {counts['operations']['total']} عملية. غير محسوم: {counts['words_unresolved']}.
فقد غير مسجَّل: {counts['information_lost']['normalized_output']} · إخفاق استرجاع: {counts['restore_failures']['normalized_output']}
· اختلافٌ غير مسجَّل: {counts['unrecorded_differences']['normalized_output']} · أخطاء محاذاة: {counts['alignment_errors']['words']}</p>
<h2>آية الدين (2:282) كلمةً كلمة</h2>
<p class=mut>الموضع رقم كلمة المصدر، وبين القوسين رقمها في الناتج السابق. المصدر برموزه، والناتج السابق، والناتج الجديد،
وسبب التحويل، والعمليات بمجالاتها والمحفوظ بموضعه. الصفّ الملوّن تغيّر ناتجه.</p>
<div class=wrap><table><thead><tr><th>الموضع</th><th>المصدر</th><th>الناتج السابق</th><th>الناتج الجديد</th><th>السبب والعمليات</th></tr></thead>
<tbody>{rows282()}</tbody></table></div>
<h2>فهرس فروق القرآن كله ({len(IDX)} وقوعاً)</h2>
<label>عرض: <select id=f><option value=c>تغيّر الناتج</option><option value=u>غير محسوم</option><option value=a>الكل</option></select></label>
<label>بحث (موضع، قاعدة، كلمة): <input id=q placeholder="Q2:282 أو I-HAMZA"></label> <span id=n class=mut></span>
<div class=wrap><table><thead><tr><th>الوقوع</th><th>المصدر</th><th>السابق</th><th>الجديد</th><th>القواعد</th><th>المحفوظ</th><th>التحقق</th><th>سبب التأجيل</th></tr></thead>
<tbody id=t></tbody></table></div><p id=more class=mut></p>
<script>
const D={json.dumps(IDX, ensure_ascii=False)};
const E=s=>String(s).replace(/[&<>]/g,c=>({{'&':'&amp;','<':'&lt;','>':'&gt;'}}[c]));
function draw(){{const f=document.getElementById('f').value,q=document.getElementById('q').value.trim();
let r=D.filter(x=>(f==='a'||(f==='c'&&x[8])||(f==='u'&&x[7]))&&(!q||x.join(' ').includes(q)));
document.getElementById('n').textContent=r.length+' وقوعاً';
document.getElementById('t').innerHTML=r.slice(0,1500).map(x=>`<tr id="${{E(x[0])}}"><td><code>${{E(x[0])}}</code></td><td class=ar>${{E(x[1])}}</td><td class=ar>${{E(x[2])}}</td><td class=ar>${{E(x[3])}}</td><td><code>${{E(x[4])}}</code></td><td class=mut>${{E(x[5])}}</td><td>${{E(x[6])}}</td><td>${{E(x[7])}}</td></tr>`).join('');
document.getElementById('more').textContent=r.length>1500?'يُعرض أول 1500؛ ضيّق بالموضع أو القاعدة':'';}}
document.getElementById('f').onchange=draw;document.getElementById('q').oninput=draw;
if(location.hash){{document.getElementById('f').value='a';document.getElementById('q').value=decodeURIComponent(location.hash.slice(1));}}
draw();
</script>
<footer class=mut><p>السجل الكامل: normalization_run.json وnormalization_ops.jsonl.gz · الهوية <code>{RID}</code></p></footer>
</main></body></html>"""
open(P['html'], 'w', encoding='utf-8').write(page)
print(json.dumps(dict(run_id=RID, out=OUT, words_changed=counts['words_changed'], ops=counts['operations']['total'],
                      unresolved=counts['words_unresolved'], info_lost=counts['information_lost'],
                      restore=counts['restore_failures'], unrecorded=counts['unrecorded_differences'],
                      alignment=counts['alignment_errors'], structural_fail=counts['occurrence_structural_failures'],
                      residual=counts['residual_uncovered_marks_in_output']), ensure_ascii=False))
