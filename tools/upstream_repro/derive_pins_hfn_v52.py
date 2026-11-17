# -*- coding: utf-8 -*-
"""derive_pins_hfn_v52.py <hfn_repo> <out.json>: سجلّ تثبيتٍ للعامل على HFN release_v52 (حكم المالك 2026-11-17 «اجعله إنتاجيّاً»).
يُشتقّ من pins_2026_11_08.json: التزامات wazn وamln وmaq وبصماتها كما هي؛ وتُستبدل هوية HFN بـ cf97e15 وrelease_v52.
كل بصمة HFN تُحسب من git show عند الالتزام المثبَّت، لا من نسخة العمل؛ وملفّات العامل من HFN مطابقة بايتاً لما في 22dcb06 (يُتحقَّق ويُطبع)."""
import hashlib, json, os, subprocess, sys
REPO, OUT = sys.argv[1:3]
HFN_COMMIT = 'cf97e15eebc63e45fbe91fdfaec4340320a51bcd'
REL = 'release_v52'
HERE = os.path.dirname(os.path.abspath(__file__))
old = json.load(open(os.path.join(HERE, '..', 'upstream', 'pins_2026_11_08.json'), encoding='utf-8'))


def blob(commit, path):
    return subprocess.run(['git', '-C', REPO, 'show', f'{commit}:{path}'], capture_output=True, check=True).stdout


sha = lambda b: hashlib.sha256(b).hexdigest()
assert subprocess.run(['git', '-C', REPO, 'rev-parse', HFN_COMMIT], capture_output=True, text=True, check=True).stdout.strip() == HFN_COMMIT
files, same = {}, {}
for k, v in old['files'].items():
    if not k.startswith('HFN:'):
        files[k] = v
        continue
    path = k[4:].replace('release/release_v47/', f'release/{REL}/')
    h = sha(blob(HFN_COMMIT, path))
    files['HFN:' + path] = h
    same[path] = h == v
manifest = sha(blob(HFN_COMMIT, f'release/{REL}/MANIFEST.json'))
assert json.loads(blob(HFN_COMMIT, f'release/{REL}/MANIFEST.json'))['release'] == 'HFN_' + REL
pins = dict(old, task='SARF_HFN_V52_PRODUCTION_2026_11_17 (مشتقّ من SARF_UPSTREAM_CONSUMPTION_2026_11_08)',
            commits=dict(old['commits'], hfn=HFN_COMMIT), requested_short=dict(old['requested_short'], hfn=HFN_COMMIT[:7]),
            hfn_release=REL, hfn_manifest_sha256=manifest, files=files)
json.dump(pins, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('MANIFEST', manifest[:12], '| HFN files byte-identical to 22dcb06:', same)
