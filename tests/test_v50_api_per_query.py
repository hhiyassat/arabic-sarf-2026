# -*- coding: utf-8 -*-
"""صحة كل استعلامٍ على حدة على HFN v50 (SARF_HFN_V50_COMPATIBILITY_01 §٧)، مباشرةً وعبر HTTP.

المتوقَّع يُبنى من CSV المثبّت بدوالّ مستقلة عن واجهة HFN وعن المستهلك (expected_*). وخمس نتائج منفصلة:
  1 EQUIVALENCE    المباشر = HTTP للسؤال نفسه (الحي والمستبعد والصفوف وتحفّظات الواجهة)
  2 SOUNDNESS      لا صفّ معاد خارج متوقَّع سؤاله
  3 COMPLETENESS   كل متوقَّعٍ لسؤاله معاد (بفهرس المفتاح المعلن dhat_K للذات)
  4 EXCLUSION      المستبعد = المسحوب ∪ الاستشهاد الوصفي (قاعدة SARF المعلنة)، كلٌّ بسببه ودليله في سجلّ التدقيق، ولا شيء منه حيّ
  5 PRESERVATION   الصف المعاد = صفّ الملف بحقوله كلها، وتحفّظات الواجهة الخام محفوظة (ومعها ملاحظة المقام)، ومصدر كل رابطٍ وجولته
                   وسند اللسان مشتقةٌ هنا مستقلةً من الصف ومطابقةٌ لما وصفه المستهلك
وقياسان باستثناءٍ مسمّى (عيوب HFN، لا تُصلح في SARF): KEY_REACHABILITY («الحاق»، D10) وDHAT_COLUMN_REACHABILITY (روابط اللسان dhat_K فيها
فارغ فلا يبلغها سؤال الذات، D11). ثم حالاتٌ مسمّاة N01–N13 وإفساداتٌ P01–P08.
يحتاج SARF_HFN_V49_DIR وSARF_HFN_V50_DIR (ومجلّد api بجانبهما)؛ وبغيابها NOT_RUN (رمز 2)."""
import copy, csv, gzip, json, os, re, shutil, socket, subprocess, sys, tempfile, time, unicodedata, urllib.request
H = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
V49, V50 = os.environ.get('SARF_HFN_V49_DIR', ''), os.environ.get('SARF_HFN_V50_DIR', '')
API = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(V50 or '.'))), 'api')
if not (os.path.isdir(V49) and os.path.isdir(V50) and os.path.exists(os.path.join(API, 'server.py'))):
    print('NOT_RUN: SARF_HFN_V49_DIR وSARF_HFN_V50_DIR (ومجلّد api) غير متاحة'); sys.exit(2)
sys.path.insert(0, os.path.join(H, 'tools', 'ajnas'))
import consumer as AC
OUT = os.environ.get('SARF_TEST_OUT')
M50 = '7e5dc7ad6244339f5a260aca2833eb0979e348cdb78ef86784ece3b0301033fb'
M49 = 'ebeec9601d3fc8f929b6c0e7fd51d07bb4c765f26f71323d572429b735760086'
FAIL, RES = [], []


def check(name, ok, got=''):
    print(('PASS ' if ok else 'FAIL ') + name + ('' if ok else f' — {str(got)[:500]}'))
    RES.append(dict(name=name, ok=bool(ok), got=None if ok else str(got)[:3000]))
    if not ok:
        FAIL.append(name)


# ── المتوقَّع من الملف وحده ──
rows = list(csv.DictReader(open(os.path.join(V50, 'ahdath_ajnas.csv'), encoding='utf-8')))
events = list(csv.DictReader(open(os.path.join(V50, 'events.csv'), encoding='utf-8')))
MAN = json.load(open(os.path.join(V50, 'MANIFEST.json'), encoding='utf-8'))
ROOT_OF = {e['event_id']: e['root_K'] for e in events}
WD = {e['event_id'] for e in events if (e.get('event_review_v36') or '').startswith('WITHDRAWN')}
BY_ID = {r['link_id']: r for r in rows}
LIVE = {r['link_id'] for r in rows if r['event_id'] not in WD and r['event_withdrawn'] != 'True'}


# مستقلٌّ عن source_contract: اشتقاق المصدر والجولة وسند اللسان من الصف هنا
def toks(r):
    return {p.strip().split(' (')[0] for p in r['residual'].split('·') if p.strip()}


def x_source(r):
    return 'LISAN' if 'SOURCE_LISAN_NO_GENUS_BAB' in toks(r) else 'MUKHASSAS'


def x_round(r):
    m = r['method']
    return 'R3_LISAN' if m.startswith('R3 Lisan') else 'R2_WIDER' if m.startswith('R2 wider forms') else 'R2_KHILAF' if m.startswith('R2 KHILAF') else 'R1_MUKHASSAS'


def x_madda(r):
    m = re.match(r'^على ذكر صاحب لسان العرب، مادّة «([^»]+)» \(سطر (\d+) من نصّ OpenITI\)$', r['qawl'])
    return (m.group(1), m.group(2)) if m and m.group(2) == r['shahid_line'] else None


X_VAL = {'R1_MUKHASSAS': MAN['ahdath_ajnas']['agreement_yes_rows']['rate'], 'R2_WIDER': MAN['ahdath_ajnas_round2']['wider_forms']['yes_rows_wilson_low'],
         'R2_KHILAF': None, 'R3_LISAN': MAN['ahdath_ajnas_round3_lisan']['yes_rows_wilson_low']}
CITE = {'قَالَ': 'قال', 'رَوَى': 'روى', 'حَكَى': 'حكى', 'أَجَازَ': 'أجاز', 'زَعَمَ': 'زعم', 'أَنْشَدَ': 'أنشد', 'ذَكَرَ': 'ذكر', 'غَلِطَ': 'غلط'}


def x_meta(r):
    """قاعدة META_CITATION المعلنة مكتوبةً هنا مستقلةً: فعل الرابط من الأفعال المعلنة، وذاته فاعل صيغةٍ منه في الشاهد مباشرةً"""
    v, d = unicodedata.normalize('NFC', r['verb']), r['dhat'].strip()
    if v not in CITE or not d:
        return False
    return bool(re.search(r'(?:^|[\s(])(?:و|ف)?' + CITE[v] + r'(?:ه|ها|وا)?\s+(?:فيه\s+)?' + re.escape(d) + r'(?=[\s:،,.؛]|$)', r['shahid']))


META = {i for i in LIVE if x_meta(BY_ID[i])}
_DI = re.compile('[ؐ-ًؚ-ٰٟۖ-ۭـ]')
_HZ = str.maketrans({'أ': 'ء', 'إ': 'ء', 'آ': 'ء', 'ؤ': 'ء', 'ئ': 'ء', 'ٱ': 'ا', 'ى': 'ي'})


def policy_key(word):
    """السياسة المعلنة لمفتاح الذات، مكتوبةٌ هنا مستقلةً (كما في اختبار v48)"""
    w = unicodedata.normalize('NFC', (word or '').split(' ')[0])
    w = _DI.sub('', w).translate(_HZ)
    w = re.sub('[^ء-ي]', '', w)
    return w[2:] if w.startswith('ال') and len(w) >= 4 else w


_IX_EV, _IX_RT, _IX_KEY = {}, {}, {}
for _r in rows:
    _IX_EV.setdefault(_r['event_id'], set()).add(_r['link_id'])
    _IX_RT.setdefault(ROOT_OF.get(_r['event_id']), set()).add(_r['link_id'])
    for _p in _r['dhat_K'].split('·'):
        if _p:
            _IX_KEY.setdefault(_p, set()).add(_r['link_id'])


def expected(iface, q, role=None):
    """→ (الحي المتوقَّع، المستبعد المسموح، المستبعد الوصفي اللازم). المسحوب مسموحٌ استبعاده بأي دور (فهرسا الجذر والذات في الواجهة
    يُسقطان المسحوب قبل الجواب، وفهرس الحدث يعيده)؛ والاستبعاد الوصفي لازمٌ لكل صفٍّ منه في سؤاله بعد التصفية بالدور."""
    ids = set((_IX_EV if iface == 'event' else _IX_RT if iface == 'root' else _IX_KEY).get(q if iface != 'dhat' else policy_key(q), ()))
    wd = ids - LIVE
    if role:
        ids = {i for i in ids if BY_ID[i]['role'] == role}
    return (ids & LIVE) - META, wd | (ids & META), ids & META


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
        self.h = getattr(b, 'h', None)

    def call(self, iface, q, role=None):
        if self.mode == 'swap' and iface == 'event' and q in self.arg:
            q = self.arg[q]
        r = self.b.call(iface, q, role)
        links = list((r.get('payload') or {}).get('links') or [])
        res = list(r.get('residuals') or [])
        if self.mode == 'global':
            links = [BY_ID[i] for i in sorted(LIVE)[:40]]
        elif self.mode == 'extra' and q == self.arg[0]:
            links = links + [BY_ID[self.arg[1]]]
        elif self.mode == 'missing' and q == self.arg and links:
            links = links[1:]
        elif self.mode == 'altered' and links:
            links = [dict(links[0], shahid_line='0')] + links[1:]
        elif self.mode == 'reverse':
            links = links[::-1]
        elif self.mode == 'drop_lisan_mark' and links:
            links = [dict(l, residual=l['residual'].replace('SOURCE_LISAN_NO_GENUS_BAB', '')) for l in links]
        elif self.mode == 'res_0822':
            res = [x.replace('0.768', '0.822') for x in res]
        if r.get('payload') is not None:
            r = dict(r, payload=dict(r['payload'], links=links), residuals=res)
        return r


def run_queries(cons, queries):
    """→ {(iface,q,role): (ids, excluded_ids, rows, answer)}"""
    out = {}
    for iface, q, role in queries:
        a = cons.query(iface, q, role)
        out[(iface, q, role)] = ({l['link_id'] for l in a['links']}, {x['link_id'] for x in a['excluded']}, a['links'], a)
    return out


def preserve_errors(key, ids, rws, a):
    e = []
    if [r for r in rws if r != BY_ID.get(r['link_id'])]:
        e.append('ROW_NOT_FILE_ROW')
    if rws and not ('AJNAS_YES_ROW_AGREEMENT_0.768_BELOW_GATE_0.78' in a['residuals'] and any(n.startswith('RESIDUAL_SCOPE_NOTE') for n in a['notes'])):
        e.append('RAW_RESIDUAL_OR_SCOPE_NOTE')
    if any(x_source(BY_ID[i]) == 'LISAN' for i in ids) and not any(x.startswith('SOME_LINKS_FROM_LISAN') for x in a['residuals']):
        e.append('LISAN_API_RESIDUAL_MISSING')
    for i in ids:
        r, m = BY_ID[i], a['link_meta'].get(i) or {}
        if m.get('source') != x_source(r) or m.get('round') != x_round(r) or (m.get('measurement') or {}).get('value') != X_VAL[x_round(r)]:
            e.append('SOURCE_ROUND_MEASURE'); break
        if x_source(r) == 'LISAN' and ((m.get('lisan') or {}).get('madda'), (m.get('lisan') or {}).get('line')) != (x_madda(r) or (None, None)):
            e.append('LISAN_MADDA_LINE'); break
        if ('LISAN_GENERIC_HUMAN_DHAT' in toks(r)) != ('GENERIC_HUMAN_NOT_GENUS' in m.get('flags', [])) or \
                (bool({'WIDER_FORM', 'ROUND2_WIDER_FORMS'} & toks(r))) != ('WIDER_FORM_NO_GENERALIZATION' in m.get('flags', [])):
            e.append('CONSTRAINT_FLAGS'); break
    return e


def judge(res, res_http=None, audit=None):
    v = dict(EQUIVALENCE=None, SOUNDNESS=[], COMPLETENESS=[], EXCLUSION=[], PRESERVATION=[])
    for key, (ids, exc, rws, a) in res.items():
        live_exp, exc_exp, meta_exp = expected(*key)
        if ids - live_exp:
            v['SOUNDNESS'].append(dict(query=key, extra=sorted(ids - live_exp)[:5]))
        if live_exp - ids:
            v['COMPLETENESS'].append(dict(query=key, missing=sorted(live_exp - ids)[:5]))
        bad_ex = [x for x in a['excluded'] if not ((x['link_id'] not in LIVE and x['reason'].startswith('EVENT_WITHDRAWN'))
                                                  or (x['link_id'] in META and x['reason'].startswith('META_CITATION') and x.get('evidence')))]
        if ids & (exc_exp | (set(BY_ID) - LIVE)) or bad_ex or not exc <= exc_exp or not meta_exp <= exc:
            v['EXCLUSION'].append(dict(query=key, excluded=sorted(exc)[:5], expected=sorted(exc_exp)[:5]))
        pe = preserve_errors(key, ids, rws, a)
        if pe:
            v['PRESERVATION'].append(dict(query=key, errors=pe))
    if res_http is not None:
        nk = (None, None, None, dict(residuals=None))
        v['EQUIVALENCE'] = [k for k in res if (res[k][0], res[k][1], res[k][3]['residuals']) != (res_http.get(k, nk)[0], res_http.get(k, nk)[1], res_http.get(k, nk)[3]['residuals'])
                            or json.loads(json.dumps(res[k][2], ensure_ascii=False)) != res_http.get(k, nk)[2]]
    return v


d50 = AC.DirectBackend(V50, API)
C = AC.AjnasConsumer(d50, 'HFN_release_v50', M50, WD)
roots = sorted({e['root_K'] for e in events})
words = sorted({w for r in rows for w in r['dhat'].split('·') if w.strip()})
keys = sorted({p for r in rows for p in r['dhat_K'].split('·') if p})
ROLES = ['فاعل', 'محلّ', 'آلة', 'مكان', 'زمان', 'مصدر']
Q = [('event', e['event_id'], None) for e in events] + [('root', r, None) for r in roots] + [('dhat', w, None) for w in words]
Q += [('dhat', k, None) for k in keys if k not in set(words)]
ev_with = sorted({r['event_id'] for r in rows})
Q += [('dhat', w, ro) for w in words for ro in ROLES] + [('event', e, ro) for e in ev_with for ro in ROLES] + [('root', r, ro) for r in sorted({ROOT_OF[r['event_id']] for r in rows}) for ro in ROLES]
srv, url = serve(V50)
D10, D11 = [], {}
try:
    CH = AC.AjnasConsumer(AC.HttpBackend(url, API), 'HFN_release_v50', M50, WD, release_dir=V50)
    t0 = time.time()
    res = run_queries(C, Q)
    res_h = run_queries(CH, Q)
    v = judge(res, res_h)
    n = len(Q)
    check(f'1 EQUIVALENCE: {n} سؤالاً، المباشر = HTTP (الحي والمستبعد والصفوف وتحفّظات الواجهة)', not v['EQUIVALENCE'], v['EQUIVALENCE'][:3])
    check('2 SOUNDNESS: لا صفّ خارج متوقَّع سؤاله (حدث، جذر، ذات، ومع الدور)', not v['SOUNDNESS'], v['SOUNDNESS'][:3])
    check('3 COMPLETENESS: كل متوقَّعٍ بالفهرس المعلن معاد لسؤاله', not v['COMPLETENESS'], v['COMPLETENESS'][:3])
    check('4 EXCLUSION: المستبعد = المسحوب ∪ الاستشهاد الوصفي، كلٌّ بسببه ودليله، ولا شيء منه حيّ؛ وسجلّ التدقيق يحوي المسحوب كله والوصفي كله',
          not v['EXCLUSION'] and {x['link_id'] for x in C.audit_log} == (set(BY_ID) - LIVE) | META, v['EXCLUSION'][:3])
    check('5 PRESERVATION: الصف = صفّ الملف؛ والتحفّظ الخام 0.768 محفوظ ومعه ملاحظة المقام؛ وتحفّظ اللسان؛ والمصدر والجولة والقياس وسند اللسان والقيود '
          'مشتقةً مستقلةً = وصف المستهلك', not v['PRESERVATION'], v['PRESERVATION'][:3])
    D10 = [dict(query=k, expected_by_stored_key=sorted(i for i in LIVE - META if k in BY_ID[i]['dhat_K'].split('·')), actual=sorted(res[('dhat', k, None)][0]),
                key_after_policy=policy_key(k))
           for k in keys if {i for i in LIVE - META if k in BY_ID[i]['dhat_K'].split('·')} - res[('dhat', k, None)][0]]
    check('KEY_REACHABILITY (قياس، استثناءٌ مسمّى): المفاتيح المخزَّنة التي لا تسترجع صفوفها بسؤالها = «الحاق» وحده (D10 في HFN، لم يُصلح في v50)',
          [x['query'] for x in D10] == ['الحاق'], D10)
    RES[-1]['measured'] = D10
    unreach = [i for i in sorted(LIVE - META) if BY_ID[i]['dhat'].strip() and i not in res[('dhat', BY_ID[i]['dhat'].split('·')[0], None)][0]]
    by_src = {}
    for i in unreach:
        by_src.setdefault(x_source(BY_ID[i]), []).append(i)
    lis_live = sorted(i for i in LIVE - META if x_source(BY_ID[i]) == 'LISAN')
    D11 = dict(unreachable_by_own_dhat_word={s: len(x) for s, x in by_src.items()}, lisan_live=len(lis_live),
               lisan_dhat_K_empty=sum(1 for i in lis_live if not BY_ID[i]['dhat_K']), mukhassas_examples=by_src.get('MUKHASSAS', [])[:20],
               lisan_examples=by_src.get('LISAN', [])[:10])
    check('DHAT_COLUMN_REACHABILITY (قياس، استثناءٌ مسمّى D11 في HFN): روابط اللسان الحية كلها لا يبلغها سؤال ذاتها لأن dhat_K فارغ؛ '
          'وتبقى مبلوغةً بالحدث والجذر', sorted(by_src.get('LISAN', [])) == lis_live and D11['lisan_dhat_K_empty'] == len(lis_live)
          and all(i in res[('event', BY_ID[i]['event_id'], None)][0] for i in lis_live), D11)
    RES[-1]['measured'] = D11
    # ── حالاتٌ مسمّاة ──
    a = C.query('event', 'HFN-E-7eb27213d3')
    m = a['link_meta'].get('HFN-AJ-697a1108b3') or {}
    check('N01 HFN-E-7eb27213d3: رابط لسانٍ HFN-AJ-697a1108b3، مادة «فشج» سطر 40447، الجولة R3 وقياسها 0.822 (1182/1403)، بلا حقول مخصّص',
          m.get('source') == 'LISAN' and m['lisan'] == dict(madda='فشج', line='40447', status='OK') and m['round'] == 'R3_LISAN'
          and m['measurement']['value'] == 0.822 and m['measurement']['rows'] == 1403 and not BY_ID['HFN-AJ-697a1108b3']['mukhassas_bab']
          and any(x.startswith('SOME_LINKS_FROM_LISAN') for x in a['residuals']), (m, a['residuals']))
    a = C.query('root', 'حلب', 'محلّ')
    check('N02 الجذر «حلب» بالدور محلّ: كل المعاد محلّ، ويساوي المتوقَّع؛ والمحلّ دورٌ دلالي في الرابط لا مفعولٌ نحوي (لا حقل نحوي)',
          a['links'] and {l['role'] for l in a['links']} == {'محلّ'} and {l['link_id'] for l in a['links']} == expected('root', 'حلب', 'محلّ')[0]
          and not any(k in l for l in a['links'] for k in ('subject', 'object', 'فاعل_نحوي')), len(a['links']))
    a1, a2 = C.query('dhat', 'الناقة', 'فاعل'), C.query('dhat', 'الناقة', 'محلّ')
    lis_naqa = sorted(i for i in LIVE - META if x_source(BY_ID[i]) == 'LISAN' and BY_ID[i]['dhat'] == 'الناقة')
    check('N03 «الناقة» بالدورين: كلٌّ بدوره ومتوقَّعه، ولا تقاطع؛ وروابط اللسان لـ«الناقة» غير مبلوغة بالذات (D11) وهي مسجّلة',
          {l['role'] for l in a1['links']} == {'فاعل'} and {l['role'] for l in a2['links']} == {'محلّ'}
          and {l['link_id'] for l in a1['links']} == expected('dhat', 'الناقة', 'فاعل')[0] and not ({l['link_id'] for l in a1['links']} & {l['link_id'] for l in a2['links']})
          and lis_naqa and not set(lis_naqa) & ({l['link_id'] for l in a1['links']} | {l['link_id'] for l in a2['links']}), (len(a1['links']), len(a2['links']), len(lis_naqa)))
    a = C.query('dhat', 'ققققق')
    check('N04 جوابٌ فارغ: NO_RESULT (not a negative)، وتحفّظ الواجهة NO_AJNAS_LINK، ولا ملاحظة مقام', a['status'].startswith('NO_RESULT') and not a['links']
          and any('NO_AJNAS_LINK' in x for x in a['residuals']) and not a['notes'], a['status'])
    wev = sorted({BY_ID[i]['event_id'] for i in set(BY_ID) - LIVE})
    a = C.query('event', wev[0])
    check(f'N05 حدثٌ مسحوب ({wev[0]}): لا حيّ، والمستبعد كله بسببه، وCONSUMER_EXCLUDED_WITHDRAWN في التحفّظ', not a['links'] and a['excluded']
          and all(x['reason'].startswith('EVENT_WITHDRAWN') for x in a['excluded']) and any(x.startswith('CONSUMER_EXCLUDED_WITHDRAWN') for x in a['residuals']), a)
    hum = next(i for i in sorted(LIVE - META) if 'LISAN_GENERIC_HUMAN_DHAT' in toks(BY_ID[i]) and BY_ID[i]['dhat'] == 'الرجل')
    a = C.query('event', BY_ID[hum]['event_id'])
    check(f'N06 الرجل/فلان ({hum}): القيد GENERIC_HUMAN_NOT_GENUS ظاهرٌ في الوصف، والعلامة في التحفّظ الخام', 'GENERIC_HUMAN_NOT_GENUS' in a['link_meta'][hum]['flags']
          and 'LISAN_GENERIC_HUMAN_DHAT' in a['links'][[l['link_id'] for l in a['links']].index(hum)]['residual'], a['link_meta'].get(hum))
    wid = next(i for i in sorted(LIVE - META) if 'WIDER_FORM' in toks(BY_ID[i]))
    a = C.query('event', BY_ID[wid]['event_id'])
    check(f'N07 WIDER_FORM ({wid}): القيد WIDER_FORM_NO_GENERALIZATION ظاهر', 'WIDER_FORM_NO_GENERALIZATION' in a['link_meta'][wid]['flags'], a['link_meta'].get(wid))
    check('N08 «الحاق»: حالته في v50 — العيب D10 قائم (لم يُصلح)، ويُعلن استثناءً مسمّى', any(x['query'] == 'الحاق' for x in D10), D10)
    errs = []
    for exp_rel, exp_m, back in (('HFN_release_v48', M50, d50), ('HFN_release_v50', M49, d50)):
        try:
            AC.AjnasConsumer(back, exp_rel, exp_m, WD).query('event', ev_with[0]); errs.append('accepted')
        except AC.AjnasIdentityError as e:
            errs.append('HFN_IDENTITY_MISMATCH' in str(e))
    s49, u49 = serve(V49)
    try:
        try:
            AC.AjnasConsumer(AC.HttpBackend(u49, API), 'HFN_release_v50', M50, WD, release_dir=V50).query('event', ev_with[0]); errs.append('accepted')
        except AC.AjnasIdentityError as e:
            errs.append('HFN_IDENTITY_MISMATCH' in str(e))
    finally:
        s49.kill()
    check('N09 هويةٌ أو بصمةٌ غير المطلوبة: اسم إصدارٍ آخر، وبصمة v49 على v50، وخادم v49 لمستهلكٍ يطلب v50 — يُرفض كلٌّ بـ HFN_IDENTITY_MISMATCH',
          errs == [True, True, True], errs)
    mixed_root = next(r for r in sorted(_IX_RT) if r and {x_source(BY_ID[i]) for i in _IX_RT[r] & (LIVE - META)} == {'LISAN', 'MUKHASSAS'})
    a = C.query('root', mixed_root)
    srcs = {a['link_meta'][l['link_id']]['source'] for l in a['links']}
    check(f'N10 جوابٌ مختلط (الجذر «{mixed_root}»): مصدر كل رابطٍ وجولته وقياسه بصفّه هو، لا بالجواب؛ والتحفّظان الخامّان (0.768 واللسان) وملاحظة المقام معاً',
          srcs == {'LISAN', 'MUKHASSAS'} and all(a['link_meta'][l['link_id']]['source'] == x_source(l) and a['link_meta'][l['link_id']]['round'] == x_round(l) for l in a['links'])
          and any(x.startswith('SOME_LINKS_FROM_LISAN') for x in a['residuals']) and 'AJNAS_YES_ROW_AGREEMENT_0.768_BELOW_GATE_0.78' in a['residuals'] and a['notes'],
          (srcs, a['residuals']))
    cr = AC.AjnasConsumer(Faulty(d50, 'reverse'), 'HFN_release_v50', M50, WD, release_dir=V50)
    big = max(ev_with, key=lambda e: len(_IX_EV[e] & LIVE))
    a, b = C.query('event', big), cr.query('event', big)
    check(f'N11 ترتيب الأدلة لا يرفع مرتبة (عكس ترتيب جواب {big}، {len(a["links"])} رابطاً): المجموعة والأوصاف والمراتب نفسها، وكلها CANDIDATE، ولا حقل موضع',
          {l['link_id'] for l in a['links']} == {l['link_id'] for l in b['links']} and a['link_meta'] == b['link_meta']
          and {l['rank'] for l in a['links'] + b['links']} == {'CANDIDATE'} and not any(k in a for k in ('first', 'best', 'selected')), big)
    a = C.query('dhat', 'الْنَّاقَةُ مثلاً')
    check('N12 مفاتيح البحث: السؤال الأصلي محفوظ، والتحويلات مسجّلة خطوةً خطوة (الكلمة الأولى، K، حذف «ال»)، والمفتاح = السياسة المستقلة',
          a['query'] == 'الْنَّاقَةُ مثلاً' and a['transforms'][-1]['value'] == policy_key('الْنَّاقَةُ مثلاً') and len(a['transforms']) >= 3, a['transforms'])
    # N13 بياناتٌ معدّلة مع تحديث بصمتها في MANIFEST: البصمة المثبّتة لـ MANIFEST تتغير فيُرفض
    tmp = tempfile.mkdtemp(prefix='v50_tamper_')
    try:
        rel2 = os.path.join(tmp, 'release_v50')
        shutil.copytree(V50, rel2)
        p = os.path.join(rel2, 'ahdath_ajnas.csv')
        txt = open(p, encoding='utf-8').read().replace('فشج', 'فشخ', 1)
        open(p, 'w', encoding='utf-8').write(txt)
        import hashlib
        mm = json.load(open(os.path.join(rel2, 'MANIFEST.json'), encoding='utf-8'))
        fe = mm['files']['ahdath_ajnas.csv']
        newsha = hashlib.sha256(open(p, 'rb').read()).hexdigest()
        if isinstance(fe, dict):
            fe.update({k: newsha for k in fe if 'sha' in k})
        else:
            mm['files']['ahdath_ajnas.csv'] = newsha
        json.dump(mm, open(os.path.join(rel2, 'MANIFEST.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        try:
            AC.AjnasConsumer(AC.DirectBackend(rel2, API), 'HFN_release_v50', M50, WD).query('event', 'HFN-E-7eb27213d3'); r13 = 'accepted'
        except AC.AjnasIdentityError as e:
            r13 = 'HFN_IDENTITY_MISMATCH' in str(e)
        except Exception as e:
            r13 = f'OTHER_ERROR:{type(e).__name__}:{e}'
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    check('N13 صفٌّ معدَّل في المورد مع تحديث بصمته في MANIFEST: بصمة MANIFEST المثبّتة تتغير، فيُرفض بـ HFN_IDENTITY_MISMATCH', r13 is True, r13)
    # ── الإفسادات: كل واحدٍ يُسقط حكمه، على عيّنةٍ ثابتة ──
    e1, e2 = ev_with[0], ev_with[1]
    sample = [('event', e1, None), ('event', e2, None)] + [q for q in Q if q[0] == 'event' and q[2] is None and q[1] in set(ev_with[2:])][:300] \
        + [('root', 'حلب', None), ('dhat', 'الناقة', 'فاعل'), ('event', 'HFN-E-7eb27213d3', None), ('root', mixed_root, None)]

    def fault(mode, arg=None):
        return run_queries(AC.AjnasConsumer(Faulty(d50, mode, arg), 'HFN_release_v50', M50, WD, release_dir=V50), sample)
    r = fault('swap', {e1: e2, e2: e1})
    j = judge(r)
    union_same = set().union(*[x[0] for x in r.values()]) == set().union(*[x[0] for x in run_queries(C, sample).values()])
    check('P01 تبديل جوابي حدثين مع بقاء الاتحاد صحيحاً: الاتحاد لا يكشفه، والفحص لكل سؤال يكشفه', union_same and j['SOUNDNESS'], union_same)
    check('P02 إعادة المجموعة العامة لكل سؤال: يسقط SOUNDNESS', bool(judge(fault('global'))['SOUNDNESS']))
    extra_id = next(i for i in sorted(LIVE - META) if BY_ID[i]['event_id'] != e1)
    check('P03 صفٌّ زائد في جواب حدث: يسقط SOUNDNESS', any(x['query'][1] == e1 for x in judge(fault('extra', (e1, extra_id)))['SOUNDNESS']))
    check('P04 صفٌّ ناقص: يسقط COMPLETENESS', any(x['query'][1] == e1 for x in judge(fault('missing', e1))['COMPLETENESS']))
    craw = AC.AjnasConsumer(d50, 'HFN_release_v50', M50, WD, release_dir=V50)
    oq = craw.query
    craw.query = lambda iface, q, role=None: oq(iface, q, None)
    check('P05 إسقاط التصفية بالدور: يسقط SOUNDNESS', bool(judge(run_queries(craw, [('dhat', 'الناقة', 'فاعل'), ('root', 'حلب', 'محلّ')]))['SOUNDNESS']))
    sA, uA = serve(V50)
    try:
        cd = AC.AjnasConsumer(Faulty(d50, 'swap', {e1: e2, e2: e1}), 'HFN_release_v50', M50, WD, release_dir=V50)
        ch = AC.AjnasConsumer(Faulty(AC.HttpBackend(uA, API), 'swap', {e1: e2, e2: e1}), 'HFN_release_v50', M50, WD, release_dir=V50)
        s2 = [('event', e1, None), ('event', e2, None)]
        j = judge(run_queries(cd, s2), run_queries(ch, s2))
    finally:
        sA.kill()
    check('P06 المباشر وHTTP يتفقان على جوابٍ خاطئ: التكافؤ يجتاز، والصحة لكل سؤال تسقط', not j['EQUIVALENCE'] and j['SOUNDNESS'], (j['EQUIVALENCE'], j['SOUNDNESS'][:1]))
    check('P07 صفٌّ معاد بحقلٍ محرَّف (رقم سطر الشاهد): يسقط PRESERVATION', bool(judge(fault('altered'))['PRESERVATION']))
    check('P08 علامة اللسان منزوعة من صفوف الجواب: يسقط PRESERVATION', bool(judge(fault('drop_lisan_mark'))['PRESERVATION']))
    check('P09 تحفّظ الواجهة 0.768 مستبدَلٌ بـ 0.822 للجميع: يسقط PRESERVATION', bool(judge(fault('res_0822'))['PRESERVATION']))
    cm = AC.AjnasConsumer(d50, 'HFN_release_v50', M50, WD, meta_citation_policy='NONE', release_dir=V50)
    check('P10 إيقاف الاستبعاد الوصفي: يسقط EXCLUSION (رابط «قال سيبويه…» حيّ)', bool(judge(run_queries(cm, [('event', BY_ID[i]['event_id'], None) for i in sorted(META)]))['EXCLUSION']))
    if OUT:
        os.makedirs(OUT, exist_ok=True)
        with gzip.open(os.path.join(OUT, 'api_per_query_v50.tsv.gz'), 'wt', encoding='utf-8') as f:
            f.write('interface\tquery\trole\texpected_live\treturned_direct\treturned_http\texcluded\tsound\tcomplete\n')
            for k in Q:
                le = expected(*k)[0]; ids = res[k][0]
                f.write('\t'.join([k[0], k[1], k[2] or '', ','.join(sorted(le)), ','.join(sorted(ids)), ','.join(sorted(res_h[k][0])),
                                   ','.join(sorted(res[k][1])), str(not (ids - le)), str(not (le - ids))]) + '\n')
        json.dump(dict(results=RES, queries=n, verdicts={k: (len(x) if isinstance(x, list) else x) for k, x in v.items()}, key_reachability_D10=D10,
                       dhat_column_reachability_D11=D11, meta_citation_excluded=sorted(META), audit_log=C.audit_log, seconds=round(time.time() - t0, 1)),
                  open(os.path.join(OUT, 'test_v50_api_per_query.results.json'), 'w'), ensure_ascii=False, indent=1)
finally:
    srv.kill()
print(f'CHECKS pass={len(RES) - len(FAIL)} fail={len(FAIL)} total={len(RES)}')
print('ALL OK' if not FAIL else f'FAILED {len(FAIL)}: {FAIL}')
sys.exit(1 if FAIL else 0)
