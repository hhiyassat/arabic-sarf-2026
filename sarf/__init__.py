# -*- coding: utf-8 -*-
"""
sarf — المحلل: وحدات مستقلة يجمعها الـ pipeline.

  chars        الحروف والعلامات وأدواتها
  normalize    التطبيع (العثماني ومستوى الكلمة)
  divine       لفظ الجلالة
  syllabify    التقطيع CV
  catalog      فهرس العوامل
  match        مطابقة العوامل
  evidence     نفي المرشَّح بالكتابة
  align        ربط العامل بمقاطعه
  pipeline     تشغيل المراحل على كائن الآية
  analyze      تحليل آية بكل المراحل
  mood         خبري/إنشائي
  output_text  الناتج النصي وJSON
  output_html  تقرير HTML
"""
