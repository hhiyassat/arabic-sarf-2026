"""tools/upstream_qac_transitions.py — انتقالات حكم الجذر بين تشغيلين، مقيسةً بمدوّنة QAC (للقياس وحده، لا مدخلاً ولا مراجعةً من المالك).

    python3 tools/upstream_qac_transitions.py <base.dump.jsonl> <other.dump.jsonl> <OUT.json>

المدخلان سجلّا SARF_ROOT_DUMP من tools/eval_root.py (لكل وقوع فعلٍ مقابَلٍ بـQAC: الحالة والجذر والجذر في QAC). لكل وقوعٍ حالته في الطرفين:
CORRECT (جذرٌ مقبول = جذر QAC)، WRONG (مقبولٌ يخالفه)، NOT_ACCEPTED (مؤجَّل أو مرجَّح أو غير منطبق)؛ ويُعدّ كل انتقال، ويُعلن ما انتقل من
CORRECT إلى غيره بمواضعه. وQAC ليس حكم المالك: الانتقال إليه أو عنه قياسٌ، لا إثبات صواب.
"""
import collections, json, sys

HZ = str.maketrans('أإؤئآ', 'ءءءءء')


def state(r):
    if r.get('status') != 'accepted' or not r.get('root'):
        return 'NOT_ACCEPTED'
    return 'CORRECT' if (r['root'] or '').translate(HZ) == (r.get('gold') or '').translate(HZ) else 'WRONG'


def load(p):
    out = {}
    for l in open(p, encoding='utf-8'):
        r = json.loads(l)
        out[(r['loc'], r['text'])] = r
    return out


def main():
    A, B, OUT = load(sys.argv[1]), load(sys.argv[2]), sys.argv[3]
    T = collections.Counter()
    regress, improve, other = [], [], []
    for k in sorted(set(A) | set(B)):
        a, b = A.get(k), B.get(k)
        if a is None or b is None:
            T['only_in_' + ('other' if a is None else 'base')] += 1
            continue
        sa, sb = state(a), state(b)
        T[f'{sa}→{sb}'] += 1
        rec = dict(loc=k[0], text=k[1], base=dict(state=sa, status=a['status'], root=a.get('root'), form=a.get('form')),
                   other=dict(state=sb, status=b['status'], root=b.get('root'), form=b.get('form'), reason=b.get('reason')), qac_root=a.get('gold'))
        if sa == 'CORRECT' and sb != 'CORRECT':
            regress.append(rec)
        elif sb == 'CORRECT' and sa != 'CORRECT':
            improve.append(rec)
        elif sa != sb or a.get('root') != b.get('root') or a['status'] != b['status']:
            other.append(rec)
    json.dump(dict(base=sys.argv[1], other=sys.argv[2], transitions=dict(sorted(T.items())), correct_to_not_correct=regress,
                   not_correct_to_correct=improve, other_changes=other,
                   note='QAC للقياس وحده؛ و«CORRECT» موافقة QAC لا حكم المالك. وما لم يُراجع لغوياً يبقى غير محكوم'),
              open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(json.dumps(dict(transitions=dict(sorted(T.items())), regress=len(regress), improve=len(improve), other=len(other)), ensure_ascii=False))


if __name__ == '__main__':
    main()
