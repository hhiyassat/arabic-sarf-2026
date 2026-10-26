# تقرير تحويل `02_mabniyat` إلى المعجم

- **مداخل مقبولة:** 281 (في `mabniyat_lexicon.jsonl`، كلها تطابق `schema/lexicon_entry.schema.json`)
- **سجلات مرفوضة:** 0 (في `mabniyat_rejected.jsonl` مع أسبابها)
- **تصحيحات إملائية آلية:** 32 في المداخل المقبولة

## لكل ملف

| الملف | السجلات | مقبولة | مدموجة (تكرار) | مرفوضة | أسباب الرفض |
|---|---|---|---|---|---|
| `building_regulations` | 4 | 0 |  |  |  |
| `built_in_adverbs` | 21 | 20 |  |  |  |
| `compound_number_details` | 4 | 0 |  |  |  |
| `compound_numbers` | 8 | 0 |  |  |  |
| `conditional_letters_tools` | 21 | 20 |  |  |  |
| `coordinating_conjunctions` | 23 | 18 | 8 |  |  |
| `copulative_particle` | 7 | 7 |  |  |  |
| `demonstrative_pronouns` | 53 | 42 | 12 |  |  |
| `estimated_parsing_indeclinables` | 4 | 0 |  |  |  |
| `functional_indeclinable_substitutes` | 7 | 0 |  |  |  |
| `grammatical_construction_cases` | 55 | 0 |  |  |  |
| `hidden_pronouns` | 11 | 0 |  |  |  |
| `imperative_verb_building` | 10 | 0 |  |  |  |
| `indeclinable_discourse_roles` | 5 | 0 |  |  |  |
| `interrogative_letters_tools` | 6 | 6 | 4 |  |  |
| `interrogative_tools_categories` | 17 | 11 |  |  |  |
| `jazm_tools` | 20 | 20 | 14 |  |  |
| `kinaya_names` | 9 | 8 | 1 |  |  |
| `letters_answers` | 10 | 7 |  |  |  |
| `past_tense_conjugation_rules` | 11 | 0 |  |  |  |
| `preposition_meanings` | 56 | 51 | 34 |  |  |
| `present_naseb_tools` | 10 | 10 | 1 |  |  |
| `present_tense_building_cases` | 3 | 0 |  |  |  |
| `pronouns_classification` | 43 | 54 | 7 |  |  |
| `relative_pronouns` | 48 | 32 | 16 |  |  |
| `types_of_i3rab` | 3 | 0 |  |  |  |
| `verb_building_rules` | 10 | 0 |  |  |  |
| `verb_name` | 57 | 59 |  |  |  |
| `vocative_particles` | 9 | 8 |  |  |  |

## التصحيحات المطبّقة من `data_fixes/mabniyat_corrections.json`

- حذف: 53، تعديل: 56، إضافة: 21
- معلّقة حتى التوثيق: 9 (في `mabniyat_held.jsonl`)
- إصلاح البنية: 5 عنوان قسم، 10 مثال أُلحق بسجله

**المعلّقة:**

- `demonstrative_pronouns` (35): «هات» غير موثّقة اسمَ إشارة
- `demonstrative_pronouns` (46): «هُنَاكَة» غير موثّقة
- `demonstrative_pronouns` (47): «ذَاهَ» غير موثّقة
- `demonstrative_pronouns` (50): «ثَمَّكَ» غير موثّقة
- `demonstrative_pronouns` (51): «هَاهُنَاكَ» غير موثّقة
- `demonstrative_pronouns` (52): «أولاءهم» غير موثّقة
- `kinaya_names` (5): «كأَيٍّ» غير موثّقة بهذا الرسم
- `letters_answers` (6): «أَوَى» غير موثّقة حرفَ جواب
- `letters_answers` (7): «أَفِي» غير موثّقة حرفَ جواب

## ملاحظات الملفات

- `building_regulations`: ملف وصفي/قواعد: لا يُكتب في المعجم.
- `compound_number_details`: ملف وصفي/قواعد: لا يُكتب في المعجم.
- `compound_numbers`: ملف وصفي/قواعد: لا يُكتب في المعجم.
- `estimated_parsing_indeclinables`: ملف وصفي/قواعد: لا يُكتب في المعجم.
- `functional_indeclinable_substitutes`: ملف وصفي/قواعد: لا يُكتب في المعجم.
- `grammatical_construction_cases`: ملف وصفي/قواعد: لا يُكتب في المعجم.
- `hidden_pronouns`: ملف قواعد لا معجم: لا يُكتب في المعجم؛ فُحصت سجلاته فقط.
- `imperative_verb_building`: ملف وصفي/قواعد: لا يُكتب في المعجم.
- `indeclinable_discourse_roles`: ملف وصفي/قواعد: لا يُكتب في المعجم.
- `past_tense_conjugation_rules`: ملف وصفي/قواعد: لا يُكتب في المعجم.
- `present_tense_building_cases`: ملف وصفي/قواعد: لا يُكتب في المعجم.
- `types_of_i3rab`: ملف وصفي/قواعد: لا يُكتب في المعجم.
- `verb_building_rules`: ملف وصفي/قواعد: لا يُكتب في المعجم.

## المقارنة بـ `operators_catalog`

- **تعارض:** «لَوْ» في المجموعة 7 من الفهرس (الشرط الجازمة فقط)، و`conditional_letters_tools` يقول: «حرف شرط غير جازم يستخدم للدلالة على امتن…».
- **في المعجم وليست في الفهرس** (`jazm_two`، المجموعة 6/7): ايان، اين، كيفما

## التصحيحات الآلية المطبّقة

- حذف السكون عن حرف المدّ: 10
- حذف الفتحة عن همزة الوصل: 8
- نقل الشدة من لام التعريف إلى لام الكلمة: 7
- دمج علامة مكرّرة على الحرف نفسه: 5
- حذف الفتحة عن لام التعريف قبل اللام المشددة: 1
- حذف مسافة قبل علامة: 1

## المداخل حسب الفئة

- `particle`: 72
- `verb_name`: 60
- `demonstrative`: 32
- `separate_pronoun`: 24
- `attached_pronoun`: 23
- `adverb`: 20
- `relative`: 16
- `conditional_noun`: 16
- `interrogative_noun`: 11
- `kinaya`: 7
