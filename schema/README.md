# مخطط بيانات المحلل الصرفي (الإصدار 1.0)

`morph_analysis.schema.json` (JSON Schema 2020-12) يحدّد شكل ناتج المحلل الصرفي. أمثلة صحيحة في `examples/`.

**النطاق:** تحليل نصّي فقط. الحالة الإعرابية تُؤخذ من العلامة **المكتوبة** على الكلمة (`observed_mark`). لا يدخل في المخطط الوصلُ والوقف ولا أحكام الأداء.

## البنية

```
text                      النص الأصلي والمطبَّع ونوع الرسم والإحالة (سورة، آية)
tokens[]                  كلمة لكل ما بين فراغين
  fixed_lexeme?           كلمة جامدة من قائمة مغلقة (لفظ الجلالة، الأعلام الأعجمية) — لا يُحلَّل جذرها ولا وزنها؛
                          ولفظ الجلالة بكل صيغه لا syllables له (لا يُقطَّع)، ويُحلَّل كغيره
  analyses[]              كل التحاليل الممكنة، مرتّبة تنازلياً بـ score
    score, status         selected | candidate | rejected
    segments[]            سوابق ← جذع واحد ← لواحق، بالترتيب
      role                proclitic | stem | suffix | enclitic
      pos                 noun | verb | particle  →  ومعه كائن واحد فقط: noun أو verb أو particle
      root, pattern       الجذر وصحته/اعتلاله، والميزان والزيادة والإعلال
      char_span, syllable_span   الربط بالحروف وبمقاطع cv_syllabifier
    evidence[]            ما بُني عليه التحليل: rule | catalog | lexicon | governor | vocalization | prior
  syllables[]             مقاطع الكلمة
dependencies[]            العامل ← المعمول: الحالة المتوقَّعة مقابل العلامة المكتوبة، وconsistent
```

## قرارات التصميم

1. **كل كلمة لها قائمة تحاليل لا تحليل واحد.** «وَمَا» لها ثلاثة في `examples/wama_kana.json`: نافية (selected)، موصولة (candidate)، وَ القسم (rejected مع السبب). المرفوض يُحفظ ومعه سببه في `evidence`.
2. **التجزئة قبل الخصائص.** السمات تُعلَّق على المكوّن لا على الكلمة: في «فَلِلَّهِ» ثلاثة مكوّنات، فَ استئناف، ولِ جارّة عاملة، واللَّهِ اسم مجرور.
3. **كائن واحد لكل نوع.** المكوّن الذي `pos` فيه `noun` يحمل `noun` فقط. والمخطط يرفض أن يجتمع `noun` و`verb` في مكوّن واحد.
4. **الجامد المغلق يُعرَف قبل التحليل.** `fixed_lexeme` يعلّم الكلمة: لفظ الجلالة لا جذر له ولا وزن في الناتج، و`derivation.class = jamid`. ولا يُقطَّع بكل صيغه: كلمته لا تحمل `syllables`، والمخطط يرفض خلاف ذلك. أما التحليل واستخراج العامل والروابط فتشمله كغيره.
5. **قيود صرفية داخل المخطط:**
   - الماضي والأمر مبنيان.
   - الأمر للمخاطب.
   - المبني لا حالة إعرابية له.
   - الجمع يحتاج نوعه، وجمع التكسير يحتاج قلّته أو كثرته.
   - المشتق يحتاج نوعه.
   - الثلاثي المجرد يحتاج بابه.
   - المعرفة تحتاج سبب تعريفها.
6. **الربط بالفهرس.** `particle.operator_ids` ومعرّفات `evidence` و`dependencies` مأخوذة من `operator_id` في `operators_catalog.jsonl` كما هي.
7. **العامل يُتحقَّق منه بالكتابة.** `dependencies[].consistent = false` معناه أن العلامة المكتوبة لا توافق عمل العامل، وهذا يدلّ على التباس في التحليل أو خطأ في التشكيل.
8. **لا حقول إضافية.** `additionalProperties: false` في كل كائن. أي حقل جديد يحتاج تعديل المخطط ورفع `schema_version`.

## القيم المغلقة الأساسية

| الحقل | القيم |
|---|---|
| `noun.subtype` | common، proper، pronoun، demonstrative، relative، interrogative، conditional، adverbial، number، ism_fiil، kinaya |
| `derivation.jamid_type` | concrete، abstract، masdar، masdar_mimi، masdar_sinai، masdar_marra، masdar_hayah |
| `derivation.mushtaq_type` | active_participle، passive_participle، adjective، intensive، elative، noun_of_time، noun_of_place، noun_of_instrument |
| `agreement.plural_type` | sound_masc، sound_fem، broken، ism_jam، ism_jins_jami |
| `inflection.marker` | damma، fatha، kasra، sukun، tanwin×3، waw، alif، ya، nun_retained، nun_deleted، implicit |
| `verb.form` | I–X، QI–QIV |
| `verb.bab` | a-u، a-i، a-a، i-a، u-u، i-i |
| `root.soundness` | salim، mahmuz، mudaaf، mithal، ajwaf، naqis، lafif_mafruq، lafif_maqrun |
| `particle.effect` | jarr، nasb_verb، jazm_one، jazm_two، nasb_ism_raf_khabar، raf_ism_nasb_khabar، nasb، none |
| `clitic_type` | conjunction، preposition، oath، future، interrogative، emphasis_lam، imperative_lam، definite_article، vocative، resumption_fa |

## التحقّق

التحقّق اختياري، والمحلل نفسه لا يحتاج مكتبة خارجية:
```
pip install jsonschema
python3 -c "import json,jsonschema; s=json.load(open('schema/morph_analysis.schema.json')); [jsonschema.validate(json.load(open(f)), s) for f in ['schema/examples/lam_yalid.json','schema/examples/falillahi_alhamd.json','schema/examples/wama_kana.json']]; print('OK')"
```
