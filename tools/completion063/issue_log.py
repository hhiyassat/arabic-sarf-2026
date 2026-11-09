"""issue_log.py <قبل.json> <بعد.json> <OUT.json> [--md OUT.md]
سجلّ القضايا قبل/الإصلاح/الدليل/بعد (SARF_COMPLETION_FROM_REPORT_063 §١ و§١٣): يقابل سجلّ الأساس بسجلّ الرأس بالنوع والموضع.
التصنيف النهائي لكل قضيةٍ من سجلّ الرأس إن بقيت، ومن سجلّ الأساس إن زالت؛ والقضية التي لم يصنّفها الأساس (UNCLASSIFIED) تُصنَّف
بما صنّفها الرأس. والإصلاح يُنسب إلى الدفعة بنوع القضية (FIX_BY)، ويُتحقّق منه بزوالها أو تغيّر مخرجها في سجلّ الرأس."""
import json, sys, collections

FIX_BY = {'FACE_CONTRADICTION': ('C063-B1', 'sarf/reconcile.py: features_final من الأوجه الحيّة', 'tests/test_reconcile.py؛ recon_b1.json'),
          'UNGOVERNED': ('C063-B3', 'sarf/relations.py: ungoverned_kind + O03', 'tests/test_c063_objects.py K05/K09؛ axes cmp'),
          'UNIT_UNCLOSED': ('C063-B4', 'sarf/algebra.py align_radicals/_weak_lam_barred؛ sarf/root.py الأجوف', 'tests/test_c063_morph.py؛ snap/eval_root'),
          'PARAGRAPH_BOUNDARY': ('C063-B5', 'sarf/algebra.py pb_conditions', 'tests/test_c063_paragraph.py G01–G05')}
A = json.load(open(sys.argv[1], encoding='utf-8'))
B = json.load(open(sys.argv[2], encoding='utf-8'))
key = lambda i: (i['kind'], i['occurrence_id'])
bi = {key(i): i for i in B['issues']}
rows = []
for i in A['issues']:
    j = bi.get(key(i))
    fx = FIX_BY.get(i['kind'], (None, None, None))
    cls = (j or i)['classification']
    if cls == 'UNCLASSIFIED' and j:
        cls = j['classification']
    if j is None:
        state = 'RESOLVED'
    elif j['actual_output'] != i['actual_output'] or j.get('resolved_in_this_run'):
        state = 'CHANGED' if not j.get('resolved_in_this_run') else 'RESOLVED_IN_FINAL_FEATURES'
    else:
        state = 'UNCHANGED'
    rows.append(dict(issue_id=i['issue_id'], kind=i['kind'], occurrence_id=i['occurrence_id'], section=i['section'],
                     classification=cls, classification_basis=(j or i)['classification_basis'],
                     before=i['actual_output'], fix=(fx[0] + ': ' + fx[1]) if state != 'UNCHANGED' and fx[0] else None,
                     evidence=fx[2] if state != 'UNCHANGED' else None, after=(j['actual_output'] if j else 'زالت القضية من مخرج الرأس'),
                     state=state, rule_or_function=i['rule_or_function'], dependency=i['dependency'],
                     required_behavior=i['required_behavior'], verification=i['verification']))
for k, j in bi.items():
    if k not in {key(i) for i in A['issues']}:
        rows.append(dict(issue_id=j['issue_id'] + '+', kind=j['kind'], occurrence_id=j['occurrence_id'], section=j['section'],
                         classification=j['classification'], classification_basis=j['classification_basis'], before=None, fix=None,
                         evidence=None, after=j['actual_output'], state='NEW_IN_HEAD', rule_or_function=j['rule_or_function'],
                         dependency=j['dependency'], required_behavior=j['required_behavior'], verification=j['verification']))
summ = dict(before=A['summary'], after=B['summary'], states=dict(collections.Counter(r['state'] for r in rows)),
            final_classes=dict(collections.Counter(r['classification'] for r in rows)),
            by_kind_state={f'{a}|{b}': n for (a, b), n in collections.Counter((r['kind'], r['state']) for r in rows).items()})
json.dump(dict(summary=summ, rows=rows), open(sys.argv[3], 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
if '--md' in sys.argv:
    with open(sys.argv[sys.argv.index('--md') + 1], 'w', encoding='utf-8') as f:
        f.write(f"# سجلّ القضايا قبل/بعد — {A['summary']['ref']}\n\nالأساس `{A['summary']['head'][:10]}` ← الرأس `{B['summary']['head'][:10]}`\n\n")
        f.write('| الحالة | العدد |\n|---|---|\n' + ''.join(f'| {k} | {v} |\n' for k, v in summ['states'].items()))
        f.write('\n| التصنيف | العدد |\n|---|---|\n' + ''.join(f'| {k} | {v} |\n' for k, v in summ['final_classes'].items()))
        f.write('\n| issue_id | الموضع | التصنيف | قبل | الإصلاح | الدليل | بعد | الحالة |\n|---|---|---|---|---|---|---|---|\n')
        for r in rows:
            f.write('| ' + ' | '.join(str(r[k] or '—').replace('|', '¦').replace('\n', ' ')[:200] for k in
                                      ('issue_id', 'occurrence_id', 'classification', 'before', 'fix', 'evidence', 'after', 'state')) + ' |\n')
print(json.dumps(summ, ensure_ascii=False))
