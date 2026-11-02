"""قارئُ مورد المبنيات (التجربة UNIVERSAL_02). يقرأ MABNIYAT_FULL_WITH_DECOMPOSITION.json
ببصمته؛ غيابُ الملفّ = RESOURCE_MISSING، واختلافُ البصمة = RESOURCE_HASH_MISMATCH؛ لا fallback صامت."""
import hashlib, json, os, sys

ROOT = os.path.join(os.path.dirname(__file__), "..", "..", "mabniyat_v4")
JSON_PATH = os.path.join(ROOT, "MABNIYAT_FULL_WITH_DECOMPOSITION.json")
EXPECT_SHA_PREFIX = "fc301d6591052b1a"


class ResourceError(Exception):
    pass


def load(path=JSON_PATH, expect_prefix=EXPECT_SHA_PREFIX):
    if not os.path.exists(path):
        raise ResourceError(f"RESOURCE_MISSING: {path}")
    b = open(path, "rb").read()
    sha = hashlib.sha256(b).hexdigest()
    if not sha.startswith(expect_prefix):
        raise ResourceError(f"RESOURCE_HASH_MISMATCH: {sha[:16]} != {expect_prefix}")
    J = json.loads(b)
    return J, sha


def summary(J):
    s = J["summary"]
    return {
        "revision": J.get("revision"),
        "resource_files": s.get("resource_files"),
        "resource_records": s.get("resource_records"),
        "decomposition_index": len(J["decomposition_index"]),
        "unsegmented_or_deferred_items": len(J["unsegmented_or_deferred_items"]),
        "records_with_pending_fields": len(J["records_with_pending_fields"]),
        "deferred_records": len(J["deferred_records"]),
    }


def index_by_surface(J):
    """name/surface (مشكول) → record؛ تُقرأ approved_decomposition وform_decompositions معًا."""
    idx = {}
    for e in J["decomposition_index"]:
        for key in ("name", "surface"):
            v = e.get(key)
            if v:
                idx.setdefault(v, e)
        for f in e.get("form_decompositions", []) or []:
            v = f.get("surface") or f.get("form")
            if v:
                idx.setdefault(v, {**e, "_form": f})
    return idx


if __name__ == "__main__":
    try:
        J, sha = load()
    except ResourceError as e:
        print(e); sys.exit(2)
    sm = summary(J)
    print("MABNIYAT_RESOURCE_JSON_SHA256 =", sha)
    for k, v in sm.items():
        print(f"  {k}: {v}")
    idx = index_by_surface(J)
    print("  surface-index entries:", len(idx))
    # spot checks required by the prompt
    for w in ("الَّذِي", "أَلَّا", "هَذَا"):
        e = idx.get(w)
        print(f"  {w}:", (e.get("approved_decomposition") or e.get("_form", {}).get("decomposition") or e.get("components")) if e else "— (ليست في الفهرس بهذا التشكيل)")
