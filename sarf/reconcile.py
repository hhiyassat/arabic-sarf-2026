"""sarf/reconcile.py — وحدة الحقيقة بين المراحل (SARF_COMPLETION_FROM_REPORT_063 §٢، ومراجعة SARF_FINAL_COMPLETION_AND_ACCEPTANCE_01 §٢).

السمات الصرفية (المرحلة ١٣) تُحسب قبل العلاقات؛ وإطار الفعل (14أ) يولّد أوجهاً كاملة (زمن، بناء، ضمير…) ويمنع بعضها بمانعٍ مثبت.

reconcile_features(features, records) → (features_final، السجلّ):
  - أوجه الوحدة من كل إطاراتها (لا يفوز الأخير بترتيب السجلات): الوجه بتوقيعه (القيم مجتمعةً)، وهو ممنوعٌ إن منعه أيّ إطار؛
  - القيمة النهائية لكل سمة هي المشتركة بين كل الأوجه الحيّة وحدها، بدليل اشتراكها؛ وإن اختلفت الأوجه أو نقص الحقل في وجهٍ حيّ
    فلا قيمة (None) والبدائل محفوظة. فلا تبقى قيمةٌ قديمة لأنها موجودةٌ في أحد الأوجه، ولا يُنتقى وجهٌ بلا دليل؛
  - الأوجه الحيّة كاملةً بهوياتها وإطاراتها في _faces؛ والقيم المستبعدة بوجهها وسببها؛ ومخرج المرحلة ١٣ محفوظٌ موسوماً بأنه تُجووز؛
  - كل الأوجه ممنوعة: لا قيمة، والحالة ALL_FACES_REJECTED.
الحالات: الحيّة LIVE_STATUSES، والممنوعة DEAD_STATUSES؛ وما سواهما خطأٌ صريح (UnknownFaceStatus).

check_consistency(features_final, records) فاحصٌ مستقل يعيد بناء الأوجه من السجلات بنفسه، ويشترط أن تتحقّق مجموعة القيم المسندة
مجتمعةً في وجهٍ حيّ واحد على الأقل، وأن تكون كل قيمةٍ مسندة مشتركةً بين الأوجه الحيّة كلها."""
import copy
import json
import re

FIELDS = ('tense', 'voice', 'subject')
LIVE_STATUSES = frozenset({'DEFERRED', 'LICENSED', 'CANDIDATE'})
DEAD_STATUSES = frozenset({'REJECTED'})
SUPERSEDED = 'مخرج مرحلي تجاوزه الدليل اللاحق (أوجه إطار الفعل في العلاقات)'


class UnknownFaceStatus(ValueError):
    pass


def _unit_key(uid):
    m = re.search(r'\.w(\d+)\.u(\d+)$', uid or '')
    return (int(m.group(1)), int(m.group(2))) if m else None


def _canon(v):
    return json.dumps(v, ensure_ascii=False, sort_keys=True)


def _status_live(st):
    if st in LIVE_STATUSES:
        return True
    if st in DEAD_STATUSES:
        return False
    raise UnknownFaceStatus(f'حالة وجهٍ غير معروفة: {st!r} (الحيّة {sorted(LIVE_STATUSES)}، والممنوعة {sorted(DEAD_STATUSES)})')


def unit_faces(records):
    """{وحدة: {'faces': {توقيع: وجه}, 'frames': [...]}} — الوجه بتوقيعه (الحقول الثلاثة مجتمعة)، وحيّ إن لم يمنعه إطار"""
    out = {}
    for r in records:
        if r.get('type') != 'VERB_FRAME':
            continue
        cands = (r.get('frame') or {}).get('candidates') or []
        key = _unit_key((r.get('heads') or {}).get('verb'))
        if key is None or not cands:
            continue
        U = out.setdefault(key, dict(faces={}, frames=[]))
        U['frames'].append(r['relation_id'])
        for c in cands:
            live = _status_live(c.get('status'))
            sig = _canon({f: c.get(f) for f in FIELDS})
            f_ = U['faces'].setdefault(sig, dict(values={f: c.get(f) for f in FIELDS}, ids=[], frames=[], live=True, reasons=[],
                                                 roles=[]))
            f_['ids'].append(c.get('id'))
            f_['frames'].append(r['relation_id'])
            if c.get('subject_role'):
                f_['roles'].append(c['subject_role'])
            if not live:
                f_['live'] = False
                f_['reasons'].append(c.get('reason'))
    return out


def reconcile_features(features, records):
    """features: {(w, u): {feature: {v, st, ev, alt}}}؛ records: سجلات العلاقات للآية → (features_final، سجلّ التغييرات)"""
    out = copy.deepcopy(features)
    log = []
    UF = unit_faces(records)
    for key in sorted(UF):
        U = UF[key]
        if key not in out:
            continue
        faces = [U['faces'][s] for s in sorted(U['faces'])]
        live = [f for f in faces if f['live']]
        dead = [f for f in faces if not f['live']]
        F = out[key]
        fr_ids = sorted(set(U['frames']))
        F['_faces'] = dict(frames=fr_ids, state='ALL_FACES_REJECTED' if not live else 'LIVE_FACES',
                           live=[dict(faces=sorted(set(map(str, f['ids']))), frames=sorted(set(f['frames'])), roles=sorted(set(f['roles'])),
                                      **f['values']) for f in live],
                           rejected=[dict(faces=sorted(set(map(str, f['ids']))), frames=sorted(set(f['frames'])),
                                          reasons=sorted(set(map(str, f['reasons']))), **f['values']) for f in dead])
        for fk in FIELDS:
            if fk not in F or not isinstance(F[fk], dict):
                continue
            old = copy.deepcopy(F[fk])
            vals = [f['values'].get(fk) for f in live]
            distinct = sorted({_canon(v) for v in vals if v is not None})
            missing = any(v is None for v in vals)
            common = json.loads(distinct[0]) if live and len(distinct) == 1 and not missing else None
            alt = [json.loads(x) for x in distinct] if len(distinct) > 1 or (missing and distinct) else None
            live_set = set(distinct)
            excluded = []
            for val in [old.get('v')] + list(old.get('alt') or []):
                if val is None or _canon(val) in live_set or any(_canon(val) == _canon(e['value']) for e in excluded):
                    continue
                by = [f for f in dead if _canon(f['values'].get(fk)) == _canon(val)]
                fids = sorted({str(i) for f in by for i in f['ids']}) or None
                excluded.append(dict(value=val, faces=fids, face='، '.join(fids) if fids else None,
                                     relation_ids=fr_ids, relation_id=fr_ids[0],
                                     reason=('؛ '.join(sorted({str(x) for f in by for x in f['reasons']})) if by
                                             else 'لا يحمله وجهٌ حيّ في أطر الوحدة')))
            new = dict(old)
            new['v'] = common
            new['alt'] = alt
            if common is not None:
                new['st'] = old.get('st') if _canon(old.get('v')) == _canon(common) else 'مرشّح'
                new['ev'] = f'مشتركةٌ بين كل الأوجه الحيّة ({len(live)}) في {", ".join(r.split(":")[3] for r in fr_ids)}'
            else:
                new['st'] = 'مرفوض' if not live else 'مؤجَّل'
                new['ev'] = ('كل الأوجه ممنوعة' if not live else
                             'حقلٌ ناقص في وجهٍ حيّ' if missing and len(distinct) <= 1 else
                             f'الأوجه الحيّة ({len(live)}) مختلفةٌ فيها، ولا يُختار وجهٌ بلا دليل')
            new['excluded'] = excluded
            changed = _canon(old.get('v')) != _canon(new['v']) or bool(excluded) or _canon(old.get('alt')) != _canon(new['alt'])
            if changed:
                new['stage13'] = dict(v=old.get('v'), st=old.get('st'), alt=old.get('alt'), note=SUPERSEDED)
                log.append(dict(unit=key, feature=fk, before=old.get('v'), after=new['v'], excluded=[e['value'] for e in excluded],
                                relation_id=fr_ids[0], relation_ids=fr_ids))
            F[fk] = new
    return out, log


def check_consistency(features_final, records):
    """فاحصٌ مستقل: يبني الأوجه من السجلات بنفسه (لا يستعمل unit_faces) → قائمة الأخطاء"""
    errs = []
    per = {}
    for r in records:
        if r.get('type') != 'VERB_FRAME':
            continue
        cands = (r.get('frame') or {}).get('candidates') or []
        m = re.search(r'\.w(\d+)\.u(\d+)$', (r.get('heads') or {}).get('verb') or '')
        if not m or not cands:
            continue
        key = (int(m.group(1)), int(m.group(2)))
        d = per.setdefault(key, {})
        for c in cands:
            st = c.get('status')
            if st not in LIVE_STATUSES and st not in DEAD_STATUSES:
                errs.append(('UNKNOWN_FACE_STATUS', key, None, st))
                continue
            sig = tuple(json.dumps(c.get(f), ensure_ascii=False, sort_keys=True) for f in FIELDS)
            d[sig] = d.get(sig, True) and st in LIVE_STATUSES
    for key, d in sorted(per.items()):
        F = features_final.get(key)
        if not F:
            continue
        live = [s for s, ok in d.items() if ok]
        assigned = {i: json.dumps((F.get(f) or {}).get('v'), ensure_ascii=False, sort_keys=True)
                    for i, f in enumerate(FIELDS) if (F.get(f) or {}).get('v') is not None}
        if not live:
            for i, v in assigned.items():
                errs.append(('VALUE_WITH_ALL_FACES_REJECTED', key, FIELDS[i], json.loads(v)))
            continue
        for i, v in assigned.items():
            if not any(s[i] == v for s in live):
                errs.append(('LIVE_VALUE_FROM_EXCLUDED_FACE', key, FIELDS[i], json.loads(v)))
            elif any(s[i] != v for s in live):
                errs.append(('SELECTED_WITHOUT_EVIDENCE', key, FIELDS[i], json.loads(v)))
        if assigned and not any(all(s[i] == v for i, v in assigned.items()) for s in live):
            errs.append(('MIXED_FACES', key, ','.join(FIELDS[i] for i in assigned), {FIELDS[i]: json.loads(v) for i, v in assigned.items()}))
    return errs
