# -*- coding: utf-8 -*-
"""
sarf.judge — الحكم بالقبول (T07، T09): لا يُقبل مرشَّح إلا بدليل إيجابي.

يُقبل المرشَّح المؤجَّل إذا اجتمعت أربعة:
  (أ) السبب: طوبق العامل بحروفه وحركة واحدة على الأقل (لا مطابقة رسمية بلا تشكيل)
  (ب) الشرط: ثبت أثره في معموله بالكتابة (العلامة توافق المتوقَّع)، أو كان معموله ضميراً
      مبنياً من الملف في موضع أثره (عَلَيْهِ، إِنَّهُ، كُنْتُمْ)، أو كان مكفوفاً بما وهي متصلة به
  (ج) الموانع: فُحصت قواعد المنع المسجَّلة له (evidence) فلم يثبت منها شيء
  (د) المنافسة: لا مرشَّح آخر غير ممنوع على خانته نفسها؛ والكاف السابقة يُنافسها كونها أصلية
      ما لم تلها «أل» أو مبني
وإلا بقي مؤجَّلاً، ويُسجَّل سبب التأجيل. والإقصاء وحده لا يكفي للقبول (T19i).
"""
from .status import DEFERRED, BLOCKED, ACCEPTED


def _kaf_certain(seg, slot, r):
    """الخانة بعد الكاف في كلمتها: أل، أو مبني من الملف"""
    if not slot:
        return False
    nxt = next((s for s in seg['slots'] if s['index'] == slot['index'] + 1), None)
    return bool(nxt) and nxt['type'] in ('أل', 'مبني', 'لفظ الجلالة')


def judge(cands, segs, rels):
    for c in cands:
        if c['status'] == BLOCKED:
            continue
        seg = segs[c['word_index']]
        slot = next((s for s in seg['slots'] if s['type'] == 'عامل'
                     and [c['operator'], c['group']] in [list(o) for o in s['operators']]), None)
        r = next((r for r in rels if r['word_index'] == c['word_index'] and
                  r['operator'] == c['operator'] and r['group'] == c['group']), None)
        why, proof = [], []
        # (أ) السبب
        if c.get('vocal_checks', 0) > 0:
            proof.append('السبب: مطابقة الحروف والحركة')
        else:
            why.append('المطابقة رسمية بلا تشكيل')
        # (د) المنافسة
        rivals = [f"{o[0]} (مج {o[1]})" for o in (slot['operators'] if slot else [])
                  if (o[0], o[1]) != (c['operator'], c['group'])]
        if rivals:
            why.append('تحليلات منافسة على الخانة: ' + '، '.join(rivals))
        # (ب) الشرط
        if r is None:
            why.append('لا علاقة مسجَّلة')
        elif c.get('kaffa'):
            proof.append('الشرط: «ما» الكافة متصلة به')
        elif r['consistent'] is True:
            proof.append(f"الشرط: العلامة المكتوبة توافق أثره ({r['expected']})")
        elif r['observed'] == 'محلاً' and r['expected']:
            proof.append(f"الشرط: معموله ضمير مبني في محلّ {r['expected']}")
        else:
            why.append('أثره في معموله لم يثبت بالكتابة' + (f" ({r['note']})" if r.get('note') else ''))
        # (د') الكاف السابقة: كلماتٌ كثيرة أولها كاف أصلية (كَرِيمٍ، كَبِدٍ)، فقراءة الكاف أصليةً منافسٌ قائم
        #      ما لم يثبت أنها سابقة: أن يليها «أل»، أو مبني (ضمير)، أو «مِثْل» (الكاف الزائدة)
        if c['method'].startswith('proclitic') and c['operator'] == 'كَ' and r and r.get('target') and \
                not r.get('zaida') and not _kaf_certain(seg, slot, r):
            why.append('الكاف قد تكون من أصل الكلمة: لا «أل» ولا ضمير بعدها')
        # (ج) الموانع: ما فُحص مسجَّل في evidence
        checked = c.get('checked', [])
        if checked:
            proof.append('الموانع المفحوصة: ' + '، '.join(checked))
        c['status'] = DEFERRED if why else ACCEPTED
        c['judgement'] = dict(proof=proof, deferred_because=why)
    return cands
