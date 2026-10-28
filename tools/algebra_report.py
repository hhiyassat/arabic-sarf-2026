#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tools/algebra_report.py — تقرير HTML للجبر اللساني على المصحف، من reports/algebra_metrics.json
(يكتبه tools/algebra_quran.py).

الاستعمال: python3 tools/algebra_report.py
"""
import os, sys, json

H = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + '/'
sys.path.insert(0, H)
from sarf.output_html import CSS, esc

M = json.load(open(H + 'reports/algebra_metrics.json', encoding='utf-8'))
C = M['counts']
V = C['verses']


def pct(a, b):
    if not b:
        return '—'
    x = 100 * a / b
    return f'{x:.2f}%' if a != b and round(x, 1) == 100.0 else f'{x:.1f}%'


def table(head, rows, cls='small'):
    return (f'<table class="{cls}"><thead><tr>' + ''.join(f'<th>{esc(h)}</th>' for h in head) + '</tr></thead><tbody>' +
            ''.join('<tr>' + ''.join(f'<td>{c}</td>' for c in r) + '</tr>' for r in rows) + '</tbody></table>')


defs = [
    ('الخلية', 's = ⟨id, C, H, L, O⟩', 'Cell', 'الصامت، والحركة a/u/i/∅، والطول، وروابط الرسم (موضع الحرف، والشدة، والمدّ، وما لا يُنطق)'),
    ('الوحدة', 'G⁽ᵏ⁾ = ⟨id, τ, A, B, Θ, Ω, O⟩', 'Geo', 'النوع والمستوى، والمكوّنات المرتبة، والروابط بأدلتها، والخصائص، والالتزامات، والارتباط بالرسم'),
    ('الأثر', 'T', 'Trace', 'سجل العمليات وأدلتها، مستقل عن الهندسة'),
    ('الدليل', 'e = سبب + شروط + موانع ثبت انتفاؤها', 'Evidence.valid', 'لا يكفي «لم نجد مانعاً»: كل مانع منفيّ يحمل برهان انتفائه'),
    ('الامتداد', "G' = Extend_{k,r,e}(G, x)، Ω' = (Ω ∖ D_e) ∪ N_e", 'extend', 'يُرفض بلا دليل مكتمل، ويُرفض بمكوّنٍ غير مغلق'),
    ('الإغلاق', 'Ĝ = Close_k(G; e_c, e_b)', 'close', 'يُرفض بلا شهادتَي الإكمال والحدّ، ومع أي التزام لازم مفتوح'),
    ('Next في المقطع', 'Next(G) = متحرك إن فرغ، وإلا ساكن ما دامت الخواتم < 2', 'syllable_next', 'فالأنماط الستة CV، CVV، CVC، CVVC، CVCC، CVVCC نتيجةٌ لا قائمة'),
    ('اللفظ', 'W = Realize(R, P, F; e)  أو  Lex(e)', 'unit_geo', 'الفعل بقالب وزنه، واسما الفاعل والمفعول بقالبيهما قياساً، والمصدر وغيره مدخلاً معجمياً في HFN، والعامل والمبني ولفظ الجلالة مداخل معجمية'),
    ('α وβ', 'α: الخلايا ↦ مواقع الجذر والزوائد؛ β: الخلايا ↦ المقاطع', 'align_alpha، syllabify', 'وقيد الإغلاق: Flatten(β) = الخلايا = ما يحققه Realize(R, P) بالترتيب'),
    ('الجملة', 'J = Close(U₁ ⊙ U₂ ⊙ …)', 'sentence_geo', 'الروابط: العامل ← المعمول بحكمه المقبول، والإسناد بجدول T18؛ والالتزامات: المعمول، والخبر، والفاعل، وإغلاق كل وحدة'),
    ('البناء', 'Build_k(x₁…xₙ; e) = Close_k(FoldExtend_k(G₀; x₁…xₙ); e_c, e_b)', 'build', 'الفقرة (السورة) من الجمل (الآيات)، والموضوع (المصحف) من الفقرات'),
]

thm = [
    ('الأولى: حفظ الوقوعات', 'كل موضع رسمٍ مغطّى مرةً واحدة بخلية أو بوقوعٍ لا يُنطق، وكل خلية يبلغها البناء من أعلاه (وما لم يُغلق محفوظ في O معلَّقاً)', C.get('T1_pass', 0)),
    ('الثانية: اتساق الجذر والوزن والتقطيع', 'في كل وحدة مغلقة: Flatten(β) هي الخلايا نفسها، وα معرَّفة على كل خلية', C.get('T2_pass', 0)),
    ('الثالثة: سلامة البناء', 'كل عقدة مغلقة تحمل شهادتين صالحتين، وكل امتداد في الأثر يحمل دليلاً مكتملاً', C.get('T3_pass', 0)),
    ('الرابعة: لا إغلاق من نفاد المحاولات', 'لا عقدة مغلقة فيها التزام لازم مفتوح؛ وما لم تثبت شهادتاه مؤجَّل', C.get('T4_pass', 0)),
    ('الخامسة: الرجوع', 'Render(Analyze(x)) = x للآية المطبَّعة كاملة', C.get('T5_pass', 0)),
]

lv = [
    ('خلية', C['cells'], C['cells'], 'كل خلية عنصر أساسي'),
    ('مقطع', C['syllables'], C['syllables_closed'], 'بالقوالب الستة'),
    ('وحدة لفظية', C['units'], C['units_closed'], 'بمدخل معجمي أو بـRealize'),
    ('جملة (آية)', V, C['sentence_closed'], 'بعد إغلاق وحداتها كلها واستيفاء التزاماتها'),
    ('فقرة (سورة)', C['paragraphs'], C['paragraphs_closed'], 'بعد إغلاق آياتها كلها'),
    ('موضوع (المصحف)', 1, C['topic_closed'], 'بعد إغلاق سوره كلها'),
]

parts = [
    '<h1>الجبر اللساني على المصحف</h1>',
    '<div class="muted">هندسة ذات أنواع تُبنى تكرارياً بالامتداد المرخَّص، وتُغلق بشهادتَي الإكمال والحدّ، ثم تدخل مكوّناً في المستوى الأعلى: '
    'خلية ≺ مقطع ≺ وحدة لفظية ≺ جملة ≺ فقرة ≺ موضوع. وفي المصحف الجملة موضعها الآية، والفقرة السورة، والموضوع المصحف. '
    'الكود: <code>sarf/algebra.py</code>، والتشغيل: <code>tools/algebra_quran.py</code>.</div>',
    '<div class="card"><div class="muted"><b>ما يثبته هذا التقرير وما لا يثبته.</b> '
    'التمثيل كلّيّ: لكل آية تعبيرٌ جبري واحد أوراقه خلايا، ومنه يعود نصها حرفاً بحرف. '
    'والمبرهنات الخمس شرطية، وقد فُحصت آليّاً على كل وقوع في المصحف. '
    'أما الإغلاق، أي أن تثبت كل وحدة بدليل لغوي، فمقياس تغطية القواعد المكتوبة حتى الآن، ولا يثبته البرهان الجبري. وهو مبيَّن هنا بأرقامه وأسباب ما بقي.</div></div>',
    '<h2>١. التعريفات وتنفيذها</h2>',
    table(['العنصر', 'التعريف', 'في الكود', 'ملاحظة'], [(esc(a), f'<code>{esc(b)}</code>', f'<code>{esc(c)}</code>', esc(d)) for a, b, c, d in defs]),
    '<h2>٢. المبرهنات، مفحوصةً على المصحف كله</h2>',
    table(['المبرهنة', 'ما يُفحص', 'الآيات التي تحققت فيها'],
          [(esc(a), esc(b), f'<b>{n} / {V}</b> ({pct(n, V)})') for a, b, n in thm]),
    '<div class="muted">'
    f'وAnalyze(Render(a)) ∋ a: أُعيد تحليل النص المستخرَج في {C.get("reanalyze", 0)} آية (آية من كل عشرين)، '
    f'فأعطى الخلايا والإغلاق أنفسهما في {C.get("reanalyze_same", 0)}. '
    f'وفي الأثر {C["trace_ops"]:,} عملية: {C["trace_extend"]:,} امتداداً، و{C["trace_close"]:,} إغلاقاً، و{C["trace_defer"]:,} تأجيلاً، '
    'وكلها بدليل؛ والامتداد بلا دليل أو بمكوّنٍ غير مغلق يُرفض بالبناء نفسه، والإغلاق بلا شهادتين كذلك.<br>'
    f'وتقطيع الجبر (من تعريف Next وحده) يطابق تقطيع المقطِّع في {C["beta_agrees"]:,} من {C["cut_units_syllabified"]:,} وحدة مقطَّعة ({pct(C["beta_agrees"], C["cut_units_syllabified"])}).'
    '</div>',
    '<h2>٣. البناء في كل مستوى</h2>',
    table(['المستوى', 'المبني', 'المغلق', 'النسبة', 'شرط الإغلاق'],
          [(esc(a), f'{b:,}', f'{c:,}', pct(c, b), esc(d)) for a, b, c, d in lv]),
    '<div class="muted">الجملة لا تُغلق إلا إذا أُغلقت وحداتها كلها، فوحدة واحدة مؤجَّلة تؤجّل آيتها، والآية المؤجَّلة تؤجّل سورتها. '
    'ولذلك ينخفض الإغلاق كلما صعدنا، وهو مقتضى القانون التكراري لا خلل فيه.</div>',
    '<h2>٤. كيف أُغلقت الوحدات، ولماذا بقي ما بقي</h2>',
    table(['طريق الإغلاق', 'الوحدات'], [(esc(k), f'{v:,}') for k, v in M['unit_closed_by'].items()]),
    table(['سبب تأجيل الوحدة', 'الوحدات'], [(esc(k or '—'), f'{v:,}') for k, v in list(M['unit_deferred'].items())[:12]]),
    table(['الالتزام المفتوح في الجملة', 'المواضع'], [(esc(k), f'{v:,}') for k, v in M['sentence_open'].items()]),
    '<div class="muted">صحة ما أُغلق: جذر كل وحدة مغلقة بـRealize أو بالبناء المعجمي يُقارَن بجذر مدوَّنة QAC '
    '(<code>tools/eval_algebra.py</code>). فالإغلاق سلامةٌ بالنسبة إلى القواعد، وصحته اللغوية تُقاس:</div>',
    table(['طريق الإغلاق', 'الموافق لـQAC', 'النسبة'],
          [(esc(r), f'{M.get("root_vs_qac", {}).get(r + " ✓", 0):,} / {M.get("root_vs_qac", {}).get(r, 0):,}',
            pct(M.get('root_vs_qac', {}).get(r + ' ✓', 0), M.get('root_vs_qac', {}).get(r, 0)))
           for r in ('فعل', 'اسم فاعل/مفعول قياساً', 'مدخل معجمي (مصدر وغيره)', 'بناء سيبويه')]),
    '<h2>٥. أمثلة: التعبير الجبري للآية</h2>',
    '<div class="card"><div class="muted">مثال من التعريف: كَتَّبَ</div><pre class="json">'
    'Cells(كَتَّبَ) = ⟨ك,a⟩⟨ت,∅⟩⟨ت,a⟩⟨ب,a⟩\n'
    'α = ⟨r1, r2, r2, r3⟩        β = ⟨كَتْ، تَ، بَ⟩ = ⟨CVC، CV، CV⟩\n'
    'Flatten(β) = Cells = Realize(ك ت ب، فَعَّلَ)\n'
    'Root(كَتَبَ) = Root(كَاتَبَ) = ك ت ب،  وCells(كَتَبَ) ≠ Cells(كَاتَبَ)</pre></div>',
]
for ref, x in M['samples'].items():
    parts.append(f'<div class="card"><div><b>{esc(ref)}</b> {esc(x["text"])} — '
                 + ('<span class="st st-accepted">J مغلقة</span>' if x['closed'] else '<span class="st st-deferred">J مؤجَّلة</span>')
                 + '</div><pre class="json">' + esc('\n'.join(x['units'])) + '</pre>')
    if x['bonds']:
        parts.append('<div class="muted">الروابط:</div><pre class="json">' + esc('\n'.join(x['bonds'])) + '</pre>')
    if x['open']:
        parts.append('<div class="muted">Ω المفتوحة: ' + esc('، '.join(x['open'])) + '</div>')
    parts.append('</div>')
parts += [
    '<h2>٦. ما يلزم لرفع الإغلاق</h2>',
    '<ul class="muted">'
    '<li>الاسم: الجذر والوزن لأوزان الاسم كلها (الجموع، والصفات، والجامد)، فلا يُغلق الآن إلا ما في HFN من مصدر أو اسم فاعل أو مفعول، أو ما يحققه قالب اسمي الفاعل والمفعول قياساً.</li>'
    '<li>الخبر والنعت والحال (T05، T10): التزامات مفتوحة في الجملة.</li>'
    '<li>حدود الجملة داخل الآية، وعلاقات الفقرة والموضوع فوق الاحتواء: لم تُعرَّف قواعدها بعد.</li>'
    '<li>الفعل المضارع المرفوع بلا لاحقة ولا عامل: لا تثبت فعليته بالكتابة بعد.</li></ul>',
]
doc = ('<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8">'
       '<meta name="viewport" content="width=device-width, initial-scale=1"><title>الجبر اللساني على المصحف</title>'
       f'<style>{CSS}\ncode{{font-family:ui-monospace,Menlo,Consolas,monospace;font-size:14px}}</style></head><body>'
       + '\n'.join(parts) + '</body></html>')
open(H + 'reports/algebra_report.html', 'w', encoding='utf-8').write(doc)
print('كُتب reports/algebra_report.html')
