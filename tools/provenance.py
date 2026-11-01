# -*- coding: utf-8 -*-
"""هوية التشغيل: ما يلزم لإعادة إنتاج تقريرٍ والتحقق من أنه وليد الشيفرة التي يُدّعى أنه منها.

يُسجَّل في كل تقرير:
  - نسخة الشيفرة: الالتزام والفرع، والملفات المعدَّلة غير الملتزم بها وبصمة فرقها؛
    وبصمةُ ملفات الشيفرة نفسها (تصلح ولو لم يكن المجلد مستودع git).
  - أمر التشغيل، وبيئته (PYTHONHASHSEED، وإصدار بايثون)، وسياسة التحليل.
  - البيانات: مسار HFN وبصمة ملفاته، وبصمات الفهرس والمعجم ونص المصحف.
  - بصمة المدخل، وهوية التشغيل (مشتقةٌ من كل ما سبق)، وبصمة المخرج (تُحسب على المحتوى قبل سطرها).
"""
import hashlib, os, subprocess, sys, platform, datetime, glob

H = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _sha(paths):
    m = hashlib.sha256()
    for p in sorted(paths):
        m.update(os.path.relpath(p, H).encode() if p.startswith(H) else os.path.basename(p).encode())
        with open(p, 'rb') as f:
            m.update(f.read())
    return m.hexdigest()[:16]


def _git(*a):
    try:
        return subprocess.run(['git', '-C', H, *a], capture_output=True, text=True, timeout=20).stdout.strip()
    except Exception:
        return ''


def code_files():
    return [p for p in glob.glob(os.path.join(H, 'sarf', '*.py')) + glob.glob(os.path.join(H, 'tools', '*.py'))
            + glob.glob(os.path.join(H, 'tools', '*.css'))]


def data_files():
    out = [os.path.join(H, f) for f in ('operators_catalog.jsonl', 'operators_catalog_split_vocalized.csv',
                                         'data/quran_hafs.tsv') if os.path.exists(os.path.join(H, f))]
    out += glob.glob(os.path.join(H, 'lexicon', '*.jsonl'))
    return out


def identity(inputs_text, policy):
    """inputs_text: نص المدخل كما حُلِّل؛ policy: وصف سياسة التحليل ومصدر كل مرحلة"""
    from sarf.root import hfn
    hp = hfn().path
    commit = _git('rev-parse', 'HEAD')
    dirty = [l for l in _git('status', '--porcelain', '--untracked-files=no').splitlines()
             if l and not l[3:].startswith('reports/')]
    diff = _git('diff', 'HEAD', '--', 'sarf', 'tools', 'tests', 'lexicon', '*.jsonl', '*.csv') if commit else ''
    rec = dict(
        commit=commit or 'ليس مستودع git',
        branch=_git('rev-parse', '--abbrev-ref', 'HEAD') or '—',
        commit_date=_git('log', '-1', '--format=%cI') or '—',
        dirty=dirty,
        dirty_diff_sha=hashlib.sha256(diff.encode()).hexdigest()[:16] if diff else '—',
        code_sha=_sha(code_files()),
        command=' '.join([os.path.relpath(sys.argv[0], H)] + sys.argv[1:]),
        python=platform.python_version(),
        hashseed=os.environ.get('PYTHONHASHSEED', 'غير مضبوط'),
        hfn_path=os.path.basename(hp) if hp else '—',
        hfn_sha=_sha(glob.glob(os.path.join(hp, '*.csv'))) if hp else '—',
        data_sha=_sha(data_files()),
        input_sha=hashlib.sha256(inputs_text.encode()).hexdigest()[:16],
        started=datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds'),
        policy=policy,
    )
    rid = hashlib.sha256('|'.join(str(rec[k]) for k in ('commit', 'dirty_diff_sha', 'code_sha', 'hfn_sha', 'data_sha',
                                                         'input_sha', 'command', 'hashseed')).encode()).hexdigest()[:12]
    rec['run_id'] = rid
    return rec


def rows(rec):
    """صفوف العرض (المفتاح، القيمة)"""
    return [
        ('هوية التشغيل', rec['run_id']),
        ('الالتزام', f"{rec['commit']} ({rec['branch']}، {rec['commit_date']})"),
        ('تعديلات غير ملتزم بها', ('، '.join(rec['dirty']) + f" — بصمة الفرق {rec['dirty_diff_sha']}") if rec['dirty']
         else 'لا شيء: الشيفرة مطابقة للالتزام'),
        ('بصمة الشيفرة (sarf/*.py وtools/*)', rec['code_sha']),
        ('الأمر', rec['command']),
        ('البيئة', f"Python {rec['python']}، PYTHONHASHSEED={rec['hashseed']}"),
        ('HFN', f"{rec['hfn_path']} — بصمة {rec['hfn_sha']}"),
        ('الفهرس والمعجم ونص المصحف', rec['data_sha']),
        ('بصمة المدخل', rec['input_sha']),
        ('وقت البدء (UTC)', rec['started']),
    ] + [(f'مصدر: {k}', v) for k, v in rec['policy']]


def stamp(page_without_stamp):
    """بصمة المخرج: تُحسب على الصفحة كلها قبل سطر البصمة، فيُتحقَّق منها بحذف السطر وإعادة الحساب"""
    return hashlib.sha256(page_without_stamp.encode('utf-8')).hexdigest()[:16]
