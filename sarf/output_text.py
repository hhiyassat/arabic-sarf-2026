# -*- coding: utf-8 -*-
"""
sarf.output_text — الناتج النصي وJSON لتحليل الآية.
"""
from . import syllabify as cv
from .segment import unit_view, STEM
from .affix import stem_info
from .root import WAZN
from .status import STATUS_AR, BLOCKED


def word_irab(a, wi):
    """→ [(نص الخانة، عبارة الإعراب، حالة العامل)] للكلمة wi، من علاقات العوامل غير الممنوعة"""
    status = {(f['word_index'], f['operator'], f['group']): f['status'] for f in a['operators']}
    out = []
    for r in a.get('relations', []):
        st = STATUS_AR.get(status.get((r['word_index'], r['operator'], r['group'])), '')
        if r['word_index'] == wi and r.get('zaida'):
            slot = a['segments'][wi]['slots'][r['slot']]['text']
            out.append((slot, 'حرف جر زائد للتوكيد (ترجيح صاحب النظرية)', st))
        k = r.get('khabar')
        if k and k['word_index'] == wi:
            out.append((k['text'], f"خبر «{r['operator']}» مقدَّم في محلّ نصب", st))
        t = r['target']
        if t and t['word_index'] == wi and r.get('role'):
            out.append((t['text'], r['role'], st))
    # بنية الجذع وحدها: الماضي والأمر مبنيان، وعلامة البناء من الكتابة
    for slot in a['segments'][wi]['slots']:
        if slot['type'] != STEM:
            continue
        m = stem_info(slot['text'])
        if m['pos'] != 'verb' or m['kind'] not in ('amr', 'madi'):
            continue
        if m['kind'] == 'amr':
            role = 'فعل أمر مبني على ' + ('حذف النون' if m['suffix'] in ('وا', 'و', 'ي') else 'السكون')
            if m.get('moved'):
                role += '، وحُرِّك بالكسر لالتقاء الساكنين'
            if not m['suffix']:
                role += '، والفاعل ضمير مستتر تقديره «أَنْتَ»'
        else:
            role = 'فعل ماضٍ مبني'
        if m['suffix'] in ('وا', 'و'):
            role += '، وواو الجماعة فاعل'
        elif m['suffix'] == 'ي':
            role += '، وياء المخاطبة فاعل'
        elif m['suffix'] == 'تْ':
            role += '، والتاء للتأنيث'
        elif m['suffix']:
            role += f"، والضمير «{m['suffix']}» فاعل"
        out.append((slot['text'], role, 'بنية'))
    # فاعل المضارع بالتوافق (T18)
    for agr in a.get('agreement', []):
        if agr['word_index'] != wi or agr.get('kind') != 'mudari':
            continue
        slot = a['segments'][wi]['slots'][agr['slot']]
        passive = agr.get('voice') == 'passive'
        unknown = 'voice' in agr and agr['voice'] is None      # يُسَاقُونَ: لا تفصل الكتابة بين المعلوم والمجهول
        if agr.get('signature') in SUBJECT_SUFFIX:
            role = SUBJECT_SUFFIX[agr['signature']] + (' نائب فاعل' if passive else
                                                       ' فاعل أو نائب فاعل' if unknown else ' فاعل')
        else:
            role = _hidden_subject(agr['pronouns'], 'نائب الفاعل' if passive else
                                   'الفاعل أو نائبه' if unknown else 'الفاعل')
        if passive:
            role = 'مبني للمجهول، و' + role
        if agr.get('verb_by_agreement'):
            role = f"فعل مضارع بالتوافق مع «{agr['narrowed_by']}» قبله، و" + role
        elif agr.get('narrowed_by'):
            role += f"، بقرينة «{agr['narrowed_by']}» قبله"
        if agr.get('conflict'):
            role += f"؛ ولا يوافق «{agr['conflict']}» قبله"
        out.append((slot['text'], role, 'T18'))
    # الجذر والصيغة (T19c)
    for m in a.get('morph', []):
        if m['word_index'] != wi or m['status'] != 'accepted':
            continue
        slot = a['segments'][wi]['slots'][m['slot']]
        root = ' '.join(m['root'])
        if m['level'] == 'event':
            ev = m['event']
            role = (f"الجذر «{root}»، والوزن {ev['hfn_form']}؛ شاهده في HFN: {ev['verb']}" +
                    (f" ← {ev['masdar']}" if ev.get('masdar') else '') +
                    (f"، ومعنى الصيغة: {ev['meaning']}" if ev.get('meaning') else ''))
        else:
            role = f"الجذر «{root}» مسجَّل في HFN، والوزن {WAZN.get(m['form_class'], m['form_class'])} بالقالب، ولا حدث مسجَّل به"
        out.append((slot['text'], role, 'T19c'))
    return out


def _hidden_subject(prons, label='الفاعل'):
    """الاستتار واجبٌ مع المتكلم والمخاطب، وجائزٌ مع الغائب: فقد يكون الفاعل اسماً ظاهراً بعده"""
    near = [p for p in prons if not p.startswith('ه')]
    far = [p for p in prons if p.startswith('ه')]
    parts = []
    if near:
        parts.append(f'{label} ضمير مستتر وجوباً تقديره ' + ' أو '.join(f'«{p}»' for p in near))
    if far:
        parts.append(('أو ' if near else '') + f'{label} للغائب' + ('ة' if far == ['هِيَ'] else '') +
                     ': ضمير مستتر تقديره ' + ' أو '.join(f'«{p}»' for p in far) + '، أو اسم ظاهر بعده')
    return '، '.join(parts)


SUBJECT_SUFFIX = {'ون': 'واو الجماعة', 'ين': 'ياء المخاطبة', 'ان': 'ألف الاثنين', 'ن': 'نون النسوة'}


def relation_text(r):
    """العامل ← المعمول: الحالة المتوقَّعة والعلامة المكتوبة"""
    if r is None:
        return '—'
    if r['note'] and r['target'] is None:
        return r['note']
    t = r['target']
    if t is None:
        return 'لا معمول في النص'
    out = f"{t['text']} ({t['type']})"
    if r['expected']:
        out += f"  متوقَّع: {r['expected']}"
    if r['observed'] == 'محلاً':
        out += f"  في محلّ {r['expected']}" if r['expected'] else '  مبني'
    elif r['observed']:
        out += f"  مكتوب: {r['observed']}"
    if r['consistent'] is not None:
        out += '  ✓' if r['consistent'] else '  ✗ يخالف العلامة المكتوبة'
    if r['note']:
        out += f"  — {r['note']}"
    return out

def text_report(a):
    out = [f"الآية:    {a['verse']}", f"المُطبَّع: {a['normalized']}"]
    out.append('')
    out.append(f"العوامل المستخرجة: {len(a['operators'])}")
    out.append('-' * 80)
    for f in a['operators']:
        top = f['meanings'][0]
        out.append(f"[{f['word_index']}] {f['word']}  ⟵  {f['operator']}  (مج {f['group']}: {f['operator_class']})")
        out.append(f"     طريقة={f['method']}  ثقة={f['confidence']}  الحكم={STATUS_AR.get(f.get('status'), '')}"
                   + (f"  بقية={f['host_rest']}" if f.get('host_rest') else '')
                   + (f"  ملاحظة: {f['note']}" if f.get('note') else ''))
        if f.get('reject_reason'):
            out.append(f"     سبب المنع: {f['reject_reason']}")
        j = f.get('judgement')
        if j:
            if j['proof']:
                out.append(f"     الأدلة: {' | '.join(j['proof'])}")
            if j['deferred_because']:
                out.append(f"     سبب التأجيل: {' | '.join(j['deferred_because'])}")
        if f.get('slot'):
            out.append(f"     الخانة: [{f['slot']['text']}] عامل — لا يُقطَّع")
        if f.get('status') != BLOCKED:
            out.append(f"     المعمول: {relation_text(f.get('relation'))}")
        out.append(f"     المعاني المرشحة:  " + ' | '.join(
            f"{m['label']} ({m['prior'] if m['prior'] is not None else '—'})" for m in f['meanings']))
        out.append(f"     العمل: {top['effect']}")
        out.append('')
    out.append('=' * 80)
    out.append(cv.report(a['syll']))
    out.append('')
    out.append(unit_view(a['segments']))
    irab = [(w['word'], x) for w in a['segments'] for x in word_irab(a, w['word_index'])]
    if irab:
        out.append('')
        out.append('الإعراب:')
        for word, (slot, role, st) in irab:
            out.append(f"  {word:<16} {slot}: {role}  [{st}]")
    return '\n'.join(out)

def to_json(a):
    d = {k: v for k, v in a.items() if k != 'syll'}
    r = a['syll']
    d['syllable_counts'] = dict(r['counts'])
    d['cv_line'] = r['cv_line']
    d['events'] = dict(r['events'])
    return d
