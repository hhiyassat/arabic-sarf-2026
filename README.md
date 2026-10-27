# arabic-sarf-2026

استخراج العوامل النحوية من الآيات القرآنية وتقطيعها مقطعياً (CV).

## البنية

الكود في الحزمة `sarf/`، كل وحدة بمسؤولية واحدة:

| الوحدة | الوظيفة |
|---|---|
| `sarf/chars.py` | الحروف والعلامات: الثوابت، وتفكيك الكلمة إلى (حرف، علامات)، وأدوات الحروف |
| `sarf/normalize.py` | التطبيع: الرسم العثماني إلى إملائي (مستوى النص)، والألف المحذوفة والمدّة والهمزات (مستوى الكلمة) |
| `sarf/divine.py` | لفظ الجلالة بكل صيغه |
| `sarf/syllabify.py` | المقطِّع CV: CVmap ∘ Resolve ∘ Syllabify ∘ Classify |
| `sarf/catalog.py` | فهرس العوامل: الوحدة (الصيغة، المجموعة) ← معانيها |
| `sarf/match.py` | مطابقة العوامل في الكلمة |
| `sarf/evidence.py` | نفي المرشَّح بالكتابة |
| `sarf/align.py` | ربط العامل بمقاطع كلمته |
| `sarf/pipeline.py` | تشغيل المراحل بالترتيب على كائن واحد للآية: normalize ← match ← evidence ← syllabify ← align |
| `sarf/analyze.py` | تحليل آية بكل المراحل (يمرّ بالـ pipeline) |
| `sarf/mood.py` | خبري/إنشائي بالعامل في بابه (سجل T14) |
| `sarf/output_text.py`، `sarf/output_html.py` | الناتج النصي وJSON، وتقرير HTML |

واجهات سطر الأوامر في الجذر، وتُبقي الأسماء القديمة للتوافق (`cv.run`، `eo.analyze`، …):

| الملف | الوظيفة |
|---|---|
| `pipeline.py` | تشغيل المراحل وفحص ناتج كل مرحلة: `--stages`، `--until`، `--skip`، `--dump` |
| `extract_operators.py` | استخراج العوامل وتقطيع الآية (نص أو JSON Lines) |
| `cv_syllabifier.py` | التقطيع وحده |
| `syllable_report.py` | تقرير HTML: جدول لكل آية، صفٌّ لكل كلمة بمقاطعها ونمط CV والعوامل |
| `mabniyat_lexicon.py` | محوِّل `02_mabniyat` إلى معجم الكلمات المغلقة |
| `schema_check.py` | فاحص JSON Schema بلا مكتبات خارجية |

| البيانات | |
|---|---|
| `operators_catalog.jsonl` | الفهرس الأساسي (المعاني، والاحتمالات، وعلامات التمييز) |
| `operators_catalog_split_vocalized.csv` | فهرس مكمّل؛ يُضاف منه ما ليس في الأساس فقط (إِنَّ، أَنَّ) |
| `verses*.txt` / `example_output*` | آيات الاختبار ونتائجها |
| `reports/syllable_report.html` | التقرير المولَّد من آيات الاختبار |

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

ليس كمثله شيء: يُعرَف كلمةً واحدة بكل صيغه وما يتصل به من سوابق (وَ، فَ، بِ، تَ، لِ، وهمزة الاستفهام ءَ) ولاحقة «ـمَّ» (`divine_name` في `sarf/divine.py`)، **ولا يُقطَّع**: لا مقاطع له ولا يدخل في عدّ المقاطع، ويُعرض في التقطيع كما هو موسوماً «لفظ الجلالة». أما استخراج العوامل (لِ في لِلَّهِ، بِ في بِٱللَّهِ) والتحليل الصرفي فتشمله كغيره. أمثلته في `verses_allah.txt`: ٱللَّه، لِلَّه، فَلِلَّه، تَٱللَّه، ءَآللَّه، ٱللَّهُمَّ — ولا يطابق ما يشبهه رسماً مثل ٱللَّهْو.
