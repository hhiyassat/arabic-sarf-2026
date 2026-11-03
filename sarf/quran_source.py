# -*- coding: utf-8 -*-
"""
sarf/quran_source.py — نصّ المصحف المدخل: منفذٌ واحد تقرؤه الأدوات والاختبارات كلها.

حكم المالك (3 نوفمبر 2026): المدخل من الآن «quran-simple-enhanced» (data/quran-simple-enhanced.txt، خارج git)،
يُحوَّل بـtools/import_quran_simple.py إلى data/quran_simple.tsv بأحكامٍ ثلاثة معتمدة:
  ١ البسملة الملصقة بالآية الأولى (112 سورة) تُفصل عنها، وتُحفظ في المصدر وفي سجل العمليات؛
  ٢ «<sel>» وقفٌ غير محدَّد النوع: يُخرج من النص المحلَّل، ويُحفظ موضعه في سجل العمليات وفي عمود المصدر؛
  ٣ المواضع تتبع كلمات الملف الجديد بمسافاته (يَا أَيُّهَا كلمتان).

والنصّ القديم (مصحف المجمّع، data/quran_hafs.tsv) يُختار صراحةً بـSARF_QURAN=hafs_kfgqpc للقياس التاريخي وحده.
TSV: سورة، آية، النص المحلَّل، [سطر المصدر كما ورد].
"""
import os

H = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT = 'quran_simple'
SOURCES = {'quran_simple': os.path.join('data', 'quran_simple.tsv'), 'hafs_kfgqpc': os.path.join('data', 'quran_hafs.tsv')}
# قراءة الرسم في التطبيع: الحرف العاري غير المدّي في هذا الرسم ساكنٌ مُخفى أو مدغم (تَدَايَنتُم، أَنتُمْ)، فالسكون الضمني «on»؛
# ورسم المجمّع يُكشف بعلاماته («auto»). وكل قارئٍ للمصحف يمرّر هذا الوضع صراحةً إلى analyze؛ ولا يُطبَّق على النصوص الحرّة.
UTHMANI_MODE = {'quran_simple': 'on', 'hafs_kfgqpc': 'auto'}


def uthmani_mode():
    return UTHMANI_MODE[name()]


def name():
    return os.environ.get('SARF_QURAN', DEFAULT)


def tsv_path(root=H):
    n = name()
    if n not in SOURCES:
        raise SystemExit(f'SARF_QURAN={n}: غير معروف ({", ".join(SOURCES)})')
    p = os.path.join(root, SOURCES[n])
    if not os.path.exists(p):
        raise SystemExit(f'نصّ المصحف غير موجود: {p}' + ('؛ شغّل tools/import_quran_simple.py' if n == 'quran_simple' else ''))
    return p


def rows(root=H):
    """→ [(سورة، آية، النص المحلَّل)] بترتيب المصحف"""
    out = []
    for l in open(tsv_path(root), encoding='utf-8'):
        p = l.rstrip('\n').split('\t')
        if len(p) >= 3 and p[0].isdigit():
            out.append((int(p[0]), int(p[1]), p[2]))
    return out


def source_line(s, v, root=H):
    """سطر المصدر كما ورد (بالبسملة و<sel>) إن حُفظ في العمود الرابع، وإلا النص المحلَّل"""
    for l in open(tsv_path(root), encoding='utf-8'):
        p = l.rstrip('\n').split('\t')
        if len(p) >= 3 and p[0] == str(s) and p[1] == str(v):
            return p[3] if len(p) >= 4 else p[2]
    return None
