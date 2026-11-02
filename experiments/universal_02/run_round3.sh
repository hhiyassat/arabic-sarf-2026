cd /Users/husseinhiyassat/arabic-sarf-2026
echo "=== stash A على القرآن كلِّه ==="
AFTER=$(python3 experiments/universal_02/a_quran_sha.py)
git stash push -- sarf/segment.py >/dev/null 2>&1
BEFORE=$(python3 experiments/universal_02/a_quran_sha.py)
git stash pop >/dev/null 2>&1
echo "A القرآن (المفتاح) = $AFTER"
echo "A القرآن (قبل)     = $BEFORE"
[ "$AFTER" = "$BEFORE" ] && echo "A_BYTE_IDENTICAL(الكلّ) = YES" || echo "اختلاف!"
echo "=== phase2 (الجولة 3) ==="
python3 experiments/universal_02/phase2_quran.py
