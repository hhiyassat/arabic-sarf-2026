# -*- coding: utf-8 -*-
"""
sarf.agreement — T18: سمات الفعل من توافقه مع الضمير.

    A(m) = { Φ(p) | R(m,p) }

  Φ(p)    سمات الضمير المنفصل (الشخص والعدد والجنس) من ملف المبنيات: دليل مستقل عن الفعل
  R(m,p)  التوافق بقواعد التصريف الموثّقة: حرف المضارعة ولاحقة الفعل يعيّنان الضمائر التي
          تحتملها الصيغة (لا تُفترض سمات الفعل ثم يُستدلّ بها على التوافق: لا دور)
  A(m)    كل حزمة سمات تحتملها الصيغة احتمالٌ مستقل (تَكْتُبُ: أنتَ، هي)، حتى تخصّصها قرينة معتبرة:
          ضميرٌ منفصل للرفع قبل الفعل مباشرة (أَنْتِ تَكْتُبِينَ). وإن لم يكن Φ(ذلك الضمير) في A(m)
          سُجّلت المخالفة ولا يُخصَّص.
"""
from .affix import stem_info
from .chars import FATHA, DAMMA, KASRA, SUKUN, SHADDA, letters
from .lexicon import MabniLexicon

# R: صيغة الفعل ← الضمائر المنفصلة التي توافقها (قواعد التصريف)
#   المفتاح: (الزمن، حرف المضارعة أو None، توقيع اللاحقة)
R = {
    # المضارع
    ('mudari', 'أ', ''): ['أَنَا'],
    ('mudari', 'ن', ''): ['نَحْنُ'],
    ('mudari', 'ي', ''): ['هُوَ'],
    ('mudari', 'ت', ''): ['أَنْتَ', 'هِيَ'],
    ('mudari', 'ت', 'ين'): ['أَنْتِ'],
    ('mudari', 'ي', 'ون'): ['هُمْ'],
    ('mudari', 'ت', 'ون'): ['أَنْتُمْ'],
    ('mudari', 'ي', 'ان'): ['هُمَا'],
    ('mudari', 'ت', 'ان'): ['أَنْتُمَا', 'هُمَا'],
    ('mudari', 'ي', 'ن'): ['هُنَّ'],
    ('mudari', 'ت', 'ن'): ['أَنْتُنَّ'],
    # «ـُوا» بعد حرفين: واو الجمع، أو واو الأصل في الناقص وبعدها ألف زائدة رسماً (يَدۡعُواْ، يَتۡلُواْ)
    ('mudari', 'ي', 'وا؟'): ['هُوَ', 'هُمْ'],
    ('mudari', 'ت', 'وا؟'): ['أَنْتَ', 'هِيَ', 'أَنْتُمْ'],
    ('mudari', 'ن', 'وا؟'): ['نَحْنُ'],
    ('mudari', 'أ', 'وا؟'): ['أَنَا'],
    # أَفۡعِلۡ: مضارع المتكلم مجزوماً، أو أمر أَفۡعَلَ (أَمۡهِلۡهُمۡ)
    ('mudari', 'أ', 'أفعل'): ['أَنَا', 'أَنْتَ'],
    # الماضي
    ('madi', None, ''): ['هُوَ'],
    ('madi', None, 'تْ'): ['هِيَ'],
    ('madi', None, 'ا'): ['هُمَا'],
    ('madi', None, 'تَا'): ['هُمَا'],
    ('madi', None, 'وا'): ['هُمْ'],
    ('madi', None, 'نَ'): ['هُنَّ'],
    ('madi', None, 'تُ'): ['أَنَا'],
    ('madi', None, 'تَ'): ['أَنْتَ'],
    ('madi', None, 'تِ'): ['أَنْتِ'],
    ('madi', None, 'تُمَا'): ['أَنْتُمَا'],
    ('madi', None, 'تُمْ'): ['أَنْتُمْ'],
    ('madi', None, 'تُنَّ'): ['أَنْتُنَّ'],
    ('madi', None, 'نَا'): ['نَحْنُ'],
    # الأمر
    ('amr', None, ''): ['أَنْتَ'],
    ('amr', None, 'ين'): ['أَنْتِ'],
    ('amr', None, 'ان'): ['أَنْتُمَا'],
    ('amr', None, 'ون'): ['أَنْتُمْ'],
    ('amr', None, 'ن'): ['أَنْتُنَّ'],
}
RULE_NOTE = {'mudari': 'حرف المضارعة «{p}» واللاحقة «{s}»', 'madi': 'لاحقة الماضي «{s}»',
             'amr': 'لاحقة الأمر «{s}»'}

_LEX = None
_PHI = None


def phi():
    """Φ: الضمير المنفصل للرفع ← (الشخص، العدد، الجنس) من ملف المبنيات"""
    global _LEX, _PHI
    if _PHI is None:
        _LEX = MabniLexicon()
        _PHI = {e['form']: (e['extra']['person'], e['extra']['number'], e['extra']['gender'])
                for e in _LEX.entries
                if e['category'] == 'separate_pronoun' and e.get('extra', {}).get('case_slot') == 'nom'}
    return _PHI


def signature(text, info):
    """توقيع اللاحقة من الكتابة: '' أو ون/ين/ان/ن للمضارع والأمر، أو ضمير الماضي بحركته"""
    toks = [(L, set(m)) for L, m in letters(text)]
    if info.get('object'):
        toks = toks[:-len(letters(info['object']))]
    n = len(toks)
    last = lambda k: toks[n - k] if n >= k else ('', set())
    L1, m1 = last(1)
    L2, m2 = last(2)
    L3, m3 = last(3)
    if info['kind'] == 'madi':
        suf = info.get('suffix')
        if suf in ('تُ', 'تَ', 'تِ'):
            return 'تَ' if FATHA in m1 else 'تِ' if KASRA in m1 else 'تُ'
        if suf in ('وا', 'و') or L1 == 'ا' and not m1 and L2 == 'و' and m2 & {SUKUN, DAMMA} and FATHA in m3:
            return 'وا'                                    # ورَمَوۡا، ٱشۡتَرَوُا
        if suf in ('تْ', 'تُمْ', 'تُمَا', 'تُنَّ', 'نَا'):
            return suf
        if L1 == 'ا' and not m1 and L2 == 'ت' and FATHA in m2 and SUKUN not in m3:
            return 'تَا'                                   # كَتَبَتَا
        if L1 == 'ا' and not m1 and FATHA in m2:
            return 'ا'                                     # كَتَبَا
        if L1 == 'ن' and FATHA in m1 and SUKUN in m2:
            return 'نَ'                                    # كَتَبْنَ
        return ''
    # المضارع والأمر
    if L1 == 'و' and m1 == {SUKUN} and FATHA in m2 or L1 == 'ن' and FATHA in m1 and L2 == 'و' and m2 == {SUKUN} \
            and FATHA in m3:
        return 'ون'                                        # جمع الناقص: تَخۡشَوۡهُمۡ، يَخۡشَوۡنَ
    if L1 == 'ن' and FATHA in m1 and L2 == 'و' and not m2 and DAMMA in m3 and info['kind'] == 'mudari' and n == 4:
        return ''                                          # يَكُونَ: الواو والنون أصليتان في المفرد الأجوف
    if info.get('suffix') == 'وا' and info['kind'] == 'mudari' and n == 5:
        return 'وا؟'                                       # ي + حرفان + ـُوا: يَدۡعُواْ (مفرد) أم يَدۡعُوا (جمع)؟
    if info.get('suffix') in ('وا', 'و') or L1 == 'ن' and FATHA in m1 and L2 == 'و' and not m2 and DAMMA in m3 or \
            L1 == 'ن' and SHADDA in m1 and FATHA in m1 and DAMMA in m2:
        return 'ون'                                        # لَتَرَوُنَّ، لَتَرۡكَبُنَّ: الجمع قبل نون التوكيد (والواو محذوفة)
    if L1 == 'ن' and SHADDA in m1 and FATHA in m1 and KASRA in m2:
        return 'ين'                                        # المخاطبة قبل نون التوكيد
    if info.get('suffix') == 'ي' or L1 == 'ن' and FATHA in m1 and L2 == 'ي' and not m2 and KASRA in m3:
        return 'ين'
    if L1 == 'ن' and KASRA in m1 and L2 == 'ا' and not m2 or L1 == 'ا' and not m1 and FATHA in m2 and n > 3:
        return 'ان'
    if L1 == 'ن' and FATHA in m1 and SUKUN in m2 and SHADDA not in m1:
        return 'ن'
    if info['kind'] == 'mudari' and info.get('prefix') == 'أ' and FATHA in toks[0][1] and m1 == {SUKUN} and \
            KASRA in m2 and n == 4 and SUKUN in toks[1][1]:
        return 'أفعل'                                      # أَمۡهِلۡ: مضارع المتكلم أو أمر أَفۡعَلَ
    return ''


def agreement(text, info=None, shape_only=False):
    """→ dict(features=[(شخص، عدد، جنس)], pronouns=[...], rule=…) أو None إن لم يكن فعلاً بدليل.
    shape_only: يُحسب A(m) لصيغة على شكل المضارع وإن لم يثبت أنها فعل (يُستعمل مع القرينة وحدها)"""
    info = info or stem_info(text)
    if info['kind'] not in ('madi', 'amr', 'mudari'):
        return None
    if info['pos'] != 'verb' and not (shape_only and info['kind'] == 'mudari'):
        return None
    sig = signature(text, info)
    key = (info['kind'], info['prefix'] if info['kind'] == 'mudari' else None, sig)
    prons = R.get(key)
    if not prons:
        return None
    P = phi()
    feats = [P[p] for p in prons if p in P]
    note = RULE_NOTE[info['kind']].format(p=info['prefix'] or '', s=sig or '—')
    return dict(features=feats, pronouns=prons, rule=note, narrowed_by=None, conflict=None,
                kind=info['kind'], signature=sig, voice=voice(text, info))


def voice(text, info):
    """المبني للمجهول من الكتابة: الماضي بضمّ أوله (قُتِلَ)؛ والمضارع بضمّ حرف المضارعة وفتحٍ أو ألفِ مدٍّ
    قبل آخره (يُولَدۡ، يُسَاقُونَ)؛ والمعلوم المزيد بالضم قبله كسرة (يُعَذِّبُ، يُحۡبِبۡ)"""
    toks = [(L, set(m)) for L, m in letters(text)]
    if info.get('object'):
        toks = toks[:-len(letters(info['object']))]
    if info['kind'] == 'madi':
        # فُعِلَ: ضمّ الأول وكسرٌ بعده (قُتِلَ، كُوِّرَتۡ، أُزۡلِفَتۡ)؛ وضمّ أول الأجوف المعلوم بلا كسر (زُرۡتُمۡ)
        core = toks[1:] if len(toks) > 2 and toks[0][0] in ('و', 'ف') and toks[0][1] == {FATHA} else toks
        # والمضعَّف: ضمّ الأول ثم شدة (حُقَّتۡ، مُدَّتۡ)، إلا نون «كُنَّا» المدغمة في الضمير
        doubled = len(core) > 1 and SHADDA in core[1][1] and core[1][0] != 'ن'
        # وفُوعِلَ وأُفۡعِلَ من المعتل: ضمٌّ ثم واو مدّ (أُوتُوا، قُوتِلُوا)
        doubled = doubled or len(core) > 2 and core[1][0] == 'و' and not core[1][1]
        return 'passive' if core and DAMMA in core[0][1] and (any(KASRA in m for _, m in core[1:]) or doubled) \
            else 'active'
    if info['kind'] != 'mudari' or not toks or DAMMA not in toks[0][1]:
        return 'active'
    # الجسم: بلا النون الأخيرة وحروف الإسناد (ـونَ، ـينَ، ـانِ، ـُوا، ـنَّ)
    body = list(toks)
    if body and body[-1][0] == 'ن':
        body = body[:-1]
    if body and body[-1][0] == 'ا' and not body[-1][1]:
        body = body[:-1]
    if body and body[-1][0] in ('و', 'ي', 'ا') and not body[-1][1]:
        body = body[:-1]
    if len(body) < 3:
        return 'active'
    pen = body[-2]
    if FATHA in pen[1]:
        return 'passive'
    if pen[0] == 'ا' and not pen[1]:
        return None                                     # يُسَاقُ (مجهول) أم يُرَاءُ (معلوم فاعَلَ)؟ لا تفصل الكتابة
    return 'active'


def narrow(agr, prev_word):
    """القرينة: ضمير رفع منفصل قبل الفعل مباشرة يخصّص A(m) إن كان فيه، وإلا تُسجَّل المخالفة"""
    if not agr or not prev_word:
        return agr
    P = phi()
    # بالشكل كاملاً لا بالحروف وحدها: أَنْتَ وأَنْتِ حروفهما واحدة
    key = [(L, frozenset(m)) for L, m in letters(prev_word)]
    form = next((f for f in P if [(L, frozenset(m)) for L, m in letters(f)] == key), None)
    if not form:
        return agr
    if P[form] in agr['features']:
        return dict(agr, features=[P[form]], pronouns=[form], narrowed_by=form)
    return dict(agr, conflict=form)


def verse_agreement(segs, governed=None):
    """لكل جذعٍ فعلٍ بدليل في الآية: (رقم الكلمة، رقم الخانة) ← A(m) مخصَّصاً بالقرينة إن وُجدت.
    governed: الجذوع التي ثبتت فعليتها بعاملٍ مقبول فيها (لَنۡ نَّبۡرَحَ) → اسم العامل"""
    governed = governed or {}
    out = {}
    for seg in segs:
        wi = seg['word_index']
        for s in seg['slots']:
            if s['type'] != 'جذع':
                continue
            prev = None
            if s['index'] == 0 and wi > 0:
                pslots = segs[wi - 1]['slots']
                if len(pslots) == 1 and pslots[0]['type'] == 'مبني':
                    prev = pslots[0]['text']
            agr = agreement(s['text'])
            if agr is None and (wi, s['index']) in governed:
                agr = agreement(s['text'], dict(stem_info(s['text']), pos='verb'))
                if agr is not None:
                    agr['verb_by_operator'] = governed[(wi, s['index'])]
            if agr is not None:
                out[(wi, s['index'])] = narrow(agr, prev)
                continue
            # صيغة على شكل المضارع لم يثبت أنها فعل: تثبت بالتوافق مع ضمير الرفع قبلها
            # (R بقاعدة التصريف، وΦ من الملف؛ فلا دور): أَنْتِ تَكْتُبِينَ
            agr = agreement(s['text'], shape_only=True)
            if agr is not None and prev:
                n = narrow(agr, prev)
                if n['narrowed_by']:
                    out[(wi, s['index'])] = dict(n, verb_by_agreement=True)
    return out
