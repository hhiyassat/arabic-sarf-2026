# تقرير تحويل `02_mabniyat` إلى المعجم

- **مداخل مقبولة:** 253 (في `mabniyat_lexicon.jsonl`، كلها تطابق `schema/lexicon_entry.schema.json`)
- **سجلات مرفوضة:** 74 (في `mabniyat_rejected.jsonl` مع أسبابها)
- **تصحيحات إملائية آلية:** 33 في المداخل المقبولة

## لكل ملف

| الملف | السجلات | مقبولة | مدموجة (تكرار) | مرفوضة | أسباب الرفض |
|---|---|---|---|---|---|
| `building_regulations` | 4 | 0 |  |  |  |
| `built_in_adverbs` | 21 | 18 |  | 3 | التنوين علامة إعراب (1)؛ الصيغة نفسها حرف عطف في coordinating_conjunctions (1)؛ شدة وسكون معاً على «…» (1) |
| `compound_number_details` | 4 | 0 |  |  |  |
| `compound_numbers` | 8 | 0 |  |  |  |
| `conditional_letters_tools` | 21 | 21 |  |  |  |
| `coordinating_conjunctions` | 23 | 23 | 12 |  |  |
| `copulative_particle` | 7 | 7 |  |  |  |
| `demonstrative_pronouns` | 53 | 41 | 12 | 12 | غير مشكولة (11)؛ مشكولة جزئياً (1) |
| `estimated_parsing_indeclinables` | 4 | 0 |  |  |  |
| `functional_indeclinable_substitutes` | 7 | 0 |  |  |  |
| `grammatical_construction_cases` | 55 | 0 |  |  |  |
| `hidden_pronouns` | 11 | 0 |  | 6 | المستتر لا يكون «…» (4)؛ المثال «…» فيه ياء المخاطبة البارزة (1)؛ تعارض (1) |
| `imperative_verb_building` | 10 | 0 |  |  |  |
| `indeclinable_discourse_roles` | 5 | 0 |  |  |  |
| `interrogative_letters_tools` | 6 | 6 | 4 |  |  |
| `interrogative_tools_categories` | 17 | 0 |  | 17 | غير مشكولة (14)؛ مشكولة جزئياً (3) |
| `jazm_tools` | 20 | 20 | 12 |  |  |
| `kinaya_names` | 9 | 8 | 1 | 1 | مشكولة جزئياً (1) |
| `letters_answers` | 10 | 10 |  |  |  |
| `past_tense_conjugation_rules` | 11 | 0 |  |  |  |
| `preposition_meanings` | 56 | 55 | 34 | 1 | غير مشكولة (1) |
| `present_naseb_tools` | 10 | 10 | 1 |  |  |
| `present_tense_building_cases` | 3 | 0 |  |  |  |
| `pronouns_classification` | 43 | 29 | 2 | 14 | خصائص مستحيلة (8)؛ صيغ متعددة في سجل واحد بخصائص مشتركة (2)؛ تعارض (1)؛ لاحقة «…» ليست ضميراً متصلاً (1)؛ الشخص أو العدد غير مستخرج من الحقول meaning/form (1)؛ «…» ليست من صيغ الضمائر المتصلة (نصب/جر) (1) |
| `relative_pronouns` | 48 | 29 | 16 | 19 | ليست في جرد الموصولات N08 من وثيقة النظرية (10)؛ غير مشكولة (4)؛ تشكيل «…» يخالف صيغة N08 في الوثيقة (3)؛ لفظ الجلالة (اللَّهُمَّ) ليس اسماً موصولاً (1)؛ حروف لاتينية في الصيغة (1) |
| `types_of_i3rab` | 3 | 0 |  |  |  |
| `verb_building_rules` | 10 | 0 |  |  |  |
| `verb_name` | 57 | 57 |  |  |  |
| `vocative_particles` | 9 | 8 |  | 1 | الملف نفسه يصنّفه «…» (1) |

## ملاحظات الملفات

- `building_regulations`: ملف وصفي/قواعد: لا يُكتب في المعجم.
- `compound_number_details`: ملف وصفي/قواعد: لا يُكتب في المعجم.
- `compound_numbers`: ملف وصفي/قواعد: لا يُكتب في المعجم.
- `estimated_parsing_indeclinables`: ملف وصفي/قواعد: لا يُكتب في المعجم.
- `functional_indeclinable_substitutes`: ملف وصفي/قواعد: لا يُكتب في المعجم.
- `grammatical_construction_cases`: ملف وصفي/قواعد: لا يُكتب في المعجم.
- `grammatical_construction_cases`: 16 سجلاً بلا case_type أو رأس جدول: [3, 4, 10, 16, 19, 20, 21, 24, 25, 26, 27, 30, 32, 33, 37, 44]
- `hidden_pronouns`: ملف قواعد لا معجم: لا يُكتب في المعجم؛ فُحصت سجلاته فقط.
- `imperative_verb_building`: ملف وصفي/قواعد: لا يُكتب في المعجم.
- `indeclinable_discourse_roles`: ملف وصفي/قواعد: لا يُكتب في المعجم.
- `past_tense_conjugation_rules`: ملف وصفي/قواعد: لا يُكتب في المعجم.
- `present_tense_building_cases`: ملف وصفي/قواعد: لا يُكتب في المعجم.
- `pronouns_classification`: خانات في الملف لكن سجلاتها مرفوضة في الضمائر المنفصلة للرفع: (شخص 2، singular، masc) «أَنْتَ»
- `pronouns_classification`: خانات غائبة عن الملف في الضمائر المنفصلة للنصب: (شخص 3، plural، masc)
- `pronouns_classification`: خانات في الملف لكن سجلاتها مرفوضة في الضمائر المنفصلة للنصب: (شخص 1، singular، common) «إِيَّايَّ»
- `pronouns_classification`: صيغ متصلة (رفع) غائبة عن الملف: ـتُ، ـنَا، ـتَ، ـتِ، ـتُمَا، ـتُمْ، ـتُنَّ
- `pronouns_classification`: صيغ متصلة (رفع) في الملف لكن سجلاتها مرفوضة: ـوا
- `pronouns_classification`: صيغ متصلة (نصب/جر) غائبة عن الملف: ـكُمَا، ـكُنَّ، ـهَا، ـهُمَا، ـهُمْ، ـهُنَّ
- `pronouns_classification`: صيغ متصلة (نصب/جر) في الملف لكن سجلاتها مرفوضة: ـكَ، ـكِ، ـهُ
- `types_of_i3rab`: ملف وصفي/قواعد: لا يُكتب في المعجم.
- `verb_building_rules`: ملف وصفي/قواعد: لا يُكتب في المعجم.
- `verb_name`: أسماء أفعال في operators_catalog (المجموعة 9) غائبة عن الملف: حيهل، رويد، هاء

## المقارنة بـ `operators_catalog`

- **تعارض:** «لَوْ» في المجموعة 7 من الفهرس (الشرط الجازمة فقط)، و`conditional_letters_tools` يقول: «حرف شرط غير جازم يستخدم للدلالة على امتن…».
- **في المعجم وليست في الفهرس** (`jazm_two`، المجموعة 6/7): ايان، اين، كيفما
- **في المعجم وليست في الفهرس** (`jarr`، المجموعة 1): كي، لعل، لولا، متي

## التصحيحات الآلية المطبّقة

- حذف السكون عن حرف المدّ: 10
- حذف الفتحة عن همزة الوصل: 9
- نقل الشدة من لام التعريف إلى لام الكلمة: 7
- دمج علامة مكرّرة على الحرف نفسه: 5
- حذف الفتحة عن لام التعريف قبل اللام المشددة: 1
- حذف مسافة قبل علامة: 1

## المداخل حسب الفئة

- `particle`: 80
- `verb_name`: 58
- `demonstrative`: 31
- `separate_pronoun`: 21
- `conditional_noun`: 19
- `adverb`: 18
- `relative`: 13
- `kinaya`: 7
- `attached_pronoun`: 6
