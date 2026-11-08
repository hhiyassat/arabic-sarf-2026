"""tools/upstream/worker.py — عاملٌ معزول يقرأ المصادر الأربع المثبتة ويعيد JSON (SARF_UPSTREAM_CONSUMPTION_2026_11_08).

يُشغَّل عمليةً فرعية وحده (python3 -I -B) من tools/upstream/client.py: لا وحدة من وحدات المحلّل في مساره، ومسار استيراده يضمّ جذور
المصادر وحدها (wazn للحزمة core، وAMLN للحزمتين word_tree وarabic_net_api، وHFN/tools لـroot_meaning)، ويُتحقَّق بعد الاستيراد أن
كل حزمةٍ عليا حُمّلت من جذرها المتوقَّع (لا تصادم core/engines/word_tree/tools). الكتابة ممنوعة: المصادر للقراءة وحدها، ولا bytecode،
وذاكرات الفهارس مُحوَّلةٌ إلى مجلدٍ مؤقت.

المدخل (stdin): {"paths": {...}, "pins": {...}, "lemmas": [{"lemma", "root", "cls"}], "roots": [{"root", "query_key", "key_rule"}]}
المخرج (stdout): {"resources", "interfaces", "lemma": {lemma: {...}}, "root": {root: {...}}, "hfn47_form_support"}

حالات كل جواب (لا تتحوّل إلى «لا نتيجة»):
  QUERY_OK_NO_RESULT   سُئل المصدر فلم يجد       RESOURCE_MISSING   الملف أو المجلد غائب
  INTERFACE_ERROR      فشل الاستيراد أو الاستدعاء   CONFIG_ERROR       إصدارٌ غير المثبت أو مخططٌ غير المتوقَّع
وكل صفٍّ يحمل match (EXACT، WASL_ONLY، SUKUN_ONLY، WASL_AND_SUKUN، OTHER) وتفصيل الفرق، ويحسمه المستهلك.
"""
import csv, difflib, hashlib, importlib, json, os, sqlite3, sys, tempfile, traceback, unicodedata

SUKUN, SHADDA, WASL = 'ْ', 'ّ', 'ٱ'
HARAKAT = set('ًٌٍَُِ')
HAMZA = set('أإآءؤئ')
MARKS = HARAKAT | {SUKUN, SHADDA, 'ٰ'}


def nfc(s):
    """التسوية الوحيدة المعلنة: NFC (تمثيلاتٌ متكافئة في Unicode)؛ ويُحفظ الأصل معها"""
    return unicodedata.normalize('NFC', s or '')


def letters(s):
    """الحروف بلا علامات، والهمزة على كرسيّها، وٱ = ا — مفتاح استرجاع المرشّحين وحده، لا حكم مطابقة"""
    return ''.join(c for c in nfc(s) if c not in MARKS and c != 'ـ').replace(WASL, 'ا')


def _kind(a, b):
    s = set(a) | set(b)
    if s and s <= {SHADDA}:
        return 'SHADDA'
    if s and s <= {SUKUN}:
        return 'SUKUN'
    if s and s <= HARAKAT:
        return 'HARAKA'
    if s and s <= {WASL, 'ا'}:
        return 'WASL'
    if s and s <= HAMZA | {'ا', 'و', 'ي', 'ى'} and s & HAMZA:
        return 'HAMZA'
    if s and s <= MARKS:
        return 'MARKS'
    return 'LETTER'


def match_class(query, row):
    """مطابقة حرفٍ وحركة بعد NFC وحده. WASL_ONLY: الفرق «ٱ/ا» وحده؛ SUKUN_ONLY: السكون وحده؛ WASL_AND_SUKUN: الاثنان معاً
    ولا غيرهما (حالةٌ مستقلة)؛ OTHER: كل ما سواه (الشدّة والحركات والهمزات والحروف)، مع مواضع الفرق وأنواعه"""
    a, b = nfc(query), nfc(row)
    if a == b:
        return 'EXACT', []
    w = lambda x: x.replace(WASL, 'ا')
    s = lambda x: x.replace(SUKUN, '')
    if w(a) == w(b):
        cls = 'WASL_ONLY'
    elif s(a) == s(b):
        cls = 'SUKUN_ONLY'
    elif s(w(a)) == s(w(b)):
        cls = 'WASL_AND_SUKUN'
    else:
        cls = 'OTHER'
    diffs = []
    for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
        if op != 'equal':
            diffs.append(dict(pos=i1, query=a[i1:i2], row=b[j1:j2], kind=_kind(a[i1:i2], b[j1:j2])))
    return cls, diffs


def sha256(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for blk in iter(lambda: f.read(1 << 20), b''):
            h.update(blk)
    return h.hexdigest()


def load_file(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m
    spec.loader.exec_module(m)
    return m


def main():
    req = json.load(sys.stdin)
    P, PIN = req['paths'], req['pins']
    out = dict(resources={}, interfaces={}, lemma={}, root={}, import_origins={}, errors=[])
    R, I = out['resources'], out['interfaces']

    def need(key, path, expect=None):
        if not os.path.exists(path):
            R[key] = dict(path=path, status='RESOURCE_MISSING', sha256=None)
            return False
        h = sha256(path) if os.path.isfile(path) else None
        st = 'OK' if (expect is None or h == expect) else 'CONFIG_ERROR: HASH_MISMATCH'
        R[key] = dict(path=path, status=st, sha256=h, expected=expect)
        return st == 'OK'

    def iface(key, fn):
        try:
            v = fn()
            I[key] = dict(status='OK')
            return v
        except Exception as e:
            I[key] = dict(status='INTERFACE_ERROR', error=f'{type(e).__name__}: {str(e)[:300]}', trace=traceback.format_exc()[-600:])
            return None

    EXP = PIN.get('files', {})
    # ---------- مسار الاستيراد: جذور المصادر وحدها، بترتيبٍ معلن ----------
    roots_on_path = [P['wazn'], P['amln'], os.path.join(P['hfn'], 'tools')]
    for r in reversed(roots_on_path):
        sys.path.insert(0, r)

    # ---------- HFN v47: الإصدار المثبت ومخططه وأحداثه (المسحوب يُعرف ويُستبعد) ----------
    rel = PIN['hfn_release']
    hdir = os.path.join(P['hfn'], 'release', rel)
    H47 = {}
    ok_ev = need(f'HFN:release/{rel}/events.csv', os.path.join(hdir, 'events.csv'), EXP.get(f'HFN:release/{rel}/events.csv'))
    ok_mf = need(f'HFN:release/{rel}/MANIFEST.json', os.path.join(hdir, 'MANIFEST.json'), EXP.get(f'HFN:release/{rel}/MANIFEST.json'))
    if ok_ev and ok_mf:
        rows = list(csv.DictReader(open(os.path.join(hdir, 'events.csv'), encoding='utf-8')))
        need_cols = set(PIN['hfn_events_schema'])
        miss = sorted(need_cols - set(rows[0].keys()))
        if miss:
            R[f'HFN:release/{rel}/events.csv']['status'] = 'CONFIG_ERROR: SCHEMA_MISSING ' + ','.join(miss)
        else:
            man = json.load(open(os.path.join(hdir, 'MANIFEST.json'), encoding='utf-8'))
            if man.get('counts', {}).get('events') != len(rows):
                R[f'HFN:release/{rel}/MANIFEST.json']['status'] = 'CONFIG_ERROR: COUNTS_EVENTS_MISMATCH'
            for e in rows:
                H47.setdefault(letters(e['verb']), []).append(e)
            out['hfn47_counts'] = dict(events=len(rows), withdrawn=sum(1 for e in rows if e['event_review_v36'].startswith('WITHDRAWN')),
                                       manifest_counts_events=man.get('counts', {}).get('events'))
            FORMS = sorted({e['form'] for e in rows})
            out['hfn47_forms'] = FORMS

    # ---------- wazn-net: المحرّك يقرأ جدوله بنفسه؛ ويُتحقَّق مما حمّله ----------
    MU = TA = None
    if need('WAZN:engines/mutawaa_engine.py', os.path.join(P['wazn'], 'engines', 'mutawaa_engine.py'), EXP.get('WAZN:engines/mutawaa_engine.py')):
        MU = iface('wazn.mutawaa_engine', lambda: importlib.import_module('engines.mutawaa_engine'))
        if MU is not None:
            tbl = os.path.relpath(MU.TABLE, P['wazn'])
            ok = need('WAZN:' + tbl, MU.TABLE, EXP.get('WAZN:' + tbl))
            if os.path.basename(MU.TABLE) != PIN['mutawaa_table']:
                I['wazn.mutawaa_engine'] = dict(status=f'CONFIG_ERROR: ENGINE_LOADED {os.path.basename(MU.TABLE)} ≠ PINNED {PIN["mutawaa_table"]}')
                MU = None
            elif not ok:
                MU = None
            else:
                I['wazn.mutawaa_engine']['table_loaded'] = tbl
    if need('WAZN:engines/taadiya_engine.py', os.path.join(P['wazn'], 'engines', 'taadiya_engine.py'), EXP.get('WAZN:engines/taadiya_engine.py')):
        TA = iface('wazn.taadiya_engine', lambda: importlib.import_module('engines.taadiya_engine'))
        if TA is not None:
            I['wazn.taadiya_engine']['ahdath_dir'] = TA.AHDATH
            if os.path.realpath(TA.AHDATH) != os.path.realpath(os.path.join(P['amln'], 'ahdath')):
                I['wazn.taadiya_engine'] = dict(status='CONFIG_ERROR: AHDATH_NOT_PINNED_AMLN', ahdath_dir=TA.AHDATH)
                TA = None

    def tsv(key, rel_):
        p = os.path.join(P['wazn'], rel_)
        if not need(key, p, EXP.get(key)):
            return None
        rows = list(csv.DictReader(open(p, encoding='utf-8'), delimiter='\t'))
        idx = {}
        for r in rows:
            idx.setdefault(letters(r['verb'] if 'verb' in r else r['hfn_form']), []).append(r)
        return rows, idx

    TW = tsv('WAZN:data/transitivity_wasit_v5.tsv', 'data/transitivity_wasit_v5.tsv')
    if TW and not {'basis_v5', 'transitivity_v1', 'harf_v1'} <= set(TW[0][0].keys()):
        R['WAZN:data/transitivity_wasit_v5.tsv']['status'] = 'CONFIG_ERROR: SCHEMA (basis_v5/transitivity_v1/harf_v1)'
        TW = None
    SF = tsv('WAZN:data/sifat_v2.tsv', 'data/sifat_v2.tsv')
    XW = None
    if need('WAZN:data/hfn_form_crosswalk.tsv', os.path.join(P['wazn'], 'data', 'hfn_form_crosswalk.tsv'), EXP.get('WAZN:data/hfn_form_crosswalk.tsv')):
        XW = {r['hfn_form']: r for r in csv.DictReader(open(os.path.join(P['wazn'], 'data', 'hfn_form_crosswalk.tsv'), encoding='utf-8'), delimiter='\t')}
    # البناء في الإصدار وجدول الربط: المدعوم وغير المدعوم كما هو، بلا تقريب إلى أقرب بناء
    if H47 and XW is not None:
        out['hfn47_form_support'] = {f: (dict(wazn_code=XW[f]['wazn_code'], status=XW[f]['status'], categories=XW[f]['categories'])
                                         if f in XW else dict(status='NOT_IN_CROSSWALK')) for f in out.get('hfn47_forms', [])}

    # ---------- AMLN: المسالك (word_tree.ahdath) والواجهة (arabic_net_api.sources) ----------
    AH = API = None
    for k in ('AMLN:ahdath/rules_R1.tsv', 'AMLN:ahdath/mutawaa_R1W_pool.tsv', 'AMLN:ahdath/taadiya_T_JAL.tsv', 'AMLN:ahdath/jiha_pool.tsv',
              'AMLN:word_tree/ahdath.py', 'AMLN:data/maqayis_bank_crosswalk.tsv'):
        need(k, os.path.join(P['amln'], k.split(':', 1)[1]), EXP.get(k))
    if all(R[k]['status'] == 'OK' for k in R if k.startswith('AMLN:ahdath/') or k == 'AMLN:word_tree/ahdath.py'):
        AH = iface('amln.word_tree.ahdath', lambda: importlib.import_module('word_tree.ahdath'))
        if AH is not None and getattr(AH, '_hfn_rel')() != rel:
            I['amln.word_tree.ahdath'] = dict(status=f'CONFIG_ERROR: AMLN_HFN_RELEASE={AH._hfn_rel()} ≠ {rel}')
            AH = None
    API = iface('amln.arabic_net_api', lambda: importlib.import_module('arabic_net_api'))
    if API is not None:
        src = iface('amln.arabic_net_api.sources', API.sources)
        out['api_sources'] = src
        if src is not None:
            hs = src.get('hfn', {})
            # الواجهة تسمّي الإصدار HFN_release_vN؛ فالفحص بمجلده الحقيقي وبصمة MANIFEST وطريقة تثبيته، لا بالاسم
            same = os.path.realpath(hs.get('dir') or '') == os.path.realpath(hdir) and hs.get('manifest_sha256') == PIN['hfn_manifest_sha256']
            if not same or hs.get('pinned_by') == 'NEWEST_VERIFIED':
                I['amln.arabic_net_api.sources']['status'] = (f'CONFIG_ERROR: api HFN dir={hs.get("dir")} manifest={str(hs.get("manifest_sha256"))[:12]} '
                                                               f'pinned_by={hs.get("pinned_by")}')

    # ---------- HFN: معنى الجذر (بنك v11) ----------
    RM = None
    if need('HFN:tools/root_meaning.py', os.path.join(P['hfn'], 'tools', 'root_meaning.py'), EXP.get('HFN:tools/root_meaning.py')) and \
            need('HFN:02_roots/' + PIN['root_bank'], os.path.join(P['hfn'], '02_roots', PIN['root_bank']), EXP.get('HFN:02_roots/' + PIN['root_bank'])):
        def _rm():
            rt = importlib.import_module('root_taxonomy')
            rt.CACHE = tempfile.mkdtemp(prefix='up_rt_cache_')        # الخبيئة لا تُكتب بجوار الأداة
            m = importlib.import_module('root_meaning')
            return m
        RM = iface('hfn.root_meaning', _rm)
        if RM is not None and os.path.basename(RM.BANK) != PIN['root_bank']:
            I['hfn.root_meaning'] = dict(status=f'CONFIG_ERROR: BANK {os.path.basename(RM.BANK)} ≠ {PIN["root_bank"]}')
            RM = None
        if RM is not None:
            rt = sys.modules['root_taxonomy']
            I['hfn.root_meaning'].update(bank=os.path.basename(RM.BANK), lexicon_dir=rt.RT, lexicon_dir_present=os.path.isdir(rt.RT))
    BANK = {}
    if RM is not None:
        BANK = RM._load()
    # ---------- مقاييس ابن فارس: جدول الربط بالبنك (AMLN) ونصّ Maqaiys-roots احتياطاً ----------
    MQX, MQJ = {}, {}
    if R.get('AMLN:data/maqayis_bank_crosswalk.tsv', {}).get('status') == 'OK':
        for r in csv.DictReader(open(os.path.join(P['amln'], 'data', 'maqayis_bank_crosswalk.tsv'), encoding='utf-8'), delimiter='\t'):
            for k in (r['bank_K'].split('|') if r['bank_K'] else []):
                MQX.setdefault(k, []).append(r)
            if not r['bank_K']:
                MQX.setdefault('', []).append(r)
    if need('MAQ:output/maqayis_all_roots.json', os.path.join(P['maq'], 'output', 'maqayis_all_roots.json'), EXP.get('MAQ:output/maqayis_all_roots.json')):
        for r in json.load(open(os.path.join(P['maq'], 'output', 'maqayis_all_roots.json'), encoding='utf-8'))['roots']:
            MQJ[str(r['id'])] = r

    # ---------- أصل كل حزمةٍ عليا محمّلة (كشف التصادم) ----------
    for name in ('core', 'engines', 'word_tree', 'arabic_net_api', 'root_meaning', 'root_taxonomy', 'hfn_common', 'tools', 'sarf'):
        m = sys.modules.get(name)
        f = getattr(m, '__file__', None) or (list(getattr(m, '__path__', []) or [None])[0] if m else None)
        out['import_origins'][name] = os.path.realpath(f) if f else None

    # ================= الأسئلة =================
    for q in req['lemmas']:
        lem = nfc(q['lemma'])
        o = {}
        # HFN v47: أحداث الحروف نفسها؛ والمسحوب يُعلَّم ولا يُعاد حياً
        if not H47:
            o['hfn47'] = dict(status='RESOURCE_MISSING' if not ok_ev else 'CONFIG_ERROR')
        else:
            rows = []
            for e in H47.get(letters(lem), []):
                m, d = match_class(lem, e['verb'])
                rows.append(dict(event_id=e['event_id'], verb=e['verb'], root_K=e['root_K'], form=e['form'], transitivity=e['transitivity'],
                                 masdar=e['masdar'], masdar_wasit_v37=e.get('masdar_wasit_v37') or None,
                                 transitivity_wasit_v37=e.get('transitivity_wasit_v37') or None, event_review=e['event_review_v36'][:160],
                                 withdrawn=e['event_review_v36'].startswith('WITHDRAWN'), match=m, diff=d))
            o['hfn47'] = dict(status='OK' if rows else 'QUERY_OK_NO_RESULT', rows=rows)
        # المطاوعة: المحرّك المثبت (يطابق بتسامح: السكون وٱ)؛ ويُعاد فحص كل صفٍّ هنا
        for key, fn_name, side in (('mutawaa', 'mutawaa_of', 'base'), ('mutawaa_base', 'base_of', 'mutawaa')):
            if MU is None:
                o[key] = dict(status=(I.get('wazn.mutawaa_engine') or {}).get('status', 'RESOURCE_MISSING'))
                continue
            try:
                ms = getattr(MU, fn_name)(lem)
                o[key] = dict(status='OK', rows=[dict(root=m.root, base=m.base, base_form=m.base_form, mutawaa=m.mutawaa, mutawaa_form=m.mutawaa_form,
                                                      athar=m.athar, route=m.route, n_lex=m.n_lex, lexicons=m.lexicons, evidence=m.evidence,
                                                      rank=m.rank, row_verb=(m.base if side == 'base' else m.mutawaa),
                                                      match=match_class(lem, m.base if side == 'base' else m.mutawaa)[0],
                                                      diff=match_class(lem, m.base if side == 'base' else m.mutawaa)[1]) for m in ms])
            except MU.NoSamaa as e:
                o[key] = dict(status='QUERY_OK_NO_RESULT', detail=str(e)[:200])
            except Exception as e:
                o[key] = dict(status='INTERFACE_ERROR', detail=f'{type(e).__name__}: {str(e)[:200]}')
        if TA is None:
            o['taadiya_T_JAL'] = dict(status=(I.get('wazn.taadiya_engine') or {}).get('status', 'RESOURCE_MISSING'))
        else:
            try:
                ts = TA.taadiya_of(lem, routes=['T_JAL'])
                o['taadiya_T_JAL'] = dict(status='OK' if ts else 'QUERY_OK_NO_RESULT',
                                          rows=[dict({k: getattr(t, k) for k in t.__dataclass_fields__}, row_verb=getattr(t, 'lazim', ''),
                                                     match=match_class(lem, getattr(t, 'lazim', ''))[0], diff=match_class(lem, getattr(t, 'lazim', ''))[1])
                                                for t in ts])
            except Exception as e:
                nm = type(e).__name__
                o['taadiya_T_JAL'] = dict(status='QUERY_OK_NO_RESULT' if nm in ('NoSamaa', 'LookupError', 'KeyError') or 'NoTaadiya' in nm
                                          else 'INTERFACE_ERROR', detail=f'{nm}: {str(e)[:200]}')
        for key, T_ in (('transitivity_wasit_v5', TW), ('sifat_v2', SF)):
            if T_ is None:
                o[key] = dict(status=R.get('WAZN:data/' + key + '.tsv', {}).get('status', 'RESOURCE_MISSING'))
                continue
            rows = [dict(r, row_verb=r['verb'], match=match_class(lem, r['verb'])[0], diff=match_class(lem, r['verb'])[1])
                    for r in T_[1].get(letters(lem), [])]
            o[key] = dict(status='OK' if rows else 'QUERY_OK_NO_RESULT', rows=rows)
        # AMLN: المرشّحون بالحروف كلّهم (keep_rejected)، ثم يُعاد فحص الصفّ حرفاً وحركة هنا؛ ولا يُقبل حكم vowel_evidence بدلاً منه
        for key, fn_name in (('ahdath', 'for_verb'), ('jiha', 'jiha')):
            if AH is None:
                o[key] = dict(status=(I.get('amln.word_tree.ahdath') or {}).get('status', 'RESOURCE_MISSING'))
                continue
            try:
                xs = getattr(AH, fn_name)(lem, keep_rejected=True)
                o[key] = dict(status='OK' if xs else 'QUERY_OK_NO_RESULT',
                              rows=[dict({k: v for k, v in x.items() if k not in ('vowel_evidence',)}, upstream_match=x.get('match'),
                                         upstream_keep=x.get('keep'), row_verb=x['verb'], match=match_class(lem, x['verb'])[0],
                                         diff=match_class(lem, x['verb'])[1]) for x in xs])
            except Exception as e:
                o[key] = dict(status='INTERFACE_ERROR', detail=f'{type(e).__name__}: {str(e)[:200]}')
        o['query_original'], o['query_nfc'], o['nfc_changed'] = q['lemma'], lem, q['lemma'] != lem
        out['lemma'][q['lemma']] = o       # المفتاح النص الأصلي كما أرسله المستهلك؛ وNFC للمقارنة وحدها

    for q in req['roots']:
        root, key = q['root'], q['query_key']
        o = dict(sarf_root=root, query_key=key, key_rule=q['key_rule'])
        if key is None:
            o['root_meaning'] = dict(status='KEY_NOT_ESTABLISHED', detail=q['key_rule'])
            o['maqayis'] = dict(status='KEY_NOT_ESTABLISHED')
            out['root'][root] = o
            continue
        if RM is None:
            o['root_meaning'] = dict(status=(I.get('hfn.root_meaning') or {}).get('status', 'RESOURCE_MISSING'))
        else:
            row = BANK.get(key)
            if row is None:
                o['root_meaning'] = dict(status='QUERY_OK_NO_RESULT', detail='ROOT_NOT_IN_BANK')
            else:
                rm = iface('hfn.root_meaning.call', lambda: RM.root_meaning(key))
                lex = []
                rt = sys.modules.get('root_taxonomy')
                for lx in (rm or {}).get('lexicons') or []:
                    if lx.get('error') == 'RECORD_NOT_FOUND':
                        fn = next((v[0] for c, v in RM.LEX.items() if RM.NAME.get(c) == lx['lexicon']), None)
                        if fn and rt is not None and not os.path.exists(os.path.join(rt.RT, fn)):
                            lx = dict(lx, error='LEXICON_FILE_MISSING', file=os.path.join(rt.RT, fn))
                    lex.append(lx)
                o['root_meaning'] = dict(status='OK' if rm is not None else 'INTERFACE_ERROR', bank_root=row.get('root'),
                                         hfn_root_id=row.get('hfn_root_id'), K=row.get('K'), lexicons=lex,
                                         backbone_only=(rm or {}).get('backbone_only'),
                                         host_refs=[x for x in (row.get('host_refs') or '').split('·') if x],
                                         text_status='OCR_UNVERIFIED')
        if not MQX:
            o['maqayis'] = dict(status='RESOURCE_MISSING')
        else:
            xs = MQX.get(key, [])
            recs = []
            for x in xs:
                j = MQJ.get(x['entry_id'])
                if j is None:
                    recs.append(dict(entry_id=x['entry_id'], basis=x['basis'], status='RESOURCE_MISSING: TEXT_NOT_IN_MAQAIYS_JSON'))
                elif nfc(j['display']) != nfc(x['root_display']):
                    recs.append(dict(entry_id=x['entry_id'], basis=x['basis'], status='CONFIG_ERROR: DISPLAY_DISAGREES',
                                     crosswalk_display=x['root_display'], json_display=j['display']))
                else:
                    recs.append(dict(entry_id=x['entry_id'], display=j['display'], basis=x['basis'], n_keys=x['n_keys'],
                                     semantic_axes=j.get('semantic_axes'), body=j.get('body_snippet'), text_status='OCR_UNVERIFIED'))
            o['maqayis'] = dict(status='OK' if recs else 'QUERY_OK_NO_RESULT', records=recs, via='AMLN:data/maqayis_bank_crosswalk.tsv (bank_K)')
        out['root'][root] = o
    out['maqayis_unmapped_entries'] = [dict(entry_id=x['entry_id'], display=x['root_display'], basis=x['basis']) for x in MQX.get('', [])]
    json.dump(out, sys.stdout, ensure_ascii=False)


if __name__ == '__main__':
    main()
