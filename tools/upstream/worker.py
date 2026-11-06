"""tools/upstream/worker.py — عاملٌ معزول يقرأ الموارد الخارجية ويعيد JSON (SARF_UPSTREAM_CONSUMPTION_ADDENDUM_01).

يُشغَّل عمليةً فرعية وحده (python3 -I)، فلا يمسّ وحدات المحلّل ولا مسار استيراده. لا يستورد حزم الموارد (word_tree، core،
engines، tools) بأسمائها العامة: يحمّل الملف المطلوب وحده باسمٍ مفرد (importlib من مساره). ولا يشغّل واجهة CLI.

المدخل (stdin): {"paths": {...}, "lemmas": [{"lemma", "root", "form"}], "roots": [...]}
المخرج (stdout): {"resources": {...}, "lemma": {lemma: {...}}, "root": {root: {...}}}

كل نقصٍ في المورد حالةٌ مسمّاة (RESOURCE_MISSING، LEXICON_FILE_MISSING، ...) لا قائمةٌ فارغة تبدو بحثاً سليماً.
"""
import csv, hashlib, importlib.util, json, os, sys, tempfile, unicodedata

SUKUN = 'ْ'
MARKS = set(chr(c) for c in range(0x064B, 0x0653)) | {'ٰ'}


def nfc(s):
    return unicodedata.normalize('NFC', s or '')


def letters(s):
    """الحروف وحدها، بالهمزة على كرسيّها كما هي، والشدّة علامةٌ تُحذف هنا لأن هذا المفتاح لفحص «الحروف نفسها» وحده"""
    return ''.join(c for c in nfc(s) if c not in MARKS and c != 'ـ')


def match_status(lemma, other):
    """مطابقة مشكولة بعد تسوية NFC المعلنة وحدها: لا تُسقط شدّةٌ ولا حركة، ولا يُستبدل كرسيّ همزة"""
    a, b = nfc(lemma), nfc(other)
    if a == b:
        return 'EXACT_VOCALIZED_MATCH', None
    if a.replace(SUKUN, '') == b.replace(SUKUN, ''):
        # موضع الفرق: أول موضعٍ يختلف فيه الرسمان
        i = next((k for k in range(min(len(a), len(b))) if a[k] != b[k]), min(len(a), len(b)))
        return 'SUKUN_ONLY_DIFFERENCE', i
    if letters(a) == letters(b):
        return 'VOCALIZATION_MISMATCH', None
    return 'LETTERS_DIFFER', None


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()[:16]


def load(name, path):
    """تحميل ملفٍ واحد باسمٍ مفرد لا يصادم أسماء المحلّل (core، tools، engines)"""
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m                    # dataclasses تطلب الوحدة في sys.modules؛ والاسم مفردٌ لا يصادم
    spec.loader.exec_module(m)
    return m


def main():
    req = json.load(sys.stdin)
    P = req['paths']
    res = dict(resources={}, lemma={}, root={})
    R = res['resources']

    def need(key, path):
        ok = os.path.exists(path)
        R[key] = dict(path=path, status='OK' if ok else 'RESOURCE_MISSING', file_hash=sha(path) if ok and os.path.isfile(path) else None)
        return ok

    # ---------- AMLN: الحدث والأثر (R1، R1W، T_JAL) وجهة الفاعل (J_SAJIYYA، J_DAA) ----------
    amln_ok = all([need('AMLN:word_tree/ahdath.py', os.path.join(P['amln'], 'word_tree', 'ahdath.py')),
                   need('AMLN:ahdath/rules_R1.tsv', os.path.join(P['amln'], 'ahdath', 'rules_R1.tsv')),
                   need('AMLN:ahdath/mutawaa_R1W_pool.tsv', os.path.join(P['amln'], 'ahdath', 'mutawaa_R1W_pool.tsv')),
                   need('AMLN:ahdath/taadiya_T_JAL.tsv', os.path.join(P['amln'], 'ahdath', 'taadiya_T_JAL.tsv')),
                   need('AMLN:ahdath/jiha_pool.tsv', os.path.join(P['amln'], 'ahdath', 'jiha_pool.tsv'))])
    AH = load('_up_amln_ahdath', os.path.join(P['amln'], 'word_tree', 'ahdath.py')) if amln_ok else None
    # ---------- wazn-net: المطاوعة، والتعدية T_JAL، وتعدّي المجرّد من الوسيط v1 ----------
    wz_ok = all([need('WAZN:engines/mutawaa_engine.py', os.path.join(P['wazn'], 'engines', 'mutawaa_engine.py')),
                 need('WAZN:data/mutawaa_v3.tsv', os.path.join(P['wazn'], 'data', 'mutawaa_v3.tsv')),
                 need('WAZN:engines/taadiya_engine.py', os.path.join(P['wazn'], 'engines', 'taadiya_engine.py'))])
    tw_ok = need('WAZN:data/transitivity_wasit.tsv', os.path.join(P['wazn'], 'data', 'transitivity_wasit.tsv'))
    MU = load('_up_wazn_mutawaa', os.path.join(P['wazn'], 'engines', 'mutawaa_engine.py')) if wz_ok else None
    TA = load('_up_wazn_taadiya', os.path.join(P['wazn'], 'engines', 'taadiya_engine.py')) if wz_ok else None
    if TA is not None:
        # مصدر التعدية في المحرّك مسارٌ ثابت تحت ~/arabic-net؛ يُعرض هنا المسار الذي قُرئ فعلاً
        R['WAZN:taadiya_engine.AHDATH'] = dict(path=TA.AHDATH, status='OK' if os.path.isdir(TA.AHDATH) else 'RESOURCE_MISSING',
                                               file_hash=None)
    TW = {}
    if tw_ok:
        for r in csv.DictReader(open(R['WAZN:data/transitivity_wasit.tsv']['path'], encoding='utf-8'), delimiter='\t'):
            TW.setdefault(nfc(r['verb']), []).append(r)
    # ---------- HFN: معنى الجذر (tools/root_meaning.py) ----------
    rm_ok = need('HFN:tools/root_meaning.py', os.path.join(P['hfn'], 'tools', 'root_meaning.py')) and \
        need('HFN:02_roots/HFN_ROOTS_v3.csv', os.path.join(P['hfn'], '02_roots', 'HFN_ROOTS_v3.csv'))
    RM = None
    if rm_ok:
        sys.path.insert(0, os.path.join(P['hfn'], 'tools'))   # في العملية الفرعية وحدها
        try:
            RM = load('_up_hfn_root_meaning', os.path.join(P['hfn'], 'tools', 'root_meaning.py'))
            rt = sys.modules.get('root_taxonomy')
            if rt is not None:
                # خبيئة فهرس المعاجم تُكتب بجوار الأداة: تُحوَّل إلى مجلدٍ مؤقت فلا يُكتب في المورد
                rt.CACHE = tempfile.mkdtemp(prefix='up_rt_cache_')
                R['HFN:root_taxonomy.RT'] = dict(path=rt.RT, status='OK' if os.path.isdir(rt.RT) else 'RESOURCE_MISSING', file_hash=None)
        except Exception as e:
            R['HFN:tools/root_meaning.py']['status'] = 'IMPORT_FAILED: ' + type(e).__name__ + ': ' + str(e)[:200]
            RM = None
    mq_path = os.path.join(P['maq'], 'output', 'maqayis_all_roots.json')
    MQ = {}
    if need('MAQ:output/maqayis_all_roots.json', mq_path):
        for r in json.load(open(mq_path, encoding='utf-8'))['roots']:
            MQ.setdefault(r['display'], []).append(r)

    for q in req['lemmas']:
        lem = q['lemma']
        out = dict(ahdath=None, jiha=None, mutawaa=None, mutawaa_base=None, taadiya_T_JAL=None, transitivity_wasit=None)
        if AH is not None:
            out['ahdath'] = [dict(x, match=match_status(lem, x['verb'])[0], diff_pos=match_status(lem, x['verb'])[1])
                             for x in AH.for_verb(lem)]
            out['jiha'] = [dict(x, match=match_status(lem, x['verb'])[0], diff_pos=match_status(lem, x['verb'])[1])
                           for x in AH.jiha(lem)]
        else:
            out['ahdath'] = out['jiha'] = 'RESOURCE_MISSING'
        if MU is not None:
            for key, fn in (('mutawaa', MU.mutawaa_of), ('mutawaa_base', MU.base_of)):
                try:
                    rows = fn(lem)
                    out[key] = [dict(root=m.root, base=m.base, base_form=m.base_form, mutawaa=m.mutawaa, mutawaa_form=m.mutawaa_form,
                                     athar=m.athar, route=m.route, n_lex=m.n_lex, lexicons=m.lexicons, evidence=m.evidence, rank=m.rank,
                                     match=match_status(lem, m.base if key == 'mutawaa' else m.mutawaa)[0],
                                     diff_pos=match_status(lem, m.base if key == 'mutawaa' else m.mutawaa)[1]) for m in rows]
                except MU.NoSamaa as e:
                    out[key] = dict(status='NO_SAMAA_IN_SOURCE', detail=str(e))
            try:
                rows = TA.taadiya_of(lem, routes=['T_JAL'])
                out['taadiya_T_JAL'] = [dict({k: getattr(t, k) for k in t.__dataclass_fields__},
                                             match=match_status(lem, getattr(t, 'lazim', '') or '')[0]) for t in rows]
            except Exception as e:
                out['taadiya_T_JAL'] = dict(status=type(e).__name__, detail=str(e)[:200])
        else:
            out['mutawaa'] = out['mutawaa_base'] = out['taadiya_T_JAL'] = 'RESOURCE_MISSING'
        if tw_ok:
            # المرشّحون بالحروف، ثم الفحص المشكول
            cands = [r for k, rs in TW.items() if letters(k) == letters(lem) for r in rs]
            out['transitivity_wasit'] = [dict(r, match=match_status(lem, r['verb'])[0]) for r in cands]
        else:
            out['transitivity_wasit'] = 'RESOURCE_MISSING'
        res['lemma'][lem] = out

    for root in req['roots']:
        o = dict(root_meaning=None, maqayis=None)
        if RM is not None:
            try:
                rm = RM.root_meaning(root)
                rt = sys.modules.get('root_taxonomy')
                for lx in rm.get('lexicons') or []:
                    # «لا سجلّ» غير «لا ملفّ معجم»: يُفحص وجود الملف نفسه
                    if lx.get('error') == 'RECORD_NOT_FOUND' and rt is not None:
                        fn = next((v[0] for c, v in RM.LEX.items() if RM.NAME.get(c) == lx['lexicon']), None)
                        if fn and not os.path.exists(os.path.join(rt.RT, fn)):
                            lx['error'] = 'LEXICON_FILE_MISSING'
                            lx['file'] = os.path.join(rt.RT, fn)
                o['root_meaning'] = rm
            except Exception as e:
                o['root_meaning'] = dict(error='CALL_FAILED: ' + type(e).__name__ + ': ' + str(e)[:200])
        else:
            o['root_meaning'] = dict(error='RESOURCE_MISSING')
        if MQ:
            key = RM_K(root, RM)
            hits = [r for d, rs in MQ.items() if RM_K(d, RM) == key for r in rs]
            o['maqayis'] = dict(retrieval_key=key, records=[dict(id=r['id'], display=r['display'], semantic_axes=r.get('semantic_axes'),
                                                               body=r.get('body_snippet')) for r in hits],
                                status='FOUND' if hits else 'ROOT_NOT_IN_MAQAYIS')
        else:
            o['maqayis'] = dict(status='RESOURCE_MISSING')
        res['root'][root] = o
    json.dump(res, sys.stdout, ensure_ascii=False)


def RM_K(s, RM):
    """مفتاح استرجاعٍ موحَّد (K من hfn_common عبر الأداة): وسيلة بحث، لا شهادة مساواة"""
    rt = sys.modules.get('root_taxonomy')
    if rt is not None:
        return rt.K(s)
    return letters(s)


if __name__ == '__main__':
    main()
