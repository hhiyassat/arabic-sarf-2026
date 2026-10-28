# -*- coding: utf-8 -*-
"""
sarf.output_html — تقرير HTML: الكلمات ومقاطعها.
لكل آية: جدول صفٌّ لكل كلمة (الرقم، الكلمة، المقاطع ملوّنة حسب النوع، نمط CV، العوامل)،
مع ملخّص أنواع المقاطع للآية، وملخّص إجمالي في رأس الصفحة.
"""
import html
from collections import Counter, OrderedDict

from .syllabify import SIX
from .align import syllables_by_word
from .mood import op_mood, has_inshai_operator
from .output_text import relation_text, word_irab
from .root import WAZN
from .status import STATUS_AR, BLOCKED

# أنواع المقاطع التي نعدّها/نلوّنها: الستة + OTHER + POISON
TYPES = SIX + ['OTHER', 'POISON']

# أسماء عربية موجزة للعرض في المفتاح والملخّص
TYPE_LABEL = OrderedDict([
    ('CV',    'CV — ساكن+حركة'),
    ('CVV',   'CVV — ساكن+مدّ'),
    ('CVC',   'CVC — مغلق قصير'),
    ('CVVC',  'CVVC — مغلق بمدّ'),
    ('CVCC',  'CVCC — مغلق بساكنين'),
    ('CVVCC', 'CVVCC — مغلق بمدّ وساكنين'),
    ('OTHER', 'OTHER — نمط خارج الستة'),
    ('POISON','POISON — تشكيل ناقص'),
])


def syl_type(cv):
    """نوع المقطع لأغراض العدّ/التلوين: ستّة معروفة، أو POISON، أو OTHER."""
    if cv == 'POISON':
        return 'POISON'
    if cv in SIX:
        return cv
    return 'OTHER'


def esc(s):
    return html.escape('' if s is None else str(s))


CSS = """
:root{
  --bg:#ffffff; --fg:#1a1a1a; --muted:#666; --card:#f6f7f9; --border:#d9dde3;
  --th:#eceff3; --warnbg:#fff3cd; --warnfg:#7a5b00; --poisonbg:#f8d7da; --poisonfg:#842029;
  --c-CV:#1565c0;    --c-CVV:#00838f;   --c-CVC:#6a1b9a;
  --c-CVVC:#ef6c00;  --c-CVCC:#ad1457;  --c-CVVCC:#283593;
}
@media (prefers-color-scheme: dark){
  :root{
    --bg:#15181d; --fg:#e8eaed; --muted:#9aa0a6; --card:#1e232b; --border:#333a44;
    --th:#242b34; --warnbg:#4a3d00; --warnfg:#ffe08a; --poisonbg:#5a1f24; --poisonfg:#ffb3b8;
    --c-CV:#64b5f6;    --c-CVV:#4dd0e1;   --c-CVC:#ce93d8;
    --c-CVVC:#ffb74d;  --c-CVCC:#f48fb1;  --c-CVVCC:#9fa8da;
  }
}
*{box-sizing:border-box}
html,body{margin:0;padding:0}
body{
  background:var(--bg); color:var(--fg);
  font-family:"Noto Naskh Arabic","Geeza Pro","Scheherazade New","Segoe UI",system-ui,sans-serif;
  font-size:20px; line-height:1.9; padding:20px 16px 60px;
}
h1{font-size:28px;margin:0 0 6px}
h2{font-size:23px;margin:34px 0 8px;border-top:2px solid var(--border);padding-top:16px}
.muted{color:var(--muted);font-size:16px;line-height:1.7}
.card{background:var(--card);border:1px solid var(--border);border-radius:10px;padding:14px 16px;margin:12px 0}
.orig{font-size:24px;line-height:2.1}
table{border-collapse:collapse;width:100%;margin:10px 0;font-size:20px}
th,td{border:1px solid var(--border);padding:8px 10px;text-align:right;vertical-align:top}
th{background:var(--th);font-size:17px;font-weight:700;white-space:nowrap}
td.num{color:var(--muted);text-align:center;font-size:17px;width:3ch}
td.word{font-size:24px;white-space:nowrap}
td.cv{font-family:ui-monospace,Menlo,Consolas,monospace;font-size:16px;direction:ltr;text-align:left;color:var(--muted)}
.chip{display:inline-block;margin:2px 3px;padding:3px 10px;border-radius:8px;font-size:21px;
  border:1px solid currentColor;line-height:1.6}
.chip small{font-family:ui-monospace,Menlo,Consolas,monospace;font-size:12px;opacity:.75;direction:ltr;margin-right:5px}
.t-CV{color:var(--c-CV)}    .t-CVV{color:var(--c-CVV)}   .t-CVC{color:var(--c-CVC)}
.t-CVVC{color:var(--c-CVVC)}.t-CVCC{color:var(--c-CVCC)} .t-CVVCC{color:var(--c-CVVCC)}
.t-OTHER{color:var(--warnfg);background:var(--warnbg);border-color:var(--warnfg)}
.t-POISON{color:var(--poisonfg);background:var(--poisonbg);border-color:var(--poisonfg);font-weight:700}
.t-FIXED{color:var(--muted);border-style:dashed}
.t-FIXED small{direction:rtl;font-family:inherit}
.op{display:block;font-size:16px;line-height:1.7;margin:2px 0;padding-right:8px;border-right:3px solid var(--border)}
.op b{font-size:19px}
.op .meta{color:var(--muted)}
.summary{font-size:16px;margin:8px 0;display:flex;flex-wrap:wrap;gap:6px}
.pill{display:inline-block;padding:2px 9px;border-radius:999px;border:1px solid var(--border)}
.pill b{font-family:ui-monospace,Menlo,Consolas,monospace}
.key{display:flex;flex-wrap:wrap;gap:8px;margin:10px 0}
.total{font-size:18px}
.total .pill{font-size:17px;padding:4px 12px}
.mood{display:inline-block;font-size:14px;font-weight:700;padding:1px 9px;border-radius:999px;
  border:1px solid currentColor;vertical-align:middle}
h2 .mood{font-size:16px}
.mood-in{color:#8e24aa;background:rgba(142,36,170,.10)}   /* إنشائي */
.mood-kh{color:#2e7d32;background:rgba(46,125,50,.10)}    /* خبري  */
.mood-rej{color:#b71c1c;background:rgba(183,28,28,.10)}
.mood-def{color:#8d6e00;background:rgba(141,110,0,.10)}   /* مؤجَّل */
.st{display:inline-block;font-size:13px;padding:0 7px;border-radius:6px;border:1px solid currentColor}
.st-accepted{color:#1b5e20} .st-deferred{color:#8d6e00} .st-blocked{color:#b71c1c;font-weight:700}
@media (prefers-color-scheme: dark){
  .mood-in{color:#ce93d8;background:rgba(206,147,216,.15)}
  .mood-kh{color:#a5d6a7;background:rgba(165,214,167,.15)}
  .mood-rej{color:#ef9a9a;background:rgba(239,154,154,.15)}
  .mood-def{color:#ffe082;background:rgba(255,224,130,.15)}
}
"""


def chips_html(sylls):
    """شارات المقاطع ملوّنة حسب النوع."""
    out = []
    for s in sylls:
        t = syl_type(s['cv'])
        out.append(
            f'<span class="chip t-{esc(t)}" title="{esc(s["cv"])}">'
            f'{esc(s["syl"])}<small>{esc(s["cv"])}</small></span>'
        )
    return ''.join(out) if out else '<span class="muted">—</span>'


def ops_html(ops):
    if not ops:
        return '<span class="muted">—</span>'
    out = []
    for f in ops:
        st = f.get('status')
        stbadge = f'<span class="st st-{esc(st)}">{esc(STATUS_AR.get(st, ""))}</span>'
        if st == BLOCKED:
            badge = stbadge
        else:
            mood = op_mood(f)
            mcls = {'إنشائي': 'mood-in', 'خبري': 'mood-kh'}.get(mood, 'mood-def')
            badge = stbadge + f' <span class="mood {mcls}">{esc(mood)}</span>'
        bits = [f'<b>{esc(f["operator"])}</b>', badge]
        bits.append(f'<span class="meta">مج {esc(f["group"])}: {esc(f["operator_class"])}</span>')
        meth = esc(f['method'])
        if f.get('host_rest'):
            meth += f' · بقية={esc(f["host_rest"])}'
        bits.append(f'<span class="meta">{meth}</span>')
        if f.get('reject_reason'):
            bits.append(f'<span class="meta">(سبب المنع: {esc(f["reject_reason"])})</span>')
        else:
            if f.get('relation'):
                bits.append(f'<span class="meta">المعمول: {esc(relation_text(f["relation"]))}</span>')
            why = (f.get('judgement') or {}).get('deferred_because')
            if why:
                bits.append(f'<span class="meta">(سبب التأجيل: {esc(" | ".join(why))})</span>')
        out.append('<span class="op">' + ' — '.join(bits) + '</span>')
    return ''.join(out)


def irab_html(items):
    if not items:
        return '<span class="muted">—</span>'
    return ''.join(f'<span class="op"><b>{esc(slot)}</b>: {esc(role)} '
                   f'<span class="meta">[{esc(st)}]</span></span>' for slot, role, st in items)


KIND_AR = {'madi': 'ماضٍ', 'mudari': 'مضارع', 'amr': 'أمر'}
VOICE_AR = {'active': 'معلوم', 'passive': 'مجهول'}
PERSON_AR = {1: 'متكلم', 2: 'مخاطب', 3: 'غائب'}
NUMBER_AR = {'singular': 'مفرد', 'dual': 'مثنى', 'plural': 'جمع'}
GENDER_AR = {'masc': 'مذكر', 'fem': 'مؤنث'}


def _feat(f):
    p, n, g = f
    return ' '.join(x for x in (PERSON_AR.get(p, ''), NUMBER_AR.get(n, ''), GENDER_AR.get(g, '')) if x)


def morph_html(a, wi):
    """الفعل وفاعله (T18) والجذر والوزن (T19c) للكلمة wi، بحالاتها ومنها المؤجَّل وسببه"""
    out = []
    for agr in a.get('agreement', []):
        if agr['word_index'] != wi:
            continue
        slot = a['segments'][wi]['slots'][agr['slot']]['text']
        bits = [f'<b>{esc(slot)}</b>: فعل {esc(KIND_AR.get(agr.get("kind"), ""))}']
        if 'voice' in agr:
            bits.append(esc(VOICE_AR.get(agr['voice'], 'المعلوم أو المجهول')))
        if agr.get('pronouns'):
            bits.append('الفاعل: ' + ' أو '.join(f'«{esc(p)}»' for p in agr['pronouns']) +
                        f' ({esc(" / ".join(_feat(f) for f in agr.get("features", [])))})')
        if agr.get('rule'):
            bits.append(f'<span class="meta">بـ{esc(agr["rule"])}</span>')
        out.append('<span class="op">' + '، '.join(bits) + ' <span class="meta">[T18]</span></span>')
    for m in a.get('morph', []):
        if m['word_index'] != wi:
            continue
        slot = a['segments'][wi]['slots'][m['slot']]['text']
        st = m['status']
        badge = f'<span class="st st-{esc(st)}">{esc(STATUS_AR.get(st, st))}</span>'
        if st == 'accepted':
            wazn = WAZN.get(m['form_class'], m['form_class'])
            txt = f'الجذر «{esc(" ".join(m["root"]))}»، الوزن {esc(wazn)} ({esc(m["form_class"])})'
            if m['level'] == 'event':
                ev = m['event']
                txt += (f' <span class="meta">— حدث HFN: {esc(ev["verb"])}' +
                        (f' ← {esc(ev["masdar"])}' if ev.get('masdar') else '') + '</span>')
            else:
                txt += ' <span class="meta">— الجذر في HFN، والوزن بالقالب</span>'
        else:
            txt = f'<span class="meta">{esc(m.get("reason") or "")} ({m.get("n_candidates", 0)} مرشَّحاً)</span>'
        out.append(f'<span class="op"><b>{esc(slot)}</b>: {badge} {txt} <span class="meta">[T19c]</span></span>')
    return ''.join(out) if out else '<span class="muted">—</span>'


def summary_pills(counter, extra_class=''):
    out = []
    for t in TYPES:
        n = counter.get(t, 0)
        if n == 0 and t in ('OTHER', 'POISON'):
            continue
        cls = f't-{t}' if t in ('OTHER', 'POISON') and n else ''
        out.append(f'<span class="pill {cls}"><b>{esc(t)}</b>: {n}</span>')
    return f'<div class="summary {extra_class}">' + ''.join(out) + '</div>'


def verse_counter(by_word):
    c = Counter()
    for wi in by_word:
        for s in by_word[wi]:
            c[syl_type(s['cv'])] += 1
    return c


def verse_html(a, idx):
    by_word = syllables_by_word(a['syll'])
    n_words = a['syll']['n_words']
    raw_words = a['syll']['raw_words']
    words = a['words']

    # عوامل مفهرسة بحسب رقم الكلمة
    ops_by_word = {}
    for f in a['operators']:
        ops_by_word.setdefault(f['word_index'], []).append(f)

    rows = []
    for wi in range(n_words):
        word = words[wi] if wi < len(words) else raw_words[wi]
        units = a['segments'][wi]['units']
        cells, pats = [], []
        for u in units:
            if u['kind'] == 'cut':
                cells.append(chips_html(u['syllables']))
                pats.append(' '.join(s['cv'] for s in u['syllables']))
            else:
                cells.append(f'<span class="chip t-FIXED">{esc(u["text"])}<small>{esc(u["label"])}</small></span>')
                pats.append('—')
        rows.append(
            '<tr>'
            f'<td class="num">{wi}</td>'
            f'<td class="word">{esc(word)}</td>'
            f'<td>{"".join(cells)}</td>'
            f'<td class="cv">{esc(" | ".join(pats))}</td>'
            f'<td>{irab_html([x for x in word_irab(a, wi) if x[2] != "T19c"])}</td>'
            f'<td>{morph_html(a, wi)}</td>'
            f'<td>{ops_html(ops_by_word.get(wi, []))}</td>'
            '</tr>'
        )

    has_in = has_inshai_operator(a['operators'])
    vlabel = 'فيها عامل إنشائي' if has_in else 'ليس فيها عامل إنشائي'
    vcls = 'mood-in' if has_in else 'mood-kh'
    head = [f'<h2>الآية {idx} <span class="mood {vcls}">{esc(vlabel)}</span></h2>',
            f'<div class="card"><div class="orig">{esc(a["verse"])}</div>']
    head.append(f'<div class="muted">المُطبَّع: {esc(a["normalized"])}</div>')
    if a['syllabified_text'] != a['normalized']:
        head.append(f'<div class="muted">للتقطيع: {esc(a["syllabified_text"])}</div>')
    head.append('</div>')

    table = (
        '<table><thead><tr>'
        '<th>#</th><th>الكلمة</th><th>المقاطع</th><th>نمط CV</th><th>الإعراب</th><th>الفعل والجذر والوزن</th><th>العوامل</th>'
        '</tr></thead><tbody>' + ''.join(rows) + '</tbody></table>'
    )

    c = verse_counter(by_word)
    total = sum(c.values())
    summ = (f'<div class="muted">مجموع المقاطع: {total}'
            f' (SYLLABLES={a["syll"]["n_syll"]})</div>' + summary_pills(c))
    return '\n'.join(head) + table + summ, c


def build_html(analyses):
    body = []
    grand = Counter()
    sections = []
    for i, a in enumerate(analyses, 1):
        s, c = verse_html(a, i)
        grand += c
        sections.append(s)


    # مفتاح الألوان
    key = ['<div class="key">']
    for t in TYPES:
        cls = f't-{t}'
        key.append(f'<span class="chip {cls}">{esc(t)}<small>{esc(TYPE_LABEL[t].split(" — ")[-1])}</small></span>')
    key.append('</div>')

    # عدّ خبري/إنشائي: الآيات بوجود عاملٍ إنشائيّ غير ممنوع؛ والمرشَّحات بحالتها (T09)
    v_in = sum(1 for a in analyses if has_inshai_operator(a['operators']))
    n_in = n_kh = n_def = 0
    states = {k: 0 for k in STATUS_AR}
    for a in analyses:
        for f in a['operators']:
            states[f.get('status')] = states.get(f.get('status'), 0) + 1
            if f.get('status') == BLOCKED:
                continue
            m = op_mood(f)
            if m == 'إنشائي':
                n_in += 1
            elif m == 'خبري':
                n_kh += 1
            else:
                n_def += 1
    mood_pills = (
        '<div class="summary">'
        f'<span class="pill">الآيات: <span class="mood mood-in">فيها عامل إنشائي</span> {v_in}'
        f' · <span class="mood mood-kh">ليس فيها</span> {len(analyses) - v_in}</span>'
        f'<span class="pill">المرشَّحات غير الممنوعة: <span class="mood mood-in">إنشائي</span> {n_in}'
        f' · <span class="mood mood-kh">خبري</span> {n_kh}'
        f' · <span class="mood mood-def">مؤجَّل</span> {n_def}</span>'
        '<span class="pill">حالات الحكم (T09): '
        + ' · '.join(f'<span class="st st-{k}">{STATUS_AR[k]}</span> {v}' for k, v in states.items()) +
        '</span></div>'
    )
    agr = [g for a in analyses for g in a.get('agreement', [])]
    mor = [m for a in analyses for m in a.get('morph', [])]
    acc = [m for m in mor if m['status'] == 'accepted']
    morph_pills = (
        '<div class="summary">'
        f'<span class="pill">الأفعال (T18): {len(agr)} · '
        + ' · '.join(f'{KIND_AR[k]} {sum(1 for g in agr if g.get("kind") == k)}' for k in KIND_AR) +
        f' · بفاعل محدَّد {sum(1 for g in agr if len(g.get("pronouns", [])) == 1)}</span>'
        f'<span class="pill">الجذر والوزن (T19c): {len(mor)} · '
        f'<span class="st st-accepted">مقبول</span> {len(acc)} '
        f'(بحدث {sum(1 for m in acc if m["level"] == "event")} · بالجذر {sum(1 for m in acc if m["level"] != "event")})'
        f' · <span class="st st-deferred">مؤجَّل</span> {len(mor) - len(acc)}</span>'
        '</div>'
    )

    header = [
        '<h1>تقرير الكلمات ومقاطعها</h1>',
        '<div class="muted">النص كما هو: كل كلمة تُقطَّع مستقلّة بحركاتها المكتوبة، بلا وصل ولا وقف؛ والتنوين حركة واحدة من جنسه.</div>',
        '<div class="muted">الكلمة تُجزَّأ خانات: العامل (من الفهرس) والمبني (ما في ملف المبنيات وحده: الكلمة، وحرف العطف، '
        'والضمير المتصل) لا يُقطَّعان ويُعرض وسمهما، ولفظ الجلالة لا يُقطَّع. وما سواها يُقطَّع، ومنه الفعل الماضي والأمر وأل التعريف. '
        'ولا تُفصل خانة تبدأ بساكن عمّا قبلها.</div>',
        f'<div class="muted">عدد الآيات: {len(analyses)} — النطاق: أنماط CV فقط (بلا أحكام تجويد صوتية).</div>',
        '<div class="card">',
        '<div class="muted">الملخّص الإجمالي:</div>',
        summary_pills(grand, 'total'),
        '<div class="muted" style="margin-top:6px">مفتاح الألوان:</div>',
        ''.join(key),
        '</div>',
        '<div class="card">',
        '<div class="muted">خبري/إنشائي بمعيار القسمة المعتمد (Q01): الإنشائي ما تُوقع مساهمةُ العامل فيه فعلاً '
        'بالتلفّظ ولا يُردّ إلى تقييد مضمون آخر، وهو الطلب (النداء، والأمر بلام الأمر وأسماء أفعال الأمر، والنهي، والتمني) '
        'والإيقاع (المدح والذم: نِعْمَ، بِئْسَ، سَاءَ، حَبَّذَا). والخبري ما يبني مضموناً أو علاقة أو يقيّدهما، '
        'ومنه القسم والرجاء ورُبَّ وهَيْهَاتَ وشَتَّانَ وسُرْعَانَ.</div>',
        '<div class="muted">مؤجَّل (T14a): لَوْ وكَمْ، لاختلاف استعمالاتهما في الفهرس '
        '(الشرط والخبرية خبر، والتمني والاستفهام طلب)؛ ولا يُحكم للوحدة إلا إذا اتّحدت استعمالاتها.</div>',
        '<div class="muted">لا يشمل وسم الآية الإنشاء بالصيغ (فعل الأمر، اللهم، همزة الاستفهام). '
        'فمصدر الطلب في «اُخْرُجْ» صيغة الأمر لا عامل (T13).</div>',
        '<div class="muted">حالات الحكم (T09): مقبول إذا ثبت السبب والشرط بالكتابة ولا منافس له على خانته؛ '
        'وممنوع إذا ثبت مانع بالكتابة، ولا يُعَدّ إنشائياً ولا خبرياً ولا يدخل في وسم الآية؛ ومؤجَّل فيما سوى ذلك.</div>',
        mood_pills,
        '</div>',
        '<div class="card">',
        '<div class="muted">الفعل وفاعله (T18): الفاعل ما يوافق لاحقة الفعل أو سابقته في جدول الإسناد، ويُضيَّق بضمير منفصل قبله. '
        'والجذر والوزن (T19c): المرشَّحات من قوالب الأوزان بقيود الحركات والمعتل، ولا يُقبل منها إلا المرخَّص في HFN: '
        'بحدثٍ مسجَّل بالجذر والوزن، أو بالجذر وحده والوزن بالقالب؛ وما سوى ذلك مؤجَّل مع سببه.</div>',
        morph_pills,
        '</div>',
    ]

    doc = [
        '<!doctype html>',
        '<html lang="ar" dir="rtl"><head><meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        '<title>تقرير الكلمات ومقاطعها</title>',
        f'<style>{CSS}</style></head><body>',
        '\n'.join(header),
        '\n'.join(sections),
        '</body></html>',
    ]
    return '\n'.join(doc), grand
