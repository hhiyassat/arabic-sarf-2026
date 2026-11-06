"""tests/test_upstream.py — اختبارات القبول لدفعة الإضافة (SARF_UPSTREAM_CONSUMPTION_ADDENDUM_01 §8).

تحتاج المسارات الصريحة SARF_UP_AMLN وSARF_UP_WAZN وSARF_UP_HFN وSARF_UP_MAQ. وإن غابت لا تنجح صامتةً:
تطبع NOT_RUN بسببها وتخرج بالرمز 2.
"""
import copy, json, os, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, 'tools', 'upstream'))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
sys.path.insert(0, os.path.join(ROOT, 'tests'))
os.chdir(ROOT)
FAIL = []


def check(name, cond, got=''):
    print(('PASS ' if cond else 'FAIL ') + name + ('' if cond else f' — {got}'))
    if not cond:
        FAIL.append(name)


import client
try:
    P = client.paths()
except client.UpstreamError as e:
    print('NOT_RUN: ' + str(e))
    sys.exit(2)
from worker import match_status
import upstream_candidates as UC

# ١ لفظان متطابقان حروفاً مختلفان تشكيلاً
check('U01 حروفٌ واحدة وتشكيلٌ مختلف (حَزِنَ / حَزُنَ): VOCALIZATION_MISMATCH، لا مطابقة',
      match_status('حَزِنَ', 'حَزُنَ')[0] == 'VOCALIZATION_MISMATCH')
# ٢ اختلاف الشدّة
check('U02 اختلاف الشدّة (ذَكَّرَ / ذَكِرَ، عَلَّمَ / عَلِمَ): لا مطابقة', match_status('ذَكَّرَ', 'ذَكِرَ')[0] == 'VOCALIZATION_MISMATCH' and
      match_status('عَلَّمَ', 'عَلِمَ')[0] == 'VOCALIZATION_MISMATCH')
# ٣ اختلاف السكون وحده: يُحفظ مرشّحاً بموضعه، ولا يُسوّى
st, pos = match_status('انْكَسَرَ', 'انكَسَرَ')
check('U03 اختلاف السكون وحده: SUKUN_ONLY_DIFFERENCE بموضع الفرق، لا تسويةٌ إلى المطابقة التامّة', st == 'SUKUN_ONLY_DIFFERENCE' and pos == 2,
      (st, pos))
check('U03b كرسيّ الهمزة لا يُستبدل: «أَمَرَ» و«ءَمَرَ» ليستا الحروف نفسها', match_status('أَمَرَ', 'ءَمَرَ')[0] == 'LETTERS_DIFFER')

# تشغيلٌ على شواهد: «يَكۡتُبۡ» مصرَّفة، ولمّتها كَتَبَ؛ و«يُذَكِّرَ» (ذَكَّرَ) يقابلها «ذَكِرَ» في جهة الفاعل
OUT = '/tmp/up_test.jsonl.gz'
SUM = '/tmp/up_test.json'
env = dict(os.environ, PYTHONHASHSEED='0')
p = subprocess.run([sys.executable, '-s', 'tools/upstream_candidates.py', OUT, SUM, '--verses', '2:282,3:154', '--jobs', '1'],
                   capture_output=True, text=True, env=env)
check('U00 المستهلك يعمل (رمز الخروج 0)', p.returncode == 0, p.stderr[-400:])
import gzip
rows = [json.loads(l) for l in gzip.open(OUT, 'rt', encoding='utf-8')]
S = json.load(open(SUM, encoding='utf-8'))
yk = [r for r in rows if r['text'] == 'يَكْتُبْ']
f_ = [x for r in yk for x in r['upstream_candidates']['features']]
check('U04 لمّةٌ صحيحة لكلمةٍ مصرَّفة: «يَكۡتُبۡ» ← المرشّح ← كَتَبَ، والسمة مرفقةٌ بالمرشّح بمعرّفه، لا بمقارنة الكلمة المصرّفة',
      yk and all(r['lemma_status'] == 'LEMMA_ESTABLISHED' and r['morph_candidate_id'] for r in yk) and
      f_ and all(x['vocalized_lemma'] == 'كَتَبَ' and x['match_status'] == 'EXACT_VOCALIZED_MATCH' for x in f_), f_[:1])
REQ = ('provider', 'repository_commit_or_dataset_version', 'file_hash', 'row_or_entry_id', 'route_id', 'vocalized_lemma', 'root',
       'pattern_or_form', 'source_reference', 'measurement_id', 'route_status', 'owner_status', 'match_status', 'consumer_scope')
allf = [x for r in rows for x in r['upstream_candidates']['features']]
check('U05 كل سمةٍ مرفقة تحمل الحقول الأربعة عشر، ورتبتها مرشّحةٌ تنتظر المالك، ومسلكها مقبولٌ بقياسٍ مسمّى',
      allf and all(all(k in x for k in REQ) and x['owner_status'] == 'CANDIDATE_PENDING_OWNER' and x['route_status'] == 'ACCEPTED_ROUTE'
                   and x['measurement_id'] for x in allf), [x for x in allf if any(k not in x for k in REQ)][:1])
dz = [x for r in rows for x in r['upstream_candidates']['excluded'] if x['vocalized_lemma'] == 'ذَكَّرَ' and x['route_id'] == 'J_DAA']
check('U06 «ذَكَّرَ» لا تُقرن بـ«ذَكِرَ» (J_DAA) وإن اشتركتا حروفاً: مستبعدةٌ بسببها', dz and all(x['match_status'] == 'VOCALIZATION_MISMATCH'
                                                                                         for x in dz), dz[:1])
pk = [r for r in rows if r['text'] in ('يَكُونَا', 'تَكُونَ', 'لَيْسَ', 'كَانَ')]
check('U15 البوابة الدستورية أولاً: «يَكُونَا» و«تَكُونَ» و«لَيْسَ» لا تُسأل عنها الموارد، ولا سمة ولا معنى جذرٍ لها',
      pk and all(r['lemma_status'] == 'PROTECTED_NOT_QUERIED' and not r['upstream_candidates']['features'] and
                 not r['upstream_candidates']['excluded'] and r['upstream_candidates']['root_meaning'] is None for r in pk),
      [(r['text'], r['lemma_status']) for r in pk])
# ٥ نتيجتان من حدثين مختلفين: كل صفٍّ بحدثه ومطابقته، ولا دمج
W = client.call([dict(lemma='عَلِمَ')], [], P)['lemma']['عَلِمَ']
tw = W['transitivity_wasit']
check('U07 نتيجتان من حدثين مختلفين للحروف نفسها (عَلِمَ، عَلُمَ…): لكلٍّ صفّه ومعرّف حدثه ومطابقته، ولا تُجمع في تحليلٍ واحد',
      len({x['event_id'] for x in tw}) >= 2 and {x['match'] for x in tw} >= {'EXACT_VOCALIZED_MATCH', 'VOCALIZATION_MISMATCH'},
      [(x['verb'], x['event_id'], x['match']) for x in tw])
# ٦ صفٌّ من مسلكٍ محجوب
blk = [x for r in rows for x in r['upstream_candidates']['excluded'] if x['route_status'].startswith('BLOCKED')]
check('U08 صفٌّ من مسلكٍ محجوب («مشترك» في تعدّي الوسيط، الأصل غير المحسوم): مستبعدٌ بسببه، ولا يُرفق',
      blk and not any(x['route_status'].startswith('BLOCKED') for x in allf), len(blk))
check('U08b المسالك المحجوبة (T، T_TAD، R2، J_LAWN، J_MUTAWAA) لا تظهر في المرفق ولا في المستبعد: لا تُقرأ أصلاً',
      not {x['route_id'] for x in allf + [y for r in rows for y in r['upstream_candidates']['excluded']]} & {'T', 'T_TAD', 'R2', 'J_LAWN', 'J_MUTAWAA'})
# ٧ جذرٌ جُمعت حروفه بلا ترتيب: لا يُسترجع به جذرٌ آخر
R = client.call([], ['كسر', 'رسك', 'سكر'], P)['root']
check('U09 جذرٌ بحروفٍ مبعثرة (رسك) لا يسترجع «كسر» ولا «سكر»: مفتاح الاسترجاع يحفظ الترتيب',
      R['رسك']['maqayis']['status'] == 'ROOT_NOT_IN_MAQAYIS' and R['كسر']['maqayis']['records'] and
      all(x['display'] != 'كسر' for x in R['سكر']['maqayis']['records']), R['رسك']['maqayis'])
check('U09b لا يُستعمل المسار الاحتياطي في for_root (حروف الجذر في الفعل): العامل لا يستدعيه',
      'for_root' not in open(os.path.join(ROOT, 'tools', 'upstream', 'worker.py'), encoding='utf-8').read().split('def main')[1])
# ٨ مصدر OCR بلا رابطٍ صالح: حالاتٌ مسمّاة منفصلة
lx = R['كسر']['root_meaning']['lexicons']
check('U10 معنى الجذر: غياب ملفّ المعجم (LEXICON_FILE_MISSING) غير غياب السجلّ وغير غياب الجذر من البنك؛ والرتبة مرشّحة',
      R['كسر']['root_meaning'].get('rank') == 'CANDIDATE' and lx and all(x.get('error') in (None, 'LEXICON_FILE_MISSING', 'RECORD_NOT_FOUND') for x in lx)
      and client.call([], ['ققق'], P)['root']['ققق']['root_meaning'].get('error') == 'ROOT_NOT_IN_BANK', [x.get('error') for x in lx][:3])
# ٩ اختلاف المصدر المطلوب عن الفعلي
bad = dict(os.environ, SARF_UP_AMLN='/nonexistent/amln')
q = subprocess.run([sys.executable, '-s', '-c', 'import sys; sys.path.insert(0,"tools/upstream"); import client; client.paths()'],
                   capture_output=True, text=True, env=bad)
q2 = subprocess.run([sys.executable, '-s', '-c', 'from sarf.root import hfn; hfn()'], capture_output=True, text=True,
                    env=dict(os.environ, SARF_HFN='/nonexistent/release_v37'))
check('U11 المسار الصريح غير الموجود يُعلن ولا يُستبدل به غيره (موارد الإضافة، وSARF_HFN)',
      q.returncode != 0 and 'SARF_UP_AMLN' in q.stderr and q2.returncode != 0 and 'لا رجوع صامت' in q2.stderr, (q.stderr[-200:], q2.stderr[-200:]))
check('U11b المصدر الفعلي مسجَّلٌ بالتزامه: الالتزامات المثبّتة في الملحق',
      {k: (S['provenance'][k]['commit'] or '')[:7] for k in S['provenance']} == dict(amln='1cadaa3', wazn='b8a4672', hfn='41dbbeb', maq='6c2c58f'),
      {k: S['provenance'][k]['commit'] for k in S['provenance']})
# ١٠ تصادم أسماء الاستيراد، والكتابة في الموارد
before = set(sys.modules)
r10 = client.call([dict(lemma='كَسَرَ')], ['كسر'], P)
new = set(sys.modules) - before
check('U12 لا تصادم أسماء: استدعاء الموارد لا يحمّل في عملية المحلّل core ولا engines ولا word_tree ولا root_taxonomy',
      not new & {'core', 'engines', 'word_tree', 'root_taxonomy', 'root_meaning', 'hfn_common'} and
      not any(m.startswith(('_up_', 'engines.', 'word_tree.', 'core.')) for m in new), sorted(new)[:10])
check('U13 لا كتابة في الموارد ولا خبيئة ولا قاعدة بيانات (الملفات قبل الاستدعاء وبعده)، ولا ملفّ في مجلد العمل',
      all(not v for v in r10['isolation']['resource_writes'].values()) and not r10['isolation']['cwd_files'], r10['isolation'])
# ١١ استقلال المخرجات القديمة عن الإضافات
from test_closure_helpers import verse_records
a1 = verse_records(2, 282)
client.call([dict(lemma='كَتَبَ')], ['كتب'], P)
a2 = verse_records(2, 282)
check('U14 المخرجات القديمة مستقلةٌ عن الإضافة: سجلات 2:282 قبل استدعاء الموارد وبعده متطابقة', a1 == a2)

print('ALL OK' if not FAIL else f'FAILED {len(FAIL)}: {FAIL}')
sys.exit(1 if FAIL else 0)
