"""حارس هوية HFN داخل العملية (§٣ و§٤): hfn() يُحمَّل مرةً ويُخزَّن، فتبديل SARF_HFN بعد التحميل لا يبدّل الإصدار؛
والحارس يرفض استمرار تشغيلٍ تختلف فيه البيئة عن المحمَّل، أو عن المتوقَّع المعلن (SARF_EXPECT_RELEASE وSARF_EXPECT_MANIFEST)."""
import os


class HFNIdentityError(RuntimeError):
    pass


def assert_identity():
    from sarf.root import hfn
    h = hfn()
    env = os.environ.get('SARF_HFN', '')
    if env and os.path.realpath(env) != os.path.realpath(h.path):
        raise HFNIdentityError(f'HFN_IDENTITY_MISMATCH: SARF_HFN={env} والمحمَّل {h.path} ({h.release})')
    er, em = os.environ.get('SARF_EXPECT_RELEASE'), os.environ.get('SARF_EXPECT_MANIFEST')
    if er and h.release != er:
        raise HFNIdentityError(f'HFN_IDENTITY_MISMATCH: المتوقَّع {er} والمحمَّل {h.release}')
    if em and (h.pin or {}).get('manifest_sha256') != em:
        raise HFNIdentityError(f'HFN_IDENTITY_MISMATCH: بصمة MANIFEST المحمَّلة {(h.pin or {}).get("manifest_sha256")} ≠ {em}')
    return dict(release=h.release, path=h.path, manifest_sha256=(h.pin or {}).get('manifest_sha256'), config_mode=(h.pin or {}).get('config_mode'))
