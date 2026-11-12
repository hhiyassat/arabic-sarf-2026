"""query_inventory.py <release_v50> <OUT.tsv.gz> — جرد الأسئلة المطلوبة (interface, query, role) لاختبار الواجهة لكل سؤال على v50،
مشتقٌّ من CSV وحده بالقاعدة المعلنة في tests/test_v50_api_per_query.py (V50C01 R3): كل حدثٍ في events.csv، وكل جذرٍ لأحداثه،
وكل لفظ ذاتٍ في الروابط، وكل مفتاح dhat_K ليس لفظاً؛ ثم مع الأدوار الستة: ألفاظ الذوات، والأحداث ذات الروابط، وجذور الروابط.
الجرد دليلٌ مستقل عن سجلّ الأسئلة: يُقابَل به السجل مقابلة مجموعات (الناقص والزائد)، لا بالعدد."""
import csv, gzip, os, sys
ROLES = ['فاعل', 'محلّ', 'آلة', 'مكان', 'زمان', 'مصدر']


def inventory(rel):
    rows = list(csv.DictReader(open(os.path.join(rel, 'ahdath_ajnas.csv'), encoding='utf-8')))
    events = list(csv.DictReader(open(os.path.join(rel, 'events.csv'), encoding='utf-8')))
    root_of = {e['event_id']: e['root_K'] for e in events}
    roots = sorted({e['root_K'] for e in events})
    words = sorted({w for r in rows for w in r['dhat'].split('·') if w.strip()})
    keys = sorted({p for r in rows for p in r['dhat_K'].split('·') if p})
    ev_with = sorted({r['event_id'] for r in rows})
    Q = [('event', e['event_id'], '') for e in events] + [('root', r, '') for r in roots] + [('dhat', w, '') for w in words]
    Q += [('dhat', k, '') for k in keys if k not in set(words)]
    Q += [('dhat', w, ro) for w in words for ro in ROLES] + [('event', e, ro) for e in ev_with for ro in ROLES]
    Q += [('root', r, ro) for r in sorted({root_of[r['event_id']] for r in rows}) for ro in ROLES]
    return Q


if __name__ == '__main__':
    Q = inventory(sys.argv[1])
    with gzip.open(sys.argv[2], 'wt', encoding='utf-8') as f:
        f.write('interface\tquery\trole\n')
        for q in Q:
            f.write('\t'.join(q) + '\n')
    print(len(Q), 'queries', len(set(Q)), 'distinct')
