# arabic-sarf-2026

استخراج العوامل النحوية من الآيات القرآنية وتقطيعها مقطعياً (CV).

| الملف | الوظيفة |
|---|---|
| `extract_operators.py` | يطبّع الرسم العثماني، ويطابق العوامل مع الفهرس، ثم يقطّع الآية ويربط كل عامل بمقاطعه |
| `cv_syllabifier.py` | محوّل CV رباعي الطبقات: Normalize ∘ CVmap ∘ Syllabify ∘ Classify |
| `operators_catalog.jsonl` | الفهرس الأساسي (المعاني، والاحتمالات، وعلامات التمييز) |
| `operators_catalog_split_vocalized.csv` | فهرس مكمّل؛ يُضاف منه ما ليس في الأساس فقط (إِنَّ، أَنَّ) |
| `verses*.txt` / `example_output*` | آيات الاختبار ونتائجها |

## التشغيل (Python 3 فقط، بلا مكتبات خارجية)

```
python3 extract_operators.py "إِنَّ ٱللَّهَ غَفُورٌ رَّحِيمٌ"
python3 extract_operators.py -f verses.txt            # آية في كل سطر
python3 extract_operators.py -f verses.txt --json     # JSON Lines
python3 extract_operators.py -f verses.txt --mode WAQF_RUN --no-idgham
python3 cv_syllabifier.py verse.txt                   # التقطيع وحده
```
