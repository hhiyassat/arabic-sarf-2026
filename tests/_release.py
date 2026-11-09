"""tests/_release.py — فصل اختبارات الإصدار المستهدف عن اختبارات v36 التاريخية (SARF_FINAL_COMPLETION_AND_ACCEPTANCE_01 §٣).
التأكيد الذي يحمل حقيقةً من بيانات v36 يبقى بنصّه في التشغيل التاريخي (SARF_HFN_RELEASE_OK=release_v36)، ولا يُغيَّر متوقَّعه لإخفاء
اختلاف البيانات؛ وفي الإصدار المستهدف يُفحص السلوك الصحيح على بياناته بسببه المكتوب (DATA_REASONS)."""
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
from sarf.root import hfn, HFN_TARGET

RELEASE = hfn().release
TARGET = HFN_TARGET['release']
HISTORICAL = RELEASE != TARGET
DATA_REASONS = {
    'QAWL_QAYL': 'v47 يضيف حدث «قَالَ يَقِيلُ» (قيل، الباب I)؛ فـ«قَالَ/قَالَتْ/قَالُوا» تحقّق قول وقيل معاً، والكتابة لا تحسم (التباسٌ صحيح '
                 'من المورد)؛ و«قُلْنَا» بضمة الفاء تعيّن قول (قاعدة B4)، فهي الشاهد الموجب في الإصدار المستهدف',
}
# الشاهد الموجب للفعل الأجوف المقبول بوجهٍ واحد ذي سابقة: في v36 «وَقَالَتْ»، وفي المستهدف «وَقُلْنَا» (DATA_REASONS['QAWL_QAYL'])
QAWL_WITNESS = 'وَقَالَتْ' if RELEASE == 'release_v36' else 'وَقُلْنَا'


if __name__ == '__main__':
    # وحدةٌ مساعدة لا اختبار؛ وتشغيلها وحدها يطبع هوية الإصدار المحمَّل
    print(f'RELEASE={RELEASE} TARGET={TARGET} HISTORICAL={HISTORICAL} pin={hfn().pin.get("mode")}')
