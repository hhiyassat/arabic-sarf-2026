"""مستهلك روابط ahdath_ajnas المرشّحة (SARF_HFN_V48_VALIDATION_COMPLETION_02 §٤ و§٧ و§٨).

- يفتح الإصدار بمساره الصريح فقط، ويرفض إصداراً أو بصمة MANIFEST غير المطلوبين (HFN_IDENTITY_MISMATCH)، ويفحص هوية كل جواب.
  ولا يقرأ «أحدث إصدار»: بلا مسار صريح لا يعمل.
- الاستهلاك الحي لا يحمل رابطاً لحدثٍ مسحوب، في الواجهات الثلاث: ما أعادته واجهة HFN منها يُحذف من الجواب الحي ويُكتب في
  سجلّ التدقيق `audit_log` بالواجهة والسؤال والمعرّف والسبب. (واجهة HFN نفسها تعيدها في ajnas_for_event: عيبٌ في HFN مسجّل، لا يُصلح هنا)
- لا يُختار حدثٌ من متعدّد، ولا يُسقط تحفّظٌ ولا سند: الروابط الحية تُعاد بصفوفها كاملة كما خدمتها الواجهة.
- السؤال الأصلي والتحويلات (مفتاح الواجهة K: حذف التشكيل وتوحيد الهمزات، وحذف «ال») تُحفظ مع الجواب: المفتاح استرجاعٌ لا شهادة مطابقة.
- مدخلٌ فارغ أو غير نصّي: INVALID_QUERY دون سؤال الواجهة.
- HttpBackend: الواجهة نفسها عبر خادم HFN (api/server.py)، بالفحوص نفسها."""
import json, os, sys, urllib.parse, urllib.request

WITHDRAWN_REASON = 'EVENT_WITHDRAWN_IN_HFN: حدثٌ مسحوب في الإصدار؛ لا يظهر في استهلاكٍ حيّ ويُحفظ في سجلّ التدقيق'


class AjnasIdentityError(RuntimeError):
    pass


def _api(api_dir):
    if api_dir not in sys.path:
        sys.path.insert(0, api_dir)
    import hfn_api
    return hfn_api


class DirectBackend:
    def __init__(self, release_dir, api_dir):
        if not release_dir:
            raise AjnasIdentityError('HFN_IDENTITY_MISMATCH: لا مسار إصدارٍ صريح؛ لا يُخدم «أحدث إصدار»')
        self.api = _api(api_dir)
        self.h = self.api.HFN(release_dir)
        self.release, self.manifest_sha256, self.has_ajnas = self.h.release, self.h.manifest_sha256, self.h.has_ajnas
        self.withdrawn = {i for i, e in self.h.events.items() if (e.get('event_review_v36') or '').startswith('WITHDRAWN')}

    def call(self, iface, q, role=None):
        if iface == 'event':
            return self.h.ajnas_for_event(q)
        if iface == 'root':
            return self.h.ajnas_for_root(q)
        return self.h.events_for_dhat(q, role)


class HttpBackend:
    def __init__(self, base_url, api_dir):
        self.base = base_url.rstrip('/')
        self.api = _api(api_dir)
        st = self.get('/stats')
        self.release, self.manifest_sha256 = st.get('served_by_release') or st.get('release'), st.get('manifest_sha256')
        self.has_ajnas = None
        self.withdrawn = None

    def get(self, path):
        with urllib.request.urlopen(self.base + path, timeout=30) as r:
            return json.loads(r.read().decode('utf-8'))

    def call(self, iface, q, role=None):
        p = f'/ajnas/{"dhat" if iface == "dhat" else iface}/' + urllib.parse.quote(q, safe='')
        if role:
            p += '?role=' + urllib.parse.quote(role)
        return self.get(p)


class AjnasConsumer:
    def __init__(self, backend, expect_release, expect_manifest_sha256, withdrawn_ids=None):
        self.b = backend
        self.expect = (expect_release, expect_manifest_sha256)
        if (backend.release, backend.manifest_sha256) != self.expect:
            raise AjnasIdentityError(f'HFN_IDENTITY_MISMATCH: طُلب {expect_release} ({expect_manifest_sha256[:12]})، '
                                     f'والمخدوم {backend.release} ({(backend.manifest_sha256 or "")[:12]})')
        self.withdrawn = set(withdrawn_ids if withdrawn_ids is not None else (backend.withdrawn or ()))
        self.audit_log = []

    def transforms(self, iface, q):
        K = self.b.api.K
        t = [dict(step='original', value=q)]
        if iface == 'dhat':
            k = K((q or '').split(' ')[0]); t.append(dict(step='K (حذف التشكيل والتطويل وتوحيد الهمزات)', value=k))
            if k.startswith('ال') and len(k) >= 4:
                k = k[2:]; t.append(dict(step='حذف «ال» (4 أحرف فأكثر)', value=k))
        elif iface == 'root':
            t.append(dict(step='K', value=K(q or '')))
        return t

    def query(self, iface, q, role=None):
        if iface not in ('event', 'root', 'dhat'):
            raise ValueError(iface)
        out = dict(interface=iface, query=q, role=role, transforms=None, status=None, links=[], excluded=[], residuals=[],
                   served_by_release=None, manifest_sha256=None, note='CANDIDATE: الرابط لمعنى بابه؛ لا حقيقة ولا اختيار حدث')
        if not isinstance(q, str) or not q.strip():
            out.update(status='INVALID_QUERY'); return out
        out['transforms'] = self.transforms(iface, q)
        r = self.b.call(iface, q, role)
        if (r.get('served_by_release'), r.get('manifest_sha256')) != self.expect:
            raise AjnasIdentityError(f'HFN_IDENTITY_MISMATCH في الجواب: {r.get("served_by_release")}')
        out.update(served_by_release=r['served_by_release'], manifest_sha256=r['manifest_sha256'],
                   residuals=list(r.get('residuals') or []), rank=r.get('rank'), is_fact=r.get('is_fact'))
        links = ((r.get('payload') or {}).get('links') or [])
        for l in links:
            if l.get('event_withdrawn') == 'True' or l.get('event_id') in self.withdrawn:
                rec = dict(interface=iface, query=q, link_id=l['link_id'], event_id=l['event_id'], reason=WITHDRAWN_REASON)
                out['excluded'].append(rec); self.audit_log.append(rec)
            elif role and l.get('role') != role:
                continue
            else:
                out['links'].append(l)
        if out['excluded']:
            out['residuals'].append(f'CONSUMER_EXCLUDED_WITHDRAWN:{len(out["excluded"])}')
        out['status'] = ('NO_RESULT (not a negative)' if not out['links'] and r.get('payload') is not None
                         else 'NOT_SERVED' if r.get('payload') is None else 'CANDIDATES')
        out['events'] = sorted({l['event_id'] for l in out['links']})
        out['multi_event'] = len(out['events']) > 1
        return out
