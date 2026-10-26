# arabic-sarf-2026

استخراج العوامل النحوية من الآيات القرآنية وتقطيعها مقطعياً (CV).

| الملف | الوظيفة |
|---|---|
| `extract_operators.py` | يطبّع الرسم العثماني، ويطابق العوامل مع الفهرس، ثم يقطّع الآية ويربط كل عامل بمقاطعه |
| `cv_syllabifier.py` | محوّل CV رباعي الطبقات: Normalize ∘ CVmap ∘ Syllabify ∘ Classify |
| `syllable_report.py` | تقرير HTML مستقلّ: جدول لكل آية، صفٌّ لكل كلمة بمقاطعها الملوّنة حسب النوع ونمط CV والعوامل، مع ملخّص الأنواع |
| `operators_catalog.jsonl` | الفهرس الأساسي (المعاني، والاحتمالات، وعلامات التمييز) |
| `operators_catalog_split_vocalized.csv` | فهرس مكمّل؛ يُضاف منه ما ليس في الأساس فقط (إِنَّ، أَنَّ) |
| `verses*.txt` / `example_output*` | آيات الاختبار ونتائجها (`verses_innama.txt`: إنّ وأخواتها + ما الكافة) |
| `reports/syllable_report.html` | مثالٌ مولَّد من آيات الاختبار الثلاث بتشغيل `syllable_report.py` |

## التشغيل (Python 3 فقط، بلا مكتبات خارجية)

النص يُعالَج كما هو: كل كلمة تُقطَّع مستقلّة بحركاتها المكتوبة، بلا وصل بين الكلمات ولا وقف في آخرها. والتنوين حركة واحدة من جنسه، وهمزة الوصل في أول الكلمة تُنطق ابتداءً.

```
python3 extract_operators.py "إِنَّ ٱللَّهَ غَفُورٌ رَّحِيمٌ"
python3 extract_operators.py -f verses.txt            # آية في كل سطر
python3 extract_operators.py -f verses.txt --json     # JSON Lines
python3 extract_operators.py --uthmani on "مِن قَبْلِ"  # عامِل النص عثمانياً (auto/on/off): يُدرج السكون الضمني
python3 cv_syllabifier.py verse.txt                   # التقطيع وحده
python3 syllable_report.py -f verses.txt verses_inna.txt verses_innama.txt verses_allah.txt -o reports/syllable_report.html
```

خيار `--uthmani {auto,on,off}` (الافتراضي `auto`): يتحكّم في المعاملة العثمانية (السكون الضمني غير المكتوب). `auto` يكتشف تلقائياً بوجود علامة عثمانية (مثل ٱ)؛ `on` يعامل النص عثمانياً دائماً؛ `off` لا يعامله أبداً. مفيد للنص العثماني القصير بلا علامات (`--uthmani on "مِن قَبْلِ"`). متوفّر في `extract_operators.py` و`syllable_report.py`.

## لفظ الجلالة

ليس كمثله شيء: يُعرَف كلمةً واحدة بكل صيغه وما يتصل به من سوابق (وَ، فَ، بِ، تَ، لِ، وهمزة الاستفهام ءَ) ولاحقة «ـمَّ» (`divine_name` في `cv_syllabifier.py`)، **ولا يُقطَّع**: لا مقاطع له ولا يدخل في عدّ المقاطع، ويُعرض في التقطيع كما هو موسوماً «لفظ الجلالة». أما استخراج العوامل (لِ في لِلَّهِ، بِ في بِٱللَّهِ) والتحليل الصرفي فتشمله كغيره. أمثلته في `verses_allah.txt`: ٱللَّه، لِلَّه، فَلِلَّه، تَٱللَّه، ءَآللَّه، ٱللَّهُمَّ — ولا يطابق ما يشبهه رسماً مثل ٱللَّهْو.
