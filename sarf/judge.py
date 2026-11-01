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


MABNI_KIND = {'relative': 'اسم موصول مبني', 'attached_pronoun': 'ضمير متصل مبني', 'separate_pronoun': 'ضمير منفصل مبني',
              'demonstrative': 'اسم إشارة مبني', 'interrogative_noun': 'اسم استفهام مبني', 'conditional_noun': 'اسم شرط مبني'}


def _mabni_kind(segs, r):
    """نوع المعمول المبني من ملف المبنيات (الَّذِي: اسم موصول، هِ: ضمير متصل)، لا «ضمير» على الإطلاق"""
    t = r.get('target') or {}
    try:
        sl = segs[t['word_index']]['slots'][t['slot']]
    except (KeyError, IndexError, TypeError):
        return 'مبنيٌّ من ملف المبنيات'
    return MABNI_KIND.get(sl.get('note'), 'مبنيٌّ من ملف المبنيات' + (f' ({sl.get("note")})' if sl.get('note') else ''))


def _prior_governor(rels, wi, effect):
    """عاملٌ في الكلمة السابقة أو في الكلمة نفسها قبلُ يقتضي الأثر نفسه (إِنۡ الشرطية قبل «لَا»)"""
    return any(x['word_index'] in (wi - 1,) and x.get('expected') == effect for x in rels)


def judge(cands, segs, rels):
    # المانع المكتوب أولاً: ما خالفت العلامةُ المكتوبة أثرَه ممنوعٌ قبل الحكم على منافسيه، فلا يُعدّ منافساً قائماً
    marked_off = set()
    for c in cands:
        if c['status'] == BLOCKED:
            marked_off.add((c['word_index'], c['operator'], c['group']))
            continue
        r = next((r for r in rels if r['word_index'] == c['word_index'] and
                  r['operator'] == c['operator'] and r['group'] == c['group']), None)
        if r is not None and r.get('consistent') is False and r.get('observed') in ('رفع', 'نصب', 'جر', 'جزم'):
            marked_off.add((c['word_index'], c['operator'], c['group']))
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
                  if (o[0], o[1]) != (c['operator'], c['group']) and (c['word_index'], o[0], o[1]) not in marked_off]
        if rivals and r is not None and r.get('consistent') is True and r.get('expected') in ('جزم', 'نصب'):
            # المنافس الذي لا أثر له في المعمول (لا النافية) تنفيه العلامة المكتوبة: الجزم أو النصب مكتوب، ولا يُحدثه هو؛
            # ما لم يسبق الكلمةَ عاملٌ آخر يقتضي الأثر نفسه فيفسّره (إِنۡ لَا تَغۡفِرۡ لِي)
            excluded = []
            for o in (slot['operators'] if slot else []):
                if (o[0], o[1]) == (c['operator'], c['group']):
                    continue
                ro = next((x for x in rels if x['word_index'] == c['word_index'] and x['operator'] == o[0] and x['group'] == o[1]), None)
                if ro is not None and not ro.get('expected') and not _prior_governor(rels, c['word_index'], r['expected']):
                    excluded.append(f"{o[0]} (مج {o[1]})")
            if excluded:
                proof.append(f"المنافس {'، '.join(excluded)} لا يُحدث {r['expected']}، و{r['expected']} مكتوبٌ في معموله ولا عامل قبله يفسّره")
                rivals = [x for x in rivals if x not in excluded]
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
            proof.append(f"الشرط: معموله {_mabni_kind(segs, r)} في محلّ {r['expected']}")
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
        if r is not None and r.get('consistent') is False and r.get('observed') in ('رفع', 'نصب', 'جر', 'جزم'):
            # العلامة المكتوبة تخالف أثره (وَٱمۡرَأَتَانِ مرفوعةٌ بعد واوٍ جارّة): مانعٌ مثبت بالكتابة، لا نقصُ دليل
            c['status'] = BLOCKED
            c['reject_reason'] = f"العلامة المكتوبة على «{(r.get('target') or {}).get('text', '')}» ({r['observed']}) " \
                                 f"تخالف أثره ({r['expected']})"
            c['judgement'] = dict(proof=proof, deferred_because=[], blocked_by=c['reject_reason'])
            continue
        if r is not None and r.get('note') and 'حذف حرف العلة' in r['note'] and not r.get('consistent'):
            why.append('نقص تغطية: حذف حرف العلة جزماً لا يُفحص بعدُ بالجذر')
        c['status'] = DEFERRED if why else ACCEPTED
        c['judgement'] = dict(proof=proof, deferred_because=why)
    return cands
