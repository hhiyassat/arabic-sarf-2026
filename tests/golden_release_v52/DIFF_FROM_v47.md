# golden_release_v52: الفرق عن golden_release_v47

**لا فرق.** الملفّات الأربعة (verses، verses_allah، verses_inna، verses_innama) مطابقة بايتاً لنظائرها في `golden_release_v47` (`cmp`).

- **السبب:** ملفّات HFN التي يقرؤها sarf (events.csv وlexical_units.csv وform_meanings.csv وسائر ملفّات التحليل) مطابقة بايتاً بين release_v47 وrelease_v52. الجديد في v52 هو `ahdath_ajnas.csv` ودليله، وتغيّر README.
- **متى:** 2026-11-17، حين نُقل الإنتاج إلى release_v52 بحكم المالك «اجعله إنتاجيّاً».
- **كيف أُنشئت:** `python3 tests/regress.py --update` على الإعداد الإنتاجي الجديد، بعد `SARF_REGRESS_AGAINST=release_v47 python3 tests/regress.py` → «لا فرق».
