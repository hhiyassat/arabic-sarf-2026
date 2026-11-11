# -*- coding: utf-8 -*-
"""روابط ahdath_ajnas: الملف والواجهة المباشرة وخادم HTTP ومستهلك SARF (SARF_HFN_V48_VALIDATION_COMPLETION_02 §٧ و§٨).
- كل صفٍّ في الملف تعيده الواجهة مرةً واحدة بحقوله كلها؛ واتحاد الأجوبة يساوي الملف.
- الاستهلاك الحي (المستهلك) لا يحمل رابط حدثٍ مسحوب في أي واجهة (حدث، جذر، ذات)، والمستبعد في سجلّ تدقيقٍ بسببه.
- HTTP يطابق الاستدعاء المباشر في كل سؤال (الأحداث والجذور ومفاتيح الذوات كلها).
- لكل واجهة: موجب، بلا نتيجة، مدخلٌ غير صالح، تعدّد أحداث، تصفية بالدور، حدثٌ مسحوب، اختلاف إصدار.
يحتاج SARF_HFN_V47_DIR وSARF_HFN_V48_DIR (وواجهة HFN في ../../api من مجلّد v48)؛ وبغيابهما NOT_RUN (رمز 2)."""
import csv, json, os, socket, subprocess, sys, time, urllib.parse, urllib.request
from collections import Counter, defaultdict
H = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
V47, V48 = os.environ.get('SARF_HFN_V47_DIR', ''), os.environ.get('SARF_HFN_V48_DIR', '')
API = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(V48 or '.'))), 'api')
if not (os.path.isdir(V47) and os.path.isdir(V48) and os.path.exists(os.path.join(API, 'server.py'))):
    print('NOT_RUN: SARF_HFN_V47_DIR وSARF_HFN_V48_DIR (ومجلّد api بجانب release) غير متاحة')
    sys.exit(2)
sys.path.insert(0, os.path.join(H, 'tools', 'ajnas'))
import consumer as AC
OUT = os.environ.get('SARF_AJNAS_TEST_OUT')
M48 = '6cd85dc63b1e920420b09e6d4be748188e37cfc32fe780a05fa2568534119a75'
FAIL, RES = [], []


def check(name, ok, got=''):
    print(('PASS ' if ok else 'FAIL ') + name + ('' if ok else f' — {str(got)[:500]}'))
    RES.append(dict(name=name, ok=bool(ok), got=None if ok else str(got)[:3000]))
    if not ok:
        FAIL.append(name)


def free_port():
    s = socket.socket(); s.bind(('127.0.0.1', 0)); p = s.getsockname()[1]; s.close(); return p


def serve(rel):
    port = free_port()
    p = subprocess.Popen([sys.executable, '-s', '-B', 'server.py', '--release', rel, '--port', str(port)], cwd=API,
                         stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, env={k: v for k, v in os.environ.items() if k != 'HFN_RELEASE'})
    for _ in range(300):
        try:
            urllib.request.urlopen(f'http://127.0.0.1:{port}/stats', timeout=2); return p, f'http://127.0.0.1:{port}'
        except Exception:
            time.sleep(0.2)
    p.kill(); raise RuntimeError('server did not start: ' + p.stderr.read().decode()[-400:])


rows = list(csv.DictReader(open(os.path.join(V48, 'ahdath_ajnas.csv'), encoding='utf-8')))
events = list(csv.DictReader(open(os.path.join(V48, 'events.csv'), encoding='utf-8')))
WD = {e['event_id'] for e in events if (e.get('event_review_v36') or '').startswith('WITHDRAWN')}
wd_rows = [r for r in rows if r['event_withdrawn'] == 'True' or r['event_id'] in WD]
live_rows = {r['link_id']: r for r in rows if r not in wd_rows}
by_id = {r['link_id']: r for r in rows}
check('F01 الملف: 11943 صفّاً بمعرّفاتٍ فريدة، والمسحوب 5 صفوف لحدثين',
      len(rows) == 11943 and len(by_id) == len(rows) and len(wd_rows) == 5 and len({r['event_id'] for r in wd_rows}) == 2,
      (len(rows), len(by_id), len(wd_rows)))
d48 = AC.DirectBackend(V48, API)
C = AC.AjnasConsumer(d48, 'HFN_release_v48', M48, WD)
srv48, url48 = serve(V48)
srv47, url47 = serve(V47)
try:
    h48 = AC.HttpBackend(url48, API)
    CH = AC.AjnasConsumer(h48, 'HFN_release_v48', M48, WD)
    stats = dict(direct_http_compared=0, mismatches=[], residual_dropped=[])

    def both(iface, q, role=None):
        a, b = C.query(iface, q, role), CH.query(iface, q, role)
        stats['direct_http_compared'] += 1
        if json.loads(json.dumps(a, ensure_ascii=False)) != b:
            stats['mismatches'].append((iface, q, role))
        raw = d48.call(iface, q, role) if isinstance(q, str) and q.strip() else None
        if raw and not set(raw.get('residuals') or []) <= set(a['residuals']):
            stats['residual_dropped'].append((iface, q))
        return a, raw

    # ── الحدث: كل الأحداث ──
    seen_raw, seen_live = Counter(), Counter()
    field_mismatch = []
    for e in events:
        a, raw = both('event', e['event_id'])
        for l in (raw.get('payload') or {}).get('links') or []:
            seen_raw[l['link_id']] += 1
            if l != by_id.get(l['link_id']):
                field_mismatch.append(l['link_id'])
        for l in a['links']:
            seen_live[l['link_id']] += 1
    check('E01 ajnas_for_event (الواجهة الخام): كل صفٍّ يُعاد مرةً واحدة بحقوله كلها، والاتحاد يساوي الملف',
          set(seen_raw) == set(by_id) and set(seen_raw.values()) == {1} and not field_mismatch, (len(seen_raw), field_mismatch[:3]))
    check('E02 المستهلك الحي عبر الأحداث: الاتحاد = الملف ناقص المسحوب الخمسة، بلا تكرار',
          set(seen_live) == set(live_rows) and set(seen_live.values()) == {1}, (len(seen_live), len(live_rows)))
    ev_log = [x for x in C.audit_log if x['interface'] == 'event']
    check('E03 سجلّ التدقيق: الروابط الخمسة المستبعدة بمعرّفها وحدثها وسببها',
          sorted(x['link_id'] for x in ev_log) == sorted(r['link_id'] for r in wd_rows) and all('EVENT_WITHDRAWN' in x['reason'] for x in ev_log), ev_log)
    raw_wd = d48.call('event', wd_rows[0]['event_id'])
    check('E04 عيب HFN مسجَّل (D1): الواجهة الخام تعيد روابط الحدث المسحوب بتحفّظ، والمستهلك يحجبها',
          any(l['event_withdrawn'] == 'True' for l in raw_wd['payload']['links']) and not C.query('event', wd_rows[0]['event_id'])['links'],
          raw_wd['residuals'])
    # ── الجذر: كل الجذور ──
    roots = sorted({e['root_K'] for e in events})
    seen_root, wd_in_root = Counter(), []
    for r in roots:
        a, raw = both('root', r)
        for l in a['links']:
            seen_root[l['link_id']] += 1
        wd_in_root += [l['link_id'] for l in a['links'] if l['link_id'] not in live_rows]
    check('R01 ajnas_for_root عبر الجذور كلها: الاتحاد = الملف ناقص المسحوب، ولا رابط مسحوب حي',
          set(seen_root) == set(live_rows) and not wd_in_root, (len(seen_root), wd_in_root[:3]))
    # ── الذات: كل مفاتيح الذوات ──
    keys = sorted({p for r in rows for p in r['dhat_K'].split('·') if p})
    words = sorted({w for r in rows for w in r['dhat'].split('·') if w.strip()})
    seen_dhat, wd_in_dhat, by_key = set(), [], {}
    for q in words + keys:
        a, raw = both('dhat', q)
        got = {l['link_id'] for l in a['links']}
        seen_dhat |= got
        if q in keys:
            by_key[q] = got
        wd_in_dhat += [l['link_id'] for l in a['links'] if l['link_id'] not in live_rows]
    miss = set(live_rows) - seen_dhat
    check('D01 events_for_dhat بألفاظ الذوات المكتوبة ومفاتيحها: كل رابطٍ حيّ يُسترجع، ولا رابط مسحوب حي',
          not miss and not wd_in_dhat, (len(miss), sorted(miss)[:5], wd_in_dhat[:3]))
    own = {k: {l for l in live_rows if k in live_rows[l]['dhat_K'].split('·')} for k in keys}
    nonidem = sorted(k for k in keys if own[k] and not (own[k] & by_key[k]))
    check('D02 (قياس) مفاتيح dhat_K التي لا تسترجع صفوفها إن سُئل بها مباشرةً — حذف «ال» في الواجهة لا يرتدّ على مفتاحها: '
          'تُسجَّل ولا تُصلح هنا', True, nonidem)
    RES[-1]['measured'] = nonidem
    check('H01 HTTP يطابق الاستدعاء المباشر في كل سؤال (الهوية والتحفّظات والروابط والمستبعد)',
          stats['direct_http_compared'] > 20000 and not stats['mismatches'], (stats['direct_http_compared'], stats['mismatches'][:5]))
    check('H02 لا يُسقط المستهلك أي تحفّظٍ أعادته الواجهة', not stats['residual_dropped'], stats['residual_dropped'][:5])
    # ── حالات كل واجهة ──
    halab = [r for r in live_rows.values() if next(e for e in events if e['event_id'] == r['event_id'])['root_K'] == 'حلب']
    a = C.query('root', 'حلب')
    check('P01 حلب (جذر): عدد الروابط يُعاد حسابه من الملف ويساوي الجواب، وتعدّد الأحداث محفوظ بلا اختيار',
          len(a['links']) == len(halab) == 13 and a['events'] == sorted({r['event_id'] for r in halab}) and 'chosen' not in a,
          (len(a['links']), len(halab), a['events']))
    fars = [r for r in live_rows.values() if 'فرس' in r['dhat_K'].split('·') and r['role'] == 'فاعل']
    a = C.query('dhat', 'الفرس', 'فاعل')
    check('P02 «الفرس» فاعلاً (ذات): يساوي حساب الملف (108)، وتحويلات المفتاح محفوظة بالسؤال الأصلي',
          len(a['links']) == len(fars) == 108 and a['transforms'][0]['value'] == 'الفرس' and a['transforms'][-1]['value'] == 'فرس',
          (len(a['links']), len(fars), a['transforms']))
    a_all = C.query('dhat', 'الفرس')
    check('P03 التصفية بالدور جزءٌ من غير المصفّى، وكل أدواره من المجموعة الدلالية الستّ',
          {l['link_id'] for l in a['links']} <= {l['link_id'] for l in a_all['links']} and
          {l['role'] for l in a_all['links']} <= {'فاعل', 'محلّ', 'آلة', 'مكان', 'زمان', 'مصدر'}, Counter(l['role'] for l in a_all['links']))
    ev_multi = max(Counter(r['event_id'] for r in live_rows.values()).items(), key=lambda x: x[1])[0]
    a = C.query('event', ev_multi, 'محلّ')
    check('P04 تصفية الدور على الحدث والجذر في المستهلك (تحويلٌ معلن): كل المعاد بالدور المطلوب',
          all(l['role'] == 'محلّ' for l in a['links']) and all(l['role'] == 'محلّ' for l in C.query('root', 'حلب', 'محلّ')['links']))
    nolink = next(e['event_id'] for e in events if e['event_id'] not in {r['event_id'] for r in rows} and e['event_id'] not in WD)
    for iface, q in (('event', nolink), ('root', 'ززز'), ('dhat', 'ززززز')):
        a = C.query(iface, q)
        check(f'N01 {iface} بلا نتيجة: لا روابط، والحالة «ليس نفياً» أو «غير مخدوم» بتحفّظها، لا نفي',
              not a['links'] and a['status'] in ('NO_RESULT (not a negative)', 'NOT_SERVED') and a['residuals'], a)
    for iface in ('event', 'root', 'dhat'):
        for bad in ('', '   ', None):
            a = C.query(iface, bad)
            check(f'V01 {iface} مدخلٌ غير صالح {bad!r}: INVALID_QUERY دون سؤال الواجهة', a['status'] == 'INVALID_QUERY' and not a['links'], a)
    a = C.query('event', 'HFN-E-ffffffffff')
    check('V02 حدثٌ غير موجود: EVENT_NOT_IN_RELEASE محفوظ، لا روابط', a['status'] == 'NOT_SERVED' and 'EVENT_NOT_IN_RELEASE' in a['residuals'], a)
    for r in wd_rows:
        root = next(e for e in events if e['event_id'] == r['event_id'])['root_K']
        for iface, q in (('event', r['event_id']), ('root', root), ('dhat', r['dhat_K'].split('·')[0])):
            a = C.query(iface, q)
            check(f'W01 {r["link_id"]} عبر {iface}: لا يظهر حيّاً', r['link_id'] not in {l['link_id'] for l in a['links']}, a['links'][:1])
    some = C.query('event', ev_multi)
    check('B01 كل رابطٍ حيّ يحمل بابه وسنده وسطر شاهده، وتحفّظ «الرابط لمعنى بابه» حاضر، والجواب مرشّح لا حقيقة',
          all(l['mukhassas_bab'] and l['mukhassas_sid'] and l['shahid_line'] for l in some['links'])
          and any('BAB_SENSE' in x for x in some['residuals']) and some['rank'] == 'CANDIDATE' and some['is_fact'] is False, some['residuals'])
    check('B02 المستهلك لا يضيف حقلاً إلى صفّ الرابط (لا «فاعل نحوي»، ولا تعدية)', all(l == by_id[l['link_id']] for l in some['links']))
    # ── اختلاف الإصدار ──
    for name, mk in (('مباشر v47', lambda: AC.AjnasConsumer(AC.DirectBackend(V47, API), 'HFN_release_v48', M48)),
                     ('HTTP v47', lambda: AC.AjnasConsumer(AC.HttpBackend(url47, API), 'HFN_release_v48', M48))):
        try:
            mk(); msg = 'لم يُرفض'
        except AC.AjnasIdentityError as e:
            msg = str(e)
        check(f'M01 مستهلكٌ يطلب v48 وخدمة {name}: HFN_IDENTITY_MISMATCH', msg.startswith('HFN_IDENTITY_MISMATCH'), msg)
    for iface, q in (('event', ev_multi), ('root', 'حلب'), ('dhat', 'الفرس')):
        path = f'/ajnas/{iface}/' + urllib.parse.quote(q)
        r = json.loads(urllib.request.urlopen(url47 + path).read().decode())
        check(f'M02 خادم v47 {iface}: AHDATH_AJNAS_NOT_IN_SERVED_RELEASE ولا رابط من v48',
              r['served_by_release'] == 'HFN_release_v47' and r['payload'] is None and 'AHDATH_AJNAS_NOT_IN_SERVED_RELEASE' in r['residuals'], r)
    kh = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(V48))), '06_handoff', 'ahdath_ajnas_v48', 'KHILAF.tsv')
    if os.path.exists(kh):
        kc = {r['cand'] for r in csv.DictReader(open(kh, encoding='utf-8'), delimiter='\t')}
        check('K01 صفوف الخلاف (KHILAF، 4262) خارج الإصدار لا تُدمج: لا معرّفٌ منها في الملف ولا في الأجوبة',
              len(kc) == 4262 and not (kc & set(by_id)), len(kc))
    else:
        check('K01 KHILAF.tsv متاح للفحص', False, kh)
finally:
    srv48.kill(); srv47.kill()
if OUT:
    os.makedirs(OUT, exist_ok=True)
    json.dump(dict(results=RES, audit_log=C.audit_log, http_compared=stats['direct_http_compared']),
              open(os.path.join(OUT, 'test_ajnas_consumer.results.json'), 'w'), ensure_ascii=False, indent=1)
print(f'CHECKS pass={len(RES) - len(FAIL)} fail={len(FAIL)} total={len(RES)}')
print('ALL OK' if not FAIL else f'FAILED {len(FAIL)}: {FAIL}')
sys.exit(1 if FAIL else 0)
