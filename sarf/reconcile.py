"""sarf/reconcile.py — وحدة الحقيقة بين المراحل (SARF_COMPLETION_FROM_REPORT_063 §٢).

السمات الصرفية (المرحلة ١٣) تُحسب قبل العلاقات؛ وإطار الفعل في العلاقات (14أ) يولّد أوجهاً كاملة (زمن، بناء، ضمير، دور، تحقيق) ويمنع بعضها
بمانعٍ مثبت. فإذا بقيت السمات تعرض قيمة وجهٍ ممنوع حيّةً تناقضت المرحلتان (الشاهد «دُعُوا»: الأمر مرشّحٌ في ١٣ وممنوعٌ في 14أ).

reconcile_features(features, records) → features_final: لكل وحدةٍ لها إطار فعلٍ بأوجه:
  - قيم الزمن والبناء والضمير من الأوجه الحيّة وحدها، ومن الوجه نفسه (لا يُجمع زمنٌ من وجه وبناءٌ من آخر): إن بقي وجهٌ حيّ واحد فقيمه،
    وإن تعدّدت فالقيمة المشتركة أو None بالبدائل، ومعها قائمة الأوجه الحيّة بقيمها مجتمعة (faces)؛
  - كل قيمةٍ من وجهٍ ممنوع، أو لا يحملها وجهٌ حيّ، تُحفظ في excluded بسببها ووجهها ومعرّف العلاقة؛
  - مخرج المرحلة ١٣ يُحفظ في stage13 موسوماً «مخرج مرحلي تجاوزه الدليل اللاحق».
ولا يُغيَّر شيءٌ في وحدةٍ لا إطار لها، ولا في إطارٍ بلا أوجه. ولا تُختار هنا قيمة لم يحملها وجهٌ حيّ.
"""
import copy
import re

FIELDS = (('tense', 'tense'), ('voice', 'voice'), ('subject', 'subject'))
SUPERSEDED = 'مخرج مرحلي تجاوزه الدليل اللاحق (أوجه إطار الفعل في العلاقات)'


def _unit_key(uid):
    m = re.search(r'\.w(\d+)\.u(\d+)$', uid or '')
    return (int(m.group(1)), int(m.group(2))) if m else None


def _same(a, b):
    return a == b


def reconcile_features(features, records):
    """features: {(w, u): {feature: {v, st, ev, alt}}}؛ records: سجلات العلاقات للآية → (features_final، سجلّ التغييرات)"""
    out = copy.deepcopy(features)
    log = []
    for r in records:
        if r.get('type') != 'VERB_FRAME':
            continue
        cands = (r.get('frame') or {}).get('candidates') or []
        if not cands:
            continue
        key = _unit_key((r.get('heads') or {}).get('verb'))
        if key is None or key not in out:
            continue
        live = [c for c in cands if c.get('status') != 'REJECTED']
        rej = [c for c in cands if c.get('status') == 'REJECTED']
        F = out[key]
        F['_faces'] = dict(relation_id=r['relation_id'], frame_status=r.get('status'),
                           live=[dict(face=c['id'], **{k: c.get(k) for k, _ in FIELDS}, role=c.get('subject_role')) for c in live],
                           rejected=[dict(face=c['id'], reason=c.get('reason'), **{k: c.get(k) for k, _ in FIELDS}) for c in rej])
        for fk, ck in FIELDS:
            if fk not in F or not isinstance(F[fk], dict):
                continue
            old = copy.deepcopy(F[fk])
            lv = []
            for c in live:
                if c.get(ck) is not None and not any(_same(c.get(ck), x) for x in lv):
                    lv.append(c.get(ck))
            excluded = []
            for val in [old.get('v')] + list(old.get('alt') or []):
                if val is None or any(_same(val, x) for x in lv) or any(_same(val, e['value']) for e in excluded):
                    continue
                by = next((c for c in rej if _same(c.get(ck), val)), None)
                excluded.append(dict(value=val, face=by['id'] if by else None, relation_id=r['relation_id'],
                                     reason=(by.get('reason') if by else f'لا يحمله وجهٌ حيّ في الإطار {r["relation_id"].split(":")[3]}')))
            if not excluded and (old.get('v') in lv or not lv):
                continue
            new = dict(old)
            new['v'] = lv[0] if len(lv) == 1 else None
            new['alt'] = lv if len(lv) > 1 else None
            new['st'] = old.get('st') if len(lv) == 1 and old.get('v') == lv[0] else ('مرشّح' if lv else 'مؤجَّل')
            new['ev'] = (f"من الأوجه الحيّة في {r['relation_id'].split(':')[3]} ({', '.join(c['id'] for c in live)}): " +
                         ('وجهٌ واحد' if len(lv) == 1 else 'أوجهٌ متعدّدة لم يُحسم بينها'))
            new['excluded'] = excluded
            new['stage13'] = dict(v=old.get('v'), st=old.get('st'), alt=old.get('alt'), note=SUPERSEDED)
            F[fk] = new
            log.append(dict(unit=key, feature=fk, before=old.get('v'), after=new['v'], excluded=[e['value'] for e in excluded],
                            relation_id=r['relation_id']))
    return out, log


def check_consistency(features_final, records):
    """→ الأخطاء: قيمةٌ حيّة في السمات النهائية لا يحملها وجهٌ حيّ، أو قيمٌ من وجهين مختلفين في وحدةٍ لها وجهٌ حيّ واحد"""
    errs = []
    for r in records:
        if r.get('type') != 'VERB_FRAME' or not (r.get('frame') or {}).get('candidates'):
            continue
        key = _unit_key((r.get('heads') or {}).get('verb'))
        F = features_final.get(key)
        if not F:
            continue
        live = [c for c in r['frame']['candidates'] if c.get('status') != 'REJECTED']
        for fk, ck in FIELDS:
            v = (F.get(fk) or {}).get('v')
            if v is not None and not any(_same(v, c.get(ck)) for c in live):
                errs.append(('LIVE_VALUE_FROM_EXCLUDED_FACE', key, fk, v))
        if len(live) == 1:
            for fk, ck in FIELDS:
                v = (F.get(fk) or {}).get('v')
                if v is not None and not _same(v, live[0].get(ck)):
                    errs.append(('MIXED_FACES', key, fk, v))
    return errs
