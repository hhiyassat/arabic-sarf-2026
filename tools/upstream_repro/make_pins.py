# -*- coding: utf-8 -*-
"""make_pins.py <pinned_dir> <out.json>: سجلّ التثبيت: الالتزامات الأربعة (من .pinned_commit)، وإصدار HFN وبصمة MANIFEST، وبصمة كل ملفٍ يستهلكه العامل."""
import sys, os, json, hashlib
D, OUT = sys.argv[1:3]
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
F = {'HFN:release/release_v47/events.csv': 'hfn/release/release_v47/events.csv', 'HFN:release/release_v47/MANIFEST.json': 'hfn/release/release_v47/MANIFEST.json',
     'HFN:tools/root_meaning.py': 'hfn/tools/root_meaning.py', 'HFN:02_roots/HFN_ROOTS_v11.csv': 'hfn/02_roots/HFN_ROOTS_v11.csv',
     'WAZN:engines/mutawaa_engine.py': 'wazn/engines/mutawaa_engine.py', 'WAZN:data/mutawaa_v7.tsv': 'wazn/data/mutawaa_v7.tsv',
     'WAZN:engines/taadiya_engine.py': 'wazn/engines/taadiya_engine.py', 'WAZN:data/transitivity_wasit_v5.tsv': 'wazn/data/transitivity_wasit_v5.tsv',
     'WAZN:data/sifat_v2.tsv': 'wazn/data/sifat_v2.tsv', 'WAZN:data/hfn_form_crosswalk.tsv': 'wazn/data/hfn_form_crosswalk.tsv',
     'AMLN:word_tree/ahdath.py': 'amln/word_tree/ahdath.py', 'AMLN:ahdath/rules_R1.tsv': 'amln/ahdath/rules_R1.tsv',
     'AMLN:ahdath/mutawaa_R1W_pool.tsv': 'amln/ahdath/mutawaa_R1W_pool.tsv', 'AMLN:ahdath/taadiya_T_JAL.tsv': 'amln/ahdath/taadiya_T_JAL.tsv',
     'AMLN:ahdath/jiha_pool.tsv': 'amln/ahdath/jiha_pool.tsv', 'AMLN:data/maqayis_bank_crosswalk.tsv': 'amln/data/maqayis_bank_crosswalk.tsv',
     'MAQ:output/maqayis_all_roots.json': 'maq/output/maqayis_all_roots.json'}
pins = dict(task='SARF_UPSTREAM_CONSUMPTION_2026_11_08',
            commits={k: open(os.path.join(D, k, '.pinned_commit')).read().strip() for k in ('hfn', 'wazn', 'amln', 'maq')},
            requested_short={'hfn': '22dcb06', 'wazn': '0f647e5', 'amln': '8da48f7', 'maq': '6c2c58f'},
            hfn_release='release_v47', hfn_manifest_sha256=sha(os.path.join(D, 'hfn/release/release_v47/MANIFEST.json')),
            hfn_events_schema=['event_id', 'root_K', 'form', 'verb', 'transitivity', 'masdar', 'event_review_v36'],
            mutawaa_table='mutawaa_v7.tsv', root_bank='HFN_ROOTS_v11.csv',
            files={k: sha(os.path.join(D, v)) for k, v in F.items()})
json.dump(pins, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(pins['commits'], pins['hfn_manifest_sha256'][:12])
