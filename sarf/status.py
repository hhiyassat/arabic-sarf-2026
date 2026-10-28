# -*- coding: utf-8 -*-
"""
sarf.status — حالات الحكم على المرشَّح (T09)، بصيغة Candidates/Judge (T07، D17).

    مؤجَّل  deferred   الأصل: لم يثبت المنع ولا القبول
    ممنوع   blocked    ثبت مانع بالكتابة (sarf.evidence)، ويُحفظ سببه
    مقبول   accepted   ثبت السبب والشرط، وفُحصت الموانع المسجّلة فلم يثبت منها شيء،
                       ولا منافس له على خانته إلا ممنوع (sarf.judge)

غياب المانع عن السجل لا يثبت انتفاءه (T07)، والإقصاء وحده لا يكفي للقبول (T19i).
"""
DEFERRED, BLOCKED, ACCEPTED = 'deferred', 'blocked', 'accepted'
STATUS_AR = {DEFERRED: 'مؤجَّل', BLOCKED: 'ممنوع', ACCEPTED: 'مقبول'}
