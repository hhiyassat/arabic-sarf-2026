# التدقيق التقني: dayn-audit-01

- الأساس: `algebra-core` 812fdc1. HFN: release_v18 في الطرفين. `PYTHONHASHSEED=0`.
- الأدوات: `tools/snapshot_outputs.py` (طبقة الآية: analyze والوحدات وsentence_geo والأثر والسمات)، و`tools/algebra_quran.py --all` (الطبقة اللغوية)، ومقابلة الجذور بـQAC خارج المستودع.
- كل إصلاحٍ قيس وحده بالترتيب: ترتيب الأسباب، ثم F10، ثم F11، ثم F07a، ثم F07b+F07c.

## التغييرات في الشيفرة

| الملف | التغيير |
|---|---|
| `sarf/algebra.py` `cond_structs` | `'6' not in g['ops']`: لام الأمر (مج 6) في الكلمة تمنع عدّ المجزوم «صالحاً لفعل الشرط» |
| `sarf/algebra.py` `words_text` | `wi + 1` |
| `sarf/algebra.py` `unit_geo` | دليل الاسمية: لاحقة التثنية بشرط sarf.features نفسه (noun_suffix و_rest) |
| `sarf/root.py` `verse_morph` | `stem_info(الجذع + الضمير)` إن خلا الجذع من لاحقة، وتلاه ضميرٌ متصل، وكان في governed |
| `sarf/root.py` `_morph` | `sorted(rooted)` |
| `sarf/pipeline.py` `_root` | governed ∪ مفاتيح agreement (T18) |
| `tools/pipeline_trace.py` | المرحلة ٢ (display وanalysis والقواعد)، و١٢ (α والتحويل وتنبيه وزن الجذع)، و١٣ (البدائل) |
| `tests/test_review_dayn.py`، `tests/test_cell_rules.py`، `tests/test_algebra.py` | اختبارات F07 وF10 وF11، وقاعدة الخنجرية؛ والمواضع المعروضة من الواحد |

## الأعداد

في `measurement.json`: المخالفات لكل خطوة (تغيّر القيم القائمة)، والإضافات، ومقاييس الطبقة اللغوية قبلُ وبعدُ، وانتقالات الجذور بأعدادها، ومواضع الشرط المتغيّرة.
