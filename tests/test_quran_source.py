#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tests/test_quran_source.py — المصحف المعتمد (quran-simple-enhanced، حكم المالك 3 نوفمبر 2026): الاستيراد وأحكامه الثلاثة،
وقراءة الرسم في التطبيع، واختبارٌ عابر للطبقات بالمصدر نفسه الذي يُبنى عليه التقرير (صفحة المسار).
"""
import html, json, os, subprocess, sys, tempfile

H = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + '/'
sys.path.insert(0, H)
os.environ.pop('SARF_QURAN', None)
from sarf import quran_source as Q

FAIL = []


def check(name, cond, got=''):
    print(('PASS ' if cond else 'FAIL ') + name + ('' if cond else f' — {got}'))
    if not cond:
        FAIL.append(name)


if not os.path.exists(H + 'data/quran_simple.tsv'):
    print('SKIP: يحتاج data/quran_simple.tsv (tools/import_quran_simple.py)')
    sys.exit(0)

R = Q.rows()
D = {(s, v): t for s, v, t in R}
ops = json.load(open(H + 'data/quran_simple_ops.json', encoding='utf-8'))
check('Q01 المصدر الافتراضي quran_simple، ووضع قراءته «on»', Q.name() == 'quran_simple' and Q.uthmani_mode() == 'on', (Q.name(), Q.uthmani_mode()))
check('Q02 6236 آية بالترتيب على أعداد حفص', len(R) == 6236 and R[0][:2] == (1, 1) and R[-1][:2] == (114, 6), (len(R), R[-1][:2]))
check('Q03 البسملة مفصولةٌ في 112 سورة (غير الفاتحة والتوبة)، ومحفوظةٌ في سجل العمليات وفي سطر المصدر',
      ops['counts']['basmala_separated'] == 112 and ops['counts']['untouched_first_verses'] == 0 and D[(2, 1)] == 'الم'
      and Q.source_line(2, 1).endswith(' الم') and Q.source_line(2, 1).startswith('بِسْمِ'), (ops['counts'], D[(2, 1)]))
src95, src97 = Q.source_line(95, 1).split(' '), Q.source_line(97, 1).split(' ')
check('Q04 «بِّسْمِ» بشدّة الباء (95:1، 97:1) مفصولةٌ أيضاً: النص المحلَّل هو سطر المصدر بعد كلمات البسملة الأربع',
      D[(95, 1)].split(' ') == src95[4:] and D[(97, 1)].split(' ') == src97[4:] and '\u0651' in src95[0], (src95[:5], D[(95, 1)]))
check('Q05 الفاتحة 1:1 هي البسملة، والتوبة 9:1 بلا بسملة', D[(1, 1)].startswith('بِسْمِ') and D[(9, 1)].startswith('بَرَاءَةٌ'), '')
check('Q06 «<sel>» خارج النص المحلَّل كله (4287 موضعاً في سجل العمليات)', not any('<sel>' in t or '<' in t for _, _, t in R)
      and ops['counts']['sel'] == 4287, ops['counts']['sel'])
w282 = D[(2, 282)].split()
check('Q07 المواضع بكلمات الملف: 2:282 = 129 كلمة، و«يَا» و«أَيُّهَا» كلمتان', len(w282) == 129
      and w282[:2] == [x for x in Q.source_line(2, 282).split(' ') if x != '<sel>'][:2] and len(w282[0]) <= 3, (len(w282), w282[:2]))
check('Q08 لا حرف ولا حركة تغيّرا: النص المحلَّل هو سطر المصدر بلا البسملة و«<sel>»', all(
    ' '.join(w for w in (Q.source_line(s, v) or '').split(' ') if w and w != '<sel>').endswith(t) for s, v, t in R[:300]), '')

# قراءة الرسم: الحرف العاري غير المدّي ساكن (تَدَايَنتُم ← تَدَايَنْتُمْ) في المصدر المعتمد وحده
from sarf.catalog import Catalog
from sarf.analyze import analyze
from sarf.algebra import Trace, sentence_geo
from sarf.features import unit_features
from sarf.relations import verse_relations, check_inflection
CAT = Catalog([H + 'operators_catalog.jsonl', H + 'operators_catalog_split_vocalized.csv'])
a = analyze(CAT, D[(2, 282)], Q.uthmani_mode())
w6 = a['segments'][5]['word']
check('Q09 السكون الضمني في المصدر المعتمد: «تَدَايَنتُم» ← «تَدَايَنْتُمْ»', w6 == 'تَدَايَنْتُمْ', w6)

# عابرٌ للطبقات بالمصدر نفسه: كل عبارةٍ في محور الإعراب معروضةٌ في صفحة المسار المبنية على المصحف المعتمد
_, U = sentence_geo(a, 'Q2:282', Trace())
o = verse_relations(a, U, unit_features(a, U), '2:282')
check('Q10 الفاحص المستقل نظيف على 2:282 من المصحف المعتمد', not check_inflection(o['axes'], o['tokens']),
      check_inflection(o['axes'], o['tokens'])[:3])
with tempfile.TemporaryDirectory() as d:
    out = os.path.join(d, 't.html')
    subprocess.run([sys.executable, H + 'tools/pipeline_trace.py', '2:282', '-o', out, '--quiet'], check=True, capture_output=True,
                   env={k: v for k, v in os.environ.items() if k != 'SARF_QURAN'})
    page = open(out, encoding='utf-8').read()
miss = [st for u, _, _ in o['tokens'] for st in [o['axes'][u]['inflection']['statement']] if st and html.escape(st) not in page]
check('Q11 عابر: صفحة المسار مبنيةٌ على المصحف المعتمد، وكل عبارةٍ في المحور فيها', not miss and 'quran_simple' in page, miss[:3])
check('Q12 الصفحة تعرض سطر المصدر بالبسملة و«<sel>» منفصلاً عن النص المحلَّل', '&lt;sel&gt;' in page, '')

# بوابة الحماية في الرسم الإملائي: «آ» أول الكلمة همزةُ استفهامٍ فوق همزة وصل «ال» وحدها
from sarf.protected import protected
fp = {w: protected(w) for w in ('آمَنَ', 'آيَاتِهِ', 'آلَاءِ', 'آوَوا', 'آتِي', 'آمِنْ')}
check('Q13 لا حماية زائفة لـ«آ» أول الكلمة في الرسم الإملائي (آمَنَ ليست أَ+مَنْ)', not any(fp.values()), fp)
keep = protected('آلْآنَ')
check('Q14 «آلْآنَ» تبقى: الاستفهام فوق همزة وصل «ال»', bool(keep) and keep.get('proclitics') == ['أَ'], keep)

# حكم المالك (4 نوفمبر 2026): تنوين الفتح على الألف يُنقل إلى ما قبلها في التمثيل التحليلي وحده
from sarf.normalize_trace import normalize_traced, restore_source
nt = normalize_traced('صَغِيراً أَوْ كَبِيراً', implicit_sukun=True)
check('Q15 «كَبِيراً» ← «كَبِيرًا» تحليلاً، بلا سكونٍ زائف، والعرض والمصدر كما وردا',
      nt['analysis'] == 'صَغِيرًا أَوْ كَبِيرًا' and nt['display'] == 'صَغِيراً أَوْ كَبِيراً'
      and sum(o['rule_id'] == 'N-TANWIN-ALIF' for o in nt['ops_analysis']) == 2, (nt['analysis'], nt['display']))
rec_, fails_ = restore_source(nt)
check('Q16 المصدر يُستعاد حرفياً بعد نقل التنوين، بلا إخفاق', rec_ == 'صَغِيراً أَوْ كَبِيراً' and not fails_, (rec_, fails_))
a2 = analyze(CAT, D[(2, 282)], Q.uthmani_mode())
ws = [sg['word'] for sg in a2['segments']]
check('Q17 2:282: «شَيْئًا» و«كَبِيرًا» كلمتان سليمتان (لا «كَ» + «بِيرْاً»)', 'شَيْئًا' in ws and 'كَبِيرًا' in ws
      and not any('\u0652\u0627\u064b' in w or '\u0652\u064b' in w for w in ws), [w for w in ws if 'يرًا' in w or 'ئ' in w][:4])
# إذن المالك: صور الرسم الإملائي لمداخل قائمة في الجرد
pr = {w: protected(w) for w in ('ذَلِكُمْ', 'وَمِيكَالَ', 'وَمَنَاةَ', 'ذَلِكُمَا')}
check('Q18 الجرد: «ذَلِكُمْ» و«مِيكَال» و«مَنَاة» صورٌ إملائية لمداخل قائمة، و«ذَلِكُمَا» ليست مدخلاً فلا تُضاف',
      pr['ذَلِكُمْ'] and pr['وَمِيكَالَ'] and pr['وَمَنَاةَ'] and not pr['ذَلِكُمَا'], {k: bool(v) for k, v in pr.items()})

print('ALL OK' if not FAIL else f'FAILED {len(FAIL)}: {FAIL}')
sys.exit(1 if FAIL else 0)
