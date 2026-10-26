#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
schema_check.py — مدقِّق JSON Schema مصغَّر بالمكتبة القياسية وحدها.

يدعم ما تستعمله مخططات المستودع فقط:
  type، enum، const، required، properties، additionalProperties(false)، items،
  minItems/maxItems، minLength/maxLength، minimum/maximum، $ref (داخل الملف وبين الملفات)،
  allOf، if/then/else، not، anyOf.
أي كلمة مفتاحية أخرى في المخطط تُرفض صراحةً بدل تجاهلها بصمت.

الاستعمال:
    from schema_check import Validator
    v = Validator('schema/lexicon_entry.schema.json')
    errors = v.errors(instance)          # [] = صالح
    python3 schema_check.py SCHEMA INSTANCE.json [INSTANCE2.json …]
"""
import json, os, sys

SUPPORTED = {'$schema', '$id', '$defs', 'title', 'description', 'examples', '$comment',
             'type', 'enum', 'const', 'required', 'properties', 'additionalProperties', 'items',
             'minItems', 'maxItems', 'minLength', 'maxLength', 'minimum', 'maximum',
             '$ref', 'allOf', 'if', 'then', 'else', 'not', 'anyOf'}

TYPES = {
    'object': lambda x: isinstance(x, dict),
    'array': lambda x: isinstance(x, list),
    'string': lambda x: isinstance(x, str),
    'integer': lambda x: isinstance(x, int) and not isinstance(x, bool),
    'number': lambda x: isinstance(x, (int, float)) and not isinstance(x, bool),
    'boolean': lambda x: isinstance(x, bool),
    'null': lambda x: x is None,
}


class Validator:
    def __init__(self, path):
        self.docs = {}
        self.root = self._load(os.path.abspath(path))

    def _load(self, path):
        if path not in self.docs:
            with open(path, encoding='utf-8') as f:
                self.docs[path] = json.load(f)
        return path

    def _resolve(self, ref, base):
        file_part, _, frag = ref.partition('#')
        doc_path = self._load(os.path.join(os.path.dirname(base), file_part)) if file_part else base
        node = self.docs[doc_path]
        for part in [p for p in frag.split('/') if p]:
            node = node[part]
        return node, doc_path

    def errors(self, instance):
        out = []
        self._check(instance, self.docs[self.root], self.root, '$', out)
        return out

    def _ok(self, x, schema, base):
        tmp = []
        self._check(x, schema, base, '$', tmp)
        return not tmp

    def _check(self, x, s, base, path, out):
        unknown = set(s) - SUPPORTED
        if unknown:
            raise ValueError(f'كلمات مفتاحية غير مدعومة في المخطط عند {path}: {sorted(unknown)}')
        if '$ref' in s:
            target, tbase = self._resolve(s['$ref'], base)
            self._check(x, target, tbase, path, out)
        t = s.get('type')
        if t and not any(TYPES[tt](x) for tt in ([t] if isinstance(t, str) else t)):
            out.append(f'{path}: النوع {type(x).__name__} بدل {t}')
            return
        if 'const' in s and x != s['const']:
            out.append(f'{path}: القيمة {x!r} بدل {s["const"]!r}')
        if 'enum' in s and x not in s['enum']:
            out.append(f'{path}: {x!r} ليست من القيم المسموحة')
        if isinstance(x, str):
            if len(x) < s.get('minLength', 0) or len(x) > s.get('maxLength', 10 ** 9):
                out.append(f'{path}: طول النص {len(x)} خارج الحدود')
        if isinstance(x, (int, float)) and not isinstance(x, bool):
            if 'minimum' in s and x < s['minimum'] or 'maximum' in s and x > s['maximum']:
                out.append(f'{path}: {x} خارج الحدود')
        if isinstance(x, list):
            if len(x) < s.get('minItems', 0) or len(x) > s.get('maxItems', 10 ** 9):
                out.append(f'{path}: عدد العناصر {len(x)} خارج الحدود')
            if 'items' in s:
                for i, item in enumerate(x):
                    self._check(item, s['items'], base, f'{path}[{i}]', out)
        if isinstance(x, dict):
            for k in s.get('required', []):
                if k not in x:
                    out.append(f'{path}: الحقل المطلوب «{k}» غائب')
            props = s.get('properties', {})
            for k, v in x.items():
                if k in props:
                    self._check(v, props[k], base, f'{path}.{k}', out)
                elif s.get('additionalProperties') is False:
                    out.append(f'{path}: حقل غير معرَّف «{k}»')
        for sub in s.get('allOf', []):
            self._check(x, sub, base, path, out)
        if 'anyOf' in s and not any(self._ok(x, sub, base) for sub in s['anyOf']):
            out.append(f'{path}: لا يطابق أيّاً من بدائل anyOf')
        if 'not' in s and self._ok(x, s['not'], base):
            out.append(f'{path}: يطابق ما يمنعه «not»')
        if 'if' in s:
            branch = 'then' if self._ok(x, s['if'], base) else 'else'
            if branch in s:
                self._check(x, s[branch], base, path, out)


if __name__ == '__main__':
    if len(sys.argv) < 3:
        sys.exit('الاستعمال: python3 schema_check.py SCHEMA INSTANCE.json [...]')
    v = Validator(sys.argv[1])
    bad = 0
    for p in sys.argv[2:]:
        with open(p, encoding='utf-8') as f:
            errs = v.errors(json.load(f))
        bad += bool(errs)
        print(('OK   ' if not errs else 'FAIL ') + p)
        for e in errs[:20]:
            print('     ' + e)
    sys.exit(1 if bad else 0)
