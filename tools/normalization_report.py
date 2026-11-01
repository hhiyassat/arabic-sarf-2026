# -*- coding: utf-8 -*-
"""مخرجات مهمة إصلاح التطبيع (PROMPT_COMPREHENSIVE_NORMALIZATION_REPAIR_01) من تشغيلٍ واحد بهويةٍ واحدة:

    python3 tools/normalization_report.py --legacy <legacy_outputs.json> [--downstream <مجلد compare>] [--out reports/normalization]

  legacy_outputs.json: ناتج uthmani_normalize في خط الأساس لكل آية (يُولَّد في شجرة خط الأساس؛ انظر technical.md)
  المخرجات:
    report_ar.md      تقرير صاحب المشروع
    technical.md      التقرير التقني: العقد والقواعد ومراجعها والملفات والاختبارات وحدود التغطية
    run.json          السجل الآلي: هوية التشغيل والبصمات والأعداد والمقارنة وسجل الفروق كاملاً بالوقوع
    ops.jsonl.gz      كل عمليات التحويل في القرآن كله (التحليلي والعرض)، سطرٌ لكل عملية
    index.html        آية الدين كلمةً كلمة، ثم فهرس الفروق في القرآن كله بالوقوع والقاعدة
"""
import argparse, collections, datetime, glob, gzip, hashlib, html, json, os, subprocess, sys, unicodedata

H = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, H)
from sarf.normalize_trace import normalize_traced, restore_source, RULES, NORM_CONTRACT, cp

ap = argparse.ArgumentParser()
ap.add_argument('--legacy', required=True)
ap.add_argument('--downstream')
ap.add_argument('--downstream-commit', help='الالتزام الذي قيس عليه الأثر اللاحق')
ap.add_argument('--downstream-analysis-sha', help='بصمة التمثيل التحليلي للقرآن كله عند ذلك الالتزام')
ap.add_argument('--out', default=os.path.join(H, 'reports', 'normalization'))
args = ap.parse_args()
os.makedirs(args.out, exist_ok=True)


def sh(*a):
    return subprocess.run(['git', '-C', H, *a], capture_output=True, text=True).stdout.strip()


def sha_file(p):
    return hashlib.sha256(open(p, 'rb').read()).hexdigest()


ROWS = [l.rstrip('\n').split('\t')[:3] for l in open(os.path.join(H, 'data/quran_hafs.tsv'), encoding='utf-8')]
LEG = json.load(open(args.legacy, encoding='utf-8'))
code_files = ['sarf/normalize.py', 'sarf/normalize_trace.py', 'sarf/chars.py', 'tools/normalization_report.py',
              'tests/test_normalize_trace.py', 'tests/test_normalize.py']
ident = dict(
    contract=NORM_CONTRACT, branch=sh('rev-parse', '--abbrev-ref', 'HEAD'), commit=sh('rev-parse', 'HEAD'),
    dirty=[l for l in sh('status', '--porcelain', '--untracked-files=no').splitlines() if not l[3:].startswith('reports/')],
    code_sha256={f: sha_file(os.path.join(H, f)) for f in code_files},
    quran=dict(path='data/quran_hafs.tsv', encoding='UTF-8 (TSV: سورة، آية، نص)', sha256=sha_file(os.path.join(H, 'data/quran_hafs.tsv')),
               verses=len(ROWS)),
    legacy=dict(path=os.path.basename(args.legacy), sha256=sha_file(args.legacy), verses=len(LEG)),
    indexing='مواضع Unicode code points في نص الآية من الصفر، والمجال نصف مفتوح [من، إلى)؛ والكلمة في المصدر ما بين مسافتين، من الواحد',
    python=sys.version.split()[0], unicode=unicodedata.unidata_version,
    generated=datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds'),
)
ident['run_id'] = hashlib.sha256(json.dumps([ident['commit'], ident['code_sha256'], ident['quran']['sha256'],
                                             ident['legacy']['sha256'], ident['dirty']], sort_keys=True).encode()).hexdigest()[:12]

# ---------- القرآن كله ----------
C = collections.Counter()
rule_a, rule_d = collections.Counter(), collections.Counter()
occ = []                       # سجل الفروق بالوقوع
unresolved = []
cp_cover = collections.defaultdict(lambda: collections.Counter())
opsz = gzip.open(os.path.join(args.out, 'ops.jsonl.gz'), 'wt', encoding='utf-8')
D282 = None
for s, v, t in ROWS:
    loc = f'{s}:{v}'
    r = normalize_traced(t, loc)
    if loc == '2:282':
        D282 = r
    C['verses'] += 1
    for which in ('analysis', 'display'):
        rs, miss = restore_source(r, which)
        C[f'restore_fail_{which}'] += (rs != t or bool(miss))
        C[f'info_lost_{which}'] += len(miss)
        for o in r['ops_' + which]:
            (rule_a if which == 'analysis' else rule_d)[o['rule']] += 1
            opsz.write(json.dumps(dict(o, mode=which, verse=loc), ensure_ascii=False) + '\n')
        in_op = {i for o in r['ops_' + which] for a, b in o['src_spans'] for i in range(a, b)}
        same = {c['src'][0] for c in r['cells_' + which] if len(c['src']) == 1 and not c['derived'] and t[c['src'][0]] == c['c']}
        C[f'unrecorded_{which}'] += sum(1 for i in range(len(t)) if i not in in_op and i not in same)
    for i, ch in enumerate(t):
        handled = sorted({o['rule'] for o in r['ops_analysis'] for a, b in o['src_spans'] if a <= i < b})
        cp_cover[f'U+{ord(ch):04X}'][','.join(handled) or 'كما هو'] += 1
    # الكلمات: كل كلمةٍ ناتجة ← كلمات المصدر بخريطة المحارف
    src_words = t.split(' ')
    wof = []
    k = 0
    for ch in t:
        wof.append(None if ch == ' ' else k)
        k += ch == ' '

    def out_words(which):
        res, cur, curw = [], '', set()
        for c in r['cells_' + which] + [dict(c=' ', src=[])]:
            if c['c'] == ' ':
                if cur:
                    res.append((cur, sorted(curw)))
                cur, curw = '', set()
            else:
                cur += c['c']
                curw |= {wof[i] for i in c['src'] if wof[i] is not None}
        return res
    A, Dd = out_words('analysis'), out_words('display')
    L = LEG[loc].split(' ')
    if not (len(A) == len(Dd) == len(L)):
        C['alignment_error_verses'] += 1
        continue
    for j, ((aw, sws), (dw, sws2), lw) in enumerate(zip(A, Dd, L)):
        C['words'] += 1
        if sws != sws2 or not sws:
            C['alignment_error_words'] += 1
            continue
        a0, b0 = sws[0], sws[-1]
        ra = sorted({o['rule'] for o in r['ops_analysis'] if set(o['words']) & {w + 1 for w in sws}})
        rd = sorted({o['rule'] for o in r['ops_display'] if set(o['words']) & {w + 1 for w in sws}})
        srcw = ' '.join(src_words[a0:b0 + 1])
        pres = sorted({p['category'] for o in r['ops_analysis'] if set(o['words']) & {w + 1 for w in sws} for p in o['preserved']})
        un = [o['note'] for o in r['ops_display'] + r['ops_analysis'] if o['status'] == 'غير محسوم'
              and set(o['words']) & {w + 1 for w in sws}]
        ch_a, ch_d = aw != lw, dw != lw
        C['words_analysis_changed'] += ch_a
        C['words_display_differs_from_legacy'] += ch_d
        if un:
            C['words_unresolved'] += 1
        if ch_a or ch_d or un:
            fix = [x for x in ra if x in ('N-IQLAB-TANWIN', 'N-SMALL-NOON', 'N-SMALL-CARRIER')]
            if ch_a:
                verdict = ('معلومةٌ مستعادة بقاعدة ' + '، '.join(fix) + ': علامتها مكتوبة في المصدر (تحقّقٌ آلي بالقاعدة)'
                           if fix else 'تغيّرٌ بلا قاعدة إصلاح: يُراجَع')
                if not fix:
                    C['analysis_change_without_fix_rule'] += 1
            else:
                verdict = 'التحليلي كما كان؛ والعرض بقواعد الإملاء المعلنة (تحقّقٌ آلي بالقاعدة، لا مراجعة بشرية لكل وقوع)'
            if un:
                verdict = 'غير محسوم: ' + '؛ '.join(sorted(set(un)))
            occ.append(dict(id=f'Q{s}:{v}:{a0 + 1}' + (f'-{b0 + 1}' if b0 > a0 else ''), loc=loc, src_words=[w + 1 for w in sws],
                            source=srcw, source_cp=cp(srcw), legacy=lw, analysis=aw, display=dw,
                            analysis_changed=ch_a, display_differs=ch_d, rules_analysis=ra, rules_display=rd,
                            preserved=pres, verdict=verdict))
            if un:
                unresolved.append(occ[-1])
opsz.close()

# بصمة التمثيل التحليلي للقرآن كله: تربط قياس الأثر اللاحق بالنسخة (إن تساوت البصمتان فالأثر نفسه)
_m = hashlib.sha256()
for s_, v_, t_ in ROWS:
    _m.update(f'{s_}:{v_}\t{normalize_traced(t_)["analysis"]}\n'.encode())
ident['analysis_sha256'] = _m.hexdigest()
ident['downstream_measured_at'] = dict(commit=args.downstream_commit, analysis_sha256=args.downstream_analysis_sha,
                                       same_analysis=args.downstream_analysis_sha == ident['analysis_sha256'])

# ---------- الأثر في المراحل اللاحقة ----------
down = None
if args.downstream and os.path.exists(os.path.join(args.downstream, 'summary.json')):
    down = json.load(open(os.path.join(args.downstream, 'summary.json'), encoding='utf-8'))
    down_md = open(os.path.join(args.downstream, 'summary.md'), encoding='utf-8').read()
else:
    down_md = 'غير مقاس في هذا التشغيل.'
down_items = []
if args.downstream and os.path.exists(os.path.join(args.downstream, 'items.csv')):
    import csv
    for r_ in csv.DictReader(open(os.path.join(args.downstream, 'items.csv'), encoding='utf-8')):
        if r_['layer'] == 'سمة مقابَلة' and r_['category'] in ('مكتسَبٌ خاطئ', 'صحيحٌ صار خاطئاً', 'صحيحٌ أُجِّل', 'صحيحٌ فُقد',
                                                               'خاطئٌ تغيّرت قيمته', 'بلا مرجع: تغيّر'):
            down_items.append(r_)
        elif r_['layer'] == 'عامل' and r_['category'] != 'تغيّر الدليل أو المعمول':
            down_items.append(r_)
        elif r_['layer'] == 'علاقة':
            down_items.append(r_)

counts = dict(
    verses=C['verses'], words=C['words'],
    words_analysis_changed=C['words_analysis_changed'],
    words_display_differs_from_legacy=C['words_display_differs_from_legacy'],
    words_unresolved=C['words_unresolved'],
    analysis_change_without_fix_rule=C['analysis_change_without_fix_rule'],
    info_lost=dict(analysis=C['info_lost_analysis'], display=C['info_lost_display']),
    restore_failures=dict(analysis=C['restore_fail_analysis'], display=C['restore_fail_display']),
    unrecorded_differences=dict(analysis=C['unrecorded_analysis'], display=C['unrecorded_display']),
    alignment_errors=dict(verses=C['alignment_error_verses'], words=C['alignment_error_words']),
    ops_by_rule=dict(analysis=dict(sorted(rule_a.items())), display=dict(sorted(rule_d.items()))),
)
by_rule_words = collections.Counter(x for o in occ if o['analysis_changed'] for x in o['rules_analysis']
                                    if x in ('N-IQLAB-TANWIN', 'N-SMALL-NOON', 'N-SMALL-CARRIER'))
counts['words_analysis_changed_by_fix_rule'] = dict(by_rule_words)
coverage = {k: dict(v) for k, v in sorted(cp_cover.items())}
run = dict(identity=ident, rules={k: dict(version=v[0], ref=v[1], doc=v[2]) for k, v in RULES.items()}, counts=counts,
           codepoint_coverage=coverage, downstream=down, downstream_items=down_items, differences=occ, unresolved=[o['id'] for o in unresolved],
           ops_log=dict(path='ops.jsonl.gz', sha256=sha_file(os.path.join(args.out, 'ops.jsonl.gz'))))
json.dump(run, open(os.path.join(args.out, 'run.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
RID = ident['run_id']


# ---------- التقرير العربي ----------
def ex_rows(pred, n=8):
    return [o for o in occ if pred(o)][:n]


def md_table(rows):
    out = ['| الموضع | المصدر | السابق | التحليلي الجديد | العرض الإملائي | القاعدة |', '|---|---|---|---|---|---|']
    for o in rows:
        out.append(f"| {o['id']} | {o['source']} | {o['legacy']} | {o['analysis']} | {o['display']} | "
                   f"{', '.join(o['rules_analysis'] if o['analysis_changed'] else o['rules_display'])} |")
    return '\n'.join(out)


ar = f"""# إصلاح التطبيع: تقرير صاحب المشروع

هوية التشغيل `{RID}` · العقد {NORM_CONTRACT} · الفرع `{ident['branch']}` · الالتزام `{ident['commit'][:10]}` · \
تعديلات غير ملتزم بها في الشيفرة: {len(ident['dirty'])} · نص المصحف sha256 `{ident['quran']['sha256'][:16]}`

لم يُدمج شيءٌ إلى main، ولم يُدفع شيء. الاعتماد لكم بعد مراجعة القياس.

## ما الذي تغيّر في الفكرة

صار للتطبيع ثلاث طبقات منفصلة، كلٌّ منها مربوطةٌ بالمصدر محرفاً محرفاً:
- **المصدر** كما ورد، لا يُكتب فوقه، ويُستعاد حرفياً من السجل (تحقّق على {counts['verses']} آية: إخفاق الاسترجاع \
{counts['restore_failures']['analysis']} في التحليلي و{counts['restore_failures']['display']} في العرض).
- **التمثيل التحليلي**: ما تقرؤه مراحل التحليل. ليس إملاءً معيارياً، بل رسمٌ عثماني مخفَّف بقواعد معلنة، وتبقى فيه \
الخنجرية والشدّة على أول الكلمة كما كانتا. وقد صُحّح فيه ما كان يُفقد معلومةً مكتوبة فقط.
- **العرض الإملائي**: إملاءٌ معياري بقواعد معلنة، ولا يضيف سكوناً لم يُكتب.
- وكل ما لا يظهر في العرض (علامات الوقف، ميم الإقلاب، الصلة، الصفر، علامة المدّ، شدّة الإدغام، علامة الاتجاه) محفوظٌ \
في السجل بموضعه وصنفه.

## ما أُصلح

**١. التنوين المرسوم بالميم الصغيرة** (القاعدة N-IQLAB-TANWIN): الحركة القصيرة وبعدها ميمٌ صغيرة إقلابُ تنوين، \
فتُكتب تنويناً، وتُحفظ الميم. والتنوين حركةٌ واحدة، ولا يُنشأ منه حرف نون. أما الميم على نونٍ عارية (مِنۢ) فإقلاب نونٍ \
ساكنة: النون تبقى (N-IQLAB-NOON). كلمات تغيّر تمثيلها التحليلي بهذه القاعدة: {by_rule_words.get('N-IQLAB-TANWIN', 0)}.

{md_table(ex_rows(lambda o: 'N-IQLAB-TANWIN' in o['rules_analysis'] and o['analysis_changed'] and o['loc'] == '2:282', 4) + ex_rows(lambda o: 'N-IQLAB-TANWIN' in o['rules_analysis'] and o['analysis_changed'] and o['loc'] != '2:282', 4))}

**٢. حرفٌ مرسومٌ صغيراً كان يُحذف**: النون الصغيرة (نُـۨجِي ← نُنْجِي، N-SMALL-NOON)، والحركة على المطّة الحاملة \
للحرف الصغير صارت للحرف لا لما قبله (لِنُحۡـِۧيَ، N-SMALL-CARRIER). كلمات: {by_rule_words.get('N-SMALL-NOON', 0)} و\
{by_rule_words.get('N-SMALL-CARRIER', 0)}.

{md_table(ex_rows(lambda o: o['analysis_changed'] and ('N-SMALL-NOON' in o['rules_analysis'] or 'N-SMALL-CARRIER' in o['rules_analysis']), 4))}

**٣. سياسة الرسم في العرض الإملائي** (والتمثيل التحليلي باقٍ كما كان فيها):
- الخنجرية بعد فتحة ألفاً، والواو والألف المقصورة الحاملتان للخنجرية ألفاً، إلا المقصورة في آخر الكلمة؛
- إلا ما تحذف الإملاء ألفه (هذا، ذلك، أولئك، لكن، إله، الرحمن، هؤلاء)؛
- والهمزة على كرسيّها بقواعد الهمزة؛
- والهمزة المفتوحة قبل ألف مدٍّ آ.

{md_table([o for o in occ if o['loc'] == '2:282' and o['display_differs'] and set(o['rules_display']) & {'I-DAGGER-ALIF', 'I-WAW-ALIF', 'I-HAMZA', 'I-ALIF-OMIT', 'I-HAMZA-MADD'}][:10])}

**٤. السكون**: ثلاث حالات مميَّزة في كل محرف:
- **سكونٌ مكتوب** (ۡ): منسوبٌ إلى محرفه.
- **غياب الحركة**: يبقى غياباً في العرض.
- **سكونٌ مضاف** في التمثيل التحليلي بقاعدة الضبط (الحرف العاري مُخفى أو مدغم، N-IMPLICIT-SUKUN): محرفٌ مشتقّ بلا مصدر، \
حالته «مشتقّ». عدد ما أُضيف: {rule_a.get('N-IMPLICIT-SUKUN', 0)}.

{md_table([o for o in occ if o['loc'] == '2:282' and o['source'] in ('تَدَايَنتُم', 'أَن', 'مِن', 'مِمَّن')][:6])}

**٥. جمع الأجزاء** (N-JOIN-LONE-ALIF): ألفٌ مفردة بعد كلمةٍ في آخرها تنوينٌ مفتوح تُجمع إليها، وهو عيبٌ في النسخة الرقمية: \
«مُّسَمࣰّ ى» و«شَيۡـࣰٔ اۚ» في آية الدين. لا يُجمع غير ذلك. عدد مرات الجمع: {rule_a.get('N-JOIN-LONE-ALIF', 0)}.

## ما بقي غير محسوم ({counts['words_unresolved']} كلمة)

- **النداء الموصول رسماً** (يَٰٓأَيُّهَا، يَٰقَوۡمِ…) و«ها» التنبيه الموصولة (هَٰٓأَنتُمۡ): الإملاء يفصلهما، ولم أفصلهما \
بلا حكمٍ منكم. وهو سؤالكم السابق عن «يَٰٓأَيُّهَا».
- **الواو والياء الصغيرتان في غير الصلة** (يَلۡوُۥنَ، إِۦلَٰفِهِمۡ، دَاوُۥدَ): 50 موضعاً. في العرض الإملائي صارتا حرفاً، \
إلا «داود». وفي التمثيل التحليلي بقي حذفهما كما كان، لأن إثباتهما يغيّر الصرف و«داود» من الأسماء الذهبية. القرار لكم.

## الأثر في المراحل اللاحقة

قيس على الالتزام `{(args.downstream_commit or '—')[:10]}`، وبصمة تمثيله التحليلي للقرآن كله \
`{(args.downstream_analysis_sha or '—')[:16]}`، وهي {'تساوي' if ident['downstream_measured_at']['same_analysis'] else '<b>لا تساوي</b>'} بصمة هذا التشغيل. \
فالتعديل اللاحق (واو «أولئك» في العرض وحده) لم يغيّر ما تقرؤه المراحل اللاحقة.

الأثر مسجَّلٌ بالموضع، ولا يُعدّ دليلاً مستقلاً على صحة التطبيع، ولم تُعدَّل قاعدةٌ في الجذر أو الصرف أو العوامل أو العطف أو الحدود.

**السمات المقابَلة بمدوّنة QAC** (للقياس وحده):
- مكتسَبٌ صحيح: {(down or {}).get('scored', {}).get('مكتسَبٌ صحيح', 0)}، معظمه التعريف والتنكير والصنف بالتنوين المستعاد؛
- مكتسَبٌ خاطئ: {(down or {}).get('scored', {}).get('مكتسَبٌ خاطئ', 0)}؛
- صحيحٌ صار خاطئاً: {(down or {}).get('scored', {}).get('صحيحٌ صار خاطئاً', 0)}؛
- صحيحٌ فُقد أو أُجِّل: {(down or {}).get('scored', {}).get('صحيحٌ فُقد', 0) + (down or {}).get('scored', {}).get('صحيحٌ أُجِّل', 0)}؛
- ما لا مرجع له فتغيّر: {(down or {}).get('scored', {}).get('بلا مرجع: تغيّر', 0)}.

**ما يحتاج قراركم أو مراجعتكم** (من سجل الأثر، بالموضع):
- **96:15 «لَنَسۡفَعَۢا»**: نون التوكيد الخفيفة مرسومةٌ رسمَ تنوين الإقلاب نفسه، فالتطبيع يكتبها تنويناً كما كُتبت، \
والصرف اللاحق يقرأ التنوين اسماً. هذا هو المكتسَب الخاطئ الوحيد. ومثله قائمٌ قبل الإصلاح في «وَلَيَكُونࣰا» (يوسف ٣٢) بالتنوين المتتابع. \
والقاعدة في الصرف لا في التطبيع.
- **«يَوۡمَئِذٍ» وتنوين العوض، و«سَبَإٍ» العَلَم**: صار تعريفها «نكرة» مثبتاً بالتنوين المستعاد، ولا مرجع لها في المدوّنة. \
التنوين فيها لا يدلّ على التنكير، فالحكم مشكوكٌ فيه، والقاعدة في الصرف.
- **7:196 «إِنَّ وَلِـِّۧيَ»**: صحّحت قاعدة حامل الحرف الصغير موضع الكسرة، فصار «إِنَّ» مؤجَّلاً بعد أن كان مقبولاً. \
وكان قبوله قائماً على قراءةٍ مشوَّهة «وَلِّييَ». وظهر مرشّح «وَ» سابقةً مؤجَّلاً، والواو فاء الكلمة لا سابقة.
- **العوامل التي قُبلت بالعلامة المستعادة**: «كَانَ … بَصِيرَۢا»، و«مِن مَّكَانِۭ» التي كانت تُقرأ «رفع». \
وزال «يا» من «لَيَّۢا» و«لا» من «كُلَّۢا». التفاصيل في run.json (`downstream_items`).

## أساس التحقّق وحدوده

**ما تحقّق آلياً على القرآن كله:**
- الاسترجاع الحرفي؛
- اكتمال تسجيل كل اختلاف: غير مسجَّل في التحليلي {counts['unrecorded_differences']['analysis']}، وفي العرض \
{counts['unrecorded_differences']['display']}؛
- النسبة إلى الكلمة الصحيحة: أخطاء المحاذاة {counts['alignment_errors']['words']}؛
- NFC والحتمية؛
- أن التمثيل التحليلي لم يتغيّر إلا بقواعد الإصلاح: تغيّرٌ بلا قاعدة إصلاح = {counts['analysis_change_without_fix_rule']}.

**ما لم يُراجَع بشرياً:** لم يُراجَع كل وقوعٍ في العرض الإملائي لغوياً. المراجَع كلمةً كلمة هو آية الدين وعيّناتٌ من كل قاعدة؛ \
والباقي تحقُّقٌ بالقاعدة لا بالقراءة. فلا أقول «كل التغييرات صحيحة».
"""
open(os.path.join(args.out, 'report_ar.md'), 'w', encoding='utf-8').write(ar)

# ---------- التقرير التقني ----------
rules_md = '\n'.join(f'| {k} | {v[0]} | {v[1]} | {rule_a.get(k, 0)} | {rule_d.get(k, 0)} | {v[2]} |' for k, v in RULES.items())
cov_md = '\n'.join(f"| {k} | {unicodedata.name(chr(int(k[2:], 16)), '?')} | " + '; '.join(f'{r}: {n}' for r, n in sorted(v.items(), key=lambda x: -x[1])[:4]) + ' |'
                   for k, v in coverage.items())
tech = f"""# التطبيع N1.0: التقرير التقني

هوية التشغيل `{RID}` · الالتزام `{ident['commit']}` · الفرع `{ident['branch']}` · Python {ident['python']} · Unicode {ident['unicode']}

## العقد
- المصدر: `data/quran_hafs.tsv` (UTF-8، sha256 `{ident['quran']['sha256']}`، {ident['quran']['verses']} آية).
- الفهرسة: {ident['indexing']}.
- الواجهة:
  - `sarf.normalize_trace.normalize_traced(text, loc, implicit_sukun=None, strict=False)` ← \
`source`، `analysis`، `display`، `cells_analysis`، `cells_display`، `ops_analysis`، `ops_display`؛
  - `restore_source(res, which)` يستعيد المصدر حرفياً؛
  - و`is_source_encoding(text)`، و`strict=True` يرفض نصاً مطبَّعاً مدخلاً.
- `sarf.normalize.uthmani_normalize` يعيد `analysis`، والسلوك السابق في `_uthmani_normalize_legacy`.
- المحرف الناتج: `c`، و`src` (مواضع المصدر؛ فارغةٌ للمضاف)، و`derived`.
- العملية: `id`، `rule`، `rule_version`، `rule_ref`، `type` (استبدال، إضافة، حذف من العرض، نقل علامة، تركيب، جمع أجزاء، غير محسوم)، \
`words`، `src_spans`، `src_text`/`src_cp`، `before`/`before_cp`، `after`/`after_cp`، `out_spans`، `preserved` (المحرف ورمزه وموضعه وصنفه)، `status`، `note`.
- العلاقات: واحدٌ إلى واحد، وواحدٌ إلى متعدد (المحرف الثاني من المصدر نفسه مشتقّ)، ومتعددٌ إلى واحد (التركيب)، والمجالات المتعددة (`src_spans` قائمة).

## القواعد

| القاعدة | الإصدار | المرجع | عمليات (تحليلي) | عمليات (عرض) | النص |
|---|---|---|---|---|---|
{rules_md}

المراجع:
- K: اصطلاحات الضبط في مصحف المدينة (رواية حفص).
- U: معيار Unicode.
- O: حكم صاحب النظرية المسجَّل في الشيفرة (D21، D22).
- I: قواعد الإملاء (عبد السلام هارون؛ ومجمع اللغة العربية في الهمزة).

## الأعداد
- الآيات: {counts['verses']}، والكلمات المقابَلة: {counts['words']}.
- الكلمات التي تغيّر تمثيلها التحليلي: {counts['words_analysis_changed']}، وبحسب القاعدة: {json.dumps(counts['words_analysis_changed_by_fix_rule'], ensure_ascii=False)}.
- التغيّر بلا قاعدة إصلاح: {counts['analysis_change_without_fix_rule']}.
- الكلمات التي يخالف عرضها الإملائي الناتجَ السابق: {counts['words_display_differs_from_legacy']}.
- فقد المعلومات (محرف مصدرٍ لا في الناتج ولا في السجل): تحليلي {counts['info_lost']['analysis']}، وعرض {counts['info_lost']['display']}.
- إخفاق الاسترجاع: {json.dumps(counts['restore_failures'], ensure_ascii=False)}.
- اختلافٌ غير مسجَّل: {json.dumps(counts['unrecorded_differences'], ensure_ascii=False)}.
- أخطاء المحاذاة: {json.dumps(counts['alignment_errors'], ensure_ascii=False)}.
- غير المحسوم: {counts['words_unresolved']} كلمة.

## تغطية المحارف (كل رمزٍ في المصدر وما عالجه في التحليلي)

| الرمز | الاسم | القواعد (أكثرها) |
|---|---|---|
{cov_md}

## الملفات المعدَّلة
- `sarf/normalize_trace.py` (جديد): العقد والقواعد والسجل.
- `sarf/normalize.py`: `uthmani_normalize` يأخذ من العقد، والقديم `_uthmani_normalize_legacy`.
- `tests/test_normalize_trace.py` (جديد)، و`tests/test_normalize.py` (توقّعٌ واحد كان يرسّخ فقد التنوين: يَوۡمَئِذِۭ).
- `tools/normalization_report.py` (جديد): هذه المخرجات.

## منطق تطبيعٍ مكرَّر خارج الوحدة (محصورٌ، لم يُعدَّل في هذه المهمة)
- `tools/pipeline_trace.py`: محاذاة المرحلة الأولى تعيد NFC وتحوّل الهمزة على المطّة وتحذف علامة الاتجاه وتطابق آ بـ ا. \
ويمكن أن تستبدل بها خريطة المحارف (`cells_analysis`) في مهمةٍ لاحقة.
- `sarf/mood.py` و`sarf/lexicon.py` و`mabniyat_lexicon.py`: NFC للمقارنة، لا تحويلٌ للنص.
- `sarf/algebra.py merge_split_shadda`: عكسُ عملية المقشِّر (فكّ الشدّة على الحدّ)، وليس تطبيعاً للمصدر.

## الاختبارات
- `python3 tests/test_normalize_trace.py`: الحالات المسمّاة والمقابلة، وعلى القرآن كله الاسترجاع والاكتمال والنسبة وNFC \
والحتمية ورفض النص المطبَّع، ومطابقة التحليلي للسلوك السابق إلا بقواعد الإصلاح.
- `python3 tests/test_normalize.py`، وبقية `tests/test_*.py`، و`tests/regress.py`.
- حدود `tests/regress.py`: عيّنة آياتٍ محفوظة في `tests/golden/`، لا القرآن كله؛ فقوله «لا فرق» ليس دليلاً على القرآن كله.

## الأثر في المراحل اللاحقة (tools/compare_runs.py: خط الأساس df9c92b مقابل هذا الالتزام)

{down_md}

## إعادة الإنتاج
```
git checkout {ident['commit'][:10]}            # الفرع {ident['branch']} (محلي، غير مدفوع)
export SARF_HFN=<release_v18 أو v19> PYTHONHASHSEED=0
python3 tests/test_normalize_trace.py
# خط الأساس: شجرة على df9c92b، ومنها legacy_outputs.json (uthmani_normalize لكل آية)
git worktree add ../norm_base df9c92b && ln -s "$(readlink -f data)" ../norm_base/data
(cd ../norm_base && python3 -c "import json,sys; sys.path.insert(0,'.'); from sarf.normalize import uthmani_normalize as u; \\
 print(json.dumps({{f'{{l.split(chr(9))[0]}}:{{l.split(chr(9))[1]}}': u(l.rstrip(chr(10)).split(chr(9))[2]) for l in open('data/quran_hafs.tsv', encoding='utf-8')}}, ensure_ascii=False))" > /tmp/legacy_outputs.json)
# الأثر اللاحق
(cd ../norm_base && bash tools/run_full.sh) && bash tools/run_full.sh && python3 tools/compare_runs.py --base ../norm_base
python3 tools/normalization_report.py --legacy /tmp/legacy_outputs.json --downstream reports/compare
```
"""
open(os.path.join(args.out, 'technical.md'), 'w', encoding='utf-8').write(tech)

# ---------- HTML ----------
h = html.escape


def word_rows_282():
    r = D282
    t = r['source']
    rows = []
    for o in [o for o in occ if o['loc'] == '2:282']:
        pass
    src_words = t.split(' ')
    wof = []
    k = 0
    for ch in t:
        wof.append(None if ch == ' ' else k)
        k += ch == ' '
    for which in ('analysis',):
        pass
    groups = []
    cur, curw = [], set()
    for c in r['cells_analysis'] + [dict(c=' ', src=[])]:
        if c['c'] == ' ':
            if cur:
                groups.append((cur, sorted(curw)))
            cur, curw = [], set()
        else:
            cur.append(c)
            curw |= {wof[i] for i in c['src'] if wof[i] is not None}
    dgroups = []
    cur = []
    for c in r['cells_display'] + [dict(c=' ', src=[])]:
        if c['c'] == ' ':
            if cur:
                dgroups.append(''.join(x['c'] for x in cur))
            cur = []
        else:
            cur.append(c)
    L = LEG['2:282'].split(' ')
    for n, ((cells, sws), dw, lw) in enumerate(zip(groups, dgroups, L)):
        ws = {w + 1 for w in sws}
        sw = ' '.join(src_words[sws[0]:sws[-1] + 1])
        aw = ''.join(c['c'] for c in cells)
        der = ''.join(f"<span class='der' title='مشتقّ بلا مصدر'>{h(c['c'])}</span>" if c['derived'] and not c['src']
                      else h(c['c']) for c in cells)
        opsa = [o for o in r['ops_analysis'] if set(o['words']) & ws]
        opsd = [o for o in r['ops_display'] if set(o['words']) & ws]
        det = ''.join(f"<li><code>{h(o['rule'])}</code> {h(o['type'])}: «{h(o['before'])}» ({h(o['before_cp'])}) ← «{h(o['after'])}» "
                      f"[{h(str(o['src_spans']))}]" + (f" · محفوظ: {h(', '.join(p['category'] + ' ' + p['cp'] for p in o['preserved']))}" if o['preserved'] else '')
                      + (f" · <b>{h(o['status'])}</b>" if o['status'] != 'مطبَّق' else '') + '</li>' for o in opsa)
        detd = ''.join(f"<li><code>{h(o['rule'])}</code> «{h(o['before'])}» ← «{h(o['after'])}»"
                       + (f" · <b>{h(o['status'])}</b>: {h(o['note'] or '')}" if o['status'] != 'مطبَّق' else '') + '</li>'
                       for o in opsd if o['rule'].startswith('I-'))
        cls = ' class="chg"' if aw != lw else ''
        rows.append(f"<tr id='w{sws[0] + 1}'{cls}><td>{', '.join(str(w) for w in sorted(ws))}</td><td class='ar'>{h(sw)}</td>"
                    f"<td><code class='cp'>{h(cp(sw))}</code></td><td class='ar'>{h(lw)}</td><td class='ar'>{der}</td>"
                    f"<td class='ar'>{h(dw)}</td><td><details><summary>{len(opsa)} تحليلي · {len([o for o in opsd if o['rule'].startswith('I-')])} عرض</summary>"
                    f"<ul>{det}</ul><ul>{detd}</ul></details></td></tr>")
    return '\n'.join(rows)


idx = [[o['id'], o['source'], o['legacy'], o['analysis'], o['display'],
        ' '.join(o['rules_analysis'] if o['analysis_changed'] else []), ' '.join(x for x in o['rules_display'] if x.startswith('I-')),
        1 if o['analysis_changed'] else 0, o['verdict']] for o in occ]
page = f"""<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>إصلاح التطبيع</title>
<style>
:root{{--bg:#fff;--fg:#1d1d1f;--mut:#666;--line:#ddd;--chg:#fff4d6;--der:#c0392b}}
@media (prefers-color-scheme:dark){{:root{{--bg:#16181c;--fg:#e8e8ea;--mut:#9a9aa0;--line:#333;--chg:#3a3320;--der:#ff7b6b}}}}
body{{background:var(--bg);color:var(--fg);font-family:system-ui,"Noto Naskh Arabic",sans-serif;margin:0;padding:16px;line-height:1.6}}
main{{max-width:1200px;margin:auto}} table{{border-collapse:collapse;width:100%;font-size:.9rem}} td,th{{border-bottom:1px solid var(--line);padding:4px 6px;vertical-align:top;text-align:right}}
.ar{{font-family:"Amiri Quran","Noto Naskh Arabic",serif;font-size:1.15rem}} .cp{{font-size:.65rem;color:var(--mut);word-break:break-all}}
tr.chg{{background:var(--chg)}} .der{{color:var(--der);font-weight:bold}} .mut{{color:var(--mut)}} code{{font-size:.8rem}}
.wrap{{overflow-x:auto}} input,select{{font-size:1rem;padding:4px;margin:4px}}
</style></head><body><main>
<h1>إصلاح التطبيع</h1>
<p class="mut">هوية التشغيل <code>{RID}</code> · العقد {NORM_CONTRACT} · الفرع <code>{h(ident['branch'])}</code> · الالتزام <code>{ident['commit'][:10]}</code>
· نص المصحف <code>{ident['quran']['sha256'][:16]}</code> · خط الأساس <code>{h(ident['legacy']['path'])}</code> <code>{ident['legacy']['sha256'][:16]}</code></p>
<p>الأعداد: كلمات تغيّر تمثيلها التحليلي <b>{counts['words_analysis_changed']}</b> (بلا قاعدة إصلاح: {counts['analysis_change_without_fix_rule']}) ·
فقد معلومات {counts['info_lost']['analysis']}/{counts['info_lost']['display']} · إخفاق استرجاع {counts['restore_failures']['analysis']}/{counts['restore_failures']['display']} ·
اختلافٌ غير مسجَّل {counts['unrecorded_differences']['analysis']}/{counts['unrecorded_differences']['display']} · أخطاء محاذاة {counts['alignment_errors']['words']} ·
غير محسوم {counts['words_unresolved']}</p>
<h2>آية الدين (2:282) كلمةً كلمة</h2>
<p class="mut">المصدر ورموزه، والناتج السابق، والتمثيل التحليلي الجديد (الأحمر محرفٌ مشتقّ بلا مصدر)، والعرض الإملائي، والعمليات بقواعدها ومجالاتها.
الصفّ الملوَّن تغيّر تمثيله التحليلي.</p>
<div class="wrap"><table><thead><tr><th>كلمة المصدر</th><th>المصدر</th><th>الرموز</th><th>السابق</th><th>التحليلي</th><th>العرض</th><th>العمليات</th></tr></thead>
<tbody>{word_rows_282()}</tbody></table></div>
<h2>فهرس الفروق في القرآن كله ({len(idx)} وقوعاً)</h2>
<p class="mut">كل كلمةٍ تغيّر تمثيلها التحليلي، أو خالف عرضها الإملائيُّ الناتجَ السابق، أو بقيت غير محسومة؛ بموضعها وقاعدتها وحكم المراجعة.</p>
<label>تصفية: <select id="f"><option value="a">تغيّر التحليلي</option><option value="u">غير محسوم</option><option value="all">الكل</option></select></label>
<label>بحث (موضع أو قاعدة أو كلمة): <input id="q" placeholder="2:282 أو I-HAMZA"></label> <span id="n" class="mut"></span>
<div class="wrap"><table><thead><tr><th>الوقوع</th><th>المصدر</th><th>السابق</th><th>التحليلي</th><th>العرض</th><th>قاعدة التحليلي</th><th>قواعد العرض</th><th>الحكم</th></tr></thead><tbody id="t"></tbody></table></div>
<p id="more" class="mut"></p>
<script>
const D={json.dumps(idx, ensure_ascii=False)};
const E=s=>String(s).replace(/[&<>]/g,c=>({{'&':'&amp;','<':'&lt;','>':'&gt;'}}[c]));
function draw(){{const f=document.getElementById('f').value,q=document.getElementById('q').value.trim();
let r=D.filter(x=>(f==='all'||(f==='a'&&x[7])||(f==='u'&&x[8].startsWith('غير محسوم')))&&(!q||x.join(' ').includes(q)));
document.getElementById('n').textContent=r.length+' وقوعاً';
document.getElementById('t').innerHTML=r.slice(0,1500).map(x=>`<tr id="${{E(x[0])}}"><td><code>${{E(x[0])}}</code></td><td class="ar">${{E(x[1])}}</td><td class="ar">${{E(x[2])}}</td><td class="ar">${{E(x[3])}}</td><td class="ar">${{E(x[4])}}</td><td><code>${{E(x[5])}}</code></td><td><code>${{E(x[6])}}</code></td><td>${{E(x[8])}}</td></tr>`).join('');
document.getElementById('more').textContent=r.length>1500?'يُعرض أول 1500؛ ضيّق البحث بموضعٍ أو قاعدة':'';}}
document.getElementById('f').onchange=draw;document.getElementById('q').oninput=draw;
if(location.hash){{document.getElementById('f').value='all';document.getElementById('q').value=decodeURIComponent(location.hash.slice(1));}}
draw();
</script>
<footer class="mut"><p>السجل الكامل: run.json (الفروق بالوقوع) وops.jsonl.gz (كل عملية). الهوية <code>{RID}</code>.</p></footer>
</main></body></html>"""
open(os.path.join(args.out, 'index.html'), 'w', encoding='utf-8').write(page)
print(json.dumps(dict(run_id=RID, **{k: counts[k] for k in ('words_analysis_changed', 'analysis_change_without_fix_rule',
                                                            'words_display_differs_from_legacy', 'words_unresolved',
                                                            'info_lost', 'restore_failures', 'unrecorded_differences',
                                                            'alignment_errors')}), ensure_ascii=False))
