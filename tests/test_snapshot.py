#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ثبات الناتج (tools/snapshot_outputs.py): التفريغ يتكرّر بعينه، والمقارنة تمسك كل قيمةٍ تغيّرت وتعدّ الإضافة.

    PYTHONHASHSEED=0 python3 tests/test_snapshot.py
"""
import copy, gzip, os, pickle, sys, tempfile

H = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + '/'
sys.path.insert(0, H + 'tools')
sys.path.insert(0, H)
import snapshot_outputs as so
from sarf.root import hfn

bad = 0
def check(name, ok, got=''):
    global bad
    bad += not ok
    print('OK ' if ok else 'BAD', name, '' if ok else got)

A = {'1:1': {'a': {'x': 1, 'l': [1, 2]}, 'F': {'(0, 0)': {'pos': 'اسم'}}}}
v, ad = so.compare(A, copy.deepcopy(A))
check('المطابق: لا مخالفة ولا إضافة', not v and not ad)
B = copy.deepcopy(A); B['1:1']['F']['(0, 0)']['lemma'] = 'x'
v, ad = so.compare(A, B)
check('الحقل المضاف إضافةٌ لا مخالفة', not v and ad == {'F/(0, 0)/lemma': 1}, (v, ad))
B = copy.deepcopy(A); B['1:1']['a']['x'] = 2
check('القيمة المتغيّرة مخالفة', len(so.compare(A, B)[0]) == 1)
B = copy.deepcopy(A); del B['1:1']['a']['x']
check('الحقل المحذوف مخالفة', len(so.compare(A, B)[0]) == 1)
B = copy.deepcopy(A); B['1:1']['a']['l'].append(3)
check('تغيّر طول القائمة مخالفة', len(so.compare(A, B)[0]) == 1)
check('الآية الغائبة مخالفة', len(so.compare(A, {})[0]) == 1)
if hfn() and os.environ.get('PYTHONHASHSEED') == '0':
    d = tempfile.mkdtemp()
    so.dump(H, d + '/a.pkl.gz', 1, {'1:1', '2:282'})
    so.dump(H, d + '/b.pkl.gz', 1, {'1:1', '2:282'})
    A_, B_ = pickle.load(gzip.open(d + '/a.pkl.gz')), pickle.load(gzip.open(d + '/b.pkl.gz'))
    v, ad = so.compare(A_, B_)
    check('تفريغان متتاليان للشيفرة نفسها متطابقان (1:1، 2:282)', len(A_) == 2 and not v and not ad, v[:3])
print('ALL OK' if not bad else f'FAILED {bad}')
sys.exit(1 if bad else 0)
