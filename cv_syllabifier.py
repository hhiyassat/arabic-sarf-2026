#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
cv_syllabifier.py — واجهة سطر الأوامر للمقطِّع (الكود في sarf/syllabify.py).
يُبقي الأسماء القديمة للتوافق: cv.run، cv.divine_name، cv.report، cv.word_view، SIX …

الاستعمال:
    python3 cv_syllabifier.py verse.txt
"""
import sys, os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sarf.chars import *                                   # noqa: F401,F403
from sarf.normalize import normalize, HAMZA_FORMS, LEXICAL_MADD   # noqa: F401
from sarf.divine import DIVINE_NAME, divine_name           # noqa: F401
from sarf.syllabify import *                               # noqa: F401,F403
from sarf.syllabify import run, report, word_view

if __name__ == '__main__':
    text = open(sys.argv[1], encoding='utf-8').read().strip() if len(sys.argv) > 1 else sys.stdin.read().strip()
    res = run(text)
    print(report(res))
    print()
    print(word_view(res))
