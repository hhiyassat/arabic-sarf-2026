"""tests/test_upstream.py — اختبارات الاستهلاك المرشّح (SARF_UPSTREAM_CONSUMPTION_2026_11_08 §١١)، من المسار العام وبشواهد موجبة ومقابلة،
وإفسادٌ في نسخٍ اختبارية (لا تُمسّ موارد المالك ولا النسخ المثبتة).

تحتاج SARF_UP_PINS وSARF_UP_HFN وSARF_UP_WAZN وSARF_UP_AMLN وSARF_UP_MAQ (وSARF_HFN للأساس). وإن غابت لا تنجح صامتةً:
تطبع NOT_RUN بسببها وتخرج بالرمز 2.
"""
import copy, gzip, json, os, shutil, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, 'tools', 'upstream'))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
sys.path.insert(0, os.path.join(ROOT, 'tests'))
os.chdir(ROOT)
FAIL, MUT = [], []


def check(name, cond, got=''):
    print(('PASS ' if cond else 'FAIL ') + name + ('' if cond else f' — {str(got)[:400]}'))
    if not cond:
        FAIL.append(name)


def mutation(name, detected, got=''):
    print(('CAUGHT ' if detected else 'MISSED ') + name + ('' if detected else f' — {str(got)[:300]}'))
    MUT.append((name, bool(detected)))
    if not detected:
        FAIL.append('MUTATION ' + name)


import client
try:
    PINS = client.load_pins()
    P = client.paths(PINS)
except client.UpstreamError as e:
    print('NOT_RUN: ' + str(e))
    sys.exit(2)
from worker import match_class
import upstream_candidates as UC
TMP = tempfile.mkdtemp(prefix='up_test_')

# ---------- ١ تثبيت الإصدار ومنع التحميل التلقائي أو خلط إصدارين ----------
def sub(code, env):
    return subprocess.run([sys.executable, '-s', '-c', 'import sys; sys.path.insert(0,"tools/upstream"); import client; ' + code],
                          capture_output=True, text=True, env=env)


e0 = {k: v for k, v in os.environ.items() if k != 'SARF_UP_PINS'}
q = sub('client.paths()', e0)
check('T01 غياب ملفّ التثبيت خطأ إعدادٍ مسمّى (PIN_MISSING)، لا تحميل لأحدث إصدار', q.returncode != 0 and 'PIN_MISSING' in q.stderr, q.stderr[-200:])
q = sub('client.paths()', dict(os.environ, SARF_UP_AMLN=''))
check('T01b غياب مسار مصدرٍ خطأ مسمّى (PIN_PATH_MISSING)', q.returncode != 0 and 'PIN_PATH_MISSING' in q.stderr, q.stderr[-200:])
# إفساد هوية الإصدار: نسخةٌ اختبارية من Maqaiys بالتزامٍ آخر
bad_maq = os.path.join(TMP, 'maq_badcommit')
shutil.copytree(P['maq'], bad_maq)
os.chmod(bad_maq, 0o755)
os.chmod(os.path.join(bad_maq, '.pinned_commit'), 0o644)
open(os.path.join(bad_maq, '.pinned_commit'), 'w').write('0' * 40)
q = sub('client.paths()', dict(os.environ, SARF_UP_MAQ=bad_maq))
mutation('M01 هوية الإصدار: نسخة مصدرٍ بالتزامٍ غير المثبت ← PIN_COMMIT_MISMATCH', q.returncode != 0 and 'PIN_COMMIT_MISMATCH' in q.stderr, q.stderr[-200:])
bad_pins = dict(PINS, hfn_manifest_sha256='0' * 64)
bp = os.path.join(TMP, 'pins_bad.json')
json.dump(bad_pins, open(bp, 'w'))
q = sub('client.paths()', dict(os.environ, SARF_UP_PINS=bp))
mutation('M02 هوية الإصدار: بصمة MANIFEST غير المثبتة ← PIN_MANIFEST_MISMATCH', q.returncode != 0 and 'PIN_MANIFEST_MISMATCH' in q.stderr, q.stderr[-200:])
# خلط إصدارين: العامل نفسه بإصدارٍ لطبقات AMLN غير إصدار التثبيت
home = tempfile.mkdtemp(prefix='up_home_mix_')
an = os.path.join(home, 'arabic-net')
os.makedirs(an)
for k, n in (('amln', 'Arabic-Mother-language-net'), ('hfn', 'HusseinFrameNet'), ('wazn', 'Arabic-Mother-language-wazn-net')):
    os.symlink(P[k], os.path.join(an, n))
envw = dict(PATH=os.environ['PATH'], HOME=home, PYTHONHASHSEED='0', PYTHONDONTWRITEBYTECODE='1', ARABIC_NET_HOME=an,
            AMLN_HFN_RELEASE='release_v46', ARABIC_NET_HFN_RELEASE=os.path.join(P['hfn'], 'release', 'release_v46'))
w = subprocess.run([sys.executable, '-I', '-B', client.WORKER], input=json.dumps(dict(paths=P, pins=PINS, lemmas=[dict(lemma='كَسَرَ')], roots=[])),
                   capture_output=True, text=True, env=envw, cwd=tempfile.mkdtemp())
wj = json.loads(w.stdout) if w.returncode == 0 else {}
mutation('M03 خلط إصدارين: طبقات AMLN وواجهتها على release_v46 والتثبيت release_v47 ← CONFIG_ERROR في الطبقة والواجهة',
         str(wj.get('interfaces', {}).get('amln.word_tree.ahdath', {}).get('status', '')).startswith('CONFIG_ERROR') and
         str(wj.get('interfaces', {}).get('amln.arabic_net_api.sources', {}).get('status', '')).startswith('CONFIG_ERROR'),
         (w.stderr[-300:], wj.get('interfaces')))

# ---------- ٢ المطابقة حرفاً وحركة ----------
M = lambda a, b: match_class(a, b)[0]
check('T02a التطابق التام EXACT', M('كَسَرَ', 'كَسَرَ') == 'EXACT')
check('T02b «ٱ/ا» وحده: WASL_ONLY', M('انْكَسَرَ', 'ٱنْكَسَرَ') == 'WASL_ONLY')
check('T02c السكون وحده: SUKUN_ONLY', M('انْكَسَرَ', 'انكَسَرَ') == 'SUKUN_ONLY')
check('T02d الوصل والسكون معاً: WASL_AND_SUKUN (حالةٌ مستقلة، لا إحدى المنفردتين)', M('انْكَسَرَ', 'ٱنكَسَرَ') == 'WASL_AND_SUKUN')
d = match_class('ذَكَّرَ', 'ذَكِرَ')
check('T02e الشدّة لا تُتجاهل: OTHER بنوع SHADDA/HARAKA وموضعه', d[0] == 'OTHER' and any(x['kind'] in ('SHADDA', 'MARKS') for x in d[1]), d)
d = match_class('حَزِنَ', 'حَزُنَ')
check('T02f الحركة لا تُتجاهل: OTHER بنوع HARAKA', d[0] == 'OTHER' and [x['kind'] for x in d[1]] == ['HARAKA'], d)
d = match_class('أَمَرَ', 'ءَمَرَ')
check('T02g كرسيّ الهمزة لا يُستبدل: OTHER بنوع HAMZA', d[0] == 'OTHER' and [x['kind'] for x in d[1]] == ['HAMZA'], d)
check('T02h الوصل مع اختلافٍ آخر (شدّة) ليس WASL_ONLY: OTHER', M('اتَّبَعَ', 'ٱتَبَعَ') == 'OTHER')
_a, _b = 'ض\u064eل\u0651\u064e', 'ض\u064eل\u064e\u0651'          # الشدّة ثم الفتحة، والفتحة ثم الشدّة: متكافئان في Unicode
check('T02i تسوية NFC وحدها (ترتيبان متكافئان للشدّة والفتحة): EXACT، والأصل غير NFC محفوظ',
      _a != _b and M(_a, _b) == 'EXACT' and match_class(_a, 'ض\u064eل\u064e')[0] == 'OTHER')

# ---------- تشغيلٌ من المدخل العام ----------
OUT, SUM = os.path.join(TMP, 'u.jsonl.gz'), os.path.join(TMP, 'u.json')
p = subprocess.run([sys.executable, '-s', 'tools/upstream_candidates.py', OUT, SUM, '--verses', '2:282,3:154', '--jobs', '1'],
                   capture_output=True, text=True, env=dict(os.environ, PYTHONHASHSEED='0'))
check('T00 المستهلك العام يعمل (رمز الخروج 0)', p.returncode == 0, p.stderr[-500:])
rows = [json.loads(l) for l in gzip.open(OUT, 'rt', encoding='utf-8')]
S = json.load(open(SUM, encoding='utf-8'))
allrows = [x for r in rows for x in r['upstream_candidates']['rows']]
check('T03 السجلّ يحمل التزامات المصادر الأربعة المثبتة وإصدار HFN وبصمة MANIFEST وما حمّلته كل واجهة',
      {k: S['provenance'][k]['commit'] for k in ('hfn', 'wazn', 'amln', 'maq')} == PINS['commits'] and
      S['provenance']['hfn_release']['requested'] == 'release_v47' and S['interfaces']['wazn.mutawaa_engine'].get('table_loaded') == 'data/mutawaa_v7.tsv'
      and S['api_sources']['hfn']['pinned_by'] == 'ARABIC_NET_HFN_RELEASE' and S['interfaces']['amln.arabic_net_api.sources']['status'] == 'OK'
      and S['interfaces']['hfn.root_meaning']['bank'] == 'HFN_ROOTS_v11.csv', (S['provenance'], S['interfaces']))

# ---------- ٣ المسالك المحجوبة ----------
check('T04 لا صفّ من R2 أو R2w أو T أو T_TAD أو J_LAWN أو J_MUTAWAA في الناتج', not {x.get('route_id') for x in allrows} & {'R2', 'R2w', 'T', 'T_TAD', 'J_LAWN', 'J_MUTAWAA'})
fr0 = dict(verse='0:0', word_index=0, unit='U', relation_id='R', text='x', morph_candidate_id='C', analysis_id='A', root='كسر', pattern='I',
           hfn_events=[dict(event_id='E1', verb='كَسَرَ')], analysis_selection='SELECTED', protected=None, hfn_base_release='release_v36')
res0 = dict(provenance={k: dict(commit='c' * 40) for k in ('hfn', 'wazn', 'amln', 'maq')}, resources={})
NO = dict(status='QUERY_OK_NO_RESULT')
W0 = dict(hfn47=NO, mutawaa=NO, mutawaa_base=NO, taadiya_T_JAL=NO, transitivity_wasit_v5=NO, sifat_v2=NO, jiha=NO,
          ahdath=dict(status='OK', rows=[dict(route='R2', verb='كَسَرَ', row_verb='كَسَرَ', event_id='E1', match='EXACT', diff=[])]))
r_ = [x for x in UC.feature_rows(fr0, 'كَسَرَ', W0, res0, PINS) if x.get('route_id') == 'R2']
mutation('M04 المسلك: صفٌّ من R2 يُحقن في جواب AMLN ← ROUTE_BLOCKED بسببه، ولا دليل منه', r_ and r_[0]['state'] == 'ROUTE_BLOCKED' and
         r_[0]['block_reason'] == UC.BLOCKED[('AMLN', 'R2')] and not UC.evidence_records(fr0, r_, None, res0['provenance']), r_)
W1 = dict(W0, ahdath=NO, transitivity_wasit_v5=dict(status='OK', rows=[dict(event_id='E2', verb='كَسَّرَ', form='فَعَّلَ', transitivity_wasit='متعدي', harf='',
                                                                             basis_v5='V1', transitivity_v1='متعدي', harf_v1='', hfn_transitivity='متعدي',
                                                                             match='EXACT', diff=[])]))
r_ = [x for x in UC.feature_rows(fr0, 'كَسَّرَ', W1, res0, PINS) if x.get('source_key') == 'transitivity_wasit_v5']
check('T05 تعدّي المزيد من الوسيط محجوب: ROUTE_BLOCKED بسببه', r_ and r_[0]['state'] == 'ROUTE_BLOCKED' and 'المزيد' in r_[0]['block_reason'], r_)
check('T05b حكم الأين مسجّلٌ بسنده ونطاقه، ولا يرفع حجب R2', UC.OWNER_RULINGS[0]['sanad'].startswith('المناوي') and 'R2' in UC.OWNER_RULINGS[0]['scope'])

# ---------- ٤ الحدث المسحوب ----------
Rw = client.call([dict(lemma='بَهْمَنَ'), dict(lemma='كَسَرَ')], [], P, PINS)
wd = [x for x in Rw['lemma']['بَهْمَنَ']['hfn47'].get('rows', []) if x['withdrawn']]
fr1 = dict(fr0, root='بهمن', pattern='QI', hfn_events=[dict(event_id='Z', verb='بَهْمَنَ')])
rw_ = [x for x in UC.feature_rows(fr1, 'بَهْمَنَ', Rw['lemma']['بَهْمَنَ'], Rw, PINS) if x.get('source_key') == 'hfn47']
check('T06 الحدث المسحوب (بَهْمَنَ، WITHDRAWN_v43) يُعلَّم WITHDRAWN_RECORD بسببه ومرجعه، ولا دليل منه',
      wd and rw_ and all(x['state'] == 'WITHDRAWN_RECORD' and x['exclusion_reason'] and x['row_id'] for x in rw_) and
      not UC.evidence_records(fr1, rw_, None, Rw['provenance']), rw_[:1])
check('T06b عدد المسحوب في الإصدار كما يقرؤه العامل: 38 من 14797', Rw.get('hfn47_counts') == dict(events=14797, withdrawn=38, manifest_counts_events=14797),
      Rw.get('hfn47_counts'))
# إفساد حالة الحدث: نسخةٌ اختبارية من الإصدار يُرفع فيها السحب عن حدث
hb = os.path.join(TMP, 'hfn_unwithdraw')
os.makedirs(os.path.join(hb, 'release'))
shutil.copytree(os.path.join(P['hfn'], 'release', 'release_v47'), os.path.join(hb, 'release', 'release_v47'))
for x in ('tools', '02_roots', 'api', 'scripts'):
    os.symlink(os.path.join(P['hfn'], x), os.path.join(hb, x))
shutil.copy(os.path.join(P['hfn'], '.pinned_commit'), hb)
ev = os.path.join(hb, 'release', 'release_v47', 'events.csv')
os.chmod(ev, 0o644)
open(ev, 'w', encoding='utf-8').write(open(ev, encoding='utf-8').read().replace('WITHDRAWN_v43: A=N: علم: ابن بهمن', 'KEEP_v43: A=N: علم: ابن بهمن', 1))
Pb = dict(P, hfn=hb)
Rb = client.call([dict(lemma='بَهْمَنَ')], [], Pb, PINS)
mutation('M05 حالة الحدث: رفع السحب عن «بَهْمَنَ» في نسخةٍ اختبارية ← بصمة events.csv تخالف التثبيت (CONFIG_ERROR) فلا يُقرأ الإصدار',
         Rb['resources']['HFN:release/release_v47/events.csv']['status'].startswith('CONFIG_ERROR') and
         Rb['lemma']['بَهْمَنَ']['hfn47']['status'] in ('CONFIG_ERROR', 'RESOURCE_MISSING'), Rb['lemma']['بَهْمَنَ']['hfn47'])

# ---------- ٥ بوابة الحماية قبل الاستدعاء (بعدّ الاستدعاءات الفعلية) ----------
pk = [r for r in rows if r.get('protected')]
check('T07 الوحدات المحمية في 2:282 و3:154 (يَكُونَا، تَكُونَ…) لم يُسأل عنها: لا صفّ ولا معنى جذر، وسبب عدم الاستدعاء مسجّل',
      pk and all(r['lemma_status'] == 'PROTECTED_NOT_QUERIED' and r['query_status'].startswith('NOT_QUERIED') and not r['upstream_candidates']['rows']
                 and r['upstream_candidates']['root_meaning'] is None for r in pk), [(r['text'], r['lemma_status']) for r in pk])
frP = dict(fr0, text='كَانَ', unit='UP', protected=dict(cls='VERBAL', identity='كَانَ', ambiguous=False), root='كون', pattern='I',
           hfn_events=[dict(event_id='EP', verb='كَانَ')])
frN = dict(fr0, text='كَتَبَ', unit='UN', root='كتب', hfn_events=[dict(event_id='EN', verb='كَتَبَ')])
n0 = len(client.CALLS)
UC.run([frP, frN], PINS)
call_ = client.CALLS[n0:]
check('T08 العدّ الفعلي: استدعاءٌ واحد للعامل، فيه لمّة غير المحمي وجذره، وليس فيه «كَانَ» ولا «كون»',
      len(call_) == 1 and call_[0]['lemmas'] == ['كَتَبَ'] and call_[0]['roots'] == ['كتب'], call_)
orig = UC.lemma_status
UC.lemma_status = lambda fr: ('LEMMA_ESTABLISHED', 'إفساد: البوابة معطّلة')
n0 = len(client.CALLS)
UC.run([frP, frN], PINS)
UC.lemma_status = orig
mutation('M06 البوابة: تعطيلها يُدخل «كَانَ» و«كون» في الاستدعاء ← يكشفه العدّ', 'كَانَ' in client.CALLS[n0]['lemmas'] and 'كون' in client.CALLS[n0]['roots'],
         client.CALLS[n0:])

# ---------- ٦ ربط السمة بوجهها ولمّتها، دون خلط البدائل ----------
est = [r for r in rows if r['lemma_status'] == 'LEMMA_ESTABLISHED']
check('T09 كل صفٍّ مربوطٌ بوقوعه ووجهه (analysis_id) ولمّته، وكل سمةٍ مطابقة CANDIDATE لا حقيقة',
      est and all(x['face']['analysis_id'] == r['analysis_id'] and x['occurrence']['relation_id'] == r['relation_id'] and
                  x['vocalized_lemma'] in {e['verb'] for e in r['hfn_events']} for r in est for x in r['upstream_candidates']['rows']) and
      all(x['rank'] == 'CANDIDATE' and x.get('is_fact') is False for x in allrows if x['state'] == 'CANDIDATE_MATCH'))
unr = [r for r in rows if r['lemma_status'] == 'IDENTITY_OR_LEMMA_UNRESOLVED']
check('T10 الوجه أو اللمّة غير المحسومة: لا CANDIDATE_MATCH ولا دليل، والسبب مسجّل',
      all(x['state'] != 'CANDIDATE_MATCH' for r in unr for x in r['upstream_candidates']['rows']) and all(not r['evidence'] or
          all(e['feature'] == 'root_meaning' for e in r['evidence']) for r in unr))
frL = dict(frN, hfn_events=[dict(event_id='E1', verb='كَتَبَ'), dict(event_id='E2', verb='كَتُبَ')])
oL, _, _, _ = UC.run([frL], PINS)
mutation('M07 اللمّة: لمّتان للجذر والوزن ← IDENTITY_OR_LEMMA_UNRESOLVED، ولا سمة مطابقة لأيٍّ منهما',
         oL[0]['lemma_status'] == 'IDENTITY_OR_LEMMA_UNRESOLVED' and not any(x['state'] == 'CANDIDATE_MATCH' for x in oL[0]['upstream_candidates']['rows']),
         oL[0]['lemma_status'])
frF = dict(frN, analysis_selection='DEFERRED_MULTIPLE_LEMMAS')
oF, _, _, _ = UC.run([frF], PINS)
mutation('M08 الوجه: وجهٌ غير مختار ← لا تُنقل السمة إلى الكلمة كلها', oF[0]['lemma_status'] == 'IDENTITY_OR_LEMMA_UNRESOLVED' and
         not any(x['state'] == 'CANDIDATE_MATCH' for x in oF[0]['upstream_candidates']['rows']), oF[0]['lemma_status'])

# ---------- ٧ فشل المصدر مقابل النتيجة الفارغة ----------
mq = os.path.join(TMP, 'maq_nojson')
shutil.copytree(P['maq'], mq)
os.chmod(os.path.join(mq, 'output'), 0o755)
os.remove(os.path.join(mq, 'output', 'maqayis_all_roots.json'))
Rm = client.call([dict(lemma='قَقَقَ')], [dict(root='كسر', query_key='كسر', key_rule='IDENTITY'), dict(root='ققق', query_key='ققق', key_rule='IDENTITY')],
                 dict(P, maq=mq), PINS)
check('T11 لمّةٌ لا يعرفها مصدرٌ سليم: QUERY_OK_NO_RESULT؛ ومفتاحٌ ليس في البنك: QUERY_OK_NO_RESULT',
      Rm['lemma']['قَقَقَ']['mutawaa']['status'] == 'QUERY_OK_NO_RESULT' and Rm['root']['ققق']['root_meaning']['status'] == 'QUERY_OK_NO_RESULT',
      (Rm['lemma']['قَقَقَ']['mutawaa'], Rm['root']['ققق']['root_meaning']))
check('T12 ملفّ المصدر الغائب: RESOURCE_MISSING، لا «لا نتيجة»', Rm['resources']['MAQ:output/maqayis_all_roots.json']['status'] == 'RESOURCE_MISSING' and
      all(x.get('status', '').startswith('RESOURCE_MISSING') for x in Rm['root']['كسر']['maqayis'].get('records', [])) and
      Rm['root']['كسر']['maqayis'].get('records'), Rm['root']['كسر']['maqayis'])
check('T13 مفتاح الجذر: التحويل المعلوم وحده (كرسيّ الهمزة، المضاعف بحرفين)، والألف المبهمة لا تُخمَّن',
      UC.query_key('أمن') == ('ءمن', 'HAMZA_SEAT→ء') and UC.query_key('مد')[0] == 'مدد' and UC.query_key('قال')[0] is None and UC.query_key('كتب') == ('كتب', 'IDENTITY'))
check('T14 مقاييس ابن فارس عبر جدول الربط بمفتاح البنك، لا بمطابقة root_display؛ والمداخل الأربعة غير المربوطة معلنة',
      len(S['maqayis_unmapped_entries']) == 4 and all(r['upstream_candidates']['root_meaning']['maqayis_fallback'].get('via', '').startswith('AMLN:data/maqayis_bank_crosswalk')
                                                      for r in est if r['upstream_candidates']['root_meaning'] and r['upstream_candidates']['root_meaning']['maqayis_fallback'].get('status') == 'OK'),
      S['maqayis_unmapped_entries'])

# ---------- ٨ عدم تصادم الاستيرادات، وعدم الكتابة ----------
before = set(sys.modules)
r10 = client.call([dict(lemma='كَسَرَ')], [dict(root='كسر', query_key='كسر', key_rule='IDENTITY')], P, PINS)
new = set(sys.modules) - before
exp = dict(core=P['wazn'], engines=P['wazn'], word_tree=P['amln'], arabic_net_api=P['amln'], root_meaning=P['hfn'], root_taxonomy=P['hfn'], hfn_common=P['hfn'])
check('T15 لا تصادم: لا تُحمَّل core ولا engines ولا word_tree في عملية المحلّل، وكل حزمةٍ في العامل من جذر مصدرها، ولا sarf ولا tools فيه',
      not new & {'core', 'engines', 'word_tree', 'root_taxonomy', 'root_meaning', 'hfn_common', 'arabic_net_api'} and
      all((r10['import_origins'].get(k) or '').startswith(os.path.realpath(v)) for k, v in exp.items()) and
      r10['import_origins'].get('sarf') is None and r10['import_origins'].get('tools') is None, r10['import_origins'])
check('T16 لا كتابة في المصادر (الملفات قبل الاستدعاء وبعده)، ولا ملف في مجلد العمل', all(not v for v in r10['isolation']['resource_writes'].values())
      and not r10['isolation']['cwd_files'], r10['isolation'])

# ---------- ٩ غياب اعتماد الأحكام القديمة على الحقول الجديدة ----------
from test_closure_helpers import verse_records
a1 = verse_records(2, 282)
client.call([dict(lemma='كَتَبَ')], [dict(root='كتب', query_key='كتب', key_rule='IDENTITY')], P, PINS)
a2 = verse_records(2, 282)
check('T17 سجلات 2:282 قبل استدعاء المصادر وبعده متطابقة', a1 == a2)
EVD = UC.load_evidence(OUT)


def certs(s, v, ev):
    from sarf.catalog import Catalog
    from sarf.analyze import analyze
    from sarf.algebra import Trace, sentence_geo, linguistic_layer, closure_certificate
    from sarf.features import unit_features
    from sarf import relations as RL, quran_source
    CAT = Catalog([os.path.join(ROOT, 'operators_catalog.jsonl'), os.path.join(ROOT, 'operators_catalog_split_vocalized.csv')])
    text = next(t for s_, v_, t in quran_source.rows() if (s_, v_) == (s, v))
    a = analyze(CAT, text, quran_source.uthmani_mode())
    S_, U_ = sentence_geo(a, f'Q{s}:{v}', Trace())
    C_, R_ = [], []
    LT, _, _ = linguistic_layer([(s, v, a, U_, S_)], Trace(), 'e', cond_out=C_, rel_out=R_)
    o = RL.verse_relations(a, U_, unit_features(a, U_), f'{s}:{v}', legacy_cond=C_, legacy_rel=R_)
    Js = [J for SP in LT for D in SP.A + SP.O.get('pending', []) for J in D.A + D.O.get('pending', [])]
    return [closure_certificate(J, o['records'], upstream=ev) for J in Js], [closure_certificate(J, o['records']) for J in Js]


ADDED_PATHS = ('certificate.external_evidence_ids', 'certificate.obligations[*].external_evidence')   # المسارات المعلنة للإضافة وحدها


def strip(c):
    c = copy.deepcopy(c)
    c.pop('external_evidence_ids', None)
    for o_ in c['obligations']:
        o_.pop('external_evidence', None)
    return c


c1, c0 = certs(2, 282, EVD)
withev = [o_ for c in c1 for o_ in c['obligations'] if o_.get('external_evidence')]
check('T18 شهادات 2:282 بالأدلّة الحديثة وبدونها متطابقة في كل حقلٍ عدا المسارين المعلنين (external_evidence_ids وexternal_evidence)، ولا دليل يستوفي التزاماً',
      withev and [strip(c) for c in c1] == [strip(c) for c in c0] and
      all(not e['discharges_obligation'] and not e['closes_face'] and not e['conditions_met'] for o_ in withev for e in o_['external_evidence']), len(withev))
bad = {u: [dict(e, discharges_obligation=True, closes_face=True, conditions_met=True) for e in v] for u, v in EVD.items()}
c2, _ = certs(2, 282, bad)
mutation('M09 الاعتماد: دليلٌ يدّعي الاستيفاء والإغلاق ← لا تتغيّر الشهادة، ويُكتب ادّعاؤه False', [strip(c) for c in c2] == [strip(c) for c in c0] and
         all(not e['discharges_obligation'] for c in c2 for o_ in c['obligations'] for e in (o_.get('external_evidence') or [])))

print(json.dumps(dict(mutations=MUT), ensure_ascii=False))
print('ALL OK' if not FAIL else f'FAILED {len(FAIL)}: {FAIL}')
shutil.rmtree(TMP, ignore_errors=True)
sys.exit(1 if FAIL else 0)
