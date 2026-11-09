"""tools/fa02/mood_exclusion.py <جذر الشيفرة> <OUT.json> [--surah 2]
أثر سجلات MOOD في الشهادات (FA02، مراجعة المالك): تُعاد شهادة كل جملةٍ في السورة مرتين — بسجلات 14أ كما هي، وبها بعد حذف MOOD —
وتُقارن كل الالتزامات بحالتها **ودليل استيفائها** (معرّف العلاقة، ومعرّف الدليل، وأعضاء satisfied_by، وأصناف غير الموضوع)، وحكم
المستويات. لا يغيّر الشيفرة: الحذف في هذه الأداة وحدها."""
import json, os, subprocess, sys
root, out = os.path.abspath(sys.argv[1]), sys.argv[2]
surah = int(sys.argv[sys.argv.index('--surah') + 1]) if '--surah' in sys.argv else 2
sys.path.insert(0, root)
sys.path.insert(0, os.path.join(root, 'tools', 'fa02'))
os.chdir(root)
from certs import ob_rec                                   # noqa: E402
from sarf import quran_source                              # noqa: E402
from sarf.stages import run, _sentences                    # noqa: E402
from sarf.algebra import closure_certificate               # noqa: E402
from sarf.root import hfn                                  # noqa: E402
C = run([x for x in quran_source.rows() if x[0] == surah], None, ['certificates'])
recs = [r for v in C.get('records').values() for r in v['records']]
nm = [r for r in recs if r['type'] != 'MOOD']
Js = _sentences(C.get('sentences')['LT'])
diffs, n_obl = [], 0
for J in Js:
    a, b = closure_certificate(J, recs), closure_certificate(J, nm)
    oa = {(o['name'], o.get('owner')): ob_rec(o) for o in a['obligations']}
    ob = {(o['name'], o.get('owner')): ob_rec(o) for o in b['obligations']}
    n_obl += len(oa)
    d = [dict(obligation=k[0], owner=k[1], with_mood=oa.get(k), without_mood=ob.get(k)) for k in sorted(set(oa) | set(ob), key=str)
         if {x: y for x, y in (oa.get(k) or {}).items() if x != 'id'} != {x: y for x, y in (ob.get(k) or {}).items() if x != 'id'}]
    if d or a['verdict_by_level'] != b['verdict_by_level']:
        diffs.append(dict(sentence=J.id, obligations=d, levels_with=a['verdict_by_level'], levels_without=b['verdict_by_level']))
H = hfn()
res = dict(surah=surah, sentences=len(Js), obligations_compared=n_obl, compared_fields=['status', 'met', 'rel', 'ev', 'sat', 'unplaced', 'legacy'],
           mood_records=sum(r['type'] == 'MOOD' for r in recs), differing_sentences=len(diffs), diffs=diffs,
           code_commit=subprocess.run(['git', '-C', root, 'rev-parse', 'HEAD'], capture_output=True, text=True).stdout.strip(),
           code_clean=not subprocess.run(['git', '-C', root, 'status', '--porcelain', '--', 'sarf'], capture_output=True, text=True).stdout.strip(),
           hfn_release=H.release, hfn_pin=H.pin, scope='سورةٌ واحدة؛ ولا يثبت غياب الأثر في غيرها')
json.dump(res, open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1, default=str)
print(surah, len(Js), 'obligations', n_obl, 'MOOD', res['mood_records'], 'differing', len(diffs))
