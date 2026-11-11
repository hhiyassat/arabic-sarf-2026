"""تتبّع منظَّم لفتح ملفات HFN (SARF_HFN_V48_VALIDATION_COMPLETION_02 §٣).
يُحمَّل بـ PYTHONPATH=tools/hfn_isolation، ويكتب سطر JSON لكل فتحٍ في ملف `$SARF_OPEN_LOG.<pid>` بالحقول:
requested (كما طُلب)، abspath، realpath (بعد حلّ الروابط الرمزية كلها)، mode، pid، caller (أقرب إطارٍ خارج المكتبة القياسية: ملف:دالة:سطر).
لا يُصفّى بالاسم: كل فتحٍ يُسجَّل إن كان مساره المطلق أو المحلول تحت أحد الجذور في `$SARF_OPEN_ROOTS` (مفصولةً بـ :)، أو يحوي `/release_v`.
`$SARF_OPEN_INJECT` (للاختبار وحده): مسارٌ يُفتح للقراءة عند الخروج، لإثبات أن الفاحص يُسقط القراءة المحقونة."""
import atexit, builtins, io, json, os, sys, sysconfig
_LOG = os.environ.get('SARF_OPEN_LOG')
if _LOG:
    _STD = tuple(p for p in {sysconfig.get_paths().get('stdlib'), sysconfig.get_paths().get('platstdlib')} if p)
    _ME = os.path.abspath(__file__)
    _ROOTS = [os.path.realpath(r) for r in os.environ.get('SARF_OPEN_ROOTS', '').split(':') if r]
    _o = builtins.open
    _fh = []

    def _caller():
        f = sys._getframe(2)
        while f is not None:
            fn = os.path.abspath(f.f_code.co_filename)
            if fn != _ME and not fn.startswith(_STD) and not fn.startswith('<frozen'):
                return f'{fn}:{f.f_code.co_name}:{f.f_lineno}'
            f = f.f_back
        return 'UNKNOWN'

    def _rel(p):
        return '/release_v' in p or any(p == r or p.startswith(r + os.sep) for r in _ROOTS)

    def _open(f, *a, **k):
        try:
            req = os.fspath(f)
            ab = os.path.abspath(req) if isinstance(req, str) else None
        except TypeError:
            ab = None
        if ab:
            rp = os.path.realpath(ab)
            if _rel(ab) or _rel(rp):
                m = a[0] if a else k.get('mode', 'r')
                if not _fh:
                    _fh.append(_o(f'{_LOG}.{os.getpid()}', 'a', encoding='utf-8'))
                _fh[0].write(json.dumps(dict(requested=req, abspath=ab, realpath=rp, mode=m, pid=os.getpid(), caller=_caller()),
                                        ensure_ascii=False) + '\n')
                _fh[0].flush()
        return _o(f, *a, **k)

    builtins.open = _open
    io.open = _open
    _inj = os.environ.get('SARF_OPEN_INJECT')
    if _inj:
        atexit.register(lambda: open(_inj, 'rb').read(16))
