# -*- coding: utf-8 -*-
"""صحة كل استعلامٍ على حدة (SARF_HFN_V48_TARGETED_REPAIR_AND_CLOSURE_03 §٧).

المتوقَّع يُبنى من CSV المثبّت بدوالّ مستقلة عن واجهة HFN وعن المستهلك (expected_*)، ثم يُقابَل بجواب المستهلك عبر الواجهة المباشرة وعبر HTTP:
  DIRECT_HTTP_EQUIVALENCE   الجوابان متطابقان للسؤال نفسه
  RETURNED_ROW_FIDELITY     كل صفٍّ معاد يساوي صفّ الملف بحقوله كلها
  PER_QUERY_SOUNDNESS       لا صفّ معاد خارج المتوقَّع لسؤاله
  PER_QUERY_COMPLETENESS    كل صفٍّ متوقَّع لسؤاله معاد (بالسياسة المعلنة للمفتاح)
  WITHDRAWN_EXCLUSION       المسحوب لا يدخل الحيّ، ويُحفظ في سجلّ التدقيق
  KEY_REACHABILITY          (قياس) كل مفتاح dhat_K مخزَّن يُسترجع بسؤاله نفسه — يفشل لـ«الحاق»: عيب HFN D10، استثناءٌ مسمّى لا يُصلح في SARF
والإفسادات P01–P06 تثبت أن هذه الأحكام تسقط حين يجب، وأن تكافؤ المباشر وHTTP لا يثبت الصحة.
يحتاج SARF_HFN_V47_DIR وSARF_HFN_V48_DIR؛ وبغيابهما NOT_RUN (رمز 2)."""
import csv, gzip, json, os, re, socket, subprocess, sys, time, unicodedata, urllib.request
H = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
V47, V48 = os.environ.get('SARF_HFN_V47_DIR', ''), os.environ.get('SARF_HFN_V48_DIR', '')
API = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(V48 or '.'))), 'api')
if not (os.path.isdir(V47) and os.path.isdir(V48) and os.path.exists(os.path.join(API, 'server.py'))):
    print('NOT_RUN: SARF_HFN_V47_DIR وSARF_HFN_V48_DIR (ومجلّد api) غير متاحة'); sys.exit(2)
sys.path.insert(0, os.path.join(H, 'tools', 'ajnas'))
import consumer as AC
OUT = os.environ.get('SARF_TEST_OUT')
M48 = '6cd85dc63b1e920420b09e6d4be748188e37cfc32fe780a05fa2568534119a75'
FAIL, RES = [], []


def check(name, ok, got=''):
    print(('PASS ' if ok else 'FAIL ') + name + ('' if ok else f' — {str(got)[:500]}'))
    RES.append(dict(name=name, ok=bool(ok), got=None if ok else str(got)[:3000]))
    if not ok:
        FAIL.append(name)


# ── المتوقَّع من الملف وحده ──
rows = list(csv.DictReader(open(os.path.join(V48, 'ahdath_ajnas.csv'), encoding='utf-8')))
events = list(csv.DictReader(open(os.path.join(V48, 'events.csv'), encoding='utf-8')))
ROOT_OF = {e['event_id']: e['root_K'] for e in events}
WD = {e['event_id'] for e in events if (e.get('event_review_v36') or '').startswith('WITHDRAWN')}
BY_ID = {r['link_id']: r for r in rows}
LIVE = {r['link_id'] for r in rows if r['event_id'] not in WD and r['event_withdrawn'] != 'True'}
_DI = re.compile('[ؐ-ًؚ-ٰٟۖ-ۭـ]')
_HZ = str.maketrans({'أ': 'ء', 'إ': 'ء', 'آ': 'ء', 'ؤ': 'ء', 'ئ': 'ء', 'ٱ': 'ا', 'ى': 'ي'})


def policy_key(word):
    """السياسة المعلنة لمفتاح الذات (توثيق واجهة HFN وعقد المستهلك)، مكتوبةٌ هنا مستقلةً: الكلمة الأولى، NFC، حذف التشكيل والتطويل،
    توحيد مقاعد الهمزة وألف الوصل والألف المقصورة، حروفٌ عربية فقط، ثم حذف «ال» إن بقي بعده حرفان فأكثر (طول ≥ 4)"""
    w = unicodedata.normalize('NFC', (word or '').split(' ')[0])
    w = _DI.sub('', w).translate(_HZ)
    w = re.sub('[^ء-ي]', '', w)
    return w[2:] if w.startswith('ال') and len(w) >= 4 else w


_IX_EV, _IX_RT, _IX_KEY = {}, {}, {}
for _r in rows:
    _IX_EV.setdefault(_r['event_id'], set()).add(_r['link_id'])
    _IX_RT.setdefault(ROOT_OF.get(_r['event_id']), set()).add(_r['link_id'])
    for _p in _r['dhat_K'].split('·'):
        _IX_KEY.setdefault(_p, set()).add(_r['link_id'])


def expected(iface, q, role=None):
    """المتوقَّع من فهارس الملف نفسه (حدث ← صفوفه، جذر الحدث في events.csv ← صفوفه، مفتاح السياسة ← صفوف dhat_K)"""
    if iface == 'event':
        ids = set(_IX_EV.get(q, ()))
    elif iface == 'root':
        ids = set(_IX_RT.get(q, ()))
    else:
        ids = set(_IX_KEY.get(policy_key(q), ()))
    if role:
        ids = {i for i in ids if BY_ID[i]['role'] == role}
    return ids & LIVE, ids - LIVE


def free_port():
    s = socket.socket(); s.bind(('127.0.0.1', 0)); p = s.getsockname()[1]; s.close(); return p


def serve(rel):
    port = free_port()
    p = subprocess.Popen([sys.executable, '-s', '-B', 'server.py', '--release', rel, '--port', str(port)], cwd=API, stdout=subprocess.DEVNULL,
                         stderr=subprocess.PIPE, env={k: v for k, v in os.environ.items() if k != 'HFN_RELEASE'})
    for _ in range(300):
        try:
            urllib.request.urlopen(f'http://127.0.0.1:{port}/stats', timeout=2); return p, f'http://127.0.0.1:{port}'
        except Exception:
            time.sleep(0.2)
    p.kill(); raise RuntimeError('server did not start')


class Faulty:
    """يغلّف خلفيةً ويُفسد أجوبتها بطريقةٍ مسمّاة (للإفسادات وحدها)"""
    def __init__(self, b, mode, arg=None):
        self.b, self.mode, self.arg = b, mode, arg
        self.api, self.release, self.manifest_sha256, self.withdrawn = b.api, b.release, b.manifest_sha256, b.withdrawn
        self.has_ajnas = getattr(b, 'has_ajnas', None)

    def call(self, iface, q, role=None):
        if self.mode == 'swap' and iface == 'event' and q in self.arg:
            q = self.arg[q]
        r = self.b.call(iface, q, role)
        links = list((r.get('payload') or {}).get('links') or [])
        if self.mode == 'global':
            links = [BY_ID[i] for i in sorted(LIVE)[:40]]
        elif self.mode == 'extra' and q == self.arg[0]:
            links = links + [BY_ID[self.arg[1]]]
        elif self.mode == 'missing' and q == self.arg and links:
            links = links[1:]
        elif self.mode == 'norole':
            links = list((self.b.call(iface, q, None).get('payload') or {}).get('links') or [])
        elif self.mode == 'altered' and links:
            links = [dict(links[0], shahid_line='0')] + links[1:]
        if r.get('payload') is not None:
            r = dict(r, payload=dict(r['payload'], links=links))
        return r


def run_queries(cons, queries):
    """→ {(iface,q,role): (ids, excluded_ids, rows)}"""
    out = {}
    for iface, q, role in queries:
        a = cons.query(iface, q, role)
        out[(iface, q, role)] = ({l['link_id'] for l in a['links']}, {x['link_id'] for x in a['excluded']}, a['links'])
    return out


def judge(res, res_http=None):
    v = dict(DIRECT_HTTP_EQUIVALENCE=None, RETURNED_ROW_FIDELITY=[], PER_QUERY_SOUNDNESS=[], PER_QUERY_COMPLETENESS=[], WITHDRAWN_EXCLUSION=[])
    for key, (ids, exc, rws) in res.items():
        live_exp, wd_exp = expected(*key)
        if ids - live_exp:
            v['PER_QUERY_SOUNDNESS'].append(dict(query=key, extra=sorted(ids - live_exp)[:5]))
        if live_exp - ids:
            v['PER_QUERY_COMPLETENESS'].append(dict(query=key, missing=sorted(live_exp - ids)[:5]))
        if [r for r in rws if r != BY_ID.get(r['link_id'])]:
            v['RETURNED_ROW_FIDELITY'].append(dict(query=key))
        if ids & (set(BY_ID) - LIVE) or not exc <= (set(BY_ID) - LIVE):
            v['WITHDRAWN_EXCLUSION'].append(dict(query=key))
    if res_http is not None:
        v['DIRECT_HTTP_EQUIVALENCE'] = [k for k in res if (res[k][0], res[k][1]) != (res_http.get(k, (None, None, None))[0], res_http.get(k, (None, None, None))[1])
                                        or json.loads(json.dumps(res[k][2], ensure_ascii=False)) != res_http.get(k, (None, None, None))[2]]
    return v


d48 = AC.DirectBackend(V48, API)
C = AC.AjnasConsumer(d48, 'HFN_release_v48', M48, WD)
roots = sorted({e['root_K'] for e in events})
words = sorted({w for r in rows for w in r['dhat'].split('·') if w.strip()})
keys = sorted({p for r in rows for p in r['dhat_K'].split('·') if p})
ROLES = ['فاعل', 'محلّ', 'آلة', 'مكان', 'زمان', 'مصدر']
Q = [('event', e['event_id'], None) for e in events] + [('root', r, None) for r in roots] + [('dhat', w, None) for w in words]
Q += [('dhat', k, None) for k in keys if k not in set(words)]
ev_with = sorted({r['event_id'] for r in rows})
Q += [('dhat', w, ro) for w in words for ro in ROLES] + [('event', e, ro) for e in ev_with for ro in ROLES] + [('root', r, ro) for r in sorted({r['root_K'] for r in rows}) for ro in ROLES]
srv48, url48 = serve(V48)
try:
    CH = AC.AjnasConsumer(AC.HttpBackend(url48, API), 'HFN_release_v48', M48, WD)
    t0 = time.time()
    res = run_queries(C, Q)
    res_h = run_queries(CH, Q)
    v = judge(res, res_h)
    n = len(Q)
    nonkey = [k for k in keys if k not in set(words)]
    D10 = [dict(query=k, expected_by_stored_key=sorted(i for i in LIVE if k in BY_ID[i]['dhat_K'].split('·')),
                expected_by_policy=sorted(expected('dhat', k)[0]), actual=sorted(res[('dhat', k, None)][0]), key_after_policy=policy_key(k))
           for k in keys if (('dhat', k, None) in res) and {i for i in LIVE if k in BY_ID[i]['dhat_K'].split('·')} - res[('dhat', k, None)][0]]
    check(f'DIRECT_HTTP_EQUIVALENCE: {n} سؤالاً، المباشر = HTTP (الروابط والمستبعد والصفوف)', not v['DIRECT_HTTP_EQUIVALENCE'], v['DIRECT_HTTP_EQUIVALENCE'][:3])
    check('RETURNED_ROW_FIDELITY: كل صفٍّ معاد = صفّ الملف بحقوله كلها', not v['RETURNED_ROW_FIDELITY'], v['RETURNED_ROW_FIDELITY'][:3])
    check('PER_QUERY_SOUNDNESS: لا صفّ خارج متوقَّع سؤاله (حدث، جذر، ذات، ومع الدور)', not v['PER_QUERY_SOUNDNESS'], v['PER_QUERY_SOUNDNESS'][:3])
    check('PER_QUERY_COMPLETENESS: كل متوقَّعٍ بالسياسة المعلنة معاد لسؤاله', not v['PER_QUERY_COMPLETENESS'], v['PER_QUERY_COMPLETENESS'][:3])
    check('WITHDRAWN_EXCLUSION: لا مسحوب حيّ، والمستبعد كله مسحوب وفي سجلّ التدقيق بسببه',
          not v['WITHDRAWN_EXCLUSION'] and C.audit_log and {x['link_id'] for x in C.audit_log} == set(BY_ID) - LIVE
          and all('EVENT_WITHDRAWN' in x['reason'] for x in C.audit_log), v['WITHDRAWN_EXCLUSION'][:3])
    check('KEY_REACHABILITY (قياس، استثناءٌ مسمّى): المفاتيح المخزَّنة التي لا تسترجع صفوفها بسؤالها نفسه = «الحاق» وحده (D10، HFN)',
          [x['query'] for x in D10] == ['الحاق'], D10)
    RES[-1]['measured'] = D10
    # ── الإفسادات: كل واحدٍ يُسقط حكمه، على عيّنةٍ ثابتة ──
    e1, e2 = ev_with[0], ev_with[1]
    sample = [('event', e1, None), ('event', e2, None)] + [q for q in Q if q[0] == 'event' and q[2] is None and q[1] in set(ev_with[2:])][:300] \
        + [('root', 'حلب', None), ('dhat', 'الفرس', 'فاعل')]
    def fault(mode, arg=None, http=False):
        b = Faulty(d48, mode, arg)
        c = AC.AjnasConsumer(b, 'HFN_release_v48', M48, WD)
        r = run_queries(c, sample)
        return r
    r = fault('swap', {e1: e2, e2: e1})
    j = judge(r)
    union_same = set().union(*[x[0] for x in r.values()]) == set().union(*[x[0] for x in run_queries(C, sample).values()])
    check('P01 تبديل جوابي حدثين مع بقاء الاتحاد صحيحاً: الاتحاد لا يكشفه، والفحص لكل سؤال يكشفه', union_same and j['PER_QUERY_SOUNDNESS'], union_same)
    j = judge(fault('global'))
    check('P02 إعادة المجموعة العامة لكل سؤال: يسقط PER_QUERY_SOUNDNESS', bool(j['PER_QUERY_SOUNDNESS']))
    extra_id = next(i for i in sorted(LIVE) if BY_ID[i]['event_id'] != e1)
    j = judge(fault('extra', (e1, extra_id)))
    check('P03 صفٌّ زائد في جواب حدث: يسقط PER_QUERY_SOUNDNESS', any(x['query'][1] == e1 for x in j['PER_QUERY_SOUNDNESS']))
    j = judge(fault('missing', e1))
    check('P04 صفٌّ ناقص: يسقط PER_QUERY_COMPLETENESS', any(x['query'][1] == e1 for x in j['PER_QUERY_COMPLETENESS']))
    b = Faulty(d48, 'norole')
    craw = AC.AjnasConsumer(b, 'HFN_release_v48', M48, WD)
    # المستهلك يصفّي الدور بنفسه أيضاً؛ فيُفسَد المستهلك هنا بتعطيل تصفيته لاختبار أن الحكم يسقط
    orig_q = craw.query
    def noflt(iface, q, role=None):
        return orig_q(iface, q, None)
    craw.query = noflt
    j = judge(run_queries(craw, [('dhat', 'الفرس', 'فاعل'), ('root', 'حلب', 'محلّ')]))
    check('P05 إسقاط التصفية بالدور: يسقط PER_QUERY_SOUNDNESS', bool(j['PER_QUERY_SOUNDNESS']))
    srvA, urlA = serve(V48)
    try:
        bh = AC.HttpBackend(urlA, API)
        cd = AC.AjnasConsumer(Faulty(d48, 'swap', {e1: e2, e2: e1}), 'HFN_release_v48', M48, WD)
        ch = AC.AjnasConsumer(Faulty(bh, 'swap', {e1: e2, e2: e1}), 'HFN_release_v48', M48, WD)
        s2 = [('event', e1, None), ('event', e2, None)]
        rd, rh = run_queries(cd, s2), run_queries(ch, s2)
        j = judge(rd, rh)
    finally:
        srvA.kill()
    check('P06 المباشر وHTTP يتفقان على جوابٍ خاطئ: التكافؤ يجتاز، والصحة لكل سؤال تسقط', not j['DIRECT_HTTP_EQUIVALENCE'] and j['PER_QUERY_SOUNDNESS'],
          (j['DIRECT_HTTP_EQUIVALENCE'], j['PER_QUERY_SOUNDNESS'][:1]))
    j = judge(fault('altered'))
    check('P07 صفٌّ معاد بحقلٍ محرَّف (رقم سطر الشاهد): يسقط RETURNED_ROW_FIDELITY', bool(j['RETURNED_ROW_FIDELITY']))
    if OUT:
        os.makedirs(OUT, exist_ok=True)
        with gzip.open(os.path.join(OUT, 'api_per_query.tsv.gz'), 'wt', encoding='utf-8') as f:
            f.write('interface\tquery\trole\texpected_live\treturned_direct\treturned_http\texcluded\tsound\tcomplete\n')
            for k in Q:
                le = expected(*k)[0]; ids = res[k][0]
                f.write('\t'.join([k[0], k[1], k[2] or '', ','.join(sorted(le)), ','.join(sorted(ids)), ','.join(sorted(res_h[k][0])),
                                   ','.join(sorted(res[k][1])), str(not (ids - le)), str(not (le - ids))]) + '\n')
        json.dump(dict(results=RES, queries=n, key_reachability_exceptions=D10, audit_log=C.audit_log, seconds=round(time.time() - t0, 1)),
                  open(os.path.join(OUT, 'test_v48c3_api_per_query.results.json'), 'w'), ensure_ascii=False, indent=1)
finally:
    srv48.kill()
print(f'CHECKS pass={len(RES) - len(FAIL)} fail={len(FAIL)} total={len(RES)}')
print('ALL OK' if not FAIL else f'FAILED {len(FAIL)}: {FAIL}')
sys.exit(1 if FAIL else 0)
