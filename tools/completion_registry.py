#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tools/completion_registry.py — سجل الاستكمال على المراحل العشرين (SARF_SEQUENTIAL_COMPLETION_PLAN_01) من الشيفرة الفعلية.

لكل بندٍ: المتطلّب، والنطاق اللغوي، والقاعدة، ومسار التنفيذ ورمزه، والمستهلكون الفعليون، والاعتمادات، والاختبارات الموجبة
والمقابلة والإفسادية، والقياس، والحالة وسبب ما بقي. والحالة تُستنتج من الشيفرة لا تُكتب باليد:
  الرمز غير موجود ← غير منفّذ؛ موجودٌ بلا مستدعٍ ← منفّذ ولا يُستدعى؛ مستدعى ولا يرد مخرجه في مستهلك ← ناتجه لا يصل؛
  والإعلان اليدوي (جزئي، مؤجَّل لمورد أو دليل، حكم المالك، غير منفّذ) يُحفظ مع سببه؛ وما سوى ذلك ← منفّذ ومختبر ويصل
  إن وُجدت اختباراته في ملفاتها، وإلا منفّذ غير مختبر.

    python3 tools/completion_registry.py [--json coverage/completion_registry.jsonl] [--csv coverage/completion_registry.csv]
"""
import argparse, csv, importlib, json, os, re, subprocess, sys

H = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, H)

STAGES = {1: 'المصدر', 2: 'التطبيع', 3: 'الخلايا', 4: 'المقاطع', 5: 'التقشير', 6: 'الحماية', 7: 'الصنف', 8: 'الجذر والوزن',
          9: 'السمات', 10: 'المعجم', 11: 'العوامل', 12: 'الإعراب', 13: 'الإسناد', 14: 'العلاقات', 15: 'التعلّق', 16: 'الجملة',
          17: 'الدلالة', 18: 'المرجع والخطاب', 19: 'الفقرة', 20: 'القياس والتقرير'}

# (id, stage, scope, rule, symbols, consumers, tests, counter, mutations, measurement, declared, residual)
# symbols: «module:attr»؛ consumers: «ملف::نص يدلّ على استهلاك المخرج»؛ tests: «ملف::معرّف»
SPEC = [
    ('C01.1', 1, 'المصدر المعتمد وروايته وبصمته', 'quran_source', ['sarf.quran_source:rows', 'sarf.quran_source:name'],
     ['tools/pipeline_trace.py::quran_source', 'tools/measure_axes.py::quran_source'], ['tests/test_quran_source.py::'], [], [],
     'بصمة المدخل في هوية التشغيل', None, ''),
    ('C01.2', 1, 'هوية التشغيل وبصمات الشيفرة والمعجم والمصادر', 'provenance', ['tools.provenance:identity'],
     ['tools/pipeline_trace.py::provenance'], ['tests/test_behaviour.py::هوية التشغيل'], [], [], 'رأس كل تقرير', None, ''),
    ('C02.1', 2, 'التطبيع الموثّق بسجل العمليات ومجالاتها', 'N3.1', ['sarf.normalize_trace:normalize_traced'],
     ['tools/pipeline_trace.py::normalize_trace'], ['tests/test_normalize_trace.py::'], [], [], 'الأمثلة والمصحف', None, ''),
    ('C02.2', 2, 'استرجاع المصدر من التمثيل التحليلي', 'N3.1', ['sarf.normalize_trace:reconstruct_source',
                                                              'sarf.normalize_trace:verify_reconstructed_source'],
     ['sarf/normalize_trace.py::verify_reconstructed_source'], ['tests/test_normalize_trace.py::'], [], [], 'اختبار الاسترجاع', None, ''),
    ('C02.3', 2, 'الخنجرية مع المقصورة (تُحذف وحدها)', 'T25', ['sarf.normalize:uthmani_normalize'],
     ['sarf/pipeline.py::uthmani_normalize'], ['tests/test_relations.py::T25'], ['tests/test_relations.py::T25'], [], 'شاهد T25', None, ''),
    ('C03.1', 3, 'خلايا المكتوب وترقيمها', 'numbering', ['sarf.numbering:cell_code', 'sarf.numbering:encode'],
     ['tools/pipeline_trace.py::numbering'], ['tests/test_numbering.py::'], [], [], 'القسم ٣', None, ''),
    ('C03.2', 3, 'خلايا الجبر (Cell) والشدة والتنوين بلا نون مكتوبة', 'cells', ['sarf.cells:cells_of'],
     ['sarf/root.py::cells'], ['tests/test_cell_rules.py::'], [], [], 'الأمثلة', None, ''),
    ('C04.1', 4, 'المقاطع المرخّصة الستة من الخلايا', 'syllables', ['sarf.syllables:syllabify', 'sarf.syllables:cell_shape'],
     ['sarf/segment.py::syllab'], ['tests/test_syllables.py::'], [], [], 'القسم ٤ و١٠', None, ''),
    ('C04.2', 4, 'خريطة المصدر ← الخلايا ← المقاطع واسترجاعها', 'align', ['sarf.align:align', 'sarf.align:syllables_by_word'],
     ['tools/pipeline_trace.py::align'], ['tests/test_syllables.py::'], [], [], 'القسم ٤ (عمود الفرق)', 'partial',
     'لا يُثبت فحصٌ مستقل استرجاع الخلايا من المقاطع في المصحف كله (يُقاس في الدفعة A)'),
    ('C05.1', 5, 'التقشير المرخّص: السوابق والجذوع واللواحق', 'R10', ['sarf.segment:segment', 'sarf.evidence:reject_candidates'],
     ['sarf/pipeline.py::segment('], ['tests/test_segment.py::'], [], [], 'مقابل QAC (HANDOFF)', None, ''),
    ('C06.1', 6, 'الحماية الدستورية قبل الجذر', 'protected', ['sarf.protected:protected', 'sarf.protected:protected_slot'],
     ['sarf/root.py::protected'], ['tests/test_protected.py::'], [], [], 'tools/eval_protected.py', None, ''),
    ('C06.2', 6, 'الحماية لا تمنع التحليل النحوي', 'X01', ['sarf.relations:verse_relations'],
     ['tools/pipeline_trace.py::protection'], ['tests/test_round006.py::X01'], ['tests/test_round006.py::X04'], [], '2:282', None, ''),
    ('C07.3', 7, 'الاسمية بنفي صيغ الفعل المكتوبة (E02 قبل الضمير، E03 الهمزة المكسورة)', 'E02/E03',
     ['sarf.features:host_case_vowel_proof', 'sarf.features:initial_hamza_kasra_proof'], ['sarf/features.py::host_case_vowel_proof('],
     ['tests/test_batch_b.py::B01', 'tests/test_batch_b.py::B04'], ['tests/test_batch_b.py::B02'], [], 'E02: 949 اسماً عند QAC، E03: 91', None, ''),
    ('C07.1', 7, 'الصنف (اسم، فعل، حرف) مستقلاً عن البناء والعمل والحماية', 'axes', ['sarf.relations:_Tok'],
     ['tools/pipeline_trace.py::word_class'], ['tests/test_round006.py::X48'], ['tests/test_relations.py::T19'], [], 'M1', None, ''),
    ('C07.2', 7, 'الصنف من التنوين وحده لا يُثبت (T19)', 'T19', ['sarf.relations:_Tok'],
     ['tools/pipeline_trace.py::T19'], ['tests/test_relations.py::T19'], ['tests/test_round006.py::X13'], [], 'M1', None, ''),
    ('C08.1', 8, 'الجذر والوزن بشهادة HFN، والترجيح لا الإثبات', 'T19c', ['sarf.root:morph', 'sarf.root:candidates'],
     ['sarf/pipeline.py::verse_morph'], ['tests/test_root.py::'], [], [], 'مقابل QAC (HANDOFF)', None, ''),
    ('C08.2', 8, 'خريطة الجذر والوزن إلى الخلايا والمقاطع', 'algebra', ['sarf.algebra:align_radicals', 'sarf.algebra:realize_skeleton'],
     ['tools/pipeline_trace.py::realiz'], ['tests/test_algebra.py::'], [], [], 'القسم ١٢', None, ''),
    ('C08.3', 8, 'التحقيق الصرفي لكل بديلٍ زمني وبنائي (لا قائمة عامة)', 'F02/F03', ['sarf.relations:_voice_faces', 'sarf.features:tense_realization'],
     ['sarf/relations.py::_voice_faces(', 'sarf/features.py::tense_realization('], ['tests/test_batch_b.py::B05', 'tests/test_round006.py::X51'],
     ['tests/test_batch_b.py::B06', 'tests/test_round006.py::X50'], ['tests/test_round006.py::M16'],
     'F03: 1718 زمناً مثبتاً توافق QAC كلها', 'partial', 'F03 يمتنع في المعتلّ والمضعّف والمهموز الأول وحرف المضارعة المكرَّر وتاء تفعّل وتفاعل'),
    ('C09.1', 9, 'سمات الاسم (الاشتقاق، العدد، التعريف، الإعراب الممكن)', 'features', ['sarf.features:noun_features'],
     ['sarf/relations.py::feats'], ['tests/test_features.py::'], [], [], 'المرحلة ١٣', None, ''),
    ('C09.2', 9, 'سمات الفعل (الزمن، البناء، ضمير الصيغة، التعدّي)', 'features', ['sarf.features:verb_features'],
     ['sarf/relations.py::feats'], ['tests/test_features.py::'], [], [], 'المرحلة ١٣', None, ''),
    ('C09.3', 9, 'الضمائر المتصلة والمنفصلة ومضيفها', 'features_ext', ['sarf.features_ext:enclitic_case'],
     ['sarf/relations.py::enclitic_case'], ['tests/test_round006.py::X07'], [], [], 'M3', None, ''),
    ('C10.1', 10, 'مطابقة المدخل المعجمي مفصولةً عن المعنى السياقي', 'HFN', ['sarf.root:hfn'],
     ['tools/pipeline_trace.py::HFN'], ['tests/test_root.py::'], [], [], 'المدلول في المرحلة ١٣', 'partial',
     'تعيين المعنى بالسياق غير منفّذ (الدفعة G)'),
    ('C10.2', 10, 'أطر الاستعمال: اللزوم والتعدّي والمكمّلات والحذف المرخّص', 'F01', ['sarf.relations:verse_relations'],
     ['tools/pipeline_trace.py::object_requirement'], ['tests/test_round006.py::X59', 'tests/test_batch_b.py::B08'], ['tests/test_round006.py::X53'], [],
     'توزيع كاشف المكمّل', 'owner', 'التعدّي لا يثبت إلا بضمير مفعولٍ متصل، فـO02 لا يُبلغ (D5)؛ والحذف المرخّص بلا قاعدة'),
    ('C11.1', 11, 'العوامل المائة: المطابقة والنفي والحكم', 'judge', ['sarf.judge:judge', 'sarf.evidence:reject_candidates'],
     ['sarf/pipeline.py::judge('], ['tests/test_mood.py::'], ['tests/test_round006.py::X18'], [], 'tools/audit_judgments.py', None, ''),
    ('C11.2', 11, 'قدرة العامل المعجمية مفصولةً عن استعماله', 'usage', ['sarf.relations:_usage_capacity'],
     ['sarf/relations.py::_usage_capacity('], ['tests/test_round006.py::X09'], [], ['tests/test_round006.py::M03'], 'M3', None, ''),
    ('C12.1', 12, 'سلسلة الإعراب: الصنف ← البناء ← العامل ← الحالة ← العلامة ← السبب ← العبارة', 'inflection',
     ['sarf.relations:_inflection', 'sarf.relations:check_inflection'], ['tools/eval_inflection.py::inflection'],
     ['tests/test_inflection.py::'], ['tests/test_round006.py::X20'], ['tests/test_round006.py::M08'], 'eval_inflection', None, ''),
    ('C12.2', 12, 'الجزم بالحذف وموانعه (M01)', 'M01', ['sarf.evidence:jazm_faces'], ['sarf/segment.py::jazm_faces'],
     ['tests/test_round006.py::X16'], ['tests/test_round006.py::X18'], [], 'المرحلة ٧', None, ''),
    ('C13.1', 13, 'الفاعل الظاهر والمتصل والمستتر', 'S01', ['sarf.relations:verse_relations'], ['tools/pipeline_trace.py::verse_relations', 'tools/measure_axes.py::verse_relations'],
     ['tests/test_round006.py::X23', 'tests/test_batch_b.py::B07'], ['tests/test_round006.py::X22', 'tests/test_batch_b.py::B12'], [], 'M4',
     'owner', '«وليّه» مرخَّص (E02 ثم S01)؛ و«الذي» و«إحداهما» والمرفوع الملاصق تحتاج حكم المالك (D1، D2، D6)'),
    ('C13.2', 13, 'نائب الفاعل والبناء بأوجهه', 'F02', ['sarf.relations:_voice_faces'], ['tools/pipeline_trace.py::voice'],
     ['tests/test_round006.py::X50'], ['tests/test_round006.py::X60'], ['tests/test_round006.py::M18'], 'M4', None, ''),
    ('C13.3', 13, 'المفعول الظاهر والمتصل (O01/O02)', 'O01/O02', ['sarf.relations:verse_relations'], ['tools/pipeline_trace.py::verse_relations', 'tools/measure_axes.py::verse_relations'],
     ['tests/test_round006.py::X08'], ['tests/test_round006.py::X24'], [], 'M5', 'partial', 'O02 للمعرفة المنصوبة بعد متعدٍّ مثبت فقط'),
    ('C13.4', 13, 'المبتدأ والخبر (N01/N02)', 'N01/N02', ['sarf.relations:verse_relations'], ['tools/pipeline_trace.py::verse_relations', 'tools/measure_axes.py::verse_relations'],
     ['tests/test_relations.py::T02'], ['tests/test_relations.py::T15'], [], 'M6', None, ''),
    ('C13.5', 13, 'اسم الناسخ وخبره (V01) والتامّ والناقص', 'V01', ['sarf.relations:verse_relations'], ['tools/pipeline_trace.py::verse_relations', 'tools/measure_axes.py::verse_relations'],
     ['tests/test_round006.py::X41'], ['tests/test_round006.py::X30'], [], 'M6', 'partial', 'حسم «يكونا» تامّاً أو ناقصاً (B2.09)'),
    ('C14.1', 14, 'الإضافة (I01/I03)', 'I01/I03', ['sarf.relations:verse_relations'], ['tools/pipeline_trace.py::verse_relations', 'tools/measure_axes.py::verse_relations'],
     ['tests/test_round006.py::X12'], ['tests/test_round006.py::X34'], ['tests/test_round006.py::M06'], 'M5', None, ''),
    ('C14.2', 14, 'الصلة والعائد (R01/R02) بأوجهها', 'R01/R02', ['sarf.relations:verse_relations'], ['tools/pipeline_trace.py::verse_relations', 'tools/measure_axes.py::verse_relations'],
     ['tests/test_round006.py::X44'], ['tests/test_round006.py::X49'], ['tests/test_round006.py::M13'], 'M5', 'partial',
     'بنية الوجه المنافس (المتعلَّق وفاعله) غير مبنية'),
    ('C14.3', 14, 'المصدر المؤوَّل ومحلّه', 'M02', ['sarf.relations:verse_relations'], ['sarf/algebra.py::MASDAR'],
     ['tests/test_batch_e.py::E04', 'tests/test_batch_e.py::E07'], ['tests/test_batch_e.py::E09'], ['tests/test_batch_e.py::E08'], 'M5',
     'partial', 'من «أَنْ» الناصبة وحدها؛ و«أَنَّ» و«ما» المصدرية و«كي» و«لو» غير منفّذة؛ والوظيفة مؤجَّلة إلا بحرف جرٍّ قبله'),
    ('C14.4', 14, 'الشرط وفعله وجوابه وملكيته (C01)', 'C01', ['sarf.relations:verse_relations'], ['tools/pipeline_trace.py::verse_relations', 'tools/measure_axes.py::verse_relations'],
     ['tests/test_round006.py::X26'], ['tests/test_round006.py::X27'], [], 'M5', None, ''),
    ('C14.5', 14, 'العطف داخل المفردات والتراكيب والجمل', 'coord', ['sarf.coord:check_coord'], ['sarf/algebra.py::coord'],
     ['tests/test_coord.py::'], [], [], 'الطبقة القديمة', 'partial',
     'لا يصل العطف إلى سجلات 14أ (غير مجسور)؛ والعاطف المستقل يحدّ بحث الفاعل (الدفعة B)'),
    ('C14.6', 14, 'النعت والحال والتوكيد والبدل وعطف البيان والتمييز', 'TAWABI', [], [], [], [], [], '', 'unimplemented',
     'لا قاعدة موجبة'),
    ('C14.7', 14, 'النداء (V02) والاستثناء والعدد والقسم', 'V02', ['sarf.relations:verse_relations'], ['tools/pipeline_trace.py::verse_relations', 'tools/measure_axes.py::verse_relations'],
     ['tests/test_round006.py::X05'], ['tests/test_round006.py::X04'], [], 'M5', 'partial', 'الاستثناء والعدد والقسم غير منفّذة'),
    ('C15.1', 15, 'تعلّق الجار والمجرور والظرف (A01/A02)', 'A01/A02', ['sarf.relations:verse_relations'], ['tools/pipeline_trace.py::verse_relations', 'tools/measure_axes.py::verse_relations'],
     ['tests/test_relations.py::T34', 'tests/test_batch_e.py::E01'], ['tests/test_relations.py::T14'], ['tests/test_batch_e.py::E03'], 'M5',
     'partial', 'A02 وجهٌ مرخَّص غير مختار؛ وجرد أطر التعلّق غير موجود، فـA01 مؤجَّل في عامّة المواضع'),
    ('C16.1', 16, 'الجملة: النوى والالتزامات وشهادة الإغلاق الموحَّدة', 'F-CERT', ['sarf.algebra:sentence_geo', 'sarf.algebra:closure_certificate'],
     ['tools/pipeline_trace.py::closure_certificate', 'tools/measure_coverage.py::closure_certificate'],
     ['tests/test_batch_f.py::F01', 'tests/test_batch_f.py::F03'], ['tests/test_batch_f.py::F02', 'tests/test_batch_f.py::F05'],
     ['tests/test_batch_f.py::F06'], 'M7 unified', 'partial',
     'الشهادة تمرّ بعد الطبقتين ولا تعيد بناء الجملة؛ والإضافة والصلة والشرط والنداء والتعلّق تُستهلك عامّاً لا استيفاءً'),
    ('C16.2', 16, 'نطاق شهادة الإغلاق', 'M7', ['tools.measure_coverage:main'], ['tools/pipeline_trace.py::scope_'],
     ['tests/test_round006.py::X52'], [], [], 'closed_unreconciled', None, ''),
    ('C17.1', 17, 'الدال وتمثيله والمدلولات المعجمية المرشّحة', 'HFN', ['sarf.features:unit_features'], ['tools/pipeline_trace.py::المدلول'],
     ['tests/test_features_ext.py::'], [], [], 'المرحلة ١٣', 'deferred',
     'تعيين المعنى بالسياق ودلالات المطابقة والتضمن والالتزام: لا مورد مقرّ (مداخل HFN is_fact=False) ولا قاعدة'),
    ('C18.1', 18, 'مرجع الضمير والمطابقة معه', 'REF', [], [], [], [], [], '', 'deferred',
     'لا قاعدة مكتوبة لتعيين المرجع؛ والمطابقة وحدها ترشّح ولا تثبت، والمعنى ليس دليلاً في المشروع'),
    ('C18.2', 18, 'الوحدة الخطابية والعلاقات بين الجمل', 'algebra', ['sarf.algebra:sentence_geo'], ['tools/pipeline_trace.py::الوحدة الخطابية'],
     ['tests/test_algebra.py::'], [], [], 'القسم ١٥', 'partial', 'العلاقات بين الجمل واستمرار الموضوع غير منفّذة'),
    ('C19.1', 19, 'هندسة الفقرة وحدّها', 'PARA', [], [], [], [], [], '', 'deferred',
     'لا قاعدة مكتوبة لحدّ الفقرة، ولا يُخترع حدٌّ (الخطة §4 G)؛ والوحدة الخطابية من الطبقة القديمة أعلى ما يُبنى'),
    ('C20.1', 20, 'القياس بالمسار نفسه للصفحة (الجسران)', 'bridged', ['tools.bridged:surah_outputs'],
     ['tools/eval_inflection.py::bridged', 'tools/compare_relations.py::bridged', 'tools/measure_axes.py::linguistic_layer'],
     [], [], [], 'المصحف كله', None, ''),
]


# المستهلك اللغوي اللاحق لعلاقات 14أ: طبقة الجملة (sarf/algebra.py وsarf/checker.py). العرض والقياس مستهلكان للعرض لا للتحليل.
SENTENCE_TYPE = {'C13.1': 'SUBJECT', 'C13.2': 'SUBJECT', 'C13.3': 'OBJECT', 'C13.4': 'PREDICATION', 'C13.5': 'NASIKH',
                 'C14.1': 'IDAFA', 'C14.2': 'SILAH', 'C14.3': 'MASDAR', 'C14.4': 'CONDITION', 'C14.7': 'VOCATIVE', 'C15.1': 'ATTACH'}


def _sentence_consumes(t):
    """→ 'named' إن سمّت طبقة الجملة النوعَ في استيفاء التزامٍ (sarf.algebra.OBLIGATION_RELATION أو نواة الشهادة)،
    و'generic' إن استهلكته شهادة الإغلاق الموحَّدة عامّاً (المفتوح منه التزامٌ مفتوح) بلا استيفاء، وFalse إن لم تستهلكه"""
    src = open(os.path.join(H, 'sarf', 'algebra.py'), encoding='utf-8').read()
    if 'def closure_certificate' not in src:
        return False
    cert = src[src.index('def closure_certificate'):]
    head = src[src.index('OBLIGATION_RELATION'):src.index('def closure_certificate')] if 'OBLIGATION_RELATION' in src else ''
    if re.search(rf"['\"]{t}['\"]", head + cert):
        return 'named'
    return 'generic'


def _exists(sym):
    mod, attr = sym.split(':')
    try:
        m = importlib.import_module(mod)
    except Exception:
        return False
    return hasattr(m, attr)


def _callers(sym):
    attr = sym.split(':')[1]
    try:
        out = subprocess.run(['grep', '-rn', '--include=*.py', f'{attr}', 'sarf', 'tools', 'pipeline.py'], cwd=H, capture_output=True,
                             text=True).stdout.splitlines()
    except Exception:
        return 0
    return sum(1 for l in out if not re.search(rf'(def|class)\s+{re.escape(attr)}\b', l) and 'completion_registry.py' not in l)


def _has(ref):
    f, key = ref.split('::', 1)
    p = os.path.join(H, f)
    if not os.path.exists(p):
        return False
    return key in open(p, encoding='utf-8').read() if key else True


def build():
    rows = []
    for (rid, st, scope, rule, syms, cons, tests, counter, muts, meas, declared, residual) in SPEC:
        ex = {s: _exists(s) for s in syms}
        calls = {s: _callers(s) for s in syms}
        cons_ok = {c: _has(c) for c in cons}
        tests_ok = {t: _has(t) for t in tests + counter + muts}
        sent = _sentence_consumes(SENTENCE_TYPE[rid]) if rid in SENTENCE_TYPE else None
        if sent is False:
            residual = (residual + '؛ ' if residual else '') + f'لا تستهلك طبقةُ الجملة علاقة {SENTENCE_TYPE[rid]} (الدفعة F)'
        elif sent == 'generic':
            residual = (residual + '؛ ' if residual else '') + \
                f'تستهلك شهادة الإغلاق الموحَّدة {SENTENCE_TYPE[rid]} عامّاً (المؤجَّل منها مفتوح)، ولا تستوفي بها التزاماً مسمّى'
            declared = declared or 'partial'
        if declared == 'unimplemented' or (syms and not all(ex.values())):
            status = 'غير منفّذ'
        elif syms and not all(calls.values()):
            status = 'منفّذ ولا يُستدعى'
        elif (cons and not any(cons_ok.values())) or sent is False:
            status = 'ناتجه لا يصل إلى المستهلك'
        elif declared == 'partial':
            status = 'منفّذ جزئياً'
        elif declared == 'deferred':
            status = 'مؤجَّل لنقص موردٍ أو دليل'
        elif declared == 'owner':
            status = 'مسألة تحتاج حكم المالك'
        elif tests and all(tests_ok.get(t) for t in tests):
            status = 'منفّذ ومختبر ويصل إلى المستهلك'
        else:
            status = 'منفّذ غير مختبر'
        rows.append(dict(requirement_id=rid, stage=st, stage_name=STAGES[st], linguistic_scope=scope, rule_id=rule,
                         implementation=syms, symbol_exists=ex, callers=calls, actual_consumers=cons, consumers_found=cons_ok,
                         positive_tests=tests, counterexamples=counter, mutation_tests=muts, tests_found=tests_ok,
                         measurement=meas, sentence_layer_consumes=sent, status=status, residual_reason=residual))
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--json', default=os.path.join(H, 'coverage', 'completion_registry.jsonl'))
    ap.add_argument('--csv', default=os.path.join(H, 'coverage', 'completion_registry.csv'))
    a = ap.parse_args()
    rows = build()
    with open(a.json, 'w', encoding='utf-8') as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + '\n')
    with open(a.csv, 'w', encoding='utf-8', newline='') as f:
        w = csv.writer(f)
        w.writerow(['requirement_id', 'stage', 'stage_name', 'linguistic_scope', 'rule_id', 'implementation', 'actual_consumers',
                    'positive_tests', 'counterexamples', 'mutation_tests', 'measurement', 'status', 'residual_reason'])
        for r in rows:
            w.writerow([r['requirement_id'], r['stage'], r['stage_name'], r['linguistic_scope'], r['rule_id'], ' '.join(r['implementation']),
                        ' '.join(r['actual_consumers']), ' '.join(r['positive_tests']), ' '.join(r['counterexamples']),
                        ' '.join(r['mutation_tests']), r['measurement'], r['status'], r['residual_reason']])
    import collections
    print(dict(collections.Counter(r['status'] for r in rows)))
    for r in rows:
        bad = [k for k, v in {**r['symbol_exists'], **r['consumers_found'], **r['tests_found']}.items() if not v]
        if bad:
            print(' ', r['requirement_id'], 'missing:', bad)


if __name__ == '__main__':
    main()
