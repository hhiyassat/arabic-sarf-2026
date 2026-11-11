"""source_contract.py — عقد المصدر لروابط ahdath_ajnas (SARF_HFN_V50_COMPATIBILITY_01 §٤–§٦).
يُشتقّ لكل رابطٍ مصدره وجولته وقياس جولته وقيوده من صفّه نفسه، دون تعديل الصف ودون توليد قيمةٍ غير موجودة.

- المصدر: LISAN إذا حمل residual العلامة SOURCE_LISAN_NO_GENUS_BAB، وإلا MUKHASSAS. ولكلٍّ متطلباته:
    MUKHASSAS: الكتاب والباب ورقم السند (رقمي) ورقم سطر الشاهد (رقمي) والشاهد غير فارغة.
    LISAN:     حقول المخصّص الثلاثة فارغة (لا تُملأ)، والشاهد غير فارغ، ورقم السطر رقمي، وqawl بالقالب المعلن في البيانات نفسها
               «على ذكر صاحب لسان العرب، مادّة «X» (سطر N من نصّ OpenITI)» فتُستخرج المادة X والسطر N، ويجب أن يساوي N رقم سطر الشاهد؛
               وإلا فالمادة MISSING بسببها، ولا تُستنتج بقاعدةٍ غير معلنة. وmethod يبدأ بـ «R3 Lisan».
- الجولة من method: R1_MUKHASSAS، R2_WIDER، R2_KHILAF، R3_LISAN؛ وقياس الجولة من كتلتها في MANIFEST الإصدار المثبّت نفسه
  (لا يُعمَّم قياس جولةٍ على غيرها، ولا 0.822 على الكل).
- القيود الظاهرة: GENERIC_HUMAN_NOT_GENUS (LISAN_GENERIC_HUMAN_DHAT: «الرجل/فلان» مثال الإنسان عامةً لا جنسٌ مخصوص)،
  WIDER_FORM_NO_GENERALIZATION (WIDER_FORM أو ROUND2_WIDER_FORMS: لا تعميم للصيغة الأوسع على كل استعمالات الحدث)،
  وDHAT_WORD_READERS_DIFFER إن وُجد.
- قاعدة الاستشهاد الوصفي META_CITATION (موثّقة، لا قائمة أسماء): الرابط يُستبعد من الاستهلاك الحي إذا كان حدثه فعلَ نقلٍ أو حكمٍ
  علمي من مجموعةٍ معلنة (CITATION_VERBS) وكانت ذاته في الشاهد فاعلَ صيغةٍ من الفعل نفسه مباشرةً — فالشاهد يصف فعل اللغوي نفسه
  (قال سيبويه، أجاز أبو علي، زعم قوم) لا استعمال الحدث في اللغة. ويبقى الصف الأصلي، ويُسجَّل الاستبعاد بدليله (مقتطف الشاهد).
  وما كانت ذاته بعد فعل نقلٍ ولم يتحقق الشرطان معاً يُعلَّم FLAG_SCHOLAR_CONTEXT_FOR_REVIEW ولا يُستبعد."""
import json, os, re, unicodedata

LISAN_MARK = 'SOURCE_LISAN_NO_GENUS_BAB'
QAWL_LISAN = re.compile(r'^على ذكر صاحب لسان العرب، مادّة «([^»]+)» \(سطر (\d+) من نصّ OpenITI\)$')
CITATION_VERBS = {'قَالَ': 'قال', 'رَوَى': 'روى', 'حَكَى': 'حكى', 'أَجَازَ': 'أجاز', 'زَعَمَ': 'زعم', 'أَنْشَدَ': 'أنشد', 'ذَكَرَ': 'ذكر', 'غَلِطَ': 'غلط'}
CITE_ANY = r'(?:قال|وقال|روى|رواه|ورواه|حكى|وحكى|أجاز|وأجاز|زعم|وزعم|أنشد|وأنشد|ذكر|وذكر|غلط فيه)'
CONTRACT = 'AJNAS_SOURCE_CONTRACT_v1'


def marks(row):
    return [p.strip().split(' (')[0] for p in (row.get('residual') or '').split('·') if p.strip()]


def source_of(row):
    return 'LISAN' if LISAN_MARK in marks(row) else 'MUKHASSAS'


def round_of(row):
    m = row.get('method') or ''
    return 'R3_LISAN' if m.startswith('R3 Lisan') else 'R2_WIDER' if m.startswith('R2 wider forms') else 'R2_KHILAF' if m.startswith('R2 KHILAF') else 'R1_MUKHASSAS'


def measurements(release_dir):
    """قياس كل جولة من MANIFEST الإصدار نفسه، بمقامه؛ والجولة بلا قياسٍ منشور تُعلَّم بذلك"""
    m = json.load(open(os.path.join(release_dir, 'MANIFEST.json'), encoding='utf-8'))
    out = {}
    a = (m.get('ahdath_ajnas') or {}).get('agreement_yes_rows')
    if a:
        out['R1_MUKHASSAS'] = dict(kind='YES_ROW_AGREEMENT_WILSON_LOW', value=a.get('rate'), agree=a.get('agree'), rows=a.get('rows'), gate=a.get('gate'),
                                   passes_gate=a.get('passes_gate'), manifest_key='ahdath_ajnas.agreement_yes_rows')
    r2 = m.get('ahdath_ajnas_round2') or {}
    w = r2.get('wider_forms') or {}
    if w:
        out['R2_WIDER'] = dict(kind='YES_ROW_AGREEMENT_WILSON_LOW', value=w.get('yes_rows_wilson_low'), agree=w.get('yes_rows_agree'), rows=w.get('yes_rows'),
                               gate=w.get('gate'), passes_gate=(w.get('yes_rows_wilson_low') or 0) >= (w.get('gate') or 1), manifest_key='ahdath_ajnas_round2.wider_forms')
    k = r2.get('khilaf_reread') or {}
    if k:
        out['R2_KHILAF'] = dict(kind='NO_PUBLISHED_AGREEMENT_MEASURE', settled_3of4=k.get('settled_3of4'), links=k.get('links'),
                                manifest_key='ahdath_ajnas_round2.khilaf_reread')
    r3 = m.get('ahdath_ajnas_round3_lisan') or {}
    if r3:
        out['R3_LISAN'] = dict(kind='YES_ROW_AGREEMENT_WILSON_LOW', value=r3.get('yes_rows_wilson_low'), agree=r3.get('yes_rows_agree'), rows=r3.get('yes_rows'),
                               gate=r3.get('gate'), passes_gate=(r3.get('yes_rows_wilson_low') or 0) >= (r3.get('gate') or 1), manifest_key='ahdath_ajnas_round3_lisan')
    return out


def lisan_madda(row):
    m = QAWL_LISAN.match(row.get('qawl') or '')
    if not m:
        return dict(madda=None, line=None, status='MISSING: qawl لا يطابق القالب المعلن')
    if m.group(2) != (row.get('shahid_line') or ''):
        return dict(madda=m.group(1), line=m.group(2), status='INCONSISTENT: سطر qawl ≠ shahid_line')
    return dict(madda=m.group(1), line=m.group(2), status='OK')


def requirements(row):
    """→ قائمة مخالفات متطلبات المصدر (فارغة إن استوفى)"""
    v = []
    src = source_of(row)
    if src == 'MUKHASSAS':
        for f in ('mukhassas_book', 'mukhassas_bab', 'shahid'):
            if not (row.get(f) or '').strip():
                v.append(f'MUKHASSAS_MISSING:{f}')
        for f in ('mukhassas_sid', 'shahid_line'):
            if not (row.get(f) or '').isdigit():
                v.append(f'MUKHASSAS_NOT_NUMERIC:{f}')
    else:
        if any((row.get(f) or '').strip() for f in ('mukhassas_book', 'mukhassas_bab', 'mukhassas_sid')):
            v.append('LISAN_WITH_MUKHASSAS_FIELDS')
        if not (row.get('shahid') or '').strip():
            v.append('LISAN_MISSING:shahid')
        if not (row.get('shahid_line') or '').isdigit():
            v.append('LISAN_NOT_NUMERIC:shahid_line')
        md = lisan_madda(row)
        if md['status'] != 'OK':
            v.append('LISAN_MADDA_' + md['status'].split(':')[0])
        if not (row.get('method') or '').startswith('R3 Lisan'):
            v.append('LISAN_METHOD_NOT_R3')
    for f in ('link_id', 'event_id', 'qawl', 'residual', 'rank'):
        if not (row.get(f) or '').strip():
            v.append(f'MISSING:{f}')
    return v


def flags(row):
    mk = set(marks(row))
    out = []
    if 'LISAN_GENERIC_HUMAN_DHAT' in mk:
        out.append('GENERIC_HUMAN_NOT_GENUS')
    if 'WIDER_FORM' in mk or 'ROUND2_WIDER_FORMS' in mk:
        out.append('WIDER_FORM_NO_GENERALIZATION')
    if 'DHAT_WORD_READERS_DIFFER' in mk:
        out.append('DHAT_WORD_READERS_DIFFER')
    return out


def meta_citation(row):
    """→ None، أو dict(decision=EXCLUDE|FLAG، evidence=…)"""
    d = (row.get('dhat') or '').strip()
    sh = row.get('shahid') or ''
    if not d:
        return None
    v = unicodedata.normalize('NFC', row.get('verb') or '')
    if v in CITATION_VERBS:
        stem = CITATION_VERBS[v]
        m = re.search(r'(?:^|[\s(])(?:و|ف)?' + stem + r'(?:ه|ها|وا)?\s+(?:فيه\s+)?' + re.escape(d) + r'(?=[\s:،,.؛]|$)', sh)
        if m:
            return dict(decision='EXCLUDE', rule='META_CITATION', verb=v, dhat=d, evidence=sh[max(0, m.start() - 30):m.end() + 30],
                        reason='حدث الرابط فعلُ نقلٍ أو حكمٍ علمي، وذاته في الشاهد فاعلُ الفعل نفسه: الشاهد يصف فعل اللغوي لا استعمال الحدث')
    m = re.search(CITE_ANY + r'\s+' + re.escape(d) + r'(?=[\s:،,.؛]|$)', sh)
    if m and v in CITATION_VERBS:
        return dict(decision='FLAG', rule='SCHOLAR_CONTEXT', verb=v, dhat=d, evidence=sh[max(0, m.start() - 30):m.end() + 30],
                    reason='فعل نقلٍ قبل الذات دون تحقق شرطَي الاستبعاد معاً: للمراجعة، لا يُستبعد')
    return None


def describe(row, meas):
    src, rnd = source_of(row), round_of(row)
    d = dict(source=src, round=rnd, measurement=meas.get(rnd) or dict(kind='UNKNOWN_ROUND'), flags=flags(row), requirement_violations=requirements(row),
             contract=CONTRACT)
    if src == 'LISAN':
        d['lisan'] = lisan_madda(row)
        d['mukhassas_fields'] = 'NOT_APPLICABLE_SOURCE_LISAN (فارغة في المورد، ولا تُملأ)'
    mc = meta_citation(row)
    if mc:
        d['meta_citation'] = mc
    return d
