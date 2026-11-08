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
W1 = dict(W0, ahdath=NO, transitivity_wasit_v5=dict(status='OK', rows=[dict(event_id='E2', root='كسر', verb='كَسَّرَ', form='فَعَّلَ', transitivity_wasit='متعدي', harf='',
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

# ================= SARF_UPSTREAM_CONSUMER_REPAIR_02 =================
# ---------- §٢ هوية المعجم: الجذر والبناء ومعرّف الحدث، في كل عائلات المصادر ----------
OUT2, SUM2 = os.path.join(TMP, 'w.jsonl.gz'), os.path.join(TMP, 'w.json')
p2 = subprocess.run([sys.executable, '-s', 'tools/upstream_candidates.py', OUT2, SUM2, '--verses', '2:8', '--jobs', '1'], capture_output=True, text=True,
                    env=dict(os.environ, PYTHONHASHSEED='0'))
R8 = [json.loads(l) for l in gzip.open(OUT2, 'rt', encoding='utf-8')]
yq = [x for r in R8 if r['text'] == 'يَقُولُ' for x in r['upstream_candidates']['rows'] if x['source_key'] == 'hfn47']
bad = [x for x in yq if x['value']['event_id'] == 'HFN-E-e1bbafba2a']
good = [x for x in yq if x['value']['event_id'] != 'HFN-E-e1bbafba2a' and x['state'] == 'CANDIDATE_MATCH']
check('R01 الشاهد الحاكم (يَقُولُ، 2:8، جذر الوجه قول): حدث «قَالَ» تحت قيل (HFN-E-e1bbafba2a، مصدره قَيْلُولَة) LEXEME_IDENTITY_CONFLICT بلا دليل، '
      'وحدث قول نفسه CANDIDATE_MATCH', p2.returncode == 0 and bad and all(x['state'] == 'LEXEME_IDENTITY_CONFLICT' and 'ROOT' in x['identity']['reason']
                                                                     and not x.get('evidence_id') for x in bad) and good and
      not any(e['source_row_id'] == 'HFN-E-e1bbafba2a' for r in R8 for e in r['evidence']), [(x['value']['event_id'], x['state']) for x in yq])
allr = [x for r in rows for x in r['upstream_candidates']['rows']]
check('R02 لا CANDIDATE_MATCH بهويةٍ غير IDENTITY_OK في أي عائلة', all(x.get('identity_status') == 'IDENTITY_OK' for x in allr if x['state'] == 'CANDIDATE_MATCH'))
fid = dict(fr0, root='قول', pattern='I', hfn_events=[dict(event_id='HFN-E-8ca9af323a', verb='قَالَ')])
EVR = lambda root, form, verb, eid='EX', wd=False: dict(event_id=eid, found=True, root_K=root, verb=verb, form=form, withdrawn=wd)
st_, d_ = UC.identity(fid, 'قيل', 'فَعَلَ', 'قَالَ', EVR('قيل', 'فَعَلَ', 'قَالَ'), {})
mutation('M10 جذر مصدرٍ مختلف مع لمّةٍ مطابقة ← LEXEME_IDENTITY_CONFLICT', st_ == 'LEXEME_IDENTITY_CONFLICT' and 'ROOT' in d_['reason'], (st_, d_))
st_, d_ = UC.identity(fid, 'قول', 'فَعَّلَ', 'قَالَ', None, {})
mutation('M11 بناءٌ غير متوافق (فَعَّلَ لوجهٍ من الباب I) ← LEXEME_IDENTITY_CONFLICT', st_ == 'LEXEME_IDENTITY_CONFLICT' and 'FORM' in d_['reason'], (st_, d_))
st_, d_ = UC.identity(fid, 'قول', 'فَعَلَ', 'قَالَ', EVR('كتب', 'فَعَلَ', 'كَتَبَ'), {})
mutation('M12 معرّف حدثٍ يخالف حقوله ← EVENT_ID_FIELD_MISMATCH', st_ == 'EVENT_ID_FIELD_MISMATCH', (st_, d_))
st_, d_ = UC.identity(fid, 'قول', 'فَعَلَ', 'قَالَ', EVR('قول', 'فَعَلَ', 'قَالَ', wd=True), {})
check('R03 معرّف حدثٍ مسحوب في صفٍّ من أي عائلة (لا HFN وحده) ← WITHDRAWN_RECORD بسبب السحب نفسه', st_ == 'WITHDRAWN_RECORD' and d_['reason'] == 'EVENT_WITHDRAWN')
st_, d_ = UC.identity(fid, None, None, 'قَالَ', None, {})
check('R04 نقص معلومات الهوية تأجيل لا تخمين: IDENTITY_UNDETERMINED', st_ == 'IDENTITY_UNDETERMINED' and d_['reason'].startswith('MISSING'))
st_, d_ = UC.identity(fid, 'قول', 'فَعَلَ', 'قَالَ', None, {'فَعَلَ': 'II'})
check('R05 جدول الربط الموثّق يخالف تصنيف sarf للبناء ← IDENTITY_UNDETERMINED (لا يُختار أحدهما)', st_ == 'IDENTITY_UNDETERMINED' and 'CROSSWALK' in d_['reason'])
st_, d_ = UC.identity(fid, 'قول', 'فَعَلَ', 'قَالَ', EVR('قول', 'فَعَلَ', 'قَالَ', 'HFN-E-8ca9af323a'), {'فَعَلَ': 'I'})
check('R06 شاهد موجب: الجذر والبناء والحدث متوافقة ← IDENTITY_OK ومرتبطٌ بحدث الوجه', st_ == 'IDENTITY_OK' and d_['event_linked_to_face'], d_)
# ---------- §٦ المسحوب يصل إلى بوابة الاستهلاك في بيئةٍ سليمة (لا بإفساد البصمة) ----------
frW = dict(fr0, text='بَهْمَنَ', unit='UW', root='بهمن', pattern='QI', hfn_events=[dict(event_id='Z', verb='بَهْمَنَ')])
oW, resW, _, _ = UC.run([frW], PINS)
rW = [x for x in oW[0]['upstream_candidates']['rows'] if x['source_key'] == 'hfn47']
check('R07 سجلٌّ مسحوبٌ حقيقي من الإصدار المثبت السليم يبلغ البوابة عبر run() ويُرفض بسبب WITHDRAWN نفسه، بلا دليل',
      rW and all(x['state'] == 'WITHDRAWN_RECORD' for x in rW) and not oW[0]['evidence'], [(x['row_text'], x['state']) for x in rW])
WI = dict(W0, ahdath=NO, sifat_v2=dict(status='OK', rows=[dict(event_id='HFN-E-34cc036f8f', root='بهمن', form='فَعْلَلَ', verb='بَهْمَنَ', word='x', template='t',
                                                               kind='k', transitivity_wasit='لازم', match='EXACT', diff=[], row_verb='بَهْمَنَ',
                                                               event_ref=resW and None)]))
evw = [e for e in client.call([dict(lemma='بَهْمَنَ')], [], P, PINS)['lemma']['بَهْمَنَ']['hfn47']['rows'] if e['withdrawn']][0]
WI['sifat_v2']['rows'][0]['event_ref'] = dict(event_id=evw['event_id'], found=True, root_K=evw['root_K'], verb=evw['verb'], form=evw['form'], withdrawn=True)
rI = [x for x in UC.feature_rows(frW, 'بَهْمَنَ', WI, res0, PINS) if x['source_key'] == 'sifat_v2']
check('R08 منفذ العلاقات: صفّ صفاتٍ يحيل بمعرّفه إلى حدثٍ مسحوب (حُقن بعد التحقّق من المصدر) ← WITHDRAWN_RECORD، لا CANDIDATE_MATCH',
      rI and rI[0]['state'] == 'WITHDRAWN_RECORD', rI[:1])
r1 = client.call([dict(lemma='بَهْمَنَ')], [], P, PINS)['lemma']['بَهْمَنَ']['hfn47']['rows']
r2 = client.call([dict(lemma='بَهْمَنَ'), dict(lemma='كَسَرَ')], [], P, PINS)['lemma']['بَهْمَنَ']['hfn47']['rows']
check('R09 منفذ الفهرس والذاكرة: كل استدعاءٍ عمليةٌ جديدة بلا خبيئة مشتركة، والسحب نفسه في الاستدعاءين، ومرجع الحدث مقروءٌ من الإصدار لا من ذاكرة',
      [x['withdrawn'] for x in r1] == [x['withdrawn'] for x in r2] and all(x['event_ref']['withdrawn'] == x['withdrawn'] for x in r1 + r2))
# ---------- §٣ معرّفات الأدلّة ----------
allev = [e for r in rows for e in r['evidence']]
check('R10 كل معرّف دليلٍ بصمة محتواه، ولا معرّفٌ واحد بمحتويين', allev and not UC.verify_evidence_registry(allev), UC.verify_evidence_registry(allev)[:3])
e0 = allev[0]
twin = dict(e0, payload=dict(e0['payload'], value='محتوى آخر'))
mutation('M13 دليلان مختلفان بالمعرّف نفسه ← SAME_ID_DIFFERENT_CONTENT وID_DOES_NOT_MATCH_CONTENT',
         {k for k, _ in UC.verify_evidence_registry([e0, twin])} >= {'ID_DOES_NOT_MATCH_CONTENT', 'SAME_ID_DIFFERENT_CONTENT'})
swap = dict(e0, analysis_id='A-OTHER-FACE')
mutation('M14 تبديل وجه الدليل مع بقاء نص الكلمة والمعرّف ← ID_DOES_NOT_MATCH_CONTENT', any(k == 'ID_DOES_NOT_MATCH_CONTENT' for k, _ in UC.verify_evidence_registry([swap])))
frD = dict(fr0, root='كسر', pattern='I', hfn_events=[dict(event_id='E1', verb='كَسَرَ')])
FACE_D = dict(morph_candidate_id=frD['morph_candidate_id'], analysis_id=frD['analysis_id'], root='كسر', pattern='I')
two = [dict(source_key='hfn47', state='CANDIDATE_MATCH', provider='HFN', route_id='RELEASE_V47_EVENT', commit='c' * 40, file='f', file_sha256='s', row_id=i,
            value=dict(event_id=i, masdar=m_), vocalized_lemma='كَسَرَ', row_text='كَسَرَ', match='EXACT', face=dict(FACE_D), route_status='RELEASE_CANDIDATE',
            route_measure=dict(wilson_low=None)) for i, m_ in (('E1', 'كَسْر'), ('E9', 'كُسُور'))]


def row_map(evs):
    """صفّ المصدر ← (معرّف الدليل، محتواه القانوني)"""
    return {(e['occurrence_id'], e['source_key'], e['route_id'], str(e['source_row_id'])): (e['evidence_id'], UC.canonical({k: v for k, v in e.items() if k not in UC.ID_KEYS}))
            for e in evs}


ev2 = UC.evidence_records(frD, [dict(x) for x in two], None, res0['provenance'], PINS)
ev2r = UC.evidence_records(frD, [dict(x) for x in reversed(two)], None, res0['provenance'], PINS)
check('R11a حدثان مختلفان للوجه نفسه: دليلان بمعرّفين ومحتويين مختلفين، ولا يستبدل أحدهما الآخر، والسجلّ سليم',
      len({e['evidence_id'] for e in ev2}) == 2 and len(row_map(ev2)) == 2 and not UC.verify_evidence_registry(ev2), UC.verify_evidence_registry(ev2))
check('R11b ثبات الربط بعكس الترتيب: لكل صفّ مصدرٍ المعرّفُ نفسه والمحتوى نفسه (لا تساوي المجموعتين وحده)', row_map(ev2) == row_map(ev2r))
# من المسار العام: وقوعان بترتيبين، وأحداث كل وقوعٍ بترتيبين
frA = dict(frN, unit='UA', relation_id='RA', hfn_events=[dict(event_id='E1', verb='كَتَبَ')])
frB = dict(fr0, text='كَسَرَ', unit='UB', relation_id='RB', root='كسر', hfn_events=[dict(event_id='E2', verb='كَسَرَ')])
o1, _, _, _ = UC.run([frA, frB], PINS)
o2, _, _, _ = UC.run([frB, frA], PINS)
m1 = row_map([e for r in o1 for e in r['evidence']])
m2 = row_map([e for r in o2 for e in r['evidence']])
check('R11c من run(): تبديل ترتيب الوقوعات لا يغيّر ربط أي صفّ مصدرٍ بمعرّفه ومحتواه', m1 and m1 == m2, (len(m1), len(m2)))
# إفساد: معرّفٌ من موضع الصفّ في التشغيل — يكشفه اختبار الربط لا اختبار المجموعتين
pos = lambda evs: [dict(e, evidence_id=f'POS-{i}', id=f'POS-{i}') for i, e in enumerate(evs)]
mutation('M22 معرّفٌ من ترتيب الصفّ: تساوي مجموعتي المعرّفات لا يكشفه، واختبار الربط يكشفه',
         {e['evidence_id'] for e in pos(ev2)} == {e['evidence_id'] for e in pos(ev2r)} and row_map(pos(ev2)) != row_map(pos(ev2r)))
# ---------- مراجعة b2f926e §١–§٢: الإحالة إلى الحدث دقيقة، وفشل المفتاح تأجيل ----------
EVK = lambda root, form, verb: dict(event_id='EK', found=True, root_K=root, verb=verb, form=form, withdrawn=False)
st_, d_ = UC.identity(fid, 'قول', 'فَعِلَ', 'قَالَ', EVK('قول', 'فَعَلَ', 'قَالَ'), {})
mutation('M16 بابٌ مختلف تحت الفئة نفسها I (الصفّ فَعِلَ، والحدث فَعَلَ) ← EVENT_ID_FIELD_MISMATCH: form', st_ == 'EVENT_ID_FIELD_MISMATCH' and 'form' in d_['reason'], (st_, d_.get('reason')))
fa = dict(fid, root='ءمم', hfn_events=[dict(event_id='EK', verb='أَمَّ')])
st_, d_ = UC.identity(fa, 'ءمم', 'فَعَلَ', 'أُمَّ', EVK('ءمم', 'فَعَلَ', 'أَمَّ'), {})
mutation('M17 تشكيلٌ مختلف بالحروف نفسها (أُمَّ / أَمَّ) ← EVENT_ID_FIELD_MISMATCH: verb', st_ == 'EVENT_ID_FIELD_MISMATCH' and 'verb' in d_['reason'], (st_, d_.get('reason')))
fq = dict(fid, root='قاو')
st_, d_ = UC.identity(fq, 'قاي', 'فَعَلَ', 'قَالَ', None, {})
mutation('M18 جذران مختلفان يفشل تحويل مفتاحيهما (قاو / قاي) ← IDENTITY_UNDETERMINED، لا مساواة قيمتي الفشل',
         st_ == 'IDENTITY_UNDETERMINED' and d_['reason'].startswith('ROOT_KEY_UNRESOLVED'), (st_, d_.get('reason')))
mis_, und_, _ = UC.reference_check('قاي', None, None, EVK('قاو', 'فَعَلَ', 'قَالَ'))
check('R14 فشل المفتاح في الإحالة إلى الحدث تأجيلٌ لا مساواة', not mis_ and und_ == ['ROOT_KEY_UNRESOLVED'], (mis_, und_))
st_, d_ = UC.identity(fid, 'قول', 'فَعَلَ', 'قَالَ', EVK('قول', 'فَعَلَ (أجوف)', 'قَالَ'), {})
check('R15 شاهد موجب: صيغة الصفّ بديلٌ في تسمية HFN («فَعَلَ» ∈ «فَعَلَ (أجوف)») ← IDENTITY_OK بتحويلٍ مسجّل',
      st_ == 'IDENTITY_OK' and any(t.startswith('FORM_LABEL_ALTERNATIVE') for t in d_['reference_check']['transforms']), d_.get('reference_check'))
st_, d_ = UC.identity(dict(fid, root='ءخذ', hfn_events=[]), 'ءخذ', 'افْتَعَلَ', 'ٱتَّخَذَ', EVK('ءخذ', 'افْتَعَلَ', 'اتَّخَذَ'), {})
check('R16 «ٱ/ا» في الفعل تحويلٌ معلن مسجّل، لا مخالفة', d_.get('reference_check', {}).get('transforms') == ['WASL_ALIF'] and st_ != 'EVENT_ID_FIELD_MISMATCH', (st_, d_))
# ---------- مراجعة b2f926e §٣: الحقول المكرّرة التي تقرؤها المستهلكات ----------
etw = next(e for e in allev if e['source_key'] == 'transitivity_wasit_v5') if any(e['source_key'] == 'transitivity_wasit_v5' for e in allev) else e0
tv = dict(etw, value=('متعدي' if etw.get('value') != 'متعدي' else 'لازم'))
codes = lambda e: {k for k, _ in UC.verify_evidence_registry([e])}
mutation('M19 تغيير value وحدها (لازم ← متعدي) مع بقاء payload.value والمعرّف ← VALUE_DIFFERS_FROM_PAYLOAD وID_DOES_NOT_MATCH_CONTENT',
         {'VALUE_DIFFERS_FROM_PAYLOAD', 'ID_DOES_NOT_MATCH_CONTENT'} <= codes(tv), codes(tv))
fr_ = dict(e0, face=dict(e0['face'], root='ءءء'))
mutation('M20 تغيير face.root وحده ← ID_DOES_NOT_MATCH_CONTENT', 'ID_DOES_NOT_MATCH_CONTENT' in codes(fr_), codes(fr_))
al = dict(e0, id='UPEV-' + '0' * 32)
mutation('M21 الحقل البديل id يخالف evidence_id ← ID_ALIAS_DIFFERS', 'ID_ALIAS_DIFFERS' in codes(al), codes(al))
check('R17 سجلات الأدلّة الحالية كلها متّسقة في الحقول المكرّرة والبصمة', not UC.verify_evidence_registry(allev), UC.verify_evidence_registry(allev)[:3])
ids_cert = {i for c in c1 for i in (c.get('external_evidence_ids') or [])}
reg = {e['evidence_id'] for e in allev}
check('R12 لا مرجع يتيم ولا ملتبس: كل معرّفٍ في الشهادات موجودٌ في السجلّ بمحتوى واحد', ids_cert and ids_cert <= reg, sorted(ids_cert - reg)[:3])
c3, _ = certs(2, 282, {u: [dict(e, discharges_obligation=True, closes_face=True, conditions_met=True, status='MET') for e in v] for u, v in EVD.items()})
mutation('M15 نقل سمةٍ حديثة إلى استيفاءٍ أو إغلاق ← الشهادة لا تتغيّر', [strip(c) for c in c3] == [strip(c) for c in c0])

print(json.dumps(dict(mutations=MUT), ensure_ascii=False))
print('ALL OK' if not FAIL else f'FAILED {len(FAIL)}: {FAIL}')
shutil.rmtree(TMP, ignore_errors=True)
sys.exit(1 if FAIL else 0)
